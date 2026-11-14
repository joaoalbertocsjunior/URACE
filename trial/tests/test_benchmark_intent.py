"""Phase 4 — Goal Fidelity tests."""
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


def test_all_good_fixes_in_scope():
    """All 10 MOCK_FIX tasks stay in declared change surface."""
    from trial.benchmark_intent import run_intent_analysis

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_intent_analysis(tmpdir)

    for result in report["good_fix_results"]:
        assert result["in_scope"], (
            f"Task {result['task_id']} has scope violations: {result['scope_violations']}"
        )


def test_out_of_scope_fix_detected():
    """A fix touching off-limits methods (get_balance, add_transaction) is flagged."""
    from trial.benchmark_intent import run_intent_analysis

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_intent_analysis(tmpdir)

    assert len(report["out_of_scope_results"]) > 0, "No out-of-scope results found"
    for result in report["out_of_scope_results"]:
        assert not result["in_scope"], (
            f"Out-of-scope fix {result['task_id']} was NOT detected as out-of-scope"
        )
        assert len(result["scope_violations"]) > 0, (
            f"Out-of-scope fix {result['task_id']} has no scope_violations recorded"
        )


def test_intent_report_schema():
    """Correct schema in intent_report.json."""
    from trial.benchmark_intent import run_intent_analysis

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_intent_analysis(tmpdir)
        assert report["schema"] == "urace-benchmark-intent-v1"
        assert "good_fix_results" in report
        assert "summary" in report
        report_path = Path(tmpdir) / "intent_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["schema"] == "urace-benchmark-intent-v1"


def test_intent_preservation_rate_is_one():
    """intent_preservation_rate == 1.0 for all 10 good fixes."""
    from trial.benchmark_intent import run_intent_analysis

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_intent_analysis(tmpdir)

    rate = report["summary"]["intent_preservation_rate"]
    assert rate == 1.0, f"Expected intent_preservation_rate=1.0, got {rate}"
