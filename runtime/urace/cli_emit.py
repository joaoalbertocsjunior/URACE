from __future__ import annotations

import argparse
import atexit
import copy
import hashlib
import json
import logging
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

from . import executor as intelligent_executor
from . import external_metrics
from . import analytics
from . import scope_priority
from . import updater
from . import authority as authority_resolver
from . import destination as destination_anchor
from . import validation as independent_validation
from . import value_trajectory
from . import outcome_verification
from . import rules as rule_ledger_module
from . import spec_audit as spec_audit_module
from .primitives import OUTPUT_SCHEMA_REGISTRY, INTEGRITY_GAP_CATALOG as IGC_KINDS
from . import decision_record as decision_record_module
from . import compaction as compaction_module
from . import cognitive_resume as cognitive_resume_module
from . import patterns as pattern_catalog_module
from . import continuation as continuation_module
from ._common import nullable_limit
from . import auto_goals, user_controls, command_surface, api_interface, freeform_routing, data_transport
# Keep build_parser and parse_cycles available from urace.cli for existing API callers.
from .cli_parser import build_parser, dispatch_parser, parse_cycles

from ._common import (
    ROOT, CONFIG_PATH, RUNTIME_ROOT, SYSTEM_ROOT,
    now, identifier, atomic_write_text, atomic_write_json, durable_unlink,
    process_exists, state_lock, load_config, save_config, state_path, load_state,
    load_state_for_read, save_state, transaction_path, input_directory,
)
from .inputs import consume_inputs, queue_input, cleanup_consumed_inputs, apply_pending_inputs
from .inspection import (
    document_metrics, compare, objective_is_eligible, goal_is_schedulable,
    objective_score, objective_score_breakdown, goal_portfolio,
    work_evaluations, context_view, resource_accounting,
    executor_efficiency_vital, evolution_vital, render, vitals_snapshot,
    render_vitals, render_cycle, command_catalog, top_level_help,
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
