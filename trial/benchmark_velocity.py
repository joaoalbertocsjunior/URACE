"""Phase 5 — Improvement Velocity.

Analyze the longitudinal report to extract velocity metrics:
- improvements_per_window: count of ACCEPTED in each 10-cycle window
- velocity_ratio: improvements in last window / first window (must be > 1.0)
- cost_per_improvement_per_window: total_cost / improvements in each window
- cost_improvement_slope: linear regression slope on cost_per_improvement (must be < 0)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TRIAL_DIR = Path(__file__).parent
_ROOT = _TRIAL_DIR.parent

WINDOW_SIZE = 10
NUM_WINDOWS = 5  # 5 windows × 10 cycles = 50 total


def _linear_regression_slope(x: list[float], y: list[float]) -> float:
    """Compute slope of simple linear regression y = slope*x + intercept."""
    n = len(x)
    if n < 2:
        return 0.0
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_xx = sum(xi * xi for xi in x)
    denom = n * sum_xx - sum_x * sum_x
    if abs(denom) < 1e-15:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom


def compute_velocity_metrics(cycles_data: list[dict]) -> dict:
    """Compute velocity metrics from longitudinal cycles data."""
    n_cycles = len(cycles_data)
    n_windows = min(NUM_WINDOWS, n_cycles // WINDOW_SIZE)

    windows = []
    for w in range(n_windows):
        start = w * WINDOW_SIZE
        end = start + WINDOW_SIZE
        window_cycles = cycles_data[start:end]

        improvements = sum(1 for c in window_cycles if c["outcome"] == "ACCEPTED")
        total_cost = sum(c["cost_usd"] for c in window_cycles)
        cost_per_improvement = total_cost / max(improvements, 1)

        windows.append({
            "window": w + 1,
            "cycle_start": start + 1,
            "cycle_end": end,
            "improvements": improvements,
            "total_cost_usd": round(total_cost, 8),
            "cost_per_improvement_usd": round(cost_per_improvement, 8),
        })

    first_window_improvements = windows[0]["improvements"] if windows else 1
    last_window_improvements = windows[-1]["improvements"] if windows else 1
    velocity_ratio = last_window_improvements / max(first_window_improvements, 1)

    # Linear regression slope on cost_per_improvement over windows
    x_vals = [float(w["window"]) for w in windows]
    y_vals = [w["cost_per_improvement_usd"] for w in windows]
    cost_improvement_slope = _linear_regression_slope(x_vals, y_vals)

    return {
        "windows": windows,
        "velocity_ratio": round(velocity_ratio, 4),
        "cost_improvement_slope": round(cost_improvement_slope, 10),
        "first_window_improvements": first_window_improvements,
        "last_window_improvements": last_window_improvements,
    }


def run_velocity_analysis(output_dir, *, longitudinal_report: dict | None = None) -> dict:
    """Run velocity analysis on the longitudinal report."""
    from trial.benchmark_longitudinal import run_longitudinal

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if longitudinal_report is None:
        # Generate a mock longitudinal report
        longitudinal_report = run_longitudinal(str(output_dir), mock=True, n_cycles=50)

    cycles_data = longitudinal_report.get("cycles", [])
    metrics = compute_velocity_metrics(cycles_data)

    report = {
        "schema": "urace-benchmark-velocity-v1",
        "generated_at": int(time.time()),
        "n_cycles": len(cycles_data),
        "n_windows": len(metrics["windows"]),
        "windows": metrics["windows"],
        "velocity_ratio": metrics["velocity_ratio"],
        "cost_improvement_slope": metrics["cost_improvement_slope"],
        "first_window_improvements": metrics["first_window_improvements"],
        "last_window_improvements": metrics["last_window_improvements"],
    }

    report_path = output_dir / "velocity_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
