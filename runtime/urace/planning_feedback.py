"""Observability → planning feedback loop.

Reads executor call outcomes and objective completion history from state,
computes a feedback_priority_adjustment per objective, and writes it back
into the objective dict so that objective_score_breakdown() picks it up.

Call apply(state) from refresh_scope_priorities() before any scoring.
"""
from __future__ import annotations
from typing import Any

_MAX_CALLS_WINDOW = 20   # look at most recent N calls per objective
_MAX_ADJUST = 12.0       # clamp final adjustment to ±12 points
_STAGNATION_CALLS = 8    # N calls with <30% success triggers stagnation penalty


def _call_outcomes_by_objective(state: dict[str, Any]) -> dict[str, list[str]]:
    """Return {objective_id: [outcome, ...]} from executor_calls history."""
    calls = state.get("executor_state", {}).get("executor_calls", [])
    by_obj: dict[str, list[str]] = {}
    for call in calls:
        obj_id = call.get("objective_id") or call.get("change_id")
        if not obj_id:
            continue
        outcome = call.get("outcome", "unknown")
        by_obj.setdefault(obj_id, []).append(outcome)
    return by_obj


def _success_rate(outcomes: list[str]) -> float:
    if not outcomes:
        return 0.5
    window = outcomes[-_MAX_CALLS_WINDOW:]
    accepted = sum(1 for o in window if o == "accepted")
    return accepted / len(window)


def compute_adjustments(state: dict[str, Any]) -> dict[str, float]:
    """Return {objective_id: adjustment_float} for every objective in state."""
    by_obj = _call_outcomes_by_objective(state)
    objectives = state.get("objectives", [])
    adjustments: dict[str, float] = {}

    # Aggregate stats from completed objectives for baseline comparison
    completed_ids = {o.get("id") for o in objectives if o.get("status") == "completed"}
    total_completed = len(completed_ids)
    total = len(objectives)
    global_completion_rate = (total_completed / total) if total else 0.5

    for obj in objectives:
        obj_id = obj.get("id", "")
        status = obj.get("status", "")

        # Completed/rejected objectives don't need adjustment
        if status in ("completed", "rejected", "cancelled"):
            adjustments[obj_id] = 0.0
            continue

        outcomes = by_obj.get(obj_id, [])
        rate = _success_rate(outcomes)
        n = len(outcomes)

        if n == 0:
            # No history yet; small boost for fresh objectives to encourage first attempt
            adjustments[obj_id] = 1.0
            continue

        # Success rate boost/penalty: range [-8, +8]
        # rate=1.0 → +8; rate=0.5 → 0; rate=0.0 → -8
        rate_component = 8.0 * (rate - 0.5) * 2.0
        rate_component = max(-8.0, min(8.0, rate_component))

        # Stagnation penalty: many attempts, low success
        stagnation = 0.0
        if n >= _STAGNATION_CALLS and rate < 0.3:
            stagnation = -4.0

        # Momentum bonus: global completion rate rising → slight boost for all active
        momentum = min(2.0, global_completion_rate * 4.0) - 2.0  # range [-2, +2]

        total_adj = rate_component + stagnation + momentum
        adjustments[obj_id] = max(-_MAX_ADJUST, min(_MAX_ADJUST, total_adj))

    return adjustments


def apply(state: dict[str, Any]) -> None:
    """Write feedback_priority_adjustment into each objective in state in-place."""
    adjustments = compute_adjustments(state)
    for obj in state.get("objectives", []):
        obj_id = obj.get("id", "")
        obj["feedback_priority_adjustment"] = adjustments.get(obj_id, 0.0)
