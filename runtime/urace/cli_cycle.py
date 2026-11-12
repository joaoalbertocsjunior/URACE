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

from .cli_emit import _emit_gap, _emit_trace, _emit_compliance_record
from .cli_state import record_executor_failure, record_blocker, product_digest
from .cli_lifecycle import (
    defer_executor_capacity, discover, discover_with_executor,
    _evaluate_wake_conditions, execute_with_executor, observe_progress,
    plan_for, refresh_executor_availability, refresh_scope_priorities,
    _run_onboard_gate, run_spec_audit, spec_audit_due, _verify_wake_registrations,
)
from .cli_helpers import (
    _compact_with_chunking, _evaluate_sweet_spot, _executor_independent_work,
    _observe_retention_gaps, _reconcile_unresolved_effects,
    _validate_authority_basis_binding, _validate_citizen_base_conformance,
    _validate_immutable_fields, _apply_customizations, _check_staleness,
    _check_scheduled_tasks, _record_quality_delta, _regression_checkpoint_gate_passes,
    _build_inspection_surface, _refresh_derived_manifests, _refresh_derived_refs,
    _refresh_derived_construct_sets, _suggest_derive_updates, _derive_milestone_from_state,
    _capability_envelope_gate_passes, _apply_effect_uncertainty_protocol,
    _apply_operator_gate,
)

def _csi_relevance_score(state: dict[str, Any], content: str) -> float:
    """Heuristic relevance: token overlap between signal content and active intent+objectives."""
    content_tokens = set(content.lower().split())
    reference_text = " ".join(filter(None, [
        str(state.get("intent", "")),
        " ".join(o.get("title", "") for o in state.get("objectives", []) if o.get("status") in {"planned", "active"}),
    ]))
    reference_tokens = set(reference_text.lower().split())
    if not reference_tokens or not content_tokens:
        return 0.0
    overlap = len(content_tokens & reference_tokens)
    return min(1.0, round(overlap / max(len(reference_tokens), 1), 4))


def _csi_confidence_score(state: dict[str, Any], source_ref: str | None, feed_id: str) -> float:
    """Bounded confidence accumulator: increment per corroborating signal from distinct feeds."""
    if not source_ref:
        return 0.0
    delta = 0.15
    existing = [
        s for s in state.get("community_signals", [])
        if s.get("source_ref") == source_ref and s.get("feed_id") != feed_id
    ]
    return min(1.0, round(len(existing) * delta, 4))


def _signal_quality(relevance: float, confidence: float) -> str:
    """Compute SignalQuality from relevance and confidence scores."""
    if relevance < 0.40:
        return "FILTERED"
    if relevance >= 0.75 and confidence >= 0.75:
        return "HIGH"
    if confidence >= 0.60:
        return "MEDIUM"
    return "LOW"


def _run_csi(config: dict[str, Any], state: dict[str, Any]) -> None:
    """§5509-5535 Community Signal Ingestion Mechanism (CSI).
    Feeds are configured in Config.community_inbox.feeds (default []); an empty feed list
    means CSI is off. State.community_feeds mirrors registered feeds for state inspection.
    Skipped unless lifecycle_state ∈ {ACTIVE, ASSESSING, DORMANT-wake} (§5525).
    """
    if state.get("lifecycle_state") not in {"ACTIVE", "ASSESSING"}:
        return
    # Feed config lives in Config.community_inbox.feeds — not in state (§5513)
    csi_config = config.get("community_inbox", {})
    feeds = csi_config.get("feeds", [])
    if not feeds:
        return
    # Mirror configured feeds into state.community_feeds for inspection (§4233)
    state_feed_ids = {f.get("id") for f in state.get("community_feeds", []) if isinstance(f, dict)}
    for feed in feeds:
        if isinstance(feed, dict) and feed.get("id") not in state_feed_ids:
            state.setdefault("community_feeds", []).append(feed)

    relevance_floor = float(csi_config.get("relevance_floor", 0.40))
    existing_refs: set[str] = {
        s.get("source_ref") for s in state.get("community_signals", []) if s.get("source_ref")
    }
    # Re-score previously filtered signals if objectives changed
    current_obj_ids = {o.get("id") for o in state.get("objectives", [])}
    for sig in state.get("community_signals", []):
        if sig.get("filtered") and sig.get("signal_quality") == "FILTERED":
            new_rel = _csi_relevance_score(state, sig.get("content", ""))
            if new_rel >= relevance_floor:
                sig["relevance_score"] = new_rel
                sig["filtered"] = False
                sig["signal_quality"] = _signal_quality(new_rel, sig.get("confidence_score", 0.0))
                sig["updated_at"] = now()

    for feed in feeds:
        if not isinstance(feed, dict) or not feed.get("active", True):
            continue
        feed_id = feed.get("id", "unknown")
        if not feed.get("terms_accepted"):
            if not any(
                g.get("kind") == "community-feed-terms-not-accepted" and g.get("detail", "").endswith(feed_id)
                for g in state.get("integrity_gaps", [])
            ):
                _emit_gap(
                    state, "community-feed-terms-not-accepted", "WARNING",
                    f"CommunityFeed {feed_id} has terms_accepted=false; ingestion disabled until accepted — {feed_id}",
                )
            continue

        # Adapter dispatch: only RSS and POLLING are auto-fetchable; WEBHOOK/PUSH arrive via input queue
        adapter_kind = feed.get("kind", "POLLING")
        if adapter_kind in {"WEBHOOK", "PUSH"}:
            # Signals from WEBHOOK/PUSH feeds arrive via the normal input pipeline — skip here
            continue

        # Attempt to fetch — real adapter would make HTTP call; here we model the contract
        timeout = int(feed.get("adapter_timeout_seconds", 30))
        retry_count = int(feed.get("adapter_retry_count", 3))
        feed_failures = feed.get("_adapter_failures", 0)

        if feed_failures >= retry_count:
            if not any(
                g.get("kind") == "community-feed-adapter-unavailable" and feed_id in g.get("detail", "")
                for g in state.get("integrity_gaps", [])
            ):
                _emit_gap(
                    state, "community-feed-adapter-unavailable", "WARNING",
                    f"CommunityFeed {feed_id} adapter exhausted {retry_count} retries; feed suspended",
                )
            continue

        # Model: inject signals from feed.pending_items if present (used by tests)
        pending_items = feed.get("_pending_items", [])
        for item in pending_items:
            source_ref = item.get("source_ref")
            if source_ref and source_ref in existing_refs:
                continue  # deduplicate
            content = item.get("content", "")
            relevance = _csi_relevance_score(state, content)
            confidence = _csi_confidence_score(state, source_ref, feed_id)
            quality = _signal_quality(relevance, confidence)
            filtered = relevance < relevance_floor
            sig: dict[str, Any] = {
                "id": identifier("csig"),
                "created_at": now(),
                "updated_at": now(),
                "feed_id": feed_id,
                "content": content,
                "source_ref": source_ref,
                "received_at": now(),
                "relevance_score": relevance,
                "confidence_score": confidence,
                "signal_quality": quality,
                "filtered": filtered,
                "filter_reason": f"relevance_score {relevance} < relevance_floor {relevance_floor}" if filtered else None,
            }
            state.setdefault("community_signals", []).append(sig)
            if source_ref:
                existing_refs.add(source_ref)
        # Clear processed items
        feed.pop("_pending_items", None)


def _run_ppm(config: dict[str, Any], state: dict[str, Any]) -> None:
    """§5543-5564 Patch Proposal Pipeline Mechanism (PPP_M).
    Synthesizes PatchProposals from HIGH/MEDIUM signals, routes by ApprovalMode,
    enforces max_queue_depth and proposal_expiry_hours.
    """
    policy = state.get("self_evolution_policy", {})
    if policy.get("mode", "NECESSARY_ONLY").upper() == "DISABLED":
        if not any(g.get("kind") == "patch-pipeline-disabled" for g in state.get("integrity_gaps", [])):
            _emit_gap(
                state, "patch-pipeline-disabled", "BLOCKING",
                "self_evolution_policy.mode=DISABLED; PPP_M halted until mode is changed",
            )
        return

    # All PPP_M settings live under Config.community_inbox (§4157)
    ppm_config = config.get("community_inbox", config.get("patch_proposal_pipeline", {}))
    max_queue_depth = int(ppm_config.get("max_queue_depth", 50))
    expiry_hours = float(ppm_config.get("proposal_expiry_hours", 168.0))
    approval_mode = ppm_config.get("approval_mode", "SMART").upper()
    confidence_threshold = float(ppm_config.get("confidence_threshold", 0.60))

    current_ts = datetime.now(timezone.utc).timestamp()
    proposals: list[dict] = state.setdefault("patch_proposals", [])

    # Enforce expiry: PENDING proposals past expiry_hours → EXPIRED
    for prop in proposals:
        if prop.get("status") == "PENDING":
            try:
                created_ts = datetime.fromisoformat(prop["created_at"]).timestamp()
                if (current_ts - created_ts) / 3600.0 >= expiry_hours:
                    prop["status"] = "EXPIRED"
                    prop["resolved_at"] = now()
            except (KeyError, ValueError):
                pass

    # Enforce max_queue_depth via 3-step eviction (§5558)
    pending_proposals = [p for p in proposals if p.get("status") == "PENDING"]
    if len(pending_proposals) >= max_queue_depth:
        # Step 1: evict CONFIDENCE_INSUFFICIENT
        for p in proposals:
            if p.get("status") == "CONFIDENCE_INSUFFICIENT" and len(pending_proposals) >= max_queue_depth:
                p["status"] = "EXPIRED"
                p["resolved_at"] = now()
                pending_proposals = [p2 for p2 in proposals if p2.get("status") == "PENDING"]
        # Step 2: evict oldest PENDING
        if len(pending_proposals) >= max_queue_depth:
            pending_by_age = sorted(pending_proposals, key=lambda p: p.get("created_at", ""))
            for p in pending_by_age[:max(0, len(pending_proposals) - max_queue_depth + 1)]:
                p["status"] = "EXPIRED"
                p["resolved_at"] = now()

    # Collect already-processed signal IDs
    processed_signal_ids: set[str] = {p.get("signal_id") for p in proposals if p.get("signal_id")}

    # Create proposals for unprocessed HIGH/MEDIUM signals
    for sig in state.get("community_signals", []):
        if sig.get("filtered") or sig.get("signal_quality") == "FILTERED":
            continue
        if sig.get("signal_quality") not in {"HIGH", "MEDIUM", "LOW"}:
            continue
        sig_id = sig.get("id")
        if sig_id in processed_signal_ids:
            continue
        # Check queue depth before adding
        live_pending = sum(1 for p in proposals if p.get("status") == "PENDING")
        if live_pending >= max_queue_depth:
            break

        confidence = sig.get("confidence_score", 0.0)
        if confidence < confidence_threshold:
            status = "CONFIDENCE_INSUFFICIENT"
        else:
            status = "PENDING"

        prop: dict[str, Any] = {
            "id": identifier("pprop"),
            "created_at": now(),
            "updated_at": now(),
            "signal_id": sig_id,
            "proposed_diff": f"[Executor-synthesized patch for signal: {sig.get('content', '')[:120]}]",
            "target": config.get("product_name", "URACE"),
            "rationale": f"Signal quality {sig.get('signal_quality')} with relevance={sig.get('relevance_score')}, confidence={confidence}",
            "status": status,
            "approval_mode": approval_mode,
            "confidence_score": confidence,
            "resolved_at": None,
            "resolved_by": None,
            "rejection_reason": None,
        }
        proposals.append(prop)
        processed_signal_ids.add(sig_id)

    # Approval routing for PENDING proposals
    for prop in proposals:
        if prop.get("status") != "PENDING":
            continue
        confidence = prop.get("confidence_score", 0.0)
        quality = next(
            (s.get("signal_quality") for s in state.get("community_signals", []) if s.get("id") == prop.get("signal_id")),
            "LOW",
        )
        if approval_mode == "AUTO":
            if confidence >= 0.80:
                prop["status"] = "AUTO_APPROVED"
                prop["resolved_at"] = now()
                prop["resolved_by"] = "auto"
            # else: falls through to SMART evaluation
        if approval_mode in {"AUTO", "SMART"} and prop.get("status") == "PENDING":
            # AUTO proposals that didn't auto-approve, or SMART mode
            if quality in {"LOW", "FILTERED"}:
                prop["status"] = "REJECTED"
                prop["resolved_at"] = now()
                prop["rejection_reason"] = f"SMART mode: autonomously rejected {quality} quality signal"
            # HIGH/MEDIUM remain PENDING for operator confirmation in SMART mode
        # HUMAN mode: all remain PENDING until inbox apply


def _run_feedback_accumulator(config: dict[str, Any], state: dict[str, Any]) -> None:
    """Process unprocessed OutcomeFeedbackRecords (§62c FAC / §62u)."""
    lifecycle = state.get("lifecycle_state", "")
    if lifecycle not in {"ACTIVE", "ASSESSING"}:
        return

    feedback_records = state.setdefault("outcome_feedback_records", [])
    for rec in feedback_records:
        if rec.get("processed"):
            continue
        signal = rec.get("signal", "NEUTRAL")  # noqa: F811 — local loop var, shadows stdlib import
        target_kind = rec.get("target_kind", "")
        target_id = rec.get("target_id", "")
        if signal == "NEGATIVE":
            if target_kind == "OBJECTIVE":
                _emit_gap(state, "feedback-negative-objective", "INFO",
                          f"NEGATIVE feedback for Objective {target_id}")
            elif target_kind == "DECISION":
                _emit_gap(state, "feedback-negative-decision", "INFO",
                          f"NEGATIVE feedback for DecisionRecord {target_id}")
        rec["processed"] = True

    # Check feedback-overdue
    window_hours = config.get("feedback", {}).get("window_hours", 168)
    window_seconds = window_hours * 3600
    objectives = state.get("objectives", [])
    feedback_target_ids = {r.get("target_id") for r in feedback_records}
    now_ts = now()
    for obj in objectives:
        if obj.get("status") not in {"ACCEPTED", "completed", "awaiting_outcome"}:
            continue
        obj_id = obj.get("id", "")
        if obj_id in feedback_target_ids:
            continue
        accepted_at = obj.get("accepted_at") or obj.get("completed_at") or obj.get("updated_at") or obj.get("created_at")
        if not accepted_at:
            continue
        try:
            accepted_dt = datetime.fromisoformat(accepted_at.replace("Z", "+00:00"))
            now_dt = datetime.fromisoformat(now_ts.replace("Z", "+00:00"))
            elapsed = (now_dt - accepted_dt).total_seconds()
        except Exception:
            continue
        if elapsed >= window_seconds:
            if not any(g.get("kind") == "feedback-overdue" and obj_id in g.get("detail", "")
                       and not g.get("resolved") for g in state.get("integrity_gaps", [])):
                _emit_gap(state, "feedback-overdue", "INFO",
                          f"Objective {obj_id} accepted >{window_hours}h ago with no feedback; "
                          f"run `urace feedback submit {obj_id} --signal <POSITIVE|NEGATIVE|NEUTRAL>`")


def _run_ram(config: dict[str, Any], state: dict[str, Any]) -> None:
    """Account for each period once; distinguish estimated cost from verified return."""
    if state.get("lifecycle_state") not in {"ACTIVE", "ASSESSING"}:
        return
    budget = config.get("product_budget")
    if not budget:
        return
    current = datetime.now(timezone.utc)
    period_hours = {"DAILY": 24, "WEEKLY": 168, "MONTHLY": 720}.get(
        budget.get("period", "MONTHLY"), float(budget.get("period_hours", 720)))
    if period_hours <= 0:
        raise ValueError("product budget period must be positive")
    start = state.setdefault("resource_period_start", state.get("created_at", current.isoformat()))
    ledger = state.setdefault("resource_ledger", [])
    snapshots = state.setdefault("roi_snapshots", [])
    if (current - datetime.fromisoformat(start)).total_seconds() >= period_hours * 3600:
        prior = next((entry for entry in reversed(ledger) if entry["period_start"] == start), None)
        if prior:
            snapshots.append({**prior, "id": identifier("rsnp"), "period_end": current.isoformat(),
                              "computed_roi": prior.get("roi"), "below_floor": prior.get("roi") is not None and prior["roi"] < float(budget.get("roi_floor", 0))})
        start = current.isoformat()
        state["resource_period_start"] = start
    start_time = datetime.fromisoformat(start)
    def in_period(item: dict[str, Any], field: str) -> bool:
        raw = item.get(field)
        return not raw or start_time <= datetime.fromisoformat(raw) <= current
    calls = [c for c in state.get("executor_state", {}).get("executor_calls", []) if in_period(c, "at")]
    operations = [o for o in state.get("operations", []) if in_period(o, "attempted_at")]
    def measured_cost(call: dict[str, Any]) -> float | None:
        raw = call.get("usage", {}).get("reported_cost_usd")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw) and raw >= 0:
            return float(raw)
        return None
    costs = [measured_cost(c) for c in calls]
    estimated_cost = float(budget.get("cost_per_executor_call", 0.01))
    call_cost = sum(c if c is not None else estimated_cost for c in costs)
    elapsed = sum(max(0.0, float(c.get("elapsed_seconds", 0))) for c in calls)
    # Older operations may predate per-call timing. Avoid counting either twice.
    timed_calls = {c.get("id") for c in calls if "elapsed_seconds" in c}
    elapsed += sum(max(0.0, float(o.get("elapsed_seconds", 0))) for o in operations
                   if isinstance(o.get("executor"), dict)
                   and o.get("executor", {}).get("logical_reservation") not in timed_calls)
    hours = elapsed / 3600
    verified = [o for o in operations if o.get("outcome", {}).get("real_user_value_verified")]
    trial_cost = sum(max(0.0, o["outcome"]["observed_cost"] - float(o.get("usage", {}).get("reported_cost_usd", 0))) for o in verified)
    total_cost = call_cost + hours * float(budget.get("hourly_rate", 0)) + trial_cost
    values = {f"{obs.get('source', 'unknown')}.{name}": float(value)
              for obs in state.get("external_metric_state", {}).get("latest", [])
              for name, value in obs.get("values", {}).items()
              if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)}
    baseline = state.setdefault("resource_metric_baseline", dict(values))
    directions = budget.get("metric_directions", {})
    changes = [(value - baseline[name]) * (1 if directions[name] == "nondecreasing" else -1)
               for name, value in values.items() if name in baseline
               and directions.get(name) in {"nondecreasing", "nonincreasing"}]
    delta_metrics = sum(changes) if changes else None
    all_costs_observed = bool(calls) and all(c is not None for c in costs)
    if float(budget.get("hourly_rate", 0)):
        all_costs_observed = all_costs_observed and all("elapsed_seconds" in c for c in calls)
    gross = sum(o["outcome"]["net_benefit"] + o["outcome"]["observed_cost"] for o in verified)
    roi = (gross - total_cost) / total_cost if verified and all_costs_observed and total_cost > 0 else None
    entry = {"id": identifier("resc"), "recorded_at": current.isoformat(), "period_start": start,
        "executor_calls": len(calls), "time_hours": hours, "total_cost": total_cost,
        "cost_basis": "observed" if all_costs_observed else "estimated_or_incomplete",
        "external_values": values, "delta_metrics": delta_metrics,
        "metric_attribution": "UNATTRIBUTED_OBSERVATION", "delta_quality": 0.0,
        "delta_capability": 0.0, "roi": roi, "roi_basis": "verified_real_user_outcomes" if roi is not None else "UNVERIFIED"}
    ledger.append(entry)
    exceeded = []
    for key, actual in (("max_cost", total_cost), ("max_time_hours", hours), ("max_executor_calls", len(calls))):
        if budget.get(key) is not None and actual > float(budget[key]):
            exceeded.append(f"{key}: {actual:g} > {budget[key]}")
    if exceeded and not any(g.get("kind") == "product-budget-exceeded" and not g.get("resolved") for g in state.get("integrity_gaps", [])):
        _emit_gap(state, "product-budget-exceeded", "BLOCKING", "; ".join(exceeded))
        if state.get("lifecycle_state") not in ("BLOCKED", "PAUSED"):
            state["lifecycle_state"] = "BLOCKED"
            _emit_trace(state, "TRANSITION", "lifecycle → BLOCKED (product-budget-exceeded)")
    if roi is not None and roi < float(budget.get("roi_floor", 0)):
        if not any(g.get("kind") == "product-roi-below-floor" and not g.get("resolved") for g in state.get("integrity_gaps", [])):
            _emit_gap(state, "product-roi-below-floor", "BLOCKING", "Verified real-user ROI is below the configured floor")
            if state.get("lifecycle_state") not in ("BLOCKED", "PAUSED"):
                state["lifecycle_state"] = "BLOCKED"
                _emit_trace(state, "TRANSITION", "lifecycle → BLOCKED (product-roi-below-floor)")


def _try_p2p_feature(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    """P2P-first gate: return a planned objective sourced from the peer network when the
    recommendation score clears the ROI threshold AND authority/intent are respected.

    The recommendation threshold adapts to resource pressure so P2P candidates
    may be considered earlier when executor-call capacity or exchange credits
    are constrained. This is a routing heuristic, not evidence that P2P is cheaper:
        adjusted_threshold = BASE × (1 − 0.5 × budget_pressure)

    Returns a 'planned' objective dict or None.  Never raises.
    """
    try:
        if not config.get("p2p", {}).get("feature_borrow_enabled", True):
            return None
        from . import peer_exchange as _pe
        exchange_root = state_path(config).parent / "exchange"
        if not exchange_root.exists():
            return None
        exchange = _pe.Exchange(exchange_root)
        policy = exchange.load()
        if not policy.get("enabled"):
            return None

        from . import product_similarity as _ps
        candidates = _ps.score_features(config, state, exchange, timeout_seconds=2.0)
        if not candidates:
            return None

        # --- Enrichment 1: Credit-based budget pressure (combined with call-count pressure) ---
        from . import credit_ledger as _cl
        _exec_state = state.get("executor_state", {})
        _calls_24h = [c for c in _exec_state.get("executor_calls", [])
                      if _ts_age(c.get("at", now())) < 86400]
        _limit = nullable_limit(config.get("executor", {}), "max_executor_calls_per_24h", 2)
        call_pressure = min(1.0, len(_calls_24h) / _limit) if _limit else 0.0
        _local_id = config.get("peer_id", "local")
        _bal = _cl.balance(state_path(config).parent, _local_id)
        _baseline = _cl.BASELINE_GRANT_UNITS
        credit_pressure = max(0.0, min(1.0, 1.0 - _bal / max(1, _baseline * 10)))
        budget_pressure = max(call_pressure, credit_pressure)

        BASE_THRESHOLD = float(config.get("p2p", {}).get("p2p_roi_threshold", 0.55))
        adjusted = BASE_THRESHOLD * (1.0 - 0.5 * budget_pressure)

        # --- Enrichment 5: Cold-start confidence gate (select best then gate) ---
        best = candidates[0]
        if best.get("score", 0.0) < adjusted:
            return None

        if best.get("cold_start") and budget_pressure < 0.8:
            _non_cold = [c for c in candidates if not c.get("cold_start") and c.get("score", 0) >= adjusted]
            if not _non_cold:
                return None
            best = _non_cold[0]

        feature_id = best["feature_id"]

        # --- Enrichment 3: Intent affinity floor ---
        _intent_floor = max(0.15, 0.30 * (1.0 - budget_pressure))
        if best.get("intent_similarity", 0.0) < _intent_floor:
            return None

        # --- Enrichment 4: Credit affordability gate ---
        _borrow_cost = _cl.feature_borrow_cost_units()
        if _cl.balance(state_path(config).parent, _local_id) < _borrow_cost:
            return None

        _ts = now()
        obj = {
            "id": identifier("objective"),
            "title": f"Apply peer-sourced feature: {feature_id}",
            "reason": (
                f"P2P recommendation score {best['score']:.3f} ≥ threshold {adjusted:.3f} "
                f"(budget_pressure={budget_pressure:.0%}, peers={best['peer_count']}, "
                f"confidence={best['confidence']})"
            ),
            "success_measure": f"Feature {feature_id!r} applied and qualifies locally",
            "scope": "runtime",
            "status": "planned",
            "created_at": _ts, "updated_at": _ts,
            "expected_value": best["score"],
            # Ranking requires a 0..1 heuristic. Keep neutral and label the
            # economic comparison unavailable; do not encode P2P as near-free.
            "estimated_cost": 0.5,
            "estimated_cost_basis": "UNVERIFIED_NEUTRAL_P2P_ROUTING_VALUE",
            "risk": 0.1,
            "urgency": 0.4,
            "source": "p2p_recommendation",
            "p2p_feature_id": feature_id,
            "p2p_score": best["score"],
            "input_links": ["p2p-recommendation"],
            "necessity_evidence": best.get("rationale", ""),
            "lower_impact_route_sufficient": True,
        }
        # Authority check: p2p feature objectives require delegated runtime authority
        _validate_authority_basis_binding(state, obj)
        state["objectives"].append(obj)
        state.setdefault("evidence", []).append({
            "id": identifier("evidence"), "at": _ts,
            "kind": "p2p-feature-candidate",
            "feature_id": feature_id,
            "score": best["score"],
            "adjusted_threshold": adjusted,
            "budget_pressure": {
                "combined": budget_pressure,
                "call_pressure": call_pressure,
                "credit_pressure": credit_pressure,
            },
        })
        return obj
    except Exception:
        return None


def _ts_age(ts_iso: str) -> float:
    """Seconds since an ISO timestamp."""
    try:
        return datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(ts_iso).timestamp()
    except Exception:
        return float("inf")


def _routing_decision(config: dict[str, Any], state: dict[str, Any]) -> dict:
    """Compute executor vs. network-hire routing score.

    Returns peer_work_market.routing_score() result or a default executor dict.
    Never raises — safe to call at any cycle point.
    """
    try:
        from . import peer_exchange as _pe
        from . import credit_ledger as _cl
        from . import peer_work_market as _pwm

        exchange_root = state_path(config).parent / "exchange"
        if not exchange_root.exists():
            return {'route': 'executor', 'confidence': 0.5, 'reason': 'no exchange dir'}
        exchange = _pe.Exchange(exchange_root)
        if not exchange.load().get("enabled"):
            return {'route': 'executor', 'confidence': 0.5, 'reason': 'exchange disabled'}

        _local_id = config.get("peer_id", "local")
        balance = _cl.balance(state_path(config).parent, _local_id)
        baseline = _cl.BASELINE_GRANT_UNITS
        executor_cost = int(config.get("executor", {}).get("cost_per_call_units", _cl.UNIT))

        # Derive spec complexity from current planned objective if available
        _planned = [o for o in state.get("objectives", []) if o.get("status") == "planned"]
        complexity = 0.4
        if _planned:
            _obj = _planned[0]
            _loc_est = int(_obj.get("estimated_loc", 0))
            complexity = min(1.0, 0.3 + _loc_est / 500.0) if _loc_est else 0.4

        # Gather peers with combined_rep from exchange audit rows
        peers = []
        try:
            for row in exchange.audit_rows():
                if row.get('kind') == 'PEER_ANNOUNCE' and row.get('peer_id'):
                    peers.append({
                        'peer_id': row['peer_id'],
                        'combined_rep': float(row.get('combined_rep', 0.0)),
                    })
        except Exception:
            pass

        return _pwm.routing_score(
            exchange=exchange,
            local_credit_balance=balance,
            baseline_grant_units=baseline,
            spec_complexity=complexity,
            executor_cost_units=executor_cost,
            available_peers=peers,
        )
    except Exception:
        return {'route': 'executor', 'confidence': 0.5, 'reason': 'routing_score error'}


def cycle(config: dict[str, Any], state: dict[str, Any], allow_execution: bool = True) -> dict[str, Any]:
    global _loaded_state_snapshot
    # --- r75: generate cycle_id for ObservabilityContract trace records ---
    _cycle_id = identifier("cycle-")
    # --- §62z: reset continuation confidence at cycle boundary ---
    continuation_module.reset_confidence(state)
    # --- r54: citizen-base conformance check on load ---
    _validate_citizen_base_conformance(state)
    # --- r75: emit CYCLE trace at cycle entry ---
    _emit_trace(state, "CYCLE", "cycle started", cycle_id=_cycle_id)
    if config.get("product_improvement_enabled") is False:
        state["lifecycle_state"]="WAITING_FOR_CONDITION"
        save_state(config,state);return {"outcome":"disabled_product","reason":"Owner disabled improvement for this product; no native call"}
    # --- OnboardGate: block autonomous cycles until operator confirms (§62o) ---
    _onboard_result = _run_onboard_gate(config, state)
    if _onboard_result is not None:
        save_state(config, state)
        return _onboard_result
    data_transport.auto_sync(state,config,state_path(config).parent)
    # --- r54: capture immutable-field snapshot for pre-save mutation detection ---
    import copy as _copy
    _loaded_state_snapshot = _copy.deepcopy({
        k: state.get(k, [])
        for k in ["goal_records", "intent_records", "constraint_records",
                  "decision_records", "evidence", "operations"]
    })
    # --- r54: authority_basis binding validation for all objectives ---
    for _obj in state.get("objectives", []):
        if isinstance(_obj, dict):
            _validate_authority_basis_binding(state, _obj)

    # --- Spec structural audit (§81): run when spec version changed ---
    if spec_audit_due(state):
        run_spec_audit(config, state)
        # Validate any stored lexical formulas
        lexical_formulas = state.get("lexical_formulas", [])
        for lf in lexical_formulas:
            try:
                from urace import primitives as _prim
                _prim.validate_lexical_formula(lf)
            except Exception as _e:
                _logger.warning("lexical_formula validation: %s", _e)

    # --- Compaction startup check: verify manifest integrity ---
    _compaction_gaps = compaction_module.verify_manifest_on_startup(str(state_path(config).parent))
    if _compaction_gaps:
        state.setdefault("integrity_gaps", []).extend(_compaction_gaps)

    # --- Wake registration liveness verification (§5501/§5505) ---
    _wake_gaps = _verify_wake_registrations(config, state)
    for _wg in _wake_gaps:
        _logger.warning("wake registration: %s", _wg)

    # --- CRC: generate or reload cognitive resume context at cycle boundary ---
    if config.get("_resume_session"):
        _crc = cognitive_resume_module.load_or_generate(str(state_path(config).parent), state)
    else:
        _crc = cognitive_resume_module.generate(state)
    state["cognitive_resume_context"] = _crc

    # --- Reconcile any indeterminate effects before assessing new work ---
    if state.get("unresolved_effects"):
        state["unresolved_effects"] = _reconcile_unresolved_effects(ROOT, state)
    if state["unresolved_effects"]:
        state["lifecycle_state"] = "BLOCKED"
        _emit_trace(state, "TRANSITION", "lifecycle → BLOCKED (unresolved effects)", cycle_id=_cycle_id)
        return {"outcome": "blocked", "reason": f"{len(state['unresolved_effects'])} unresolved external effects require reconciliation; file-hash and journal-phase reconciliation attempted"}

    # --- Destination anchor integrity check ---
    anchor_status = destination_anchor.check_anchor_integrity(state, config)
    if anchor_status["status"] == "not_established":
        state["destination_anchor"] = anchor_status["anchor"]
    elif anchor_status["status"] == "changed":
        state["lifecycle_state"] = "BLOCKED"
        _emit_gap(state, "governance-anchor-drift", "BLOCKING",
            "destination anchor drift detected — cycle blocked pending re-anchoring",
            prior_digest=anchor_status.get("prior_digest"),
            current_digest=anchor_status.get("current_digest"),
        )
        _emit_trace(state, "TRANSITION", "lifecycle → BLOCKED (governance-anchor-drift)", cycle_id=_cycle_id)
        save_state(config, state)
        return {"outcome": "blocked", "reason": "destination anchor drift detected — governance-anchor-drift BLOCKING gap emitted"}

    # --- Evaluate due wake conditions ---
    due_wake = _evaluate_wake_conditions(state)
    for condition in due_wake:
        state.setdefault("triggers", []).append({
            "id": identifier("trigger"), "at": now(),
            "kind": "SCHEDULED_WAKE",
            "condition": condition,
            "disposition": "REASSESS",
            "provenance": "wake_registry",
        })
    if due_wake:
        state.setdefault("executor_state", {})["discovery_trigger"] = {
            "reason": "scheduled wake condition elapsed",
            "signature": f"wake:{len(due_wake)}",
        }
        # R6 — Wake trigger atomic write: persist state immediately after recording wake conditions
        save_state(config, state)

    # --- Community Signal Ingestion + Patch Proposal Pipeline (§5509-5564) ---
    # Activated only when Config.community_inbox.feeds is non-empty (default [])
    if config.get("community_inbox", {}).get("feeds"):
        _run_csi(config, state)
        _run_ppm(config, state)
    outcome_verification.refresh(ROOT, config, state)
    _run_feedback_accumulator(config, state)
    _run_ram(config, state)

    # §2571 Capability Envelope Gate — BLOCKING enforcement
    _cap_breach_gaps = [
        g for g in state.get("integrity_gaps", [])
        if g.get("kind") == "capability-envelope-breach"
        and not g.get("resolved")
    ]
    if _cap_breach_gaps:
        state["lifecycle_state"] = "BLOCKED"
        save_state(config, state)
        return {
            "outcome": "blocked",
            "reason": (
                f"{len(_cap_breach_gaps)} unresolved capability-envelope-breach gap(s); "
                "resolve via DecisionRecord(kind=AUTHORITY_GRANT) to authorize capability expansion"
            ),
        }

    state["lifecycle_state"] = "ASSESSING"
    _emit_trace(state, "TRANSITION", "lifecycle → ASSESSING (cycle entry)", cycle_id=_cycle_id)
    availability = refresh_executor_availability(config, state)
    metric_settings = dict(config.get("external_metrics", {"mode": "DISABLED"}))
    configured_sources = list(metric_settings.get("sources", []))
    sources_by_id = {item["id"]: item for item in configured_sources}
    for item in state.get("connector_sources", []):
        if item.get("status") == "ACTIVE":
            sources_by_id[item["id"]] = item
        else:
            sources_by_id.pop(item.get("id"), None)
    metric_settings["sources"] = list(sources_by_id.values())
    prior_external = state.get("external_metric_state", {})
    last_collection = prior_external.get("last_collection")
    next_collection = prior_external.get("next_collection_at")
    collection_due = not next_collection or datetime.now(timezone.utc).timestamp() >= datetime.fromisoformat(next_collection).timestamp()
    if collection_due:
        runtime = state.setdefault("runtime_efficiency", {})
        runtime["external_collections"] = int(runtime.get("external_collections", 0)) + 1
    if collection_due:
        try:
            external = external_metrics.collect(ROOT, metric_settings, prior_external.get("last_known_good"))
        except Exception as collection_error:
            external = {"at": now(), "mode": metric_settings.get("mode", "DISABLED"), "observations": [], "errors": [{"source": "collection", "error": str(collection_error)}], "last_known_good": prior_external.get("last_known_good", {})}
    else:
        external = {"at": last_collection, "mode": metric_settings.get("mode", "DISABLED"), "observations": prior_external.get("latest", []), "errors": prior_external.get("errors", []), "cached": True}
    external_state = state.setdefault("external_metric_state", {"mode": external["mode"], "last_collection": None, "latest": [], "errors": []})
    previous_events = {
        (event.get("kind"), event.get("id")): event.get("updated_at")
        for observation in prior_external.get("latest", []) for event in observation.get("events", [])
    }
    changed_events = [
        event for observation in external["observations"] for event in observation.get("events", [])
        if previous_events.get((event.get("kind"), event.get("id"))) != event.get("updated_at")
    ] if not external.get("cached") and previous_events else []
    decision_links = [
        {"operation": operation["id"], "attribution_status": "UNATTRIBUTED", "reason": "temporal proximity alone is not causal evidence"}
        for operation in state.get("operations", []) if operation.get("status") == "ACCEPTED"
    ][-10:]
    metric_policy = config.get("external_metrics", {})
    if not external.get("cached"):
        failed_only = bool(external["errors"]) and not external["observations"]
        failure_streak = int(prior_external.get("failure_streak", 0)) + 1 if failed_only else 0
        base_interval = float(metric_settings.get("collection_interval_seconds", 300))
        max_interval = float(metric_settings.get("max_collection_interval_seconds", 21600))
        next_interval = min(max_interval, base_interval * (2 ** min(failure_streak, 10)))
        next_collection_at = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + next_interval, timezone.utc).isoformat()
    else:
        failure_streak = int(prior_external.get("failure_streak", 0))
        next_collection_at = prior_external.get("next_collection_at")
    external_state.update({
        "mode": external["mode"],
        "source": metric_policy.get("source", "bootstrap default"),
        "provenance": metric_policy.get("provenance", "no attributable selection supplied"),
        "last_collection": external["at"], "latest": external["observations"],
        "errors": external["errors"], "candidate_decision_links": decision_links,
        "failure_streak": failure_streak, "next_collection_at": next_collection_at,
        "last_known_good": external.get("last_known_good", prior_external.get("last_known_good", {})),
    })
    from . import value_discovery
    try:state['value_discovery']=value_discovery.refresh(config,state)
    except (OSError,ValueError,RuntimeError,KeyError) as error:state['value_discovery']={'status':'EVIDENCE_UNAVAILABLE','reason':type(error).__name__+': '+str(error)[:300]}
    from . import decision_feedback
    try:state['decision_feedback_status']=decision_feedback.refresh(config,state)
    except (OSError,ValueError,TypeError,KeyError) as error:state['decision_feedback_status']={'status':'EVIDENCE_UNAVAILABLE','reason':type(error).__name__+': '+str(error)[:300],'additional_model_calls':0}
    from . import milestone_suggestions
    try:state['milestone_suggestions_status']=milestone_suggestions.refresh(config,state)
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as error:state['milestone_suggestions_status']={'status':'EVIDENCE_UNAVAILABLE','reason':type(error).__name__+': '+str(error)[:300],'additional_model_calls':0}
    # Advance connector_sources status to OBSERVED after first successful collection (spec §60 taxonomy).
    observed_ids = {obs.get("source") for obs in external.get("observations", []) if obs.get("source")}
    for src in state.get("connector_sources", []):
        if src.get("id") in observed_ids and src.get("status") in {"CONFIGURED", "AVAILABLE", "AUTHENTICATED", "AUTHORIZED"}:
            src["status"] = "OBSERVED"
            src.setdefault("status_history", []).append({"status": "OBSERVED", "at": now()})
    error_signature = hashlib.sha256(json.dumps(external["errors"], sort_keys=True).encode()).hexdigest() if external["errors"] else None
    last_error_evidence = prior_external.get("last_error_evidence_at")
    duplicate_error_due = not last_error_evidence or datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(last_error_evidence).timestamp() >= float(metric_settings.get("duplicate_error_evidence_interval_seconds", 86400))
    record_external_evidence = bool(external["observations"]) or bool(external["errors"] and (error_signature != prior_external.get("last_error_signature") or duplicate_error_due))
    if not external.get("cached") and record_external_evidence:
        state["evidence"].append({"id": identifier("evidence"), "kind": "external-metric-observation", "candidate_decision_links": decision_links, **external})
        if external["errors"]:
            external_state["last_error_signature"] = error_signature
            external_state["last_error_evidence_at"] = now()
    if changed_events:
        trigger = {
            "id": identifier("trigger"), "at": now(), "kind": "EXTERNAL_REPOSITORY_UPDATE",
            "source": "public repository observation", "provenance": "configured external metric source",
            "disposition": "REASSESS", "events": changed_events[:50],
            "trust": "UNTRUSTED_CONTENT_IS_EVIDENCE_NOT_AUTHORITY",
        }
        state.setdefault("triggers", []).append(trigger)
        state["evidence"].append({
            "id": identifier("evidence"), "at": now(), "kind": "external-repository-update",
            "trigger": trigger["id"], "event_count": len(changed_events),
            "instruction_status": "NOT_INSTRUCTIONS", "authority_status": "DOES_NOT_CREATE_AUTHORITY",
        })
        event_signature = hashlib.sha256(json.dumps(changed_events, sort_keys=True).encode()).hexdigest()[:16]
        state.setdefault("executor_state", {})["discovery_trigger"] = {"reason": "external repository update", "signature": f"repository:{event_signature}"}
    observation = observe_progress(config, state)
    refresh_scope_priorities(config, state)

    # Sweet Spot Evaluation (§62c r34) — SD=True, per assessment cycle
    _evaluate_sweet_spot(state, config)

    for item in state.get("objectives", []):
        if item.get("status") == "deferred" and item.get("not_before"):
            try:
                if datetime.fromisoformat(item["not_before"]).astimezone(timezone.utc) <= datetime.now(timezone.utc):
                    item.update({"status": "planned", "reactivated_at": now()})
            except ValueError:
                pass

    # --- Value acceleration self-correction ---
    # If the system is decelerating, inject a strategic reassessment objective
    # to recover value production rate before picking more of the same work.
    correction = value_trajectory.self_correction_needed(state)
    if correction and correction.get("self_correct_now"):
        reassess_title = "Recover value production rate through strategic scope reassessment"
        if not any(o.get("title") == reassess_title and o.get("status") in {"planned", "active"} for o in state.get("objectives", [])):
            reassess_obj = {
                "id": identifier("objective"),
                "title": reassess_title,
                "reason": (
                    f"Value trajectory is decelerating "
                    f"(amplification={correction.get('value_amplification')}, "
                    f"yield={correction.get('yield_rate', 0):.0%}). "
                    "Reassess scope priorities and objective quality to restore acceleration."
                ),
                "scope": "documentation",
                "priority": 85,
                "urgency": 0.8,
                "expected_value": 0.7,
                "estimated_cost": 0.3,
                "risk": 0.2,
                "status": "planned",
                "created_at": now(),
                "source": "value_trajectory_self_correction",
            }
            state["objectives"].append(reassess_obj)
            state.setdefault("evidence", []).append({
                "id": identifier("evidence"), "at": now(),
                "kind": "value-deceleration-self-correction",
                "correction": correction,
                "objective_injected": reassess_obj["id"],
            })

    # Derive a project objective through the existing authority/planning pipeline.
    if allow_execution:
        auto_goals.select(config, state)
    candidates = [item for item in state.get("objectives", []) if item.get("status") in {"planned", "policy_blocked"}]
    for candidate in candidates:
        if candidate.get("scope") in {"runtime", "rebootstrap"}:
            candidate["status"] = "planned" if objective_is_eligible(state, candidate) else "policy_blocked"
    # R5 — Self-evolution budget guard: self-evolution Objectives MUST NOT consume >20% of executor_calls budget
    _exec_calls = state.get("executor_state", {}).get("executor_calls", [])
    _current_ts = datetime.now(timezone.utc).timestamp()
    _calls_24h = [c for c in _exec_calls if _current_ts - datetime.fromisoformat(c["at"]).timestamp() < 86400]
    _max_24h = nullable_limit(config.get("executor",{}),"max_executor_calls_per_24h",2)
    _remaining_budget = max(0,_max_24h-len(_calls_24h)) if _max_24h is not None else len(candidates)
    _self_evo_budget_ceiling = max(1, int(_remaining_budget * 0.20))
    _self_evo_calls_24h = [c for c in _calls_24h if c.get("stage") == "execution"]  # rough proxy
    def _is_self_evolution_objective(obj: dict) -> bool:
        return (
            "self-evolution" in obj.get("tags", [])
            or obj.get("kind") == "self-evolution"
            or obj.get("source") == "self-evolution"
            or obj.get("scope") in {"runtime", "rebootstrap"}
        )
    _self_evo_scheduled_count = sum(1 for c in candidates if _is_self_evolution_objective(c) and c.get("status") == "planned")
    if _self_evo_scheduled_count > _self_evo_budget_ceiling:
        import logging as _logging
        _logging.getLogger("urace.cycle").debug(
            "self-evolution budget guard: %d self-evolution candidates exceed 20%% ceiling (%d); deferring excess",
            _self_evo_scheduled_count, _self_evo_budget_ceiling,
        )
        # Demote excess self-evolution candidates beyond the ceiling
        _evo_seen = 0
        for _cand in sorted(candidates, key=objective_score, reverse=True):
            if _is_self_evolution_objective(_cand) and _cand.get("status") == "planned":
                _evo_seen += 1
                if _evo_seen > _self_evo_budget_ceiling:
                    _cand["status"] = "deferred"
                    _cand["defer_reason"] = "self-evolution budget guard: 20% ceiling"
    ranked = [item for item in sorted(candidates, key=objective_score, reverse=True) if item.get("status") == "planned" and goal_is_schedulable(state, item)]
    from .implementation_sequence import plan as implementation_plan,local_only
    sequencing=implementation_plan(state.get("objectives",[]),scores={t["id"]:objective_score(t) for t in state.get("objectives",[])},eligible={t["id"]:goal_is_schedulable(state,t) for t in state.get("objectives",[])})
    order={key:i for i,key in enumerate(sequencing["dispatch_order"])}
    ranked.sort(key=lambda t:order.get(t["id"],len(order)))
    state["implementation_sequence"]=sequencing
    comparison = [{"id": item.get("id"), "title": item.get("title"), "scope": item.get("scope"), "score": objective_score(item), "score_breakdown": objective_score_breakdown(item)} for item in ranked[:5]]
    objective = ranked[0] if ranked else None
    if objective is None:
        objective = discover(config, state, observation)
    if objective is None:
        # Routing: P2P-feature → network-hire → executor.
        # 1. Check pre-existing P2P features (no new work needed).
        # 2. Routing score decides: if network-hire is favoured, record evidence and
        #    skip executor — hiring is done via peer_work_market (async, out-of-band).
        # 3. Fall through to executor when neither gate fires.
        _p2p_candidate = _try_p2p_feature(config, state)
        if _p2p_candidate:
            objective = _p2p_candidate
        else:
            _routing = _routing_decision(config, state)
            if _routing.get('route') == 'network_hire' and _routing.get('network_hire_viable'):
                # Record routing decision; actual work-request creation is caller's
                # responsibility via peer_work_market.create_work_request().
                state.setdefault("evidence", []).append({
                    "id": identifier("evidence"),
                    "at": now(),
                    "kind": "network-hire-preferred",
                    "route": _routing['route'],
                    "confidence": _routing['confidence'],
                    "reason": _routing['reason'],
                    "avg_peer_rep": _routing.get('avg_peer_rep', 0.0),
                    "executor_cost_factor": _routing.get('executor_cost_factor'),
                    "credit_pressure": _routing.get('credit_pressure', 0.0),
                })
                # Do not invoke executor — leave objective=None so caller can post a
                # WORK_REQUEST to the exchange at the appropriate scope.
            else:
                try:
                    objective = discover_with_executor(config, state, persist_usage=True)
                    if objective:
                        refresh_scope_priorities(config, state)
                except intelligent_executor.ExecutorUnavailable as error:
                    defer_executor_capacity(config, state, error, "discovery")
                    state["lifecycle_state"] = "WAITING_FOR_CAPACITY"
                except RuntimeError as error:
                    record_executor_failure(state, "discovery", str(error))
                    continuation_module.handle_unspecified(
                        state, str(error), context="intelligent discovery", cycle_id=_cycle_id)

    # --- Executor-independent work (spec §55) ---
    # When no Executor is available, URACE MUST NOT become fully dormant.
    # Process wake conditions, pending validations, and deterministic work.
    if not availability.get("available") and objective is None:
        independent_done = _executor_independent_work(config, state, observation)
        if independent_done:
            state.setdefault("runtime_efficiency", {})["last_independent_work_at"] = now()

    if objective:
        # --- R4: Authority resolution cache TTL invalidation (3600s) ---
        cached_auth = objective.get("authority_resolution")
        if cached_auth:
            cached_at = cached_auth.get("resolved_at", "")
            if cached_at:
                try:
                    age_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(cached_at)).total_seconds()
                    if age_seconds > 3600:
                        objective.pop("authority_resolution", None)
                except (ValueError, TypeError):
                    pass
        # --- Authority resolution gate (spec §14-16) ---
        if not objective.get("authority_resolution"):
            auth_result = authority_resolver.resolve(objective, config, state)
            objective["authority_resolution"] = auth_result
            authority_resolver.record_resolution(state, objective, auth_result)
            outcome_code = auth_result["outcome"]
            if outcome_code == authority_resolver.DENIED:
                objective["status"] = "policy_blocked"
                objective["authority_resolution"] = auth_result
                state.setdefault("evidence", []).append({
                    "id": identifier("evidence"), "at": now(),
                    "kind": "authority-resolution-denied",
                    "objective": objective.get("id"),
                    "basis": auth_result["basis"],
                    "gate": auth_result["gate"],
                })
                _emit_compliance_record(state, "governance", "DECLINING",
                    objective.get("id"), "authority denial — compliance record", objective.get("scope"))
                objective = None
            elif outcome_code == authority_resolver.REQUIRES_AUTHORITATIVE_DECISION:
                objective["status"] = "awaiting_operator_decision"
                state["lifecycle_state"] = "WAITING_FOR_AUTHORITATIVE_DECISION"
                state.setdefault("evidence", []).append({
                    "id": identifier("evidence"), "at": now(),
                    "kind": "authority-resolution-escalated",
                    "objective": objective.get("id"),
                    "basis": auth_result["basis"],
                    "gate": auth_result["gate"],
                })
                objective = None

    if objective:
        if not any(item["id"] == objective.get("id") for item in comparison):
            comparison.append({"id": objective.get("id"), "title": objective.get("title"), "scope": objective.get("scope"), "score": objective_score(objective), "score_breakdown": objective_score_breakdown(objective)})
        current_plan = state.get("current_plan")
        plan = current_plan if isinstance(current_plan, dict) and current_plan.get("objective_reference") == objective["id"] and current_plan.get("status") == "ready" else plan_for(state, objective)
        try:
            execution = execute_with_executor(config, state, objective, plan, persist_usage=True) if allow_execution and (local_only(objective) or config.get("executor", {}).get("enabled") and availability["available"]) else None
            execution_status = (execution or {}).get("status")
            if execution_status == "PENDING_VALIDATION":
                state["lifecycle_state"] = "WAITING_FOR_CONDITION"
            elif execution_status == "AWAITING_OPERATOR_DECISION":
                state["lifecycle_state"] = "WAITING_FOR_AUTHORITATIVE_DECISION"
            else:
                state["lifecycle_state"] = "ACTIVE"
            outcome = {"outcome": "pending_validation" if execution_status == "PENDING_VALIDATION" else ("executed" if execution else "planned"), "objective": objective, "plan": plan, "execution": execution, "candidate_comparison": comparison}
        except intelligent_executor.ExecutorUnavailable as error:
            defer_executor_capacity(config, state, error, "execution")
            objective["status"] = "planned"
            state["lifecycle_state"] = "WAITING_FOR_CAPACITY"
            outcome = {"outcome": "deferred_executor_capacity", "objective": objective, "retry_at": error.retry_at, "reason": "provider capacity unavailable; task remains planned"}
        except RuntimeError as error:
            if not local_only(objective):record_executor_failure(state, "execution", str(error))
            record_blocker(state, objective["id"], str(error))
            objective["status"] = "blocked"
            continuation_module.handle_unspecified(
                state, str(error), context="execution", cycle_id=_cycle_id)
            state["lifecycle_state"] = "DORMANT"
            outcome = {"outcome": "dormant", "objective": objective, "reason": str(error)}
    else:
        state["current_objective"] = None
        state["current_plan"] = None
        # Resolve the precise no-work lifecycle state per §64.
        _exec_state = state.get("executor_state", {})
        _budget_status = _exec_state.get("discovery_budget_status", "")
        _unschedulable = [item for item in state.get("objectives", []) if item.get("status") == "planned" and not goal_is_schedulable(state, item)]
        _has_capacity_wait = state.get("lifecycle_state") == "WAITING_FOR_CAPACITY"
        if _unschedulable and not _has_capacity_wait:
            # Planned objectives exist but a precondition is not yet met.
            state["lifecycle_state"] = "WAITING_FOR_CONDITION"
            _condition_desc = _unschedulable[0].get("blockers", [{}])[-1].get("reason", "precondition not yet satisfied") if _unschedulable[0].get("blockers") else "precondition not yet satisfied"
            reason = f"waiting for condition: {_condition_desc}"
        elif _budget_status == "LOCAL_CONTROLLER_ONLY":
            state["lifecycle_state"] = "WAITING_FOR_CONDITION"
            reason = "Only local orchestration remains; resolve its handler/condition without executor delegation"
        elif _budget_status not in {"WITHIN_BUDGET", "DISCOVERY_YIELD_EXHAUSTED", "DEFERRED_PROPORTIONALITY", "DAILY_LIMIT_OR_RESERVE_REACHED", "MONTHLY_LIMIT_OR_RESERVE_REACHED", "SYSTEMATIC_FAILURE_COOLDOWN", "WAITING_PROVIDER_CAPACITY", ""} and not _has_capacity_wait:
            # Discovery is deferred by schedule (backoff interval not yet elapsed).
            state["lifecycle_state"] = "WAITING_FOR_SCHEDULE"
            reason = f"waiting for scheduled discovery window; current status={_budget_status}"
        elif not _has_capacity_wait:
            state["lifecycle_state"] = "DORMANT"
            _emit_trace(state, "TRANSITION", "lifecycle → DORMANT (cycle complete)", cycle_id=_cycle_id)
            reason = "no justified authorized action; follow-up remains scheduled"
        else:
            reason = "executor unavailable; capacity or availability retry scheduled"
        outcome = {"outcome": "dormant", "reason": reason}
    # --- Retention violation check (§62f) ---
    _retention_gaps = compaction_module.check_retention_violations(state)
    if _retention_gaps:
        _observe_retention_gaps(state, _retention_gaps)

    # --- r54: objective-lifecycle chunking (A3) ---
    _compaction_cfg = config.get("compaction", {})
    if _compaction_cfg.get("chunking_enabled") and _compaction_cfg.get("chunk_by") == "OBJECTIVE_LIFECYCLE":
        # r55: destination_anchor guard — skip compaction if BLOCKED on anchor drift
        if state.get("lifecycle_state") == "BLOCKED":
            _emit_gap(state, "compaction-blocked-on-anchor-drift", "WARNING",
                "compaction skipped: lifecycle_state=BLOCKED (governance-anchor-drift)")
        else:
            for _fp in ["operations", "evidence", "decision_records"]:
                _recs = state.get(_fp, [])
                if _recs:
                    _policy = {"id": "default", "compaction_mode": "ARCHIVE"}
                    _compact_with_chunking(state, _fp, _recs, _policy)

    # --- Technique applicability gate (§62h) ---
    from urace._common import technique_applicability_gate
    _applied_this_cycle: set = set()
    for _tech in ["T1", "T2", "T3", "T4", "T5", "T6"]:
        _ta_record = technique_applicability_gate(_tech, state, config, applied_this_cycle=_applied_this_cycle)
        if _ta_record["verdict"] == "APPLY":
            _applied_this_cycle.add(_tech)
        state.setdefault("technique_application_log", []).append(_ta_record)
    # Trim log to last 100 records
    state["technique_application_log"] = state["technique_application_log"][-100:]

    # --- r54: immutable field mutation detection before save ---
    _validate_immutable_fields(state, _loaded_state_snapshot)

    # --- r75: emit CYCLE trace at cycle exit ---
    _emit_trace(state, "CYCLE", f"cycle ended: {outcome.get('outcome', 'unknown')}", cycle_id=_cycle_id)
    state["last_cycle"] = {"at": now(), **outcome}
    signature = f"{outcome['outcome']}:{outcome.get('reason') or outcome.get('objective', {}).get('scope', 'general')}"
    patterns = state.setdefault("pattern_memory", {})
    pattern = patterns.setdefault(signature, {"count": 0, "first_seen": now(), "last_seen": None, "recurring": False})
    pattern.update({"count": pattern["count"] + 1, "last_seen": now()})
    pattern["recurring"] = pattern["count"] >= 3
    digest = product_digest(config)
    last_checkpoint = state["checkpoints"][-1] if state["checkpoints"] else None
    if last_checkpoint is None or last_checkpoint.get("digest") != digest:
        state["checkpoints"].append({"id": identifier("checkpoint"), "at": now(), "kind": "assessment", "digest": digest})
    # --- §62z: attach continuation_confidence to outcome ---
    outcome["continuation_confidence"] = state.get("continuation_confidence", 1.0)
    return outcome


def emit_cycle_feedback(state: dict[str, Any], outcome: dict[str, Any], index: int, json_mode: bool, quiet: bool, verbose: bool = False) -> None:
    recovery_manifest = state.get("executor_state", {}).get("recovery_manifest")
    if json_mode:
        print(render_cycle(state, outcome, index, True), flush=True)
        if not quiet:
            print(render_cycle(state, outcome, index, False, verbose), file=sys.stderr, flush=True)
        elif recovery_manifest:
            rm = recovery_manifest
            print(
                f"[recovery-pending] manifest={rm.get('manifest_id')} "
                f"cause={rm.get('emission_cause')} "
                f"progress={rm.get('progress_at_emit')} "
                f"delta={rm.get('goal_delta', 'unknown')}",
                file=sys.stderr, flush=True,
            )
    elif not quiet:
        print(render_cycle(state, outcome, index, False, verbose), flush=True)
    elif recovery_manifest:
        rm = recovery_manifest
        print(
            f"[recovery-pending] manifest={rm.get('manifest_id')} "
            f"cause={rm.get('emission_cause')} "
            f"progress={rm.get('progress_at_emit')} "
            f"delta={rm.get('goal_delta', 'unknown')}",
            flush=True,
        )


def emit_auto_startup(json_mode: bool, quiet: bool) -> None:
    if json_mode or quiet:
        return
    print("Second terminal ready — /auto is running.")
    print("  /command for direct access  |  any text for free-form  |  /help for reference")
