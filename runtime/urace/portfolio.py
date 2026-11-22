#!/usr/bin/env python3
"""Deployment-local bounded URACE portfolio controller — thin hub."""

from __future__ import annotations

import argparse
import json
import os
import sys

# ---------------------------------------------------------------------------
# Standalone-script compatibility: when run as `python3 portfolio.py`, inject
# the runtime package path so that relative imports work correctly.
# ---------------------------------------------------------------------------
if __name__ == "__main__" and __package__ is None:
    _parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    # Re-execute this file as part of the urace package so relative imports work.
    import runpy
    runpy.run_module("urace.portfolio", run_name="__main__", alter_sys=True)
    sys.exit(0)

# ---------------------------------------------------------------------------
# Re-export everything from the focused sub-modules so callers continue to
# work unchanged: portfolio.load(), portfolio.save(), portfolio.parser(), etc.
# ---------------------------------------------------------------------------

from .portfolio_storage import (
    product_root,
    ROOT, SYSTEM_ROOT, PORTFOLIO_ROOT, GENERATED_ROOT, TEMPORARY_ROOT,
    RETIRED_PORTFOLIOS_ROOT, DATA, LEDGER_LOCK, OPERATION_LOCK,
    CONTROL_INBOX, VARIANTS, INTEGRITY_KEY,
    SAFE_NAME, MAX_ADVISORY_TEXT, MAX_AGORA_RECORDS,
    now, integrity_key, canonical, ledger_digest, verify_ledger,
    load, save, record_payload, append_agora,
    write_authenticated_archive, verify_authenticated_archive,
    cmd_verify, verify_agora, bounded_text, name,
    rotate_integrity_key, cmd_rotate_integrity_key,
    unit_interval,
)

from .portfolio_product import (
    COHORT_POLICIES, COHORT_POLICY_ALIASES, ACCEPTED_STATE_SOURCES,
    variant, git,
    effective_cohort_policy, effective_accepted_state_source,
    resolve_accepted_product_identity, product_source_digest,
    snapshot_current_product, accepted_product_commit,
    reconcile_accepted_product,
    cmd_policy, cmd_policy_status,
    cmd_accepted_state_source, cmd_accepted_state_source_status,
    cmd_init, cmd_spawn, cmd_cohort,
)

from .portfolio_executor import (
    BUILTIN_ADAPTER, PLAN_SCHEMA, EVALUATION_SCHEMA,
    EVALUATOR_MANIPULATION_PATTERNS,
    MAX_CANDIDATE_CHANGED_LINES, MAX_CANDIDATE_NET_ADDITIONS,
    ISOLATION_PROBE_ATTEMPTS,
    StageBudgetExhausted, AcceptedProductReconciled,
    is_executor_unavailable, controller_fault_descriptor,
    attempt_controller_auto_repair,
    routed_portfolio_executor, executor_progress,
    automation_env, isolated_candidate_command,
    run_isolated_command, run_isolation_probe,
    run_automation_stage,
    record_candidate_stage_failure, record_candidate_stage_incomplete,
    wait_for_executor_capacity, archive_old_variants,
    scope_priorities, builtin_plan, builtin_mutate, builtin_evaluate,
    workflow_command,
)

from .portfolio_runner import (
    PROTECTED_WORKFLOW_FIELDS,
    AUTO_MIN_OBSERVED_GENERATIONS, AUTO_MIN_METRIC_IMPROVEMENT,
    AUTO_CLOSE_MARGIN, AUTO_MAX_CLOSE_GENERATIONS, AUTO_SUMMARY_RETENTION,
    LIVE_CONTROL_ACTIONS,
    CohortPolicyPaused,
    normalize_run_options, cmd_run_cohort, cmd_run,
    parse_cycle_limit, queue_portfolio_control, consume_portfolio_controls,
    sync_live_controls, pause_if_cohort_disabled,
    autonomous_safe_boundary, checkpoint_interruption,
    begin_planner_attempt, abandon_exhausted_planning_generation,
    defer_planner_attempt, persist_planning_checkpoint,
    cohort_goal_schedule, portfolio_material_signature,
    completed_generation_summary, portfolio_worth_assessment,
    cooperative_memory,
    workflow_preflight, print_preflight,
    cmd_preflight, cmd_launch, cmd_autonomous,
)

# ---------------------------------------------------------------------------
# Functions kept directly in portfolio.py (governance, agora, status, misc)
# ---------------------------------------------------------------------------


def cmd_record(args: argparse.Namespace) -> None:
    data = load(); item = variant(data, args.variant)
    observation = {"at": now(), "value": args.value, "resource_cost": args.resource_cost, "evidence_units": args.evidence_units, "guardrails": args.guardrails, "note": args.note}
    item["observations"].append(observation); item["status"] = "OBSERVED"; save(data)
    print(json.dumps(observation, indent=2))


def eligible(data: dict, item: dict) -> dict | None:
    if any(entry["guardrails"] == "fail" and not entry.get("invalidated_at") for entry in item["observations"]):
        return None
    observations = [entry for entry in item["observations"] if entry["guardrails"] == "pass" and not entry.get("invalidated_at")]
    evidence = sum(entry["evidence_units"] for entry in observations)
    if not observations or evidence < data["shared_contract"]["minimum_evidence"]:
        return None
    latest = observations[-1]
    return {"name": item["name"], "generation": item["generation"], "value": latest["value"], "system_contribution_bonus": float(item.get("system_contribution_bonus", 0)), "resource_cost": sum(entry["resource_cost"] for entry in observations), "evidence_units": evidence}


def ranking(data: dict, cohort: str | None = None) -> list[dict]:
    entries = [result for item in data["variants"].values() if (cohort is None or item.get("cohort") == cohort) and (result := eligible(data, item))]
    reverse = data["shared_contract"]["direction"] == "maximize"
    return sorted(entries, key=lambda item: (item["value"], item["system_contribution_bonus"], -item["resource_cost"]) if reverse else (-item["value"], item["system_contribution_bonus"], -item["resource_cost"]), reverse=True)


def cmd_rank(args: argparse.Namespace) -> None:
    data = load(); print(json.dumps(decision_report(data, cohort=args.cohort), indent=2))


def decision_report(data: dict, selected: str | None = None, cohort: str | None = None) -> dict:
    ranked = ranking(data, cohort); winner = selected or (ranked[0]["name"] if ranked else None)
    winner_entry = next((entry for entry in ranked if entry["name"] == winner), None)
    decisions = []
    for item in data["variants"].values():
        if cohort is not None and item.get("cohort") != cohort:
            continue
        failed = [entry for entry in item["observations"] if entry["guardrails"] == "fail" and not entry.get("invalidated_at")]
        candidate = next((entry for entry in ranked if entry["name"] == item["name"]), None)
        if failed:
            reason, disposition = "lost: at least one recorded guardrail failed", "REJECTED_GUARDRAIL"
        elif candidate is None:
            evidence = sum(entry["evidence_units"] for entry in item["observations"] if entry["guardrails"] == "pass" and not entry.get("invalidated_at"))
            reason, disposition = f"undecided: Evidence {evidence}/{data['shared_contract']['minimum_evidence']}", "INSUFFICIENT_EVIDENCE"
        elif item["name"] == winner:
            reason, disposition = "survived: best eligible declared metric; resource cost breaks only exact metric ties", "SELECTED"
        else:
            delta = candidate["value"] - winner_entry["value"] if winner_entry else None
            reason, disposition = f"lost current comparison: metric delta versus selected={delta}; Evidence retained", "NOT_SELECTED"
        decisions.append({"variant": item["name"], "generation": item["generation"], "disposition": disposition, "reason": reason})
    return {"metric": data["shared_contract"]["metric"], "direction": data["shared_contract"]["direction"], "cohort": cohort, "ranking": ranked, "decisions": decisions}


def cmd_select(args: argparse.Namespace) -> None:
    data = load(); ranked = ranking(data, args.cohort)
    if not ranked:
        raise SystemExit("No variant has passed guardrails with enough Evidence")
    winner = args.variant or ranked[0]["name"]
    if winner not in {item["name"] for item in ranked}:
        raise SystemExit("Selected variant is not eligible")
    report = decision_report(data, winner, args.cohort)
    previous = data.get("selected")
    if previous and previous != winner and data["variants"][previous]["status"] == "SELECTED":
        data["variants"][previous]["status"] = "RETAINED_SEED"
    data["selected"] = winner; data["variants"][winner]["status"] = "SELECTED"
    for decision in report["decisions"]:
        item = data["variants"][decision["variant"]]
        item["selection_decisions"].append({"at": now(), **decision})
        if decision["disposition"] != "SELECTED":
            item["status"] = (
                "REJECTED_INSUFFICIENT_EVIDENCE"
                if decision["disposition"] == "INSUFFICIENT_EVIDENCE"
                else decision["disposition"]
            )
    data["events"].append({"at": now(), "kind": "SELECTION_RECORDED", "variant": winner, "report": report})
    save(data); print(json.dumps(report, indent=2)); print(f"Selected {winner}; promotion still requires ordinary validation and acceptance")


def cmd_stop(args: argparse.Namespace) -> None:
    data = load(); item = variant(data, args.variant); item["status"] = "STOPPED"; item["stopped_at"] = now(); save(data)
    print("Marked STOPPED; worktree and Evidence retained. Remove only after review with git worktree remove.")


def cmd_review(args: argparse.Namespace) -> None:
    data = load(); variant(data, args.reviewer); variant(data, args.subject)
    if args.reviewer == args.subject:
        raise SystemExit("A peer review requires different reviewer and subject variants")
    review = {
        "id": f"review-{len(data['peer_reviews']) + 1}", "at": now(), "reviewer": args.reviewer,
        "subject": args.subject, "finding": args.finding, "evidence": args.evidence,
        "recommendation": args.recommendation, "confidence": args.confidence,
        "trust": "ADVISORY_UNTRUSTED_PEER_EVIDENCE", "authority_effect": "NONE",
    }
    data["peer_reviews"].append(review); data["peer_reviews"] = data["peer_reviews"][-500:]; save(data)
    print(json.dumps(review, indent=2))


def agora_proposal(data: dict, proposal_id: str) -> dict:
    try:
        return next(item for item in data["agora"]["proposals"] if item["id"] == proposal_id)
    except StopIteration:
        raise SystemExit(f"Unknown agora proposal: {proposal_id}") from None


def proposal_status(data: dict, proposal: dict) -> str:
    if any(item.get("proposal") == proposal["id"] for item in data["agora"].get("system_confirmations", [])):
        return "VALIDATED_SYSTEM_BENEFIT"
    decision = next((item for item in reversed(data["agora"].get("decisions", [])) if item.get("proposal") == proposal["id"]), None)
    if not decision:
        return "OPEN"
    return "ADOPTED" if decision["outcome"] == "adopt" else decision["outcome"].upper()


def agora_tally(data: dict, proposal_id: str) -> dict:
    proposal = agora_proposal(data, proposal_id)
    eligible_names = {item["name"] for item in data["variants"].values() if item.get("generation") == proposal["generation"]}
    effective = {}
    for vote in data["agora"]["votes"]:
        if vote["proposal"] == proposal_id and vote["voter"] in eligible_names:
            effective[vote["voter"]] = vote
    counts = {choice: sum(vote["choice"] == choice for vote in effective.values()) for choice in ("support", "oppose", "abstain")}
    eligible_count = len(eligible_names)
    return {**counts, "participation": len(effective), "required_participation": (eligible_count + 1) // 2, "eligible_variants": eligible_count, "effective_votes": list(effective.values())}


def cmd_agora_propose(args: argparse.Namespace) -> None:
    data = load(); item = variant(data, args.variant)
    if args.scope == "portfolio-system" and not all((args.necessity_evidence, args.experiment_benefit, args.invariants_preserved)):
        raise SystemExit("portfolio-system proposals require necessity Evidence, experiment-wide benefit, and preserved-invariant evidence")
    for field in ("decision", "rationale", "evidence", "counterevidence", "applicability", "expected_effect", "necessity_evidence", "experiment_benefit", "invariants_preserved"):
        setattr(args, field, bounded_text(getattr(args, field, None), field))
    proposal = {
        "id": f"proposal-{len(data['agora']['proposals']) + 1}", "at": now(),
        "proposer": item["name"], "generation": item["generation"], "decision": args.decision,
        "rationale": args.rationale, "supporting_evidence": args.evidence,
        "counterevidence": args.counterevidence, "applicability": args.applicability,
        "expected_effect": args.expected_effect, "status": "OPEN",
        "scope": args.scope, "necessity_evidence": args.necessity_evidence,
        "experiment_wide_benefit": args.experiment_benefit, "invariants_preserved": args.invariants_preserved,
        "trust": "ADVISORY_UNTRUSTED_VARIANT_PROPOSAL", "authority_effect": "NONE",
    }
    append_agora(data, "proposals", proposal)
    data["events"].append({"at": now(), "kind": "AGORA_PROPOSAL_SUBMITTED", "proposal": proposal["id"], "variant": item["name"]})
    save(data); print(json.dumps(proposal, indent=2))


def cmd_agora_vote(args: argparse.Namespace) -> None:
    data = load(); voter = variant(data, args.voter); proposal = agora_proposal(data, args.proposal)
    if proposal_status(data, proposal) != "OPEN":
        raise SystemExit("Voting is closed for this proposal")
    if voter.get("generation") != proposal.get("generation"):
        raise SystemExit("Only variants admitted to the proposal generation may vote")
    args.reason = bounded_text(args.reason, "reason"); args.evidence = bounded_text(args.evidence, "evidence")
    prior = next((vote for vote in reversed(data["agora"]["votes"]) if vote["proposal"] == args.proposal and vote["voter"] == args.voter), None)
    vote = {
        "id": f"vote-{len(data['agora']['votes']) + 1}", "at": now(), "proposal": args.proposal,
        "voter": args.voter, "choice": args.choice, "reason": args.reason,
        "evidence": args.evidence, "confidence": args.confidence,
        "supersedes": prior["id"] if prior else None, "weight": 1,
        "trust": "ADVISORY_UNTRUSTED_VARIANT_VOTE", "authority_effect": "NONE",
    }
    append_agora(data, "votes", vote); save(data)
    print(json.dumps({"vote": vote, "tally": agora_tally(data, args.proposal)}, indent=2))


def cmd_agora_decide(args: argparse.Namespace) -> None:
    data = load(); proposal = agora_proposal(data, args.proposal)
    if proposal_status(data, proposal) != "OPEN":
        raise SystemExit("Proposal already has a controller decision")
    tally = agora_tally(data, args.proposal)
    if proposal.get("scope", "candidate") == "portfolio-system" and args.outcome == "adopt":
        raise SystemExit("portfolio-system proposals may be referred for independent review, not adopted by variants")
    if args.outcome == "refer" and proposal.get("scope", "candidate") != "portfolio-system":
        raise SystemExit("only portfolio-system proposals use refer")
    if args.outcome in {"adopt", "refer"} and (tally["participation"] < tally["required_participation"] or tally["support"] < args.minimum_support or tally["support"] <= tally["oppose"]):
        raise SystemExit("Adoption requires majority participation, minimum support, and strictly more support than opposition")
    inheritance_parent = None
    if args.outcome == "adopt":
        inheritance_parent = args.inherit_from or data.get("selected")
        if not inheritance_parent or inheritance_parent != data.get("selected"):
            raise SystemExit("An adopted decision must inherit from the currently selected winner")
        variant(data, inheritance_parent)
    decision = {
        "id": f"decision-{len(data['agora']['decisions']) + 1}", "at": now(),
        "proposal": args.proposal, "outcome": args.outcome, "approved_by": args.approved_by,
        "reason": args.reason, "applicability": args.applicability or proposal["applicability"],
        "tally_at_decision": tally, "minimum_support": args.minimum_support,
        "inheritance_parent": inheritance_parent,
        "status": "SURVIVING_APPROVED_DECISION" if args.outcome == "adopt" else ("REFERRED_SYSTEM_REVIEW" if args.outcome == "refer" else args.outcome.upper()),
        "authority_effect": "NONE; INHERITANCE REQUIRES EXPLICIT CHILD LINK" if args.outcome == "adopt" else "NONE; SYSTEM CHANGE REQUIRES ORDINARY INDEPENDENT URACE REVIEW",
    }
    append_agora(data, "decisions", decision)
    data["events"].append({"at": now(), "kind": "AGORA_DECISION_RECORDED", "decision": decision["id"], "proposal": args.proposal, "outcome": args.outcome})
    save(data); print(json.dumps(decision, indent=2))


def cmd_agora_confirm_system(args: argparse.Namespace) -> None:
    data = load(); proposal = agora_proposal(data, args.proposal)
    if proposal.get("scope") != "portfolio-system" or proposal_status(data, proposal) != "REFER":
        raise SystemExit("system confirmation requires a referred portfolio-system proposal")
    if not args.invariants_preserved:
        raise SystemExit("system confirmation must affirm preserved selection, Authority, budget, isolation, and recovery invariants")
    bonus = min(args.bonus, 0.05)
    proposer = variant(data, proposal["proposer"])
    proposer["system_contribution_bonus"] = max(float(proposer.get("system_contribution_bonus", 0)), bonus)
    confirmation = {"id": f"system-confirmation-{len(data['agora']['system_confirmations']) + 1}", "at": now(), "proposal": args.proposal, "approved_by": args.approved_by, "validation_evidence": args.validation_evidence, "experiment_wide_benefit": args.experiment_benefit, "invariants_preserved": True, "bonus": bonus, "bonus_effect": "EXACT_PRIMARY_METRIC_TIE_BREAK_ONLY"}
    append_agora(data, "system_confirmations", confirmation); save(data)
    print(json.dumps(confirmation, indent=2))


def cmd_agora_show(args: argparse.Namespace) -> None:
    data = load()
    proposals = [{**item, "effective_status": proposal_status(data, item), "tally": agora_tally(data, item["id"])} for item in data["agora"]["proposals"]]
    print(json.dumps({"proposals": proposals, "decisions": data["agora"]["decisions"], "system_confirmations": data["agora"]["system_confirmations"]}, indent=2))


def cmd_lesson(args: argparse.Namespace) -> None:
    data = load()
    sources = [item.strip() for item in args.from_variants.split(",") if item.strip()]
    for source in sources: variant(data, source)
    lesson = {
        "id": f"lesson-{len(data['lessons']) + 1}", "at": now(), "source_variants": sources,
        "statement": args.statement, "supporting_evidence": args.evidence,
        "counterevidence": args.counterevidence, "applicability": args.applicability,
        "confidence": args.confidence, "approved_by": args.approved_by,
        "authority_effect": "NONE", "status": "APPROVED_LEARNING_INPUT",
    }
    data["lessons"].append(lesson); data["lessons"] = data["lessons"][-200:]; save(data)
    print(json.dumps(lesson, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    data = load(); print(json.dumps({**data, "current_decision_report": decision_report(data, data.get("selected"))}, indent=2))


def feedback_snapshot(data: dict) -> dict:
    automation = data.get("automation", {})
    cohort = automation.get("cohort")
    current = [item for item in data["variants"].values() if not cohort or item.get("cohort") == cohort]
    next_by_phase = {"IDLE": "plan the next generation", "PLANNED": "create the planned cohort", "CREATED": "mutate each candidate", "MUTATED": "evaluate each candidate", "EVALUATED": "select and archive"}
    variants_list = []
    for item in sorted(current, key=lambda entry: entry["name"]):
        valid_observations = [
            observation
            for observation in item.get("observations", [])
            if not observation.get("invalidated_at")
        ]
        latest = valid_observations[-1] if valid_observations else None
        variants_list.append({
            "name": item["name"], "status": item["status"], "metric_value": latest.get("value") if latest else None,
            "guardrails": latest.get("guardrails") if latest else "not measured", "evidence_units": latest.get("evidence_units", 0) if latest else 0,
            "executor_invocations": {"used": item.get("executor_invocations_used", 0), "hard_cap": item.get("executor_invocation_budget")},
            "resource_budget": item.get("resource_budget"), "system_contribution_bonus": item.get("system_contribution_bonus", 0),
            "priority_scope": item.get("priority_scope", "unattributed"),
        })
    proposals = data["agora"]["proposals"]
    return {
        "status": automation.get("status", "MANUAL"), "phase": automation.get("phase", "MANUAL"),
        "cohort_policy": {"mode": effective_cohort_policy(data), "explicit": "cohort_policy" in data},
        "accepted_state_source": {**effective_accepted_state_source(data), "resolved_commit": resolve_accepted_product_identity(data)},
        "accepted_product": data.get("accepted_product"),
        "generation": automation.get("generation", 0), "completed_generations": automation.get("cycles_completed", 0),
        "cohort": cohort, "selected": data.get("selected"), "next": next_by_phase.get(automation.get("phase"), "manual portfolio operation"),
        "planner_invocations": {"used": automation.get("planner_invocations_used", 0), "hard_cap": automation.get("planner_invocation_hard_cap")},
        "planner_stage": automation.get("planner_stage"),
        "controller_recovery": {
            "identical_failures": automation.get("identical_failure_count", 0),
            "status": automation.get("controller_repair_status", "NOT_NEEDED"),
            "attempts_this_generation": automation.get("controller_repair_attempts", {}).get(str(automation.get("generation", 0)), 0),
        },
        "executor_capacity": automation.get("executor_capacity", {"status": "AVAILABLE_OR_UNKNOWN"}),
        "executor_pool": automation.get("executor_pool", {}),
        "scope_priorities": automation.get("scope_priorities"),
        "goal_schedule": automation.get("goal_schedule"),
        "portfolio_worth": automation.get("portfolio_worth"),
        "pending_live_controls": len(list(CONTROL_INBOX.glob("*.json"))) if CONTROL_INBOX.exists() else 0,
        "variants": variants_list,
        "agora": {"open": sum(proposal_status(data, item) == "OPEN" for item in proposals), "referred": sum(proposal_status(data, item) == "REFER" for item in proposals), "validated_system_benefits": len(data["agora"].get("system_confirmations", [])), "surviving_decisions": sum(item["outcome"] == "adopt" for item in data["agora"]["decisions"])},
        "last_error": automation.get("last_error"), "limitations": ["provider calls inside an adapter require adapter-level hard caps", "built-in candidates use Codex sandboxed worktrees; custom commands require Bubblewrap", "mutually hostile tenants still require separate identities or machines and an authenticated broker"],
    }


def print_feedback(data: dict, as_json: bool = False) -> None:
    snapshot = feedback_snapshot(data)
    if as_json:
        print(json.dumps(snapshot, indent=2, sort_keys=True)); return
    print(f"Portfolio: {snapshot['status']} | phase={snapshot['phase']} | generation={snapshot['generation']} | completed={snapshot['completed_generations']}")
    print(f"Cohort policy: {snapshot['cohort_policy']['mode']} ({'explicit' if snapshot['cohort_policy']['explicit'] else 'default'})")
    source = snapshot["accepted_state_source"]
    print(f"Accepted-state source: {source['mode']}" + (f" | ref={source.get('ref')}" if source.get("ref") else "") + (f" | resolved={source.get('resolved_commit')}" if source.get("resolved_commit") else ""))
    print(f"Selected: {snapshot['selected'] or 'none'} | cohort={snapshot['cohort'] or 'none'} | next={snapshot['next']}")
    planner = snapshot["planner_invocations"]
    print(f"Planner invocations: {planner['used']} used" + (f" / {planner['hard_cap']} hard cap" if planner["hard_cap"] is not None else ""))
    if snapshot.get("planner_stage"):
        stage = snapshot["planner_stage"]
        print(f"Planner stage: {stage.get('status')} | transport attempts={stage.get('transport_attempts', 0)} | logical reservation reused={'yes' if stage.get('logical_reservation_reused') else 'no'}" + (f" | retry={stage.get('retry_at')}" if stage.get("retry_at") else ""))
    recovery = snapshot["controller_recovery"]
    print(f"Controller recovery: {recovery['status']} | identical failures={recovery['identical_failures']} | attempts this generation={recovery['attempts_this_generation']}")
    capacity = snapshot["executor_capacity"]
    print(f"Executor capacity: {capacity.get('status')}" + (f" | retry={capacity.get('retry_at')} | checkpoint={capacity.get('variant')}:{capacity.get('stage')}" if capacity.get('retry_at') else ""))
    pool = snapshot.get("executor_pool", {})
    provider_rows = [(n, v) for n, v in pool.items() if isinstance(v, dict) and n not in {"last_route"}]
    if provider_rows:
        print("Executor pool: " + ", ".join(f"{n}={'AVAILABLE' if v.get('available') else 'UNAVAILABLE'} recent-completions={len(v.get('completion_history', []))}" + (f" retry={v.get('retry_at')}" if v.get('retry_at') else "") for n, v in provider_rows))
    priorities = snapshot.get("scope_priorities")
    if priorities:
        detail = ", ".join(f"{n}={r['normalized_weight']} ({r['allocated_plans']} plans)" for n, r in priorities["scopes"].items())
        print(f"Scope priorities: {detail} | basis={priorities['basis']}")
    goals = snapshot.get("goal_schedule")
    if goals:
        selected = ", ".join(goals.get("selected_goal_ids", [])) or "none"
        print(f"Goal schedule: selected={selected} | cutoff={goals.get('evidence_cutoff')} | digest={goals.get('digest', '')[:12]}")
    worth = snapshot.get("portfolio_worth")
    if worth:
        print(f"Portfolio worth: {worth.get('decision')} | {worth.get('reasons', ['no reason recorded'])[0]} | {worth.get('basis')}")
    print(f"Pending live controls: {snapshot.get('pending_live_controls', 0)}")
    print("Candidates:")
    if not snapshot["variants"]: print("  none")
    for item in snapshot["variants"]:
        calls = item["executor_invocations"]; budget = item["resource_budget"] or {}
        print(f"  {item['name']}: {item['status']} | scope={item['priority_scope']} | metric={item['metric_value']} | guardrails={item['guardrails']} | evidence={item['evidence_units']} | executor={calls['used']}/{calls['hard_cap'] if calls['hard_cap'] is not None else '?'} | allocation={budget.get('allocated', '?')} {budget.get('unit', '')} | system-bonus={item['system_contribution_bonus']}")
    agora = snapshot["agora"]
    print(f"Agora: open={agora['open']} referred={agora['referred']} validated-system-benefits={agora['validated_system_benefits']} surviving-decisions={agora['surviving_decisions']}")
    print(f"Last error: {snapshot['last_error'] or 'none'}")
    print("Limits: " + "; ".join(snapshot["limitations"]))


def cmd_feedback(args: argparse.Namespace) -> None:
    print_feedback(load(), args.json)


def cmd_commands(args: argparse.Namespace) -> None:
    rows = [
        ("preflight WORKFLOW [--json]", "validate adapters, effects, frozen rules and hard caps without running them"),
        ("verify [--json]", "verify authenticated live ledger, Agora chain and archived segments"),
        ("launch WORKFLOW", "preflight, then run persistent resumable generations"),
        ("feedback [--json]", "read current activity, decisions, budgets, errors and next step"),
        ("auto WORKFLOW [--cycles X|infinity]", "run comparisons only while controller Evidence justifies their added cost"),
        ("next WORKFLOW", "complete one resumable generation"),
        ("autonomous --workflow FILE --cycles X|infinity", "explicit finite or persistent generations"),
        ("policy adaptive|always|off", "choose cost-aware comparison, continuous permission, or no new comparisons"),
        ("policy-status [--json]", "read the effective and explicitly stored cohort policy"),
        ("accepted-state-source lifecycle|repository [--ref REF]", "designate the accepted Product-state resolver; repository requires an authoritative ref"),
        ("accepted-state-source-status [--json]", "inspect the source, designated ref and resolved accepted commit"),
        ("status", "complete machine-readable ledger"), ("explain", "short lineage and selection explanation"),
        ("cohort / run-cohort", "create and run an equal-budget cohort"), ("agora-show", "inspect proposals, votes and decisions"),
        ("stop / record / review / agora-* / lesson", "apply immediately when idle or queue for the next safe boundary while autonomous ownership is active"),
    ]
    if args.json: print(json.dumps([{"command": a, "purpose": b} for a, b in rows], indent=2)); return
    for command, purpose in rows: print(f"{command}: {purpose}")


def cmd_auto(args: argparse.Namespace) -> None:
    data = load()
    if effective_cohort_policy(data) != "auto" or "cohort_policy" not in data:
        previous = effective_cohort_policy(data)
        data["cohort_policy"] = {"mode": "auto", "set_at": now(), "source": "portfolio auto command"}
        data.setdefault("events", []).append({"at": now(), "kind": "COHORT_POLICY_CHANGED", "from": previous, "to": "auto", "source": "portfolio auto command"})
        save(data)
    cmd_autonomous(argparse.Namespace(workflow=args.workflow, cycles=args.cycles))


def cmd_next(args: argparse.Namespace) -> None:
    cmd_autonomous(argparse.Namespace(workflow=args.workflow, cycles=1))


def cmd_explain(args: argparse.Namespace) -> None:
    data = load(); contract = data["shared_contract"]; report = decision_report(data, data.get("selected"))
    print(f"BASE {data['baseline']['commit'][:12]} context={data['baseline']['context_snapshot']}")
    print(f"OBJECTIVE {contract['objective']}")
    print(f"SELECTION {contract['direction']} {contract['metric']} minimum-evidence={contract['minimum_evidence']} selected={data.get('selected')}")
    for item in sorted(data["variants"].values(), key=lambda entry: (entry["generation"], entry["name"])):
        parent = item.get("parent_variant") or "BASE"
        print(f"G{item['generation']} {item['name']} <- {parent} status={item['status']}")
        print(f"  mutation: {item['mutation']}")
        print(f"  hypothesis: {item['hypothesis']}")
    print("DECISIONS")
    for decision in report["decisions"]:
        print(f"  {decision['variant']}: {decision['disposition']} — {decision['reason']}")
    surviving = sum(item["outcome"] == "adopt" for item in data["agora"]["decisions"])
    print(f"PEER REVIEWS {len(data.get('peer_reviews', []))} | APPROVED LESSONS {len(data.get('lessons', []))} | AGORA PROPOSALS {len(data['agora']['proposals'])} | SURVIVING DECISIONS {surviving}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Bounded competing variants using Git worktrees")
    sub = root.add_subparsers(dest="action", required=True)
    command = sub.add_parser("init"); command.add_argument("--objective", required=True); command.add_argument("--metric", required=True); command.add_argument("--direction", choices=["maximize", "minimize"], required=True); command.add_argument("--minimum-evidence", type=int, default=3); command.add_argument("--max-active", type=int, default=3); command.add_argument("--authority", required=True); command.add_argument("--guardrail-definition", required=True); command.add_argument("--evaluation-protocol", required=True); command.add_argument("--context-snapshot", required=True); command.set_defaults(function=cmd_init)
    command = sub.add_parser("spawn"); command.add_argument("variant", type=name); command.add_argument("--parent"); command.add_argument("--mutation", required=True); command.add_argument("--hypothesis", required=True); command.add_argument("--expected-effect", required=True); command.add_argument("--lesson", action="append", default=[]); command.add_argument("--decision", action="append", default=[]); command.set_defaults(function=cmd_spawn)
    command = sub.add_parser("cohort"); command.add_argument("--count", type=int, required=True); command.add_argument("--prefix", type=name, required=True); command.add_argument("--plan", required=True); command.add_argument("--parent"); command.add_argument("--total-resource-budget", type=float, required=True); command.add_argument("--resource-unit", required=True); command.set_defaults(function=cmd_cohort, resume=False)
    command = sub.add_parser("run-cohort"); command.add_argument("cohort", type=name); command.add_argument("--timeout", type=float, default=300); command.add_argument("--max-parallel", type=int); command.add_argument("command", nargs=argparse.REMAINDER); command.set_defaults(function=cmd_run_cohort)
    command = sub.add_parser("run"); command.add_argument("variant", type=name); command.add_argument("--timeout", type=float, default=300); command.add_argument("command", nargs=argparse.REMAINDER); command.set_defaults(function=cmd_run)
    command = sub.add_parser("autonomous"); command.add_argument("--workflow", required=True); command.add_argument("--cycles", type=parse_cycle_limit, default=1); command.set_defaults(function=cmd_autonomous)
    command = sub.add_parser("policy"); command.add_argument("mode", choices=sorted(COHORT_POLICY_ALIASES)); command.set_defaults(function=cmd_policy)
    command = sub.add_parser("policy-status"); command.add_argument("--json", action="store_true"); command.set_defaults(function=cmd_policy_status)
    command = sub.add_parser("accepted-state-source"); command.add_argument("mode", choices=sorted(ACCEPTED_STATE_SOURCES)); command.add_argument("--ref"); command.set_defaults(function=cmd_accepted_state_source)
    command = sub.add_parser("accepted-state-source-status"); command.add_argument("--json", action="store_true"); command.set_defaults(function=cmd_accepted_state_source_status)
    command = sub.add_parser("preflight"); command.add_argument("workflow"); command.add_argument("--json", action="store_true"); command.set_defaults(function=cmd_preflight)
    command = sub.add_parser("verify"); command.add_argument("--json", action="store_true"); command.set_defaults(function=cmd_verify)
    command = sub.add_parser("launch"); command.add_argument("workflow"); command.set_defaults(function=cmd_launch)
    command = sub.add_parser("auto"); command.add_argument("workflow"); command.add_argument("--cycles", type=parse_cycle_limit, default=None); command.set_defaults(function=cmd_auto)
    command = sub.add_parser("next"); command.add_argument("workflow"); command.set_defaults(function=cmd_next)
    command = sub.add_parser("record"); command.add_argument("variant", type=name); command.add_argument("--value", type=float, required=True); command.add_argument("--resource-cost", type=float, default=0); command.add_argument("--evidence-units", type=int, default=1); command.add_argument("--guardrails", choices=["pass", "fail"], required=True); command.add_argument("--note", default=""); command.set_defaults(function=cmd_record)
    command = sub.add_parser("rank"); command.add_argument("--cohort", type=name); command.set_defaults(function=cmd_rank)
    command = sub.add_parser("select"); command.add_argument("variant", nargs="?", type=name); command.add_argument("--cohort", type=name); command.set_defaults(function=cmd_select)
    command = sub.add_parser("stop"); command.add_argument("variant", type=name); command.set_defaults(function=cmd_stop)
    command = sub.add_parser("review"); command.add_argument("reviewer", type=name); command.add_argument("subject", type=name); command.add_argument("--finding", required=True); command.add_argument("--evidence", required=True); command.add_argument("--recommendation", required=True); command.add_argument("--confidence", type=unit_interval, required=True); command.set_defaults(function=cmd_review)
    command = sub.add_parser("agora-propose"); command.add_argument("variant", type=name); command.add_argument("--decision", required=True); command.add_argument("--rationale", required=True); command.add_argument("--evidence", required=True); command.add_argument("--counterevidence", required=True); command.add_argument("--applicability", required=True); command.add_argument("--expected-effect", required=True); command.add_argument("--scope", choices=["candidate", "portfolio-system"], default="candidate"); command.add_argument("--necessity-evidence"); command.add_argument("--experiment-benefit"); command.add_argument("--invariants-preserved"); command.set_defaults(function=cmd_agora_propose)
    command = sub.add_parser("agora-vote"); command.add_argument("voter", type=name); command.add_argument("proposal", type=name); command.add_argument("--choice", choices=["support", "oppose", "abstain"], required=True); command.add_argument("--reason", required=True); command.add_argument("--evidence", required=True); command.add_argument("--confidence", type=unit_interval, required=True); command.set_defaults(function=cmd_agora_vote)
    command = sub.add_parser("agora-decide"); command.add_argument("proposal", type=name); command.add_argument("--outcome", choices=["adopt", "refer", "reject", "defer"], required=True); command.add_argument("--approved-by", required=True); command.add_argument("--reason", required=True); command.add_argument("--applicability"); command.add_argument("--minimum-support", type=int, default=1); command.add_argument("--inherit-from", type=name); command.set_defaults(function=cmd_agora_decide)
    command = sub.add_parser("agora-confirm-system"); command.add_argument("proposal", type=name); command.add_argument("--approved-by", required=True); command.add_argument("--validation-evidence", required=True); command.add_argument("--experiment-benefit", required=True); command.add_argument("--invariants-preserved", action="store_true"); command.add_argument("--bonus", type=unit_interval, default=0); command.set_defaults(function=cmd_agora_confirm_system)
    sub.add_parser("agora-show").set_defaults(function=cmd_agora_show)
    sub.add_parser("rotate-integrity-key").set_defaults(function=cmd_rotate_integrity_key)
    command = sub.add_parser("lesson"); command.add_argument("--from-variants", required=True); command.add_argument("--statement", required=True); command.add_argument("--evidence", required=True); command.add_argument("--counterevidence", required=True); command.add_argument("--applicability", required=True); command.add_argument("--confidence", type=unit_interval, required=True); command.add_argument("--approved-by", required=True); command.set_defaults(function=cmd_lesson)
    sub.add_parser("explain").set_defaults(function=cmd_explain)
    sub.add_parser("status").set_defaults(function=cmd_status)
    command = sub.add_parser("feedback"); command.add_argument("--json", action="store_true"); command.set_defaults(function=cmd_feedback)
    command = sub.add_parser("commands"); command.add_argument("--json", action="store_true"); command.set_defaults(function=cmd_commands)
    return root


if __name__ == "__main__":
    args = parser().parse_args()
    args.function(args)
