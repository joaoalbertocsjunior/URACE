"""Runtime regression guard — checks whether the most recent quality delta for
each scope is a REGRESSION before allowing state persistence.

The guard is a soft gate: it emits a REGRESSION_BLOCKED decision record and
returns 'REGRESSION' so the cycle caller can suppress the state save. It never
raises and never modifies state without being explicitly asked to record a
decision.
"""
from __future__ import annotations

from typing import Any


def check(state: dict[str, Any], *, scope: str | None = None) -> str:
    """Return 'OK' or 'REGRESSION'.

    Checks the most recent QualityDelta for `scope`. If no scope is given,
    checks all scopes with quality history. Returns 'REGRESSION' if any
    scope's most recent delta is classified REGRESSION and no subsequent
    CHECKPOINT_ACCEPTANCE DecisionRecord exists for that scope.
    """
    deltas = state.get("quality_deltas", [])
    if not deltas:
        return "OK"

    scopes_to_check = {scope} if scope else {d.get("scope") for d in deltas if d.get("scope")}

    for s in scopes_to_check:
        scope_deltas = [d for d in deltas if d.get("scope") == s]
        if not scope_deltas:
            continue
        latest = max(scope_deltas, key=lambda d: d.get("measured_at", ""))
        if latest.get("classification") != "REGRESSION":
            continue
        regression_at = latest.get("measured_at", "")
        accepted = any(
            r.get("kind") == "CHECKPOINT_ACCEPTANCE"
            and r.get("decided_at", "") >= regression_at
            and s in str(r.get("subject", ""))
            for r in state.get("decision_records", [])
        )
        if not accepted:
            return "REGRESSION"

    return "OK"


def record_blocked(state: dict[str, Any], scope: str | None = None) -> dict[str, Any]:
    """Append a REGRESSION_BLOCKED DecisionRecord to state.decision_records.

    Returns the new record.
    """
    from ._common import now, identifier
    record: dict[str, Any] = {
        "id": identifier("decision"),
        "kind": "REGRESSION_BLOCKED",
        "decided_at": now(),
        "disposition": "REGRESSION_BLOCKED",
        "subject": scope or "all-scopes",
        "rationale": "Cycle blocked: most recent quality delta is REGRESSION with no subsequent CHECKPOINT_ACCEPTANCE",
    }
    state.setdefault("decision_records", []).append(record)
    return record


def guard_status(state: dict[str, Any]) -> dict[str, Any]:
    """Return a status dict suitable for `urace check --guard` output."""
    result = check(state)
    deltas = state.get("quality_deltas", [])
    scopes = list({d.get("scope") for d in deltas if d.get("scope")})
    per_scope = {}
    for s in scopes:
        scope_deltas = [d for d in deltas if d.get("scope") == s]
        if scope_deltas:
            latest = max(scope_deltas, key=lambda d: d.get("measured_at", ""))
            per_scope[s] = {
                "classification": latest.get("classification"),
                "measured_at": latest.get("measured_at"),
                "delta": latest.get("delta"),
            }
    return {
        "status": result,
        "checked_scopes": len(scopes),
        "per_scope": per_scope,
    }
