"""Phase 1 — Live API Calibration tests."""
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


def test_calibration_mock_runs():
    """Mock mode produces valid report without API key."""
    from trial.benchmark_calibration import run_calibration

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_calibration(tmpdir)
        assert isinstance(report, dict)
        assert "schema" in report
        assert "tiers" in report
        assert report["mock"] is True


def test_calibration_schema():
    """Schema field is urace-benchmark-calibration-v1."""
    from trial.benchmark_calibration import run_calibration

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_calibration(tmpdir)
        assert report["schema"] == "urace-benchmark-calibration-v1"


def test_calibration_mock_ratios():
    """Mock mode token_ratio == 1.0 for all tiers."""
    from trial.benchmark_calibration import run_calibration

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_calibration(tmpdir)
        for tier_name, tier_data in report["tiers"].items():
            assert tier_data["token_ratio"] == pytest.approx(1.0), (
                f"Tier {tier_name}: expected token_ratio=1.0, got {tier_data['token_ratio']}"
            )


def test_calibration_report_written():
    """JSON file written to output_dir."""
    from trial.benchmark_calibration import run_calibration

    with tempfile.TemporaryDirectory() as tmpdir:
        run_calibration(tmpdir)
        report_path = Path(tmpdir) / "calibration_report.json"
        assert report_path.exists(), "calibration_report.json not written"
        data = json.loads(report_path.read_text())
        assert data["schema"] == "urace-benchmark-calibration-v1"
        assert "easy" in data["tiers"]
        assert "medium" in data["tiers"]
        assert "hard" in data["tiers"]
