from __future__ import annotations

import json
import os
import sys as _sys
from pathlib import Path
from typing import Any, Callable

from ._common import (
    now,
    identifier,
    atomic_write_json as _atomic_write_json,
    CONFIG_PATH as _CONFIG_PATH,
    input_directory,
    load_config,
    state_path,
    load_state,
    save_state,
    state_lock,
    durable_unlink,
)
from . import rules as rule_ledger_module


def _write_config(path: Path, config: dict) -> None:
    """Write config through cli's namespace so tests can patch cli.atomic_write_json."""
    _cli = _sys.modules.get("urace.cli")
    if _cli is not None:
        _cli.atomic_write_json(path, config)
    else:
        _atomic_write_json(path, config)


def _config_path() -> Path:
    _cli = _sys.modules.get("urace.cli")
    return _cli.CONFIG_PATH if _cli is not None else _CONFIG_PATH


# ---------------------------------------------------------------------------
# Individual input handlers
# Each returns True (or any truthy) to have the outer loop append standard
# "authoritative-input-consumed" evidence, or False to suppress it (handler
# already appended its own evidence and marked the item as processed/consumed).
# ---------------------------------------------------------------------------


def _handle_context(item: dict, payload: dict, config: dict, state: dict) -> bool:
    state.setdefault("context_inputs", []).append({"id": item["id"], "at": item["at"], "origin": "USER_SUPPLIED", **payload})
    state["context_inputs"] = state["context_inputs"][-200:]
    state.setdefault("executor_state", {})["discovery_trigger"] = {"reason": "authoritative context added", "signature": item["id"]}
    return True


def _handle_goal(item: dict, payload: dict, config: dict, state: dict) -> bool:
    objective = {
        "id": identifier("objective"), "title": payload["title"], "reason": payload.get("reason") or "authoritative user goal",
        "success_measure": payload["success_measure"], "outcome_measure_id": payload.get("outcome_measure_id"), "scope": "runtime" if payload.get("target") == "urace" else "documentation",
        "target": payload.get("target", "product"), "priority": int(payload.get("priority", 70)), "status": "planned",
        "expected_value": payload.get("expected_value", 0.7), "estimated_cost": payload.get("estimated_cost", 0.5),
        "risk": payload.get("risk", 0.3), "urgency": payload.get("urgency", 0.5),
        "necessity_evidence": payload.get("necessity_evidence", ""), "lower_impact_route_sufficient": not payload.get("lower_impact_insufficient", False),
        "dependencies": payload.get("dependencies", []), "deadline": payload.get("deadline"), "not_before": payload.get("not_before"),
        "estimate": payload.get("estimate", {}), "estimate_confidence": payload.get("estimate_confidence", "low"),
        "priority_floor": payload.get("priority_floor"), "priority_ceiling": payload.get("priority_ceiling"), "pinned": bool(payload.get("pinned", False)),
        "created_at": item["at"], "updated_at": item["at"], "authority_basis": "authoritative queued user input", "source_input": item["id"],
    }
    if payload.get("source_text"):
        objective["source_text"]=payload["source_text"];objective["semantic_section"]=payload.get("semantic_section")
    if payload.get("update_candidate"):
        objective["update_candidate"] = payload["update_candidate"]
    state["objectives"].append(objective)
    return True


def _handle_source(item: dict, payload: dict, config: dict, state: dict) -> bool:
    source = dict(payload)
    supported = source.get("kind") in {"json_file", "http_json", "github_repository"}
    # Spec §60: CONFIGURED is the initial status; progression: CONFIGURED → AVAILABLE → AUTHENTICATED → AUTHORIZED → OBSERVED
    source["status"] = "CONFIGURED" if supported else "ADAPTER_REQUIRED"
    source["status_history"] = [{"status": source["status"], "at": now()}]
    _src_ts = now(); source["created_at"] = _src_ts; source["updated_at"] = _src_ts; source.setdefault("deleted_at", None)
    sources = state.setdefault("connector_sources", [])
    sources[:] = [entry for entry in sources if entry.get("id") != source.get("id")]
    sources.append(source)
    sources[:] = sources[-100:]
    return True


def _handle_metric(item: dict, payload: dict, config: dict, state: dict) -> bool:
    definitions = state.setdefault("metric_definitions", [])
    definitions[:] = [entry for entry in definitions if entry.get("name") != payload.get("name")]
    definitions.append({"id": item["id"], **payload, "created_at": now(), "updated_at": now()})
    definitions[:] = definitions[-500:]
    source = next((entry for entry in state.setdefault("connector_sources", []) if entry.get("id") == payload.get("source")), None)
    if source is not None:
        source.setdefault("values", {})[payload["name"]] = payload["path"]
    return True


def _handle_vital(item: dict, payload: dict, config: dict, state: dict) -> bool:
    definitions = state.setdefault("vital_definitions", [])
    definitions[:] = [entry for entry in definitions if entry.get("name") != payload.get("name")]
    definitions.append({"id": item["id"], **payload, "created_at": now(), "updated_at": now()})
    definitions[:] = definitions[-500:]
    return True


def _handle_source_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    sources = state.setdefault("connector_sources", [])
    source = next((entry for entry in sources if entry.get("id") == payload["id"]), None)
    if source is None:
        configured = next((entry for entry in config.get("external_metrics", {}).get("sources", []) if entry.get("id") == payload["id"]), None)
        if configured is not None:
            source = {**configured, "status": "CONFIGURED"}
            sources.append(source)
    if source is None:
        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "authoritative-input-rejected", "input": item["id"], "reason": f"connector source not found: {payload['id']}"})
        processed = state.setdefault("processed_input_ids", [])
        processed.append(item["id"])
        return False  # already handled; suppress outer evidence append
    if payload["action"] == "remove":
        source["status"] = "REMOVED"; source["deleted_at"] = now()
    elif payload["action"] == "disable":
        source["status"] = "DISABLED"
    elif payload["action"] == "enable":
        source["status"] = "CONFIGURED" if source.get("kind") in {"json_file", "http_json", "github_repository"} else "ADAPTER_REQUIRED"
    source["updated_at"] = now(); source.setdefault("status_history", []).append({"status": source["status"], "at": source["updated_at"]})
    return True


def _handle_metric_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    state.setdefault("metric_definitions", [])[:] = [entry for entry in state["metric_definitions"] if entry.get("name") != payload["name"]]
    for source in state.setdefault("connector_sources", []):
        source.setdefault("values", {}).pop(payload["name"], None)
    return True


def _handle_vital_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    state.setdefault("vital_definitions", [])[:] = [entry for entry in state["vital_definitions"] if entry.get("name") != payload["name"]]
    return True


def _handle_goal_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    from datetime import datetime, timezone
    goal = next((entry for entry in state.get("objectives", []) if entry.get("id") == payload["id"]), None)
    if goal is None:
        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "authoritative-input-rejected", "input": item["id"], "reason": f"goal not found: {payload['id']}"})
        processed = state.setdefault("processed_input_ids", [])
        processed.append(item["id"])
        return False  # already handled; suppress outer evidence append
    action = payload["action"]
    if action == "cancel" and goal.get("status") in {"planned", "active", "needs_reassessment", "deferred_budget", "deferred", "disabled", "blocked", "awaiting_operator_decision"}:
        goal["status"] = "cancelled"; goal["cancelled_at"] = item["at"]; goal["updated_at"] = item["at"]
    elif action == "disable":
        goal.update({"status": "disabled", "disabled_at": item["at"], "updated_at": item["at"]})
    elif action == "defer":
        goal.update({"status": "deferred", "not_before": payload.get("until"), "deferred_at": item["at"], "updated_at": item["at"]})
    elif action == "resume":
        if goal.get("status") in {"deferred", "disabled", "deferred_budget"}:
            goal.update({"status": "planned", "not_before": None, "resumed_at": item["at"], "updated_at": item["at"]})
    elif action == "resolve-update":
        decision = str(payload.get("decision", "")).strip()
        if goal.get("status") != "awaiting_operator_decision" or not goal.get("update_candidate") or not decision:
            state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "authoritative-input-rejected", "input": item["id"], "reason": "update resolution requires a checkpointed update conflict and a non-empty decision"})
        else:
            goal.update({
                "status": "planned",
                "update_resolution": {"decision": decision, "at": item["at"], "source_input": item["id"]},
                "resumed_at": item["at"],
            })
    elif action == "pin":
        goal.update({"pinned": True, "pinned_at": item["at"]})
    elif action == "unpin":
        goal.update({"pinned": False, "unpinned_at": item["at"]})
    elif action == "prioritize":
        if payload.get("priority") is not None: goal["priority"] = int(payload["priority"])
        if payload.get("floor") is not None: goal["priority_floor"] = int(payload["floor"])
        if payload.get("ceiling") is not None: goal["priority_ceiling"] = int(payload["ceiling"])
        goal["priority_changed_at"] = item["at"]
    elif action == "schedule":
        if payload.get("clear_deadline"): goal["deadline"] = None
        elif payload.get("deadline") is not None: goal["deadline"] = payload["deadline"]
        if payload.get("clear_not_before"):
            goal["not_before"] = None
            if goal.get("status") == "deferred": goal["status"] = "planned"
        elif payload.get("not_before") is not None:
            goal["not_before"] = payload["not_before"]
            try:
                if datetime.fromisoformat(payload["not_before"]).astimezone(timezone.utc) > datetime.now(timezone.utc): goal["status"] = "deferred"
                elif goal.get("status") == "deferred": goal["status"] = "planned"
            except ValueError:
                pass
        if payload.get("estimate_min_hours") is not None or payload.get("estimate_max_hours") is not None:
            estimate = goal.setdefault("estimate", {})
            if payload.get("estimate_min_hours") is not None: estimate["min_hours"] = float(payload["estimate_min_hours"])
            if payload.get("estimate_max_hours") is not None: estimate["max_hours"] = float(payload["estimate_max_hours"])
        if payload.get("estimate_confidence") is not None: goal["estimate_confidence"] = payload["estimate_confidence"]
        if payload.get("dependencies") is not None: goal["dependencies"] = payload["dependencies"]
        goal["schedule_changed_at"] = item["at"]
    elif action == "delete":
        goal.update({"status": "deleted", "deleted_at": item["at"], "tombstone": True, "pinned": False})
    goal.setdefault("control_history", []).append({"input": item["id"], "at": item["at"], **payload})
    goal["control_history"] = goal["control_history"][-50:]
    return True


def _handle_executor_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    settings = config.setdefault("executor", {})
    providers = settings.setdefault("providers", [])
    provider_id = payload.get("id", "codex-primary")
    provider = next((entry for entry in providers if entry.get("id") == provider_id), None)
    if payload["action"] == "retry-policy":
        if provider is None:
            state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "authoritative-input-rejected", "input": item["id"], "reason": f"executor not found: {provider_id}"})
            processed = state.setdefault("processed_input_ids", [])
            processed.append(item["id"])
            return False  # already handled; suppress outer evidence append
        provider.update({"capacity_retry_mode": payload["mode"], "capacity_retry_delay_ms": int(payload["delay_ms"]), "capacity_fallback_seconds": int(payload["fallback_seconds"])})
    elif payload["action"] == "attach":
        if provider is None:
            provider = {"id": provider_id}; providers.append(provider)
        provider.update({
            "enabled": True, "adapter": payload.get("adapter", "codex-cli"),
            "priority": int(payload.get("priority", 100)),
            "capabilities": payload.get("capabilities") or ["discovery", "planning", "mutation", "evaluation", "execution"],
            "capability_priorities": payload.get("capability_priorities") or {},
            "max_calls_per_24h": None if payload.get("max_calls_per_24h", 100) is None else int(payload.get("max_calls_per_24h", 100)),
            "max_calls_per_30d": None if payload.get("max_calls_per_30d", 1000) is None else int(payload.get("max_calls_per_30d", 1000)),
            "capacity_retry_mode": payload.get("mode", "automatic"),
            "capacity_retry_delay_ms": int(payload.get("delay_ms", 60000)),
            "capacity_fallback_seconds": int(payload.get("fallback_seconds", 18000)),
        })
        if payload.get("command"): provider["command"] = payload["command"]
    elif provider is not None:
        provider["enabled"] = False
    settings["enabled"] = any(entry.get("enabled", True) for entry in providers)
    _write_config(_config_path(), config)
    executor_state = state.setdefault("executor_state", {})
    executor_state.setdefault("provider_pool", {}).pop(provider_id, None)
    executor_state["discovery_trigger"] = {"reason": f"executor {payload['action']}: {provider_id}", "signature": item["id"]}
    return True


def _handle_policy_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    if payload["name"] == "self-evolution":
        policy = {"mode": payload["value"], "source": "repository owner", "provenance": f"queued input {item['id']}"}
        config["self_evolution_policy"] = policy
        state["self_evolution_policy"] = policy
    elif payload["name"] == "change-explanations":
        config["change_explanations"] = {"mode": payload["value"], "source": "repository owner", "provenance": f"queued input {item['id']}"}
    elif payload["name"] == "external-metrics":
        config.setdefault("external_metrics", {})["mode"] = payload["value"]
        state.setdefault("external_metric_state", {})["mode"] = payload["value"]
    else:
        config.setdefault("analytics_export", {})["mode"] = payload["value"]
    _write_config(_config_path(), config)
    return True


def _handle_budget_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    settings = config.setdefault("executor", {})
    settings["max_executor_calls_per_24h"] = payload["daily"]
    settings["max_executor_calls_per_30d"] = payload["monthly"]
    _write_config(_config_path(), config)
    return True


def _handle_evaluation_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    evaluation = state.setdefault("evaluation_system", {**config.get("evaluation_system", {}), "change_history": []})
    before = {"version": evaluation.get("version", 1), "minimum_evidence_units": evaluation.get("minimum_evidence_units", 5), "weights": dict(evaluation.get("weights", {}))}
    if payload["action"] == "set-weight":
        evaluation.setdefault("weights", {})[payload["component"]] = payload["value"]
    else:
        evaluation["minimum_evidence_units"] = payload["value"]
    evaluation["version"] = int(evaluation.get("version", 1)) + 1
    evaluation["last_review_at"] = item["at"]
    evaluation["last_assessment"] = "authoritative evaluator configuration change"
    evaluation["change_needed"] = False
    after = {"version": evaluation["version"], "minimum_evidence_units": evaluation.get("minimum_evidence_units", 5), "weights": dict(evaluation.get("weights", {}))}
    evaluation.setdefault("change_history", []).append({"at": item["at"], "input": item["id"], "before": before, "after": after})
    evaluation["change_history"] = evaluation["change_history"][-100:]
    config["evaluation_system"] = {key: after[key] for key in ("version", "minimum_evidence_units", "weights")}
    _write_config(_config_path(), config)
    return True


def _handle_intent_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    ledger = state.setdefault("rule_ledger", rule_ledger_module.new_ledger())
    action = payload.get("action", "add")
    if action == "add":
        rule = rule_ledger_module.make_rule(
            kind=payload.get("rule_kind", "DIRECTIVE"),
            statement=payload["statement"],
            source=item["id"],
            scope=payload.get("scope", "product"),
            derivation=rule_ledger_module.EXPLICIT,
        )
        rule_ledger_module.add_rule(ledger, rule)
        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "rule-added", "rule_id": rule["id"], "rule_kind": rule["kind"], "source_input": item["id"]})
    elif action == "supersede" and payload.get("old_rule_id"):
        new_rule = rule_ledger_module.make_rule(
            kind=payload.get("rule_kind", "DIRECTIVE"),
            statement=payload["statement"],
            source=item["id"],
            scope=payload.get("scope", "product"),
            derivation=rule_ledger_module.EXPLICIT,
        )
        rule_ledger_module.supersede_rule(ledger, payload["old_rule_id"], new_rule)
        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "rule-superseded", "old_rule_id": payload["old_rule_id"], "new_rule_id": new_rule["id"], "source_input": item["id"]})
    elif action == "deactivate" and payload.get("rule_id"):
        rule_ledger_module.deactivate_rule(ledger, payload["rule_id"], reason=f"operator deactivation via input {item['id']}")
        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "rule-deactivated", "rule_id": payload["rule_id"], "source_input": item["id"]})
    return True


def _handle_constraint_control(item: dict, payload: dict, config: dict, state: dict) -> bool:
    ledger = state.setdefault("rule_ledger", rule_ledger_module.new_ledger())
    rule_kind = payload.get("rule_kind", "PROHIBITION")
    if rule_kind not in {"PROHIBITION", "PERMISSION"}:
        rule_kind = "PROHIBITION"
    action = payload.get("action", "add")
    if action == "add":
        rule = rule_ledger_module.make_rule(
            kind=rule_kind,
            statement=payload["statement"],
            source=item["id"],
            scope=payload.get("scope", "product"),
            derivation=rule_ledger_module.EXPLICIT,
        )
        rule_ledger_module.add_rule(ledger, rule)
        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "rule-added", "rule_id": rule["id"], "rule_kind": rule["kind"], "source_input": item["id"]})
    elif action == "deactivate" and payload.get("rule_id"):
        rule_ledger_module.deactivate_rule(ledger, payload["rule_id"], reason=f"operator constraint removal via input {item['id']}")
        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "rule-deactivated", "rule_id": payload["rule_id"], "source_input": item["id"]})
    return True


def _handle_schedule_task(item: dict, payload: dict, config: dict, state: dict) -> bool:
    """AP18 — schedule a durable task via inbox input."""
    task = dict(payload.get("task", {}))
    if not task.get("id"):
        task["id"] = identifier("task")
    if not task.get("status"):
        task["status"] = "ACTIVE"
    task["created_by"] = task.get("created_by", "USER")
    from urace import primitives as _p
    try:
        _p.validate_scheduled_task(task)
    except ValueError as e:
        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "scheduled-task-rejected", "reason": str(e), "source_input": item.get("id")})
        return False
    state.setdefault("scheduled_tasks", []).append(task)
    state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "scheduled-task-registered", "task_id": task["id"], "task_name": task.get("name"), "source_input": item.get("id")})
    return True


def _handle_evidence(item: dict, payload: dict, config: dict, state: dict) -> None:
    ev = {
        "id": identifier("evidence"),
        "at": now(),
        "kind": payload.get("kind", "operator-submitted"),
        "summary": payload.get("summary"),
        "detail": payload.get("detail"),
        "source": payload.get("source"),
        "source_input": item.get("id"),
    }
    state.setdefault("evidence", []).append(ev)


_INPUT_HANDLERS: dict[str, Callable] = {
    "context": _handle_context,
    "goal": _handle_goal,
    "source": _handle_source,
    "metric": _handle_metric,
    "vital": _handle_vital,
    "evidence": _handle_evidence,
    "source_control": _handle_source_control,
    "metric_control": _handle_metric_control,
    "vital_control": _handle_vital_control,
    "goal_control": _handle_goal_control,
    "executor_control": _handle_executor_control,
    "policy_control": _handle_policy_control,
    "budget_control": _handle_budget_control,
    "evaluation_control": _handle_evaluation_control,
    "intent_control": _handle_intent_control,
    "constraint_control": _handle_constraint_control,
    "schedule-task": _handle_schedule_task,
}


def consume_inputs(config: dict[str, Any], state: dict[str, Any]) -> list[Path]:
    processed = state.setdefault("processed_input_ids", [])
    consumed = []
    # Load all inputs first, then sort by at timestamp for §62c FIFO ordering contract.
    # Single-read: loading during glob avoids a second read just for the sort key.
    pending_inputs: list[tuple[str, Path, dict]] = []
    for path in input_directory(config).glob("*.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            pending_inputs.append((item.get("at", str(path)), path, item))
        except (OSError, json.JSONDecodeError) as _parse_err:
            path.replace(path.with_suffix(".rejected"))
            state.setdefault("evidence", []).append({
                "id": identifier("evidence"), "at": now(),
                "kind": "authoritative-input-rejected",
                "source_input": None, "rejected_at": now(),
                "reason": f"malformed inbox file {path.name}: {type(_parse_err).__name__}",
            })
    # AP14 §62i priority-tier contract: Tier 0 (CRITICAL) before Tier 1 (STANDARD) before Tier 2 (OPPORTUNISTIC).
    # Within each tier, FIFO by `at` is strict. Tier 0 is hardcoded to control+pause/stop; other Tier 0
    # self-assignments are demoted to Tier 1 with an integrity gap (inbox-priority-tier-violation).
    _HARDCODED_TIER0_KINDS = {"control"}
    _HARDCODED_TIER0_ACTIONS = {"pause", "stop"}

    def _effective_tier(item: dict) -> int:
        declared = item.get("priority_tier", 1)
        kind = item.get("kind", "")
        action = item.get("payload", {}).get("action", "")
        is_hardcoded_tier0 = kind in _HARDCODED_TIER0_KINDS and action in _HARDCODED_TIER0_ACTIONS
        if declared == 0 and not is_hardcoded_tier0:
            state.setdefault("integrity_gaps", []).append({
                "id": identifier("igap"), "at": now(),
                "kind": "inbox-priority-tier-violation", "severity": "WARNING",
                "input_id": item.get("id"), "declared_tier": 0, "active": True,
            })
            return 1
        if is_hardcoded_tier0:
            return 0
        return max(0, min(2, int(declared) if isinstance(declared, int) else 1))

    pending_inputs.sort(key=lambda x: (_effective_tier(x[2]), x[0]))
    for _at, path, item in pending_inputs:
        if item.get("id") in processed:
            consumed.append(path)
            continue
        payload = item.get("payload", {})
        kind = item.get("kind")
        handler = _INPUT_HANDLERS.get(kind)
        if handler is None:
            state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "authoritative-input-rejected", "input": item.get("id"), "reason": f"unsupported queued input kind: {kind}"})
            if item.get("id"):
                processed.append(item["id"])
            consumed.append(path)
            continue
        result = handler(item, payload, config, state)
        if result is not False:
            state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "authoritative-input-consumed", "input": item["id"], "source_input": item["id"], "input_kind": kind})
            processed.append(item["id"])
            processed[:] = processed[-1000:]
        consumed.append(path)
    return consumed


def queue_input(config: dict[str, Any], kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    item = {"id": identifier("input"), "at": now(), "kind": kind, "payload": payload, "status": "QUEUED"}
    directory = input_directory(config)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    _atomic_write_json(directory / f"{item['at'].replace(':', '-')}-{item['id']}.json", item)
    return item


def cleanup_consumed_inputs(paths: list[Path]) -> None:
    for path in paths:
        durable_unlink(path)


def apply_pending_inputs() -> int:
    """Apply the shared control inbox at a safe boundary for any long-running owner."""
    config = load_config(); path = state_path(config)
    with state_lock(path):
        state = load_state(config)
        consumed = consume_inputs(config, state)
        if consumed:
            state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "live-control-boundary", "applied_inputs": len(consumed), "outcome": "APPLIED_WITHOUT_OWNER_RESTART"})
            save_state(config, state)
            cleanup_consumed_inputs(consumed)
        return len(consumed)
