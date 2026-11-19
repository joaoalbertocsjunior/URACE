"""Phase 9 — Integrated KPI Dashboard tests."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


_TESTS_DIR = Path(__file__).resolve().parent
_TRIAL_DIR = _TESTS_DIR.parent
_ROOT = _TRIAL_DIR.parent
sys.path.insert(0, str(_ROOT))


def test_dashboard_mock_runs():
    """Runs all mock-compatible phases, produces valid JSON."""
    from trial.run_all_benchmarks import run_all

    with tempfile.TemporaryDirectory() as tmpdir:
        dashboard = run_all(tmpdir, mock=True)
        assert isinstance(dashboard, dict)
        assert dashboard["schema"] == "urace-benchmark-kpi-dashboard-v1"
        assert "kpis" in dashboard
        assert "phases_run" in dashboard
        dashboard_path = Path(tmpdir) / "kpi_dashboard.json"
        assert dashboard_path.exists(), "kpi_dashboard.json not written"
        data = json.loads(dashboard_path.read_text())
        assert data["schema"] == "urace-benchmark-kpi-dashboard-v1"


def test_dashboard_all_kpis_present():
    """kpi_dashboard.json has all KPI keys."""
    from trial.run_all_benchmarks import run_all, KPI_THRESHOLDS

    with tempfile.TemporaryDirectory() as tmpdir:
        dashboard = run_all(tmpdir, mock=True)

    kpis = dashboard["kpis"]
    # All expected KPI keys must be present
    expected_kpis = set(KPI_THRESHOLDS.keys())
    present_kpis = set(kpis.keys())
    missing = expected_kpis - present_kpis
    assert not missing, f"Missing KPI keys in dashboard: {missing}"


def test_dashboard_all_kpis_pass():
    """All KPI values meet acceptance thresholds."""
    from trial.run_all_benchmarks import run_all

    with tempfile.TemporaryDirectory() as tmpdir:
        dashboard = run_all(tmpdir, mock=True)

    failures = []
    for kpi, passed in dashboard["kpi_pass"].items():
        if not passed:
            value = dashboard["kpis"].get(kpi)
            failures.append(f"{kpi}: {value}")

    assert not failures, "KPIs did not meet thresholds:\n" + "\n".join(failures)
