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
from .cli_state import (
    _current_spec_version, product_digest, _product_digest_at,
    validate_product, runtime_files,
)
from .cli_helpers import _regression_checkpoint_gate_passes



def _update_progress_vector(state: dict, stagnation_threshold: int = 5) -> None:
    """r23: Update progress_vector and stagnation counter. Trigger REPAIRING on stagnation."""
    objectives = state.get("objectives", [])
    total = len(objectives)
    if total == 0:
        return
    completed = sum(1 for o in objectives if o.get("status") == "completed")
    new_pv = round(completed / total, 4)
    es = state["executor_state"]
    old_pv = es.get("progress_vector")
    if old_pv is not None and new_pv <= old_pv:
        es["progress_stagnant_cycles"] = es.get("progress_stagnant_cycles", 0) + 1
    else:
        es["progress_stagnant_cycles"] = 0
    es["progress_vector"] = new_pv
    stagnant = es.get("progress_stagnant_cycles", 0)
    if stagnant >= stagnation_threshold and state.get("lifecycle_state") == "ACTIVE":
        state["lifecycle_state"] = "REPAIRING"
        _emit_gap(state, "progress-stagnation", "BLOCKING",
                  f"progress_vector stagnant for {stagnant} consecutive cycles "
                  f"(threshold {stagnation_threshold}); last value: {old_pv}")
        es["progress_stagnant_cycles"] = 0


def _emit_recovery_manifest(state: dict, emission_cause: str, execution_mode: str) -> dict:
    """r23: Emit RecoveryManifest to executor_state.recovery_manifest."""
    es = state["executor_state"]
    failures = es.get("failures", [])
    objectives = state.get("objectives", [])
    incomplete = [o.get("title", o["id"]) for o in objectives if o.get("status") != "completed"]
    checkpoints = state.get("checkpoints", [])
    last_checkpoint = checkpoints[-1]["id"] if checkpoints else None
    manifest = {
        "manifest_id": identifier("manifest"),
        "emitted_at": now(),
        "emission_cause": emission_cause,
        "last_safe_state": state.get("lifecycle_state", "DORMANT"),
        "last_safe_commit": last_checkpoint,
        "failure_summary": [f"{f['stage']}:{f['error']}" for f in failures[-5:]],
        "goal_delta": "; ".join(incomplete) if incomplete else "no incomplete objectives",
        "progress_at_emit": es.get("progress_vector"),
        "budget_consumed": es.get("execution_budget"),
        "recommended_tier": None,
        "execution_mode": execution_mode,
    }
    es["recovery_manifest"] = manifest
    return manifest


def observe_progress(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    values = document_metrics(config)
    profile = state["progress_profiles"][0]
    results = {}
    for name, value in values.items():
        measure = profile["measures"][name]
        prior = measure["current"]
        measure["previous"] = prior
        measure["current"] = value
        results[name] = {
            "value": value,
            "vs_baseline": compare(measure["direction"], value, measure["baseline"]),
            "vs_previous": compare(measure["direction"], value, prior),
            "target_met": value >= measure["target"] if measure["direction"] == "nondecreasing" else value <= measure["target"],
        }
    observation = {"id": identifier("observation"), "at": now(), "profile": profile["id"], "results": results}
    prior_observation = state["progress_observations"][-1] if state["progress_observations"] else None
    changed = prior_observation is None or any(
        result["value"] != prior_observation["results"].get(name, {}).get("value")
        for name, result in results.items()
    )
    interval = float(config.get("efficiency", {}).get("unchanged_observation_interval_seconds", 86400))
    due = prior_observation is None or datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(prior_observation["at"]).timestamp() >= interval
    if changed or due:
        state["progress_observations"].append(observation)
    if state.get("lifecycle_state") == "ACTIVE":
        profile["next_follow_up"] = "next autonomous cycle or product change"
    return observation


def discover(config: dict[str, Any], state: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any] | None:
    regressions = [name for name, result in observation.get("results", {}).items() if result.get("vs_previous") == "regressed"]
    unresolved = observation.get("results", {}).get("unresolved_markers", {}).get("value", [])
    if regressions:
        title, reason, priority = "Repair measurable blueprint regression", f"Regressed measures: {', '.join(regressions)}", 100
    elif unresolved:
        title, reason, priority = "Resolve explicit blueprint uncertainty", f"{int(unresolved)} unresolved markers remain", 80
    else:
        return None
    existing = next((item for item in state["objectives"] if item["title"] == title and item["status"] in {"planned", "active"}), None)
    if existing:
        return existing
    if observation.get("id") and not any(item.get("id")==observation["id"] for item in state.get("progress_observations",[])):
        state.setdefault("progress_observations",[]).append(copy.deepcopy(observation))
    _ts = now(); objective = {
        "id": identifier("objective"), "title": title, "reason": reason, "priority": priority,
        "metadata": {"bottleneck_observation_ref": observation.get("id")},
        "status": "planned", "created_at": _ts, "updated_at": _ts,
        "success_measure": "metric regression resolved or unresolved_markers reduced to zero",
        "scope": "documentation", "target": "product",
        "authority_basis": "delegated objectives",
        "expected_value": 0.7, "estimated_cost": 0.3, "risk": 0.2, "urgency": 0.8,
        "necessity_evidence": reason, "lower_impact_route_sufficient": False,
        "dependencies": [], "pinned": False,
    }
    state["objectives"].append(objective)
    return objective


def plan_for(state: dict[str, Any], objective: dict[str, Any]) -> dict[str, Any]:
    plan = {
        "id": identifier("plan"),
        "objective_reference": objective["id"],
        "steps": ["inspect relevant evidence", "prepare bounded local change", "run validation", "measure follow-up"],
        "validation_strategy": "run behavioral tests and compare progress guardrails",
        "next_review_condition": "after execution or new evidence",
        "status": "ready",
        "created_at": now(), "updated_at": now(), "completed_at": None,
    }
    state["current_objective"] = objective["id"]
    state["current_plan"] = plan
    state.setdefault("decision_records", []).append({
        "id": identifier("decision"), "at": now(), "kind": "plan",
        "outcome": plan["id"], "authority_basis": "delegated plans",
        "justification": objective["reason"], "objective_ref": objective["id"],
    })
    return plan


def refresh_scope_priorities(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    system = scope_priority.derive(ROOT, config, state)
    dependent_counts = {item.get("id"): 0 for item in state.get("objectives", [])}
    for item in state.get("objectives", []):
        for dependency in item.get("dependencies", []):
            if dependency in dependent_counts: dependent_counts[dependency] += 1
    for objective in state.get("objectives", []):
        if not objective.get("priority_scope"):
            objective["priority_scope"] = scope_priority.infer_scope(config, objective.get("scope", "documentation"))
        objective["scope_attention_adjustment"] = scope_priority.ranking_adjustment(objective, system)
        objective["scope_priority_version"] = system["version"]
        objective["dependency_unblocking_adjustment"] = min(10.0, 2.0 * dependent_counts.get(objective.get("id"), 0))
    state["scope_priority_system"] = system
    from . import planning_feedback as _pf
    _pf.apply(state)
    return system


def material_state_signature(state: dict[str, Any]) -> str:
    """Exclude high-frequency timestamps while retaining consequential changes."""
    executor = state.get("executor_state", {})
    external = state.get("external_metric_state", {})
    material = {
        "lifecycle": state.get("lifecycle_state"), "current_objective": state.get("current_objective"),
        "current_plan": state.get("current_plan"), "objectives": state.get("objectives", []),
        "operations": state.get("operations", []), "evidence_count": len(state.get("evidence", [])),
        "trigger_count": len(state.get("triggers", [])), "decision_count": len(state.get("decision_records", [])),
        "checkpoint_count": len(state.get("checkpoints", [])), "blocker_count": len(state.get("blockers", [])),
        "unresolved_effects": state.get("unresolved_effects", []), "processed_inputs": state.get("processed_input_ids", []),
        "progress": state.get("progress_profiles", []), "metric_system": state.get("metric_system", {}), "evaluation_system": state.get("evaluation_system", {}),
        "executor": {"available": executor.get("available"), "availability_failure_streak": executor.get("availability_failure_streak"), "calls": executor.get("executor_calls", []), "failures": executor.get("failures", []), "trigger": executor.get("discovery_trigger"), "unproductive_streak": executor.get("unproductive_discovery_streak")},
        "external": {"latest": external.get("latest", []), "errors": external.get("errors", []), "failure_streak": external.get("failure_streak"), "next_collection_at": external.get("next_collection_at")},
        "restart_requested": state.get("restart_requested"), "pending_runtime_activation": state.get("pending_runtime_activation"),
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode()).hexdigest()


def executor_discovery_due(config: dict[str, Any], state: dict[str, Any]) -> bool:
    settings = config.get("executor", {})
    if not settings.get("enabled"):
        return False
    executor_state = state.setdefault("executor_state", {"last_discovery_at": None, "last_operation_at": None, "last_availability_check": None, "available": None, "failures": []})
    current = datetime.now(timezone.utc).timestamp()
    # Priority 1: systematic failure cooldown — always checked first per §62c ordering contract.
    systematic_cooldown = executor_state.get("systematic_failure_cooldown_until")
    if systematic_cooldown and current < datetime.fromisoformat(systematic_cooldown).timestamp():
        executor_state["discovery_budget_status"] = "SYSTEMATIC_FAILURE_COOLDOWN"
        executor_state["discovery_defer_reason"] = "systematic failure cooldown active; executor dispatch suppressed until cooldown expires"
        return False
    calls = executor_state.setdefault("executor_calls", [])
    if not calls and isinstance(executor_state.get("discovery_calls"), list):
        calls.extend({**item, "stage": "discovery", "outcome": "legacy"} for item in executor_state["discovery_calls"])
    calls[:] = [item for item in calls if current - datetime.fromisoformat(item["at"]).timestamp() < 3024000]
    calls_24h = [item for item in calls if current - datetime.fromisoformat(item["at"]).timestamp() < 86400]
    # Priority 2: budget ceilings — reserve one additional call so accepted discovery can
    # be executed without beginning work that the current budget cannot finish.
    if nullable_limit(settings,"max_executor_calls_per_24h",2) is not None and len(calls_24h)+2>nullable_limit(settings,"max_executor_calls_per_24h",2):
        executor_state["discovery_budget_status"] = "DAILY_LIMIT_OR_RESERVE_REACHED"
        executor_state["discovery_defer_reason"] = f"rolling 24h call count {len(calls_24h)} at or beyond ceiling {settings.get('max_executor_calls_per_24h', 2)} (reserve included)"
        return False
    if nullable_limit(settings,"max_executor_calls_per_30d",12) is not None and len(calls)+2>nullable_limit(settings,"max_executor_calls_per_30d",12):
        executor_state["discovery_budget_status"] = "MONTHLY_LIMIT_OR_RESERVE_REACHED"
        executor_state["discovery_defer_reason"] = f"rolling 30d call count {len(calls)} at or beyond ceiling {settings.get('max_executor_calls_per_30d', 12)} (reserve included)"
        return False
    # Priority 3: deferred call retry — evaluated after higher-priority gates so a deferred
    # call cannot bypass systematic cooldown or budget exhaustion.
    if executor_state.get("deferred_discovery_call"):
        retry_at = executor_state.get("capacity_retry_at")
        return not retry_at or current >= datetime.fromisoformat(retry_at).timestamp()
    previous = executor_state.get("last_discovery_at")
    if previous is None:
        return True
    elapsed = current - datetime.fromisoformat(previous).timestamp()
    trigger = executor_state.get("discovery_trigger")
    if trigger:
        signature = trigger.get("signature", trigger.get("reason", "trigger")) if isinstance(trigger, dict) else str(trigger)
        previous_trigger = executor_state.get("last_trigger_call", {})
        if previous_trigger.get("signature") == signature:
            since_same = current - datetime.fromisoformat(previous_trigger["at"]).timestamp()
            if since_same < float(settings.get("trigger_dedupe_seconds", 21600)):
                executor_state["discovery_budget_status"] = "DUPLICATE_TRIGGER_SUPPRESSED"
                executor_state["discovery_defer_reason"] = f"trigger signature {signature!r} was already processed within the dedupe window ({settings.get('trigger_dedupe_seconds', 21600)}s)"
                return False
        return elapsed >= float(settings.get("triggered_discovery_cooldown_seconds", 300))
    # Proportionality gate: if lifecycle is BLOCKED, discovered work cannot be acted on.
    lifecycle_state = state.get("lifecycle_state", "ACTIVE")
    if lifecycle_state == "BLOCKED":
        executor_state["discovery_budget_status"] = "DEFERRED_PROPORTIONALITY"
        _defer_reason = "lifecycle BLOCKED; discovered work cannot proceed until unresolved effect is reconciled"
        executor_state["discovery_defer_reason"] = _defer_reason
        # §5242: deferred conditions MUST surface as named IntegrityGaps (idempotent)
        if not any(g.get("kind") == "discovery-proportionality-deferred" for g in state.get("integrity_gaps", [])):
            _emit_gap(state, "discovery-proportionality-deferred", "WARNING", _defer_reason)
        return False
    streak = int(executor_state.get("unproductive_discovery_streak", 0))
    exhausted_threshold = int(settings.get("discovery_yield_exhausted_threshold", 5))
    if streak >= exhausted_threshold and not executor_state.get("discovery_trigger"):
        executor_state["discovery_budget_status"] = "DISCOVERY_YIELD_EXHAUSTED"
        _defer_reason = f"unproductive streak {streak} reached exhausted threshold {exhausted_threshold}; requires qualifying reset event"
        executor_state["discovery_defer_reason"] = _defer_reason
        # §5244: yield-exhaustion deferral MUST surface as named IntegrityGap (idempotent)
        if not any(g.get("kind") == "discovery-yield-exhausted" for g in state.get("integrity_gaps", [])):
            _emit_gap(state, "discovery-yield-exhausted", "WARNING", _defer_reason)
        return False
    executor_state.pop("discovery_defer_reason", None)
    base = float(settings.get("discovery_interval_seconds", 604800))
    maximum = float(settings.get("max_discovery_interval_seconds", 4838400))
    allocation = user_controls.discovery_interval(config, state, base, maximum, streak)
    executor_state['resource_allocation'] = allocation
    return elapsed >= allocation['discovery_interval_seconds']


def _check_stale_derived_manifests(state: dict, candidate_version: str) -> list[dict]:
    """Return stale DerivedManifestRef and ConstructSetRef records (§62j r27/r45)."""
    stale = []
    for ref in state.get("derived_manifest_refs", []):
        if ref.get("spec_version") != candidate_version:
            stale.append(ref)
            state.setdefault("evidence", []).append({
                "id": identifier("evidence"), "at": now(),
                "kind": "derived-manifest-stale",
                "manifest_id": ref["manifest_id"],
                "stale_spec_version": ref["spec_version"],
                "candidate_spec_version": candidate_version,
                "intent": ref.get("intent", ""),
            })
    for ref in state.get("construct_set_refs", []):
        if ref.get("spec_version") != candidate_version:
            stale.append(ref)
            state.setdefault("evidence", []).append({
                "id": identifier("evidence"), "at": now(),
                "kind": "derived-construct-set-stale",
                "construct_set_id": ref["construct_set_id"],
                "stale_spec_version": ref["spec_version"],
                "candidate_spec_version": candidate_version,
                "intent": ref.get("intent", ""),
            })
    for ref in state.get("feature_bundle_refs", []):
        if ref.get("spec_version") != candidate_version:
            stale.append(ref)
            state.setdefault("evidence", []).append({
                "id": identifier("evidence"), "at": now(),
                "kind": "derived-construct-set-stale",
                "bundle_name": ref.get("bundle_name", ""),
                "stale_spec_version": ref["spec_version"],
                "candidate_spec_version": candidate_version,
            })
    return stale





def spec_audit_due(state: dict[str, Any]) -> bool:
    """True when URACE.md has not been audited at the current spec version (§81)."""
    spec_path = ROOT / "URACE.md"
    if not spec_path.exists():
        return False
    try:
        current_version = spec_audit_module.extract_spec_version(spec_path.read_text(encoding="utf-8"))
    except OSError:
        return False
    existing = state.get("spec_audit_state") or {}
    return existing.get("spec_version") != current_version


def run_spec_audit(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    """Run deterministic spec structural audit (§81); store as Evidence; return compact summary."""
    spec_path = ROOT / "URACE.md"
    if not spec_path.exists():
        return None
    try:
        report = spec_audit_module.audit(spec_path)
    except Exception:
        return None
    summary = spec_audit_module.build_summary(report)
    state["spec_audit_state"] = {
        "spec_version": report["metadata"]["spec_version"],
        "last_audited_at": now(),
        "section_count": report["metadata"]["section_count"],
        "fence_parity_even": report["global_summary"]["fence_parity_even"],
        "rfc2119_totals": report["global_summary"]["rfc2119_totals"],
        "high_ambiguity_sections": summary["high_ambiguity_sections"],
        "medium_ambiguity_sections": summary["medium_ambiguity_sections"],
        "top_gap_sections": summary["top_gap_sections"],
        "normative_density_per_section": summary["normative_density_per_section"],
    }
    state.setdefault("evidence", []).append({
        "id": identifier("evidence"),
        "at": now(),
        "kind": "spec-structural-audit",
        "spec_version": report["metadata"]["spec_version"],
        "summary": summary,
    })
    return summary


def executor_execution_allowed(config: dict[str, Any], state: dict[str, Any]) -> bool:
    settings = config.get("executor", {})
    executor_state = state.setdefault("executor_state", {})
    current = datetime.now(timezone.utc).timestamp()
    retry_at = executor_state.get("capacity_retry_at")
    if retry_at and current < datetime.fromisoformat(retry_at).timestamp():
        executor_state["discovery_budget_status"] = "WAITING_PROVIDER_CAPACITY"
        return False
    calls = executor_state.setdefault("executor_calls", [])
    calls[:] = [item for item in calls if current - datetime.fromisoformat(item["at"]).timestamp() < 2592000]
    calls_24h = [item for item in calls if current - datetime.fromisoformat(item["at"]).timestamp() < 86400]
    if nullable_limit(settings,"max_executor_calls_per_24h",2) is not None and len(calls_24h)>=nullable_limit(settings,"max_executor_calls_per_24h",2):
        executor_state["discovery_budget_status"] = "DAILY_LIMIT_OR_RESERVE_REACHED"
        return False
    if nullable_limit(settings,"max_executor_calls_per_30d",12) is not None and len(calls)>=nullable_limit(settings,"max_executor_calls_per_30d",12):
        executor_state["discovery_budget_status"] = "MONTHLY_LIMIT_OR_RESERVE_REACHED"
        return False
    return True


def defer_executor_capacity(config: dict[str, Any], state: dict[str, Any], error: intelligent_executor.ExecutorUnavailable, stage: str) -> None:
    executor_state = state.setdefault("executor_state", {})
    fallback_seconds = float(config.get("executor", {}).get("capacity_fallback_seconds", 18000))
    fallback = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + fallback_seconds, timezone.utc).isoformat()
    retained_retry = executor_state.get("capacity_retry_at") if executor_state.get("capacity_category") == error.category and executor_state.get("capacity_stage") == stage else None
    retry_at = error.retry_at or retained_retry or fallback
    signature = hashlib.sha256(json.dumps({"status": "WAITING_PROVIDER_CAPACITY", "retry_at": retry_at, "category": error.category, "stage": stage}, sort_keys=True).encode()).hexdigest()
    changed = executor_state.get("capacity_observation_signature") != signature
    executor_state.update({
        "available": False, "capacity_status": "WAITING_PROVIDER_CAPACITY",
        "capacity_retry_at": retry_at, "capacity_category": error.category,
        "capacity_stage": stage, "availability_reason": "provider capacity window unavailable",
        "capacity_observation_signature": signature,
    })
    if changed:
        state.setdefault("evidence", []).append({
            "id": identifier("evidence"), "at": now(), "kind": "executor-capacity-deferred",
            "stage": stage, "retry_at": retry_at, "category": error.category,
            "disposition": "WAIT_WITHOUT_NEW_EXECUTOR_TASKS",
        })


def _retain_call_usage(call: dict[str, Any], metadata: Any) -> None:
    """Accumulate distinct route receipts on a reused logical reservation."""
    if not isinstance(metadata, dict):
        return
    current = call.get("usage") if isinstance(call.get("usage"), dict) else {}
    if not current:
        call["usage"] = copy.deepcopy(metadata)
        return
    old_receipts = current.get("transport_usage", []) if isinstance(current.get("transport_usage"), list) else []
    new_receipts = metadata.get("transport_usage", []) if isinstance(metadata.get("transport_usage"), list) else []
    # Legacy/adapter-reported usage can lack individual transport identities.
    # Preserve it as an explicitly unattributed group, never invent a provider.
    if not old_receipts:
        old_receipts = [{"provider_id": None, "usage": current,
                         "usage_scope": "unattributed_reported_usage_group"}]
    if not new_receipts:
        new_receipts = [{"provider_id": None, "usage": metadata,
                         "usage_scope": "unattributed_reported_usage_group"}]
    receipts = copy.deepcopy(old_receipts + new_receipts)
    combined = intelligent_executor._aggregate_transport_usage(receipts)
    call["usage"] = combined if combined is not None else {"transport_usage": receipts}


def _current_route_usage(state: dict[str, Any], metadata: Any, prior_route: Any = None) -> Any:
    """Attach this route's receipts without changing adapter metadata otherwise."""
    route = state.get("executor_state", {}).get("provider_pool", {}).get("last_route", {})
    if prior_route is not None and route == prior_route:
        return metadata
    receipts = route.get("transport_usage") if isinstance(route, dict) else None
    if not isinstance(receipts, list):
        return metadata
    if not isinstance(metadata, dict):
        return {
            "source": "provider transport receipt", "usage_provenance": "PARTIAL",
            "input_tokens": None, "cached_input_tokens": None, "output_tokens": None,
            "reported_cost_usd": None, "transport_usage": copy.deepcopy(receipts),
        }
    if "transport_usage" in metadata:
        return metadata
    enriched = copy.deepcopy(metadata)
    enriched["transport_usage"] = copy.deepcopy(receipts)
    return enriched


def _executor_readiness_capability(state: dict[str, Any]) -> str:
    """Return the capability required by the next runnable lifecycle stage."""
    if any(
        objective.get("status") == "planned" and goal_is_schedulable(state, objective)
        for objective in state.get("objectives", [])
    ):
        return "execution"
    return "discovery"


def refresh_executor_availability(config: dict[str, Any], state: dict[str, Any], force: bool = False) -> dict[str, Any]:
    settings = config.get("executor", {})
    executor_state = state.setdefault("executor_state", {"last_discovery_at": None, "last_operation_at": None, "last_availability_check": None, "available": None, "failures": []})
    if not settings.get("enabled"):
        executor_state["available"] = False
        return {"available": False, "transition": None, "reason": "executor disabled"}
    capability = _executor_readiness_capability(state)
    retry_at = executor_state.get("capacity_retry_at")
    if retry_at and datetime.now(timezone.utc).timestamp() < datetime.fromisoformat(retry_at).timestamp():
        return {"available": False, "transition": None, "reason": "provider capacity retry scheduled", "retry_at": retry_at}
    if retry_at:
        executor_state.pop("capacity_retry_at", None)
        executor_state["capacity_status"] = "PROBE_DUE"
        force = True
    last_check = executor_state.get("last_availability_check")
    cached_capability = executor_state.get("availability_capability", "discovery")
    if last_check and cached_capability == capability and not force:
        elapsed = datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(last_check).timestamp()
        if executor_state.get("available"):
            interval = float(settings.get("available_probe_interval_seconds", 300))
        else:
            failures = int(executor_state.get("availability_failure_streak", 0))
            interval = min(float(settings.get("max_unavailable_probe_interval_seconds", 900)), float(settings.get("availability_probe_interval_seconds", 30)) * (2 ** min(failures, 10)))
        if elapsed < interval:
            runtime = state.setdefault("runtime_efficiency", {})
            runtime["availability_checks_suppressed"] = int(runtime.get("availability_checks_suppressed", 0)) + 1
            return {"available": bool(executor_state.get("available")), "transition": None, "reason": executor_state.get("availability_reason", "cached")}
    previous = executor_state.get("available")
    runtime = state.setdefault("runtime_efficiency", {})
    runtime["availability_probes"] = int(runtime.get("availability_probes", 0)) + 1
    probe_started = time.monotonic()
    result = intelligent_executor.pool_availability(settings, executor_state.setdefault("provider_pool", {}), capability)
    runtime["availability_probe_seconds"] = float(runtime.get("availability_probe_seconds", 0)) + (time.monotonic() - probe_started)
    current = result["available"]
    executor_state["availability_failure_streak"] = 0 if current else int(executor_state.get("availability_failure_streak", 0)) + 1
    executor_state.update({"available": current, "last_availability_check": result["checked_at"], "availability_capability": capability, "availability_reason": result["reason"]})
    # Preserve provider-reported authentication separately from availability.
    authenticated = result.get("authenticated")
    if authenticated is False and executor_state.get("authenticated") is not False:
        executor_state["authenticated"] = False
        state["evidence"].append({"id": identifier("evidence"), "at": now(), "kind": "executor-auth-failure", "reason": result.get("authentication_reason") or result.get("reason"), "disposition": "EXECUTOR_AUTHENTICATED_FAILED"})
    else:
        executor_state["authenticated"] = authenticated
    transition = None if previous is None or previous == current else f"{'AVAILABLE' if current else 'UNAVAILABLE'}"
    if previous is None and current:
        transition = "AVAILABLE"
    if transition:
        trigger = {
            "id": identifier("trigger"), "at": now(), "kind": f"EXECUTOR_{transition}",
            "source": settings.get("kind", "executor"), "provenance": "executor availability probe", "disposition": "REASSESS",
        }
        state.setdefault("triggers", []).append(trigger)
        state["evidence"].append({"id": identifier("evidence"), "at": now(), "kind": "executor-availability", "available": current, "provenance": trigger["id"]})
        if current:
            executor_state["capacity_status"] = "AVAILABLE"
            executor_state["discovery_trigger"] = {"reason": "executor became available", "signature": "executor-available"}
    return {**result, "transition": transition}


def discover_with_executor(config: dict[str, Any], state: dict[str, Any], persist_usage: bool = False) -> dict[str, Any] | None:
    from .implementation_sequence import local_only
    pending=[t for t in state.get("objectives",[]) if str(t.get("status","")).lower() not in {"completed","achieved","superseded","cancelled","disabled"}]
    if pending and all(local_only(t) for t in pending):
        state.setdefault("executor_state",{})["discovery_budget_status"]="LOCAL_CONTROLLER_ONLY"
        return None
    if not state.get("executor_state", {}).get("available"):
        return None
    if not executor_execution_allowed(config, state):
        return None
    if not executor_discovery_due(config, state):
        return None
    executor_state = state["executor_state"]
    deferred_id = executor_state.get("deferred_discovery_call")
    call = next((item for item in executor_state.setdefault("executor_calls", []) if deferred_id and item.get("id") == deferred_id), None)
    if call:
        call.update({"outcome": "attempted", "last_transport_attempt_at": now(), "transport_attempts": int(call.get("transport_attempts", 1)) + 1, "logical_reservation_reused": True})
        reason = call.get("reason"); signature = call.get("trigger_signature")
    else:
        executor_state["last_discovery_at"] = now()
        trigger_reason = executor_state.pop("discovery_trigger", None)
        reason = trigger_reason.get("reason") if isinstance(trigger_reason, dict) else trigger_reason
        signature = trigger_reason.get("signature") if isinstance(trigger_reason, dict) else trigger_reason
        call = {"id": identifier("executor-call"), "at": executor_state["last_discovery_at"], "reason": reason or "periodic opportunity audit", "trigger_signature": signature, "stage": "discovery", "outcome": "attempted", "transport_attempts": 1, "logical_reservation_reused": False}
        from ._common import integration_context
        if integration_context():call["integration_context"]=integration_context()
        executor_state["executor_calls"].append(call)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        executor_state["executor_calls"] = [c for c in executor_state["executor_calls"] if c.get("started_at", c.get("at", cutoff)) >= cutoff]
    if signature:
        state["executor_state"]["last_trigger_call"] = {"at": call["at"], "signature": signature}
    state["executor_state"]["discovery_budget_status"] = "WITHIN_BUDGET"
    if persist_usage:
        save_state(config, state)
    _discovery_started = time.monotonic()
    prior_route = copy.deepcopy(executor_state.get("provider_pool", {}).get("last_route"))
    try:
        proposal = intelligent_executor.discover(ROOT, config, state)
    except intelligent_executor.ExecutorUnavailable as error:
        call["outcome"] = "deferred_provider_capacity"
        _retain_call_usage(call, _current_route_usage(state, getattr(error, "__urace_executor_metadata__", None), prior_route))
        executor_state["deferred_discovery_call"] = call["id"]
        raise
    except Exception as error:
        call["outcome"] = "failed"
        _retain_call_usage(call, _current_route_usage(state, getattr(error, "__urace_executor_metadata__", None), prior_route))
        executor_state.pop("deferred_discovery_call", None)
        state["executor_state"]["unproductive_discovery_streak"] = int(state["executor_state"].get("unproductive_discovery_streak", 0)) + 1
        raise
    finally:
        call["elapsed_seconds"] = time.monotonic() - _discovery_started
    _retain_call_usage(call, _current_route_usage(state, proposal.get("__urace_executor_metadata__"), prior_route))
    hypothesis = proposal.get("pattern_hypothesis", "").strip()
    executor_state.pop("deferred_discovery_call", None)
    if hypothesis:
        memory = state.setdefault("reasoning_memory", [])
        existing = next((item for item in memory if item["hypothesis"].casefold() == hypothesis.casefold()), None)
        entry = existing or {"id": identifier("pattern"), "hypothesis": hypothesis, "first_seen": now(), "observations": 0}
        entry.update({
            "last_seen": now(), "observations": entry["observations"] + 1,
            "supporting_evidence": proposal.get("pattern_evidence", [])[-10:],
            "counterevidence": proposal.get("pattern_counterevidence", [])[-10:],
            "confidence": proposal.get("pattern_confidence", 0),
            "applicability": proposal.get("pattern_applicability", "unspecified"),
            "learned_response": proposal.get("learned_response", "investigate before acting"),
            "status": "ACTIVE" if proposal.get("pattern_confidence", 0) >= 0.6 else "TENTATIVE",
        })
        if existing is None:
            memory.append(entry)
        limit = int(config.get("efficiency", {}).get("max_reasoning_memory_entries", 100))
        if len(memory) > limit:
            memory[:] = sorted(memory, key=lambda item: (item.get("status") == "ACTIVE", item.get("confidence", 0), item.get("last_seen", "")), reverse=True)[:limit]
    metric_system = state.setdefault("metric_system", {"version": 1, "last_review_at": None, "last_assessment": None, "change_needed": False, "change_history": []})
    metric_system.update({"last_review_at": now(), "last_assessment": proposal["metric_assessment"], "change_needed": proposal["metric_change_needed"]})
    evaluation_system = state.setdefault("evaluation_system", {**config.get("evaluation_system", {}), "last_review_at": None, "last_assessment": None, "change_needed": False, "change_history": []})
    evaluation_system.update({"last_review_at": now(), "last_assessment": proposal.get("evaluation_assessment", "No separate evaluation-system assessment returned"), "change_needed": proposal.get("evaluation_change_needed", False)})
    proposal_evidence={"id": identifier("evidence"), "at": now(), "kind": "executor-proposal", "proposal": proposal, "provenance": "Existing read-only discovery executor"}
    state["evidence"].append(proposal_evidence)
    if not proposal["should_act"]:
        call["outcome"] = "no_action"
        state["executor_state"]["unproductive_discovery_streak"] = int(state["executor_state"].get("unproductive_discovery_streak", 0)) + 1
        return None
    if proposal["scope"] in {"runtime", "rebootstrap"}:
        policy = state.get("self_evolution_policy", {"mode": "DISABLED"})
        mode = policy.get("mode", "DISABLED").upper()
        eligible = mode == "CONTINUOUS" or (
            mode == "NECESSARY_ONLY"
            and proposal["self_evolution_necessary"]
            and bool(proposal["necessity_evidence"].strip())
            and not proposal["lower_impact_route_sufficient"]
        )
        if not eligible:
            call["outcome"] = "ineligible"
            state["executor_state"]["unproductive_discovery_streak"] = int(state["executor_state"].get("unproductive_discovery_streak", 0)) + 1
            state["evidence"].append({
                "id": identifier("evidence"), "at": now(), "kind": "self-evolution-policy-decision",
                "outcome": "INELIGIBLE", "mode": mode, "scope": proposal["scope"],
                "reason": "proposal did not satisfy the selected self-evolution policy",
                "proposal": proposal,
            })
            return None
    priority_scope = proposal.get("priority_scope")
    definition = config.get("scope_priority", {}).get("scopes", {}).get(priority_scope, {})
    if proposal["scope"] not in definition.get("execution_scopes", []):
        priority_scope = scope_priority.infer_scope(config, proposal["scope"])
    objective = {
        "id": identifier("objective"),
        "title": proposal["title"],
        "reason": proposal["reason"],
        "success_measure": proposal["success_measure"],
        "outcome_measure_id": proposal.get("outcome_measure_id"),
        "scope": proposal["scope"],
        "priority_scope": priority_scope,
        "priority": 60,
        "metadata": {"forecast_evidence_ref": proposal_evidence["id"]},
        "expected_value": proposal.get("expected_value", 0.5), "estimated_cost": proposal.get("estimated_cost", 0.5),
        "risk": proposal.get("risk", 0.5), "urgency": proposal.get("urgency", 0.5), "confidence": proposal.get("pattern_confidence", 0.5),
        "necessity_evidence": proposal.get("necessity_evidence", ""), "lower_impact_route_sufficient": proposal.get("lower_impact_route_sufficient", True),
        "status": "planned",
        "created_at": now(), "updated_at": now(),
    }
    if signature:
        objective["input_links"] = [signature]

    # --- Destination drift check (spec §8-9, §24) ---
    anchor = state.get("destination_anchor", {})
    if anchor:
        drift = destination_anchor.drift_score(objective, anchor)
        objective["destination_drift_score"] = drift
        if drift >= destination_anchor.DRIFT_FLAG:
            drift_evidence = destination_anchor.build_drift_evidence(objective, drift, anchor)
            drift_evidence["id"] = identifier("evidence")
            drift_evidence["at"] = now()
            state.setdefault("evidence", []).append(drift_evidence)
            if drift >= destination_anchor.DRIFT_BLOCK:
                objective["status"] = "awaiting_operator_decision"
                objective["drift_blocked"] = True
                state["lifecycle_state"] = "WAITING_FOR_AUTHORITATIVE_DECISION"
                call["outcome"] = "drift_escalated"
                state["objectives"].append(objective)
                return None

    state["objectives"].append(objective)
    call["objective_id"] = objective["id"]
    call["outcome"] = "objective_created"
    state["executor_state"]["unproductive_discovery_streak"] = 0

    # Multi-objective: process additional proposals from the `objectives` array.
    # The primary objective is already appended above; these are ranked secondary proposals.
    for extra in proposal.get("objectives", []):
        if not isinstance(extra, dict) or not extra.get("title"):
            continue
        if extra.get("title") == proposal.get("title"):
            continue  # skip if duplicate of primary
        extra_obj = {
            "id": identifier("objective"),
            "title": extra["title"],
            "reason": extra.get("reason", ""),
            "success_measure": extra.get("success_measure", ""),
            "outcome_measure_id": extra.get("outcome_measure_id"),
            "scope": extra.get("scope", "documentation"),
            "priority_scope": extra.get("priority_scope", "product_guidance"),
            "priority": 50,  # secondary proposals rank below primary
            "metadata": {"forecast_evidence_ref": proposal_evidence["id"], "secondary": True},
            "expected_value": extra.get("expected_value", 0.5),
            "estimated_cost": extra.get("estimated_cost", 0.5),
            "risk": extra.get("risk", 0.5),
            "urgency": extra.get("urgency", 0.5),
            "confidence": proposal.get("pattern_confidence", 0.5),
            "necessity_evidence": extra.get("necessity_evidence", ""),
            "lower_impact_route_sufficient": extra.get("lower_impact_route_sufficient", True),
            "status": "planned",
            "created_at": now(), "updated_at": now(),
        }
        if signature:
            extra_obj["input_links"] = [signature]
        state["objectives"].append(extra_obj)

    return objective


def _transition(state: dict[str, Any], destination: str, operation_id: str) -> None:
    prior = state.get("lifecycle_state")
    state["lifecycle_state"] = destination
    state.setdefault("status_transitions", []).append({"from": prior, "to": destination,
        "status": destination, "at": now(), "operation": operation_id})


def execute_with_executor(config: dict[str, Any], state: dict[str, Any], objective: dict[str, Any], plan: dict[str, Any], persist_usage: bool = False) -> dict[str, Any]:
    from .implementation_sequence import local_only,execute_local
    if local_only(objective):
        if not goal_is_schedulable(state,objective):raise RuntimeError("Local action authority or dependency not satisfied")
        return execute_local(config,state,objective)
    reservation_id = objective.get("executor_capacity_reservation")
    execution_call = next((item for item in state.setdefault("executor_state", {}).setdefault("executor_calls", []) if reservation_id and item.get("id") == reservation_id), None)
    if not execution_call and not executor_execution_allowed(config, state):
        objective["status"] = "deferred_budget"
        return {"status": "DEFERRED_BUDGET", "changed_files": []}
    if execution_call:
        execution_call.update({"outcome": "attempted", "last_transport_attempt_at": now(), "transport_attempts": int(execution_call.get("transport_attempts", 1)) + 1, "logical_reservation_reused": True})
    else:
        execution_call = {"id": identifier("executor-call"), "at": now(), "reason": objective["id"], "stage": "execution", "outcome": "attempted", "transport_attempts": 1, "logical_reservation_reused": False}
        from ._common import integration_context
        if integration_context():execution_call["integration_context"]=integration_context()
        state["executor_state"]["executor_calls"].append(execution_call)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        state["executor_state"]["executor_calls"] = [c for c in state["executor_state"]["executor_calls"] if c.get("started_at", c.get("at", cutoff)) >= cutoff]
    if persist_usage:
        save_state(config, state)
    _execution_started = time.monotonic()
    before_metrics = document_metrics(config)
    scope = objective.get("scope", "documentation")
    operation = {
        "id": identifier("operation"), "objective_reference": objective["id"], "plan_reference": plan["id"],
        "executor": "codex-cli", "status": "ATTEMPTED", "attempted_at": now(), "updated_at": now(),
        "authority_basis": "delegated specification evolution" if scope == "documentation" else ("external metric policy" if scope == "metrics" else "delegated runtime self-evolution and re-bootstrap"),
        "scope": scope,
        "priority_scope": objective.get("priority_scope"),
        "outcome_contract": outcome_verification.capture(ROOT, config, objective),
    }
    state["operations"].append(operation)
    prior_route = copy.deepcopy(state.get("executor_state", {}).get("provider_pool", {}).get("last_route"))
    try:
        prepared = intelligent_executor.execute(ROOT, config, state, objective)
    except intelligent_executor.ExecutorUnavailable as error:
        execution_call["outcome"] = "deferred_provider_capacity"
        operation["status"] = "DEFERRED_PROVIDER_CAPACITY"
        metadata = _current_route_usage(state, getattr(error, "__urace_executor_metadata__", None), prior_route)
        if isinstance(metadata, dict):
            operation["usage"] = copy.deepcopy(metadata)
            _retain_call_usage(execution_call, metadata)
        objective["executor_capacity_reservation"] = execution_call["id"]
        raise
    except Exception as error:
        execution_call["outcome"] = "failed"
        operation["status"] = "FAILED"
        if hasattr(error, "__urace_executor_metadata__"):
            operation["usage"] = _current_route_usage(state, getattr(error, "__urace_executor_metadata__"), prior_route)
            _retain_call_usage(execution_call, operation["usage"])
        objective.pop("executor_capacity_reservation", None)
        raise
    finally:
        operation["elapsed_seconds"] = time.monotonic() - _execution_started
        execution_call["elapsed_seconds"] = operation["elapsed_seconds"]
    objective.pop("executor_capacity_reservation", None)
    route = prepared.get("__urace_route__") or state.get("executor_state", {}).get("provider_pool", {}).get("last_route") or {}
    attribution = {
        "executor_id": route.get("provider", "unknown"), "adapter": route.get("adapter", "unknown"),
        "capability": route.get("capability", "execution"), "attempted_executors": route.get("attempted", []),
        "logical_reservation": execution_call["id"],
    }
    execution_call["executor_attribution"] = attribution
    operation["executor"] = attribution
    operation["change_id"] = operation["id"]
    operation["executor_source_summary"] = str(prepared.get("message", "")).strip()[:4000]
    operation["usage"] = _current_route_usage(state, prepared.get("__urace_executor_metadata__", {}), prior_route)
    operation["elapsed_seconds"] = time.monotonic() - _execution_started
    execution_call["elapsed_seconds"] = operation["elapsed_seconds"]
    _retain_call_usage(execution_call, operation["usage"])
    try:
        from urace.cost_model import receipt_from_operation, store_receipt
        _receipt = receipt_from_operation(operation)
        if _receipt is not None:
            store_receipt(config, _receipt)
    except Exception:
        pass
    if prepared["status"] == "NO_EFFECT":
        execution_call["outcome"] = "no_effect"
        operation["status"] = "OBSERVED_NO_EFFECT"
        objective["status"] = "needs_reassessment"
        return {"status": "NO_EFFECT", "operation": operation["id"]}
    if prepared["status"] == "UPDATE_CONFLICT":
        execution_call["outcome"] = "awaiting_operator_decision"
        operation.update({"status": "AWAITING_OPERATOR_DECISION", "conflict": prepared["conflict"], "observed_at": now()})
        objective.update({"status": "awaiting_operator_decision", "update_conflict": prepared["conflict"]})
        state["lifecycle_state"] = "WAITING_FOR_AUTHORITATIVE_DECISION"
        state["evidence"].append({
            "id": identifier("evidence"), "at": now(), "kind": "update-customization-conflict",
            "operation": operation["id"], "candidate": objective.get("update_candidate", {}).get("sha256"),
            "explanation": prepared["conflict"], "disposition": "NO_FILES_APPLIED",
            "next": "inspect the explanation, add attributable resolution context or revise/cancel the goal, then resume",
        })
        return {"status": "AWAITING_OPERATOR_DECISION", "operation": operation["id"], "conflict": prepared["conflict"]}
    transaction_id = identifier("transaction")
    after_contents = prepared["contents"]
    # §78-BE: Check for concurrent external edits BEFORE scope validation — a stale
    # base_hash means the file changed since the executor captured it; abort immediately
    # without touching the file, regardless of scope.
    conflicts = [
        item for item in after_contents
        if (ROOT / item).exists()
        and hashlib.sha256((ROOT / item).read_bytes()).hexdigest() != prepared.get("base_hashes", {}).get(item)
    ]
    if conflicts:
        execution_call.update({"outcome": "concurrent_change", "conflicting_files": conflicts})
        operation.update({"status": "CONCURRENT_CHANGE", "conflicting_files": conflicts, "observed_at": now()})
        objective["status"] = "needs_reassessment"
        state["evidence"].append({
            "id": identifier("evidence"), "at": now(), "kind": "concurrent-product-change",
            "operation": operation["id"], "files": conflicts, "disposition": "CANDIDATE_NOT_APPLIED",
        })
        return {"status": "CONCURRENT_CHANGE", "operation": operation["id"], "conflicting_files": conflicts}
    file_errors = independent_validation.candidate_file_errors(ROOT, scope, list(after_contents), config)
    if set(after_contents) != set(prepared["changed_files"]):
        file_errors.append("candidate contents differ from declared changed_files")
    if file_errors:
        operation["status"] = "REJECTED_SCOPE"
        raise RuntimeError("candidate rejected before application: " + "; ".join(file_errors))
    operation["changed_files"] = list(after_contents)
    before_contents = {item: (ROOT / item).read_text(encoding="utf-8") for item in after_contents}
    journal = {
        "id": transaction_id,
        "recovery_protocol": "atomic-v2",
        "operation": operation["id"],
        "created_at": now(),
        "phase": "PREPARED",
        "before": {relative: before_contents[relative] for relative in after_contents},
        "after": after_contents,
        "applied": [],
    }
    atomic_write_json(transaction_path(config), journal)
    try:
        journal["phase"] = "APPLYING"
        atomic_write_json(transaction_path(config), journal)
        for relative, content in after_contents.items():
            atomic_write_text(ROOT / relative, content)
            journal["applied"].append(relative)
            atomic_write_json(transaction_path(config), journal)
        after_metrics = document_metrics(config)
        before_size = sum(len(content.encode("utf-8")) for content in before_contents.values())
        after_size = sum(len(content.encode("utf-8")) for content in after_contents.values())
        efficiency = config.get("efficiency", {})
        allowed_growth = min(
            before_size * (float(efficiency.get("max_product_growth_ratio_per_change", 1.25)) - 1.0),
            float(efficiency.get("max_product_growth_bytes_per_change", 100000)),
        )
        if after_size - before_size > allowed_growth:
            raise RuntimeError(f"prepared change exceeded Product growth budget: +{after_size - before_size} bytes > +{allowed_growth:g}")
        guardrails_ok = (
            after_metrics["normative_rules"] >= before_metrics["normative_rules"]
            and after_metrics["behavioral_tests"] >= before_metrics["behavioral_tests"]
        )
        if not guardrails_ok:
            raise RuntimeError("prepared change violated measurable blueprint guardrails")
        integrity_errors = validate_product(config, before_metrics)
        if integrity_errors:
            raise RuntimeError("prepared change failed Product integrity: " + "; ".join(integrity_errors))
        journal["phase"] = "APPLIED"
        atomic_write_json(transaction_path(config), journal)
        operation["applied_at"] = now()
        _transition(state, "VALIDATING", operation["id"])
    except Exception:
        for relative, content in journal["before"].items():
            atomic_write_text(ROOT / relative, content)
        durable_unlink(transaction_path(config))
        _ts = now(); operation["status"] = "REJECTED_ROLLED_BACK"; operation["rejected_at"] = _ts; operation["rolled_back_at"] = _ts; operation["updated_at"] = _ts
        _transition(state, "REPAIRING", operation["id"])
        raise
    directions = {name: item["direction"] for name, item in state["progress_profiles"][0]["measures"].items()}
    improved = sum(compare(directions.get(name, "increase"), value, before_metrics.get(name, value)) == "improved" for name, value in after_metrics.items())
    regressed = sum(compare(directions.get(name, "increase"), value, before_metrics.get(name, value)) == "regressed" for name, value in after_metrics.items())

    # --- Independent validation gate (spec §54, §60) ---
    # Executor result is an Observation until independently validated.
    try:
        validation_result = independent_validation.validate_operation(
            ROOT, operation, before_metrics, after_metrics, config, state
        )
    except Exception:
        for relative, content in journal["before"].items():
            atomic_write_text(ROOT / relative, content)
        durable_unlink(transaction_path(config))
        operation["status"] = "REJECTED_VALIDATION_ERROR"
        _transition(state, "REPAIRING", operation["id"])
        save_state(config, state)
        raise
    operation["independent_validation"] = validation_result
    if validation_result["verdict"] == independent_validation.PENDING_CAPABILITY:
        for relative, content in journal["before"].items():
            atomic_write_text(ROOT / relative, content)
        operation["status"] = "PENDING_VALIDATION"
        objective["status"] = "awaiting_validation"
        pending = independent_validation.pending_validation_record(operation, validation_result["basis"])
        pending["candidate"] = {"contents": after_contents, "base_hashes": prepared["base_hashes"]}
        state.setdefault("pending_validations", []).append(pending)
        _transition(state, "WAITING_FOR_CONDITION", operation["id"])
        save_state(config, state)
        durable_unlink(transaction_path(config))
        return {"status": "PENDING_VALIDATION", "operation": operation["id"], "changed_files": []}
    if validation_result["verdict"] == independent_validation.REJECTED:
        # Roll back: independent validation rejected the change.
        for relative, content in journal["before"].items():
            atomic_write_text(ROOT / relative, content)
        durable_unlink(transaction_path(config))
        _ts = now(); operation["status"] = "REJECTED_INDEPENDENT_VALIDATION"; operation["rejected_at"] = _ts; operation["updated_at"] = _ts
        _transition(state, "REPAIRING", operation["id"])
        _fails_r = {c.get("domain", ""): c.get("detail", "") for c in validation_result.get("fails", []) if "domain" in c}
        for _dom_r in ("authority", "intent", "schema", "constraint"):
            _status_r = "NON_COMPLIANT" if _dom_r in _fails_r else "UNKNOWN"
            _detail_r = _fails_r.get(_dom_r)
            _emit_compliance_record(state, _dom_r, _status_r, operation.get("id"), _detail_r, operation.get("scope"))
        fail_summary = "; ".join(c["detail"] for c in validation_result["fails"])
        raise RuntimeError(f"Independent validation rejected applied change: {fail_summary}")

    # Emit ComplianceRecord per domain (spec §54 compliance recording contract, r48)
    op_id = operation.get("id")
    op_scope = operation.get("scope")
    _iv = validation_result
    _passes = {c["domain"] for c in _iv.get("passes", []) if "domain" in c}
    _fails  = {c["domain"]: c.get("detail", "") for c in _iv.get("fails", []) if "domain" in c}
    for _dom in ("authority", "intent", "schema", "constraint"):
        if _dom in _fails:
            _emit_compliance_record(state, _dom, "NON_COMPLIANT", op_id, _fails[_dom], op_scope)
        elif _dom in _passes:
            _emit_compliance_record(state, _dom, "COMPLIANT", op_id, None, op_scope)

    journal["phase"] = "VALIDATED"
    atomic_write_json(transaction_path(config), journal)
    _transition(state, "ASSESSING", operation["id"])
    _transition(state, "ACTIVE", operation["id"])
    execution_call.update({"outcome": "accepted", "observed_metric_effect": {"improved": improved, "regressed": regressed}, "changed_files": prepared["changed_files"], "change_id": operation["id"]})
    _accepted_ts = now(); operation.update({"status": "ACCEPTED", "accepted_at": _accepted_ts, "updated_at": _accepted_ts, "transaction": transaction_id, "changed_files": prepared["changed_files"], "before_metrics": before_metrics, "after_metrics": after_metrics, "observed_metric_effect": {"improved": improved, "regressed": regressed}, "decision": objective.get("title"), "decision_basis": objective.get("reason")})
    # R7 — Compliance symmetric recording: emit ADVANCING record on ACCEPTED transitions
    _emit_compliance_record(state, scope, "ADVANCING", operation.get("id"), "operation accepted — compliance advancing", scope)
    explanation_mode = str(config.get("change_explanations", {}).get("mode", "disabled")).lower()
    if explanation_mode == "enabled" or (explanation_mode == "auto" and (len(prepared["changed_files"]) > 1 or float(objective.get("risk", 0)) >= 0.5)):
        operation["explanation"] = operation["executor_source_summary"] or f"Implemented {objective.get('title')} and passed validation."
    objective["implementation_status"] = "accepted"
    objective["status"] = "awaiting_outcome"
    objective["outcome_status"] = "PENDING_OUTCOME"
    objective["updated_at"] = operation["accepted_at"]
    objective.pop("executor_capacity_reservation", None)
    plan["status"] = "completed"; plan["completed_at"] = operation["accepted_at"]; plan["updated_at"] = operation["accepted_at"]
    state["executor_state"]["last_operation_at"] = now()
    # X2: Regression-scope checkpoint gate (§62c Quality Streak Mechanism)
    if not _regression_checkpoint_gate_passes(state, scope):
        _emit_gap(state, "regression-checkpoint-pending", "WARNING",
                  f"Checkpoint for scope={scope} blocked: most recent QualityDelta is REGRESSION; "
                  f"a CHECKPOINT_ACCEPTANCE DecisionRecord is required before acceptance.")
    else:
        state["checkpoints"].append({"id": identifier("checkpoint"), "at": now(), "kind": "accepted-product-change", "digest": product_digest(config), "operation": operation["id"], "transaction": transaction_id})

    # --- Value trajectory recording (spec §60 continuous follow-up) ---
    elapsed_seconds = time.monotonic() - _execution_started
    operation["elapsed_seconds"] = elapsed_seconds
    execution_call["elapsed_seconds"] = elapsed_seconds
    # Structural measurements remain diagnostics and earn no outcome credit.
    value_trajectory.record_checkpoint(state, operation, before_metrics, after_metrics, elapsed_seconds)
    if not any(o.get("id") == objective["id"] for o in state["objectives"]):
        state["objectives"].append(objective)
    outcome_verification.refresh(ROOT, config, state)

    # --- Rule Ledger: bind this accepted change to its governing rules (Change Schema) ---
    ledger = state.get("rule_ledger")
    if ledger is not None:
        _exec = operation.get("executor", {})
        rule_ledger_module.bind_change(
            ledger,
            operation["id"],
            scope,
            kind="ACCEPTED",
            description=str(objective.get("title", "")),
            state_before_digest=_product_digest_at(config, journal.get("before", {})),
            state_after_digest=product_digest(config),
            delta_to_rules=[],
            executor={"id": _exec.get("executor_id", ""), "route": _exec.get("__urace_route__", {})},
            validation={"verdict": "ACCEPTED", "checks": validation_result.get("checks", [])},
            value_delta=float(operation.get("outcome_value_credited", 0.0)),
        )

    if scope in {"metrics", "runtime", "rebootstrap"}:
        state["pending_runtime_activation"] = {"transaction": transaction_id, "scope": scope, "operation": operation["id"], "requested_at": now()}
        state["restart_requested"] = True
    journal["phase"] = "ACCEPTED"
    atomic_write_json(transaction_path(config), journal)
    save_state(config, state)
    return {"status": "ACCEPTED", "operation": operation["id"], "changed_files": prepared["changed_files"],
            "outcome_status": operation["outcome"]["status"], "real_user_value_verified": operation["outcome"]["real_user_value_verified"]}


def core_fault_descriptor(error: BaseException, command: str) -> dict[str, str] | None:
    """Describe only trusted control structure; never forward exception or Product content."""
    if command != "auto" or not isinstance(error, (AssertionError, AttributeError, KeyError, TypeError)):
        return None
    return {"component": "lifecycle", "code": "UNEXPECTED_CONTROLLER_EXCEPTION", "operation": command, "exception_class": type(error).__name__}


def runtime_version_digest(config: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(runtime_files(config)):
        path = ROOT / relative
        digest.update(relative.encode()); digest.update(path.read_bytes())
    return digest.hexdigest()


def attempt_core_auto_repair(config: dict[str, Any], state: dict[str, Any], fault: dict[str, str] | None, confirmed_recurrence: bool = False) -> str:
    """Deduplicate and execute a supervised repair for trusted core-controller faults."""
    if fault is None or state.get("self_evolution_policy", {}).get("mode") == "DISABLED":
        return "INELIGIBLE"
    state["lifecycle_state"] = "REPAIRING"
    save_state(config, state)
    version = runtime_version_digest(config)
    key = hashlib.sha256(json.dumps({"fault": fault, "runtime": version}, sort_keys=True).encode()).hexdigest()
    registry = state.setdefault("system_repair_registry", {})
    entry = registry.setdefault(key, {"fault": fault, "runtime_version": version, "count": 0, "status": "OBSERVED", "first_at": now()})
    entry["count"] = int(entry.get("count", 0)) + 1; entry["last_at"] = now()
    if confirmed_recurrence:
        entry["count"] = max(2, entry["count"])
    if entry["status"] not in {"OBSERVED", "RETRY_PENDING"}:
        save_state(config, state); return "DEDUPLICATED"
    if entry["count"] < 2:
        entry["status"] = "RETRY_PENDING"; save_state(config, state); return "RETRY"
    availability = intelligent_executor.availability(config.get("executor", {}))
    if not availability.get("available") or not executor_execution_allowed(config, state):
        entry["status"] = "DEFERRED_CAPABILITY_OR_BUDGET"; save_state(config, state); return "DEFERRED"
    if state.get("self_evolution_policy", {}).get("mode") == "NECESSARY_ONLY":
        state.setdefault("evidence", []).append({
            "id": identifier("evidence"), "at": now(),
            "kind": "self-evolution-necessity-justification",
            "necessity": f"Trusted controller fault code {fault.get('code')} recurred in {fault.get('operation', fault.get('phase', 'unknown'))} with exception class {fault.get('exception_class')}",
            "policy_mode": "NECESSARY_ONLY",
            "disposition": "PROCEEDING_WITH_JUSTIFIED_REPAIR",
        })
    entry["status"] = "VALIDATING"
    objective = {
        "id": identifier("objective"), "title": "Repair a repeated core lifecycle controller fault",
        "reason": f"Trusted controller fault code {fault['code']} recurred in {fault.get('operation', fault.get('phase', 'unknown'))} with exception class {fault['exception_class']}. No Product, cohort, candidate, peer, metric, Executor, connector, or exception-message content is included.",
        "success_measure": "The failing lifecycle path has a regression test and the complete runtime suite passes",
        "scope": "runtime", "target": "urace", "priority": 100, "status": "planned",
        "expected_value": 1.0, "estimated_cost": 0.25, "risk": 0.25, "urgency": 1.0,
        "necessity_evidence": f"The same trusted controller fault code occurred {entry['count']} times on runtime version {version[:12]}",
        "lower_impact_route_sufficient": False, "created_at": now(), "updated_at": now(), "authority_basis": "delegated runtime self-evolution",
        "repair_key": key,
    }
    state.setdefault("objectives", []).append(objective)
    plan = plan_for(state, objective)
    try:
        result = execute_with_executor(config, state, objective, plan, persist_usage=True)
        entry["status"] = "ACTIVATION_REQUESTED" if result.get("status") == "ACCEPTED" else result.get("status", "NO_EFFECT")
    except Exception as repair_error:
        entry["status"] = "FAILED_VALIDATION"
        entry["failure_class"] = type(repair_error).__name__
        save_state(config, state); return "FAILED"
    state["lifecycle_state"] = "ASSESSING"
    save_state(config, state)
    return "ACTIVATE" if entry["status"] == "ACTIVATION_REQUESTED" else "COMPLETE"


def _evaluate_wake_conditions(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Dequeue any wake conditions whose scheduled_at has elapsed."""
    current_ts = datetime.now(timezone.utc).timestamp()
    due, remaining = [], []
    for condition in state.get("wake_registry", []):
        try:
            if datetime.fromisoformat(condition["scheduled_at"]).timestamp() <= current_ts:
                due.append(condition)
                continue
        except (KeyError, ValueError):
            pass
        remaining.append(condition)
    state["wake_registry"] = remaining
    return due


def _run_onboard_gate(config: dict, state: dict) -> "dict | None":
    """
    Returns None if onboard gate passes (or already onboarded).
    Returns a dict {"outcome": "onboarding", "reason": ...} to halt cycle when blocked.
    SD=True — never touches executor.
    """
    product_name = config.get("product", "")
    onboard_records = state.get("onboard_records", [])
    # Find active record for current product
    active_record = next(
        (r for r in onboard_records
         if r.get("product_name") == product_name and not r.get("superseded_at")),
        None
    )
    if active_record:
        # Check config digest staleness
        current_digest = product_digest(config)
        if active_record.get("config_digest") != current_digest:
            detail = f"Config digest diverged from OnboardRecord {active_record['id']} — run `urace onboard confirm` to refresh"
            if not any(g.get('kind') == 'onboard-record-config-diverged' and g.get('detail') == detail
                       and not g.get('resolved') and g.get('active', True)
                       for g in state.get('integrity_gaps', [])):
                _emit_gap(state, "onboard-record-config-diverged", "WARNING", detail)
            observation = state.setdefault('integrity_gap_observations', {}).setdefault(
                'onboard:' + active_record['id'], {'observations': 0})
            observation.update(last_observed_at=now(), config_digest=current_digest,
                               observations=observation['observations'] + 1,
                               condition_still_present=True)
        return None  # Gate passes; autonomous cycles authorized

    # No matching OnboardRecord — enter ONBOARDING
    state["lifecycle_state"] = "ONBOARDING"
    _emit_trace(state, "ONBOARD", "lifecycle → ONBOARDING (no OnboardRecord for product)")

    # --- Gate 1: Config completeness ---
    missing_fields = []
    if not config.get("product"):
        missing_fields.append("product")
    if not config.get("intent", {}).get("purpose"):
        missing_fields.append("intent.purpose")
    if not config.get("capability_envelope"):
        missing_fields.append("capability_envelope (or set capability_envelope_waived)")
    if missing_fields:
        _emit_gap(state, "onboard-config-incomplete", "BLOCKING",
            f"Config missing required fields: {', '.join(missing_fields)}")

    # --- Gate 2: product_files readable ---
    import os as _os
    product_files = config.get("product_files", [])
    unreadable = [p for p in product_files if not _os.access(str(ROOT / p), _os.R_OK)]
    if unreadable:
        _emit_gap(state, "onboard-no-readable-product-files", "BLOCKING",
            f"Unreadable product_files: {', '.join(unreadable)}")

    # --- Gate 3: intent anchored ---
    if not config.get("intent", {}).get("purpose"):
        _emit_gap(state, "onboard-intent-unanchored", "BLOCKING",
            "Config.intent.purpose is absent or empty — set a non-empty purpose to anchor autonomous evolution")

    # --- Gate 4: capability_envelope declared (WARNING only) ---
    if not config.get("capability_envelope"):
        _emit_gap(state, "onboard-capability-envelope-missing", "WARNING",
            "Config.capability_envelope is absent — capabilities will be unconstrained; declare envelope or set capability_envelope_waived")

    # --- Gate 5: self_evolution_policy (INFO — default applied silently) ---
    if not config.get("self_evolution_policy"):
        state.setdefault("evidence", []).append({
            "id": identifier("ev-"),
            "kind": "onboard-policy-defaulted",
            "at": now(),
            "summary": "self_evolution_policy absent; NECESSARY_ONLY applied as default",
        })

    # --- Check if any BLOCKING gaps are active (gates 1-3) ---
    active_blocking = [
        g for g in state.get("integrity_gaps", [])
        if g.get("active", True) and g.get("severity") == "BLOCKING"
        and g.get("kind", "").startswith("onboard-")
    ]
    if active_blocking:
        return {"outcome": "onboarding", "reason": f"ONBOARDING blocked: {', '.join(g['kind'] for g in active_blocking)} — run `urace onboard status` to see gate results"}

    # Gates 1-3 pass — emit confirmation-pending
    _emit_gap(state, "onboard-confirmation-pending", "BLOCKING",
        "All BLOCKING onboard gates passed — run `urace onboard confirm` to authorize autonomous cycles")
    return {"outcome": "onboarding", "reason": "awaiting operator confirmation — run `urace onboard confirm`"}


def _verify_wake_registrations(config: dict[str, Any], state: dict[str, Any]) -> list[str]:
    """§67 Wake Registration Verification Mechanism (r33): on restart, verify each
    entry in wake_registry is still active. Returns list of wake-integrity-gap details.
    Entries lacking required fields or lacking verified_at are treated as unverifiable.
    Tracks liveness_failures per entry; after 3 failures marks stale_since. After
    max_stale_hours (default 168) of STALE status escalates to BLOCKING gap
    wake-registration-expired (§5505). SD=True — reads only local state.
    """
    max_stale_hours = float(config.get("wake", {}).get("max_stale_hours", 168))
    current_ts = datetime.now(timezone.utc).timestamp()
    gaps: list[str] = []
    for reg in state.get("wake_registry", []):
        reg_id = reg.get("id", "unknown")
        unverifiable = not reg.get("kind") or not reg.get("scheduled_at") or not reg.get("verified_at")
        if unverifiable:
            # Increment liveness failure counter
            reg["liveness_failures"] = reg.get("liveness_failures", 0) + 1
            failures = reg["liveness_failures"]
            # After 3 failures, mark stale if not already
            if failures >= 3 and not reg.get("stale_since"):
                reg["stale_since"] = now()
            if reg.get("stale_since"):
                stale_ts = datetime.fromisoformat(reg["stale_since"]).timestamp()
                elapsed_hours = (current_ts - stale_ts) / 3600.0
                if elapsed_hours >= max_stale_hours:
                    # Escalate to BLOCKING — emit gap directly and record in gaps list
                    _emit_gap(
                        state,
                        "wake-registration-expired",
                        "BLOCKING",
                        f"WakeRegistration {reg_id} STALE > {max_stale_hours:.0f}h; re-establish or remove",
                    )
                    gaps.append(
                        f"WakeRegistration {reg_id} STALE for {elapsed_hours:.1f}h (>{max_stale_hours:.0f}h); "
                        f"escalated to wake-registration-expired BLOCKING gap"
                    )
                else:
                    if not reg.get("kind") or not reg.get("scheduled_at"):
                        gaps.append(
                            f"WakeRegistration {reg_id} missing required fields (kind or scheduled_at); "
                            f"cannot verify as active (failures: {failures})"
                        )
                    else:
                        gaps.append(
                            f"WakeRegistration {reg_id} has no verified_at; "
                            f"registration cannot be confirmed active in current environment (failures: {failures})"
                        )
            else:
                if not reg.get("kind") or not reg.get("scheduled_at"):
                    gaps.append(
                        f"WakeRegistration {reg_id} missing required fields (kind or scheduled_at); "
                        f"cannot verify as active"
                    )
                else:
                    gaps.append(
                        f"WakeRegistration {reg_id} has no verified_at; "
                        f"registration cannot be confirmed active in current environment"
                    )
        else:
            # Successful verification — reset failure tracking
            reg["liveness_failures"] = 0
            reg.pop("stale_since", None)
            reg["verified_at"] = now()
    return gaps


def decompose_objective_into_subtasks(
    objective: dict[str, Any],
    config: dict[str, Any],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Decompose a multi-file runtime objective into ordered subtasks with rollback checkpoints.

    Each subtask targets a bounded subset of the allowed files, has its own rollback
    checkpoint identifier, and must be executed in order. If any subtask fails, the
    caller should roll back to the subtask's checkpoint before retrying or aborting.

    Returns a list of subtask dicts. For single-file objectives, returns a single-item list.
    Returns an empty list when the objective scope is not 'runtime' or 'rebootstrap'.

    This is a planning utility — it does not modify state. Callers integrate the subtasks
    into the planning stage and persist them under objective['subtasks'].
    """
    scope = objective.get("scope", "")
    if scope not in {"runtime", "rebootstrap"}:
        return []

    allowed_files: list[str] = config.get("executor", {}).get("allowed_files_by_scope", {}).get(scope, [])
    if not allowed_files:
        return []

    # Group files by directory prefix to form natural subtask boundaries.
    # Files in the same directory are co-located changes; files across directories
    # suggest separate independent subtasks with rollback between them.
    from collections import defaultdict
    groups: dict[str, list[str]] = defaultdict(list)
    for f in allowed_files:
        prefix = str(Path(f).parent) if Path(f).parent != Path(".") else "root"
        groups[prefix].append(f)

    if len(groups) <= 1:
        # All files in one directory — single subtask, no decomposition needed.
        return [{
            "id": identifier("subtask"),
            "parent_objective_id": objective.get("id"),
            "index": 0,
            "title": objective.get("title", ""),
            "files": allowed_files,
            "rollback_checkpoint": identifier("checkpoint"),
            "status": "pending",
            "created_at": now(),
        }]

    subtasks = []
    for i, (group_prefix, files) in enumerate(sorted(groups.items())):
        subtasks.append({
            "id": identifier("subtask"),
            "parent_objective_id": objective.get("id"),
            "index": i,
            "title": f"{objective.get('title', '')} [{group_prefix}]",
            "files": sorted(files),
            "rollback_checkpoint": identifier("checkpoint"),
            "status": "pending",
            "created_at": now(),
        })
    return subtasks

