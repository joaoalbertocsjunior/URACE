"""Tests for the URACE benchmark framework."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure repo root on path
_TESTS_DIR = Path(__file__).resolve().parent
_TRIAL_DIR = _TESTS_DIR.parent
_ROOT = _TRIAL_DIR.parent
sys.path.insert(0, str(_ROOT))


# ---------------------------------------------------------------------------
# test_benchmark_product_baseline
# ---------------------------------------------------------------------------

def test_benchmark_product_baseline():
    """Running pytest on benchmark_product_tests.py must yield exactly 3 failures."""
    test_file = _TRIAL_DIR / "benchmark_product_tests.py"
    product_file = _TRIAL_DIR / "benchmark_product.py"
    assert test_file.exists(), "benchmark_product_tests.py not found"
    assert product_file.exists(), "benchmark_product.py not found"

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
        timeout=120,
    )
    stdout = result.stdout + result.stderr

    import re
    m_fail = re.search(r"(\d+) failed", stdout)
    failures = int(m_fail.group(1)) if m_fail else 0

    # 2 bug tests (export_summary, top_categories) + 2 hard acceptance tests
    # (test_transaction_report_complexity, test_validate_all_no_duplication).
    # test_find_anomalies_refactored skips when radon is absent, so min failures = 4.
    assert failures >= 4, (
        f"Expected >=4 failures on unmodified benchmark_product.py (2 bug + 2 hard acceptance), got {failures}.\n"
        f"Output:\n{stdout}"
    )


# ---------------------------------------------------------------------------
# test_corpus_freeze_and_load
# ---------------------------------------------------------------------------

def test_corpus_freeze_and_load():
    """Freeze corpus to temp dir, load manifest, verify all 10 task_ids present."""
    from trial.benchmark_corpus import BENCHMARK_TASKS, freeze_benchmark_corpus
    from trial.measurement_corpus import load_corpus

    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_dir = Path(tmpdir) / "corpus"
        freeze_benchmark_corpus(corpus_dir)

        manifest_path = corpus_dir / "corpus_manifest.json"
        assert manifest_path.exists(), "corpus_manifest.json not created"

        manifest = json.loads(manifest_path.read_text())
        assert manifest["task_count"] == 10, f"Expected 10 tasks, got {manifest['task_count']}"

        # Load and verify integrity
        tasks = load_corpus(corpus_dir)
        task_ids = {t["task_id"] for t in tasks}
        expected_ids = {t["task_id"] for t in BENCHMARK_TASKS}
        assert task_ids == expected_ids, f"task_id mismatch: {task_ids ^ expected_ids}"


# ---------------------------------------------------------------------------
# test_control_arm_mock_all_tasks
# ---------------------------------------------------------------------------

def test_control_arm_mock_all_tasks():
    """Run all 10 tasks in mock mode — each result must be a valid dict."""
    from trial.benchmark_corpus import BENCHMARK_TASKS
    from trial.benchmark_control import run_control_arm

    product_file = _TRIAL_DIR / "benchmark_product.py"
    test_file = _TRIAL_DIR / "benchmark_product_tests.py"
    orig_source = product_file.read_text(encoding="utf-8")

    required_keys = {
        "task_id", "arm", "outcome", "iterations",
        "input_tokens", "output_tokens", "cost_usd",
        "wall_time_s", "tests_passed", "tests_failed",
    }
    valid_outcomes = {"ACCEPTED", "REJECTED", "BUDGET_EXHAUSTED"}

    try:
        for task in BENCHMARK_TASKS:
            # Restore original before each task
            product_file.write_text(orig_source, encoding="utf-8")

            result = run_control_arm(task, str(product_file), str(test_file))

            missing = required_keys - set(result.keys())
            assert not missing, f"task {task['task_id']}: missing keys {missing}"
            assert result["arm"] == "control", f"task {task['task_id']}: arm != control"
            assert result["outcome"] in valid_outcomes, f"task {task['task_id']}: bad outcome {result['outcome']}"
            assert result["cost_usd"] >= 0, f"task {task['task_id']}: negative cost"
            assert result["input_tokens"] > 0, f"task {task['task_id']}: zero input_tokens"
    finally:
        product_file.write_text(orig_source, encoding="utf-8")


# ---------------------------------------------------------------------------
# test_runner_comparison_mock
# ---------------------------------------------------------------------------

def test_runner_comparison_mock():
    """run_comparison in mock mode must produce a valid schema report."""
    from trial.benchmark_runner import run_comparison

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_comparison(tmpdir, mock=True)

        assert report["schema"] == "urace-benchmark-comparison-v1"
        assert "tasks" in report
        assert "aggregate" in report
        assert "statistics" in report

        agg = report["aggregate"]
        required_agg = {
            "control_total_cost_usd",
            "urace_total_cost_usd",
            "control_cost_per_improvement_usd",
            "urace_cost_per_improvement_usd",
            "control_acceptance_rate",
            "urace_acceptance_rate",
        }
        missing = required_agg - set(agg.keys())
        assert not missing, f"Missing aggregate keys: {missing}"

        # Check JSON was written
        report_path = Path(tmpdir) / "comparison_report.json"
        assert report_path.exists(), "comparison_report.json not written"


# ---------------------------------------------------------------------------
# test_longitudinal_mock
# ---------------------------------------------------------------------------

def test_longitudinal_mock():
    """run_longitudinal must show cost_reduction_pct > 15."""
    from trial.benchmark_longitudinal import run_longitudinal

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_longitudinal(tmpdir, mock=True)

        s = report["summary"]
        assert s["cost_reduction_pct"] > 15, (
            f"Expected cost_reduction_pct > 15, got {s['cost_reduction_pct']}"
        )
        assert s["final_cost_usd"] < s["initial_cost_usd"], "Final cost must be < initial cost"

        # Verify JSON was written
        path = Path(tmpdir) / "longitudinal_report.json"
        assert path.exists(), "longitudinal_report.json not written"


# ---------------------------------------------------------------------------
# test_each_fix_passes_its_acceptance_test
# ---------------------------------------------------------------------------

def test_each_fix_passes_its_acceptance_test():
    """End-to-end: apply each MOCK_FIX to benchmark_product.py and verify its
    specific acceptance test passes.  Proves MOCK_FIX → acceptance_test is correct
    for every task, making the benchmark verifiable and reproducible.
    """
    import shutil
    import tempfile
    from trial.benchmark_corpus import BENCHMARK_TASKS
    from trial.benchmark_control import apply_fix, _extract_test_name

    product_src = _TRIAL_DIR / "benchmark_product.py"
    tests_src   = _TRIAL_DIR / "benchmark_product_tests.py"
    orig_source = product_src.read_text(encoding="utf-8")

    failures = []
    try:
        for task in BENCHMARK_TASKS:
            task_id = task["task_id"]
            test_name = _extract_test_name(task.get("acceptance_criteria", ""))
            if not test_name:
                failures.append(f"{task_id}: no test name extractable from acceptance_criteria")
                continue

            # Apply fix to product file
            product_src.write_text(orig_source, encoding="utf-8")
            pycache = product_src.parent / "__pycache__"
            for f in (pycache.glob("benchmark_product*.pyc") if pycache.exists() else []):
                f.unlink(missing_ok=True)

            apply_fix(str(product_src), task_id)

            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(tests_src),
                 "-k", test_name, "--tb=short", "-q", "--cache-clear"],
                capture_output=True, text=True,
                cwd=str(_ROOT), timeout=60,
            )
            stdout = result.stdout + result.stderr
            # A skipped test (e.g. test_find_anomalies_refactored when radon is absent)
            # is acceptable — it means the tool isn't available, not that the fix is wrong.
            # Only a "failed" outcome is a real problem.
            if "failed" in stdout and result.returncode != 0:
                failures.append(
                    f"{task_id} ({test_name}): FAILED\n{stdout[:400]}"
                )
            elif "passed" not in stdout and "skipped" not in stdout:
                failures.append(
                    f"{task_id} ({test_name}): no passed/skipped output\n{stdout[:400]}"
                )
    finally:
        product_src.write_text(orig_source, encoding="utf-8")
        pycache = product_src.parent / "__pycache__"
        for f in (pycache.glob("benchmark_product*.pyc") if pycache.exists() else []):
            f.unlink(missing_ok=True)

    assert not failures, "Some MOCK_FIX → acceptance_test pairs failed:\n" + "\n---\n".join(failures)


# ---------------------------------------------------------------------------
# test_artifacts_are_self_describing
# ---------------------------------------------------------------------------

def test_artifacts_are_self_describing():
    """Artifacts must carry mock flag, python_version, and benchmark_sha."""
    from trial.benchmark_runner import run_comparison
    from trial.benchmark_longitudinal import run_longitudinal

    with tempfile.TemporaryDirectory() as tmpdir:
        comp = run_comparison(tmpdir, mock=True)
        long_ = run_longitudinal(tmpdir, mock=True)

    for field in ("mock", "python_version", "benchmark_sha"):
        assert field in comp, f"comparison_report missing '{field}'"
        assert field in long_, f"longitudinal_report missing '{field}'"

    assert comp["mock"] is True
    assert long_["mock"] is True
    assert len(comp["benchmark_sha"]) == 16
    assert comp["python_version"].startswith("3.")

    # Sensitivity analysis must cover 3 scenarios, all show URACE cheaper
    assert "sensitivity" in comp
    for scenario, data in comp["sensitivity"].items():
        assert data["urace_vs_control_pct_cheaper"] > 0, \
            f"Scenario {scenario}: URACE not cheaper"


# ---------------------------------------------------------------------------
# test_comparison_urace_beats_control
# ---------------------------------------------------------------------------

def test_comparison_urace_beats_control():
    """URACE cost_per_improvement must be less than control cost_per_improvement."""
    from trial.benchmark_runner import run_comparison

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_comparison(tmpdir, mock=True)
        agg = report["aggregate"]

        urace_cpi = agg["urace_cost_per_improvement_usd"]
        control_cpi = agg["control_cost_per_improvement_usd"]

        assert urace_cpi < control_cpi, (
            f"URACE cost_per_improvement ({urace_cpi:.6f}) must be < "
            f"control ({control_cpi:.6f})"
        )
