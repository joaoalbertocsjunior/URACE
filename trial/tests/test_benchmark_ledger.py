"""Phase 8 — Ledger Integrity tests."""
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


def test_tamper_detection_rate_is_one():
    """All 5 tamper scenarios are detected."""
    from trial.benchmark_ledger import run_ledger_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_ledger_benchmark(tmpdir)

    rate = report["summary"]["tamper_detection_rate"]
    assert rate == 1.0, (
        f"Expected tamper_detection_rate=1.0, got {rate}. "
        f"Scenarios: {report['scenario_results']}"
    )

    for result in report["scenario_results"]:
        assert result["detected"], (
            f"Scenario '{result['scenario']}' was NOT detected as tampered"
        )


def test_false_positive_rate_is_zero():
    """Clean ledger passes verify() without raising."""
    from trial.benchmark_ledger import run_ledger_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_ledger_benchmark(tmpdir)

    assert report["clean_ledger_verified"], (
        "Clean untampered ledger failed verify() — false positive detected"
    )
    assert report["summary"]["false_positive_rate"] == 0.0, (
        f"Expected false_positive_rate=0.0, got {report['summary']['false_positive_rate']}"
    )


def test_ledger_report_schema():
    """Correct schema in ledger_report.json."""
    from trial.benchmark_ledger import run_ledger_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_ledger_benchmark(tmpdir)
        assert report["schema"] == "urace-benchmark-ledger-v1"
        assert "scenario_results" in report
        assert "summary" in report
        required_keys = {"tamper_detection_rate", "scenarios_tested", "scenarios_detected", "false_positive_rate"}
        missing = required_keys - set(report["summary"].keys())
        assert not missing, f"Missing summary keys: {missing}"
        report_path = Path(tmpdir) / "ledger_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["schema"] == "urace-benchmark-ledger-v1"
