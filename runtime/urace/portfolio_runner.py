#!/usr/bin/env python3
"""Portfolio workflow runner, planner lifecycle, and preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from .portfolio_storage import (
    ROOT, DATA, CONTROL_INBOX, PORTFOLIO_ROOT, INTEGRITY_KEY,
    load, save, now, canonical, bounded_text, name as _name,
    verify_authenticated_archive, integrity_key,
)
from .portfolio_product import (
    COHORT_POLICIES, COHORT_POLICY_ALIASES, ACCEPTED_STATE_SOURCES,
    effective_cohort_policy, effective_accepted_state_source,
    resolve_accepted_product_identity, reconcile_accepted_product,
    accepted_product_commit, snapshot_current_product,
    cmd_policy, cmd_policy_status, cmd_accepted_state_source,
    cmd_accepted_state_source_status, cmd_init, cmd_spawn, cmd_cohort,
    variant, git,
)
from .portfolio_executor import (
    BUILTIN_ADAPTER, PLAN_SCHEMA, EVALUATION_SCHEMA,
    EVALUATOR_MANIPULATION_PATTERNS, MAX_CANDIDATE_CHANGED_LINES,
    MAX_CANDIDATE_NET_ADDITIONS, ISOLATION_PROBE_ATTEMPTS,
    StageBudgetExhausted, AcceptedProductReconciled,
    is_executor_unavailable, controller_fault_descriptor,
    attempt_controller_auto_repair, routed_portfolio_executor,
    executor_progress, automation_env, isolated_candidate_command,
    run_isolated_command, run_isolation_probe, run_automation_stage,
    record_candidate_stage_failure, record_candidate_stage_incomplete,
    wait_for_executor_capacity, archive_old_variants, scope_priorities,
    builtin_plan, builtin_mutate, builtin_evaluate, workflow_command,
)

_DEFAULT_PATH = os.environ.get("PATH", "/usr/bin:/bin" if sys.platform != "win32" else "C:\\Windows\\System32;C:\\Windows")
_TMP_HOME = __import__("tempfile").gettempdir()


def _get_root():
    """Get ROOT from portfolio hub so patch.object(portfolio, 'ROOT', ...) tests work."""
    try:
        import urace.portfolio as _hub
        return _hub.ROOT
    except (ImportError, AttributeError):
        return ROOT


def _get_data():
    """Get DATA from portfolio hub so patch.object(portfolio, 'DATA', ...) tests work."""
    try:
        import urace.portfolio as _hub
        return _hub.DATA
    except (ImportError, AttributeError):
        return DATA


def _get_portfolio_root():
    """Get PORTFOLIO_ROOT from portfolio hub so patch.object works."""
    try:
        import urace.portfolio as _hub
        return _hub.PORTFOLIO_ROOT
    except (ImportError, AttributeError):
        return PORTFOLIO_ROOT


def _get_integrity_key():
    """Get INTEGRITY_KEY from portfolio hub so patch.object works."""
    try:
        import urace.portfolio as _hub
        return _hub.INTEGRITY_KEY
    except (ImportError, AttributeError):
        return INTEGRITY_KEY

PROTECTED_WORKFLOW_FIELDS = (
    "cohort_size", "total_resource_budget", "resource_unit",
    "executor_invocation_budget_per_generation", "planner_invocation_budget_per_generation",
    "plan_command", "mutate_command", "evaluate_command", "evaluation_protocol_version",
    "provider_internal_hard_caps", "external_effects",
    "candidate_isolation", "candidate_network", "candidate_environment_allowlist",
    "analytics_native_workbook",
)

AUTO_MIN_OBSERVED_GENERATIONS = 2
AUTO_MIN_METRIC_IMPROVEMENT = 0.5
AUTO_CLOSE_MARGIN = 1.0
AUTO_MAX_CLOSE_GENERATIONS = 2
AUTO_SUMMARY_RETENTION = 50

LIVE_CONTROL_ACTIONS = {"stop", "record", "review", "agora-propose", "agora-vote", "agora-decide", "agora-confirm-system", "lesson", "policy", "accepted-state-source"}


class CohortPolicyPaused(Exception):
    pass


def normalize_run_options(args: argparse.Namespace, allow_parallel: bool = False) -> None:
    """Accept bounded-run options before or after the variant/cohort positional."""
    command = list(args.command)
    while command:
        option = command[0]
        if option == "--":
            command.pop(0)
            break
        if option == "--timeout" and len(command) >= 2:
            args.timeout = float(command[1]); del command[:2]
            continue
        if allow_parallel and option == "--max-parallel" and len(command) >= 2:
            args.max_parallel = int(command[1]); del command[:2]
            continue
        break
    if args.timeout <= 0 or (allow_parallel and args.max_parallel is not None and args.max_parallel < 1):
        raise SystemExit("timeout and maximum parallelism must be positive")
    args.command = command


def cmd_run_cohort(args: argparse.Namespace) -> None:
    import concurrent.futures
    normalize_run_options(args, allow_parallel=True)
    data = load()
    items = [item for item in data["variants"].values() if item.get("cohort") == args.cohort and item["status"] not in {"STOPPED", "NOT_SELECTED", "REJECTED_GUARDRAIL"}]
    if not items:
        raise SystemExit("No runnable variants found for that cohort")
    if not args.command:
        raise SystemExit("Provide a command after --")
    parallel = min(args.max_parallel or 1, len(items))

    def run_one(index_item: tuple[int, dict]) -> tuple[str, dict]:
        index, item = index_item
        environment = os.environ.copy()
        environment.update({
            "URACE_VARIANT_NAME": item["name"], "URACE_VARIANT_INDEX": str(index),
            "URACE_COHORT": args.cohort, "URACE_RESOURCE_BUDGET": str(item["resource_budget"]["allocated"]),
            "URACE_RESOURCE_UNIT": item["resource_budget"]["unit"], "URACE_PORT_OFFSET": str(index - 1),
        })
        started = time.monotonic()
        timeout = args.timeout
        if item["resource_budget"]["unit"] == "wall_seconds":
            timeout = min(timeout, float(item["resource_budget"]["allocated"]))
        try:
            isolation = {"candidate_isolation": "bubblewrap-no-host-filesystem", "candidate_network": False, "candidate_environment_allowlist": []}
            command = isolated_candidate_command(Path(item["path"]), args.command, isolation, environment)
            result = subprocess.run(command, cwd=_get_root(), env={"PATH": _DEFAULT_PATH}, text=True, capture_output=True, timeout=timeout)
            outcome = {"at": now(), "command": args.command, "seconds": time.monotonic() - started, "effective_timeout": timeout, "exit_code": result.returncode, "stdout_tail": result.stdout[-2000:], "stderr_tail": result.stderr[-2000:], "cohort": args.cohort, "allocated_budget": item["resource_budget"], "budget_enforcement": "WALL_SECONDS_AND_TIMEOUT" if item["resource_budget"]["unit"] == "wall_seconds" else "TIMEOUT_ONLY; OTHER UNITS REQUIRE AN ADAPTER"}
        except subprocess.TimeoutExpired as error:
            outcome = {"at": now(), "command": args.command, "seconds": time.monotonic() - started, "effective_timeout": timeout, "exit_code": None, "timeout": True, "stdout_tail": (error.stdout or "")[-2000:], "stderr_tail": (error.stderr or "")[-2000:], "cohort": args.cohort, "allocated_budget": item["resource_budget"], "budget_enforcement": "WALL_SECONDS_AND_TIMEOUT" if item["resource_budget"]["unit"] == "wall_seconds" else "TIMEOUT_ONLY; OTHER UNITS REQUIRE AN ADAPTER"}
        except OSError as error:
            outcome = {"at": now(), "command": args.command, "seconds": time.monotonic() - started, "effective_timeout": timeout, "exit_code": None, "launch_error": str(error), "stdout_tail": "", "stderr_tail": "", "cohort": args.cohort, "allocated_budget": item["resource_budget"], "budget_enforcement": "WALL_SECONDS_AND_TIMEOUT" if item["resource_budget"]["unit"] == "wall_seconds" else "TIMEOUT_ONLY; OTHER UNITS REQUIRE AN ADAPTER"}
        return item["name"], outcome

    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
        results = dict(executor.map(run_one, enumerate(items, 1)))
    data = load()
    for variant_name, outcome in results.items():
        item = variant(data, variant_name); item["runs"].append(outcome); item["runs"] = item["runs"][-50:]
    data["events"].append({"at": now(), "kind": "COHORT_RUN_COMPLETED", "cohort": args.cohort, "parallelism": parallel, "timeout_each": args.timeout, "results": {key: value.get("exit_code") for key, value in results.items()}}); save(data)
    print(json.dumps(results, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    normalize_run_options(args)
    data = load(); item = variant(data, args.variant)
    if item["status"] == "STOPPED":
        raise SystemExit("Stopped variants cannot run")
    if not args.command:
        raise SystemExit("Provide a command after --")
    started = time.monotonic(); item["status"] = "RUNNING"; save(data)
    try:
        isolation = {"candidate_isolation": "bubblewrap-no-host-filesystem", "candidate_network": False, "candidate_environment_allowlist": []}
        environment = {"PATH": _DEFAULT_PATH, "LANG": os.environ.get("LANG", "C.UTF-8"), "HOME": _TMP_HOME, "URACE_VARIANT_NAME": item["name"]}
        command = isolated_candidate_command(Path(item["path"]), args.command, isolation, environment)
        result = subprocess.run(command, cwd=_get_root(), env={"PATH": _DEFAULT_PATH}, text=True, capture_output=True, timeout=args.timeout)
        outcome = {"at": now(), "command": args.command, "seconds": time.monotonic() - started, "exit_code": result.returncode, "stdout_tail": result.stdout[-2000:], "stderr_tail": result.stderr[-2000:]}
    except subprocess.TimeoutExpired as error:
        outcome = {"at": now(), "command": args.command, "seconds": time.monotonic() - started, "exit_code": None, "timeout": True, "stdout_tail": (error.stdout or "")[-2000:], "stderr_tail": (error.stderr or "")[-2000:]}
    data = load(); item = variant(data, args.variant); item["runs"].append(outcome); item["runs"] = item["runs"][-50:]; item["status"] = "CREATED"; save(data)
    print(json.dumps(outcome, indent=2)); raise SystemExit(0 if outcome.get("exit_code") == 0 else 1)


def parse_cycle_limit(value: str) -> int | None:
    if value.lower() in {"infinity", "infinite", "forever", "inf"}:
        return None
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("cycles must be non-negative or infinity")
    return result


def queue_portfolio_control(argv: list[str]) -> str:
    CONTROL_INBOX.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(CONTROL_INBOX, 0o700)
    control_id = f"control-{hashlib.sha256((now() + json.dumps(argv)).encode()).hexdigest()[:16]}"
    payload = {"id": control_id, "at": now(), "argv": argv, "status": "QUEUED"}
    target = CONTROL_INBOX / f"{payload['at'].replace(':', '-')}-{control_id}.json"
    temporary = target.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    return control_id


def consume_portfolio_controls() -> int:
    # Import parser lazily to avoid circular import
    from . import portfolio as _portfolio_hub
    applied = 0
    for path in sorted(CONTROL_INBOX.glob("*.json")):
        payload = {}
        original_load = original_save = None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            arguments = _portfolio_hub.parser().parse_args(payload["argv"])
            if arguments.action not in LIVE_CONTROL_ACTIONS:
                raise ValueError("operation is not eligible for live queuing")
            data = load()
            if payload["id"] in data.setdefault("processed_control_ids", []):
                path.unlink(missing_ok=True); continue
            original_load, original_save = _portfolio_hub.load, _portfolio_hub.save
            _portfolio_hub.load = lambda _d=data: _d
            _portfolio_hub.save = lambda _data: None
            try:
                arguments.function(arguments)
            finally:
                _portfolio_hub.load, _portfolio_hub.save = original_load, original_save
            disposition = "APPLIED"
        except BaseException as error:
            if original_load is not None:
                _portfolio_hub.load, _portfolio_hub.save = original_load, original_save
            data = load(); disposition = "REJECTED"
            data.setdefault("events", []).append({"at": now(), "kind": "LIVE_CONTROL_REJECTED", "control": payload.get("id", path.name), "error": f"{type(error).__name__}: {str(error)[:300]}"})
        control_id = payload.get("id", path.name)
        data.setdefault("processed_control_ids", []).append(control_id); data["processed_control_ids"] = data["processed_control_ids"][-1000:]
        data.setdefault("events", []).append({"at": now(), "kind": "LIVE_CONTROL_PROCESSED", "control": control_id, "disposition": disposition})
        save(data); path.unlink(missing_ok=True); applied += disposition == "APPLIED"
    return applied


def sync_live_controls() -> None:
    try:
        from urace.cli import apply_pending_inputs
        apply_pending_inputs()
    except ModuleNotFoundError:
        pass
    except RuntimeError as error:
        if "state is locked by live process" not in str(error) and "URACE is not initialized" not in str(error):
            raise
    consume_portfolio_controls()


def pause_if_cohort_disabled(data: dict) -> bool:
    if effective_cohort_policy(data) != "disabled":
        return False
    automation = data.setdefault("automation", {})
    automation.update({"status": "PAUSED_POLICY", "policy_pause_at": now()})
    save(data)
    print(f"Portfolio cohort policy is disabled; checkpointed at phase {automation.get('phase', 'IDLE')}. Set `portfolio policy enabled` or `portfolio policy auto` to resume.", flush=True)
    return True


def autonomous_safe_boundary(workflow: dict) -> None:
    """Apply live controls and freshness before starting another indivisible stage."""
    sync_live_controls()
    data = load()
    if pause_if_cohort_disabled(data):
        raise CohortPolicyPaused
    before = data.get("_loaded_digest")
    if reconcile_accepted_product(data, workflow):
        save(data)
        print("Portfolio reconciled a newer accepted Product state; the stale cohort was retained as evidence and superseded.", flush=True)
        raise AcceptedProductReconciled
    from .portfolio_storage import ledger_digest
    if ledger_digest(data) != before:
        save(data)


def checkpoint_interruption(message: str) -> None:
    """Persist one clean shutdown checkpoint while ignoring repeated Ctrl-C."""
    previous = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        data = load(); data["automation"].update({"status": "INTERRUPTED", "interrupted_at": now()}); save(data)
        print(message, file=sys.stderr, flush=True)
    finally:
        signal.signal(signal.SIGINT, previous)


def begin_planner_attempt(data: dict, generation: int, planner_limit: int) -> tuple[bool, int]:
    """Reserve one logical planning call; transport retries reuse that reservation."""
    automation = data["automation"]
    if automation.get("planning_generation") != generation:
        automation.update({"planning_generation": generation, "planner_invocations_used": 0, "planner_stage": None})
    stage = automation.get("planner_stage") or {}
    reusing = stage.get("generation") == generation and stage.get("status") in {"DEFERRED_AVAILABILITY", "RUNNING"}
    if not reusing:
        if int(automation.get("planner_invocations_used", 0)) >= planner_limit:
            raise RuntimeError(f"hard planner invocation cap exhausted for generation {generation}")
        automation["planner_invocations_used"] = int(automation.get("planner_invocations_used", 0)) + 1
    attempts = int(stage.get("transport_attempts", 0)) + 1 if reusing else 1
    automation["planner_stage"] = {
        "status": "RUNNING", "at": now(), "generation": generation,
        "transport_attempts": attempts, "logical_reservation_reused": reusing,
    }
    return reusing, attempts


def abandon_exhausted_planning_generation(data: dict, error: BaseException) -> int:
    """Close one planning-only generation without weakening or resetting its hard cap."""
    automation = data["automation"]
    generation = int(automation.get("planning_generation") or (int(automation.get("generation", 0)) + 1))
    stage = dict(automation.get("planner_stage") or {})
    stage.update({"status": "ABANDONED_HARD_CAP", "closed_at": now(), "generation": generation, "error": str(error)[-2000:]})
    automation.update({
        "generation": max(int(automation.get("generation", 0)), generation),
        "phase": "IDLE", "status": "RUNNING", "planner_stage": stage,
        "last_error": str(error), "last_error_at": now(),
    })
    automation.pop("cohort", None); automation.pop("plan", None)
    data.setdefault("events", []).append({
        "at": now(), "kind": "PLANNING_GENERATION_ABANDONED_HARD_CAP",
        "generation": generation,
        "planner_invocations_used": int(automation.get("planner_invocations_used", 0)),
        "disposition": "PRESERVE_RESERVATIONS_AND_CONTINUE_NEXT_GENERATION",
    })
    return generation


def defer_planner_attempt(data: dict, generation: int, error: BaseException, attempts: int, reusing: bool) -> None:
    data["automation"]["planner_stage"] = {
        "status": "DEFERRED_AVAILABILITY", "at": now(), "generation": generation,
        "retry_at": getattr(error, "retry_at", None), "category": getattr(error, "category", "PROVIDER_CAPACITY"),
        "transport_attempts": attempts, "logical_reservation_reused": reusing,
        "resume_mode": "REPLAY_LOGICAL_STAGE; PROVIDER_SESSION_RESUME_UNAVAILABLE",
    }


def persist_planning_checkpoint(generation: int, cohort: str, plans: list[dict]) -> Path:
    """Write the plan, then merge its phase into the newest authenticated ledger."""
    plan_dir = _get_data().parent / "controller"; plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / f"{cohort}.json"; temporary = plan_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(plans, indent=2) + "\n", encoding="utf-8"); os.replace(temporary, plan_path)
    data = load(); automation = data["automation"]
    if automation.get("planning_generation") != generation or automation.get("phase") != "IDLE":
        raise RuntimeError("planning checkpoint changed while the Executor was running; preserve the newer state and reassess")
    stage = automation.get("planner_stage") or {}
    automation.update({"phase": "PLANNED", "generation": generation, "cohort": cohort, "plan": str(plan_path), "last_error": None})
    automation["planner_stage"] = {**stage, "status": "COMPLETED", "at": now(), "generation": generation}
    save(data)
    return plan_path


def _real_cohort_goal_schedule(lifecycle_state: dict | None = None) -> dict:
    """Project the canonical goal portfolio onto this public-document experiment."""
    from urace.cli import goal_portfolio, load_config, load_state

    state = lifecycle_state if lifecycle_state is not None else load_state(load_config())
    report = goal_portfolio(state)
    objectives = {item.get("id"): item for item in state.get("objectives", [])}
    rows = []
    for row in report["goals"]:
        objective = objectives.get(row.get("id"), {})
        applicable = objective.get("scope") == "documentation" or objective.get("priority_scope") in {
            "product_guidance", "authoritative_specification", "guidance", "specification",
        }
        rows.append({
            "id": row.get("id"), "title": row.get("title"), "rank": row.get("rank"),
            "score": row.get("score"), "eligible": bool(row.get("eligible")),
            "applicable": applicable, "dependencies": row.get("dependencies", []),
            "blockers": row.get("blockers", []), "estimate": row.get("estimate", {}),
            "forecast": row.get("forecast", {}), "priority_reason": row.get("priority_reason", ""),
        })
    selected = [row for row in rows if row["eligible"] and row["applicable"]]
    snapshot = {
        "version": "shared-goal-portfolio-v1", "evidence_cutoff": report["generated_at"],
        "basis": report["basis"], "goals": rows, "selected_goal_ids": [row["id"] for row in selected],
    }
    snapshot["digest"] = hashlib.sha256(canonical(snapshot)).hexdigest()
    return snapshot


def cohort_goal_schedule(lifecycle_state: dict | None = None) -> dict:
    """Dispatch through portfolio hub so patch.object(portfolio, 'cohort_goal_schedule') works in tests."""
    import sys
    hub = sys.modules.get("urace.portfolio")
    if hub is not None:
        hub_fn = hub.__dict__.get("cohort_goal_schedule")
        if hub_fn is not None and hub_fn is not cohort_goal_schedule:
            return hub_fn(lifecycle_state)
    return _real_cohort_goal_schedule(lifecycle_state)


def _real_portfolio_material_signature(data: dict, workflow_digest: str) -> str:
    """Identify inputs that can make another comparison newly useful without an Executor call."""
    try:
        goals = cohort_goal_schedule()
    except ModuleNotFoundError:
        goals = {"goals": [], "selected_goal_ids": []}
    stable_goals = [
        {key: row.get(key) for key in ("id", "score", "eligible", "applicable", "dependencies", "blockers", "estimate", "forecast")}
        for row in goals.get("goals", [])
    ]
    material = {
        "accepted_product": resolve_accepted_product_identity(data),
        "goals": stable_goals,
        "selected_goal_ids": goals.get("selected_goal_ids", []),
        "workflow_digest": workflow_digest,
        "cohort_policy": effective_cohort_policy(data),
    }
    return hashlib.sha256(canonical(material)).hexdigest()


def portfolio_material_signature(data: dict, workflow_digest: str) -> str:
    """Dispatch through portfolio hub so patch.object(portfolio, 'portfolio_material_signature') works in tests."""
    import sys
    hub = sys.modules.get("urace.portfolio")
    if hub is not None:
        hub_fn = hub.__dict__.get("portfolio_material_signature")
        if hub_fn is not None and hub_fn is not portfolio_material_signature:
            return hub_fn(data, workflow_digest)
    return _real_portfolio_material_signature(data, workflow_digest)


def _eligible(data: dict, item: dict) -> dict | None:
    """Local copy of eligible() to avoid circular import with portfolio hub."""
    if any(entry["guardrails"] == "fail" and not entry.get("invalidated_at") for entry in item["observations"]):
        return None
    observations = [entry for entry in item["observations"] if entry["guardrails"] == "pass" and not entry.get("invalidated_at")]
    evidence = sum(entry["evidence_units"] for entry in observations)
    if not observations or evidence < data["shared_contract"]["minimum_evidence"]:
        return None
    latest = observations[-1]
    return {"name": item["name"], "generation": item["generation"], "value": latest["value"], "system_contribution_bonus": float(item.get("system_contribution_bonus", 0)), "resource_cost": sum(entry["resource_cost"] for entry in observations), "evidence_units": evidence}


def _ranking(data: dict, cohort: str | None = None) -> list[dict]:
    """Local copy of ranking() to avoid circular import with portfolio hub."""
    entries = [result for item in data["variants"].values() if (cohort is None or item.get("cohort") == cohort) and (result := _eligible(data, item))]
    reverse = data["shared_contract"]["direction"] == "maximize"
    return sorted(entries, key=lambda item: (item["value"], item["system_contribution_bonus"], -item["resource_cost"]) if reverse else (-item["value"], item["system_contribution_bonus"], -item["resource_cost"]), reverse=True)


def completed_generation_summary(data: dict, cohort: str, generation: int) -> dict:
    """Retain bounded controller Evidence needed by the automatic worth gate."""
    ranked = _ranking(data, cohort)
    members = [item for item in data.get("variants", {}).values() if item.get("cohort") == cohort]
    top_gap = None
    if len(ranked) > 1:
        top_gap = abs(float(ranked[0]["value"]) - float(ranked[1]["value"]))
    return {
        "at": now(), "cohort": cohort, "generation": generation,
        "selected": ranked[0]["name"] if ranked else None,
        "winner_value": float(ranked[0]["value"]) if ranked else None,
        "eligible_count": len(ranked), "candidate_count": len(members),
        "guardrail_failures": sum(_eligible(data, item) is None for item in members),
        "top_gap": top_gap,
        "resource_cost": sum(float(entry.get("resource_cost", 0)) for entry in ranked),
    }


def portfolio_worth_assessment(data: dict, workflow: dict, workflow_digest: str) -> dict:
    """Decide at an idle boundary whether another equal-cost comparison is justified."""
    mode = effective_cohort_policy(data)
    signature = portfolio_material_signature(data, workflow_digest)
    automation = data.get("automation", {})
    previous = automation.get("portfolio_worth", {})
    summaries = automation.get("generation_summaries", [])
    if not summaries:
        generations = sorted({int(item.get("generation", 0)) for item in data.get("variants", {}).values() if item.get("cohort") and int(item.get("generation", 0)) > 0})
        summaries = [completed_generation_summary(data, f"generation-{generation}", generation) for generation in generations]
        if summaries:
            automation["generation_summaries"] = summaries[-AUTO_SUMMARY_RETENTION:]
    decision, reasons = "RUN", []
    if mode == "enabled":
        reasons.append("operator policy explicitly enables repeated comparison")
    elif mode == "disabled":
        decision, reasons = "DORMANT", ["operator policy disables comparison"]
    elif previous.get("last_run_input_signature") and previous.get("last_run_input_signature") != signature:
        reasons.append("material Product, goal, workflow or policy input changed")
    elif len(summaries) < AUTO_MIN_OBSERVED_GENERATIONS:
        reasons.append("insufficient completed comparison Evidence for a cost/value decision")
    else:
        recent = summaries[-AUTO_MIN_OBSERVED_GENERATIONS:]
        values = [item.get("winner_value") for item in recent]
        if any(value is None for value in values):
            decision, reasons = "DORMANT", ["recent comparisons produced no eligible result"]
        else:
            delta = float(values[-1]) - float(values[-2])
            if data.get("shared_contract", {}).get("direction") == "minimize":
                delta = -delta
            close_streak = 0
            for item in reversed(summaries):
                gap = item.get("top_gap")
                if gap is None or float(gap) > AUTO_CLOSE_MARGIN:
                    break
                close_streak += 1
            if delta >= AUTO_MIN_METRIC_IMPROVEMENT:
                reasons.append(f"recent winner improved by {delta:g} metric units")
            elif close_streak and close_streak < AUTO_MAX_CLOSE_GENERATIONS:
                reasons.append("one bounded follow-up can discriminate close eligible alternatives")
            else:
                decision = "DORMANT"
                reasons.append("recent Evidence does not justify another equal-budget comparison")
    assessed = {
        "decision": decision, "mode": mode, "reasons": reasons,
        "material_signature": signature, "assessed_at": now(),
        "basis": "controller Evidence only; no Executor invocation",
        "thresholds": {
            "observed_generations": AUTO_MIN_OBSERVED_GENERATIONS,
            "minimum_metric_improvement": AUTO_MIN_METRIC_IMPROVEMENT,
            "close_margin": AUTO_CLOSE_MARGIN,
            "maximum_close_generations": AUTO_MAX_CLOSE_GENERATIONS,
        },
    }
    assessed["last_run_input_signature"] = signature if decision == "RUN" else previous.get("last_run_input_signature")
    return assessed


def cooperative_memory(data: dict, limit: int = 12) -> dict:
    """Build bounded controller-curated learning without another Executor call."""
    from .portfolio_storage import bounded_text as _bounded_text
    findings = []
    for item in sorted(data.get("variants", {}).values(), key=lambda value: (value.get("generation", 0), value.get("name", "")), reverse=True):
        observations = [value for value in item.get("observations", []) if not value.get("invalidated_at")]
        if observations:
            latest = observations[-1]
            findings.append({"variant": item.get("name"), "generation": item.get("generation"), "disposition": item.get("status"), "metric": latest.get("value"), "guardrails": latest.get("guardrails"), "note": _bounded_text(latest.get("note", ""), "cooperative finding")[:500]})
        if len(findings) >= limit: break
    lessons = [{key: value for key, value in item.items() if key in {"id", "statement", "supporting_evidence", "counterevidence", "applicability", "confidence", "status"}} for item in data.get("lessons", [])[-limit:]]
    decisions = [{key: value for key, value in item.items() if key in {"id", "proposal", "outcome", "reason", "status", "inheritance_parent"}} for item in data.get("agora", {}).get("decisions", [])[-limit:]]
    payload = {"version": "cooperative-memory-v1", "findings": findings, "approved_lessons": lessons, "agora_decisions": decisions}
    payload["digest"] = hashlib.sha256(canonical(payload)).hexdigest()
    return payload


def workflow_preflight(workflow_path: Path) -> dict:
    checks = []
    try:
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"ready": False, "workflow": str(workflow_path), "checks": [{"name": "workflow", "status": "FAIL", "detail": str(error)}]}
    required = {"cohort_size", "total_resource_budget", "resource_unit", "executor_invocation_budget_per_generation", "plan_command", "mutate_command", "evaluate_command"}
    missing = sorted(required - workflow.keys())
    checks.append({"name": "schema", "status": "PASS" if not missing else "FAIL", "detail": "required fields present" if not missing else f"missing: {', '.join(missing)}"})
    if missing:
        return {"ready": False, "workflow": str(workflow_path), "checks": checks}
    cohort = int(workflow["cohort_size"]); executor_budget = int(workflow["executor_invocation_budget_per_generation"])
    budget_ok = cohort > 0 and float(workflow["total_resource_budget"]) > 0 and executor_budget >= cohort * 2 and executor_budget % cohort == 0 and int(workflow.get("planner_invocation_budget_per_generation") or 0) > 0
    checks.append({"name": "equal-hard-budgets", "status": "PASS" if budget_ok else "FAIL", "detail": f"{executor_budget // cohort if cohort else 0} controller invocations per variant; planning cap={workflow.get('planner_invocation_budget_per_generation')}"})
    for key in ("plan_command", "mutate_command", "evaluate_command"):
        try:
            command = workflow_command(workflow, key)
            executable = command[0]
            builtin = command[:2] in ([BUILTIN_ADAPTER, "plan"], [BUILTIN_ADAPTER, "mutate"], [BUILTIN_ADAPTER, "evaluate"])
            found = builtin or shutil.which(executable) or ((_get_root() / executable).exists() if "/" in executable else False)
            operands = [] if "-c" in command else command[1:]
            local_operands = [_get_root() / value for value in operands if isinstance(value, str) and (value.endswith(".py") or value.startswith(("./", "../"))) and not value.startswith("-")]
            missing_operands = [str(path) for path in local_operands if not path.exists()]
            ok = bool(found) and not missing_operands
            detail = "validated built-in adapter" if builtin and ok else ("executable and local adapter operands found" if ok else f"missing executable or operands: {executable} {missing_operands}")
        except RuntimeError as error:
            ok, detail = False, str(error)
        checks.append({"name": key, "status": "PASS" if ok else "FAIL", "detail": detail})
    caps = workflow.get("provider_internal_hard_caps") is True
    builtin_only = all(workflow_command(workflow, key)[0] == BUILTIN_ADAPTER for key in ("plan_command", "mutate_command", "evaluate_command"))
    cap_detail = "built-in adapters preserve one logical stage reservation and bound transport attempts by the compatible Executor pool; provider token and monetary usage remain separately disclosed" if builtin_only else "adapters attest that provider transports remain bounded by the declared logical stage and pool; unavailable token or monetary units must remain separately disclosed"
    checks.append({"name": "provider-internal-caps", "status": "PASS" if caps else "FAIL", "detail": cap_detail if caps else "set true only after every adapter enforces its own provider-invocation limit"})
    effects = workflow.get("external_effects") in {"none", "idempotent-and-reconciled"}
    checks.append({"name": "external-effects", "status": "PASS" if effects else "FAIL", "detail": str(workflow.get("external_effects", "undeclared"))})
    allowlist = workflow.get("candidate_environment_allowlist", [])
    isolation_mode = workflow.get("candidate_isolation")
    isolation_declared = isolation_mode in {"bubblewrap-no-host-filesystem", "executor-workspace-sandbox"} and isinstance(allowlist, list) and all(isinstance(item, str) and item and not item.startswith("URACE_") for item in allowlist)
    isolation_ok, isolation_detail = False, "candidate isolation declaration or environment allowlist is invalid"
    isolation_error = ""
    if isolation_declared and builtin_only and isolation_mode == "executor-workspace-sandbox":
        from urace.cli import load_config
        from urace.executor import provider_definitions, provider_settings
        executor_config = load_config()["executor"]
        codex_provider = next((item for item in provider_definitions(executor_config) if item.get("adapter", "codex-cli") == "codex-cli"), {})
        executor_settings = provider_settings(executor_config, codex_provider)
        executable = shutil.which(executor_settings.get("command", "codex"))
        private_bwrap = Path(executor_settings.get("sandbox_bwrap_directory", "")) / "bwrap"
        disabled_features = set(executor_settings.get("disabled_features", []))
        uses_legacy_sandbox = "use_linux_sandbox_bwrap" in disabled_features
        configured_version = executor_settings.get("workspace_write_validated_version")
        observed_version = None
        if executable:
            try:
                version_result = subprocess.run([executable, "--version"], text=True, capture_output=True, timeout=10, check=False)
                if version_result.returncode == 0:
                    observed_version = version_result.stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                pass
        isolation_ok = (
            executor_settings.get("enabled") is True
            and executor_settings.get("kind") == "codex-cli"
            and bool(executable)
            and workflow.get("candidate_network") is False
            and (
                uses_legacy_sandbox
                and executor_settings.get("workspace_write_validated") is True
                and configured_version == observed_version
                or not uses_legacy_sandbox
                and private_bwrap.is_file()
                and os.access(private_bwrap, os.X_OK)
            )
        )
        if isolation_ok and not uses_legacy_sandbox:
            probe = _get_portfolio_root() / ".executor-isolation-probe"; probe.mkdir(parents=True, exist_ok=True)
            probe_workflow = {**workflow, "candidate_isolation": "bubblewrap-no-host-filesystem"}
            _data_path = _get_data(); _ikey_path = _get_integrity_key(); _root_path = _get_root()
            probe_script = f"""from pathlib import Path
import socket
assert not Path({str(_data_path)!r}).exists()
assert not Path({str(_ikey_path)!r}).exists()
assert not Path({str(_root_path / 'runtime')!r}).exists()
s = socket.socket(); s.settimeout(.2)
try:
    s.connect(('1.1.1.1', 80))
except OSError:
    pass
else:
    raise SystemExit('candidate network unexpectedly reachable')
"""
            probe_command = isolated_candidate_command(probe, [sys.executable, "-c", probe_script], probe_workflow, {"PATH": _DEFAULT_PATH, "HOME": _TMP_HOME, "LANG": "C.UTF-8"})
            probe_command[0] = str(private_bwrap)
            result = subprocess.run(probe_command, cwd=_root_path, text=True, capture_output=True, timeout=10)
            isolation_ok = result.returncode == 0
            isolation_error = result.stderr.strip()[-1000:]
            probe.rmdir()
        if isolation_ok and uses_legacy_sandbox:
            isolation_detail = f"built-in adapters use isolated worktrees plus the validated Codex workspace sandbox via {executable} ({observed_version}); candidate networking is not requested"
        elif isolation_ok:
            isolation_detail = f"built-in adapters use isolated worktrees plus Codex sandboxes via {executable}; private {private_bwrap} passed filesystem and no-network probes"
        else:
            isolation_detail = "the configured Codex workspace sandbox is unavailable, its validation no longer matches the executable version, confinement failed, or candidate_network is not false" + (f": {isolation_error}" if isolation_error else "")
    elif isolation_declared and isolation_mode == "bubblewrap-no-host-filesystem" and shutil.which("bwrap"):
        probe = _get_portfolio_root() / ".isolation-probe"; probe.mkdir(parents=True, exist_ok=True)
        try:
            command = isolated_candidate_command(probe, ["/bin/sh", "-c", f"test ! -e {_get_data()} && test ! -e {_get_integrity_key()} && test ! -e {_get_root() / 'runtime'}"], workflow, {"PATH": _DEFAULT_PATH, "HOME": _TMP_HOME, "LANG": "C.UTF-8"})
            result, attempts = run_isolation_probe(command)
            isolation_ok = result.returncode == 0
            isolation_detail = (
                "bubblewrap probe denied candidate visibility of ledger, key and runtime"
                + (f" after {attempts} attempts" if attempts > 1 else "")
                if isolation_ok else (result.stderr.strip() or "bubblewrap isolation probe failed")
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            isolation_detail = str(error)
        finally:
            probe.rmdir()
    checks.append({"name": "candidate-ledger-isolation", "status": "PASS" if isolation_ok else "FAIL", "detail": isolation_detail})
    try:
        integrity_key()
        archive_paths = sorted((_get_data().parent / "archive").glob("*.json"))
        for archive_path in archive_paths:
            verify_authenticated_archive(archive_path)
    except SystemExit as error:
        integrity_ok, integrity_detail = False, str(error)
    else:
        integrity_ok, integrity_detail = True, f"authenticated HMAC-SHA256 ledger seal and {len(archive_paths)} archives; owner-only key at {_get_integrity_key().relative_to(_get_root())}"
    checks.append({"name": "cryptographic-ledger-integrity", "status": "PASS" if integrity_ok else "FAIL", "detail": integrity_detail})
    try:
        data = load(); automation = data.get("automation", {})
        digest = hashlib.sha256(json.dumps(workflow, sort_keys=True).encode()).hexdigest()
        frozen = automation.get("workflow_digest") in {None, digest}
    except SystemExit as error:
        frozen, detail = False, str(error)
    else:
        detail = "matches frozen experiment" if frozen else "differs from the portfolio's frozen workflow"
    checks.append({"name": "experiment-constitution", "status": "PASS" if frozen else "FAIL", "detail": detail})
    return {"ready": all(item["status"] == "PASS" for item in checks), "workflow": str(workflow_path), "checks": checks, "mode": "sequential candidates; equal controller-level budgets"}


def print_preflight(report: dict, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True)); return
    print(f"Portfolio preflight: {'READY' if report['ready'] else 'NOT READY'}", flush=True)
    for item in report["checks"]:
        print(f"  {item['status']} {item['name']}: {item['detail']}", flush=True)


def cmd_preflight(args: argparse.Namespace) -> None:
    path = (_get_root() / args.workflow).resolve() if not Path(args.workflow).is_absolute() else Path(args.workflow)
    report = workflow_preflight(path); print_preflight(report, args.json)
    if not report["ready"]:
        raise SystemExit(2)


def cmd_launch(args: argparse.Namespace) -> None:
    path = (_get_root() / args.workflow).resolve() if not Path(args.workflow).is_absolute() else Path(args.workflow)
    report = workflow_preflight(path); print_preflight(report, False)
    if not report["ready"]:
        raise SystemExit("launch stopped before effects because preflight did not pass")
    print("Portfolio launch: preflight passed; entering persistent autonomous operation", flush=True)
    cmd_autonomous(argparse.Namespace(workflow=str(path), cycles=None))


def cmd_autonomous(args: argparse.Namespace) -> None:
    from . import portfolio as _portfolio_hub
    workflow_path = (_get_root() / args.workflow).resolve() if not Path(args.workflow).is_absolute() else Path(args.workflow)
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    required = {"cohort_size", "total_resource_budget", "resource_unit", "executor_invocation_budget_per_generation", "plan_command", "mutate_command", "evaluate_command"}
    if not required <= workflow.keys() or int(workflow["cohort_size"]) < 1 or float(workflow["total_resource_budget"]) <= 0:
        raise SystemExit(f"workflow requires positive cohort_size and total_resource_budget plus {sorted(required)}")
    for key in ("plan_command", "mutate_command", "evaluate_command"):
        workflow_command(workflow, key)
    cohort_size = int(workflow["cohort_size"]); executor_budget = int(workflow["executor_invocation_budget_per_generation"])
    if executor_budget < cohort_size * 2 or executor_budget % cohort_size:
        raise SystemExit("executor_invocation_budget_per_generation must divide equally and provide at least mutate + evaluate for every variant")
    digest = hashlib.sha256(json.dumps(workflow, sort_keys=True).encode()).hexdigest()
    constitution = {key: workflow.get(key) for key in PROTECTED_WORKFLOW_FIELDS}
    constitution_digest = hashlib.sha256(json.dumps(constitution, sort_keys=True).encode()).hexdigest()
    data = load(); automation = data.setdefault("automation", {"phase": "IDLE", "generation": 0, "cycles_completed": 0, "consecutive_failures": 0})
    if automation.get("workflow_digest") not in {None, digest}:
        raise SystemExit("the workflow is frozen for this portfolio; start a new portfolio for a different experiment")
    if automation.get("constitution_digest") not in {None, constitution_digest}:
        raise SystemExit("the experiment constitution or resource ceilings changed; variants cannot alter protected rules")
    reconcile_accepted_product(data, workflow)
    automation = data["automation"]
    automation.update({"workflow_digest": digest, "constitution": constitution, "constitution_digest": constitution_digest, "workflow_path": str(workflow_path), "status": "RUNNING", "planner_invocation_hard_cap": int(workflow.get("planner_invocation_budget_per_generation", 1))}); save(data)
    if pause_if_cohort_disabled(load()):
        return
    completed_here = 0
    while args.cycles is None or completed_here < args.cycles:
        try:
            autonomous_safe_boundary(workflow)
            data = load(); automation = data["automation"]
            if automation["phase"] == "IDLE":
                assessment = portfolio_worth_assessment(data, workflow, digest)
                prior = automation.get("portfolio_worth", {})
                automation["portfolio_worth"] = assessment
                if assessment["decision"] == "DORMANT":
                    automation["status"] = "DORMANT_AUTO"
                    changed = (prior.get("decision"), prior.get("material_signature")) != (assessment["decision"], assessment["material_signature"])
                    save(data)
                    if changed:
                        print(f"Portfolio auto: dormant — {assessment['reasons'][0]}. It will recheck without Executor calls and wake after a material Product, goal, workflow or policy change.", flush=True)
                    if args.cycles is not None:
                        return
                    try:
                        time.sleep(max(1.0, min(60.0, float(workflow.get("portfolio_auto_recheck_seconds", 300)))))
                    except KeyboardInterrupt:
                        checkpoint_interruption("Interrupted safely while portfolio auto was dormant; rerun the same command to resume")
                        return
                    continue
                automation["status"] = "RUNNING"
                if prior.get("decision") == "DORMANT":
                    print(f"Portfolio auto: active — {assessment['reasons'][0]}.", flush=True)
                save(data)
                data = load(); automation = data["automation"]
                generation = int(automation["generation"]) + 1; cohort = f"generation-{generation}"
                planner_limit = int(workflow.get("planner_invocation_budget_per_generation", 1))
                reusing_planner, planner_transport_attempts = begin_planner_attempt(data, generation, planner_limit)
                save(data)
                # Health gate: verify mutation executor is available before spending a planner credit.
                # If no mutation-capable provider is ready, wait and retry rather than planning a generation
                # that will fail 100% at the mutation stage.
                try:
                    from urace import executor as _exec_module
                    from urace.cli import load_config as _load_cfg
                    _gate_config = _load_cfg()
                    _gate_pool = data.get("automation", {}).get("executor_pool", {})
                    _gate_report = _exec_module.pool_availability(_gate_config["executor"], _gate_pool, "mutation")
                    if not _gate_report["available"]:
                        retry_hint = _gate_report.get("providers", [{}])[0].get("retry_at") if _gate_report.get("providers") else None
                        print(f"Portfolio auto: mutation executor unavailable ({_gate_report['reason']}); deferring generation {generation} planning. retry_at={retry_hint}", flush=True)
                        data = load(); automation = data["automation"]
                        automation["phase"] = "IDLE"
                        automation["executor_health_gate"] = {"checked_at": now(), "generation": generation, "available": False, "reason": _gate_report["reason"], "retry_at": retry_hint}
                        save(data)
                        time.sleep(max(30.0, float(workflow.get("portfolio_auto_recheck_seconds", 300))))
                        continue
                    data = load(); automation = data["automation"]
                    automation.pop("executor_health_gate", None)
                    save(data)
                except Exception:
                    pass  # health gate failure is non-blocking; proceed and let the mutation stage surface the actual error
                plan_command = workflow_command(workflow, "plan_command")
                try:
                    if plan_command[:2] == [BUILTIN_ADAPTER, "plan"]:
                        plans = builtin_plan(generation, cohort, workflow, data)
                    else:
                        result = subprocess.run(plan_command, cwd=_get_root(), env=automation_env(None, generation, cohort), text=True, capture_output=True, timeout=float(workflow.get("plan_timeout_seconds", 300)))
                        if result.returncode:
                            raise RuntimeError(f"plan command failed: {result.stderr[-500:]}")
                        plans = json.loads(result.stdout)
                    if not isinstance(plans, list) or len(plans) != int(workflow["cohort_size"]):
                        raise RuntimeError("plan command must output a JSON array matching cohort_size")
                    for index, plan in enumerate(plans, 1):
                        if not isinstance(plan, dict): raise RuntimeError("each mutation plan must be an object")
                        for field in ("mutation", "hypothesis", "expected_effect"):
                            plan[field] = bounded_text(plan.get(field), field)
                        plan["name"] = f"g{generation}-{index}"
                    persist_planning_checkpoint(generation, cohort, plans)
                    if reusing_planner:
                        subprocess.run([sys.executable, "-m", "urace", "executor-capacity", "clear", "--stage", "portfolio:controller:planning"], cwd=_get_root(), check=False, stdout=subprocess.DEVNULL)
                except Exception as error:
                    latest = load()
                    if is_executor_unavailable(error):
                        defer_planner_attempt(latest, generation, error, planner_transport_attempts, reusing_planner)
                        save(latest)
                        wait_for_executor_capacity(error, workflow, "controller", "planning")
                        continue
                    latest["automation"]["planner_stage"] = {
                        "status": "FAILED", "at": now(), "generation": generation,
                        "transport_attempts": planner_transport_attempts, "error": str(error)[-2000:],
                    }
                    save(latest)
                    raise
            data = load(); automation = data["automation"]; generation = automation["generation"]; cohort = automation["cohort"]
            if automation["phase"] == "PLANNED":
                autonomous_safe_boundary(workflow)
                data = load(); automation = data["automation"]
                cmd_cohort(argparse.Namespace(count=int(workflow["cohort_size"]), prefix=cohort, plan=automation["plan"], parent=automation["accepted_parent_commit"], lineage_parent=data.get("selected"), total_resource_budget=float(workflow["total_resource_budget"]), resource_unit=workflow["resource_unit"], resume=True))
                data = load()
                equal_executor_budget = executor_budget // cohort_size
                for item in data["variants"].values():
                    if item.get("cohort") == cohort:
                        item.setdefault("executor_invocation_budget", equal_executor_budget)
                        item.setdefault("executor_invocations_used", 0)
                data["automation"]["phase"] = "CREATED"; save(data)
            data = load(); automation = data["automation"]
            if automation["phase"] == "CREATED":
                for item in [entry for entry in data["variants"].values() if entry.get("cohort") == cohort]:
                    if item.get("automation_stages", {}).get("mutate", {}).get("status") not in {"COMPLETED", "FAILED", "INCOMPLETE_RESOURCE"}:
                        autonomous_safe_boundary(workflow)
                        try:
                            run_automation_stage(item, generation, cohort, workflow, "mutate")
                        except Exception as error:
                            if is_executor_unavailable(error):
                                wait_for_executor_capacity(error, workflow, item["name"], "mutate")
                                raise
                            if isinstance(error, StageBudgetExhausted):
                                record_candidate_stage_incomplete(item["name"], "mutate", error)
                                continue
                            _attr = None
                            try:
                                _attr = load().get("automation", {}).get("executor_pool", {}).get("last_route")
                            except Exception:
                                pass
                            record_candidate_stage_failure(item["name"], "mutate", error, executor_attribution=_attr)
                data = load(); data["automation"]["phase"] = "MUTATED"; save(data)
            data = load(); automation = data["automation"]
            if automation["phase"] == "MUTATED":
                for item in [entry for entry in data["variants"].values() if entry.get("cohort") == cohort]:
                    if item.get("automation_stages", {}).get("mutate", {}).get("status") != "COMPLETED":
                        continue
                    stage = item.get("automation_stages", {}).get("evaluate", {})
                    if stage.get("status") not in {"COMPLETED", "FAILED", "INCOMPLETE_RESOURCE"}:
                        autonomous_safe_boundary(workflow)
                        try:
                            outcome = run_automation_stage(item, generation, cohort, workflow, "evaluate")
                            stage = outcome
                        except Exception as error:
                            if is_executor_unavailable(error):
                                wait_for_executor_capacity(error, workflow, item["name"], "evaluate")
                                raise
                            if isinstance(error, StageBudgetExhausted):
                                record_candidate_stage_incomplete(item["name"], "evaluate", error)
                                continue
                            _attr = None
                            try:
                                _attr = load().get("automation", {}).get("executor_pool", {}).get("last_route")
                            except Exception:
                                pass
                            record_candidate_stage_failure(item["name"], "evaluate", error, executor_attribution=_attr)
                            continue
                    if not any(not observation.get("invalidated_at") for observation in item.get("observations", [])):
                        _portfolio_hub.cmd_record(argparse.Namespace(variant=item["name"], **stage["measurement"]))
                data = load(); data["automation"]["phase"] = "EVALUATED"; save(data)
            data = load(); automation = data["automation"]
            if automation["phase"] == "EVALUATED":
                summary = completed_generation_summary(data, cohort, generation)
                if _portfolio_hub.ranking(data, cohort):
                    _portfolio_hub.cmd_select(argparse.Namespace(variant=None, cohort=cohort))
                else:
                    data.setdefault("events", []).append({"at": now(), "kind": "GENERATION_NO_ELIGIBLE_VARIANT", "generation": generation, "cohort": cohort, "disposition": "RETAIN_PARENT"})
                    save(data)
                    print("No candidate passed evaluation; retained the prior selected parent and continued.", flush=True)
                data = load(); automation = data["automation"]
                automation.setdefault("generation_summaries", []).append(summary)
                automation["generation_summaries"] = automation["generation_summaries"][-AUTO_SUMMARY_RETENTION:]
                automation.update({"phase": "IDLE", "cycles_completed": int(automation["cycles_completed"]) + 1, "consecutive_failures": 0, "last_completed_at": now(), "last_error": None})
                automation.pop("last_error_at", None)
                automation.pop("last_failure_signature", None)
                automation["identical_failure_count"] = 0
                automation["controller_repair_status"] = "NOT_NEEDED"
                archive_old_variants(data, generation, int(workflow.get("retain_generations", 10))); save(data)
                completed_here += 1
                data = load(); data["automation"]["status"] = "RUNNING" if args.cycles is None or completed_here < args.cycles else "IDLE"; save(data)
                _portfolio_hub.print_feedback(load())
                report_command = [sys.executable, "-m", "urace", "report", "export", "--output", "urace/generated/reports/latest"]
                if workflow.get("analytics_native_workbook") is True:
                    report_command.append("--xlsx")
                subprocess.run(report_command, cwd=_get_root(), check=False, stdout=subprocess.DEVNULL)
                if args.cycles is None or completed_here < args.cycles:
                    time.sleep(max(0, float(workflow.get("cycle_delay_seconds", 0))))
        except CohortPolicyPaused:
            return
        except AcceptedProductReconciled:
            continue
        except KeyboardInterrupt:
            checkpoint_interruption("Interrupted safely; rerun the same command to resume"); return
        except (Exception, SystemExit) as error:
            if is_executor_unavailable(error):
                continue
            data = load(); automation = data["automation"]
            fault = controller_fault_descriptor(error, str(automation.get("phase", "UNKNOWN")))
            signature_material = json.dumps(fault, sort_keys=True) if fault else f"NON_REPAIRABLE:{type(error).__name__}:{error}"
            signature = hashlib.sha256(signature_material.encode()).hexdigest()
            identical = int(automation.get("identical_failure_count", 0)) + 1 if automation.get("last_failure_signature") == signature else 1
            automation["consecutive_failures"] = int(automation.get("consecutive_failures", 0)) + 1
            automation.update({"last_error": str(error), "last_error_at": now(), "last_failure_signature": signature, "identical_failure_count": identical, "status": "BACKOFF"}); save(data)
            if str(error).startswith("hard ") and " cap exhausted" in str(error):
                data = load(); generation = abandon_exhausted_planning_generation(data, error); save(data)
                backoff = max(0, float(workflow.get("error_backoff_seconds", 30)))
                print(f"Portfolio closed planning generation {generation}: {error}. Its fixed reservations remain recorded; autonomous operation will continue with a new generation after {backoff:g}s.", file=sys.stderr, flush=True)
                try:
                    time.sleep(backoff)
                except KeyboardInterrupt:
                    checkpoint_interruption("Interrupted safely during planning-generation backoff; rerun the same command to resume")
                    return
                continue
            if automation["consecutive_failures"] >= int(workflow.get("max_consecutive_failures", 5)):
                print(f"Portfolio paused after {automation['consecutive_failures']} consecutive failures: {error}", file=sys.stderr, flush=True); return
            repair_returncode = attempt_controller_auto_repair(fault, workflow, automation)
            if repair_returncode == 75:
                print("Portfolio recovery: validated runtime repair prepared; launcher is activating it and will resume this checkpoint", flush=True)
                raise SystemExit(75)
            backoff = max(0, float(workflow.get("error_backoff_seconds", 30)))
            print(f"Portfolio attempt failed ({automation['consecutive_failures']}/{workflow.get('max_consecutive_failures', 5)}); retrying after {backoff:g}s. Inspect anytime with `portfolio feedback`.", file=sys.stderr, flush=True)
            try:
                time.sleep(backoff)
            except KeyboardInterrupt:
                checkpoint_interruption("Interrupted safely during backoff; rerun the same command to resume")
                return
    data = load(); data["automation"]["status"] = "IDLE"; save(data)

