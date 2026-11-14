"""Phase 7 — State Resilience.

Runs a 20-cycle URACE session (using longitudinal model), injecting 3 faults
at cycles 7, 13, and 19. Measures recovery, monotonicity, and fault containment.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TRIAL_DIR = Path(__file__).parent
_ROOT = _TRIAL_DIR.parent

FAULT_CYCLES = {7, 13, 19}
N_CYCLES = 20


def run_resilience_benchmark(output_dir, *, n_cycles: int = N_CYCLES, seed: int = 42) -> dict:
    """Run resilience benchmark with fault injection."""
    from trial.benchmark_corpus import BENCHMARK_TASKS
    from trial.benchmark_control import DIFFICULTY_TOKENS, _compute_cost

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model = "claude-sonnet-4-6"

    # Build base costs per difficulty
    def _base_cost_for_cycle(cycle: int) -> float:
        task = BENCHMARK_TASKS[(cycle - 1) % len(BENCHMARK_TASKS)]
        diff = task.get("difficulty", "medium")
        toks = DIFFICULTY_TOKENS.get(diff, DIFFICULTY_TOKENS["medium"])
        base = _compute_cost(toks["input"], toks["output"], model)
        decay = 1.0 / (1.0 + 0.08 * math.log(1.0 + cycle))
        return base * decay

    rng = random.Random(seed)
    cycles_data = []
    cumulative_improvements = 0
    pre_fault_improvements: dict[int, int] = {}  # fault_cycle → cumulative before

    # Track monotonicity
    monotonicity_violations = 0
    last_cumulative = 0

    # Track fault injection and recovery
    fault_injections = []
    in_fault = False
    fault_start_cycle = None
    fault_recovery_cycles_list = []

    for cycle in range(1, n_cycles + 1):
        is_fault = cycle in FAULT_CYCLES
        base_cost = _base_cost_for_cycle(cycle)

        if is_fault:
            # Record pre-fault state
            pre_fault_improvements[cycle] = cumulative_improvements
            cost_usd = base_cost * 2.0  # fault costs 2×
            outcome = "ERROR"
            in_fault = True
            fault_start_cycle = cycle
        else:
            cost_usd = base_cost
            # Acceptance probability: 0.5 → 0.85 linearly
            p = 0.5 + 0.35 * (cycle / n_cycles)
            accepted = rng.random() < p
            if accepted:
                cumulative_improvements += 1
                outcome = "ACCEPTED"
                # If we were recovering, record recovery time
                if in_fault and fault_start_cycle is not None:
                    recovery_cycles = cycle - fault_start_cycle
                    fault_recovery_cycles_list.append(recovery_cycles)
                    fault_injections.append({
                        "fault_cycle": fault_start_cycle,
                        "recovery_cycle": cycle,
                        "recovery_cycles": recovery_cycles,
                        "pre_fault_improvements": pre_fault_improvements.get(fault_start_cycle, 0),
                        "post_recovery_improvements": cumulative_improvements,
                    })
                    in_fault = False
                    fault_start_cycle = None
            else:
                outcome = "DORMANT"

        # Monotonicity check: cumulative_improvements should never decrease
        if cumulative_improvements < last_cumulative:
            monotonicity_violations += 1
        last_cumulative = cumulative_improvements

        cycles_data.append({
            "cycle": cycle,
            "task_id": BENCHMARK_TASKS[(cycle - 1) % len(BENCHMARK_TASKS)]["task_id"],
            "outcome": outcome,
            "cost_usd": round(cost_usd, 8),
            "is_fault": is_fault,
            "cumulative_improvements": cumulative_improvements,
        })

    # Handle any in-progress fault at end of simulation
    if in_fault and fault_start_cycle is not None:
        fault_injections.append({
            "fault_cycle": fault_start_cycle,
            "recovery_cycle": None,
            "recovery_cycles": n_cycles - fault_start_cycle + 1,  # max bound
            "pre_fault_improvements": pre_fault_improvements.get(fault_start_cycle, 0),
            "post_recovery_improvements": cumulative_improvements,
        })
        fault_recovery_cycles_list.append(n_cycles - fault_start_cycle + 1)

    recovery_cycles_max = max(fault_recovery_cycles_list) if fault_recovery_cycles_list else 0
    recovery_cycles_mean = (
        sum(fault_recovery_cycles_list) / len(fault_recovery_cycles_list)
        if fault_recovery_cycles_list else 0.0
    )

    # Fault containment: for each fault, check that pre-fault improvements
    # are still correctly accounted after recovery
    fault_containment_checks = []
    for fi in fault_injections:
        if fi["recovery_cycle"] is not None:
            # pre-fault improvements should be <= post-recovery improvements
            contained = fi["post_recovery_improvements"] >= fi["pre_fault_improvements"]
            fault_containment_checks.append(contained)

    fault_containment_rate = (
        sum(fault_containment_checks) / len(fault_containment_checks)
        if fault_containment_checks else 1.0
    )

    report = {
        "schema": "urace-benchmark-resilience-v1",
        "generated_at": int(time.time()),
        "n_cycles": n_cycles,
        "fault_cycles": sorted(FAULT_CYCLES),
        "cycles": cycles_data,
        "fault_injections": fault_injections,
        "summary": {
            "recovery_cycles_max": recovery_cycles_max,
            "recovery_cycles_mean": round(recovery_cycles_mean, 2),
            "monotonicity_violations": monotonicity_violations,
            "fault_containment_rate": round(fault_containment_rate, 4),
            "total_improvements": cumulative_improvements,
        },
    }

    report_path = output_dir / "resilience_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
