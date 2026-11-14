"""Phase 7 — State Resilience tests."""
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


def test_monotonicity_never_violated():
    """cumulative_improvements never decrements."""
    from trial.benchmark_resilience import run_resilience_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_resilience_benchmark(tmpdir)

    assert report["summary"]["monotonicity_violations"] == 0, (
        f"Expected 0 monotonicity violations, got {report['summary']['monotonicity_violations']}"
    )
    # Also verify by scanning cycles directly
    prev = 0
    for cycle in report["cycles"]:
        ci = cycle["cumulative_improvements"]
        assert ci >= prev, (
            f"Cycle {cycle['cycle']}: cumulative_improvements decreased from {prev} to {ci}"
        )
        prev = ci


def test_recovery_within_bound():
    """Max recovery cycles <= 3."""
    from trial.benchmark_resilience import run_resilience_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_resilience_benchmark(tmpdir)

    # With seed=42 and p increasing from 0.5 to 0.85, recovery should be quick
    max_recovery = report["summary"]["recovery_cycles_max"]
    assert max_recovery <= 3, (
        f"Expected max recovery cycles <= 3, got {max_recovery}. "
        f"Fault injections: {report['fault_injections']}"
    )


def test_fault_containment():
    """Pre-fault improvements counted intact after fault."""
    from trial.benchmark_resilience import run_resilience_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_resilience_benchmark(tmpdir)

    assert report["summary"]["fault_containment_rate"] == 1.0, (
        f"Fault containment rate < 1.0: {report['summary']['fault_containment_rate']}"
    )
    # Also check: for each fault injection with recovery, post >= pre
    for fi in report["fault_injections"]:
        if fi["recovery_cycle"] is not None:
            assert fi["post_recovery_improvements"] >= fi["pre_fault_improvements"], (
                f"Fault at cycle {fi['fault_cycle']}: pre_fault={fi['pre_fault_improvements']}, "
                f"post_recovery={fi['post_recovery_improvements']} — improvements lost!"
            )


def test_resilience_report_schema():
    """Correct schema in resilience_report.json."""
    from trial.benchmark_resilience import run_resilience_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_resilience_benchmark(tmpdir)
        assert report["schema"] == "urace-benchmark-resilience-v1"
        assert "cycles" in report
        assert "summary" in report
        required_kpis = {
            "recovery_cycles_max", "recovery_cycles_mean",
            "monotonicity_violations", "fault_containment_rate",
        }
        missing = required_kpis - set(report["summary"].keys())
        assert not missing, f"Missing KPIs: {missing}"
        report_path = Path(tmpdir) / "resilience_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["schema"] == "urace-benchmark-resilience-v1"
