from __future__ import annotations
from ._common import nullable_limit

import datetime
import hashlib
import json
import os
import re
from datetime import datetime as _datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ._common import now, load_config, transaction_path, ROOT
from . import scope_priority


def document_metrics(config: dict[str, Any]) -> dict[str, float]:
    text = "\n".join((ROOT / item).read_text(encoding="utf-8") for item in config["product_files"] if (ROOT / item).exists())
    normative = len(re.findall(r"\bMUST(?: NOT)?\b", text))
    tests = len(re.findall(r"^\*\*[A-Z]{1,2} —", text, re.MULTILINE))
    todos = len(re.findall(r"\b(?:TODO|TBD|FIXME)\b", text, re.IGNORECASE))
    return {
        "normative_rules": float(normative),
        "behavioral_tests": float(tests),
        "unresolved_markers": float(todos),
    }


def compare(direction: str, current: float, reference: float) -> str:
    delta = current - reference
    if delta == 0:
        return "stable"
    improved = delta > 0 if direction == "nondecreasing" else delta < 0
    return "improved" if improved else "regressed"


def _has_capability_expansion_authority(state: dict[str, Any], objective: dict[str, Any]) -> bool:
    """Return True if a DecisionRecord explicitly authorizes capability scope expansion
    for this objective (§2571 Capability Envelope Gate).
    """
    obj_id = objective.get("id", "")
    obj_title = objective.get("title", "")
    for dr in state.get("decision_records", []):
        if dr.get("kind") != "AUTHORITY_GRANT":
            continue
        authorized = dr.get("authorized_objective_ids", [])
        if obj_id and obj_id in authorized:
            return True
        subj = dr.get("subject", "")
        if obj_id and obj_id in subj:
            return True
        if obj_title and obj_title in subj:
            return True
        if dr.get("capability_expansion_authorized"):
            return True
    return False


def objective_is_eligible(state: dict[str, Any], objective: dict[str, Any]) -> bool:
    # §2571 Capability Envelope Gate: CAPABILITY_DEFINING objectives require explicit
    # authority at CAPABLE or OPTIMIZED maturity.
    if objective.get("kind") == "CAPABILITY_DEFINING":
        assessments = state.get("sweet_spot_assessments", [])
        maturity = assessments[-1].get("maturity_level") if assessments else None
        if maturity in {"CAPABLE", "OPTIMIZED"}:
            if not _has_capability_expansion_authority(state, objective):
                gaps = state.setdefault("integrity_gaps", [])
                objective_id = objective.get('id', 'unknown')
                base_id = f"igap-cap-envelope-{objective_id}"
                if any(not gap.get("resolved")
                       and gap.get("kind") == "capability-envelope-breach"
                       and (gap.get("objective") == objective_id or gap.get("id") == base_id)
                       for gap in gaps):
                    return False
                existing_ids = {gap.get("id") for gap in gaps}
                gap_id, recurrence = base_id, 1
                while gap_id in existing_ids:
                    recurrence += 1
                    gap_id = f"{base_id}-{recurrence}"
                gaps.append({
                    "id": gap_id,
                    "objective": objective_id,
                    "kind": "capability-envelope-breach",
                    "severity": "WARNING",
                    "detail": (
                        f"CAPABILITY_DEFINING objective '{objective.get('title', '')}' requires "
                        f"explicit DecisionRecord(kind=AUTHORITY_GRANT) at {maturity} maturity"
                    ),
                    "at": now(),
                    "resolved": False,
                })
                return False
    if objective.get("scope") not in {"runtime", "rebootstrap"}:
        return True
    # §74: NECESSARY_ONLY is the default; DISABLED must be explicit.
    mode = state.get("self_evolution_policy", {}).get("mode", "NECESSARY_ONLY").upper()
    if mode == "CONTINUOUS":
        return True
    if mode == "NECESSARY_ONLY":
        return bool(str(objective.get("necessity_evidence", "")).strip()) and not objective.get("lower_impact_route_sufficient", True)
    return False


def goal_is_schedulable(state: dict[str, Any], objective: dict[str, Any]) -> bool:
    if objective.get("status") not in {"planned", "policy_blocked", "needs_reassessment", "deferred_budget"}:
        return False
    if objective.get("not_before"):
        try:
            if _datetime.fromisoformat(objective["not_before"]).astimezone(timezone.utc) > _datetime.now(timezone.utc):
                return False
        except ValueError:
            return False
    by_id = {item.get("id"): item for item in state.get("objectives", [])}
    if any(by_id.get(dependency, {}).get("status") != "completed" for dependency in objective.get("dependencies", [])):
        return False
    return objective_is_eligible(state, objective)


def objective_score(objective: dict[str, Any]) -> float:
    return objective_score_breakdown(objective)["total"]


def objective_score_breakdown(objective: dict[str, Any]) -> dict[str, float]:
    declared = float(objective.get("priority", 50))
    if objective.get("priority_floor") is not None:
        declared = max(declared, float(objective["priority_floor"]))
    if objective.get("priority_ceiling") is not None:
        declared = min(declared, float(objective["priority_ceiling"]))
    deadline_pressure = 0.0
    if objective.get("deadline"):
        try:
            days = (_datetime.fromisoformat(objective["deadline"]).astimezone(timezone.utc) - _datetime.now(timezone.utc)).total_seconds() / 86400
            deadline_pressure = 15.0 if days <= 0 else max(0.0, 15.0 * (1.0 - min(days, 30.0) / 30.0))
        except ValueError:
            pass
    waiting_age = 0.0
    if objective.get("created_at"):
        try:
            days_waiting = max(0.0, (_datetime.now(timezone.utc) - _datetime.fromisoformat(objective["created_at"]).astimezone(timezone.utc)).total_seconds() / 86400)
            waiting_age = min(5.0, days_waiting / 30.0)
        except ValueError:
            pass
    components = {
        "priority": declared,
        "pinned_attention": 20.0 if objective.get("pinned") else 0.0,
        "expected_value": 20 * float(objective.get("expected_value", 0.5)),
        "urgency": 10 * float(objective.get("urgency", 0.5)),
        "deadline_pressure": deadline_pressure,
        "dependency_unblocking": float(objective.get("dependency_unblocking_adjustment", 0.0)),
        "starvation_correction": waiting_age,
        "confidence": 5 * float(objective.get("confidence", 0.5)),
        "estimated_cost_penalty": -10 * float(objective.get("estimated_cost", 0.5)),
        "risk_penalty": -10 * float(objective.get("risk", 0.5)),
        "scope_attention": float(objective.get("scope_attention_adjustment", 0.0)),
        "feedback_adjustment": float(objective.get("feedback_priority_adjustment", 0.0)),
    }
    return {**components, "total": sum(components.values())}


def goal_portfolio(state: dict[str, Any]) -> dict[str, Any]:
    """Build an advisory, explainable forecast; canonical scheduling remains the lifecycle loop."""
    objectives = state.get("objectives", [])
    dependent_counts = {item.get("id"): 0 for item in objectives}
    for item in objectives:
        for dependency in item.get("dependencies", []):
            if dependency in dependent_counts: dependent_counts[dependency] += 1
    for item in objectives:
        item["dependency_unblocking_adjustment"] = min(10.0, 2.0 * dependent_counts.get(item.get("id"), 0))
    ranked = sorted(objectives, key=lambda item: (goal_is_schedulable(state, item), objective_score(item)), reverse=True)
    cursor_min = cursor_max = _datetime.now(timezone.utc)
    rows = []
    by_id = {item.get("id"): item for item in objectives}
    for rank, goal in enumerate(ranked, 1):
        dependencies = goal.get("dependencies", [])
        blockers = [item for item in dependencies if by_id.get(item, {}).get("status") != "completed"]
        eligible = goal_is_schedulable(state, goal)
        estimate = goal.get("estimate") or {}
        low = max(0.0, float(estimate.get("min_hours", 0.0)))
        high = max(low, float(estimate.get("max_hours", low)))
        confidence = goal.get("estimate_confidence", "low")
        estimate_basis = "declared"
        if high == 0:
            comparable = []
            for prior in objectives:
                if prior.get("status") != "completed" or prior.get("scope") != goal.get("scope") or not prior.get("created_at") or not prior.get("completed_at"): continue
                try: comparable.append(max(0.0, (_datetime.fromisoformat(prior["completed_at"]) - _datetime.fromisoformat(prior["created_at"])).total_seconds() / 3600))
                except ValueError: pass
            if comparable:
                ordered = sorted(comparable); nominal = ordered[len(ordered) // 2]; confidence = "medium"; estimate_basis = "historical completed goals"
            else:
                nominal = max(0.25, 8.0 * float(goal.get("estimated_cost", 0.5))); estimate_basis = "estimated-cost proxy"
            low, high = nominal * 0.5, nominal * 1.5
        earliest = latest = None
        if eligible and high:
            cursor_min += timedelta(hours=low); cursor_max += timedelta(hours=high)
            earliest, latest = cursor_min.isoformat(), cursor_max.isoformat()
        reasons = []
        if goal.get("pinned"): reasons.append("pinned attention")
        if goal.get("deadline"): reasons.append(f"deadline {goal['deadline']}")
        if blockers: reasons.append("waiting for " + ", ".join(blockers))
        if goal.get("not_before"): reasons.append(f"deferred until {goal['not_before']}")
        reasons.append("value, urgency, confidence, cost, risk and scope evidence")
        rows.append({
            "rank": rank, "id": goal.get("id"), "title": goal.get("title"), "status": goal.get("status"),
            "eligible": eligible, "score": objective_score(goal), "score_breakdown": objective_score_breakdown(goal),
            "dependencies": dependencies, "blockers": blockers, "estimate": {"min_hours": low, "max_hours": high, "confidence": confidence, "basis": estimate_basis},
            "forecast": {"earliest": earliest, "latest": latest, "advisory": True}, "priority_reason": "; ".join(reasons),
        })
    from .implementation_sequence import plan
    sequence=plan(objectives,scores={g["id"]:objective_score(g) for g in objectives},eligible={g["id"]:goal_is_schedulable(state,g) for g in objectives})
    from .uncertainty_followup import plan as followups
    from .intent_trace import assessment as trace
    requests=[{"id":g["id"],"title":g.get("title"),"success_measure":g.get("success_measure"),"validation_plan":"Check independent acceptance for the exact goal/source and compare with its declared success measure"} for g in objectives]
    return {"generated_at": now(), "basis": "advisory sequential capacity; recalculated at lifecycle boundaries", "goals": rows,"implementation_sequence":sequence,"request_claim_trace":trace(requests,state.get("implementation_claims",[])),"uncertainty_followups":followups(state.get("implementation_claims",[]))}


def work_evaluations(state: dict[str, Any]) -> dict[str, Any]:
    calls = state.get("executor_state", {}).get("executor_calls", [])
    operations = state.get("operations", [])
    goals = []
    for objective in state.get("objectives", [])[-100:]:
        related_calls = [item for item in calls if item.get("reason") == objective.get("id") or item.get("objective_id") == objective.get("id")]
        goals.append({
            "id": objective.get("id"), "title": objective.get("title"), "target": objective.get("target", "product"),
            "scope": objective.get("scope"), "status": objective.get("status"), "outcome_status": objective.get("outcome_status", "UNVERIFIED"), "score": objective_score(objective), "score_breakdown": objective_score_breakdown(objective),
            "model_calls": len(related_calls), "accepted_changes": sum(item.get("outcome") == "accepted" for item in related_calls),
            "metric_effect": {"improved": sum(int(item.get("observed_metric_effect", {}).get("improved", 0)) for item in related_calls), "regressed": sum(int(item.get("observed_metric_effect", {}).get("regressed", 0)) for item in related_calls)},
            "attribution": "UNATTRIBUTED_COST_OUTCOME_ASSOCIATION",
        })
    contexts = []
    for context in state.get("context_inputs", [])[-100:]:
        related = [item for item in calls if item.get("trigger_signature") == context.get("id")]
        contexts.append({"id": context.get("id"), "source": context.get("source"), "discovery_calls": len(related), "outcomes": [item.get("outcome") for item in related], "attribution": "UNATTRIBUTED_INPUT_OUTCOME_ASSOCIATION"})
    action_groups = {}
    for operation in operations[-100:]:
        scope = operation.get("scope", "unknown")
        group = "urace_self_evolution" if scope in {"runtime", "rebootstrap"} else "product_evolution"
        summary = action_groups.setdefault(group, {"attempted": 0, "accepted": 0, "rejected_or_no_effect": 0})
        summary["attempted"] += 1
        if operation.get("status") == "ACCEPTED":
            summary["accepted"] += 1
        elif operation.get("status") in {"REJECTED_ROLLED_BACK", "OBSERVED_NO_EFFECT"}:
            summary["rejected_or_no_effect"] += 1
    return {"goals": goals, "contexts": contexts, "actions": action_groups, "attribution": "ASSOCIATIONS_REQUIRE_CAUSAL_REVIEW"}


def context_view(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "governing": {"intent": state.get("intent"), "authority": state.get("authority"), "constraints": state.get("constraints", [])},
        "user_supplied": [{**item, "origin": item.get("origin", "USER_SUPPLIED")} for item in state.get("context_inputs", [])],
        "urace_derived": {
            "objectives": state.get("objectives", [])[-100:],
            "reasoning_hypotheses": state.get("reasoning_memory", [])[-100:],
            "external_observations": state.get("external_metric_state", {}).get("latest", [])[-100:],
        },
        "provenance_note": "Derived context is Evidence or a hypothesis; it does not replace user Intent or create Authority.",
    }


def resource_accounting(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    from .resource_usage import summary
    native_usage = summary(config, state)
    executor = state.get("executor_state", {})
    calls = executor.get("executor_calls", [])
    reported_tokens = native_usage['known_tokens']
    reported_cost = native_usage['reported_cost_usd']
    if reported_cost:
        cost = {"unit": "provider_currency", "value": reported_cost, "source": "PROVIDER_REPORTED"}
    elif reported_tokens:
        cost = {"unit": "tokens", "value": reported_tokens, "source": "EXECUTOR_REPORTED"}
    else:
        cost = {"unit": "model_calls", "value": len(calls), "source": "CALL_COUNT_PROXY"}
    limits = config.get("executor", {})
    current = _datetime.now(timezone.utc).timestamp()
    recent_24h = sum(current - _datetime.fromisoformat(item["at"]).timestamp() < 86400 for item in calls)
    recent_30d = sum(current - _datetime.fromisoformat(item["at"]).timestamp() < 2592000 for item in calls)
    runtime = state.get("runtime_efficiency", {})
    probe_count = int(runtime.get("availability_probes", 0))
    readiness_transitions = sum(item.get("kind") == "executor-availability" for item in state.get("evidence", []))
    context_links = {item.get("trigger_signature") for item in calls if item.get("trigger_signature")}
    unused_context = sum(item.get("id") not in context_links for item in state.get("context_inputs", []))
    stale_goals = 0
    for objective in state.get("objectives", []):
        created = objective.get("created_at")
        if objective.get("status") in {"planned", "policy_blocked", "deferred_budget", "needs_reassessment"} and created:
            stale_goals += current - _datetime.fromisoformat(created).timestamp() >= 2592000
    unproductive = sum(item.get("outcome") in {"failed", "no_action", "ineligible", "no_effect", "concurrent_change"} for item in calls)
    streak = int(executor.get("unproductive_discovery_streak", 0))
    exhausted_threshold = int(limits.get("discovery_yield_exhausted_threshold", 5))
    discovery_exhausted = streak >= exhausted_threshold
    discovery_yield_30d = sum(item.get("outcome") in {"objective_created", "accepted"} for item in calls) / len(calls) if calls else None
    sinks = {
        "unproductive_model_calls": unproductive,
        "unused_context_inputs": unused_context,
        "stale_open_goals_30d": stale_goals,
        "executor_failures": len(executor.get("failures", [])),
        "systematic_failure_active": bool(executor.get("systematic_failure_cooldown_until") and _datetime.now(timezone.utc).timestamp() < _datetime.fromisoformat(executor["systematic_failure_cooldown_until"]).timestamp()),
        "external_failure_streak": int(state.get("external_metric_state", {}).get("failure_streak", 0)),
    }
    # Discovery loop is a required named resource-sink category evaluated independently.
    discovery_loop_sink = {
        "unproductive_streak": streak,
        "exhausted_threshold": exhausted_threshold,
        "confirmed_active_sink": discovery_exhausted,
        "productive_yield_30d": discovery_yield_30d,
        "ceiling_interval_seconds": float(limits.get("max_discovery_interval_seconds", 4838400)),
        "defer_reason": executor.get("discovery_defer_reason"),
        "qualifying_reset_conditions": ["new inbox input applied", "net-new evidence record", "intent or product-file change", "operator force-discovery"],
    }
    return {
        "native_usage": native_usage,
        "executor_cost": cost,
        "estimated_executor_capacity": {
            "available": executor.get("available"),
            "remaining_calls_24h": (None if nullable_limit(limits,"max_executor_calls_per_24h",2) is None else max(0,nullable_limit(limits,"max_executor_calls_per_24h",2)-recent_24h)),
            "remaining_calls_30d": (None if nullable_limit(limits,"max_executor_calls_per_30d",12) is None else max(0,nullable_limit(limits,"max_executor_calls_per_30d",12)-recent_30d)),
            "basis": "configured call ceilings and readiness; null remaining calls means no configured call ceiling, not provider credit balance",
        },
        "deterministic_resources": {
            "cycles": int(runtime.get("cycles", 0)),
            "availability_probes": probe_count,
            "availability_probe_seconds": float(runtime.get("availability_probe_seconds", 0)),
            "availability_checks_suppressed": int(runtime.get("availability_checks_suppressed", 0)),
            "external_collections": int(runtime.get("external_collections", 0)),
            "durable_writes": int(runtime.get("durable_writes", 0)),
            "suppressed_writes": int(runtime.get("suppressed_writes", 0)),
        },
        "availability_probe_efficiency": {
            "readiness_transitions_observed": readiness_transitions,
            "transitions_per_probe": readiness_transitions / probe_count if probe_count else None,
            "probe_seconds_per_transition": float(runtime.get("availability_probe_seconds", 0)) / readiness_transitions if probe_count and readiness_transitions else None,
            "measurement_coverage": "CURRENT_COUNTERS" if probe_count else "HISTORICAL_PROBE_COUNT_UNAVAILABLE",
            "interpretation": "operational resource-versus-readiness proxy; not Executor price, usage, balance, or credit",
        },
        "resource_sink_indicators": {**sinks, "review_required": any(sinks.values())},
        "discovery_loop_yield_sink": discovery_loop_sink,
        "non_combinable_dimensions": True,
    }


def executor_efficiency_vital(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Return bounded cost/outcome evidence without asserting causal attribution."""
    current = _datetime.now(timezone.utc).timestamp()
    calls = state.get("executor_state", {}).get("executor_calls", [])
    productive = {"objective_created", "accepted"}

    def window(seconds: int) -> dict[str, Any]:
        selected = [item for item in calls if current - _datetime.fromisoformat(item["at"]).timestamp() < seconds]
        productive_calls = sum(item.get("outcome") in productive for item in selected)
        accepted = sum(item.get("outcome") == "accepted" for item in selected)
        improved = sum(int(item.get("observed_metric_effect", {}).get("improved", 0)) for item in selected)
        regressed = sum(int(item.get("observed_metric_effect", {}).get("regressed", 0)) for item in selected)
        count = len(selected)
        return {
            "model_calls": count,
            "productive_calls": productive_calls,
            "productive_yield": productive_calls / count if count else None,
            "accepted_changes": accepted,
            "calls_per_accepted_change": count / accepted if accepted else None,
            "observed_metric_improvements": improved,
            "observed_metric_regressions": regressed,
            "attribution": "UNATTRIBUTED_COST_OUTCOME_ASSOCIATION",
        }

    executor_state = state.get("executor_state", {})
    streak = int(executor_state.get("unproductive_discovery_streak", 0))
    exhausted_threshold = int(config.get("executor", {}).get("discovery_yield_exhausted_threshold", 5))
    exhausted = streak >= exhausted_threshold
    yield_entry: dict[str, Any] = {
        "unproductive_streak": streak,
        "exhausted_threshold": exhausted_threshold,
        "discovery_yield_exhausted": exhausted,
        "defer_reason": executor_state.get("discovery_defer_reason"),
    }
    if exhausted:
        yield_entry["qualifying_reset_conditions"] = ["new inbox input applied", "net-new evidence record", "intent or product-file change", "operator force-discovery"]
    return {
        "unit": "model_calls",
        "short_run_24h": window(86400),
        "long_run_30d": window(2592000),
        "discovery_loop_yield": yield_entry,
    }


def evolution_vital(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    settings = state.get("evaluation_system", config.get("evaluation_system", {}))
    weights = settings.get("weights", {})
    current = _datetime.now(timezone.utc).timestamp()

    def recent(items: list[dict[str, Any]], seconds: int, field: str) -> list[dict[str, Any]]:
        selected = []
        for item in items:
            value = item.get(field)
            if value and current - _datetime.fromisoformat(value).timestamp() < seconds:
                selected.append(item)
        return selected

    def window(seconds: int) -> dict[str, Any]:
        calls = recent(state.get("executor_state", {}).get("executor_calls", []), seconds, "at")
        objectives = recent(state.get("objectives", []), seconds, "created_at")
        executions = [item for item in calls if item.get("stage") == "execution"]
        effects = [item.get("observed_metric_effect", {}) for item in executions if item.get("observed_metric_effect")]
        improved = sum(int(item.get("improved", 0)) for item in effects)
        regressed = sum(int(item.get("regressed", 0)) for item in effects)
        components = {}
        if calls:
            components["productive_call_yield"] = sum(item.get("outcome") in {"objective_created", "accepted"} for item in calls) / len(calls)
        if executions:
            components["execution_acceptance"] = sum(item.get("outcome") == "accepted" for item in executions) / len(executions)
        if improved + regressed:
            components["regression_safety"] = improved / (improved + regressed)
        if objectives:
            components["goal_completion"] = sum(item.get("status") == "completed" for item in objectives) / len(objectives)
        applicable_weight = sum(float(weights.get(name, 0)) for name in components)
        score = 100 * sum(value * float(weights.get(name, 0)) for name, value in components.items()) / applicable_weight if applicable_weight else None
        evidence_units = len(calls) + len(objectives) + improved + regressed
        minimum = max(1, int(settings.get("minimum_evidence_units", 5)))
        days = seconds / 86400
        accepted = sum(item.get("outcome") == "accepted" for item in executions)
        return {
            "diagnostic_score": score, "score_scale": "0..100", "components": components,
            "confidence": min(1.0, evidence_units / minimum), "evidence_units": evidence_units,
            "accepted_change_rate_per_day": accepted / days,
            "metric_improvement_rate_per_day": improved / days,
            "metric_regression_rate_per_day": regressed / days,
            "model_calls": len(calls), "attribution": "UNATTRIBUTED_DIAGNOSTIC_ASSOCIATION",
        }

    return {"system_version": settings.get("version", 1), "short_run_24h": window(86400), "long_run_30d": window(2592000), "change_needed": settings.get("change_needed", False), "last_assessment": settings.get("last_assessment")}


def render(state: dict[str, Any]) -> str:
    profile = state["progress_profiles"][0]
    lines = [
        f"Product: {load_config()['product']}",
        f"Lifecycle: {state['lifecycle_state']}",
        f"Intent: {state['intent']['purpose']}",
        f"State version: {state['state_version']}",
        f"Current objective: {state['current_objective'] or 'none'}",
        "Progress:",
    ]
    for name, measure in profile["measures"].items():
        lines.append(f"  {name}: baseline={measure['baseline']:g} current={measure['current']:g} target={measure['target']:g}")
    executor_state = state.get("executor_state", {})
    lines.extend([
        f"Next follow-up: {profile['next_follow_up']}",
        f"Executor: {load_config().get('executor', {}).get('kind', 'deterministic')} ({'enabled' if load_config().get('executor', {}).get('enabled') else 'disabled'})",
        f"Executor available: {executor_state.get('available')}",
        f"Executor pool:" + ("".join(f" {pid}(available={ps.get('available')} authenticated={ps.get('authenticated')})" for pid, ps in executor_state.get("provider_pool", {}).items() if isinstance(ps, dict)) or " none"),
        f"Last availability check: {executor_state.get('last_availability_check') or 'never'}",
        f"Executor failures: {len(executor_state.get('failures', []))}",
        f"Executor calls retained (30d): {len(executor_state.get('executor_calls', []))}/{load_config().get('executor', {}).get('max_executor_calls_per_30d', 12)}",
        f"Executor budget: {executor_state.get('discovery_budget_status', 'WITHIN_BUDGET')}",
        f"Unproductive discovery streak: {executor_state.get('unproductive_discovery_streak', 0)}/{load_config().get('executor', {}).get('discovery_yield_exhausted_threshold', 5)} (exhausted at threshold)",
        *([f"DISCOVERY_YIELD_EXHAUSTED: streak reached threshold; next discovery requires a qualifying reset event (new goal, new evidence, intent change, or force-discovery)"] if int(executor_state.get("unproductive_discovery_streak", 0)) >= int(load_config().get("executor", {}).get("discovery_yield_exhausted_threshold", 5)) else []),
        *([ f"Discovery defer reason: {executor_state['discovery_defer_reason']}"] if executor_state.get("discovery_defer_reason") else []),
        f"Self-evolution policy: {state.get('self_evolution_policy', {}).get('mode', 'DISABLED')}",
        f"External metrics: {state.get('external_metric_state', {}).get('mode', 'DISABLED')} ({len(state.get('external_metric_state', {}).get('latest', []))} sources observed)",
        f"Reasoning memory: {len(state.get('reasoning_memory', []))} structured patterns",
        f"Unresolved effects: {len(state['unresolved_effects'])}",
    ])
    # technique gate summary
    if "technique_application_log" in state:
        log = state["technique_application_log"]
        recent = log[-12:] if len(log) > 12 else log
        summary = {r["technique"]: r["verdict"] for r in recent}
        lines.append(f"  technique-gate: {summary}")
    _eval_sys = state.get("evaluation_system", {})
    _last_assessment = str(_eval_sys.get("last_assessment", "")).lower()
    _evidence_count = len(state.get("evidence", []))
    _min_units = int(_eval_sys.get("minimum_evidence_units", 5))
    _evidence_blocked = "insufficient" in _last_assessment or _evidence_count < _min_units
    if _evidence_blocked:
        _shortfall = max(0, _min_units - _evidence_count)
        lines.extend([
            "Evidence-blocked: True",
            f"  missing-dimension: evidence_quality",
            f"  shortfall: {_shortfall} evidence units below minimum ({_min_units})",
            f"  advancement-blocked: True",
            f"  earliest-qualifying-condition: accumulate {_shortfall} additional evidence units or lower evaluation minimum",
        ])
    return "\n".join(lines)


def vitals_snapshot(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    from . import value_trajectory
    profile = state["progress_profiles"][0]
    transaction_active = transaction_path(config).exists()
    actual = {name: measure["current"] for name, measure in profile["measures"].items()} if transaction_active else document_metrics(config)
    progress = {}
    for name, measure in profile["measures"].items():
        value = actual.get(name, measure["current"])
        reference = measure.get("previous") if measure.get("previous") is not None else measure["baseline"]
        progress[name] = {
            "baseline": measure["baseline"], "previous": measure.get("previous"),
            "current": value, "target": measure["target"], "direction": measure["direction"],
            "trend": compare(measure["direction"], value, reference),
        }
    executor_state = state.get("executor_state", {})
    current = _datetime.now(timezone.utc).timestamp()
    calls_30d = [item for item in executor_state.get("executor_calls", []) if current - _datetime.fromisoformat(item["at"]).timestamp() < 2592000]
    calls_24h = [item for item in calls_30d if current - _datetime.fromisoformat(item["at"]).timestamp() < 86400]
    settings = config.get("executor", {})
    external = state.get("external_metric_state", {})
    runtime_efficiency = state.get("runtime_efficiency", {})
    efficiency_cycles = int(runtime_efficiency.get("cycles", 0))
    suppressed_writes = int(runtime_efficiency.get("suppressed_writes", 0))
    observed_values = {observation.get("source", "unknown"): observation.get("values", {}) for observation in external.get("latest", [])}
    flattened_values = {name: value for values in observed_values.values() for name, value in values.items()}
    custom_vitals = []
    for definition in state.get("vital_definitions", []):
        numerator = flattened_values.get(definition.get("numerator"))
        denominator_name = definition.get("denominator")
        denominator = flattened_values.get(denominator_name) if denominator_name else None
        if numerator is None:
            value, status = None, "AWAITING_METRIC"
        elif denominator_name and (denominator is None or denominator == 0):
            value, status = None, "AWAITING_VALID_DENOMINATOR"
        else:
            value, status = (numerator / denominator if denominator_name else numerator), "OBSERVED"
        custom_vitals.append({**definition, "value": value, "status": status, "attribution": "UNATTRIBUTED_OBSERVATION"})
    evolution = evolution_vital(config, state)
    long_evolution = evolution["long_run_30d"]
    progress_known = bool(progress)
    progress_score = (sum(1 for item in progress.values() if item["trend"] == "improved") + 0.5 * sum(1 for item in progress.values() if item["trend"] == "stable")) / len(progress) if progress else None
    safety_score = 0.0 if state["lifecycle_state"] == "BLOCKED" or state.get("unresolved_effects") else 1.0
    efficiency_score = long_evolution.get("diagnostic_score")
    dimensions = {
        "outcome_progress": {"score": progress_score, "confidence": 0.7 if progress_known else 0.0, "source": "declared progress measures"},
        "evidence_quality": {"score": min(1.0, long_evolution.get("evidence_units", 0) / max(1, config.get("evaluation_system", {}).get("minimum_evidence_units", 5))), "confidence": long_evolution.get("confidence", 0), "source": "30-day evolution evidence"},
        "safety_and_continuity": {"score": safety_score, "confidence": 1.0, "source": "blockers and unresolved effects"},
        "resource_efficiency": {"score": efficiency_score, "confidence": long_evolution.get("confidence", 0), "source": "30-day qualified evolution diagnostic"},
    }
    available = [item for item in dimensions.values() if item["score"] is not None]
    coverage = len(available) / len(dimensions)
    vetoes = []
    if safety_score == 0: vetoes.append("failed safety or continuity condition")
    qualified = coverage == 1 and min(item["confidence"] for item in available) >= 0.5 and not vetoes
    system_scorecard = {"dimensions": dimensions, "coverage": coverage, "vetoes": vetoes, "overall_diagnostic_score": (sum(item["score"] for item in available) / len(available)) if qualified else None, "overall_status": "QUALIFIED" if qualified else "WITHHELD", "meaning": "decision aid only; never Authority, acceptance, causal proof, or a substitute for a failed guardrail"}
    repair_registry = state.get("system_repair_registry", {})
    repair_statuses: dict[str, int] = {}
    for entry in repair_registry.values():
        status = str(entry.get("status", "UNKNOWN")); repair_statuses[status] = repair_statuses.get(status, 0) + 1
    return {
        "type": "urace_vitals", "at": now(), "lifecycle": state["lifecycle_state"],
        "state_version": state["state_version"], "progress_metrics": progress,
        "progress_metric_source": "durable_state_during_transaction" if transaction_active else "live_product",
        "executor_credit_usage": {
            "unit": "model_calls", "calls_24h": len(calls_24h),
            "limit_24h": settings.get("max_executor_calls_per_24h", 2),
            "calls_30d": len(calls_30d), "limit_30d": settings.get("max_executor_calls_per_30d", 12),
            "status": executor_state.get("discovery_budget_status", "WITHIN_BUDGET"),
            "unproductive_streak": executor_state.get("unproductive_discovery_streak", 0),
            "discovery_yield_exhausted_threshold": int(settings.get("discovery_yield_exhausted_threshold", 5)),
            "discovery_yield_exhausted": int(executor_state.get("unproductive_discovery_streak", 0)) >= int(settings.get("discovery_yield_exhausted_threshold", 5)),
            "discovery_productive_yield_30d": (sum(item.get("outcome") in {"objective_created", "accepted"} for item in calls_30d) / len(calls_30d)) if calls_30d else None,
            "discovery_productive_yield_24h": (sum(item.get("outcome") in {"objective_created", "accepted"} for item in calls_24h) / len(calls_24h)) if calls_24h else None,
            "discovery_defer_reason": executor_state.get("discovery_defer_reason"),
            "transport_attempts_30d": sum(int(item.get("transport_attempts", 1)) for item in calls_30d),
            "capacity_deferred_logical_calls_30d": sum(item.get("outcome") == "deferred_provider_capacity" for item in calls_30d),
            "capacity_status": executor_state.get("capacity_status", "AVAILABLE_OR_UNKNOWN"),
            "capacity_retry_at": executor_state.get("capacity_retry_at"),
        },
        "executor_pool": executor_state.get("provider_pool", {}),
        "executor_efficiency": executor_efficiency_vital(config, state),
        "evolution": evolution,
        "system_scorecard": system_scorecard,
        "work_evaluations": work_evaluations(state),
        "resource_accounting": resource_accounting(config, state),
        "runtime_efficiency": {
            "cycles": efficiency_cycles,
            "durable_writes": int(runtime_efficiency.get("durable_writes", 0)),
            "suppressed_writes": suppressed_writes,
            "write_suppression_ratio": suppressed_writes / efficiency_cycles if efficiency_cycles else None,
            "state_bytes": _state_path_size(config),
            "availability_failure_streak": executor_state.get("availability_failure_streak", 0),
            "external_failure_streak": external.get("failure_streak", 0),
            "external_next_collection_at": external.get("next_collection_at"),
        },
        "controller_recovery": {"registered_identities": len(repair_registry), "statuses": repair_statuses},
        "scope_priorities": state.get("scope_priority_system", {}),
        "external_evidence": {
            "mode": external.get("mode", "DISABLED"), "last_collection": external.get("last_collection"),
            "observed_sources": len(external.get("latest", [])), "values": observed_values,
            "metric_definitions": state.get("metric_definitions", []), "vital_definitions": state.get("vital_definitions", []),
            "custom_vitals": custom_vitals,
            "connectors": list(({item["id"]: {**item, "status": "ACTIVE"} for item in config.get("external_metrics", {}).get("sources", [])} | {item["id"]: item for item in state.get("connector_sources", [])}).values()),
            "errors": external.get("errors", []),
        },
        "health": {
            "recorded_blockers": len(state.get("blockers", [])), "lifecycle_blocked": state["lifecycle_state"] == "BLOCKED",
            "unresolved_effects": len(state.get("unresolved_effects", [])),
            "pending_validation": len(state.get("pending_validation", [])),
            "executor_available": executor_state.get("available"), "next_follow_up": profile["next_follow_up"],
        },
        "policies": {
            "self_evolution": state.get("self_evolution_policy", {}).get("mode", "DISABLED"),
            "authority_boundary": {
                "delegated": (state.get("authority") or {}).get("delegated", []),
                "reserved": (state.get("authority") or {}).get("reserved", []),
            },
            "destination_anchor": {
                "digest": state.get("destination_anchor", {}).get("digest"),
                "purpose": state.get("destination_anchor", {}).get("purpose"),
                "established_at": state.get("destination_anchor", {}).get("established_at"),
            },
        },
        "value_trajectory": {
            "acceleration": state.get("value_trajectory", {}).get("acceleration"),
            "cumulative_value": state.get("value_trajectory", {}).get("cumulative_value", 0.0),
            "peak_velocity": state.get("value_trajectory", {}).get("peak_velocity", 0.0),
            "checkpoints_recorded": len(state.get("value_trajectory", {}).get("checkpoints", [])),
            "self_correction": value_trajectory.self_correction_needed(state),
        },
        "objective_outcomes": _objective_outcomes(state),
    }


def _objective_outcomes(state: dict[str, Any]) -> dict[str, Any]:
    """Aggregate objective completion, stall, and failure rates."""
    by_status: dict[str, int] = {}
    stalled_30d = 0
    now_ts = _datetime.now(timezone.utc).timestamp()
    open_statuses = {"planned", "policy_blocked", "deferred_budget", "needs_reassessment"}
    for obj in state.get("objectives", []):
        s = obj.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
        if s in open_statuses:
            created = obj.get("created_at")
            if created:
                try:
                    age = now_ts - _datetime.fromisoformat(created).astimezone(timezone.utc).timestamp()
                    if age > 30 * 86400:
                        stalled_30d += 1
                except ValueError:
                    pass
    total = sum(by_status.values())
    completed = by_status.get("completed", 0)
    return {
        "total": total,
        "by_status": by_status,
        "completion_rate": completed / total if total else None,
        "stalled_30d": stalled_30d,
        "stall_rate": stalled_30d / total if total else None,
    }


def _state_path_size(config: dict[str, Any]) -> int:
    """Return state file size without importing cli.py."""
    from ._common import state_path
    sp = state_path(config)
    return sp.stat().st_size if sp.exists() else 0


def render_vitals(vitals: dict[str, Any]) -> str:
    usage = vitals["executor_credit_usage"]
    short = vitals["executor_efficiency"]["short_run_24h"]
    long = vitals["executor_efficiency"]["long_run_30d"]
    runtime = vitals["runtime_efficiency"]
    evolution_short = vitals["evolution"]["short_run_24h"]
    evolution_long = vitals["evolution"]["long_run_30d"]
    lines = [
        f"URACE core vitals at {vitals['at']}",
        f"Lifecycle: {vitals['lifecycle']} (state {vitals['state_version']})",
        "Progress metrics:",
    ]
    scope_system = vitals.get("scope_priorities", {})
    if scope_system.get("scopes"):
        lines.append("Dynamic planning attention:")
        for name, record in scope_system["scopes"].items():
            lines.append(f"  {name}: weight={record['normalized_weight']} ranking-multiplier={record['ranking_multiplier']} backlog={record['backlog']} age-days={record['days_since_accepted_change']}")
    for name, metric in vitals["progress_metrics"].items():
        lines.append(f"  {name}: {metric['current']:g} trend={metric['trend']} baseline={metric['baseline']:g} target={metric['target']:g}")
    if vitals["external_evidence"].get("custom_vitals"):
        lines.append("Connected vitals:")
        for vital in vitals["external_evidence"]["custom_vitals"]:
            display_status = "BASELINE_PENDING" if vital["status"] == "AWAITING_METRIC" else vital["status"]
            lines.append(f"  {vital['name']}: value={vital['value']} status={display_status} window={vital['window']} attribution={vital['attribution']}")
    lines.extend([
        f"System scorecard: overall={vitals['system_scorecard']['overall_diagnostic_score']} status={vitals['system_scorecard']['overall_status']} coverage={vitals['system_scorecard']['coverage']} vetoes={vitals['system_scorecard']['vetoes']}",
        f"Executor credit usage: day={usage['calls_24h']}/{usage['limit_24h']} month={usage['calls_30d']}/{usage['limit_30d']} unit={usage['unit']} status={usage['status']} transport-attempts={usage['transport_attempts_30d']} capacity={usage['capacity_status']} retry={usage['capacity_retry_at']}",
        f"Short-run efficiency (24h): productive-yield={short['productive_yield']} accepted={short['accepted_changes']} calls-per-accepted={short['calls_per_accepted_change']}",
        f"Long-run efficiency (30d): productive-yield={long['productive_yield']} accepted={long['accepted_changes']} calls-per-accepted={long['calls_per_accepted_change']} metric-improved={long['observed_metric_improvements']} metric-regressed={long['observed_metric_regressions']}",
        f"Attribution: {long['attribution']}",
        f"Evolution vital: short-score={evolution_short['diagnostic_score']} short-confidence={evolution_short['confidence']} long-score={evolution_long['diagnostic_score']} long-confidence={evolution_long['confidence']} accepted/day={evolution_long['accepted_change_rate_per_day']} attribution={evolution_long['attribution']}",
        f"Work evaluations: goals={len(vitals['work_evaluations']['goals'])} contexts={len(vitals['work_evaluations']['contexts'])} action-groups={len(vitals['work_evaluations']['actions'])}",
        f"Resource accounting: executor={vitals['resource_accounting']['executor_cost']['value']} {vitals['resource_accounting']['executor_cost']['unit']} source={vitals['resource_accounting']['executor_cost']['source']} remaining-capacity-day={vitals['resource_accounting']['estimated_executor_capacity']['remaining_calls_24h']} availability={vitals['resource_accounting']['estimated_executor_capacity']['available']}",
        f"Availability-probe efficiency: {vitals['resource_accounting']['availability_probe_efficiency']}",
        f"Resource sinks: {vitals['resource_accounting']['resource_sink_indicators']}",
        f"Discovery-loop yield: streak={vitals['executor_efficiency']['discovery_loop_yield']['unproductive_streak']}/{vitals['executor_efficiency']['discovery_loop_yield']['exhausted_threshold']} exhausted={vitals['executor_efficiency']['discovery_loop_yield']['discovery_yield_exhausted']} productive-yield-24h={vitals['executor_credit_usage']['discovery_productive_yield_24h']} productive-yield-30d={vitals['executor_credit_usage']['discovery_productive_yield_30d']}" + (f" defer-reason={vitals['executor_efficiency']['discovery_loop_yield']['defer_reason']}" if vitals['executor_efficiency']['discovery_loop_yield'].get('defer_reason') else "") + (f" reset-conditions={vitals['executor_efficiency']['discovery_loop_yield'].get('qualifying_reset_conditions', [])}" if vitals['executor_efficiency']['discovery_loop_yield']['discovery_yield_exhausted'] else ""),
        f"Runtime efficiency: cycles={runtime['cycles']} durable-writes={runtime['durable_writes']} suppressed-writes={runtime['suppressed_writes']} suppression-ratio={runtime['write_suppression_ratio']} state-bytes={runtime['state_bytes']}",
        f"Controller recovery: identities={vitals['controller_recovery']['registered_identities']} statuses={vitals['controller_recovery']['statuses']}",
        f"External evidence: mode={vitals['external_evidence']['mode']} observed={vitals['external_evidence']['observed_sources']} errors={len(vitals['external_evidence']['errors'])}" + ("".join(f" | {e['source']} last-known-good={e['last_known_good'].get('at','?')}" for e in vitals['external_evidence']['errors'] if e.get('last_known_good')) if vitals['external_evidence']['errors'] else ""),
        f"Health: lifecycle-blocked={vitals['health']['lifecycle_blocked']} recorded-blockers={vitals['health']['recorded_blockers']} unresolved-effects={vitals['health']['unresolved_effects']} executor-available={vitals['health']['executor_available']}",
        f"Next follow-up: {vitals['health']['next_follow_up']}",
        f"Objective outcomes: total={vitals['objective_outcomes']['total']} completion-rate={vitals['objective_outcomes']['completion_rate']} stalled-30d={vitals['objective_outcomes']['stalled_30d']} stall-rate={vitals['objective_outcomes']['stall_rate']} by-status={vitals['objective_outcomes']['by_status']}",
    ])
    return "\n".join(lines)


def command_catalog() -> dict[str, list[dict[str, str]]]:
    return {
        "immediate": [
            {"command": "help [operation]", "purpose": "inspect installed operations and contextual usage without an Executor call"},
            {"command": "init", "purpose": "initialize durable lifecycle state"},
            {"command": "check", "purpose": "inspect complete lifecycle state"},
            {"command": "vitals", "purpose": "inspect focused metrics, cost, and health"},
            {"command": "report status|export", "purpose": "inspect analytics capabilities or export portable CSV/HTML and optional XLSX"},
            {"command": "configuration auto-goals status|enable|disable; configuration auto-goals replenish status|enable|disable", "purpose": "control one auto-goals feature and its replenishment sub-setting"},
            {"command": "configuration effort status|low|medium|high [--executor ID]", "purpose": "URACE resource effort; inherit --executor ID removes an override"},
            {"command": "commands", "purpose": "show this command contract"},
            {"command": "inbox list", "purpose": "inspect durable pending inputs"},
            {"command": "context list", "purpose": "inspect governing, user-supplied, and URACE-derived context"},
            {"command": "executor status", "purpose": "inspect configured Executor readiness"},
            {"command": "source|metric|vital list; goal list|inspect|forecast", "purpose": "inspect configuration, explain goal priority, and view advisory schedules"},
            {"command": "policy list|budget show", "purpose": "inspect autonomy policy and Executor limits"},
            {"command": "evaluation show", "purpose": "inspect the versioned evolution evaluator and current results"},
            {"command": "update download|explain", "purpose": "obtain and inspect a hash-identified specification candidate without changing the accepted implementation"},
            {"command": "portfolio ...", "purpose": "run the optional isolated-worktree portfolio helper"},
            {"command": "plan", "purpose": "assess and plan one cycle without execution"},
            {"command": "auto", "purpose": "run bounded or persistent lifecycle execution"},
            {"command": "why [change-id]", "purpose": "trace the decision record and governing rules for a change"},
            {"command": "rules list|show [rule-id]", "purpose": "inspect the active Rule Ledger"},
            {"command": "crc show|regenerate", "purpose": "inspect or regenerate the Cognitive Resume Context"},
            {"command": "compact|decompact [field]", "purpose": "compact governed list fields at a safe lifecycle boundary or restore from archive"},
            {"command": "pause|resume", "purpose": "pause lifecycle execution or resume from PAUSED state"},
            {"command": "intent list|add|supersede|deactivate", "purpose": "inspect or modify the Rule Ledger intent entries"},
            {"command": "constraint list|add|deactivate", "purpose": "inspect or modify the Rule Ledger constraint entries"},
            {"command": "amend [record-id] --reason <text>", "purpose": "amend a compacted archive record with a non-destructive provenance annotation"},
        ],
        "durable_input": [
            {"command": "add-context|add-goal|add-source|add-metric|add-vital", "purpose": "queue authoritative input"},
            {"command": "source enable|disable|remove", "purpose": "queue connector control"},
            {"command": "metric|vital remove", "purpose": "queue observability removal"},
            {"command": "goal prioritize|schedule|pin|unpin|defer|resume|disable|cancel|delete", "purpose": "queue safe-boundary goal management; delete retains an audit tombstone"},
            {"command": "executor attach|detach|retry-policy", "purpose": "queue Executor configuration or per-Executor capacity scheduling"},
            {"command": "policy set|budget set", "purpose": "queue autonomy policy or Executor limit changes"},
            {"command": "evaluation set-weight|set-minimum", "purpose": "queue an audited evaluator revision"},
            {"command": "update apply", "purpose": "queue a hash-bound specification migration through isolated validation and rollback"},
        ],
    }


def top_level_help() -> str:
    return """URACE commands

  urace "<freeform-text>"             interpret intent using an available Executor
  status [SUBJECT]                    read-only status; defaults to runtime
  configuration [SETTING]            persistent settings, models and resource effort
  change                  list changes or explain one accepted change

Lifecycle:       init, auto, plan, pause, resume, onboard
Work and input:  add, goal, context, source, metric, vital, inbox, feedback
Execution:      executor, product, fleet, portfolio, data
Governance:     rules, intent, constraint, govern, blocker
Investigation:  change, decision, explain, why, trace, evidence
Maintenance:    update, derive, compact, decompact, amend, crc
Integration:    trial, report, resource, schema, api, commands, help

Status subjects:
  runtime, vitals, executors, resources, products, fleet, data, quality,
  compliance, milestones, blockers, integrity, onboarding, configuration,
  inbox, goals, evaluation

Configuration settings:
  auto-goals, effort, executor, self-evolution, change-explanations,
  external-metrics, analytics-export, executor-budget,
  evaluation-minimum, evaluation-weight

Use `urace help <command> [subcommand ...]` or `<command> --help`.
`urace commands` lists installed commands by concern; `urace api commands`
exports typed machine discovery. Help spends no Executor credit.
Compatibility names (including check, vitals, autonomous, add-goal,
add-context, self-evolution, policy and budget) remain accepted.
Freeform inference is fallible; unresolved sections remain explicit."""



def render_cycle(state: dict[str, Any], outcome: dict[str, Any], index: int, json_mode: bool, verbose: bool = False) -> str:
    profile = state["progress_profiles"][0]
    executor_state = state.get("executor_state", {})
    metrics = {}
    for name, measure in profile["measures"].items():
        reference = measure.get("previous") if measure.get("previous") is not None else measure["baseline"]
        metrics[name] = {
            "baseline": measure["baseline"], "previous": measure.get("previous"),
            "current": measure["current"], "target": measure["target"],
            "trend": compare(measure["direction"], measure["current"], reference),
        }
    objective = outcome.get("objective") if isinstance(outcome.get("objective"), dict) else None
    plan = outcome.get("plan") if isinstance(outcome.get("plan"), dict) else None
    execution = outcome.get("execution") if isinstance(outcome.get("execution"), dict) else None
    decision_trace = {
        "decision": objective.get("title") if objective else outcome["outcome"],
        "basis": objective.get("reason") if objective else outcome.get("reason", "cycle assessment"),
        "authority": "delegated lifecycle navigation" if objective else "no consequential action selected",
        "planned_steps": plan.get("steps", []) if plan else [],
        "validation": execution.get("status") if execution else ("not applicable" if not objective else "pending"),
        "changed_files": execution.get("changed_files", []) if execution else [],
        "alternatives": outcome.get("candidate_comparison", []),
    }
    budget_now = _datetime.now(timezone.utc).timestamp()
    budget_calls_30d = [item for item in executor_state.get("executor_calls", []) if budget_now - _datetime.fromisoformat(item["at"]).timestamp() < 2592000]
    budget_calls_24h = [item for item in budget_calls_30d if budget_now - _datetime.fromisoformat(item["at"]).timestamp() < 86400]
    event = {
        "type": "autonomous_cycle", "cycle": index, "at": now(),
        "lifecycle": state["lifecycle_state"], "outcome": outcome,
        "metrics": metrics, "metric_system": state.get("metric_system", {}),
        "executor_available": executor_state.get("available"),
        "executor_credit_budget": {"calls_24h": len(budget_calls_24h), "limit_24h": load_config().get("executor", {}).get("max_executor_calls_per_24h", 2), "calls_30d": len(budget_calls_30d), "limit_30d": load_config().get("executor", {}).get("max_executor_calls_per_30d", 12), "unproductive_streak": executor_state.get("unproductive_discovery_streak", 0), "status": executor_state.get("discovery_budget_status", "WITHIN_BUDGET")},
        "executor_efficiency_vital": executor_efficiency_vital(load_config(), state),
        "evolution_vital": evolution_vital(load_config(), state),
        "resource_accounting": resource_accounting(load_config(), state),
        "self_evolution_policy": state.get("self_evolution_policy", {"mode": "DISABLED"}),
        "external_metrics": state.get("external_metric_state", {"mode": "DISABLED", "latest": [], "errors": []}),
        "reasoning_memory_summary": {"entries": len(state.get("reasoning_memory", [])), "recurring_signatures": sum(1 for item in state.get("pattern_memory", {}).values() if item.get("recurring"))},
        "decision_trace": decision_trace,
        "next_follow_up": profile["next_follow_up"], "state_version": state["state_version"],
        "recovery_manifest": executor_state.get("recovery_manifest"),
        "progress_vector": executor_state.get("progress_vector"),
        "progress_stagnant_cycles": executor_state.get("progress_stagnant_cycles", 0),
    }
    if json_mode:
        return json.dumps(event, sort_keys=True)
    summary = objective.get("title") if objective else (outcome.get("reason") or outcome["outcome"])
    lines = [f"[{event['at']}] cycle={index} lifecycle={event['lifecycle']} outcome={outcome['outcome']}", f"  activity: {summary}"]
    if not verbose:
        if decision_trace["changed_files"]: lines.append(f"  changed: {', '.join(decision_trace['changed_files'])}")
        lines.append(f"  validation: {decision_trace['validation']} | next: {event['next_follow_up']}")
        budget_status = event["executor_credit_budget"]["status"]
        if budget_status != "WITHIN_BUDGET":
            defer_reason = executor_state.get("discovery_defer_reason") or budget_status
            lines.append(f"  discovery-deferred: {defer_reason}")
        if event["progress_vector"] is not None:
            lines.append(f"  progress: {event['progress_vector']:.1%}")
        if event["recovery_manifest"]:
            rm = event["recovery_manifest"]
            lines.append(
                f"  recovery-pending: manifest={rm.get('manifest_id')} "
                f"cause={rm.get('emission_cause')} "
                f"progress={rm.get('progress_at_emit')} "
                f"delta={rm.get('goal_delta', 'unknown')}"
            )
        return "\n".join(lines)
    lines.extend([
        f"  decision-basis: {decision_trace['basis']}",
        f"  authority: {decision_trace['authority']}",
        f"  candidate-comparison: {decision_trace['alternatives']}",
        f"  validation: {decision_trace['validation']}",
    ])
    if decision_trace["planned_steps"]:
        lines.append(f"  plan: {' -> '.join(decision_trace['planned_steps'])}")
    if decision_trace["changed_files"]:
        lines.append(f"  changed-files: {', '.join(decision_trace['changed_files'])}")
    budget_status = event["executor_credit_budget"]["status"]
    if budget_status != "WITHIN_BUDGET":
        defer_reason = executor_state.get("discovery_defer_reason") or budget_status
        lines.append(f"  discovery-deferred: {defer_reason}")
    for name, metric in metrics.items():
        lines.append(f"  metric {name}: {metric['current']:g} trend={metric['trend']} baseline={metric['baseline']:g} target={metric['target']:g}")
    lines.extend([
        f"  metric-system: v{event['metric_system'].get('version', 1)} change-needed={event['metric_system'].get('change_needed')}",
        f"  executor-available: {event['executor_available']}",
        f"  executor-credit-budget: day={event['executor_credit_budget']['calls_24h']}/{event['executor_credit_budget']['limit_24h']} month={event['executor_credit_budget']['calls_30d']}/{event['executor_credit_budget']['limit_30d']} unproductive-streak={event['executor_credit_budget']['unproductive_streak']} status={event['executor_credit_budget']['status']}",
        f"  executor-efficiency-vital: short-yield={event['executor_efficiency_vital']['short_run_24h']['productive_yield']} long-yield={event['executor_efficiency_vital']['long_run_30d']['productive_yield']} long-calls-per-accepted={event['executor_efficiency_vital']['long_run_30d']['calls_per_accepted_change']} attribution={event['executor_efficiency_vital']['long_run_30d']['attribution']}",
        f"  evolution-vital: short-score={event['evolution_vital']['short_run_24h']['diagnostic_score']} short-confidence={event['evolution_vital']['short_run_24h']['confidence']} long-score={event['evolution_vital']['long_run_30d']['diagnostic_score']} long-confidence={event['evolution_vital']['long_run_30d']['confidence']}",
        f"  resources: executor={event['resource_accounting']['executor_cost']['value']} {event['resource_accounting']['executor_cost']['unit']} source={event['resource_accounting']['executor_cost']['source']} remaining-day={event['resource_accounting']['estimated_executor_capacity']['remaining_calls_24h']} probes={event['resource_accounting']['deterministic_resources']['availability_probes']} collections={event['resource_accounting']['deterministic_resources']['external_collections']}",
        f"  resource-sinks: {event['resource_accounting']['resource_sink_indicators']}",
        f"  self-evolution-policy: {event['self_evolution_policy'].get('mode', 'DISABLED')}",
        f"  external-metrics: {event['external_metrics'].get('mode', 'DISABLED')} observed={len(event['external_metrics'].get('latest', []))} errors={len(event['external_metrics'].get('errors', []))}",
        f"  reasoning-memory: entries={event['reasoning_memory_summary']['entries']} recurring-signatures={event['reasoning_memory_summary']['recurring_signatures']}",
        f"  progress-vector: {event['progress_vector']} stagnant-cycles={event['progress_stagnant_cycles']}",
        f"  next-follow-up: {event['next_follow_up']}",
    ])
    if event["recovery_manifest"]:
        rm = event["recovery_manifest"]
        lines.extend([
            f"  recovery-manifest: id={rm.get('manifest_id')} cause={rm.get('emission_cause')} emitted={rm.get('emitted_at')}",
            f"    last-safe-state={rm.get('last_safe_state')} commit={rm.get('last_safe_commit')}",
            f"    progress-at-emit={rm.get('progress_at_emit')} delta={rm.get('goal_delta')}",
            f"    recommended-tier={rm.get('recommended_tier')} mode={rm.get('execution_mode')}",
        ])
    return "\n".join(lines)
