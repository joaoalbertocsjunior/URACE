"""Regression guard — verify good fixes have zero regressions, bad fixes are detected."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TRIAL_DIR = Path(__file__).parent
_ROOT = _TRIAL_DIR.parent

FULL_TEST_FILES = [
    str(_TRIAL_DIR / "benchmark_product_tests.py"),
    str(_TRIAL_DIR / "benchmark_regression_tests.py"),
]


def _run_pytest_collect_names(test_path: str) -> list[str]:
    """Collect all test names from a test file without running them."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "--collect-only", "-q", "--cache-clear"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    names = []
    for line in (result.stdout + result.stderr).splitlines():
        m = re.match(r"\s*(test_\w+)", line)
        if m:
            names.append(m.group(1))
    return names


def _run_full_suite(product_path: str) -> dict:
    """Run all test files against the given product_path and return pass/fail by test name."""
    all_results: dict[str, bool] = {}
    for test_file in FULL_TEST_FILES:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=no", "--cache-clear",
             f"--import-mode=importlib"],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONPATH": str(_ROOT)},
        )
        stdout = result.stdout + result.stderr
        for line in stdout.splitlines():
            # Lines like: "trial/benchmark_product_tests.py::test_foo PASSED"
            m = re.search(r"::(test_\w+)\s+(PASSED|FAILED|ERROR|SKIPPED)", line)
            if m:
                name = m.group(1)
                status = m.group(2)
                all_results[name] = status in ("PASSED", "SKIPPED")
    return all_results


def _clear_product_pycache() -> None:
    """Remove all pycache entries for benchmark_product to force reimport."""
    pycache = _TRIAL_DIR / "__pycache__"
    if pycache.exists():
        for f in pycache.glob("benchmark_product*.pyc"):
            f.unlink(missing_ok=True)
        for f in pycache.glob("benchmark_product*.pyo"):
            f.unlink(missing_ok=True)


def _run_full_suite_with_source(product_source: str) -> dict:
    """Temporarily write product_source to trial/benchmark_product.py,
    run full suite, restore canonical, return pass/fail by name."""
    product_path = _TRIAL_DIR / "benchmark_product.py"
    canonical_path = _TRIAL_DIR / "benchmark_product_canonical.py"
    # Always restore to canonical — prevents contamination from concurrent access or prior failures
    restore_source = (
        canonical_path.read_text(encoding="utf-8")
        if canonical_path.exists()
        else product_path.read_text(encoding="utf-8")
    )

    _clear_product_pycache()

    try:
        product_path.write_text(product_source, encoding="utf-8")
        _clear_product_pycache()

        all_results: dict[str, bool] = {}
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for test_file in FULL_TEST_FILES:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "pytest", test_file, "-v", "--tb=no",
                 "--cache-clear"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(_ROOT),
                env=env,
            )
            stdout = result.stdout + result.stderr
            for line in stdout.splitlines():
                m = re.search(r"::(test_\w+)\s+(PASSED|FAILED|ERROR|SKIPPED)", line)
                if m:
                    name = m.group(1)
                    status = m.group(2)
                    all_results[name] = status in ("PASSED", "SKIPPED")
        return all_results
    finally:
        product_path.write_text(restore_source, encoding="utf-8")
        _clear_product_pycache()


def _get_canonical_source() -> str:
    """Return canonical product source."""
    canonical = _TRIAL_DIR / "benchmark_product_canonical.py"
    return (
        canonical.read_text(encoding="utf-8")
        if canonical.exists()
        else (_TRIAL_DIR / "benchmark_product.py").read_text(encoding="utf-8")
    )


def _get_baseline_results() -> dict[str, bool]:
    """Run full suite on UNMODIFIED product, return pass/fail by test name."""
    return _run_full_suite_with_source(_get_canonical_source())


def _apply_fix_to_source(source: str, task_id: str) -> str:
    """Apply a MOCK_FIX or BAD_FIX to source string and return patched source."""
    from trial.benchmark_control import MOCK_FIXES, METHOD_PATTERNS, _replace_method

    if task_id.startswith("bad-"):
        from trial.benchmark_bad_fixes import BAD_FIXES
        # Map bad task ids to method names
        bad_method_map = {
            "bad-easy-001": "export_summary",
            "bad-medium-001": "import_csv",
            "bad-hard-001": "transaction_report",
        }
        method_name = bad_method_map.get(task_id)
        new_code = BAD_FIXES.get(task_id)
    else:
        method_name = METHOD_PATTERNS.get(task_id)
        new_code = MOCK_FIXES.get(task_id)

    if method_name is None or new_code is None:
        return source
    return _replace_method(source, method_name, new_code)


# Tests that are expected to break when a task fix is applied.
# These are NOT regressions — they are the intended structural changes:
#   - Stub removal: "test_X_raises" tests fail when stubs are implemented
#   - Complexity fixes: complexity-measuring tests fail when complexity is reduced
_EXPECTED_STUB_BREAKS: dict[str, set[str]] = {
    "medium-001": {"test_import_csv_raises"},
    "medium-002": {"test_forecast_spending_raises"},
    "medium-003": {"test_categorize_uncategorized_raises"},
    "medium-004": {"test_merge_accounts_raises"},
    # Complexity fixes: tests that CHECK for bad complexity patterns will fail
    # after the fix removes those patterns. This is expected/intentional.
    "hard-001": {"test_find_anomalies_complexity"},   # CC > 10 test → fails after refactor
    "hard-002": {"test_transaction_report_complexity"},  # O(n^2) pattern → gone after fix
    "hard-003": {"test_validate_all_complexity"},     # duplicated block check → gone after fix
}


def run_regression_guard(output_dir) -> dict:
    """Run regression analysis for all good fixes and bad fixes."""
    from trial.benchmark_corpus import BENCHMARK_TASKS
    from trial.benchmark_bad_fixes import BAD_FIXES

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    orig_source = _get_canonical_source()

    # Baseline: which tests pass on unmodified code
    baseline = _get_baseline_results()

    good_fix_results = []
    for task in BENCHMARK_TASKS:
        task_id = task["task_id"]
        patched = _apply_fix_to_source(orig_source, task_id)
        after = _run_full_suite_with_source(patched)

        # Expected breaks: stub-status tests for this task (not counted as regressions)
        expected_breaks = _EXPECTED_STUB_BREAKS.get(task_id, set())

        # Regression = test that PASSED in baseline but FAILS after fix,
        # excluding expected stub-status breaks.
        regressions = []
        for test_name, passed_before in baseline.items():
            if test_name in expected_breaks:
                continue
            if passed_before and not after.get(test_name, True):
                regressions.append(test_name)

        good_fix_results.append({
            "task_id": task_id,
            "regressions": regressions,
            "regression_count": len(regressions),
            "regression_rate": 1.0 if regressions else 0.0,
        })

    bad_fix_results = []
    for bad_task_id in BAD_FIXES:
        patched = _apply_fix_to_source(orig_source, bad_task_id)
        after = _run_full_suite_with_source(patched)

        regressions = []
        for test_name, passed_before in baseline.items():
            if passed_before and not after.get(test_name, True):
                regressions.append(test_name)

        bad_fix_results.append({
            "task_id": bad_task_id,
            "regressions": regressions,
            "regression_count": len(regressions),
            "detected": len(regressions) > 0,
        })

    good_regression_rate = max(
        (r["regression_rate"] for r in good_fix_results), default=0.0
    )
    detection_rate = (
        sum(1 for r in bad_fix_results if r["detected"]) / len(bad_fix_results)
        if bad_fix_results else 0.0
    )

    report = {
        "schema": "urace-benchmark-regression-v1",
        "generated_at": int(time.time()),
        "good_fix_results": good_fix_results,
        "bad_fix_results": bad_fix_results,
        "summary": {
            "good_regression_rate": good_regression_rate,
            "detection_rate": round(detection_rate, 4),
            "good_fixes_tested": len(good_fix_results),
            "bad_fixes_tested": len(bad_fix_results),
        },
    }

    report_path = output_dir / "regression_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
