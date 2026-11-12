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

from .cli_emit import _emit_compaction_event

def start_default_portfolio_owner(config: dict[str, Any], *, quiet: bool = False, json_mode: bool = False) -> subprocess.Popen[str] | None:
    """Attach adaptive portfolio work to the persistent owner when it is installed and initialized."""
    state_root = state_path(config).parent
    workflow = state_root / "portfolio-workflow.json"
    ledger = state_root / "portfolio" / "portfolio.json"
    helper = RUNTIME_ROOT / "urace" / "portfolio.py"
    if not (workflow.is_file() and ledger.is_file() and helper.is_file()):
        return None
    try:
        policy = json.loads(ledger.read_text(encoding="utf-8")).get("cohort_policy", {}).get("mode", "auto")
    except (OSError, json.JSONDecodeError):
        return None
    if policy == "disabled":
        return None
    child = subprocess.Popen(
        [sys.executable, str(helper), "autonomous", "--workflow", str(workflow), "--cycles", "infinity"],
        cwd=ROOT, text=True,
        stdout=subprocess.DEVNULL if quiet else (sys.stderr if json_mode else None),
        stderr=subprocess.DEVNULL if quiet else None,
    )
    def stop_child() -> None:
        if child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.terminate(); child.wait(timeout=5)
    atexit.register(stop_child)
    return child


def attached_portfolio_activity(config: dict[str, Any], owner: subprocess.Popen[str] | None) -> dict[str, Any] | None:
    """Report delegated comparison work without calling its Executor or mutating its ledger."""
    if owner is None or owner.poll() is not None:
        return None
    ledger = state_path(config).parent / "portfolio" / "portfolio.json"
    try:
        automation = json.loads(ledger.read_text(encoding="utf-8")).get("automation", {})
    except (OSError, json.JSONDecodeError):
        return None
    phase = automation.get("phase", "IDLE")
    planner = automation.get("planner_stage") or {}
    active = automation.get("status") == "RUNNING" and (phase != "IDLE" or planner.get("status") == "RUNNING")
    if not active:
        return None
    return {"phase": phase, "generation": automation.get("generation"), "planner_stage": planner.get("status")}




@contextmanager
def refresh_analytics(config: dict[str, Any], state: dict[str, Any]) -> None:
    settings = config.get("analytics_export", {})
    if settings.get("mode") != "ON_CHECKPOINT":
        return
    output = Path(settings.get("output", "urace/generated/reports/latest"))
    if not output.is_absolute(): output = ROOT / output
    try:
        analytics.export_portable(ROOT, state, vitals_snapshot(config, state), output, include_xlsx=bool(settings.get("include_xlsx", False)))
    except Exception as error:
        print(f"urace: analytics export warning: {error}", file=sys.stderr)


def record_executor_failure(state: dict[str, Any], stage: str, error: str, systematic_threshold: int = 3) -> None:
    executor_state = state.setdefault("executor_state", {})
    failures = executor_state.setdefault("failures", [])
    existing = next((item for item in reversed(failures) if item.get("stage") == stage and item.get("error") == error), None)
    if existing:
        existing.update({"last_at": now(), "count": int(existing.get("count", 1)) + 1})
        if int(existing["count"]) >= systematic_threshold and not existing.get("systematic"):
            existing["systematic"] = True
            fallback = float(state.get("config", {}).get("executor", {}).get("capacity_fallback_seconds", 18000))
            cooldown_until = (datetime.now(timezone.utc) + timedelta(seconds=fallback)).isoformat()
            executor_state["systematic_failure_cooldown_until"] = cooldown_until
            executor_state["systematic_failure_stage"] = stage
            executor_state["systematic_failure_error_class"] = error[:120]
    else:
        failures.append({"at": now(), "last_at": now(), "stage": stage, "error": error, "count": 1})
    if len(failures) > 100:
        _emit_compaction_event(state, "executor_failures", len(failures) - 100)
        failures[:] = failures[-100:]


def record_blocker(
    state: dict[str, Any],
    scope: str,
    reason: str,
    classification: str = "PERSISTENT",
    evidence_id: str | None = None,
    auto_clear_on: str | None = None,
) -> None:
    blockers = state.setdefault("blockers", [])
    existing = next(
        (item for item in reversed(blockers)
         if item.get("scope") == scope and item.get("reason") == reason and item.get("resolved_at") is None),
        None,
    )
    if existing:
        new_count = int(existing.get("count", 1)) + 1
        existing.update({"last_at": now(), "count": new_count})
        if evidence_id and not existing.get("evidence_id"):
            existing["evidence_id"] = evidence_id
        if auto_clear_on and not existing.get("auto_clear_on"):
            existing["auto_clear_on"] = auto_clear_on
        _escalation_order = {"TRANSIENT": 0, "PERSISTENT": 1, "ESCALATION": 2, "OPERATOR_GATE": 3}
        if _escalation_order.get(classification, 1) > _escalation_order.get(existing.get("classification", "PERSISTENT"), 1):
            existing["classification"] = classification
        _maybe_auto_escalate(existing, state)
    else:
        blocker: dict[str, Any] = {
            "id": identifier("blocker"),
            "at": now(),
            "last_at": now(),
            "scope": scope,
            "reason": reason,
            "count": 1,
            "resolved_at": None,
            "classification": classification,
            "evidence_id": evidence_id,
            "auto_clear_on": auto_clear_on,
            "escalation_due": None,
        }
        blockers.append(blocker)
    blockers[:] = [b for b in blockers if b.get("resolved_at") is None][-100:]


def _maybe_auto_escalate(blocker: dict[str, Any], state: dict[str, Any]) -> None:
    if blocker.get("classification") in ("ESCALATION", "OPERATOR_GATE"):
        return
    count = int(blocker.get("count", 1))
    if count < 5:
        return
    try:
        created = datetime.fromisoformat(blocker["at"].replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - created).total_seconds()
    except (KeyError, ValueError):
        return
    if age_seconds > 3600:
        blocker["classification"] = "ESCALATION"
        blocker["escalation_due"] = (datetime.now(timezone.utc) + timedelta(seconds=3600)).strftime("%Y-%m-%dT%H:%M:%SZ")
        state.setdefault("integrity_gaps", []).append({
            "id": identifier("igap"),
            "at": now(),
            "kind": "blocker-escalated",
            "severity": "WARNING",
            "blocker_id": blocker["id"],
            "scope": blocker.get("scope", ""),
            "active": True,
        })


def _auto_resolve_blockers(state: dict[str, Any]) -> None:
    now_ts = datetime.now(timezone.utc)
    for blocker in state.get("blockers", []):
        if blocker.get("resolved_at") is not None:
            continue
        classification = blocker.get("classification", "PERSISTENT")
        if classification == "OPERATOR_GATE":
            continue
        if classification == "TRANSIENT":
            try:
                last = datetime.fromisoformat(blocker["last_at"].replace("Z", "+00:00"))
                if (now_ts - last).total_seconds() > 600:
                    blocker["resolved_at"] = now_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
                    state.setdefault("evidence", []).append({
                        "id": identifier("evidence"),
                        "at": now(),
                        "kind": "blocker-transient-expired",
                        "blocker_id": blocker["id"],
                        "scope": blocker.get("scope", ""),
                    })
            except (KeyError, ValueError):
                pass


def record_assessment_gap(
    state: dict[str, Any],
    cycle_id: str,
    dimension: str,
    reason: str,
    minimum_met: str,
    blocking: bool,
) -> dict[str, Any]:
    """Create or update an AssessmentGap (agap-). Deduplication contract: same
    cycle_id+dimension MUST update last_at rather than append a new record."""
    gaps: list[dict] = state.setdefault("assessment_gaps", [])
    ts = now()
    for gap in gaps:
        if gap.get("cycle_id") == cycle_id and gap.get("dimension") == dimension and gap.get("resolved_at") is None:
            gap["last_at"] = ts
            gap["reason"] = reason
            gap["minimum_met"] = minimum_met
            gap["blocking"] = blocking
            return gap
    gap = {
        "id": identifier("agap"),
        "at": ts,
        "last_at": ts,
        "cycle_id": cycle_id,
        "dimension": dimension,
        "reason": reason,
        "minimum_met": minimum_met,
        "blocking": blocking,
        "resolved_at": None,
    }
    gaps.append(gap)
    return gap


def resolve_assessment_gap(state: dict[str, Any], cycle_id: str, dimension: str) -> bool:
    """Set resolved_at on a matching active AssessmentGap. Returns True if found."""
    ts = now()
    for gap in state.get("assessment_gaps", []):
        if gap.get("cycle_id") == cycle_id and gap.get("dimension") == dimension and gap.get("resolved_at") is None:
            gap["resolved_at"] = ts
            return True
    return False


def transaction_is_accepted(state: dict[str, Any], transaction_id: str) -> bool:
    return any(checkpoint.get("transaction") == transaction_id for checkpoint in state.get("checkpoints", []))


def reconcile_transaction(config: dict[str, Any], root: Path | None = None) -> str | None:
    root = ROOT if root is None else Path(root).resolve()
    journal_path = transaction_path(config)
    if not journal_path.exists():
        return None
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    path = state_path(config)
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    accepted = transaction_is_accepted(state, journal["id"])
    before,after=journal.get('before'),journal.get('after')
    if not isinstance(before,dict) or not isinstance(after,dict) or set(before)!=set(after):
        raise RuntimeError('Recovery journal file sets conflict; preserving state and journal')
    for relative in before:
        if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or not (root/relative).resolve().is_relative_to(root.resolve()) or (root/relative).is_symlink():
            raise RuntimeError('Recovery journal path escapes Product scope; preserving journal')
        if not isinstance(before[relative],str) or not isinstance(after[relative],str):raise RuntimeError('Invalid recovery contents; preserving journal')
        current=(root/relative).read_text(encoding='utf-8') if (root/relative).exists() else None
        # Legacy APPLYING journals allowed partial, non-atomic writes. New journals
        # declare atomic replacement, so unexpected bytes are an owner conflict.
        legacy_partial = journal.get('recovery_protocol') is None and journal.get('phase') == 'APPLYING' and relative in journal.get('applied', [])
        if current not in (before[relative],after[relative]) and not legacy_partial:
            raise RuntimeError('Recovery conflicts with owner edits; preserving current files and journal')
    selected = after if accepted else before
    for relative, content in selected.items():
        atomic_write_text(root / relative, content)
    durable_unlink(journal_path)
    disposition = "ROLLED_FORWARD" if accepted else "ROLLED_BACK"
    if state:
        state.setdefault("evidence", []).append({
            "id": identifier("evidence"), "at": now(), "kind": "transaction-recovery",
            "transaction": journal["id"], "disposition": disposition,
        })
        save_state(config, state)
    return disposition


def finalize_committed_transaction(config: dict[str, Any], state: dict[str, Any]) -> None:
    journal_path = transaction_path(config)
    if not journal_path.exists():
        return
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if transaction_is_accepted(state, journal["id"]):
        durable_unlink(journal_path)


def stable_path(config: dict[str, Any]) -> Path:
    return state_path(config).parent / "stable"


def runtime_files(config: dict[str, Any]) -> list[str]:
    if config.get("product_bootstrap") and not config.get("executor",{}).get("allowed_files_by_scope",{}).get("runtime"):return []
    files = [item for item in config["executor"]["allowed_files_by_scope"]["runtime"] if item.startswith("urace/runtime/")]
    # Recovery includes the installed workflow extension without granting native
    # executors permission to modify that extension or any deployment evidence.
    core = ROOT / 'urace/runtime/urace'
    if core.is_dir():
        files.extend(str(path.relative_to(ROOT)) for path in core.glob('*.py') if path.is_file() and not path.is_symlink())
    tests=ROOT/'urace/runtime/tests'
    if tests.is_dir():files.extend(str(path.relative_to(ROOT)) for path in tests.glob('*.py') if path.is_file() and not path.is_symlink())
    trial = ROOT / 'urace/trial'
    if trial.is_dir():
        for path in trial.iterdir():
            if path.is_file() and not path.is_symlink() and (path.suffix == '.py' or path.name in
                    {'urace','empty-mcp.json','efficiency.example.json','harness-manifest.json','runtime-qualification-config.json','runtime-cycle-installation.json','qualification-dependencies.json'}):
                files.append(str(path.relative_to(ROOT)))
    runtime_base = ROOT / 'urace/runtime'
    if runtime_base.is_dir():
        for path in runtime_base.iterdir():
            if path.is_file() and not path.is_symlink() and path.name.endswith('.json'):
                files.append(str(path.relative_to(ROOT)))
    return sorted(set(files))


def runtime_stable_path(config: dict[str, Any]) -> Path:
    return state_path(config).parent / "stable-runtime"


def write_runtime_snapshot(config: dict[str, Any]) -> None:
    directory = runtime_stable_path(config)
    files = {}
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        current = set(runtime_files(config))
        for relative in set(prior.get("files", {})) - current:
            obsolete = directory / relative
            durable_unlink(obsolete)
            parent = obsolete.parent
            while parent != directory and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    for relative in runtime_files(config):
        content = (ROOT / relative).read_text(encoding="utf-8")
        atomic_write_text(directory / relative, content)
        files[relative] = hashlib.sha256(content.encode()).hexdigest()
    atomic_write_json(manifest_path, {"accepted_at": now(), "files": files})


def validate_product(config: dict[str, Any], baseline_metrics: dict[str, float] | None = None) -> list[str]:
    errors = []
    bootstrap=config.get("product_bootstrap")
    if bootstrap:
        purpose=ROOT/bootstrap["original_intent_path"]
        if purpose.is_symlink() or not purpose.is_file() or hashlib.sha256(purpose.read_bytes()).hexdigest()!=bootstrap["intent_sha256"]:errors.append("Original owner intent changed or unavailable")
    required = {
        "URACE.md": ["# URACE", "Primary invariant:", "# 79. Bootstrap Execution Requirements"],
        "README.md": ["# URACE", "## Get Running", "## Use It"],
    }
    for relative in config["product_files"]:
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if len(text) < (1 if bootstrap else 1000):
            errors.append(f"{relative} is unexpectedly short")
        if text.count("```") % 2 and not (bootstrap and relative==bootstrap["original_intent_path"]):
            errors.append(f"{relative} has an unclosed fenced block")
        for marker in required.get(relative, []):
            if marker not in text:
                errors.append(f"{relative} lost required marker: {marker}")
        if relative == "URACE.md" and not re.search(r"(?m)^# \d+\. Final Invariant[ \t]*$", text):
            errors.append("URACE.md lost required heading: Final Invariant")
    if baseline_metrics:
        current = document_metrics(config)
        for name in ("normative_rules", "behavioral_tests"):
            if current[name] < baseline_metrics.get(name, 0):
                errors.append(f"{name} regressed from stable baseline")
    return errors


def write_stable_snapshot(config: dict[str, Any]) -> None:
    directory = stable_path(config)
    directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for relative in config["product_files"]:
        path = ROOT / relative
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        atomic_write_text(directory / relative, content)
        files[relative] = hashlib.sha256(content.encode()).hexdigest()
    atomic_write_json(directory / "manifest.json", {"accepted_at": now(), "files": files, "metrics": document_metrics(config)})


def ensure_stable_product(config: dict[str, Any], state: dict[str, Any]) -> bool:
    manifest_path = stable_path(config) / "manifest.json"
    if not manifest_path.exists():
        errors = validate_product(config)
        if errors:
            raise RuntimeError("cannot establish stable Product snapshot: " + "; ".join(errors))
        write_stable_snapshot(config)
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = validate_product(config)
    if errors:
        raise RuntimeError("current Product failed structural validation; files were preserved: " + "; ".join(errors))
    current = {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
               for relative in config["product_files"] if (ROOT / relative).exists()}
    if current == manifest.get("files", {}):
        return False
    previous = dict(manifest.get("files", {}))
    prior_lifecycle = state.get("lifecycle_state", "DORMANT")
    state["lifecycle_state"] = "RECONCILING"
    write_stable_snapshot(config)
    reconciliation_id = identifier("evidence")
    state.setdefault("evidence", []).append({
        "id": reconciliation_id, "at": now(), "kind": "external-product-reconciliation",
        "previous_files": previous, "current_files": current,
        "disposition": "ACCEPTED_CURRENT_SOURCE_WITH_NEW_SNAPSHOT",
    })
    state.setdefault("executor_state", {})["discovery_trigger"] = {"reason": "product-file change detected", "signature": reconciliation_id}
    state["lifecycle_state"] = prior_lifecycle
    return True


def product_digest(config: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for item in sorted(config["product_files"]):
        path = ROOT / item
        if path.exists():
            digest.update(item.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _product_digest_at(config: dict[str, Any], before_snapshot: dict[str, str]) -> str:
    """Product digest computed from a before-snapshot dict (path → content string).
    Used for state_before_digest in Change bindings so no disk re-read is needed."""
    digest = hashlib.sha256()
    for item in sorted(config["product_files"]):
        if item in before_snapshot:
            digest.update(item.encode())
            digest.update(before_snapshot[item].encode("utf-8"))
        else:
            path = ROOT / item
            if path.exists():
                digest.update(item.encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def initial_state(config: dict[str, Any] | None = None) -> dict[str, Any]:
    if config is None:
        config = load_config()
    observed = document_metrics(config)
    created = now()
    profile = {
        "id": "blueprint-verification",
        "objective_reference": "continuous-improvement",
        "intended_outcome": "Increase verified blueprint quality without weakening invariants",
        "measures": {
            key: {
                "baseline": value,
                "current": value,
                "previous": None,
                "target": value if key != "unresolved_markers" else 0.0,
                "direction": "nondecreasing" if key != "unresolved_markers" else "nonincreasing",
            }
            for key, value in observed.items()
        },
        "guardrails": ["normative_rules must not decrease", "behavioral_tests must not decrease"],
        "cadence": "each autonomous cycle or product change",
        "next_follow_up": created,
        "status": "active",
        "created_at": created,
        "updated_at": created,
    }
    return {
        "schema_version": 1,
        "state_version": 0,
        "created_at": created,
        "updated_at": created,
        "lifecycle_state": "DORMANT",
        "intent": config["intent"],
        "authority": config["authority"],
        "constraints": config["constraints"],
        "self_evolution_policy": config.get("self_evolution_policy", {"mode": "NECESSARY_ONLY", "source": "bootstrap default", "provenance": "no attributable selection supplied; NECESSARY_ONLY applied per §74+§79 default"}),
        "objectives": [],
        "current_objective": None,
        "current_plan": None,
        "operations": [],
        "evidence": [],
        "decision_records": [],
        "integrity_gaps": [],
        "assessment_gaps": [],
        "lifecycle_boundaries": [],
        "integrity_signals": [],
        "status_transitions": [],
        "checkpoints": [{"id": identifier("checkpoint"), "at": created, "kind": "bootstrap", "digest": product_digest(config)}],
        "progress_profiles": [profile],
        "progress_observations": [],
        "metric_system": {"version": 1, "last_review_at": None, "last_assessment": "bootstrap metrics", "change_needed": False, "change_history": []},
        "evaluation_system": {**config.get("evaluation_system", {"version": 1, "minimum_evidence_units": 5, "weights": {}}), "last_review_at": None, "last_assessment": "bootstrap evaluation system", "change_needed": False, "change_history": []},
        "scope_priority_system": scope_priority.derive(ROOT, config, {"objectives": [], "operations": []}),
        "external_metric_state": {
            "mode": config.get("external_metrics", {}).get("mode", "DISABLED"),
            "source": config.get("external_metrics", {}).get("source", "bootstrap default"),
            "provenance": config.get("external_metrics", {}).get("provenance", "no attributable selection supplied"),
            "last_collection": None, "latest": [], "errors": [],
        },
        "operator_patterns": config.get("operator_patterns", []),
        "context_inputs": [],
        "connector_sources": [],
        "metric_definitions": [],
        "vital_definitions": [],
        "processed_input_ids": [],
        "pattern_memory": {},
        "reasoning_memory": [],
        "unresolved_effects": [],
        "pending_validations": [],
        "destination_anchor": destination_anchor.anchor_from_config(config),
        "value_trajectory": {"checkpoints": [], "acceleration": None, "established_at": created, "cumulative_value": 0.0, "peak_velocity": 0.0},
        "rule_ledger": rule_ledger_module.seed_from_config(config),
        "wake_registry": [],
        "blockers": [],
        "last_cycle": None,
        "executor_state": {
            "last_discovery_at": None,
            "last_operation_at": None,
            "last_availability_check": None,
            "available": None,
            "failures": [],
            "executor_calls": [],
            "discovery_calls": 0,
            "provider_pool": {},
            "discovery_budget_status": "WITHIN_BUDGET",
            "unproductive_discovery_streak": 0,
            "progress_vector": None,
            "progress_stagnant_cycles": 0,
            "execution_budget": None,
            "recovery_manifest": None,
        },
        "spec_audit_state": None,
        "derived_manifest_refs": [],
        "derivation_records": [],
        "derivation_refs": [],
        "construct_set_refs": [],
        "quality_deltas": [],
        "quality_state": {},
        "reingestion_records": [],
        "sweet_spot_assessments": [],
        "capability_states": [],
        "value_density_history": [],
        "product_versions": [],
        "test_run_records": [],
        "policy_records": [],
        "hard_constraints": [],
        "assessment_records": [],
        "discovery_records": [],
        "ownership_markers": [],
        "market_signals": [],
        "fit_hypotheses": [],
        "compliance_records": [],
        "compliance_state": {},
        "community_feeds": [],
        "community_signals": [],
        "patch_proposals": [],
        "onboard_records": [],
        "switch_records": [],
        "fleet_records": [],
        "trace_records": [],
        "outcome_feedback_records": [],
        "resource_ledger": [],
        "roi_snapshots": [],
        "gap_calibration_records": [],
        "directive_mutation_records": [],
        "state_audit_records": [],
        "executor_trust_profiles": [],
        "contention_decision_records": [],
        "external_edit_records": [],
        "unsupported_intent_records": [],
        "lifecycle_inheritance_records": [],
        "objective_scope_declarations": [],
        "evidence_sufficiency_snapshots": [],
        "evidence_age_retirement_records": [],
        "operator_decision_escalation_records": [],
        "rollback_completeness_attestations": [],
        "metric_registry": [],
        "adaptive_config_proposals": [],
            "intent_formula_validity_records": [],
            "authority_ceiling_records": [],
            "intent_ambiguity_audit_records": [],
            "goal_coverage_completeness_records": [],
            "strategic_review_records":           [],
            "domain_weight_records":              [],
            "evidence_requests":                  [],
        "state_transition_validation_records": [],
        "intent_drift_records":                [],
        "intent_aggregate_gap_records":        [],
        "gap_impact_estimates":                [],
        "causal_edge_records":                  [],
        "causal_model_records":                 [],
        "lookahead_plan_records":               [],
        "principal_records":                    [],
        "authority_conflict_records":           [],
        "adversarial_signal_records":           [],
        "uncertainty_bands":                    [],
        "fleet_knowledge_records":              [],
        "constraint_candidates":                [],
        "explanation_records":                  [],
        "portfolio_allocation_records":         [],
        "deadline_records":                     [],
        "goal_tree_nodes":                      [],
        "objective_dependency_records":         [],
        "intent_version_records":               [],
        "self_modification_records":            [],
        "normative_violation_records":          [],
        "value_ledger_entries":                 [],
        "attention_budget_records":             [],
        "policy_override_records":              [],
        "event_trigger_records":                [],
        "degradation_records":                  [],
        "state_space_audit_records":            [],
        "feedback_latency_records":             [],
        "resource_conflict_records":            [],
        "schema_migration_records":             [],
        "rollback_records":                     [],
        "fleet_resource_registry":              {},
        "last_self_modification_cycle":     0,
        "bootstrap_file_hashes":            {},
        "normative_halt_records":           [],
        "value_calibration_factor":         1.0,
        "transform_records":                [],
        # r117
        "data_source_records":          [],
        "credential_records":           [],
        "data_sync_records":            [],
        "route_graph_records":          [],
    }


def seed_confirmed_onboard(config: dict, state: dict) -> None:
    """Inject a pre-confirmed OnboardRecord into state so OnboardGate passes.
    Used in tests to bypass the onboarding ceremony for states that represent
    an already-onboarded product. Idempotent — does nothing if a matching
    active record already exists.
    """
    product_name = config.get("product", "")
    onboard_records = state.setdefault("onboard_records", [])
    already = any(
        r.get("product_name") == product_name and not r.get("superseded_at")
        for r in onboard_records
    )
    if already:
        return
    confirmed_at = now()
    onboard_records.append({
        "id": identifier("onb-"),
        "created_at": confirmed_at,
        "product_name": product_name,
        "confirmed_by": "test-seed",
        "confirmed_at": confirmed_at,
        "config_digest": product_digest(config),
        "gates_passed": ["config-completeness", "product-files-readable", "intent-anchored"],
        "notes": None,
    })


# ── Spec version (relocated from lifecycle for dep ordering) ─────────────────

def _current_spec_version() -> str:
    """Return the current URACE spec version string, or 'unknown' if unreadable."""
    spec_path = ROOT / "URACE.md"
    try:
        return spec_audit_module.extract_spec_version(spec_path.read_text(encoding="utf-8")) or "unknown"
    except (OSError, AttributeError):
        return "unknown"
