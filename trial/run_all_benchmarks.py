"""Run all benchmark phases and produce kpi_dashboard.json.

Usage:
    python3 trial/run_all_benchmarks.py --mock --output /tmp/kpi_out
"""
from __future__ import annotations

import argparse
import json
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TRIAL_DIR = Path(__file__).parent
_ROOT = _TRIAL_DIR.parent

# KPI acceptance thresholds
KPI_THRESHOLDS = {
    "calibration_token_ratio_easy": (0.9, 1.1),      # within 10%
    "calibration_token_ratio_medium": (0.9, 1.1),
    "calibration_token_ratio_hard": (0.9, 1.1),
    "regression_good_regression_rate": (0.0, 0.0),   # must be 0
    "regression_detection_rate": (1.0, 1.0),          # must be 1
    "qualification_recall": (1.0, 1.0),               # must be 1
    "qualification_detection_rate": (1.0, 1.0),       # must be 1
    "intent_preservation_rate": (1.0, 1.0),           # must be 1
    "velocity_ratio": (1.0, float("inf")),             # must be > 1
    "velocity_cost_slope": (float("-inf"), 0.0),       # must be < 0
    "resilience_monotonicity_violations": (0, 0),      # must be 0
    "resilience_recovery_cycles_max": (0, 3),          # must be <= 3
    "resilience_fault_containment_rate": (1.0, 1.0),  # must be 1
    "ledger_tamper_detection_rate": (1.0, 1.0),       # must be 1
    "ledger_false_positive_rate": (0.0, 0.0),         # must be 0
}


def _phase_result(phase_name: str, fn, output_dir: Path, **kwargs) -> tuple[dict | None, str | None]:
    """Run a phase function, return (report, error_message)."""
    try:
        report = fn(str(output_dir), **kwargs)
        return report, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def run_all(output_dir: str, *, mock: bool = True, api_key: str | None = None) -> dict:
    """Run all phases and collect KPIs."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    phases_run = []
    kpis: dict[str, float] = {}
    errors: dict[str, str] = {}

    # --- Phase 1: Calibration ---
    from trial.benchmark_calibration import run_calibration
    phase1_dir = output_path / "phase1_calibration"
    r1, e1 = _phase_result("calibration", run_calibration, phase1_dir,
                            api_key=api_key)
    if r1:
        phases_run.append("phase1_calibration")
        for tier in ("easy", "medium", "hard"):
            key = f"calibration_token_ratio_{tier}"
            kpis[key] = r1["tiers"][tier]["token_ratio"]
    else:
        errors["phase1_calibration"] = e1

    # --- Phase 2: Regression Guard ---
    from trial.benchmark_regression import run_regression_guard
    phase2_dir = output_path / "phase2_regression"
    r2, e2 = _phase_result("regression", run_regression_guard, phase2_dir)
    if r2:
        phases_run.append("phase2_regression")
        kpis["regression_good_regression_rate"] = r2["summary"]["good_regression_rate"]
        kpis["regression_detection_rate"] = r2["summary"]["detection_rate"]
    else:
        errors["phase2_regression"] = e2

    # --- Phase 3: Qualification Signal ---
    from trial.benchmark_qualification import run_qualification
    phase3_dir = output_path / "phase3_qualification"
    r3, e3 = _phase_result("qualification", run_qualification, phase3_dir)
    if r3:
        phases_run.append("phase3_qualification")
        kpis["qualification_recall"] = r3["summary"]["good_recall_extended_gate"]
        kpis["qualification_detection_rate"] = r3["summary"]["detection_rate_extended"]
    else:
        errors["phase3_qualification"] = e3

    # --- Phase 4: Goal Fidelity ---
    from trial.benchmark_intent import run_intent_analysis
    phase4_dir = output_path / "phase4_intent"
    r4, e4 = _phase_result("intent", run_intent_analysis, phase4_dir)
    if r4:
        phases_run.append("phase4_intent")
        kpis["intent_preservation_rate"] = r4["summary"]["intent_preservation_rate"]
    else:
        errors["phase4_intent"] = e4

    # --- Phase 5: Improvement Velocity ---
    from trial.benchmark_velocity import run_velocity_analysis
    phase5_dir = output_path / "phase5_velocity"
    r5, e5 = _phase_result("velocity", run_velocity_analysis, phase5_dir)
    if r5:
        phases_run.append("phase5_velocity")
        kpis["velocity_ratio"] = r5["velocity_ratio"]
        kpis["velocity_cost_slope"] = r5["cost_improvement_slope"]
    else:
        errors["phase5_velocity"] = e5

    # --- Phase 6: Peer Exchange (skipped) ---
    phases_run.append("phase6_peer_exchange_skipped")

    # --- Phase 7: State Resilience ---
    from trial.benchmark_resilience import run_resilience_benchmark
    phase7_dir = output_path / "phase7_resilience"
    r7, e7 = _phase_result("resilience", run_resilience_benchmark, phase7_dir)
    if r7:
        phases_run.append("phase7_resilience")
        kpis["resilience_monotonicity_violations"] = float(r7["summary"]["monotonicity_violations"])
        kpis["resilience_recovery_cycles_max"] = float(r7["summary"]["recovery_cycles_max"])
        kpis["resilience_fault_containment_rate"] = r7["summary"]["fault_containment_rate"]
    else:
        errors["phase7_resilience"] = e7

    # --- Phase 8: Ledger Integrity ---
    from trial.benchmark_ledger import run_ledger_benchmark
    phase8_dir = output_path / "phase8_ledger"
    r8, e8 = _phase_result("ledger", run_ledger_benchmark, phase8_dir)
    if r8:
        phases_run.append("phase8_ledger")
        kpis["ledger_tamper_detection_rate"] = r8["summary"]["tamper_detection_rate"]
        kpis["ledger_false_positive_rate"] = r8["summary"]["false_positive_rate"]
    else:
        errors["phase8_ledger"] = e8

    # --- KPI evaluation ---
    kpi_pass: dict[str, bool] = {}
    for kpi_name, value in kpis.items():
        threshold = KPI_THRESHOLDS.get(kpi_name)
        if threshold is not None:
            lo, hi = threshold
            kpi_pass[kpi_name] = lo <= value <= hi
        else:
            kpi_pass[kpi_name] = True

    all_pass = all(kpi_pass.values())

    dashboard = {
        "schema": "urace-benchmark-kpi-dashboard-v1",
        "generated_at": int(time.time()),
        "mock": mock,
        "phases_run": phases_run,
        "errors": errors,
        "kpis": kpis,
        "kpi_pass": kpi_pass,
        "all_kpis_pass": all_pass,
    }

    dashboard_path = output_path / "kpi_dashboard.json"
    dashboard_path.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
    return dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all URACE benchmarks")
    parser.add_argument("--mock", action="store_true", default=True,
                        help="Run in mock mode (no API key required)")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--api-key", default=None, help="API key for live mode")
    args = parser.parse_args()

    print(f"Running all benchmarks (mock={args.mock}) → {args.output}")
    dashboard = run_all(args.output, mock=args.mock, api_key=args.api_key)

    print(f"\nPhases run: {dashboard['phases_run']}")
    if dashboard["errors"]:
        print(f"Errors: {dashboard['errors']}")
    print("\nKPI Results:")
    for kpi, value in dashboard["kpis"].items():
        passed = dashboard["kpi_pass"].get(kpi, True)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {kpi}: {value}")
    print(f"\nAll KPIs pass: {dashboard['all_kpis_pass']}")
    print(f"Dashboard written: {args.output}/kpi_dashboard.json")


if __name__ == "__main__":
    main()
