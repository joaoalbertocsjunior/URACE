from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

# Keep build_parser and parse_cycles available from urace.cli for existing API callers.

from ._common import (
    now, identifier,
)


# ── Emit helpers (extracted from cli.py) ────────────────────────────────────

def _emit_gap(state: dict[str, Any], kind: str, severity: str, detail: str, **extra: Any) -> None:
    """Emit an IntegrityGap validated against IntegrityGapCatalog (§62l r39).
    Unknown kinds also emit a meta-gap warning.
    """
    try:
        from urace import primitives as _p
        canonical_sev = _p.gap_severity(kind)
        if canonical_sev is None:
            state.setdefault("integrity_gaps", []).append({
                "id": identifier("igap"),
                "kind": "unknown-gap-kind",
                "severity": "WARNING",
                "detail": f"Unregistered IntegrityGap kind '{kind}' — register in IntegrityGapCatalog (§62l)",
                "at": now(),
                "resolved": False,
            })
        used_severity = canonical_sev or severity
    except Exception:
        used_severity = severity
    state.setdefault("integrity_gaps", []).append({
        "id": identifier("igap"),
        "kind": kind,
        "severity": used_severity,
        "detail": detail,
        "at": now(),
        "resolved": False,
        **extra,
    })


def _emit_trace(
    state: dict,
    kind: str,
    summary: str,
    *,
    cycle_id: "str | None" = None,
    operation_id: "str | None" = None,
    decision_id: "str | None" = None,
    detail: "str | None" = None,
    recorded_by: str = "runtime",
) -> None:
    """Emit a TraceRecord into State.trace_records (§62r ObservabilityContract)."""
    state.setdefault("trace_records", []).append({
        "id": identifier("trace-"),
        "at": now(),
        "kind": kind,
        "cycle_id": cycle_id,
        "operation_id": operation_id,
        "decision_id": decision_id,
        "summary": summary,
        "detail": detail,
        "recorded_by": recorded_by,
    })

def _emit_compaction_event(state: dict[str, Any], record_type: str, dropped_count: int) -> None:
    """Emit a CompactionEvent before governed truncation of a record list."""
    event = {
        "id": identifier("cevt"),
        "record_type": record_type,
        "dropped_count": dropped_count,
        "compacted_at": now(),
        "authorized_by": "RetentionPolicy",
    }
    state.setdefault("compaction_events", []).append(event)


def _emit_compliance_record(state: dict[str, Any], domain: str, status: str,
                             operation_id: str | None = None, violation_detail: str | None = None,
                             scope: str | None = None) -> None:
    """Emit a ComplianceRecord and update ComplianceState (spec §54 compliance recording contract, r48)."""
    ts = now()
    record: dict[str, Any] = {"id": identifier("cpl"), "domain": domain, "status": status,
                               "evaluated_at": ts}
    if operation_id:
        record["operation_id"] = operation_id
    if violation_detail:
        record["violation_detail"] = violation_detail
    if scope:
        record["scope"] = scope
    state.setdefault("compliance_records", []).append(record)
    cs_map: dict[str, Any] = state.setdefault("compliance_state", {})
    entry = cs_map.setdefault(domain, {"domain": domain, "status": "UNKNOWN",
                                        "last_checked_at": ts, "violation_refs": [],
                                        "consecutive_clean": 0})
    entry["status"] = status
    entry["last_checked_at"] = ts
    if status == "COMPLIANT":
        entry["consecutive_clean"] = int(entry.get("consecutive_clean", 0)) + 1
    elif status == "NON_COMPLIANT":
        entry["consecutive_clean"] = 0
        entry.setdefault("violation_refs", []).append(record["id"])
