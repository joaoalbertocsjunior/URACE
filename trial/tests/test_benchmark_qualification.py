"""Phase 3 — Qualification Signal tests."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_TRIAL_DIR = _TESTS_DIR.parent
_ROOT = _TRIAL_DIR.parent
sys.path.insert(0, str(_ROOT))


def test_good_fixes_pass_extended_gate():
    """Recall == 1.0: all good fixes pass the extended gate."""
    from trial.benchmark_qualification import run_qualification

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_qualification(tmpdir)

    for result in report["good_fix_extended_results"]:
        assert result["passes_extended_gate"], (
            f"Good fix {result['task_id']} FAILED the extended gate (recall < 1.0)"
        )


def test_bad_fixes_caught_by_extended_gate():
    """All 5 bad fixes fail the extended gate."""
    from trial.benchmark_qualification import run_qualification

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_qualification(tmpdir)

    assert len(report["bad_fix_extended_results"]) == 5, (
        f"Expected 5 bad fix results, got {len(report['bad_fix_extended_results'])}"
    )
    for result in report["bad_fix_extended_results"]:
        assert result["caught_by_extended"], (
            f"Bad fix {result['task_id']} was NOT caught by extended gate"
        )


def test_qualification_report_schema():
    """Correct schema in qualification_report.json."""
    from trial.benchmark_qualification import run_qualification

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_qualification(tmpdir)
        assert report["schema"] == "urace-benchmark-qualification-v1"
        assert "good_fix_extended_results" in report
        assert "bad_fix_extended_results" in report
        assert "summary" in report
        report_path = Path(tmpdir) / "qualification_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["schema"] == "urace-benchmark-qualification-v1"
