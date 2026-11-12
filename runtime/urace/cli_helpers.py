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

from .cli_emit import _emit_gap, _emit_trace, _emit_compaction_event, _emit_compliance_record
from .cli_state import _current_spec_version



def _inspect_list(
    records: list,
    args: Any,
    *,
    fmt: "Callable[[dict], str]",
    empty_msg: str = "No records.",
    envelope: bool = False,
    json_key: str = "records",
    default_limit: int = 20,
    time_field: "str | None" = "at",
) -> int:
    """InspectionContract shared pipeline: time-filter → paginate → output.
    Domain-specific filters must be applied by the caller before passing records.
    """
    if time_field:
        since = getattr(args, "since", None)
        until = getattr(args, "until", None)
        if since:
            records = [r for r in records if (r.get(time_field) or "") >= since]
        if until:
            records = [r for r in records if (r.get(time_field) or "") <= until]
    total = len(records)
    offset = getattr(args, "offset", 0) or 0
    limit = getattr(args, "limit", default_limit)
    if limit is not None:
        records = records[offset: offset + limit]
    else:
        records = records[offset:]
    if getattr(args, "json", False):
        if envelope:
            print(json.dumps(
                {"schema_version": "1.0", json_key: records, "total": total},
                indent=2, sort_keys=True,
            ))
        else:
            print(json.dumps(records, indent=2, sort_keys=True))
    else:
        if not records:
            print(empty_msg)
        else:
            for r in records:
                print(fmt(r))
    return 0


def _help_action(guide: str, args: Any) -> int:
    """Shared SD=True help handler: print guide or emit {schema_version, guide} JSON."""
    if getattr(args, "json", False):
        print(json.dumps({"schema_version": "1.0", "guide": guide}, indent=2))
    else:
        print(guide)
    return 0


def _mutate_command(
    config: dict,
    args: Any,
    *,
    mutate: "Callable[[dict], tuple[dict, str]]",
    trace_kind: str,
    fmt: "Callable[[dict], str]",
) -> int:
    """Mutation pipeline: load → mutate+validate → trace → save → output.
    mutate(state) raises ValueError on validation failure; returns (result_dict, trace_summary).
    Guarantees TraceRecord emission per ObservabilityContract (§62l).
    """
    state = load_state(config)
    try:
        result, trace_summary = mutate(state)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _emit_trace(state, trace_kind, trace_summary)
    save_state(config, state)
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(fmt(result))
    return 0



def _apply_effect_uncertainty_protocol(
    state: dict[str, Any],
    effect_id: str,
    operation_id: str,
    detail: str,
) -> None:
    """EffectUncertaintyProtocol (§62l r39): classify INDETERMINATE, block retry, surface blocker."""
    existing = [e for e in state.get("unresolved_effects", []) if e.get("id") == effect_id]
    if not existing:
        state.setdefault("unresolved_effects", []).append({
            "id": effect_id,
            "operation_id": operation_id,
            "status": "INDETERMINATE",
            "reconciliation_required": True,
            "uncertainty_detail": detail,
            "recorded_at": now(),
        })
    _emit_gap(
        state, "indeterminate-effect-unresolvable", "BLOCKING",
        f"Effect {effect_id} (op {operation_id}) INDETERMINATE: {detail}",
        effect_id=effect_id, operation_id=operation_id,
    )


def _apply_operator_gate(
    state: dict[str, Any],
    condition_kind: str,
    reason: str,
    scope: str = "*",
) -> None:
    """OperatorGateProtocol (§62l r39): surface named BLOCKING gap; clearance requires operator action."""
    _emit_gap(
        state, "operator-gate-open", "BLOCKING",
        f"Operator gate [{condition_kind}]: {reason} (scope={scope}). "
        f"Clear via authenticated lifecycle command; clearance recorded as durable event.",
        gate_condition=condition_kind, gate_scope=scope,
    )


def _determine_revalidation_scope(change_class: str) -> str:
    """Return minimum RevalidationScope for change_class (§62l r39)."""
    try:
        from urace import primitives as _p
        return _p.determine_revalidation_scope(change_class)
    except Exception:
        return "FULL_LIFECYCLE"


def _check_authority_closure(action_source: str) -> bool:
    """Return True if action_source is a valid Authority origin (§62l AuthorityClosureInvariant r39)."""
    try:
        from urace import primitives as _p
        return _p.check_authority_closure(action_source)
    except Exception:
        return True


def _sha256_digest(records: list) -> str:
    """Compute SHA-256 digest of a list of records (canonical JSON)."""
    import json as _json
    return hashlib.sha256(_json.dumps(records, sort_keys=True, default=str).encode()).hexdigest()


def _observe_retention_gaps(state: dict[str, Any], gaps: list[dict]) -> None:
    """Keep one active retention warning per field; retain historical events."""
    def identity(gap):
        text = gap.get('description', gap.get('detail', ''))
        return text.split(' has ', 1)[0]
    existing = {identity(g): g for g in state.get('integrity_gaps', [])
                if g.get('kind') == 'retention-policy-violated' and not g.get('resolved')
                and g.get('active', True)}
    observations = state.setdefault('integrity_gap_observations', {})
    for gap in gaps:
        key = identity(gap)
        if key not in existing:
            state.setdefault('integrity_gaps', []).append(gap)
            existing[key] = gap
        prior = observations.get('retention:' + key, {})
        observations['retention:' + key] = {
            'gap_id': existing[key]['id'], 'last_observed_at': now(),
            'observations': prior.get('observations', 0) + 1,
            'latest_detail': gap.get('description', gap.get('detail', ''))}


def _validate_citizen_base_conformance(state: dict[str, Any]) -> None:
    """Emit citizen-base-violation gaps for records missing CitizenBase required fields (A2 r54)."""
    base_required = {"id", "created_at", "updated_at"}
    list_fields = [
        "goal_records", "intent_records", "constraint_records",
        "decision_records", "evidence", "operations", "executor_records",
        "compaction_events", "compliance_records", "assessment_records",
        "metric_definitions", "wake_registry", "retention_policies",
    ]
    existing = {gap.get('detail', '').split(' missing CitizenBase fields:', 1)[0]: gap
                for gap in state.get('integrity_gaps', [])
                if gap.get('kind') == 'citizen-base-violation' and not gap.get('resolved')
                and gap.get('active', True) and ' missing CitizenBase fields:' in gap.get('detail', '')}
    observations = state.setdefault('integrity_gap_observations', {})
    for field in list_fields:
        for record in state.get(field, []):
            if not isinstance(record, dict):
                continue
            missing = base_required - set(record.keys())
            if missing:
                prefix = f"{field} record {record.get('id', '?')}"
                # Preserve every historical gap. Record repeated observations of
                # the same unresolved entity instead of appending O(cycles) gaps.
                if prefix not in existing:
                    _emit_gap(state, "citizen-base-violation", "WARNING",
                              prefix + " missing CitizenBase fields: " + repr(sorted(missing)))
                    existing[prefix] = state['integrity_gaps'][-1]
                prior = observations.get('citizen:' + prefix, {})
                observations['citizen:' + prefix] = {
                    'gap_id': existing[prefix]['id'], 'last_observed_at': now(),
                    'observations': prior.get('observations', 0) + 1,
                    'missing_fields': sorted(missing), 'condition_still_present': True}
            else:
                key = 'citizen:' + f"{field} record {record.get('id', '?')}"
                if key in observations:
                    observations[key]['condition_still_present'] = False


_loaded_state_snapshot: dict[str, Any] | None = None


def _validate_immutable_fields(current_state: dict[str, Any], previous_state: dict[str, Any] | None) -> None:
    """Check that id and created_at haven't been mutated on existing records (A6 r54)."""
    if not previous_state:
        return
    list_fields = ["goal_records", "intent_records", "constraint_records",
                   "decision_records", "evidence", "operations"]
    for field in list_fields:
        prev_by_id = {r["id"]: r for r in previous_state.get(field, []) if isinstance(r, dict) and "id" in r}
        for record in current_state.get(field, []):
            if not isinstance(record, dict):
                continue
            rid = record.get("id")
            if rid in prev_by_id:
                prev = prev_by_id[rid]
                if record.get("created_at") != prev.get("created_at"):
                    _emit_gap(current_state, "citizen-base-violation", "WARNING",
                        f"{field} record {rid} created_at mutated (immutability violation)")


def _compact_with_chunking(state: dict[str, Any], field_path: str, records: list, policy: dict) -> list:
    """Group records by (objective_id, objective_status) for OBJECTIVE_LIFECYCLE chunking (A3 r54)."""
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for r in records:
        key = (r.get("objective_id", "__none__"), r.get("objective_status", "__none__"))
        groups[key].append(r)

    chunks = []
    for (obj_id, obj_status), group_records in groups.items():
        is_decompactable = obj_status in ("completed", "cancelled")
        record_ids = [r["id"] for r in group_records if "id" in r]
        digest = _sha256_digest(group_records)
        chunk = {
            "id": identifier("chunk-"),
            "created_at": now(),
            "updated_at": now(),
            "field_path": field_path,
            "objective_id": obj_id if obj_id != "__none__" else None,
            "objective_status": obj_status if obj_status != "__none__" else None,
            "record_ids": record_ids,
            "time_range": {
                "earliest": min((r.get("created_at", now()) for r in group_records), default=now()),
                "latest": max((r.get("updated_at", now()) for r in group_records), default=now()),
            },
            "record_count": len(group_records),
            "original_digest": digest,
            "is_decompactable": is_decompactable,
            "authorized_by": f"retention_policy:{policy.get('id', 'default')}",
            "status": "ARCHIVED" if is_decompactable else "ACTIVE",
            "archived_at": now() if is_decompactable else None,
            "chunk_format": "OBJECTIVE_LIFECYCLE",
        }
        chunks.append(chunk)
        _emit_compaction_event(state, field_path, len(group_records))

    state.setdefault("chunks", []).extend(chunks)
    return chunks


def _validate_authority_basis_binding(state: dict[str, Any], objective: dict) -> None:
    """Check that authority_basis references an active Rule Ledger entry (A7 r54)."""
    authority_basis = objective.get("authority_basis")
    if not authority_basis:
        return
    ledger = state.get("rule_ledger", {})
    rules = ledger.get("rules") or []
    active_ids = {r["id"] for r in rules if isinstance(r, dict) and r.get("status") not in ("SUPERSEDED", "DELETED")}
    if authority_basis not in active_ids and not str(authority_basis).startswith("DIRECTIVE"):
        _emit_gap(state, "authority-cache-stale", "WARNING",
            f"authority_basis {authority_basis!r} references no active Rule Ledger entry")


def _ledger_size_warning(state_path_val: Path) -> dict | None:
    ledger = state_path_val.parent / "context_ledger.jsonl"
    if not ledger.exists():
        return None
    size_mb = ledger.stat().st_size / (1024 * 1024)
    if size_mb >= 50:
        return {"warning": "ledger_large", "size_mb": round(size_mb, 1), "action": "run 'urace compact' to archive old entries"}
    return None


def _build_inspection_surface(state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Build InspectionSurface-compliant output for urace check (§62l r39)."""
    gaps = state.get("integrity_gaps", [])
    blocking = [g for g in gaps if g.get("severity") == "BLOCKING" and not g.get("resolved", False)]
    warning = [g for g in gaps if g.get("severity") == "WARNING" and not g.get("resolved", False)]
    indeterminate = list(state.get("unresolved_effects", []))
    operator_gates = [g for g in blocking if g.get("kind") == "operator-gate-open"]
    spec_ver = _current_spec_version()
    stale_items: list[dict] = []
    for ref in list(state.get("derivation_refs", [])) + list(state.get("derived_manifest_refs", [])):
        if isinstance(ref, dict) and ref.get("spec_version") != spec_ver:
            stale_items.append({"kind": "stale-manifest", "manifest_id": ref.get("manifest_id"), "stale_version": ref.get("spec_version")})
    cap_readiness: dict[str, str] = {}
    for e in state.get("capability_states", []):
        if isinstance(e, dict):
            cap_id = e.get("capability_id") or e.get("id", "?")
            cap_readiness[cap_id] = e.get("status", "ABSENT")
    scheduled = [
        {"id": r.get("id"), "kind": r.get("kind"), "scheduled_at": r.get("scheduled_at")}
        for r in state.get("wake_registry", []) if isinstance(r, dict)
    ]
    policy_violations = [g for g in gaps if any(k in g.get("kind", "") for k in ("policy", "constraint", "governing-record"))]
    open_pvs = [pv for pv in state.get("pending_validations", []) if isinstance(pv, dict) and not pv.get("resolved_at")]
    n_block, n_warn = len(blocking), len(warning)
    lc = state.get("lifecycle_state", "UNKNOWN")
    if n_block:
        summary = f"{lc}: {n_block} blocking gap(s), {n_warn} warning(s)"
    elif n_warn:
        summary = f"{lc}: {n_warn} warning(s), no blocking gaps"
    else:
        summary = f"{lc}: no gaps"
    return {
        "lifecycle_state": lc,
        "assessed_at": (state.get("executor_state") or {}).get("last_discovery_at") or now(),
        "blocking_gaps": blocking,
        "warning_gaps": warning,
        "indeterminate_effects": indeterminate,
        "operator_gates": operator_gates,
        "stale_items": stale_items,
        "capability_readiness": cap_readiness,
        "scheduled_conditions": scheduled,
        "policy_violations": policy_violations,
        "open_pending_validations": open_pvs,
        "summary": summary,
    }

def _try_reconcile_effect(root: Path, effect: dict[str, Any]) -> bool:
    """Attempt strongest-practical reconciliation for an indeterminate effect.

    Returns True if the effect is confirmed complete (can be removed from
    unresolved_effects). Returns False if outcome is still indeterminate.

    Strategies used in order:
      1. Check whether the changed files match the intended after-content hash.
      2. Check whether the effect's transaction journal phase is VALIDATED or ACCEPTED.
      3. Fall through to indeterminate (False).
    """
    # Strategy 1: file content hash check.
    file_hashes = effect.get("expected_file_hashes", {})
    if file_hashes:
        import hashlib as _hashlib
        all_match = all(
            (root / relative).exists()
            and _hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
            for relative, expected in file_hashes.items()
        )
        if all_match:
            return True

    # Strategy 2: transaction journal phase.
    journal_phase = effect.get("journal_phase")
    if journal_phase in {"VALIDATED", "ACCEPTED"}:
        return True

    return False


def _reconcile_unresolved_effects(root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    """Attempt reconciliation of all unresolved effects. Return those still unresolved."""
    reconciled, still_unresolved = [], []
    try:
        for effect in state.get("unresolved_effects", []):
            if _try_reconcile_effect(root, effect):
                reconciled.append({**effect, "reconciled_at": now(), "outcome": "CONFIRMED_COMPLETE"})
            else:
                still_unresolved.append(effect)
        if reconciled:
            state.setdefault("evidence", []).append({
                "id": identifier("evidence"), "at": now(),
                "kind": "effect-reconciliation",
                "reconciled_count": len(reconciled),
                "reconciled": reconciled,
            })
        # R2 — Audit trail Evidence record after reconciliation completes
        state.setdefault("evidence", []).append({
            "id": identifier("evidence"),
            "at": now(),
            "kind": "unresolved-effects-reconciliation",
            "summary": f"reconciled {len(reconciled)} unresolved effects",
            "reconciled_count": len(reconciled),
            "authority": "system",
        })
    except Exception as _reconcile_error:
        _emit_gap(state, "unresolved-effects-reconciliation-failure", "WARNING",
                  f"_reconcile_unresolved_effects raised exception: {type(_reconcile_error).__name__}: {_reconcile_error}")
    return still_unresolved


def _executor_independent_work(
    config: dict[str, Any],
    state: dict[str, Any],
    observation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Work that can proceed regardless of Executor availability.

    Spec §55: Zero-executor cardinality is NOT equivalent to zero autonomy.
    Executor-independent work (input processing, metric observation, wake
    evaluation, pending-validation follow-up) remains eligible.
    """
    work_done = []
    from .cli_lifecycle import discover  # lazy import — avoids circular dep at module level

    # Wake conditions are evaluated by cycle() before this function is called.

    # 2. Surface pending-validation observations that have been waiting too long.
    pending = state.get("pending_validations", [])
    if pending:
        work_done.append({
            "kind": "pending_validation_surfaced",
            "count": len(pending),
            "note": "Validation capability was previously unavailable; re-evaluate when restored",
        })

    # 3. Deterministic discovery (regression / unresolved markers) — no executor needed.
    det = discover(config, state, observation)
    if det:
        work_done.append({"kind": "deterministic_objective_discovered", "objective_id": det.get("id")})

    # 4. Process any queued input files.
    inbox = input_directory(config)
    if inbox.exists():
        pending_inputs = [p for p in inbox.glob("*.json") if p.exists()]
        if pending_inputs:
            work_done.append({"kind": "pending_inputs", "count": len(pending_inputs)})

    return work_done


def _check_scheduled_tasks(state: dict[str, Any], config: dict[str, Any]) -> None:
    """AP18 — evaluate ScheduledTasks and trigger due ones."""
    from urace._common import scheduled_task_due
    import datetime as _dt
    _now_ts = time.time()
    for _task in state.get("scheduled_tasks", []):
        if _task.get("status") != "ACTIVE":
            continue
        if scheduled_task_due(_task, _now_ts):
            _task["last_run_at"] = now()
            _task.setdefault("run_count", 0)
            _task["run_count"] = int(_task["run_count"]) + 1
            _sched = _task.get("schedule", {})
            if _sched.get("kind") == "INTERVAL_SECONDS":
                _interval = _sched.get("interval_seconds", 3600)
                _next = _dt.datetime.fromtimestamp(_now_ts + _interval, tz=_dt.timezone.utc).isoformat()
                _sched["next_run_at"] = _next
            state.setdefault("evidence", []).append({
                "id": identifier("evidence"),
                "at": now(),
                "kind": "scheduled-task-triggered",
                "source": "cli:cycle",
                "detail": f"task {_task.get('id')} ({_task.get('name')}) triggered: action={_task.get('action')}",
            })


def _record_quality_delta(
    state: dict[str, Any],
    operation_id: str,
    scope: str,
    score_before: "float | None",
    score_after: float,
    measured_at: str,
) -> dict[str, Any]:
    """Emit a QualityDelta and update QualityStateEntry in state.quality_state (AP9 — Monotone Accumulator).

    r32: quality streak state lives in state.quality_state (Product-level), not executor_state.
    This ensures streak history survives executor replacement (agnosticism-first principle).
    """
    delta = round(score_after - score_before, 6) if score_before is not None else 0.0
    if delta > 0.0:
        classification = "IMPROVEMENT"
    elif delta < 0.0:
        classification = "REGRESSION"
    else:
        classification = "NEUTRAL"
    record: dict[str, Any] = {
        "id": identifier("qdl"),
        "operation_id": operation_id,
        "scope": scope,
        "score_after": score_after,
        "delta": delta,
        "classification": classification,
        "measured_at": measured_at,
    }
    if score_before is not None:
        record["score_before"] = score_before
    state.setdefault("quality_deltas", []).append(record)

    qs_map: dict[str, Any] = state.setdefault("quality_state", {})
    entry = qs_map.setdefault(scope, {
        "scope": scope,
        "current_streak": 0,
        "best_streak": 0,
        "streak_started_at": None,
        "last_evaluated_at": measured_at,
    })
    if classification == "IMPROVEMENT":
        entry["current_streak"] = entry.get("current_streak", 0) + 1
        if entry["current_streak"] == 1:
            entry["streak_started_at"] = measured_at
        if entry["current_streak"] > entry.get("best_streak", 0):
            entry["best_streak"] = entry["current_streak"]
    elif classification == "REGRESSION":
        entry["current_streak"] = 0
        entry["streak_started_at"] = None
    entry["last_evaluated_at"] = measured_at
    return record


def _check_staleness(state: dict[str, Any], config: dict[str, Any]) -> list[str]:
    """Staleness Detection Mechanism — §62c r33: SD=True, WARNING-only, three domains.
    D2: per-scope decision windows. X6: stale decisions produce PendingValidation records.
    """
    import datetime as _dt
    cfg = config.get("staleness_windows", {})
    global_decision_window = cfg.get("decision_seconds", 86400 * 30)
    evidence_window = cfg.get("evidence_seconds", 86400 * 7)
    rules_window = cfg.get("rules_seconds", 86400 * 90)
    by_scope: dict[str, int] = cfg.get("by_scope", {})
    now_ts = _dt.datetime.now(_dt.timezone.utc).timestamp()
    warnings: list[str] = []

    # r55: CheckpointRecord baseline — use last accepted-product-change checkpoint for temporal baseline
    _checkpoints = state.get("checkpoints", [])
    _last_accepted_checkpoint = next(
        (c for c in reversed(_checkpoints) if isinstance(c, dict) and c.get("kind") == "accepted-product-change"),
        None,
    )
    if _last_accepted_checkpoint:
        try:
            _cp_ts = _dt.datetime.fromisoformat(_last_accepted_checkpoint["at"]).timestamp()
            if now_ts - _cp_ts > evidence_window:
                warnings.append(f"staleness:checkpoint-baseline — last accepted-product-change checkpoint age>{evidence_window}s")
        except (ValueError, KeyError):
            pass

    # DOMAIN: Decisions — per-scope window resolution (D2) + PendingValidation production (X6)
    decisions = state.get("decision_records", [])
    pending_validations = state.setdefault("pending_validations", [])
    existing_pv_sources = {pv.get("source_operation_id") for pv in pending_validations}
    for rec in decisions:
        if rec.get("provenance_status", "CURRENT") != "CURRENT":
            continue
        scope = rec.get("scope", "*")
        window = by_scope.get(scope, global_decision_window)
        ts_str = rec.get("decided_at") or rec.get("at") or rec.get("created_at") or ""
        if not ts_str:
            continue
        try:
            age = now_ts - _dt.datetime.fromisoformat(ts_str).timestamp()
        except ValueError:
            continue
        if age > window:
            rec_id = rec.get("id", "unknown")
            warnings.append(
                f"staleness:decisions — DecisionRecord {rec_id} scope={scope} age>{window}s"
            )
            # X6: produce PendingValidation if not already queued
            if rec_id not in existing_pv_sources:
                pv_id = identifier("pnv")
                pending_validations.append({
                    "id": pv_id,
                    "source_operation_id": rec_id,
                    "kind": "stale-decision-revalidation",
                    "blocked_on_capability": "decision-revalidation",
                    "queued_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                    "stale_reason": f"decision_age exceeds staleness window ({window}s) for scope={scope}",
                })
                existing_pv_sources.add(rec_id)

    # DOMAIN: Evidence
    evidence = state.get("evidence", [])
    if evidence:
        latest = max((e.get("at") or "" for e in evidence), default="")
        if latest:
            try:
                if now_ts - _dt.datetime.fromisoformat(latest).timestamp() > evidence_window:
                    warnings.append(f"staleness:evidence — no new evidence in >{evidence_window}s")
            except ValueError:
                pass

    # DOMAIN: Rules
    rule_ledger = state.get("rule_ledger", {})
    rules_list = rule_ledger.get("rules", []) if isinstance(rule_ledger, dict) else []
    if rules_list:
        latest = max((r.get("created_at") or r.get("at") or "" for r in rules_list), default="")
        if latest:
            try:
                if now_ts - _dt.datetime.fromisoformat(latest).timestamp() > rules_window:
                    warnings.append(f"staleness:rules — no rule changes in >{rules_window}s")
            except ValueError:
                pass

    # R1 — Mutable metric baseline drift detection: scan ALL MetricDefinitions
    evidence_list = state.get("evidence", [])
    replaced_metric_ids = {
        e.get("metric_id") for e in evidence_list
        if isinstance(e, dict) and e.get("kind") == "metric-definition-replaced"
    }
    for mdef in state.get("metric_definitions", []):
        if not isinstance(mdef, dict):
            continue
        authority = mdef.get("authority", "")
        updated_at_str = mdef.get("updated_at", "")
        created_at_str = mdef.get("created_at", "")
        if not updated_at_str or not created_at_str:
            continue
        try:
            updated_ts = _dt.datetime.fromisoformat(updated_at_str).timestamp()
            created_ts = _dt.datetime.fromisoformat(created_at_str).timestamp()
        except ValueError:
            continue
        if updated_ts > created_ts:
            mdef_id = mdef.get("id", "unknown")
            if authority == "DIRECTIVE":
                # DIRECTIVE metrics already checked via existing contract; no new gap here
                pass
            else:
                # Non-DIRECTIVE: emit WARNING if no metric-definition-replaced evidence exists
                if mdef_id not in replaced_metric_ids:
                    _emit_gap(state, "metric-definition-drift", "WARNING",
                              f"MetricDefinition {mdef_id} name={mdef.get('name')} mutated without replacement evidence record")
                    warnings.append(f"staleness:metric-definition — MetricDefinition {mdef_id} updated_at > created_at, no metric-definition-replaced evidence")

    return warnings


def _regression_checkpoint_gate_passes(state: dict[str, Any], scope: str) -> bool:
    """X2 gate: if most recent QualityDelta for scope is REGRESSION, require a
    CHECKPOINT_ACCEPTANCE DecisionRecord written after that regression before accepting
    a new checkpoint. Returns True (gate passes) or False (gate blocks — PENDING).
    Gate is a no-op when no quality history exists for the scope.
    """
    deltas = [
        d for d in state.get("quality_deltas", [])
        if d.get("scope") == scope
    ]
    if not deltas:
        return True  # no quality history — gate is inactive for this scope
    latest = max(deltas, key=lambda d: d.get("measured_at", ""))
    if latest.get("classification") != "REGRESSION":
        return True  # most recent delta is not a regression — gate passes
    regression_at = latest.get("measured_at", "")
    # Look for a CHECKPOINT_ACCEPTANCE DecisionRecord written after the regression
    for rec in state.get("decision_records", []):
        if rec.get("kind") != "CHECKPOINT_ACCEPTANCE":
            continue
        decided_at = rec.get("decided_at", "")
        if decided_at >= regression_at and scope in str(rec.get("subject", "")):
            return True
    return False  # REGRESSION scope, no justifying DecisionRecord found


def _apply_customizations(state: dict[str, Any], config: dict[str, Any]) -> None:
    """AP19 — apply user customizations from config to state."""
    customizations = config.get("user_customizations", [])
    for cust in customizations:
        scope = cust.get("scope")
        key = cust.get("key")
        value = cust.get("value")
        if scope == "config" and key and value is not None:
            pass  # config-scope customizations are already in config
        elif scope == "runtime_behavior" and key:
            state.setdefault("user_customizations_applied", {})[key] = value


def _evaluate_sweet_spot(state: dict[str, Any], config: dict[str, Any]) -> None:
    """Sweet Spot Evaluation Mechanism — §62c r34. SD=True: no executor credits.
    Computes maturity level, capability completeness, value density, milestone status.
    Writes SweetSpotAssessment and ValueDensityRecord to state.
    """
    envelope = config.get("capability_envelope")
    if not envelope:
        return

    declared_caps: list[dict] = envelope.get("capabilities", [])
    total = len(declared_caps)
    if total == 0:
        return

    cap_states: list[dict] = state.setdefault("capability_states", [])
    state_by_id = {e["capability_id"]: e for e in cap_states if isinstance(e, dict)}

    # Capability completeness — §2600: CAPABLE status without passing TestRunRecord emits WARNING
    _passing_trr_caps: set[str] = set()
    for trr in state.get("test_run_records", []):
        if (isinstance(trr, dict)
                and trr.get("verdict") == "PASS"
                and trr.get("kind") in {"CAPABILITY_GATE", "ACCEPTANCE"}):
            for cid in (trr.get("capability_ids_covered") or []):
                _passing_trr_caps.add(cid)
    capable_count = 0
    for cap in declared_caps:
        cap_id = cap.get("id", "")
        cap_status = state_by_id.get(cap_id, {}).get("status")
        if cap_status in {"CAPABLE", "OVER_ENGINEERED"}:
            capable_count += 1
            if cap_id not in _passing_trr_caps:
                _emit_gap(
                    state,
                    "capability-without-test-coverage",
                    "WARNING",
                    f"Capability '{cap_id}' has status {cap_status} but no passing CAPABILITY_GATE or ACCEPTANCE TestRunRecord covers it (§2600)",
                )
    completeness = capable_count / total

    # Weighted completeness for value density
    weighted = sum(
        cap.get("value_weight", 0.0) * state_by_id.get(cap.get("id", ""), {}).get("completeness_fraction", 0.0)
        for cap in declared_caps
        if isinstance(cap, dict)
    )

    # Product surface measure (line count proxy)
    surface = 0
    root = ROOT.resolve()
    for pf in config.get("product_files", []):
        fpath = root / pf
        if not fpath.resolve().is_relative_to(root):
            _emit_gap(state, "product-surface-unavailable", "WARNING",
                      "Product surface source escapes the Product root; assessment remains unverified")
            return
        try:
            with fpath.open("r", encoding="utf-8", errors="ignore") as handle:
                surface += sum(1 for _ in handle)
        except OSError:
            _emit_gap(state, "product-surface-unavailable", "WARNING",
                      "A configured Product surface source is unreadable; assessment remains unverified")
            return

    value_density = weighted / max(surface, 1)

    completeness_target = float(envelope.get("completeness_target", 1.0))
    ceiling = envelope.get("complexity_ceiling")
    density_floor = envelope.get("value_density_floor")

    # Maturity level
    history = state.get("value_density_history", [])
    best_density = max((r.get("value_density", 0.0) for r in history), default=0.0)

    if completeness < completeness_target:
        maturity = "FORMING"
    elif ceiling is not None and ceiling < surface:
        maturity = "OVER_ENGINEERED"
    elif density_floor is not None and value_density < density_floor:
        maturity = "FORMING"
    else:
        maturity = "OPTIMIZED" if value_density > best_density + 1e-9 else "CAPABLE"

    # Capability gaps and over-engineered caps
    cap_gaps = [
        cap["id"] for cap in declared_caps
        if isinstance(cap, dict)
        and state_by_id.get(cap.get("id", ""), {}).get("status", "ABSENT") not in {"CAPABLE", "OVER_ENGINEERED"}
    ]
    over_eng = [
        cap["id"] for cap in declared_caps
        if isinstance(cap, dict)
        and state_by_id.get(cap.get("id", ""), {}).get("status") == "OVER_ENGINEERED"
    ]

    # Active milestone check
    milestones: list[dict] = envelope.get("milestones", [])
    active_milestone = next((m for m in milestones if isinstance(m, dict) and m.get("status") == "ACTIVE"), None)
    milestone_status_out = None
    milestone_id_out = None
    if active_milestone:
        milestone_id_out = active_milestone.get("id")
        gates_ok = all(
            state_by_id.get(gid, {}).get("status") in {"CAPABLE", "OVER_ENGINEERED"}
            for gid in active_milestone.get("capability_gates", [])
        )
        qgates_ok = True
        for qg in active_milestone.get("quality_gates", []):
            scope = qg.get("scope", "*")
            min_streak = qg.get("min_streak", 0)
            qs_entry = state.get("quality_state", {}).get(scope, {})
            if qs_entry.get("current_streak", 0) < min_streak:
                qgates_ok = False
                break
        milestone_ceiling = active_milestone.get("complexity_ceiling")
        if milestone_ceiling is None:
            milestone_ceiling = ceiling
        milestone_density_floor = active_milestone.get("value_density_floor")
        if milestone_density_floor is None:
            milestone_density_floor = density_floor
        ceiling_ok = milestone_ceiling is None or surface <= milestone_ceiling
        density_ok = milestone_density_floor is None or value_density >= milestone_density_floor
        if gates_ok and qgates_ok and ceiling_ok and density_ok:
            active_milestone["status"] = "ACHIEVED"
            active_milestone["achieved_at"] = now()
            milestone_status_out = "ACHIEVED"
            _ach_at = now()
            state.setdefault("evidence", []).append({
                "id": identifier("evi"),
                "kind": "milestone-achieved",
                "at": _ach_at,
                "milestone_id": milestone_id_out,
                "version": active_milestone.get("version", ""),
                "detail": f"ProductMilestone {milestone_id_out} achieved: "
                          f"version={active_milestone.get('version', 'unversioned')} all gates passed",
            })
            # r35: create ProductVersion record
            _next_mid = active_milestone.get("next_milestone_id")
            pver = {
                "id": identifier("pver"),
                "version": active_milestone.get("version", "v0"),
                "milestone_id": milestone_id_out,
                "achieved_at": _ach_at,
                "maturity_level": maturity,
                "capability_completeness": round(completeness, 6),
                "value_density": round(value_density, 8),
                "product_surface_measure": surface,
                "next_milestone_id": _next_mid,
            }
            state.setdefault("product_versions", []).append(pver)
            # r35: chain-activate next milestone
            if _next_mid:
                for ms in milestones:
                    if isinstance(ms, dict) and ms.get("id") == _next_mid:
                        if ms.get("status") == "PENDING":
                            ms["status"] = "ACTIVE"
                            state.setdefault("evidence", []).append({
                                "id": identifier("evi"),
                                "kind": "milestone-activated",
                                "at": _ach_at,
                                "milestone_id": _next_mid,
                                "triggered_by": milestone_id_out,
                                "detail": f"Next milestone {_next_mid} activated by {milestone_id_out} achievement",
                            })
                        break
        else:
            milestone_status_out = "PENDING"

    assessed_at = now()
    ssa = {
        "id": identifier("ssa"),
        "assessed_at": assessed_at,
        "maturity_level": maturity,
        "capability_completeness": round(completeness, 6),
        "value_density": round(value_density, 8),
        "product_surface_measure": surface,
        "active_milestone_id": milestone_id_out,
        "milestone_status": milestone_status_out,
        "capability_gaps": cap_gaps if cap_gaps else None,
        "over_engineered_caps": over_eng if over_eng else None,
    }
    state.setdefault("sweet_spot_assessments", []).append(ssa)

    prev_records = state.get("value_density_history", [])
    prev_density = prev_records[-1]["value_density"] if prev_records else None
    delta = round(value_density - prev_density, 8) if prev_density is not None else None
    trend = None
    if delta is not None:
        trend = "IMPROVING" if delta > 1e-9 else ("DECLINING" if delta < -1e-9 else "NEUTRAL")

    vdr = {
        "id": identifier("vdr"),
        "recorded_at": assessed_at,
        "value_density": round(value_density, 8),
        "surface_measure": surface,
        "delta": delta,
        "trend": trend,
        "assessment_id": ssa["id"],
    }
    state.setdefault("value_density_history", []).append(vdr)

    if maturity == "OVER_ENGINEERED":
        _emit_gap(state, "over-engineered", "WARNING",
                  f"Product surface {surface} exceeds complexity_ceiling {ceiling} at CAPABLE maturity")


def _capability_envelope_gate_passes(state: dict[str, Any], config: dict[str, Any], post_change_surface: int, operation: dict[str, Any]) -> bool:
    """Capability Envelope Gate (§62c r34): blocks surface growth beyond ceiling when CAPABLE/OPTIMIZED.
    Returns True (gate passes) or False (gate blocks).
    """
    envelope = config.get("capability_envelope")
    if not envelope:
        return True
    ceiling = envelope.get("complexity_ceiling")
    if ceiling is None:
        return True
    assessments = state.get("sweet_spot_assessments", [])
    if not assessments:
        return True
    latest = assessments[-1]
    if latest.get("maturity_level") not in {"CAPABLE", "OPTIMIZED"}:
        return True
    if post_change_surface <= ceiling:
        return True
    # Check for authorized expansion DecisionRecord
    op_created = operation.get("created_at", "")
    scope = operation.get("scope", "*")
    for rec in state.get("decision_records", []):
        if rec.get("kind") != "CAPABILITY_SCOPE_EXPANSION":
            continue
        if rec.get("decided_at", "") >= op_created and scope in str(rec.get("subject", "")):
            return True
    return False


def _derive_capabilities_from_patterns(
    adopted_pattern_ids: list[str],
    existing_cap_ids: set[str],
) -> list[dict]:
    """r35: Derive draft CapabilityStatements from AP pattern provides clauses.
    Returns draft records (status=ABSENT) for provides-clause items not already declared.
    """
    try:
        catalog = pattern_catalog_module.PATTERN_CATALOG
    except Exception:
        return []
    drafts: list[dict] = []
    seen_names: set[str] = set()
    for pid in adopted_pattern_ids:
        entry = catalog.get(pid)
        if not entry:
            continue
        provides_raw = entry.get("provides", "")
        # provides may be a list or a comma-delimited string
        if isinstance(provides_raw, list):
            provides_items = provides_raw
        else:
            provides_items = [s.strip() for s in str(provides_raw).split(",")]
        for item in provides_items:
            name = item.strip()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            # Check if already declared by name similarity (simple substring match)
            already = any(name.lower()[:12] in cid.lower() for cid in existing_cap_ids)
            if not already:
                # Generate a cap- id from the name
                slug = "".join(c if c.isalnum() else "" for c in name.lower())[:8].ljust(8, "0")
                cap_id = f"cap-{slug[:10]}"
                if cap_id not in existing_cap_ids:
                    drafts.append({
                        "id": cap_id,
                        "name": name,
                        "description": f"Derived from {pid} provides clause: {name}",
                        "scope": "*",
                        "tier": entry.get("tier", "FOUNDATIONAL"),
                        "value_weight": 0.1,
                        "_draft": True,
                        "_source_pattern": pid,
                    })
    return drafts


def _derive_milestone_from_state(state: dict, config: dict) -> "dict | None":
    """r36: Draft a ProductMilestone from capability states — targets ABSENT/PARTIAL caps."""
    envelope = config.get("capability_envelope", {})
    declared_caps = envelope.get("capabilities", [])
    if not declared_caps:
        return None
    cap_states = {c.get("id"): c.get("status", "ABSENT") for c in state.get("capability_states", [])}
    gates = []
    for cap in declared_caps:
        cap_id = cap.get("id", "")
        status = cap_states.get(cap_id, "ABSENT")
        if status in ("ABSENT", "PARTIAL"):
            gates.append(cap_id)
    if not gates:
        return None
    return {
        "id": identifier("mst"),
        "name": "Derived milestone — capability completion target",
        "description": f"Auto-drafted from {len(gates)} incomplete capabilities",
        "version": "v-draft",
        "capability_gates": gates,
        "status": "PENDING",
        "_draft": True,
    }


def _refresh_derived_refs(
    state: dict,
    refs_key: str,
    id_field: str,
    adopted_field: str,
    build_fn,
    new_ids_fn,
    delta_key: str,
    drv_kind: str,
    drv_adopted_key: str,
    artifact_result_key: str,
    new_ref_builder,
    state_update_fn,
    error_id_field: str,
    empty_msg: str,
    not_found_msg_fn,
    id_filter: "str | None",
    show_delta: bool,
) -> "list[dict]":
    """Generic refresh loop shared by construct-set and pattern-manifest refresh."""
    refs = list(state.get(refs_key, []))
    if not refs:
        return [{"status":"not_found","detail":not_found_msg_fn(id_filter)}] if id_filter else [{"status": "no_saved_refs", "detail": empty_msg}]
    if id_filter:
        refs = [r for r in refs if r.get(id_field) == id_filter]
        if not refs:
            return [{"status": "not_found", "detail": not_found_msg_fn(id_filter)}]
    results = []
    spec_ver = _current_spec_version()
    for ref in refs:
        old_ids = ref.get(adopted_field, [])
        old_spec = ref.get("spec_version", "")
        intent = ref.get("intent", "refreshed derive")
        try:
            new_artifact = build_fn(old_ids, intent, spec_ver)
        except Exception as e:
            results.append({error_id_field: ref.get(id_field), "status": "error", "detail": str(e)})
            continue
        new_ids = new_ids_fn(new_artifact)
        delta: dict = {}
        if show_delta:
            added = [x for x in new_ids if x not in old_ids]
            removed = [x for x in old_ids if x not in new_ids]
            delta = {f"added_{delta_key}": added, f"removed_{delta_key}": removed,
                     "spec_version_was": old_spec, "spec_version_now": spec_ver}
        new_ref = new_ref_builder(ref, new_artifact, new_ids, spec_ver, intent)
        state_update_fn(state, ref, new_ref)
        state.setdefault("derivation_records", []).append({
            "id": identifier("drv"), "kind": drv_kind,
            id_field: new_ref[id_field],
            drv_adopted_key: new_ids,
            "spec_version": spec_ver,
            "derived_at": new_ref["generated_at"],
            "delta_summary": f"refreshed from spec {old_spec} -> {spec_ver}; {delta_key}: {len(old_ids)} -> {len(new_ids)}",
        })
        results.append({
            f"old_{id_field}": ref.get(id_field),
            f"new_{id_field}": new_ref[id_field],
            artifact_result_key: new_artifact,
            "status": "refreshed", "spec_was": old_spec, "spec_now": spec_ver, "delta": delta,
        })
    return results


def _refresh_derived_construct_sets(
    state: dict,
    config: dict,
    construct_set_id_filter: "str | None",
    show_delta: bool,
) -> "list[dict]":
    """r45: Re-derive saved ConstructSetRefs with latest spec."""
    def _build(old_ids, intent, spec_ver):
        return pattern_catalog_module.build_derived_construct_set(
            construct_ids=old_ids, intent=intent, spec_version=spec_ver)
    def _new_ids(cset):
        return [r["construct_id"] for r in cset.get("adopted_constructs", [])]
    def _new_ref(ref, cset, new_ids, spec_ver, intent):
        from .derived_artifacts import seal
        return seal({
            "id": ref.get("id") or identifier("csr"),
            "construct_set_id": cset["construct_set_id"],
            "spec_version": spec_ver, "generated_at": cset["generated_at"],
            "adopted_construct_ids": new_ids, "kinds_present": cset.get("kinds_present", []),
            "intent": intent,
            "construct_digests": pattern_catalog_module.construct_digests_for_ids(new_ids),
        },cset,config)
    def _update(state, ref, new_ref):
        state["construct_set_refs"] = [
            r for r in state.get("construct_set_refs", [])
            if r.get("construct_set_id") != ref.get("construct_set_id")
        ] + [new_ref]
    return _refresh_derived_refs(
        state, "construct_set_refs", "construct_set_id", "adopted_construct_ids",
        _build, _new_ids, "constructs", "CONSTRUCT_SET_REFRESH",
        "construct_ids", "new_construct_set",
        _new_ref, _update,
        "construct_set_id",
        "No saved ConstructSetRefs. Run `urace derive --kind ... --save` first.",
        lambda f: f"No saved ref with construct_set_id={f}",
        construct_set_id_filter, show_delta,
    )


def _refresh_derived_manifests(
    state: dict,
    config: dict,
    manifest_id_filter: "str | None",
    show_delta: bool,
) -> "list[dict]":
    """r36: Re-derive saved DerivedManifestRefs with latest spec. Returns result summaries."""
    # merge derivation_refs + legacy derived_manifest_refs, deduplicated
    refs = state.get("derivation_refs", [])
    legacy = state.get("derived_manifest_refs", [])
    merged = refs + [r for r in legacy if not any(x.get("manifest_id") == r.get("manifest_id") for x in refs)]
    # temporarily write merged into state key for the generic loop
    original = state.get("derivation_refs", [])
    state["derivation_refs"] = merged
    def _build(old_pids, intent, spec_ver):
        return pattern_catalog_module.build_derived_manifest(
            pattern_ids=old_pids, intent=intent, spec_version=spec_ver)
    def _new_ids(manifest):
        return [r["pattern_id"] for r in manifest.get("adopted_patterns", []) if isinstance(r, dict)]
    def _new_ref(ref, manifest, new_pids, spec_ver, intent):
        from .derived_artifacts import seal
        return seal({
            "id": ref.get("id") or identifier("dmr"),
            "manifest_id": manifest["manifest_id"],
            "spec_version": spec_ver, "generated_at": manifest["generated_at"],
            "adopted_pattern_ids": new_pids, "intent": intent,
            "pattern_digests": pattern_catalog_module.pattern_digests_for_ids(new_pids),
        },manifest,config)
    def _update(state, ref, new_ref):
        state["derivation_refs"] = [
            r for r in state.get("derivation_refs", [])
            if r.get("manifest_id") != ref.get("manifest_id")
        ] + [new_ref]
        state["derived_manifest_refs"] = [
            r for r in state.get("derived_manifest_refs", [])
            if r.get("manifest_id") != ref.get("manifest_id")
        ]
    return _refresh_derived_refs(
        state, "derivation_refs", "manifest_id", "adopted_pattern_ids",
        _build, _new_ids, "patterns", "REFRESH",
        "pattern_ids", "new_manifest",
        _new_ref, _update,
        "manifest_id",
        "No saved DerivedManifestRefs found. Run `urace derive --constructs ... --save` first.",
        lambda f: f"No saved ref with manifest_id={f}",
        manifest_id_filter, show_delta,
    )


def _print_derive_update_suggestions(updates: dict) -> None:
    """Print human-readable derive-update suggestions produced by _suggest_derive_updates."""
    for item in updates.get("updated_constructs", []):
        cids = ", ".join(item["updated_construct_ids"])
        print(f"  construct update available: [{cids}] changed in your saved set {item['construct_set_id']!r} — run `urace derive --refresh` to adopt updates")
    for item in updates.get("updated_patterns", []):
        pids = ", ".join(item["updated_pattern_ids"])
        print(f"  pattern update available: [{pids}] changed in your saved manifest {item['manifest_id']!r} — run `urace derive --refresh` to adopt updates")
    for item in updates.get("new_construct_suggestions", []):
        ids = ", ".join(s["construct_id"] for s in item["suggestions"])
        print(f"  new construct match for '{item['intent']}': {ids} — run `urace derive '{item['intent']}' --kind {','.join(item['kinds'])} --suggest` to preview")
    for item in updates.get("new_pattern_suggestions", []):
        ids = ", ".join(s["pattern_id"] for s in item["suggestions"])
        print(f"  new pattern match for '{item['intent']}': {ids} — run `urace derive '{item['intent']}' --suggest` to preview")


def _suggest_derive_updates(state: dict) -> dict:
    """r46: Return new-construct/pattern suggestions and update-detected entries for all saved sets."""
    # Construct sets — new suggestions
    cset_refs = state.get("construct_set_refs", [])
    new_construct_suggestions = pattern_catalog_module.suggest_new_constructs_for_saved_sets(cset_refs, top_n=3)

    # Construct sets — update detection (digest diff)
    updated_constructs: list[dict] = []
    for ref in cset_refs:
        saved_digests = ref.get("construct_digests", {})
        adopted_ids = ref.get("adopted_construct_ids", [])
        if saved_digests and adopted_ids:
            changed = pattern_catalog_module.diff_construct_digests(saved_digests, adopted_ids)
            if changed:
                updated_constructs.append({
                    "construct_set_id": ref["construct_set_id"],
                    "intent": ref.get("intent", ""),
                    "updated_construct_ids": changed,
                })

    # Pattern manifests — new suggestions
    all_manifest_refs = list(state.get("derivation_refs", [])) + [
        r for r in state.get("derived_manifest_refs", [])
        if not any(x.get("manifest_id") == r.get("manifest_id") for x in state.get("derivation_refs", []))
    ]
    new_pattern_suggestions = pattern_catalog_module.suggest_new_patterns_for_saved_manifests(all_manifest_refs, top_n=3)

    # Pattern manifests — update detection
    updated_patterns: list[dict] = []
    seen_mids: set[str] = set()
    for ref in all_manifest_refs:
        mid = ref.get("manifest_id", "")
        if mid in seen_mids:
            continue
        seen_mids.add(mid)
        saved_pdigests = ref.get("pattern_digests", {})
        adopted_pids = ref.get("adopted_pattern_ids", [])
        if saved_pdigests and adopted_pids:
            changed_p = pattern_catalog_module.diff_pattern_digests(saved_pdigests, adopted_pids)
            if changed_p:
                updated_patterns.append({
                    "manifest_id": mid,
                    "intent": ref.get("intent", ""),
                    "updated_pattern_ids": changed_p,
                })

    return {
        "new_construct_suggestions": new_construct_suggestions,
        "updated_constructs": updated_constructs,
        "new_pattern_suggestions": new_pattern_suggestions,
        "updated_patterns": updated_patterns,
    }


