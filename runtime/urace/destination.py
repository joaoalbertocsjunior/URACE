"""Destination anchor — preserves retained Intent and detects destination drift.

Spec §8-9, §24: The highest non-delegated Intent is the fixed destination.
Evidence that a route is failing is NOT authorization to change the destination.
Destination drift is invalid even if the new destination appears more valuable.
URACE MUST detect and surface drift rather than silently accepting it.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

# Drift score thresholds
DRIFT_FLAG = 0.30   # surface as evidence, note on objective
DRIFT_BLOCK = 0.65  # escalate to REQUIRES_AUTHORITATIVE_DECISION

# Phrases that signal intent to redefine the destination.
_DESTINATION_REDEFINE_SIGNALS = (
    "change purpose",
    "redefine purpose",
    "new goal",
    "different goal",
    "pivot",
    "replace purpose",
    "abandon purpose",
    "shift direction",
    "change direction",
    "move away from",
)

# Phrases that signal retained-constraint violation.
_RETAINED_VIOLATION_VERBS = {
    "remove", "delete", "weaken", "override", "bypass", "ignore", "disable",
    "drop", "eliminate", "abandon",
}


def anchor_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Extract and hash the retained destination from config intent.

    The anchor is a stable, content-addressed snapshot of the intent that
    URACE was bootstrapped with. Any change to config intent produces a
    different digest, which triggers an integrity alert.
    """
    intent = config.get("intent", {})
    purpose = str(intent.get("purpose", ""))
    retained = sorted(str(r) for r in intent.get("retained", []))
    anchor_content = {"purpose": purpose, "retained": retained}
    digest = hashlib.sha256(
        json.dumps(anchor_content, sort_keys=True).encode()
    ).hexdigest()
    return {
        "purpose": purpose,
        "retained": retained,
        "digest": digest,
        "established_at": datetime.now(timezone.utc).isoformat(),
    }


def drift_score(objective: dict[str, Any], anchor: dict[str, Any]) -> float:
    """Return a 0.0–1.0 drift score for a proposed Objective.

    0.0 = fully aligned with retained destination.
    1.0 = complete destination redefinition attempt.

    Uses heuristic signals; exact semantic alignment requires human review.
    A score at or above DRIFT_BLOCK warrants escalation; DRIFT_FLAG warrants
    recording as evidence without blocking.
    """
    if not anchor:
        return 0.0

    purpose_words = {w for w in str(anchor.get("purpose", "")).lower().split() if len(w) > 4}
    retained = [str(r).lower() for r in anchor.get("retained", [])]

    title = str(objective.get("title", "")).lower()
    reason = str(objective.get("reason", "")).lower()
    scope = str(objective.get("scope", "")).lower()
    combined = f"{title} {reason}"

    score = 0.0

    # Explicit destination-redefine signals (highest weight).
    for signal in _DESTINATION_REDEFINE_SIGNALS:
        if signal in combined:
            score += 0.50
            break

    # Retained-constraint violation (high weight).
    for retained_item in retained:
        retained_keywords = {w for w in retained_item.split() if len(w) > 3}
        if (
            any(verb in combined for verb in _RETAINED_VIOLATION_VERBS)
            and any(kw in combined for kw in retained_keywords)
        ):
            score += 0.30
            break

    # Zero overlap with purpose vocabulary (low weight, only for product scopes).
    if scope not in {"runtime", "rebootstrap"} and purpose_words:
        overlap = sum(1 for w in purpose_words if w in combined)
        if overlap == 0:
            score += 0.10

    return min(1.0, round(score, 4))


def check_anchor_integrity(
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Verify the stored anchor matches the current config intent.

    A digest mismatch means the retained destination changed between sessions;
    this requires an authoritative review before autonomous work continues.
    """
    current = anchor_from_config(config)
    stored = state.get("destination_anchor", {})
    if not stored:
        return {"status": "not_established", "anchor": current}
    if stored.get("digest") != current["digest"]:
        return {
            "status": "changed",
            "prior_digest": stored.get("digest"),
            "current_digest": current["digest"],
            "anchor": current,
            "note": (
                "Retained destination changed since last anchor — "
                "requires authoritative review before autonomous work resumes"
            ),
        }
    return {"status": "intact", "anchor": stored}


def build_drift_evidence(
    objective: dict[str, Any],
    score: float,
    anchor: dict[str, Any],
) -> dict[str, Any]:
    """Build an evidence record for a detected drift event."""
    return {
        "kind": "destination-drift-detected",
        "objective_id": objective.get("id"),
        "objective_title": objective.get("title"),
        "drift_score": score,
        "threshold_flagged": DRIFT_FLAG,
        "threshold_blocked": DRIFT_BLOCK,
        "anchor_digest": anchor.get("digest"),
        "anchor_purpose": anchor.get("purpose"),
        "disposition": (
            "ESCALATED_TO_AUTHORITATIVE_DECISION"
            if score >= DRIFT_BLOCK
            else "FLAGGED_FOR_EVIDENCE"
        ),
        "note": (
            "Drift score measures semantic distance from retained destination; "
            "it is evidence, not Authority. Heuristic — human review recommended."
        ),
    }
