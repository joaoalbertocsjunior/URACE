"""Decision record management — §45 and §62d of URACE.md.

Implements the DecisionRecord canonical schema: creation, loading, flagging
provenance-revised, and surfacing provenance gaps as IntegrityGap candidates.

All I/O is through the state document (records keyed under state["decision_records"]).
No Executor calls are made here; this is pure lifecycle-controller logic.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from . import primitives as _primitives


# ── Identifier helpers ────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id(prefix: str) -> str:
    """Generate a spec-compliant Identifier: {prefix}-{10-char-lowercase-hex}."""
    raw = os.urandom(5).hex()
    return f"{prefix}-{raw}"


# ── DecisionRecord CRUD ───────────────────────────────────────────────────────

def create_decision_record(
    *,
    kind: str,
    subject: str,
    outcome: str,
    governing_intent_ref: str,
    state_digest: str,
    executor: dict,
    authority_basis: str | None = None,
    evidence_refs: list[str] | None = None,
    constraints: list[str] | None = None,
    assumptions: list[str] | None = None,
    uncertainty: float | None = None,
    objective_ref: str | None = None,
    plan_ref: str | None = None,
    operation_ref: str | None = None,
    alternatives: list[dict] | None = None,
    justification_summary: str | None = None,
    validity_conditions: list[str] | None = None,
    prior_decision_refs: list[str] | None = None,
    completeness: float | None = None,
    reasoning_steps: list[dict] | None = None,
    justification_context_id: str | None = None,
) -> dict:
    """Build a validated DecisionRecord dict ready for persistence.

    Raises ValueError if any required field is invalid.
    """
    record: dict[str, Any] = {
        "id": _make_id("dec"),
        "kind": kind,
        "subject": subject,
        "outcome": outcome,
        "governing_intent_ref": governing_intent_ref,
        "state_digest": state_digest,
        "executor": executor,
        "provenance_status": "CURRENT",
        "decided_at": _now_iso(),
    }
    if authority_basis is not None:
        record["authority_basis"] = authority_basis
    if evidence_refs is not None:
        record["evidence_refs"] = evidence_refs
    if constraints is not None:
        record["constraints"] = constraints
    if assumptions is not None:
        record["assumptions"] = assumptions
    if uncertainty is not None:
        record["uncertainty"] = uncertainty
    if objective_ref is not None:
        record["objective_ref"] = objective_ref
    if plan_ref is not None:
        record["plan_ref"] = plan_ref
    if operation_ref is not None:
        record["operation_ref"] = operation_ref
    if alternatives is not None:
        record["alternatives"] = alternatives
    if justification_summary is not None:
        record["justification_summary"] = justification_summary
    if validity_conditions is not None:
        record["validity_conditions"] = validity_conditions
    if prior_decision_refs is not None:
        record["prior_decision_refs"] = prior_decision_refs
    if completeness is not None:
        record["completeness"] = completeness
    if reasoning_steps is not None:
        record["reasoning_steps"] = reasoning_steps
    if justification_context_id is not None:
        record["justification_context_id"] = justification_context_id

    _primitives.validate("DecisionRecord", record)
    return record


def flag_provenance_revised(record: dict, revision_notice: str) -> dict:
    """Return a copy of *record* with provenance_status set to PROVENANCE_REVISED.

    The original fields are preserved intact; revision_notice is added.
    Raises ValueError if record is not a valid DecisionRecord or already SUPERSEDED.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a DecisionRecord dict")
    if record.get("provenance_status") == "SUPERSEDED":
        raise ValueError(
            f"DecisionRecord {record.get('id')} is already SUPERSEDED; "
            "cannot flag as PROVENANCE_REVISED"
        )
    if not revision_notice or not isinstance(revision_notice, str):
        raise ValueError("revision_notice must be a non-empty str")
    revised = dict(record)
    revised["provenance_status"] = "PROVENANCE_REVISED"
    revised["revision_notice"] = revision_notice
    _primitives.validate("DecisionRecord", revised)
    return revised


def supersede(record: dict, revision_notice: str) -> dict:
    """Return a copy of *record* with provenance_status set to SUPERSEDED."""
    if not isinstance(record, dict):
        raise ValueError("record must be a DecisionRecord dict")
    if not revision_notice or not isinstance(revision_notice, str):
        raise ValueError("revision_notice must be a non-empty str")
    superseded = dict(record)
    superseded["provenance_status"] = "SUPERSEDED"
    superseded["revision_notice"] = revision_notice
    _primitives.validate("DecisionRecord", superseded)
    return superseded


# ── OutcomeFeedback ───────────────────────────────────────────────────────────

def attach_outcome_feedback(
    record: dict,
    *,
    observed_at: str,
    materialized: bool,
    triggers_revision: bool,
    divergence_note: str | None = None,
    evidence_ref: str | None = None,
) -> dict:
    """Return a copy of *record* with outcome_feedback attached.

    Raises ValueError if record already has outcome_feedback (immutable once written),
    or if materialized is False without a divergence_note.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a DecisionRecord dict")
    if record.get("outcome_feedback") is not None:
        raise ValueError(
            f"DecisionRecord {record.get('id')} already has outcome_feedback; "
            "it is immutable once written"
        )
    feedback: dict[str, Any] = {
        "observed_at": observed_at,
        "materialized": materialized,
        "triggers_revision": triggers_revision,
    }
    if divergence_note is not None:
        feedback["divergence_note"] = divergence_note
    if evidence_ref is not None:
        feedback["evidence_ref"] = evidence_ref
    _primitives.validate("OutcomeFeedback", feedback)
    updated = dict(record)
    updated["outcome_feedback"] = feedback
    if triggers_revision and updated.get("provenance_status") == "CURRENT":
        updated["provenance_status"] = "PROVENANCE_REVISED"
        updated["revision_notice"] = (
            f"Outcome feedback at {observed_at} indicates materialized={materialized}; "
            "triggers_revision=true"
        )
    _primitives.validate("DecisionRecord", updated)
    return updated


# ── Reasoning chain traversal (§62g) ─────────────────────────────────────────

def traverse_reasoning_chain(
    state: dict,
    root_id: str,
    max_depth: int | None = None,
) -> list[dict]:
    """Traverse the reasoning chain rooted at *root_id* to *max_depth*.

    Returns a list of node dicts ordered from root (index 0) to leaves, each with:
      id, kind, subject (if available), decided_at, provenance_status, outcome,
      reasoning_step_count, prior_decision_refs, depth, is_compacted.

    Cycle detection: stops traversal at a node already visited and marks it
    cycle_detected=True. Compacted nodes (not in live state) are marked
    is_compacted=True with available fields from CompactionSummary where possible.

    Raises ValueError if *root_id* is not found in live state and no CompactionSummary
    reference is available.
    """
    records_by_id: dict[str, dict] = {
        r["id"]: r for r in load_decision_records(state)
        if isinstance(r, dict) and "id" in r
    }

    def _node(rec: dict, depth: int) -> dict:
        return {
            "id": rec.get("id"),
            "kind": rec.get("kind"),
            "subject": rec.get("subject"),
            "decided_at": rec.get("decided_at"),
            "provenance_status": rec.get("provenance_status"),
            "outcome": rec.get("outcome"),
            "reasoning_step_count": len(rec.get("reasoning_steps") or []),
            "prior_decision_refs": rec.get("prior_decision_refs") or [],
            "depth": depth,
            "is_compacted": False,
        }

    if root_id not in records_by_id:
        raise ValueError(
            f"DecisionRecord '{root_id}' not found in live state"
        )

    result: list[dict] = []
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(root_id, 0)]

    while queue:
        current_id, depth = queue.pop(0)
        if max_depth is not None and depth > max_depth:
            continue
        if current_id in visited:
            result.append({
                "id": current_id,
                "depth": depth,
                "cycle_detected": True,
            })
            continue
        visited.add(current_id)
        rec = records_by_id.get(current_id)
        if rec is None:
            result.append({
                "id": current_id,
                "depth": depth,
                "is_compacted": True,
            })
            continue
        node = _node(rec, depth)
        result.append(node)
        for ref_id in node["prior_decision_refs"]:
            queue.append((ref_id, depth + 1))

    return result


# ── State document integration ────────────────────────────────────────────────

def load_decision_records(state: dict) -> list[dict]:
    """Return the decision_records list from state, or empty list."""
    return state.get("decision_records") or []


def save_decision_record(state: dict, record: dict) -> None:
    """Append *record* to state["decision_records"] in place.

    Validates before appending. Initialises the list if absent.
    """
    _primitives.validate("DecisionRecord", record)
    if "decision_records" not in state:
        state["decision_records"] = []
    state["decision_records"].append(record)


def find_by_id(state: dict, record_id: str) -> dict | None:
    """Return the DecisionRecord with *record_id* from state, or None."""
    for r in load_decision_records(state):
        if r.get("id") == record_id:
            return r
    return None


def update_in_state(state: dict, updated_record: dict) -> bool:
    """Replace the existing record with the same id in state["decision_records"].

    Returns True if found and replaced, False if not found.
    """
    _primitives.validate("DecisionRecord", updated_record)
    records = load_decision_records(state)
    for i, r in enumerate(records):
        if r.get("id") == updated_record["id"]:
            records[i] = updated_record
            state["decision_records"] = records
            return True
    return False


# ── Integrity gap helpers ─────────────────────────────────────────────────────

def provenance_revised_gap_ids(state: dict) -> list[str]:
    """Return IDs of DecisionRecords with provenance_status=PROVENANCE_REVISED."""
    return [
        r["id"]
        for r in load_decision_records(state)
        if r.get("provenance_status") == "PROVENANCE_REVISED"
    ]


def check_decision_record_gaps(state: dict) -> list[dict]:
    """Return IntegrityGap dicts for any provenance-revised DecisionRecords that are
    still referenced by active Objectives or Operations in state.

    Returns a (possibly empty) list of gap dicts ready for insertion into
    state["integrity_gaps"]. Callers are responsible for persistence.
    """
    revised_ids = set(provenance_revised_gap_ids(state))
    if not revised_ids:
        return []

    active_objectives = [
        o for o in state.get("objectives", [])
        if o.get("status") not in ("COMPLETED", "REJECTED", "SUPERSEDED")
    ]
    active_operations = [
        op for op in state.get("operations", [])
        if op.get("status") not in ("COMPLETED", "REJECTED", "CANCELLED")
    ]

    affected_subjects: list[str] = []
    for obj in active_objectives:
        if obj.get("decision_record_id") in revised_ids:
            affected_subjects.append(f"objective:{obj.get('id')}")
    for op in active_operations:
        if op.get("decision_record_id") in revised_ids:
            affected_subjects.append(f"operation:{op.get('id')}")

    if not affected_subjects:
        return []

    now = _now_iso()
    gap_id = _make_id("gap")
    return [{
        "id": gap_id,
        "kind": "decision-record-provenance-revised",
        "at": now,
        "description": (
            "Active lifecycle work depends on provenance-revised DecisionRecords: "
            + ", ".join(affected_subjects)
        ),
        "severity": "WARNING",
        "source": "decision_record",
        "active": True,
        "resolved_at": None,
        "evidence_id": None,
    }]
