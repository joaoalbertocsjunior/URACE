"""Authority resolution — evaluates every Objective against the delegated boundary.

Spec §14-16: Before acting, URACE MUST resolve whether a decision is
AUTONOMOUSLY_AUTHORIZED, DENIED, REQUIRES_AUTHORITATIVE_DECISION, or UNRESOLVED.
Authority is typed and scoped; it is enforced at runtime, not assumed from config.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

AUTONOMOUSLY_AUTHORIZED = "AUTONOMOUSLY_AUTHORIZED"
DENIED = "DENIED"
REQUIRES_AUTHORITATIVE_DECISION = "REQUIRES_AUTHORITATIVE_DECISION"
UNRESOLVED = "UNRESOLVED"

# Map execution scopes to the delegated authority categories they require.
_SCOPE_AUTHORITY_MAP: dict[str, set[str]] = {
    "implementation": {"local implementation changes"},
    "documentation": {
        "assessment", "objectives", "priority", "plans",
        "local implementation changes",
        "urace.md specification evolution within the retained purpose, authority boundaries, and normative invariants",
    },
    "metrics": {"measurement"},
    "runtime": {"runtime self-evolution and re-bootstrap with validated rollback"},
    "rebootstrap": {
        "runtime self-evolution and re-bootstrap with validated rollback",
        "urace.md specification evolution within the retained purpose, authority boundaries, and normative invariants",
    },
}

# Phrases whose presence in an objective title/reason signal a reserved-decision attempt.
_RESERVED_SIGNAL_PHRASES = (
    "change retained purpose",
    "weaken normative invariants",
    "publish externally",
    "spend money",
    "destructive external effects",
    "remove invariant",
    "delete invariant",
    "override authority",
    "bypass authority",
)

# Verbs that, combined with a constraint keyword, signal constraint-weakening.
_WEAKENING_VERBS = {"remove", "delete", "weaken", "relax", "bypass", "ignore", "disable", "override"}


def _has_weakening_request(text: str) -> bool:
    """Recognize action words while preserving explicit prohibitions on them.

    Only a direct negation and its coordinated verb list are excluded. Other
    clauses, including a later affirmative instruction, remain subject to review.
    This does not change reserved decisions, delegation, or necessity checks.
    """
    verb = r"(?:" + "|".join(sorted(_WEAKENING_VERBS)) + r")"
    prohibition = (r"\b(?:do\s+not|must\s+not|don't|never)\s+" + verb
                   + r"\b(?:\s+(?:or|and)\s+" + verb + r"\b)*")
    actions = re.sub(prohibition, " ", text)
    return re.search(r"\b" + verb + r"\b", actions) is not None


def resolve(
    objective: dict[str, Any],
    config: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether an Objective is within the delegated Authority boundary.

    Returns a resolution record with outcome, basis, gate, and timestamp.
    Records the resolution on the objective so it is attributable.
    """
    authority = state.get("authority") or config.get("authority", {})
    delegated_raw = authority.get("delegated", [])
    reserved_raw = authority.get("reserved", [])
    constraints = list(state.get("constraints") or config.get("constraints", []))

    delegated = {str(d).lower() for d in delegated_raw}
    reserved = {str(r).lower() for r in reserved_raw}

    scope = str(objective.get("scope", "documentation")).lower()
    title = str(objective.get("title", "")).lower()
    reason = str(objective.get("reason", "")).lower()
    combined = f"{title} {reason}"

    # 1. Hard-block: objective matches a reserved decision.
    for reserved_phrase in reserved:
        if reserved_phrase in combined:
            return _resolution(
                DENIED,
                f"Objective matches reserved decision: '{reserved_phrase}'",
                "reserved_decision",
            )
    for signal in _RESERVED_SIGNAL_PHRASES:
        if signal in combined:
            return _resolution(
                DENIED,
                f"Objective contains reserved-decision signal phrase: '{signal}'",
                "reserved_decision_signal",
            )

    # 2. Scope must map to at least one delegated authority category.
    required = _SCOPE_AUTHORITY_MAP.get(scope, set())
    matched = required & delegated
    if required and not matched:
        return _resolution(
            REQUIRES_AUTHORITATIVE_DECISION,
            (
                f"Scope '{scope}' requires authority not found in the delegated boundary. "
                f"Required one of: {sorted(required)}. "
                f"Delegated: {sorted(delegated)}"
            ),
            "scope_boundary",
        )

    # 3. Objective must not signal constraint-weakening.
    for constraint in constraints:
        constraint_lower = str(constraint).lower()
        constraint_keywords = {w for w in constraint_lower.split() if len(w) > 4}
        if _has_weakening_request(combined) and any(kw in combined for kw in constraint_keywords):
            return _resolution(
                REQUIRES_AUTHORITATIVE_DECISION,
                f"Objective appears to weaken retained constraint: '{constraint}'",
                "constraint_protection",
            )

    # 4. Self-evolution policy gate for runtime/rebootstrap scopes.
    if scope in {"runtime", "rebootstrap"}:
        policy_mode = str(state.get("self_evolution_policy", {}).get("mode", "DISABLED")).upper()
        if policy_mode == "DISABLED":
            return _resolution(
                DENIED,
                "Self-evolution policy is DISABLED; runtime/rebootstrap scope not authorized",
                "self_evolution_policy",
            )
        if policy_mode == "NECESSARY_ONLY":
            necessity = str(objective.get("necessity_evidence", "")).strip()
            lower_impact = bool(objective.get("lower_impact_route_sufficient", True))
            if not necessity or lower_impact:
                return _resolution(
                    REQUIRES_AUTHORITATIVE_DECISION,
                    (
                        "Self-evolution policy NECESSARY_ONLY requires non-empty necessity_evidence "
                        "and lower_impact_route_sufficient=False"
                    ),
                    "necessity_gate",
                )

    # 5. Unknown scope — surface for authoritative review rather than silently passing.
    if scope not in _SCOPE_AUTHORITY_MAP:
        return _resolution(
            UNRESOLVED,
            f"Unknown scope '{scope}'; cannot map to delegated authority boundary",
            "unknown_scope",
        )

    return _resolution(
        AUTONOMOUSLY_AUTHORIZED,
        f"Scope '{scope}' matched delegated authority: {sorted(matched or {'(implicit)'})}",
        "passed",
    )


def record_resolution(
    state: dict[str, Any],
    objective: dict[str, Any],
    resolution: dict[str, Any],
) -> None:
    """Append the resolution to state decision_records so it is attributable."""
    state.setdefault("decision_records", []).append({
        "id": f"auth-{objective.get('id', 'unknown')}",
        "at": resolution["resolution_at"],
        "kind": "authority_resolution",
        "objective": objective.get("id"),
        "outcome": resolution["outcome"],
        "basis": resolution["basis"],
        "gate": resolution["gate"],
    })


def _resolution(outcome: str, basis: str, gate: str) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "basis": basis,
        "gate": gate,
        "resolution_at": datetime.now(timezone.utc).isoformat(),
    }
