from __future__ import annotations

from typing import Any

from ._common import now, identifier


def degrade(
    state: dict[str, Any],
    reason: str,
    context: str = "",
    confidence_reduction: float = 0.25,
    cycle_id: "str | None" = None,
) -> None:
    """§62z DefaultContinuationSemantics: record degradation and continue.

    Emits a DegradationEvent into state.degradation_events and a
    DEGRADED trace record. Decrements state.continuation_confidence by
    confidence_reduction (floor 0.0).
    """
    event: dict[str, Any] = {
        "id": identifier("deg-"),
        "at": now(),
        "reason": reason,
        "context": context,
        "confidence_reduction": confidence_reduction,
        "cycle_id": cycle_id,
    }
    state.setdefault("degradation_events", []).append(event)

    current = float(state.get("continuation_confidence", 1.0))
    state["continuation_confidence"] = max(0.0, current - confidence_reduction)

    state.setdefault("trace_records", []).append({
        "id": identifier("trace-"),
        "at": now(),
        "kind": "DEGRADED",
        "cycle_id": cycle_id,
        "operation_id": None,
        "decision_id": None,
        "summary": f"default continuation: {reason}",
        "detail": context or None,
        "recorded_by": "continuation",
    })


def handle_unspecified(
    state: dict[str, Any],
    situation: str,
    context: str = "",
    cycle_id: "str | None" = None,
) -> None:
    """§62z: unspecified situation handler — best-effort continuation.

    Called when no explicit spec contract covers the encountered situation.
    Degrades confidence and emits evidence so the situation is reviewable.
    Never blocks the cycle.
    """
    degrade(state, reason=f"unspecified situation: {situation}", context=context,
            confidence_reduction=0.15, cycle_id=cycle_id)

    state.setdefault("evidence", []).append({
        "id": identifier("ev-"),
        "kind": "unspecified-situation",
        "summary": situation,
        "detail": context,
        "at": now(),
        "provenance": "continuation",
        "confidence": state.get("continuation_confidence", 1.0),
    })


def reset_confidence(state: dict[str, Any]) -> None:
    """Reset continuation_confidence to 1.0 at cycle boundary when no degradation occurred."""
    events = state.get("degradation_events", [])
    # Retain the audit history; the cursor separates successive cycles.
    previous_count = state.get("continuation_event_cursor", 0)
    if len(events) <= previous_count:
        state["continuation_confidence"] = 1.0
    state["continuation_event_cursor"] = len(events)
