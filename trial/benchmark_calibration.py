"""Calibrate DIFFICULTY_TOKENS estimates against real API usage.

Mock mode: returns expected calibration (actual = estimated, ratio = 1.0).
Live mode: runs easy-001, medium-001, hard-001 and records actual token counts.
"""
from __future__ import annotations

import json
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CALIBRATION_TIERS = {
    "easy": "easy-001",
    "medium": "medium-001",
    "hard": "hard-001",
}


def run_calibration(
    output_dir,
    *,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """Run calibration and write calibration_report.json.

    Mock mode: actual == estimated, ratio == 1.0.
    Live mode: runs the 3 tier tasks and records real token counts.
    """
    from trial.benchmark_control import DIFFICULTY_TOKENS, run_control_arm
    from trial.benchmark_corpus import BENCHMARK_TASKS

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mock = api_key is None
    tiers: dict[str, dict] = {}

    for tier_name, task_id in CALIBRATION_TIERS.items():
        estimated_input = DIFFICULTY_TOKENS[tier_name]["input"]
        estimated_output = DIFFICULTY_TOKENS[tier_name]["output"]

        if mock:
            actual_input = estimated_input
            actual_output = estimated_output
        else:
            task = next((t for t in BENCHMARK_TASKS if t["task_id"] == task_id), None)
            if task is None:
                actual_input = estimated_input
                actual_output = estimated_output
            else:
                _trial_dir = Path(__file__).parent
                result = run_control_arm(
                    task,
                    str(_trial_dir / "benchmark_product.py"),
                    str(_trial_dir / "benchmark_product_tests.py"),
                    api_key=api_key,
                    model=model,
                )
                actual_input = result["input_tokens"]
                actual_output = result["output_tokens"]

        token_ratio = actual_input / estimated_input if estimated_input > 0 else 1.0

        tiers[tier_name] = {
            "estimated_input": estimated_input,
            "estimated_output": estimated_output,
            "actual_input": actual_input,
            "actual_output": actual_output,
            "token_ratio": round(token_ratio, 6),
        }

    report = {
        "schema": "urace-benchmark-calibration-v1",
        "generated_at": int(time.time()),
        "mock": mock,
        "tiers": tiers,
    }

    report_path = output_dir / "calibration_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
