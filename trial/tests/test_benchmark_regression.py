"""Phase 2 — Regression Guard tests."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


_TESTS_DIR = Path(__file__).resolve().parent
_TRIAL_DIR = _TESTS_DIR.parent
_ROOT = _TRIAL_DIR.parent
sys.path.insert(0, str(_ROOT))


def test_good_fixes_have_zero_regressions():
    """All 10 MOCK_FIX tasks produce regression_rate == 0."""
    from trial.benchmark_regression import run_regression_guard

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_regression_guard(tmpdir)

    for result in report["good_fix_results"]:
        assert result["regression_rate"] == 0.0, (
            f"Task {result['task_id']} introduced regressions: {result['regressions']}"
        )


def test_bad_fixes_are_detected():
    """All bad fix tasks have regressions detected."""
    from trial.benchmark_regression import run_regression_guard

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_regression_guard(tmpdir)

    assert len(report["bad_fix_results"]) > 0, "No bad fix results found"
    for result in report["bad_fix_results"]:
        assert result["detected"], (
            f"Bad fix {result['task_id']} was NOT detected: no regressions found"
        )


def test_regression_report_schema():
    """Correct schema in regression_report.json."""
    from trial.benchmark_regression import run_regression_guard

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_regression_guard(tmpdir)
        assert report["schema"] == "urace-benchmark-regression-v1"
        assert "good_fix_results" in report
        assert "bad_fix_results" in report
        assert "summary" in report


def test_regression_report_written():
    """JSON file written to output_dir."""
    from trial.benchmark_regression import run_regression_guard

    with tempfile.TemporaryDirectory() as tmpdir:
        run_regression_guard(tmpdir)
        report_path = Path(tmpdir) / "regression_report.json"
        assert report_path.exists(), "regression_report.json not written"
        data = json.loads(report_path.read_text())
        assert data["schema"] == "urace-benchmark-regression-v1"
