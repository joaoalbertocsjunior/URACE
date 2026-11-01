"""Cognitive Resume Context — §62e of URACE.md.

Implements CognitiveResumeContext generation, staleness detection, and injection.

The lifecycle controller MUST generate a fresh CRC at every cycle boundary and
inject it to any Executor that is initialized or reinitialized. An Executor MUST
be resumable from the CRC plus current durable state, with no reliance on
in-process memory from a prior invocation.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import primitives as _primitives


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id(prefix: str) -> str:
    raw = os.urandom(5).hex()
    return f"{prefix}-{raw}"


def _state_digest(state: dict) -> str:
    """SHA-256 of the canonical JSON serialization of *state*."""
    serialized = json.dumps(state, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True).encode()
    return hashlib.sha256(serialized).hexdigest()


# ── Phase inference ───────────────────────────────────────────────────────────

_STATUS_TO_PHASE: dict[str, str] = {
    "ACTIVE":     "EXECUTING",
    "ACCEPTED":   "VALIDATING",
    "ASSESSING":  "ASSESSING",
    "PLANNING":   "PLANNING",
    "VALIDATING": "VALIDATING",
    "DORMANT":    "DORMANT",
    "BLOCKED":    "EXECUTING",
    "RECONCILING": "VALIDATING",
    "REPAIRING":  "EXECUTING",
    "PAUSED":     "DORMANT",
    "WAITING_FOR_CAPACITY":               "DORMANT",
    "WAITING_FOR_AUTHORITATIVE_DECISION": "DORMANT",
    "WAITING_FOR_CONDITION":              "DORMANT",
    "WAITING_FOR_SCHEDULE":               "DORMANT",
}


def _infer_phase(state: dict) -> str:
    """Infer the current lifecycle phase from state."""
    lifecycle_state = state.get("lifecycle_state") or ""
    return _STATUS_TO_PHASE.get(lifecycle_state.upper(), "ASSESSING")


# ── CRC generation ────────────────────────────────────────────────────────────

def generate(state: dict) -> dict:
    """Generate a fresh CognitiveResumeContext from *state*.

    This MUST be called at every cycle boundary before the next cycle begins.
    The returned dict is ready for persistence and injection.
    """
    phase = _infer_phase(state)

    active_objective_id: str | None = None
    active_operation_id: str | None = None

    for obj in state.get("objectives") or []:
        if obj.get("status") in ("ACTIVE", "IN_PROGRESS", "PLANNING"):
            active_objective_id = obj.get("id")
            break

    for op in state.get("operations") or []:
        if op.get("status") in ("ACTIVE", "IN_PROGRESS", "EXECUTING", "VALIDATING"):
            active_operation_id = op.get("id")
            break

    # Find in-progress Transaction id
    pending_tx: str | None = None
    for tx in state.get("transactions") or []:
        if tx.get("phase") in ("PREPARED", "APPLYING", "APPLIED"):
            pending_tx = tx.get("id")
            break

    # Pending validations — derived from state["pending_validation"] (State Document §62b)
    pending_validations: list[str] = [
        pv.get("operation_id") or ""
        for pv in state.get("pending_validation") or []
        if pv.get("status") == "PENDING_CAPABILITY" and pv.get("operation_id")
    ]

    # Blocking gaps
    blocking_gaps: list[str] = [
        gap.get("id") or ""
        for gap in state.get("integrity_gaps") or []
        if gap.get("severity") == "BLOCKING" and gap.get("active") is True
        and gap.get("id")
    ]

    digest = _state_digest(state)

    crc: dict[str, Any] = {
        "id": _make_id("crc"),
        "generated_at": _now_iso(),
        "cycle_phase": phase,
        "pending_validations": pending_validations,
        "blocking_gaps": blocking_gaps,
        "state_digest": digest,
    }
    if active_objective_id is not None:
        crc["active_objective_id"] = active_objective_id
    if active_operation_id is not None:
        crc["active_operation_id"] = active_operation_id
    if pending_tx is not None:
        crc["pending_transaction"] = pending_tx

    _primitives.validate("CognitiveResumeContext", crc)
    return crc


# ── Staleness detection ───────────────────────────────────────────────────────

def is_stale(crc: dict, state: dict) -> bool:
    """Return True if *crc* is stale relative to the current *state*.

    A CRC is stale when its state_digest doesn't match the current state.
    """
    current_digest = _state_digest(state)
    return crc.get("state_digest") != current_digest


def staleness_gap(crc: dict) -> dict:
    """Return an IntegrityGap dict for a stale CognitiveResumeContext."""
    return {
        "id": _make_id("gap"),
        "kind": "cognitive-resume-stale",
        "at": _now_iso(),
        "description": (
            f"CognitiveResumeContext {crc.get('id')} state_digest does not match "
            "current state; regeneration required before Executor initialization"
        ),
        "severity": "WARNING",
        "source": "cognitive_resume",
        "active": True,
        "resolved_at": None,
        "evidence_id": None,
    }


# ── Injection helpers ─────────────────────────────────────────────────────────

def build_executor_context(
    crc: dict,
    state: dict,
    *,
    include_resume_summary: bool = True,
) -> dict:
    """Build the structured context dict injected to an Executor on initialization.

    The returned dict contains:
      - "cognitive_resume_context": the CRC dict
      - "state_digest": the current state digest (from CRC)
      - "cycle_phase": the current phase
      - "blocking_gaps": list of blocking gap IDs
      - "pending_validations": list of pending validation IDs
      - "active_objective_id": if any
      - "active_operation_id": if any
      - "resume_summary": from CRC (if include_resume_summary and present)

    Raises ValueError if the CRC is stale.
    """
    if is_stale(crc, state):
        raise ValueError(
            "CognitiveResumeContext is stale; regenerate before injection. "
            f"CRC id: {crc.get('id')}"
        )
    _primitives.validate("CognitiveResumeContext", crc)

    ctx: dict[str, Any] = {
        "cognitive_resume_context": crc,
        "state_digest": crc["state_digest"],
        "cycle_phase": crc["cycle_phase"],
        "blocking_gaps": crc["blocking_gaps"],
        "pending_validations": crc["pending_validations"],
    }
    if crc.get("active_objective_id"):
        ctx["active_objective_id"] = crc["active_objective_id"]
    if crc.get("active_operation_id"):
        ctx["active_operation_id"] = crc["active_operation_id"]
    if crc.get("pending_transaction"):
        ctx["pending_transaction"] = crc["pending_transaction"]
    if include_resume_summary and crc.get("resume_summary"):
        ctx["resume_summary"] = crc["resume_summary"]
    return ctx


# ── Persistence ───────────────────────────────────────────────────────────────

CRC_FILENAME = "cognitive-resume-context.json"


def save(state_path: str, crc: dict) -> None:
    """Persist the CRC to disk at {state_path}/cognitive-resume-context.json."""
    _primitives.validate("CognitiveResumeContext", crc)
    p = Path(state_path) / CRC_FILENAME
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(crc, f, indent=2, ensure_ascii=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(p)


def load(state_path: str) -> dict | None:
    """Load CRC from disk. Returns None if not present."""
    p = Path(state_path) / CRC_FILENAME
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        crc = json.load(f)
    _primitives.validate("CognitiveResumeContext", crc)
    return crc


def load_or_generate(state_path: str, state: dict) -> dict:
    """Load existing CRC or generate a fresh one. Returns a fresh one if stale."""
    existing = load(state_path)
    if existing is not None and not is_stale(existing, state):
        return existing
    fresh = generate(state)
    save(state_path, fresh)
    return fresh
