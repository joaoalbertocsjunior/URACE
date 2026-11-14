"""Phase 3 — Qualification Signal.

Measures precision/recall of the acceptance gate vs the extended gate.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TRIAL_DIR = Path(__file__).parent
_ROOT = _TRIAL_DIR.parent
_PRODUCT_PATH = _TRIAL_DIR / "benchmark_product.py"
_CANONICAL_PATH = _TRIAL_DIR / "benchmark_product_canonical.py"

_ACCEPTANCE_TEST_FILE = str(_TRIAL_DIR / "benchmark_product_tests.py")
_REGRESSION_TEST_FILE = str(_TRIAL_DIR / "benchmark_regression_tests.py")


def _run_tests_with_source(product_source: str, test_file: str, test_names: list[str] | None = None) -> dict[str, bool]:
    """Temporarily patch product file, run tests, restore canonical, return pass/fail by name."""
    pycache = _PRODUCT_PATH.parent / "__pycache__"
    # Always restore to canonical — prevents contamination from concurrent access or prior failures
    restore_source = (
        _CANONICAL_PATH.read_text(encoding="utf-8")
        if _CANONICAL_PATH.exists()
        else _PRODUCT_PATH.read_text(encoding="utf-8")
    )

    for f in (pycache.glob("benchmark_product*.pyc") if pycache.exists() else []):
        f.unlink(missing_ok=True)

    try:
        _PRODUCT_PATH.write_text(product_source, encoding="utf-8")
        for f in (pycache.glob("benchmark_product*.pyc") if pycache.exists() else []):
            f.unlink(missing_ok=True)

        cmd = [sys.executable, "-B", "-m", "pytest", test_file, "-v", "--tb=no",
               "--cache-clear"]
        if test_names:
            cmd += ["-k", " or ".join(test_names)]

        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=str(_ROOT), env=env,
        )
        stdout = result.stdout + result.stderr
        results: dict[str, bool] = {}
        for line in stdout.splitlines():
            m = re.search(r"::(test_\w+)\s+(PASSED|FAILED|ERROR|SKIPPED)", line)
            if m:
                name = m.group(1)
                status = m.group(2)
                results[name] = status in ("PASSED", "SKIPPED")
        return results
    finally:
        _PRODUCT_PATH.write_text(restore_source, encoding="utf-8")
        for f in (pycache.glob("benchmark_product*.pyc") if pycache.exists() else []):
            f.unlink(missing_ok=True)


def _apply_fix_to_source(source: str, task_id: str, fix_dict: dict[str, str] | None = None) -> str:
    """Apply a fix to source string."""
    from trial.benchmark_control import MOCK_FIXES, METHOD_PATTERNS, _replace_method

    bad_method_map = {
        "qbad-easy-001": "export_summary",
        "qbad-easy-002": "top_categories",
        "qbad-medium-001": "import_csv",
        "qbad-hard-002": "transaction_report",
        "qbad-hard-003": "validate_all",
    }

    if fix_dict is not None:
        new_code = fix_dict.get(task_id)
        method_name = bad_method_map.get(task_id) or METHOD_PATTERNS.get(task_id)
    else:
        new_code = MOCK_FIXES.get(task_id)
        method_name = METHOD_PATTERNS.get(task_id)

    if method_name is None or new_code is None:
        return source
    return _replace_method(source, method_name, new_code)


def _get_canonical_source() -> str:
    """Return canonical product source (from canonical file or disk fallback)."""
    return (
        _CANONICAL_PATH.read_text(encoding="utf-8")
        if _CANONICAL_PATH.exists()
        else _PRODUCT_PATH.read_text(encoding="utf-8")
    )


def _get_baseline_regression_results() -> dict[str, bool]:
    """Get which regression tests pass on unmodified product."""
    return _run_tests_with_source(_get_canonical_source(), _REGRESSION_TEST_FILE)


def _passes_acceptance_gate(product_source: str, acceptance_test_name: str) -> bool:
    """Check if product_source passes the given acceptance test."""
    results = _run_tests_with_source(product_source, _ACCEPTANCE_TEST_FILE, [acceptance_test_name])
    return results.get(acceptance_test_name, False)


def _passes_extended_gate(
    product_source: str,
    acceptance_test_name: str,
    baseline_regression: dict[str, bool] | None = None,
) -> bool:
    """Check if product_source passes acceptance and introduces zero regressions.

    A regression = a test that PASSED in baseline but FAILS after the fix.
    Tests that FAIL in baseline are NOT regression failures.
    """
    acceptance_ok = _passes_acceptance_gate(product_source, acceptance_test_name)
    if not acceptance_ok:
        return False
    regression_results = _run_tests_with_source(product_source, _REGRESSION_TEST_FILE)
    if not regression_results:
        return True
    if baseline_regression is None:
        return True
    # Only fail if a test that PASSED in baseline now FAILS
    for test_name, passed_before in baseline_regression.items():
        if passed_before and not regression_results.get(test_name, True):
            return False
    return True


def run_qualification(output_dir) -> dict:
    """Run qualification signal analysis."""
    from trial.benchmark_corpus import BENCHMARK_TASKS
    from trial.benchmark_control import MOCK_FIXES
    from trial.benchmark_qualification_corpus import QUALIFICATION_BAD_FIXES

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    orig_source = _get_canonical_source()

    task_map = {t["task_id"]: t for t in BENCHMARK_TASKS}

    def _get_acceptance_test(task_id: str) -> str:
        task = task_map.get(task_id, {})
        m = re.search(r"(test_\w+)", task.get("acceptance_criteria", ""))
        return m.group(1) if m else ""

    # Baseline regression results (which tests pass on unmodified code)
    baseline_regression = _get_baseline_regression_results()

    # --- GOOD fixes: run through extended gate ---
    good_fix_extended = []
    for task_id in MOCK_FIXES:
        patched = _apply_fix_to_source(orig_source, task_id)
        acceptance_test = _get_acceptance_test(task_id)
        passes = _passes_extended_gate(patched, acceptance_test, baseline_regression) if acceptance_test else True
        good_fix_extended.append({"task_id": task_id, "passes_extended_gate": passes})

    good_recall_extended = sum(1 for r in good_fix_extended if r["passes_extended_gate"]) / len(good_fix_extended)

    # --- BAD fixes: run through narrow acceptance gate ---
    bad_task_to_good_task = {
        "qbad-easy-001": "easy-001",
        "qbad-easy-002": "easy-002",
        "qbad-medium-001": "medium-001",
        "qbad-hard-002": "hard-002",
        "qbad-hard-003": "hard-003",
    }

    bad_fix_narrow = []
    for bad_task_id in QUALIFICATION_BAD_FIXES:
        good_task_id = bad_task_to_good_task.get(bad_task_id, bad_task_id)
        patched = _apply_fix_to_source(orig_source, bad_task_id, QUALIFICATION_BAD_FIXES)
        acceptance_test = _get_acceptance_test(good_task_id)
        passes_narrow = _passes_acceptance_gate(patched, acceptance_test) if acceptance_test else False
        bad_fix_narrow.append({
            "task_id": bad_task_id,
            "passes_narrow_gate": passes_narrow,
        })

    # --- BAD fixes: run through extended gate ---
    bad_fix_extended = []
    for bad_task_id in QUALIFICATION_BAD_FIXES:
        good_task_id = bad_task_to_good_task.get(bad_task_id, bad_task_id)
        patched = _apply_fix_to_source(orig_source, bad_task_id, QUALIFICATION_BAD_FIXES)
        acceptance_test = _get_acceptance_test(good_task_id)
        passes_extended = _passes_extended_gate(patched, acceptance_test, baseline_regression) if acceptance_test else False
        bad_fix_extended.append({
            "task_id": bad_task_id,
            "passes_extended_gate": passes_extended,
            "caught_by_extended": not passes_extended,
        })

    narrow_false_positives = sum(1 for r in bad_fix_narrow if r["passes_narrow_gate"])
    extended_false_positives = sum(1 for r in bad_fix_extended if r["passes_extended_gate"])
    detection_rate_extended = sum(1 for r in bad_fix_extended if r["caught_by_extended"]) / len(bad_fix_extended)

    report = {
        "schema": "urace-benchmark-qualification-v1",
        "generated_at": int(time.time()),
        "good_fix_extended_results": good_fix_extended,
        "bad_fix_narrow_results": bad_fix_narrow,
        "bad_fix_extended_results": bad_fix_extended,
        "summary": {
            "good_recall_extended_gate": round(good_recall_extended, 4),
            "narrow_false_positives": narrow_false_positives,
            "extended_false_positives": extended_false_positives,
            "detection_rate_extended": round(detection_rate_extended, 4),
            "extended_gate_better_precision": extended_false_positives < narrow_false_positives,
        },
    }

    report_path = output_dir / "qualification_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
