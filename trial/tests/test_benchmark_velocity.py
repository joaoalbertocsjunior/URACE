"""Phase 5 — Improvement Velocity tests."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path


_TESTS_DIR = Path(__file__).resolve().parent
_TRIAL_DIR = _TESTS_DIR.parent
_ROOT = _TRIAL_DIR.parent
sys.path.insert(0, str(_ROOT))


def test_velocity_ratio_positive():
    """velocity_ratio > 1.0: later cycles are more productive."""
    from trial.benchmark_velocity import run_velocity_analysis

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_velocity_analysis(tmpdir)

    assert report["velocity_ratio"] > 1.0, (
        f"Expected velocity_ratio > 1.0, got {report['velocity_ratio']}. "
        f"First window: {report['first_window_improvements']}, "
        f"Last window: {report['last_window_improvements']}"
    )


def test_cost_slope_negative():
    """Cost per improvement falls over windows (slope < 0)."""
    from trial.benchmark_velocity import run_velocity_analysis

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_velocity_analysis(tmpdir)

    slope = report["cost_improvement_slope"]
    assert slope < 0, (
        f"Expected cost_improvement_slope < 0 (falling cost), got {slope}"
    )


def test_velocity_report_schema():
    """Correct schema in velocity_report.json."""
    from trial.benchmark_velocity import run_velocity_analysis

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_velocity_analysis(tmpdir)
        assert report["schema"] == "urace-benchmark-velocity-v1"
        assert "windows" in report
        assert "velocity_ratio" in report
        assert "cost_improvement_slope" in report
        report_path = Path(tmpdir) / "velocity_report.json"
        assert report_path.exists()


def test_velocity_windows_cover_all_cycles():
    """5 windows × 10 cycles = 50 total cycles."""
    from trial.benchmark_velocity import run_velocity_analysis, WINDOW_SIZE, NUM_WINDOWS

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_velocity_analysis(tmpdir)

    n_windows = report["n_windows"]
    n_cycles = report["n_cycles"]

    assert n_windows == NUM_WINDOWS, f"Expected {NUM_WINDOWS} windows, got {n_windows}"
    assert n_cycles == 50, f"Expected 50 cycles, got {n_cycles}"
    total_covered = n_windows * WINDOW_SIZE
    assert total_covered == 50, f"Expected 5×10=50 cycles covered, got {total_covered}"
