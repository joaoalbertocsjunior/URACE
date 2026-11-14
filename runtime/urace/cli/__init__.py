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

from .. import executor as intelligent_executor
from .. import external_metrics
from .. import analytics
from .. import scope_priority
from .. import updater
from .. import authority as authority_resolver
from .. import destination as destination_anchor
from .. import validation as independent_validation
from .. import value_trajectory
from .. import outcome_verification
from .. import rules as rule_ledger_module
from .. import spec_audit as spec_audit_module
from ..primitives import OUTPUT_SCHEMA_REGISTRY, INTEGRITY_GAP_CATALOG as IGC_KINDS
from .. import decision_record as decision_record_module
from .. import compaction as compaction_module
from .. import cognitive_resume as cognitive_resume_module
from .. import patterns as pattern_catalog_module
from .. import continuation as continuation_module
from .._common import nullable_limit
from .. import auto_goals, user_controls, command_surface, api_interface, freeform_routing, data_transport
# Keep build_parser and parse_cycles available from urace.cli for existing API callers.
from ..cli_parser import build_parser, dispatch_parser, parse_cycles

from .._common import (
    ROOT, CONFIG_PATH, RUNTIME_ROOT, SYSTEM_ROOT,
    now, identifier, atomic_write_text, atomic_write_json, durable_unlink,
    process_exists, state_lock, load_config, save_config, state_path, load_state,
    load_state_for_read, save_state, transaction_path, input_directory,
)
from ..inputs import consume_inputs, queue_input, cleanup_consumed_inputs, apply_pending_inputs
from ..inspection import (
    document_metrics, compare, objective_is_eligible, goal_is_schedulable,
    objective_score, objective_score_breakdown, goal_portfolio,
    work_evaluations, context_view, resource_accounting,
    executor_efficiency_vital, evolution_vital, render, vitals_snapshot,
    render_vitals, render_cycle, command_catalog, top_level_help,
)

# ── Re-exports from extracted sub-modules (backward-compat) ──────────────────
from ..cli_emit import (
    _emit_gap, _emit_trace, _emit_compaction_event, _emit_compliance_record,
)
from ..cli_output import (
    _utcnow, _session_context_path, _load_session_context, _save_session_turn,
    _render_report_html, _json_to_xml, _print_fmt, _XmlConvertStream,
    _validate_freeform_query, _resolve_scope_target,
)
from ..cli_state import (
    start_default_portfolio_owner, attached_portfolio_activity, refresh_analytics,
    record_executor_failure, record_blocker, _maybe_auto_escalate, _auto_resolve_blockers,
    record_assessment_gap, resolve_assessment_gap, transaction_is_accepted,
    reconcile_transaction, finalize_committed_transaction, stable_path, runtime_files,
    runtime_stable_path, write_runtime_snapshot, validate_product, write_stable_snapshot,
    ensure_stable_product, product_digest, _product_digest_at, initial_state,
    seed_confirmed_onboard, _current_spec_version,
)
from ..cli_lifecycle import (
    _update_progress_vector, _emit_recovery_manifest, observe_progress, discover,
    plan_for, refresh_scope_priorities, material_state_signature, executor_discovery_due,
    _check_stale_derived_manifests, spec_audit_due, run_spec_audit,
    executor_execution_allowed, defer_executor_capacity, _retain_call_usage,
    _current_route_usage, _executor_readiness_capability, refresh_executor_availability,
    discover_with_executor, _transition, execute_with_executor, core_fault_descriptor,
    runtime_version_digest, attempt_core_auto_repair, _evaluate_wake_conditions,
    _run_onboard_gate, _verify_wake_registrations,
)
from ..cli_helpers import (
    _inspect_list, _help_action, _mutate_command,
    _apply_effect_uncertainty_protocol, _apply_operator_gate, _determine_revalidation_scope,
    _check_authority_closure, _sha256_digest, _observe_retention_gaps,
    _validate_citizen_base_conformance, _validate_immutable_fields, _compact_with_chunking,
    _validate_authority_basis_binding, _ledger_size_warning, _build_inspection_surface,
    _try_reconcile_effect, _reconcile_unresolved_effects, _executor_independent_work,
    _check_scheduled_tasks, _record_quality_delta, _check_staleness,
    _regression_checkpoint_gate_passes, _apply_customizations, _evaluate_sweet_spot,
    _capability_envelope_gate_passes, _derive_capabilities_from_patterns,
    _derive_milestone_from_state, _refresh_derived_refs, _refresh_derived_construct_sets,
    _refresh_derived_manifests, _print_derive_update_suggestions, _suggest_derive_updates,
)
from ..cli_cycle import (
    _csi_relevance_score, _csi_confidence_score, _signal_quality, _run_csi,
    _run_ppm, _run_feedback_accumulator, _run_ram, _try_p2p_feature,
    _ts_age, _routing_decision, cycle, emit_cycle_feedback, emit_auto_startup,
)



# r62: Built-in FeatureBundle registry (§62j)
BUILTIN_BUNDLES: dict[str, list[str]] = {
    "community-inbox": [
        "AP38", "CSI", "PPP_M", "PPP",
        "CommunityFeed", "CommunitySignal", "PatchProposal",
        "FeatureBundle", "FeatureBundleRef",
    ],
}

_KNOWN_TOP_COMMANDS = {
    # lifecycle control
    "auto", "pause", "resume", "init", "bootstrap", "activate",
    # inspection
    "status", "check", "vitals", "rules", "change", "commands", "inspect", "why", "crc",
    # input/data management
    "add", "classify", "declare", "add-goal", "add-context", "add-source", "add-metric", "add-vital",
    "inbox", "context", "source", "metric", "vital", "analytics", "derive",
    # governance
    "intent", "constraint", "goal", "policy", "budget", "evaluation",
    "self-evolution", "configuration",
    # executor/plan
    "executor", "executor-capacity", "plan", "portfolio",
    # update/evolution
    "update", "repair", "repair-controller", "amend", "reset",
    # compaction/export
    "compact", "decompact", "compress", "decompress", "export", "report",
    # quality/resilience
    "quality",
    "compliance",
    # milestone versioning
    "milestone",
    # lifecycle shortcuts
    "start", "stop", "run",
    # interactive control shell
    "shell",
    # curses monitoring dashboard (explicit)
    "dashboard",
    # other
    "help", "schedule-task",
    # onboarding
    "onboard",
    # product registry
    "product",
    # fleet orchestration
    "fleet",
    # new commands r73
    "evidence", "blocker", "decision", "integrity-signal", "govern", "autonomous",
    # r75
    "trace",
    # r77
    "schema", "feedback",
    # r85
    "resource",
    # r93
    "api",
    # r117
    "data", "trial",
    # r113 ExplanationProtocol
    "explain",
    # runtime improvement feed
    "watch",
    # granular controls and ledger search
    "controls", "search",
    # system health
    "doctor",
    # qualification audit
    "qualification",
    # crypto wallet
    "crypto",
    # freeform text routing
    "freeform-text",
    # background daemon loop
    "daemon",
    # unified M2M JSON entry point
    "m2m",
    # rollback
    "rollback",
    # features
    "features",
    # config show-all
    "config",
    # security audit
    "security",
    # top-level exchange shorthand
    "exchange",
    # github / git / gh integration
    "github", "git", "gh",
    # binary content references
    "content",
    # usage analytics
    "usage",
}

_KNOWN_TOP_COMMANDS -= command_surface.PHANTOMS

# SD=True: canonical exact-match aliases — heuristically classifiable at command time
# MUST be conservative: only exact matches to known commands/aliases, no fuzzy matching
_SD_TRUE_EXACT: dict[str, list[str]] = {
    # single-word direct mappings
    "check": ["check"],
    "vitals": ["vitals"],
    "pause": ["pause"],
    "resume": ["resume"],
    "help": ["help"],
    "rules": ["rules", "list"],
    "status": ["status"],
    "stop": ["pause"],
    "start": ["resume"],
    # two-word exact patterns
    "rules list": ["rules", "list"],
    "rules graph": ["rules", "graph"],
    "rules conflicts": ["rules", "conflicts"],
    "change list": ["change", "list"],
    "goal list": ["goal", "list"],
    "vitals check": ["vitals"],
    "check status": ["check"],
    # onboard / product / fleet exact patterns
    "onboard status": ["onboard", "status"],
    "onboard confirm": ["onboard", "confirm"],
    "product list": ["product", "list"],
    "product status": ["product", "status"],
    "fleet status": ["fleet", "status"],
    "fleet run": ["fleet", "run"],
    "fleet stop": ["fleet", "stop"],
    "fleet broadcast": ["fleet", "broadcast"],
    # r73 new commands
    "evidence list": ["evidence", "list"],
    "blocker list": ["blocker", "list"],
    "blocker resolve": ["blocker", "resolve"],
    "decision list": ["decision", "list"],
    "decision inspect": ["decision", "inspect"],
    "integrity-signal list": ["integrity-signal", "list"],
    "govern list-gates": ["govern", "list-gates"],
    "govern clear": ["govern", "clear"],
    # r75 trace
    "trace list": ["trace", "list"],
    "trace inspect": ["trace", "inspect"],
    # r77 schema + feedback
    "schema list": ["schema", "list"],
    "schema inspect": ["schema", "inspect"],
    "schema export": ["schema", "export"],
    "feedback list": ["feedback", "list"],
    # r85 resource budget
    "resource status": ["resource", "status"],
    "resource report": ["resource", "report"],
    "resource help": ["resource", "help"],
    # r86 help subcommand routing (all SD=True)
    "inbox help": ["inbox", "help"],
    "onboard help": ["onboard", "help"],
    "product help": ["product", "help"],
    "fleet help": ["fleet", "help"],
    "trace help": ["trace", "help"],
    "feedback help": ["feedback", "help"],
    "update help": ["update", "help"],
    "schema help": ["schema", "help"],
    # r93 api command routing
    "api help": ["api", "help"],
    "api call": ["api", "call"],
    "api batch": ["api", "batch"],
    # r98 api extensions
    "api watch": ["api", "watch"],
    "api version": ["api", "version"],
    # r101: add subcommands (canonical)
    "add context": ["add", "context"],
    "add goal": ["add", "goal"],
    "add source": ["add", "source"],
    "add metric": ["add", "metric"],
    "add vital": ["add", "vital"],
    "add evidence": ["add", "evidence"],
    # backwards compat: declare aliases → add (r100 deprecated forms)
    "declare context": ["add", "context"],
    "declare goal": ["add", "goal"],
    "declare source": ["add", "source"],
    "declare metric": ["add", "metric"],
    "declare vital": ["add", "vital"],
}

def _preprocess_args(raw_args: list[str]) -> list[str]:
    """Three-tier routing.

    Tier 0: /command  → direct, zero cost, always works
    Tier 1: SD=True exact match → direct, zero cost
    Tier 1b: known command pass-through → argparse (recovery in main)
    Tier 2: everything else → executor via classify handler (internal, freeform)
    """
    if len(raw_args)>=2 and raw_args[0] in ('status','/status') and raw_args[1]=='scores':
        return ['trial','status','scores',*raw_args[2:]]
    if not raw_args or (raw_args[0].startswith("-") and raw_args[0] not in {"--json","--format"} and not raw_args[0].startswith("--format=")):
        return raw_args
    first = raw_args[0]
    if first in {"--json","--format"} or first.startswith("--format="):
        prefix=[];rest=list(raw_args)
        while rest:
            if rest[0]=="--json" or rest[0].startswith("--format="):prefix.append(rest.pop(0))
            elif rest[0]=="--format" and len(rest)>1:prefix.extend([rest.pop(0),rest.pop(0)])
            else:break
        return prefix+_preprocess_args(rest) if rest else raw_args

    # Routing flags outside quoted prose are controls, not part of the operator text.
    if first not in _KNOWN_TOP_COMMANDS and first.lstrip("/") not in _KNOWN_TOP_COMMANDS:
        for index,token in enumerate(raw_args[1:],1):
            if token in {"--json","--format","--confirm","--selection","--p2p-asset"} or token.startswith(("--format=","--selection=","--p2p-asset=")):
                text=" ".join(raw_args[:index])
                return ["classify",text[1:] if text.startswith("/") else text,*raw_args[index:]]

    # Tier 0: slash-prefixed direct command
    if first.startswith("/"):
        stripped = first[1:]
        if stripped in _KNOWN_TOP_COMMANDS:
            return [stripped] + raw_args[1:]
        # Unknown slash → free-form (strip the /)
        free_text = (stripped + (" " + " ".join(raw_args[1:])) if raw_args[1:] else stripped).strip()
        sd = _SD_TRUE_EXACT.get(free_text.lower())
        return list(sd) if sd is not None else ["classify", free_text]

    # Tier 1: full-input SD=True exact match (aliases + natural phrases)
    full = " ".join(raw_args).strip()
    sd = _SD_TRUE_EXACT.get(full.lower())
    if sd is not None:
        return list(sd)

    # Tier 1b: known command — pass to argparse; main() handles recovery
    if first in _KNOWN_TOP_COMMANDS:
        return raw_args

    # Tier 2: executor classification via internal classify handler
    return ["classify", full]


def _handle_data_credential_command(args: Any, state: dict[str, Any], fmt: str) -> None:
    """Compatibility wrapper for the data-source credential handler."""
    from ..data_cli import handle_data_credential_command
    return handle_data_credential_command(args, state, fmt, identifier=identifier)


def _handle_data_command(args: Any, state: dict, config: dict) -> int:
    """Compatibility wrapper; data command behavior lives in data_cli."""
    from ..data_cli import handle_data_command
    return handle_data_command(args, state, config, identifier=identifier,
                               emit_gap=_emit_gap, state_path=state_path)


def _handle_source_add_unified(args: Any, config: dict, parser: Any) -> int:
    """Dispatch `urace source add --kind <kind>` to underlying add handlers."""
    kind = getattr(args, "kind", None)
    if not kind:
        parser.error("source add requires --kind (file|csv|json|sqlite|api|connector|executor|metric|vital|github|product|peer)")
    _name = getattr(args, "id", None) or getattr(args, "name", None) or ""
    _fmt = ["--json"] if getattr(args, "format", None) == "json" else []

    if kind in {"file", "csv", "json", "sqlite", "api"}:
        _argv = ["data", "add", _name,
                 "--type", getattr(args, "adapter_kind", None) or kind,
                 "--connect", getattr(args, "dsn", None) or ""]
        _argv += ["--direction", getattr(args, "direction", "read")]
        if not getattr(args, "auto", True):
            _argv += ["--auto", "false"]
        if getattr(args, "schema_hint", None):
            _argv += ["--schema", args.schema_hint]
        return main(_argv + _fmt)

    if kind == "connector":
        _loc = getattr(args, "location", None) or ""
        if not _loc:
            parser.error("source add --kind connector requires --location")
        print("Note: `urace add source` is also available for connector sources.", file=sys.stderr)
        _argv = ["add", "source", _name, "--kind", "connector",
                 "--location", _loc, "--visibility", getattr(args, "visibility", "private")]
        if getattr(args, "credential_env", None):
            _argv += ["--credential-env", args.credential_env]
        return main(_argv + _fmt)

    if kind == "executor":
        _argv = ["executor", "attach"]
        if _name:
            _argv += ["--id", _name]
        if getattr(args, "executor_binary", None):
            _argv += ["--command", args.executor_binary]
        if getattr(args, "adapter", None):
            _argv += ["--adapter", args.adapter]
        _argv += ["--priority", str(getattr(args, "priority", 100))]
        for cap in (getattr(args, "capability", []) or []):
            _argv += ["--capability", cap]
        for cp in (getattr(args, "capability_priority", []) or []):
            _argv += ["--capability-priority", cp]
        if getattr(args, "max_calls_24h", None) is not None:
            _argv += ["--max-calls-24h", str(args.max_calls_24h)]
        if getattr(args, "max_calls_30d", None) is not None:
            _argv += ["--max-calls-30d", str(args.max_calls_30d)]
        return main(_argv + _fmt)

    if kind == "metric":
        _mname = _name
        _src = getattr(args, "metric_source", None) or ""
        _path = getattr(args, "metric_path", None) or ""
        if not _mname:
            parser.error("source add --kind metric requires a name (positional id or --name)")
        if not _src:
            parser.error("source add --kind metric requires --metric-source")
        if not _path:
            parser.error("source add --kind metric requires --metric-path")
        print("Note: `urace add metric` is also available directly.", file=sys.stderr)
        _dir = getattr(args, "direction", "nondecreasing")
        if _dir not in {"nondecreasing", "nonincreasing"}:
            _dir = "nondecreasing"
        _argv = ["add", "metric", _mname, "--source", _src, "--path", _path, "--direction", _dir]
        if getattr(args, "metric_target", None) is not None:
            _argv += ["--target", str(args.metric_target)]
        return main(_argv + _fmt)

    if kind == "vital":
        _vname = _name
        _num = getattr(args, "numerator", None) or ""
        if not _vname:
            parser.error("source add --kind vital requires a name (positional id or --name)")
        if not _num:
            parser.error("source add --kind vital requires --numerator")
        print("Note: `urace add vital` is also available directly.", file=sys.stderr)
        _argv = ["add", "vital", _vname, "--numerator", _num]
        if getattr(args, "denominator", None):
            _argv += ["--denominator", args.denominator]
        if getattr(args, "window", None):
            _argv += ["--window", args.window]
        if getattr(args, "description", None):
            _argv += ["--description", args.description]
        return main(_argv + _fmt)

    if kind == "github":
        _repo = getattr(args, "repo", None) or _name or ""
        if not _repo:
            parser.error("source add --kind github requires --repo owner/repo")
        print("Note: `urace github connect` is also available directly.", file=sys.stderr)
        _argv = ["github", "connect", _repo]
        if getattr(args, "token_env", None):
            _argv += ["--token-env", args.token_env]
        return main(_argv + _fmt)

    if kind == "product":
        if not _name:
            parser.error("source add --kind product requires a product id (positional id or --name)")
        _argv = ["product", "register", _name]
        return main(_argv + _fmt)

    if kind == "peer":
        _target = _name or getattr(args, "location", None) or ""
        if not _target:
            parser.error("source add --kind peer requires an address (positional id or --location)")
        _argv = ["exchange", "network", "peer-add", _target]
        return main(_argv + _fmt)

    parser.error(f"unknown source kind: {kind}")
    return 1  # unreachable


def _build_route_graph(prompt: str, state: dict) -> dict:
    """Decompose a multi-intent prompt into a RouteGraphRecord (r117 §62w)."""
    # Split on semantic connectives
    sub_intents = re.split(r'\s+(?:and|then|also|after(?:\s+that)?)\s+|,\s*', prompt, flags=re.IGNORECASE)
    sub_intents = [s.strip() for s in sub_intents if s.strip()]

    nodes = []
    edges = []
    for i, sub in enumerate(sub_intents):
        node_id = f"rn-{i}"
        route_type = "COMMAND"
        target = "freeform"
        confidence = 0.7
        if re.search(r'\bdata\b|\bsync\b|\bpush\b|\bdatabase\b|\bfile\b', sub, re.IGNORECASE):
            route_type = "DATA_OPERATION"
            target = "data"
        nodes.append({
            "node_id": node_id,
            "route_type": route_type,
            "target": target,
            "confidence": confidence,
            "args": {"text": sub},
            "status": "PENDING",
        })
        if i > 0:
            edges.append({
                "from_node_id": f"rn-{i-1}",
                "to_node_id": node_id,
                "dependency_type": "SEQUENTIAL",
            })

    conflict_pairs: list = []
    threshold = 0.5
    min_conf = min(n["confidence"] for n in nodes) if nodes else 1.0
    dispatch_tier = "AUTO" if min_conf >= threshold and not conflict_pairs else "CONFIRM"

    rgr = {
        "id": identifier("rgr-"),
        "prompt": prompt,
        "route_nodes": nodes,
        "route_edges": edges,
        "conflict_pairs": conflict_pairs,
        "dispatch_tier": dispatch_tier,
        "status": "PENDING",
    }
    state["route_graph_records"].append(rgr)
    return rgr


def run(state: dict, cfg: dict) -> int:
    """Thin shim for tests: parse sys.argv[1:] and dispatch data/route commands
    against the provided in-memory state and config.  Only handles the commands
    that test code needs to drive without touching the filesystem.
    """
    raw = list(sys.argv[1:])
    if not raw:
        return 0
    command = raw[0]
    if command != "data":
        # Fall through to main() for everything else
        return main(raw)

    # Build a minimal parser for the data sub-command
    parser = argparse.ArgumentParser(prog="urace data", add_help=False)
    data_sub = parser.add_subparsers(dest="data_action")

    da = data_sub.add_parser("add")
    da.add_argument("name")
    da.add_argument("--type", dest="adapter_kind", required=True)
    da.add_argument("--connect", dest="dsn", required=True)
    da.add_argument("--direction", choices=["read", "write", "both"], default="read")
    da.add_argument("--label", default="")
    da.add_argument("--format", choices=["text", "json"], default="text")
    da.add_argument("--auto", type=command_surface.boolean, default=True,
                    help="Auto-sync changed readable local sources (default true); writes require explicit push")
    da.add_argument("--schema", dest="schema_hint", default=None,
                    help="Schema hint (table, sheet, collection name)")

    du = data_sub.add_parser("update")
    du.add_argument("name")
    du.add_argument("--type", dest="adapter_kind", default=None)
    du.add_argument("--connect", dest="dsn", default=None)
    du.add_argument("--direction", choices=["read", "write", "both"], default=None)
    du.add_argument("--label", default=None)
    du.add_argument("--format", choices=["text", "json"], default="text")
    du.add_argument("--auto", type=command_surface.boolean, default=None)
    du.add_argument("--schema", dest="schema_hint", default=None)

    dr = data_sub.add_parser("remove")
    dr.add_argument("name")
    dr.add_argument("--format", choices=["text", "json"], default="text")

    dl = data_sub.add_parser("list")
    dl.add_argument("--type", dest="adapter_kind", default=None)
    dl.add_argument("--format", choices=["text", "json"], default="text")
    dl.add_argument("--direction", choices=["read", "write", "both"], default=None)
    dl.add_argument("--status", choices=["CONNECTED", "DISCONNECTED", "DEGRADED", "PENDING"], default=None)

    ds = data_sub.add_parser("sync")
    ds.add_argument("name")
    ds.add_argument("--format", choices=["text", "json"], default="text")

    dp = data_sub.add_parser("push")
    dp.add_argument("name")
    dp.add_argument("--input-json",dest="data_input_json")
    dp.add_argument("--format", choices=["text", "json"], default="text")

    di = data_sub.add_parser("inspect")
    di.add_argument("name")
    di.add_argument("--format", choices=["text", "json"], default="text")

    dv = data_sub.add_parser("verify", help="Test connectivity without data transfer")
    dv.add_argument("name", help="Data source name")
    dv.add_argument("--format", choices=["text", "json"], default="text")

    dstat = data_sub.add_parser("status", help="Health overview of all data sources")
    dstat.add_argument("--format", choices=["text", "json"], default="text")

    data_cred = data_sub.add_parser("credential", help="Manage credentials for a data source")
    data_cred_sub = data_cred.add_subparsers(dest="credential_action")

    data_cred_add = data_cred_sub.add_parser("add", help="Attach a credential")
    data_cred_add.add_argument("name", help="Data source name")
    data_cred_add.add_argument("--auth", dest="auth_kind", required=True,
        choices=["DSN", "API_KEY", "OAUTH2", "CERT", "BASIC", "KERBEROS", "IAM_ROLE", "VAULT_PATH", "ENV_VAR"])
    data_cred_add.add_argument("--ref", dest="secret_ref", required=True,
        help="Pointer to secret (env var name, vault path)")
    data_cred_add.add_argument("--expires", dest="expires_at", default=None, help="ISO-8601 expiry")
    data_cred_add.add_argument("--format", choices=["text", "json"], default="text")

    data_cred_remove = data_cred_sub.add_parser("remove", help="Detach credential")
    data_cred_remove.add_argument("name", help="Data source name")
    data_cred_remove.add_argument("--format", choices=["text", "json"], default="text")

    data_cred_inspect = data_cred_sub.add_parser("inspect", help="Show credential metadata")
    data_cred_inspect.add_argument("name", help="Data source name")
    data_cred_inspect.add_argument("--format", choices=["text", "json"], default="text")

    try:
        args = parser.parse_args(raw[1:])
    except SystemExit:
        raise
    return _handle_data_command(args, state, cfg)




def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    from ..runtime_product import mutation_blocker
    _blocked=mutation_blocker(SYSTEM_ROOT,raw_args)
    if _blocked:
        print(json.dumps({'status':'DEFERRED','reason':_blocked,'schema':'runtime-transaction-admission-v1'}));return 2

    if raw_args and raw_args[0] == "trial":
        from ..trial import main as trial_main
        return trial_main(raw_args[1:])
    explicit_classifier=bool(raw_args and raw_args[0].lstrip("/")=="classify")
    raw_args = _preprocess_args(raw_args)
    if not raw_args:
        import sys as _sys
        if hasattr(_sys.stdout,'isatty') and _sys.stdout.isatty():
            try:_shell_cfg=load_config()
            except Exception:_shell_cfg={}
            from .. import _daemon as _dm, shell as _sh
            _pid=_dm._read_pid(_shell_cfg)
            if not _pid or not _dm._is_running(_pid):
                import argparse as _ap2, threading as _thr2, time as _t2
                _da=_ap2.Namespace(command='daemon',daemon_action='start',
                                   json=False,format=None,interval_minutes=30.0,
                                   max_cycles=0,cycles=0)
                _thr2.Thread(target=_dm.dispatch,args=(_da,_shell_cfg),daemon=True).start()
                _t2.sleep(0.3)  # let daemon write pid before shell checks status
            return _sh.run_shell(_shell_cfg)
        else:
            from .. import tui as _tui
            try:_tui_cfg=load_config()
            except Exception:_tui_cfg={}
            return _tui.launch(_tui_cfg,SYSTEM_ROOT)
    if raw_args in (["help"], ["-h"], ["--help"]):
        print(top_level_help())
        return 0
    parser = dispatch_parser()
    if not explicit_classifier:
        prefix_end=0
        while prefix_end<len(raw_args):
            token=raw_args[prefix_end]
            if token=="--json" or token.startswith("--format="):prefix_end+=1
            elif token=="--format":prefix_end+=2
            else:break
        if len(raw_args)>prefix_end+1 and raw_args[prefix_end]=="classify":
            matched=command_surface.match_quoted_command(parser,raw_args[prefix_end+1])
            if matched:raw_args=[*raw_args[:prefix_end],*matched,*raw_args[prefix_end+2:]]
    _original_raw = raw_args[:]
    args, _unknown = parser.parse_known_args(raw_args)
    # r106: unify --json and --format into canonical _fmt; wrap stdout for XML conversion
    # Scan raw_args for top-level --format (subparser default=None can shadow it)
    _top_fmt: str | None = None
    for _i, _arg in enumerate(raw_args):
        if _arg == "--format" and _i + 1 < len(raw_args):
            _top_fmt = raw_args[_i + 1]
        elif _arg.startswith("--format="):
            _top_fmt = _arg.split("=", 1)[1]
        elif _arg in ("--json", "--json=true"):
            if _top_fmt is None:
                _top_fmt = "json"
    _fmt = getattr(args, "format", None) or _top_fmt or None
    if not hasattr(args,"format"):args.format=None
    if args.command=='api':
        _server_flags=any(x.split('=')[0] in {'--transport','--policy','--port','--token-env'} for x in raw_args)
        if _server_flags and args.action!='serve':parser.error('Server options require api serve')
        if args.action=='serve' and args.transport!='a2a' and any(x.split('=')[0] in {'--port','--token-env'} for x in raw_args):parser.error('--port/--token-env require --transport a2a')
        if args.action=='serve' and args.transport=='a2a' and not 0<=args.port<=65535:parser.error('A2A port must be between 0 and 65535')
        if args.action=='serve' and any(x.split('=')[0] in {'--command','--argv','--params','--input-json','--stream','--follow'} for x in raw_args):parser.error('api serve owns stdio; nested calls and streaming wrappers are not applicable')
    if args.command in {'derive','update'} and getattr(args,'verify',False) and getattr(args,'no_verify',False):parser.error('--verify conflicts with --no-verify')
    args.json = bool(_fmt)  # always set for handler backward compat
    if _fmt == "xml":
        sys.stdout = _XmlConvertStream(sys.stdout)
    from .. import preflight as _preflight_module
    try:_pf_cfg=load_config()
    except Exception:_pf_cfg={}
    _preflight_hints=_preflight_module.hints(_pf_cfg,SYSTEM_ROOT)
    if not args.json and _preflight_hints:
        for _h in _preflight_hints:print(f"hint [{_h['level']}]: {_h['message']} — {_h['action']}",file=sys.stderr)
    if args.command=='features':
        from .. import runtime_features as _rf
        _feat_action=getattr(args,'action',None) or 'list'
        if _feat_action=='summary':
            _feat_data=_rf.summary()
            if args.json:print(json.dumps(_feat_data,indent=2));return 0
            for _s,_c in sorted(_feat_data.items()):print(f"  {_s:<14}{_c}")
            return 0
        if _feat_action=='show':
            _feat=_rf.get(args.feature_id)
            if _feat is None:print(f"unknown feature: {args.feature_id}",file=sys.stderr);return 1
            if args.json:print(json.dumps(_feat,indent=2));return 0
            for _k,_v in _feat.items():print(f"  {_k:<22}{_v}")
            return 0
        if _feat_action=='candidates':
            _feats=_rf.improvement_candidates()
            if args.json:print(json.dumps(_feats,indent=2));return 0
            print(f"  {'id':<35} {'status':<12} {'coverage':<8} name")
            for _f in _feats:print(f"  {_f['id']:<35} {_f['status']:<12} {_f['test_coverage']:<8} {_f['name']}")
            return 0
        _status_f=getattr(args,'status',None);_tag_f=getattr(args,'tag',None)
        _feats=_rf.all_features()
        if _status_f:_feats=[_f for _f in _feats if _f['status']==_status_f]
        if _tag_f:_feats=[_f for _f in _feats if _tag_f in _f['tags']]
        if args.json:print(json.dumps(_feats,indent=2));return 0
        print(f"  {'id':<35} {'status':<12} {'coverage':<8} name")
        for _f in _feats:
            _bl=' [blockers: '+','.join(_f.get('blockers',[]))+']' if _f.get('blockers') else ''
            print(f"  {_f['id']:<35} {_f['status']:<12} {_f['test_coverage']:<8} {_f['name']}{_bl}")
        return 0
    if args.command == 'rollback':
        try:
            _rb_config = load_config()
        except Exception as _e:
            print(json.dumps({'status': 'ERROR', 'error': str(_e)}) if args.json else f"error: {_e}", file=sys.stderr)
            return 1
        _snap_dir = stable_path(_rb_config)
        _manifest_path = _snap_dir / "manifest.json"
        if not _manifest_path.exists():
            _msg = "no stable snapshot available; run a full cycle first"
            print(json.dumps({'status': 'ERROR', 'error': _msg}) if args.json else f"error: {_msg}", file=sys.stderr)
            return 1
        _manifest = json.loads(_manifest_path.read_text(encoding="utf-8"))
        _snap_files = _manifest.get("files", {})
        _restores = []
        for _rel, _snap_hash in _snap_files.items():
            _snap_src = _snap_dir / _rel
            if not _snap_src.exists():
                _restores.append({"file": _rel, "status": "missing_in_snapshot"})
                continue
            _live = ROOT / _rel
            _live_hash = hashlib.sha256(_live.read_bytes()).hexdigest() if _live.exists() else None
            if _live_hash == _snap_hash:
                _restores.append({"file": _rel, "status": "unchanged"})
            else:
                _restores.append({"file": _rel, "status": "would_restore" if getattr(args, 'dry_run', False) else "restored"})
                if not getattr(args, 'dry_run', False):
                    atomic_write_text(_live, _snap_src.read_text(encoding="utf-8"))
        _result = {"status": "DRY_RUN" if getattr(args, 'dry_run', False) else "OK",
                   "snapshot_at": _manifest.get("accepted_at", "unknown"), "files": _restores}
        if args.json:
            print(json.dumps(_result, indent=2))
        else:
            _tag = "[dry-run] " if getattr(args, 'dry_run', False) else ""
            print(f"{_tag}stable snapshot from {_result['snapshot_at']}")
            for _f in _restores:
                print(f"  {_f['status']:<20} {_f['file']}")
        return 0
    if args.command == 'peer-review':
        from .. import peer_improvement as _pi
        _pr_action = getattr(args, 'action', None) or 'list'
        if _pr_action == 'list':
            _bundles = _pi.list_quarantined(SYSTEM_ROOT)
            if args.json:
                print(json.dumps(_bundles, indent=2))
            else:
                if not _bundles:
                    print("  no quarantined peer artifacts")
                else:
                    print(f"  {'bundle_id':<20} {'feature':<20} {'bytes':>8}  sender")
                    for _b in _bundles:
                        import datetime as _dt
                        _age = round((time.time() - _b['created_unix']) / 86400, 0)
                        print(f"  {_b['bundle_id'][:18]:<20} {_b['feature']:<20} {_b['artifact_bytes']:>8}  {_b['sender']} ({int(_age)}d ago)")
            return 0
        if _pr_action == 'evaluate':
            try:
                _report = _pi.evaluate(SYSTEM_ROOT, args.bundle_id)
            except (FileNotFoundError, ValueError) as _e:
                print(json.dumps({'status': 'error', 'error': str(_e)}) if args.json else f"error: {_e}", file=sys.stderr)
                return 1
            if args.json:
                print(json.dumps(_report, indent=2))
            else:
                print(f"  bundle:   {_report['bundle_id']}")
                print(f"  verdict:  {_report['verdict']}")
                print(f"  feature:  {_report['feature']}")
                print(f"  bytes:    {_report['artifact_bytes']}")
                print(f"  age:      {_report['age_days']}d")
                print(f"  signals:  {_report['relevant_signals']}")
                if _report['issues']:
                    for _iss in _report['issues']:
                        print(f"  issue:    {_iss}")
            return 0 if _report['verdict'] != 'UNSAFE' else 1
        if _pr_action == 'promote':
            try:
                _rb_config = load_config()
                _rb_state = load_state(_rb_config)
            except Exception as _e:
                print(json.dumps({'status': 'error', 'error': str(_e)}) if args.json else f"error: {_e}", file=sys.stderr)
                return 1
            try:
                _result = _pi.promote(SYSTEM_ROOT, args.bundle_id, _rb_config, _rb_state)
            except (FileNotFoundError, ValueError) as _e:
                print(json.dumps({'status': 'error', 'error': str(_e)}) if args.json else f"error: {_e}", file=sys.stderr)
                return 1
            if args.json:
                print(json.dumps(_result, indent=2))
            else:
                print(f"promoted: {_result['bundle_id'][:18]} → input {_result['queued_input_id']}")
            return 0
    if args.command == 'similarity':
        from .. import product_similarity as _ps
        from .. import peer_exchange as _pe
        try:
            _sim_config = load_config()
            _sim_state = load_state(_sim_config)
        except Exception as _e:
            print(json.dumps({'status': 'error', 'error': str(_e)}) if args.json else f"error: {_e}", file=sys.stderr)
            return 1
        try:
            _sim_dir = _pe.directory(_sim_config)
            _sim_exchange = _pe.Exchange(_sim_dir)
        except Exception as _e:
            print(json.dumps({'status': 'error', 'error': str(_e)}) if args.json else f"error: {_e}", file=sys.stderr)
            return 1
        _sim_results = _ps.score_features(
            _sim_config, _sim_state, _sim_exchange,
            max_peer_age_seconds=args.max_peer_age_seconds,
            timeout_seconds=args.timeout_seconds,
        )
        _min_score = getattr(args, 'min_score', 0.0)
        _sim_results = [r for r in _sim_results if r['score'] >= _min_score]
        if args.json:
            print(json.dumps({'schema': _ps.SCHEMA, 'results': _sim_results}, indent=2))
        else:
            if not _sim_results:
                print('  no peer feature recommendations (no recent adoption data)')
            else:
                print(f"  {'feature':<30} {'score':>7}  {'conf':<8}  {'peers':>5}  {'adopt':>6}  {'sim':>6}")
                print(f"  {'-'*30} {'-'*7}  {'-'*8}  {'-'*5}  {'-'*6}  {'-'*6}")
                for _r in _sim_results[:20]:
                    print(f"  {_r['feature_id']:<30} {_r['score']:>7.4f}  {_r['confidence']:<8}  {_r['peer_count']:>5}  {_r['adoption_rate']:>6.2f}  {_r['intent_similarity']:>6.2f}")
        return 0
    if args.command == 'p2p':
        import os as _os
        from pathlib import Path as _p2p_Path
        _p2p_action = getattr(args, 'action', None)
        if _p2p_action == 'keygen':
            from ..evolution_guard import p2p_keygen as _p2p_keygen
            _out = _p2p_Path(args.out) if args.out else None
            _kg = _p2p_keygen(_out)
            if getattr(args, 'json', False):
                print(json.dumps(_kg, indent=2))
            else:
                print(f"  public key:  {_kg['pub_key_hex']}")
                print(f"  private key: {_kg['priv_key_path']}  (chmod 600)")
                print()
                print(_kg['instructions'])
            return 0
        if _p2p_action == 'build-update':
            from ..evolution_guard import build_p2p_update_bundle as _p2p_build_fn, RELEASE_AUTHORITY_KEYS as _ra_keys
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as _Ed
            from cryptography.hazmat.primitives.serialization import Encoding as _Enc, PublicFormat as _PF
            _sign_fns = []
            for _kp in (args.keys or []):
                _kpath = _p2p_Path(_kp)
                if not _kpath.exists():
                    print(f"error: key file not found: {_kpath}", file=sys.stderr); return 1
                try:
                    _priv_raw = bytes.fromhex(_kpath.read_text().strip())
                except ValueError:
                    print(f"error: {_kpath} must contain 64 hex chars", file=sys.stderr); return 1
                _priv_key = _Ed.from_private_bytes(_priv_raw)
                _pub_hex  = _priv_key.public_key().public_bytes(_Enc.Raw, _PF.Raw).hex()
                _sign_fns.append((_pub_hex, lambda d, _p=_priv_raw: _Ed.from_private_bytes(_p).sign(d).hex()))
            _sign_arg = _sign_fns if len(_sign_fns) > 1 else (_sign_fns[0][1] if _sign_fns else (lambda d: ""))
            _bundle = _p2p_build_fn(SYSTEM_ROOT, _sign_arg,
                                    log_rekor=getattr(args, 'log_rekor', False),
                                    anchor_ots=getattr(args, 'anchor_ots', False))
            _out_path = _p2p_Path(args.out) if args.out else _p2p_Path("urace-update-bundle.json")
            _out_path.write_text(json.dumps(_bundle, indent=2), encoding="utf-8")
            if getattr(args, 'json', False):
                print(json.dumps({"status": "OK", "path": str(_out_path), "schema": _bundle["schema"],
                                  "corpus_fingerprint": _bundle["corpus_fingerprint"],
                                  "transparency_log": _bundle.get("transparency_log"),
                                  "opentimestamps": bool(_bundle.get("opentimestamps_proof"))}, indent=2))
            else:
                print(f"  bundle written: {_out_path}")
                print(f"  schema:         {_bundle['schema']}")
                print(f"  fingerprint:    {_bundle['corpus_fingerprint']}")
                if _bundle.get("transparency_log"):
                    _tl = _bundle["transparency_log"]
                    if "error" in _tl:
                        print(f"  rekor:          ERROR — {_tl['error']}")
                    else:
                        print(f"  rekor log idx:  {_tl.get('log_index')}  (uuid: {_tl.get('uuid','')[:16]}...)")
                if _bundle.get("opentimestamps_proof"):
                    print("  opentimestamps: anchored to Bitcoin calendar")
            return 0
        if _p2p_action == 'publish-update':
            from ..peer_discovery import p2p_update_publish as _p2p_pub_fn
            _key_path = _p2p_Path(args.key)
            if not _key_path.exists():
                print(f"error: key file not found: {_key_path}", file=sys.stderr); return 1
            _bundle_path = _p2p_Path(args.bundle)
            if not _bundle_path.exists():
                print(f"error: bundle file not found: {_bundle_path}", file=sys.stderr); return 1
            _priv_raw = bytes.fromhex(_key_path.read_text().strip())
            _bundle   = json.loads(_bundle_path.read_text())
            _result   = _p2p_pub_fn(_bundle, _priv_raw, bundle_url=getattr(args, 'url', ''))
            if getattr(args, 'json', False):
                print(json.dumps(_result, indent=2))
            else:
                if _result.get("status") == "PUBLISHED":
                    print("  status:      PUBLISHED")
                    print(f"  dht_key:     {_result['dht_key']}")
                    print(f"  fingerprint: {_result['corpus_fingerprint']}")
                    print(f"  bundle_url:  {_result.get('bundle_url') or '(none)'}")
                    print(f"  announced:   {_result['announced_to']} nodes")
                else:
                    print(f"error: {_result.get('error')}", file=sys.stderr)
                    return 1
            return 0
        if _p2p_action == 'check-update':
            from ..evolution_guard import RELEASE_AUTHORITY_PUB_KEY_HEX as _ra_key
            if not _ra_key:
                print("error: RELEASE_AUTHORITY_PUB_KEY_HEX not configured in evolution_guard.py",
                      file=sys.stderr); return 1
            try:
                _p2p_cfg  = load_config()
                _p2p_state = load_state(_p2p_cfg)
                from .. import peer_exchange as _pex
                _p2p_exch = _pex.Exchange(SYSTEM_ROOT / "urace" / "p2p")
                _p2p_exch.configure(enabled=True, network=True)
            except Exception as _e:
                print(f"error: {_e}", file=sys.stderr); return 1
            from ..peer_discovery import p2p_update_check as _p2p_chk
            _chk = _p2p_chk(_p2p_exch, _ra_key)
            if getattr(args, 'json', False):
                print(json.dumps(_chk, indent=2))
            else:
                if _chk.get("available"):
                    print("  UPDATE AVAILABLE")
                    print(f"  remote fingerprint: {_chk['corpus_fingerprint']}")
                    print(f"  local  fingerprint: {_chk['local_fingerprint']}")
                    print(f"  bundle_url:         {_chk.get('bundle_url') or '(none)'}")
                    print("  Apply with: urace p2p apply-update --bundle <downloaded-bundle.json>")
                else:
                    print(f"  no update available  (local fingerprint: {_chk.get('local_fingerprint','')})")
            return 0
        if _p2p_action == 'apply-update':
            _bundle_path = _p2p_Path(args.bundle)
            if not _bundle_path.exists():
                print(f"error: bundle file not found: {_bundle_path}", file=sys.stderr); return 1
            _bundle = json.loads(_bundle_path.read_text())
            from ..evolution_guard import apply_p2p_update_bundle as _p2p_apply_fn, verify_release_signature as _vrs2
            _run_tests = not getattr(args, 'no_tests', False)
            _errors = _p2p_apply_fn(_bundle, SYSTEM_ROOT, _vrs2, run_tests=_run_tests)
            if _errors:
                if getattr(args, 'json', False):
                    print(json.dumps({"status": "REJECTED", "errors": _errors}, indent=2))
                else:
                    print("  REJECTED:")
                    for _e in _errors: print(f"  - {_e}")
                return 1
            if getattr(args, 'json', False):
                print(json.dumps({"status": "APPLIED",
                                  "corpus_fingerprint": _bundle.get("corpus_fingerprint")}, indent=2))
            else:
                print(f"  APPLIED  fingerprint: {_bundle.get('corpus_fingerprint')}")
            return 0
    if args.command=='product' and args.action=='create':
        if _unknown:parser.error('Unknown product creation arguments: '+' '.join(_unknown))
        from ..product_creation import create
        try:print(json.dumps(create(sys.modules[__name__],args.description,args.creation_name),indent=2));return 0
        except (ValueError,OSError) as error:parser.error(str(error))
    if args.command=='product' and args.action=='exchange':
        if _unknown:parser.error('Unrecognized exchange arguments: '+' '.join(_unknown))
        from ..exchange_cli import run as run_exchange
        try:return run_exchange(args,load_config())
        except (ValueError,OSError) as error:parser.error(str(error))
    if args.command=='exchange':
        if _unknown:parser.error('Unrecognized exchange arguments: '+' '.join(_unknown))
        from ..exchange_cli import run as run_exchange
        try:return run_exchange(args,load_config())
        except (ValueError,OSError) as error:parser.error(str(error))
    if args.command in {'executor-skills-config','context-guard-config'}:
        from .. import executor_capabilities as ec
        if _unknown:parser.error('Unknown capability configuration arguments: '+' '.join(_unknown))
        key='executor_skills' if args.command=='executor-skills-config' else 'context_guard';changes={k:getattr(args,k) for k in ('enabled','mode','max_selected','max_instruction_bytes') if getattr(args,k,None) is not None}
        try:
            if getattr(args,'catalog_file',None):
                from ..exchange_cli import bounded_file
                changes['catalog']=json.loads(bounded_file(args.catalog_file,262144))
            with state_lock(CONFIG_PATH) if changes else nullcontext():
                config=load_config();value={**(ec.settings(config) if key=='executor_skills' else ec.context_settings(config)),**changes};ec.contract({**config,key:value})
                if changes:config[key]=value;save_config(config)
            print(json.dumps(value,indent=2,sort_keys=True));return 0
        except (ValueError,OSError,TypeError) as error:parser.error(str(error))
    if args.command=='runtime-improvement-config':
        sys.path.insert(0,str(SYSTEM_ROOT/'trial'))
        from runtime_cycle import settings as runtime_settings
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized runtime improvement arguments: '+' '.join(_unknown))
        try:
            changes={k:getattr(args,k) for k in ('enabled','auto_deploy','interval_seconds') if getattr(args,k,None) is not None}
            with state_lock(CONFIG_PATH) if changes else nullcontext():
                config=load_config();merged={**config.get('runtime_workflow',{}),**changes};updated=runtime_settings({'runtime_workflow':merged})
                if changes:config['runtime_workflow']=merged;save_config(config)
            print(json.dumps(updated,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,TypeError) as error:parser.error(str(error))
    if args.command=='crypto':
        from .. import crypto_wallet as _cw
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized crypto arguments: '+' '.join(_unknown))
        try:
            verb=getattr(args,'wallet_verb',None)
            if verb=='init':
                result=_cw.wallet_init(wallet_dir=args.wallet_dir,overwrite=args.overwrite)
            elif verb=='show':
                result=_cw.wallet_show(wallet_dir=args.wallet_dir)
            elif verb=='sign':
                result=_cw.wallet_sign(payload=args.payload,wallet_dir=args.wallet_dir)
            elif verb=='rotate':
                _backup=getattr(args,'backup_dir',None)
                _bdir=Path(_backup) if _backup else None
                result=_cw.wallet_rotate(wallet_dir=args.wallet_dir,backup_dir=_bdir)
            else:
                parser.error('Unknown crypto wallet verb: '+str(verb))
            print(json.dumps(result,indent=2,sort_keys=True));return 0
        except FileExistsError as e:
            print(json.dumps({'status':'error','error':str(e)},indent=2));return 1
        except FileNotFoundError as e:
            print(json.dumps({'status':'error','error':str(e)},indent=2));return 1
        except (OSError,ValueError) as error:parser.error(str(error))
    if args.command=='qualification':
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized qualification arguments: '+' '.join(_unknown))
        try:
            action=getattr(args,'qualification_action',None)
            try:
                config=load_config();state=load_state(config)
            except RuntimeError as _e:
                if action=='list':
                    print(json.dumps({'status':'ok','evidence':[]},indent=2));return 0
                print(json.dumps({'status':'error','error':str(_e)},indent=2));return 1
            if action=='list':
                kind_filter=getattr(args,'evidence_kind',None)
                limit=getattr(args,'limit',20)
                evidence=state.get('evidence',[])
                if kind_filter:evidence=[e for e in evidence if e.get('kind')==kind_filter]
                result={'status':'ok','evidence':[{'id':e['id'],'kind':e.get('kind','unknown'),'at':e.get('at',''),'has_proposal':bool(e.get('proposal'))} for e in evidence[-limit:]]}
            elif action=='replay':
                eid=args.evidence_id
                evidence=state.get('evidence',[])
                record=next((e for e in evidence if e.get('id')==eid),None)
                if not record:
                    print(json.dumps({'status':'error','error':f'Evidence not found: {eid}'},indent=2));return 1
                # Find associated decisions
                decisions=state.get('decisions',[])
                linked_decisions=[d for d in decisions if d.get('evidence_id')==eid or eid in d.get('provenance_ids',[])]
                # Hash-verify proposal integrity
                import hashlib as _hl
                proposal=record.get('proposal',{})
                proposal_str=json.dumps(proposal,sort_keys=True)
                replay_hash=_hl.sha256(proposal_str.encode()).hexdigest()
                stored_hash=record.get('content_hash')
                # Re-assess score from stored evidence fields
                stored_score=None
                replayed_score=None
                for d in linked_decisions:
                    if d.get('score_delta') is not None:
                        stored_score=d['score_delta']
                        break
                # Re-compute score
                replay_mode=getattr(args,'replay_mode','estimate')
                criteria_drift=None
                evaluation_weights_current=None
                evaluation_weights_at_qualification=None
                if proposal:
                    import math as _math
                    desc_len=len(str(proposal.get('description',''))+str(proposal.get('changes','')))
                    replayed_score=round(min(1.0,_math.log2(1+desc_len/200)),4)
                if replay_mode=='full':
                    # Full mode: use evaluation_system weights to detect criteria drift
                    ev_sys=config.get('evaluation_system',{})
                    evaluation_weights_current=ev_sys.get('weights',{})
                    # Find stored weights from the linked decision (if it recorded them)
                    stored_weights=next((d.get('evaluation_weights') for d in linked_decisions if d.get('evaluation_weights')),None)
                    evaluation_weights_at_qualification=stored_weights
                    if stored_weights is not None:
                        criteria_drift=evaluation_weights_current!=stored_weights
                        if not criteria_drift and stored_score is not None:
                            replayed_score=stored_score  # deterministically reproducible
                        else:
                            criteria_drift=True
                    else:
                        criteria_drift=None  # unknown — weights not stored in original decision
                    # Weighted re-score from proposal assessment fields
                    if evaluation_weights_current:
                        assessment=str(proposal.get('evaluation_assessment',''))
                        weights=list(evaluation_weights_current.values())
                        total_weight=sum(weights)
                        if total_weight>0 and assessment:
                            # Heuristic: each component contributes proportionally if mentioned in assessment
                            component_scores=[]
                            for component,w in evaluation_weights_current.items():
                                mentioned=component.lower() in assessment.lower()
                                component_scores.append(w*(1.0 if mentioned else 0.5))
                            replayed_score=round(sum(component_scores)/total_weight,4)
                integrity='verified' if (stored_hash and stored_hash==replay_hash) else ('no_stored_hash' if not stored_hash else 'mismatch')
                result={
                    'status':'ok',
                    'evidence_id':eid,
                    'kind':record.get('kind','unknown'),
                    'at':record.get('at',''),
                    'replay_mode':replay_mode,
                    'integrity':integrity,
                    'replay_hash':replay_hash,
                    'linked_decisions':len(linked_decisions),
                    'stored_score_delta':stored_score,
                    'replayed_score_estimate':replayed_score,
                    'score_match': stored_score is not None and replayed_score is not None and abs(stored_score-replayed_score)<0.5,
                    'decision_outcomes':[d.get('outcome') for d in linked_decisions],
                    'proposal_summary':{
                        'has_description':bool(proposal.get('description')),
                        'has_changes':bool(proposal.get('changes')),
                        'field_count':len(proposal),
                    },
                }
                if replay_mode=='full':
                    result['evaluation_weights_current']=evaluation_weights_current
                    result['evaluation_weights_at_qualification']=evaluation_weights_at_qualification
                    result['criteria_drift']=criteria_drift
            else:
                parser.error('Unknown qualification action: '+str(action))
            print(json.dumps(result,indent=2,sort_keys=True));return 0
        except FileNotFoundError:
            print(json.dumps({'status':'error','error':'State not found — run urace init first'},indent=2));return 1
        except (OSError,ValueError,KeyError) as error:parser.error(str(error))
    if args.command == 'config':
        if args.config_verb == 'show-all':
            import json as _jm
            _base = _jm.loads(CONFIG_PATH.read_text())
            caps = _base.get('capability_flags', {})
            executor_cfg = _base.get('executor', {})
            exchange_cfg = _base.get('exchange', {})
            fleet_cfg = _base.get('fleet', {})
            resources_cfg = _base.get('resources', {})
            result = {
                'status': 'ok',
                'capability_flags': caps,
                'executor': {k: v for k, v in executor_cfg.items() if k != 'providers'},
                'exchange': {k: v for k, v in exchange_cfg.items() if k not in ('peers', 'certs')},
                'fleet': fleet_cfg,
                'resources': resources_cfg,
            }
            print(json.dumps(result, indent=2))
            return 0
    if args.command == 'security':
        if args.security_verb == 'audit':
            config = load_config()
            checks = []
            def _sec_check(name, status, detail=""):
                checks.append({"check": name, "status": status, "detail": detail})
            # 1. Wallet
            _wallet_dir = Path.home() / ".urace" / "wallet"
            _key_path = _wallet_dir / "key.json"
            if _key_path.exists():
                try:
                    _wdata = json.loads(_key_path.read_text())
                    _sec_check("wallet_present", "OK", f"address={_wdata.get('address','?')[:12]}...")
                except Exception as _e:
                    _sec_check("wallet_present", "WARN", str(_e))
            else:
                _sec_check("wallet_present", "WARN", "no wallet — run: urace crypto wallet init")
            # 2. Consensus threshold
            _exch_cfg = config.get("exchange", {})
            _min_thresh = _exch_cfg.get("p2p", {}).get("consensus_trigger_min_peers", 2)
            if _min_thresh >= 3:
                _sec_check("consensus_threshold", "OK", f"min_threshold={_min_thresh}")
            else:
                _sec_check("consensus_threshold", "WARN", f"min_threshold={_min_thresh} (<3) — raise with: urace exchange settings set --consensus-min-threshold 3")
            # 3. Compliance mode
            _caps = config.get("capability_flags", {})
            _comp_mode = _caps.get("compliance_mode", False)
            _sec_check("compliance_mode", "OK" if _comp_mode else "INFO", "enabled" if _comp_mode else "disabled — enable with: urace controls set --compliance-mode true")
            # 4. Circuit breaker
            try:
                from .. import circuit_breaker as _cb
                _exec_settings = config.get("executor", {})
                _pool_state = load_state_for_read(config) or {}
                _pool = _pool_state.get("executor_state", {}).get("provider_pool", {})
                _cb_status = _cb.status(_exec_settings, _pool)
                _tripped = _cb_status.get("tripped_count", 0)
                if _tripped == 0:
                    _sec_check("circuit_breaker", "OK", f"all {_cb_status.get('healthy_count',0)} providers healthy")
                else:
                    _sec_check("circuit_breaker", "WARN", f"{_tripped} provider(s) tripped — run: urace executor circuit-breaker --json")
            except Exception as _e:
                _sec_check("circuit_breaker", "INFO", str(_e))
            # 5. Exchange certificate
            from .. import peer_exchange as _pe_sec
            _exch_root_path = _exch_cfg.get("root") or str(ROOT / "exchange")
            _cert_path = Path(_exch_root_path) / "identity-cert.pem"
            if _cert_path.exists():
                _sec_check("peer_certificate", "OK", f"certificate present at {_cert_path}")
            else:
                _sec_check("peer_certificate", "INFO", "no certificate — run: urace exchange peer identity")
            # 6. Runtime integrity vs GitHub release
            if not getattr(args, "no_network", False):
                try:
                    import urllib.request as _ghr_ur
                    _gh_repo = config.get("github", {}).get("repo", "joaoalbertocsjunior/URACE")
                    _ver_file = ROOT / "VERSION"
                    _local_ver = _ver_file.read_text().strip() if _ver_file.exists() else None
                    if _local_ver:
                        _req_rel = _ghr_ur.Request(
                            f"https://api.github.com/repos/{_gh_repo}/releases/tags/v{_local_ver}",
                            headers={"Accept": "application/vnd.github+json", "User-Agent": "urace-security-audit/1"})
                        with _ghr_ur.urlopen(_req_rel, timeout=8) as _rr:  # noqa: S310
                            _rel_data = json.loads(_rr.read().decode())
                        _assets = _rel_data.get("assets", [])
                        _whl_asset = next((a for a in _assets if a.get("name", "").endswith(".whl")), None)
                        if _whl_asset:
                            _sec_check("github_release_asset", "OK", f"release v{_local_ver} has wheel asset: {_whl_asset['name']}")
                        else:
                            _sec_check("github_release_asset", "INFO", f"release v{_local_ver} found (no wheel asset listed)")
                    else:
                        _sec_check("github_release_asset", "INFO", "VERSION file absent — cannot verify against GitHub release")
                except Exception as _ge:
                    _sec_check("github_release_asset", "INFO", f"GitHub release check skipped: {type(_ge).__name__}")
            _overall = "PASS" if all(c["status"] in ("OK", "INFO") for c in checks) else "WARN"
            result = {"status": _overall, "checks": checks, "pass_count": sum(1 for c in checks if c["status"] == "OK"), "warn_count": sum(1 for c in checks if c["status"] == "WARN")}
            if getattr(args, 'format', None) == 'json':
                print(json.dumps(result, indent=2))
            else:
                print(f"Security Audit: {_overall}")
                for c in checks:
                    icon = "v" if c["status"] == "OK" else ("!" if c["status"] == "WARN" else ".")
                    print(f"  [{icon}] {c['check']:30s} {c['status']:6s}  {c['detail']}")
            return 0
    if args.command == "content":
        from .. import content_store as _cs
        verb = getattr(args, "action", None)
        if verb == "ref":
            result = _cs.content_ref(ROOT, args.path)
        elif verb == "list":
            result = {"refs": _cs.content_list(ROOT)}
        elif verb == "show":
            result = _cs.content_show(ROOT, args.ref_id) or {"error": f"ref not found: {args.ref_id}"}
        else:
            result = {"error": f"unknown content verb: {verb}"}
        print(json.dumps(result, indent=2))
        return 0
    if args.command=='github-workflow-config':
        from .. import portfolio_github as _pgh
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized github-workflow arguments: '+' '.join(_unknown))
        try:
            _keys=('auto_pull','auto_commit','auto_push','commit_message_template','branch_strategy')
            changes={k:getattr(args,k) for k in _keys if getattr(args,k,None) is not None}
            with state_lock(CONFIG_PATH) if changes else nullcontext():
                config=load_config()
                if changes:config['github_workflow']={**_pgh.workflow_settings(config),**changes};save_config(config)
                updated=_pgh.workflow_settings(config)
            print(json.dumps(updated,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,TypeError) as error:parser.error(str(error))
    if args.command=='auto-milestones-config':
        from .. import milestone_suggestions as ms
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized auto-milestones arguments: '+' '.join(_unknown))
        try:
            with state_lock(CONFIG_PATH) if args.enabled is not None else nullcontext():
                config=load_config();updated=ms.settings(config)
                if args.enabled is not None:
                    updated['enabled']=args.enabled;config['auto_milestones']=updated;save_config(config)
            print(json.dumps(updated,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,TypeError) as error:parser.error(str(error))
    if args.command=='decision-feedback-config':
        from .. import decision_feedback as df
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized decision feedback arguments: '+' '.join(_unknown))
        try:
            config=load_config();changes={k:getattr(args,k) for k in df.DEFAULTS if getattr(args,k,None) is not None}
            with state_lock(CONFIG_PATH) if changes else nullcontext():
                config=load_config();updated=df.settings({**config,'decision_feedback':{**df.settings(config),**changes}})
                if changes:config['decision_feedback']=updated;save_config(config)
            print(json.dumps(updated,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,TypeError) as error:parser.error(str(error))
    if args.command in {'value-discovery-config','value-status'} or (args.command=='product' and args.action=='value'):
        from .. import value_discovery as vd
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized value command arguments: '+' '.join(_unknown))
        try:
            config=load_config()
            if args.command=='value-discovery-config':
                changes={name:getattr(args,name) for name in vd.DEFAULTS if getattr(args,name,None) is not None}
                with state_lock(CONFIG_PATH) if changes else nullcontext():
                    config=load_config();updated={**vd.settings(config),**changes};vd.settings({**config,'value_discovery':updated})
                    if changes:config['value_discovery']=updated;save_config(config)
                payload=updated
            elif args.command=='value-status':payload=vd.status(config)
            else:payload=vd.dispatch(args,config,ROOT)
            print(json.dumps(payload,indent=2,sort_keys=True));return 0
        except (OSError,ValueError,KeyError,TypeError) as error:parser.error(str(error))
    if args.command == "product" and args.action == "work":
        if args.name=='clarify':
            if _unknown:parser.error('Unknown clarification arguments: '+' '.join(_unknown))
            sys.path.insert(0,str(SYSTEM_ROOT/'trial'));from project_work import clarify
            try:print(json.dumps(clarify(args.project,args.requirement_id,args.answer,SYSTEM_ROOT/'trial'),indent=2));return 0
            except (ValueError,OSError) as error:parser.error(str(error))
        if args.name not in ('init','run','status') or not args.project:parser.error('Use product work init|run|status --project PATH')
        from ..trial import main as trial_main
        route=['work',args.name,'--project',args.project,'--template',args.template,'--executor',args.work_executor,'--execution-mode',args.execution_mode,'--max-seconds',str(args.max_seconds),'--adaptive',args.adaptive,'--json']
        if args.run_id:route+=['--run-id',args.run_id]
        return trial_main(route)
    if args.command=='product' and args.action!='improvements' and args.improvement_product_id is not None:parser.error('Unexpected product argument; use product improvements enable|disable PRODUCT_ID')
    if args.command=='product' and args.all_products and args.action!='improvements':parser.error('--all-products requires product improvements list')
    if args.command=='product' and args.action in ('improvements','enable','disable'):
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized product improvement arguments: '+' '.join(_unknown))
        sys.path.insert(0,str(SYSTEM_ROOT/'trial'))
        from product_controls import set_improvement_enabled,get_improvement_enabled
        base=SYSTEM_ROOT/'trial';verb=(args.name or 'list') if args.action=='improvements' else args.action
        product_id=args.improvement_product_id if args.action=='improvements' else args.name
        products=json.loads((base/'products.json').read_text()).get('products',[]) if (base/'products.json').exists() else []
        main_id=json.loads((base/'contract.json').read_text()).get('product_id') if (base/'contract.json').exists() else None
        config=load_config()
        owner_products=[p for p in config.get('product_registry',[]) if p.get('kind')=='bootstrapped']
        products=[*products,*owner_products]
        supported=lambda row:row.get('kind') in ('runtime','bootstrapped') or row.get('id')==main_id
        if verb not in ('list','enable','disable'):parser.error('Use product improvements list|enable|disable')
        if verb=='list':
            if product_id:parser.error('product improvements list takes no product ID')
            rows=[{**{k:p.get(k) for k in ('id','name','kind')},'improvement_enabled':p.get('improvement_enabled',True) if p.get('kind')=='bootstrapped' else get_improvement_enabled(p['id'],base),'improvement_supported':supported(p)} for p in products if args.all_products or supported(p)]
            result={'schema':'product-improvement-controls-v1','products':rows,'includes_study_artifacts':args.all_products}
            if args.json:print(json.dumps(result,indent=2,sort_keys=True))
            else:
                for row in rows:print(str(row['id'])+'  improvement '+('enabled' if row['improvement_enabled'] else 'disabled')+('' if row['improvement_supported'] else ' (accounting artifact; use owning study controls)'))
            return 0
        if args.all_products:parser.error('--all-products is inspection only')
        if not product_id:parser.error('An explicit improvement product ID is required')
        owner_product=next((p for p in owner_products if p.get('id')==product_id),None)
        if owner_product:
            with state_lock(CONFIG_PATH):
                fresh=load_config();entry=next(p for p in fresh['product_registry'] if p.get('id')==product_id);entry['improvement_enabled']=verb=='enable';save_config(fresh)
            print(json.dumps({'id':product_id,'improvement_enabled':verb=='enable','source':'owner product registry'}));return 0
        row=next((p for p in products if p.get('id')==product_id),None)
        if row is None or not supported(row):parser.error('No improvement worker for this ID; accounting artifacts use their owning study controls')
        result=set_improvement_enabled(product_id,verb=='enable',base)
        if args.json:print(json.dumps(result,sort_keys=True))
        else:print('improvement '+('enabled' if verb=='enable' else 'disabled')+' for product: '+product_id)
        return 0
    if args.command == "trial":
        from ..trial import main as trial_main
        trial_args = raw_args[raw_args.index("trial") + 1:]
        if _fmt and trial_args[:2] in (["status", "resources"], ["status", "scores"]) and "--json" not in trial_args:
            trial_args.append("--json")
        return trial_main(trial_args)
    if getattr(args,'status_subject',None)=='scores':
        if _unknown:parser.error('unrecognized score arguments: '+' '.join(_unknown))
        from ..trial import main as trial_main
        route=['status','scores','--compare',args.compare,'--executor',args.executor,'--limit',str(args.limit)]
        if args.version is not None:route.extend(['--version',str(args.version)])
        if args.history:route.append('--history')
        if args.json:route.append('--json')
        return trial_main(route)
    _non_flag_unknown = [u for u in _unknown if not u.startswith("-")]
    if _non_flag_unknown and getattr(args, "command", None) not in {None, "classify"}:
        # A1: command word + unrecognized positional args → quoting hint before re-routing
        _cmd = getattr(args, "command", raw_args[0] if raw_args else "")
        if _cmd in _KNOWN_TOP_COMMANDS or _cmd in {"auto-goals","effort","executor-options"}:
            _joined = " ".join(_original_raw)
            print(
                f"error: unrecognized arguments for `{_cmd}`: {' '.join(_non_flag_unknown)}\n"
                f"Tip: to classify freeform text, quote it — e.g.: urace \"{_joined}\"",
                file=sys.stderr,
            )
            return 1
        # Unknown non-flag args after a known command → re-route entire input as free-form
        raw_args = ["classify", " ".join(_original_raw)]
        args = parser.parse_args(raw_args)
    elif _unknown:
        # Unknown flags → let argparse report the error properly
        parser.parse_args(raw_args)
    def _sigterm_handler(signum, frame):  # noqa: ARG001
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _sigterm_handler)
    if args.command == "watch":
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized watch arguments: '+' '.join(_unknown))
        selected=[name for name in ('report','guard','dashboard') if getattr(args,name,False)]
        if selected and args.watch_action!='events' and selected[0]!=args.watch_action:parser.error('Conflicting watch views')
        view=selected[0] if selected else args.watch_action
        if args.follow and view!='events':parser.error('--follow requires watch events')
        args.report=view=='report';args.guard=view=='guard';args.dashboard=view=='dashboard'

        _trial_base = SYSTEM_ROOT / 'trial'
        sys.path.insert(0, str(_trial_base))
        try:
            import runtime_snapshot as _rs
            import runtime_trial as _rt
        except ImportError as _e:
            print(f'error: runtime improvement modules not found: {_e}', file=sys.stderr)
            return 1
        if getattr(args, 'report', False):
            report = _rt.redeployment_report(str(_trial_base))
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        if getattr(args, 'guard', False):
            try:
                import runtime_regression_guard as _rg
                guard_result = _rg.check(str(_trial_base),load_config())
                print(json.dumps(guard_result, indent=2, sort_keys=True))
            except ImportError as _ge:
                print(json.dumps({'error': f'runtime_regression_guard not available: {_ge}'}))
            return 0
        if getattr(args, 'dashboard', False):
            import runtime_dashboard as _dashboard
            config=load_config()
            if args.json:print(json.dumps(_dashboard.data(_trial_base,config),sort_keys=True))
            else:print(_dashboard.render(_trial_base,config))
            return 0
        def _watch_render(entry, as_json):
            if as_json:
                return json.dumps({k: v for k, v in entry.items() if not k.startswith('change_log')}, sort_keys=True)
            ts = (entry.get('at') or entry.get('recorded_at', ''))[:19]
            kind = entry.get('_kind', 'snapshot')
            sid = entry.get('snapshot_id', '')[:16]
            delta = entry.get('quality_delta') or entry.get('quality', {}).get('delta') or entry.get('delta')
            delta_str = f'+{delta:.1f}' if delta is not None else 'n/a'
            if kind=='cycle':return f"[{ts}] {entry.get('stage','UNKNOWN')} {entry.get('reason','')}"
            if kind == 'deployment':
                files = ', '.join(entry.get('files_changed', [])[:2])
                return f"[{ts}] {entry.get('event','DEPLOYMENT_EVENT')} {sid}  delta={delta_str}  files={files}"
            return f'[{ts}] snapshot {sid}  delta={delta_str}  {entry.get("rationale","")[:60]}'
        def _load_feed(limit):
            if limit==0:return []
            feed = []
            for s in _rs.stream_summaries(str(_trial_base), limit=limit):
                entry = dict(s); entry['_kind'] = 'snapshot'; entry['at'] = s.get('recorded_at', '')
                feed.append(entry)
            for e in _rt.deployment_log(str(_trial_base)):
                entry = dict(e); entry['_kind'] = 'deployment'
                feed.append(entry)
            _cycle_log=_trial_base/'runtime-cycle-events.jsonl'
            if _cycle_log.exists():
                for line in _cycle_log.read_text().splitlines()[-limit:]:
                    entry=json.loads(line);entry['_kind']='cycle';entry['at']=entry.get('updated_at','');feed.append(entry)
            feed.sort(key=lambda x: x.get('at', x.get('recorded_at', '')))
            return feed[-limit:]
        # Print guard status header in non-JSON mode
        _guard_header = ''
        if not args.json:
            try:
                import runtime_regression_guard as _rg
                _gr = _rg.check(str(_trial_base),load_config())
                _gs = _gr['status']
                _gc = _gr.get('current_score')
                _ga = _gr.get('accepted_score')
                _gd = _gr.get('delta')
                if _gs == 'OK':
                    _guard_header = f'Guard: OK (current={_gc}, accepted={_ga})'
                elif _gs == 'REGRESSION':
                    _guard_header = f'Guard: REGRESSION delta={_gd:.2f}'
                else:
                    _guard_header = f'Guard: {_gs}'
            except Exception:
                pass
        if _guard_header:
            print(_guard_header, flush=True)
        feed = _load_feed(args.limit)
        for entry in feed:
            print(_watch_render(entry, args.json), flush=True)
        if args.follow:
            seen = {(e.get('_kind'),e.get('snapshot_id'),e.get('at')) for e in _load_feed(max(200,args.limit))}
            while True:
                time.sleep(3)
                new_feed = _load_feed(200)
                for entry in new_feed:
                    key = (entry.get('_kind'),entry.get('snapshot_id'),entry.get('at'))
                    if key not in seen:
                        print(_watch_render(entry, args.json), flush=True)
                        seen.add(key)
        return 0
    if args.command == "usage":
        command_surface.validate(args, raw_args, parser)
        if _unknown: parser.error('Unrecognized usage arguments: ' + ' '.join(_unknown))
        config = load_config(); state = load_state(config)
        action = getattr(args, 'usage_action', None)
        if action == 'patterns':
            limit = getattr(args, 'limit', 20)
            # Top commands by frequency
            executor_calls = state.get('executor_state', {}).get('executor_calls', [])
            kind_counts: dict[str, int] = {}
            freeform_tokens = 0; executor_tokens = 0
            for call in executor_calls:
                k = call.get('kind', call.get('scope', 'unknown'))
                kind_counts[k] = kind_counts.get(k, 0) + 1
                usage_data = call.get('usage', {})
                if isinstance(usage_data, dict):
                    toks = usage_data.get('total_tokens', 0) or 0
                    if call.get('kind') == 'freeform':
                        freeform_tokens += int(toks)
                    else:
                        executor_tokens += int(toks)
            top_commands = sorted(kind_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            # Goal outcomes
            operations = state.get('operations', [])
            goal_success: dict[str, int] = {}; goal_total: dict[str, int] = {}
            for op in operations:
                ref = op.get('objective_reference', op.get('decision', 'unknown'))
                goal_total[ref] = goal_total.get(ref, 0) + 1
                if op.get('outcome', {}).get('status') in ('VERIFIED', 'ACCEPTED', 'verified', 'accepted'):
                    goal_success[ref] = goal_success.get(ref, 0) + 1
            goal_outcomes = [{'goal': g, 'success_rate': round(goal_success.get(g, 0) / t, 3), 'total': t}
                             for g, t in sorted(goal_total.items(), key=lambda x: x[1], reverse=True)[:limit]]
            freeform_calls = [c for c in executor_calls if c.get("kind") == "freeform-routing"]
            # Cache hits are calls with 0 tokens (served from cache)
            freeform_cache_hits = sum(1 for c in freeform_calls if int(c.get("tokens", 0) or 0) == 0)
            freeform_total = len(freeform_calls)
            payload = {
                'status': 'ok',
                'top_commands': [{'kind': k, 'count': c} for k, c in top_commands],
                'token_breakdown': {'freeform_tokens': freeform_tokens, 'executor_tokens': executor_tokens},
                'goal_outcomes': goal_outcomes,
                'freeform_stats': {
                    'total_calls': freeform_total,
                    'cache_hits': freeform_cache_hits,
                    'cache_hit_rate': round(freeform_cache_hits / freeform_total, 3) if freeform_total > 0 else None,
                },
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        parser.error(f'Unknown usage action: {action}')
    if args.command == "cost":
        command_surface.validate(args, raw_args, parser)
        if _unknown: parser.error('Unrecognized cost arguments: ' + ' '.join(_unknown))
        config = load_config()
        from urace.cost_model import load_receipts as _load_receipts, summarize_receipts as _summarize
        action = getattr(args, 'cost_action', None)
        since = getattr(args, 'since', None)
        limit = getattr(args, 'limit', None)
        receipts = _load_receipts(config, since=since, limit=limit)
        fmt = getattr(args, 'format', None)
        if action == 'summary':
            summary = _summarize(receipts)
            if fmt == 'json':
                print(json.dumps(summary, indent=2, sort_keys=True))
            else:
                models_str = ', '.join(f'{m} ({c})' for m, c in summary['models'].items()) or 'none'
                usd = summary['usd_provider_rate_total']
                usd_str = f'${usd:.6f}' if usd is not None else 'unavailable'
                print(f"Receipts:          {summary['receipt_count']}")
                print(f"Input tokens:      {summary['total_input_tokens']:,}")
                print(f"Output tokens:     {summary['total_output_tokens']:,}")
                print(f"Cache read tokens: {summary['total_cache_read_tokens']:,}")
                print(f"Models:            {models_str}")
                print(f"USD (provider rate): {usd_str}")
                print(f"Note: {summary['usd_source_note']}")
            return 0
        if action == 'list':
            if fmt == 'json':
                print(json.dumps(receipts, indent=2))
            else:
                if not receipts:
                    print('No receipts found.')
                for r in receipts:
                    usd = r.get('usd_observed')
                    usd_str = f'${usd:.6f}' if isinstance(usd, (int, float)) else 'n/a'
                    src = r.get('usd_source', '')
                    model = r.get('model', 'unknown')
                    op_id = r.get('operation_id', '')[:16]
                    inp = r.get('input_tokens', 0)
                    out = r.get('output_tokens', 0)
                    print(f'{op_id}  {model:<28} in={inp:>7,} out={out:>6,}  {usd_str} ({src})')
            return 0
        parser.error(f'Unknown cost action: {action}')
    if args.command == "help":
        if not args.operation:
            if args.json:
                print(json.dumps({"schema_version": "1.0", "command": "help", "guide": "Use 'urace help <operation>' to get help for a specific operation."}, indent=2))
                return 0
            parser.print_help()
            return 0
        help_root=parser;help_path=list(args.operation)
        if help_path[0]=="portfolio":
            from .. import portfolio as _portfolio_help
            help_root=_portfolio_help.parser();help_path=help_path[1:]
        try:operation=command_surface.help_parser(help_root,help_path)
        except ValueError as error:parser.error(str(error))
        if args.json:
            import io as _io_help
            _buf = _io_help.StringIO()
            operation.print_help(_buf)
            guide_text = _buf.getvalue()
            print(json.dumps({"schema_version": "1.0", "command": " ".join(args.operation), "guide": guide_text}, indent=2))
            return 0
        operation.print_help()
        return 0
    args.command={"compress":"compact","decompress":"decompact"}.get(args.command,args.command)
    command_surface.validate(args,raw_args,parser)
    if hasattr(args, "status_subject") and args.status_subject in {None, "runtime", "resources", "vitals"}:
        active_config = load_config()
        if active_config.get("execution_workflow", "core") == "specification-trial":
            from ..trial import main as trial_main
            if getattr(args, "migration_dry_run", False) or getattr(args, "fail_on", None) or getattr(args, "since", None) or getattr(args, "until", None):
                parser.error("These filters inspect the generic lifecycle; use check or vitals explicitly. Active trial resources support --scope trial|epoch|lifetime.")
            subject = "runtime" if args.status_subject in {None, "runtime"} else "resources"
            route = ["status", subject]
            if subject == "resources":
                for option in ("product", "executor", "scope"):
                    value = getattr(args, option, None)
                    if value is not None: route.extend(["--" + option, value])
                if getattr(args, "all_products", False): route.append("--all-products")
            if args.json: route.append("--json")
            return trial_main(route)
        elif args.status_subject == "resources" and any(getattr(args, name, None) for name in ("product", "executor", "scope", "all_products")):
            parser.error("These scoped counters belong to the specification trial; use trial status resources explicitly.")
    if args.command == "executor-options":
        if args.model is not None and (not args.model.strip() or args.model.startswith("-") or any(ord(c) < 32 for c in args.model)):
            parser.error("model must be a nonempty model identifier")
        if args.model is not None and args.inherit_model:
            parser.error("--model and --inherit-model are mutually exclusive")
        changing = args.model is not None or args.native_effort is not None or args.inherit_model
        with state_lock(CONFIG_PATH) if changing else nullcontext():
            config = load_config()
            settings = config.setdefault("executor", {})
            known = {"codex", "claude"} | {p.get("id") for p in settings.get("providers", [])}
            if args.executor_id not in known:parser.error("unknown executor: " + args.executor_id)
            options = dict(settings.get("native_options", {}).get(args.executor_id, {}))
            if args.inherit_model:options.pop("model", None)
            elif args.model is not None:options["model"] = args.model
            if args.native_effort == "inherit":options.pop("native_effort", None)
            elif args.native_effort is not None:options["native_effort"] = args.native_effort
            if changing:
                overrides = settings.setdefault("native_options", {})
                if options:overrides[args.executor_id] = options
                else:overrides.pop(args.executor_id, None)
                save_config(config)
        print(json.dumps({"executor": args.executor_id, "native_options": options, "resource_effort": user_controls.resource_profile(config, args.executor_id)["effort"], "note": "Model/effort support is validated by the native provider at execution; settings apply to new calls."}, indent=2, sort_keys=True))
        return 0
    if args.command in {"auto-goals", "effort"}:
        if args.command == "auto-goals" and args.value is not None and args.action != "replenish":parser.error("enable/disable takes no extra value; use auto-goals replenish enable|disable")
        if args.command == "effort" and args.mode == "inherit" and not args.executor_id:parser.error("inherit requires --executor")
        changing = (args.action not in {"status"} and (args.action != "replenish" or args.value not in {None,"status"})) if args.command == "auto-goals" else args.mode != "status"
        with state_lock(CONFIG_PATH) if changing else nullcontext():
            config = load_config()
            if args.command == "auto-goals":
                action = args.value or "status" if args.action == "replenish" else args.action
                if action != "status":config.setdefault("auto_goals", {})["replenish_backlog" if args.action == "replenish" else "enabled"] = action == "enable";save_config(config)
                payload = user_controls.auto_goals(config)
            else:
                settings = config.setdefault("resources", {})
                known = {"codex", "claude"} | {p.get("id") for p in config.get("executor", {}).get("providers", [])}
                if args.executor_id and args.executor_id not in known:parser.error("unknown executor: " + args.executor_id)
                if args.mode != "status":
                    if args.executor_id:
                        overrides = settings.setdefault("executor_effort", {})
                        if args.mode == "inherit":overrides.pop(args.executor_id, None)
                        else:overrides[args.executor_id] = args.mode
                    else:settings["effort"] = args.mode
                    save_config(config)
                payload = {"global": settings.get("effort", "medium"), "per_executor": settings.get("executor_effort", {}), "effective": {p:user_controls.effort_mode(settings,p) for p in sorted(known) if p is not None}}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command in {"configuration", "self-evolution"}:
        config = load_config()
        setting = "self-evolution" if args.command == "self-evolution" else args.setting
        value = args.mode if args.command == "self-evolution" else args.value
        if setting == "show" or (value in {None,"status"} and (setting!="executor-budget" or (args.daily is None and args.monthly is None))):
            self_mode = {"NECESSARY_ONLY": "auto", "CONTINUOUS": "always", "DISABLED": "never"}.get(str(config.get("self_evolution_policy", {}).get("mode", "NECESSARY_ONLY")).upper(), "auto")
            payload = {"self-evolution": self_mode, "change-explanations": config.get("change_explanations", {}).get("mode", "disabled"), "external-metrics": config.get("external_metrics", {}).get("mode", "DISABLED").lower().replace("_", "-"), "analytics-export": config.get("analytics_export", {}).get("mode", "DISABLED").lower().replace("_", "-"), "executor-budget": {"daily": config.get("executor", {}).get("max_executor_calls_per_24h"), "monthly": config.get("executor", {}).get("max_executor_calls_per_30d")}, "evaluation": config.get("evaluation_system", {})}
            payload["workflow"] = config.get("execution_workflow", "core")
            from ..value_discovery import settings as value_settings
            payload["value-discovery"] = value_settings(config)
            payload.update({"auto-goals":user_controls.auto_goals(config),"effort":{"global":config.get("resources",{}).get("effort","medium"),"per_executor":config.get("resources",{}).get("executor_effort",{})},"native-executors":config.get("executor",{}).get("native_options",{})})
            print(json.dumps(payload, indent=2, sort_keys=True) if args.json else "\n".join(f"{key}: {value}" for key, value in payload.items()))
            return 0
        if setting == "workflow":
            if value not in {"core", "specification-trial"}: parser.error("workflow must be core or specification-trial")
            with state_lock(state_path(config)):
                config["execution_workflow"] = value
                save_config(config)
            print(json.dumps({"status":"configured","workflow":value,"applies":"new auto invocations"}))
            return 0
        if setting == "self-evolution":
            aliases = {"auto": "NECESSARY_ONLY", "always": "CONTINUOUS", "never": "DISABLED"}
            if value not in aliases: parser.error("self-evolution must be auto, always, or never")
            queued = queue_input(config, "policy_control", {"name": "self-evolution", "value": aliases[value]})
        elif setting == "change-explanations":
            if value not in {"auto", "enabled", "disabled"}: parser.error("change-explanations must be auto, enabled, or disabled")
            queued = queue_input(config, "policy_control", {"name": "change-explanations", "value": value})
        elif setting == "external-metrics":
            aliases = {"disabled": "DISABLED", "provided-only": "PROVIDED_ONLY", "discover-public-and-use-provided": "DISCOVER_PUBLIC_AND_USE_PROVIDED"}
            if value not in aliases: parser.error("external-metrics must be disabled, provided-only, or discover-public-and-use-provided")
            queued = queue_input(config, "policy_control", {"name": "external-metrics", "value": aliases[value]})
        elif setting == "analytics-export":
            aliases = {"disabled": "DISABLED", "on-demand": "ON_DEMAND", "on-checkpoint": "ON_CHECKPOINT"}
            if value not in aliases: parser.error("analytics-export must be disabled, on-demand, or on-checkpoint")
            queued = queue_input(config, "policy_control", {"name": "analytics-export", "value": aliases[value]})
        elif setting == "executor-budget":
            if value=="unlimited" and args.daily is None and args.monthly is None:daily=monthly=None
            else:
                daily=args.daily if args.daily is not None else config.get("executor",{}).get("max_executor_calls_per_24h")
                monthly=args.monthly if args.monthly is not None else config.get("executor",{}).get("max_executor_calls_per_30d")
                command_surface.validate_budget(daily,monthly,parser)
            queued = queue_input(config,"budget_control",{"daily":daily,"monthly":monthly})
        else:
            try: numeric = float(value) if value is not None else None
            except ValueError: parser.error(f"{setting} requires a numeric value")
            if numeric is None: parser.error(f"{setting} requires a numeric value")
            action = "set-minimum" if setting == "evaluation-minimum" else "set-weight"
            if action == "set-weight" and not args.component: parser.error("evaluation-weight requires --component")
            numeric=command_surface.validate_evaluation(config,action,args.component,numeric,parser)
            queued = queue_input(config, "evaluation_control", {"action": action, "component": args.component, "value": numeric})
        print(json.dumps({"status":"queued","setting":setting,"value":value,"id":queued["id"],"applies":"next safe boundary"}) if args.json else f"Queued {setting}={value}; it will apply at the next safe boundary")
        return 0
    if args.command == "change":
        config = load_config(); path = state_path(config)
        state = load_state_for_read(config)
        if state is None: return 2
        changes = [item for item in state.get("operations", []) if item.get("status") == "ACCEPTED"]
        if args.action == "list":
            rows = [{"change_id": item.get("change_id", item.get("id")), "at": item.get("accepted_at"), "decision": item.get("decision") or item.get("objective_reference"), "executor": item.get("executor", {}), "changed_files": item.get("changed_files", []), "validation": item.get("status"), "outcome_status": item.get("outcome", {}).get("status", "UNVERIFIED"), "real_user_value_verified": item.get("outcome", {}).get("real_user_value_verified", False), "attribution_state": item.get("attribution_state", "UNATTRIBUTED"), "resource_cost": item.get("usage", {}).get("cost") or item.get("usage", {}).get("total_tokens")} for item in changes]
            return _inspect_list(rows, args,
                fmt=lambda r: f"{r['change_id']}: {r['decision']} | executor={r['executor'].get('executor_id', 'unknown')} | files={', '.join(r['changed_files']) or 'none'} | attribution={r['attribution_state']} | cost={r['resource_cost']}",
                empty_msg="No accepted changes recorded",
                time_field="at")
        if not args.id: parser.error("change explain requires a change ID")
        operation = next((item for item in changes if item.get("change_id", item.get("id")) == args.id), None)
        if operation is None: parser.error(f"change not found: {args.id}")
        explanation = operation.get("explanation") or operation.get("executor_source_summary")
        generated = False
        if not explanation:
            try:
                with state_lock(path):
                    state = load_state(config)
                    operation = next(item for item in state.get("operations", []) if item.get("change_id", item.get("id")) == args.id)
                    result = intelligent_executor.explain_change(ROOT, config, state, operation)
                    explanation = str(result.get("message", "")).strip()
                    operation["explanation"] = explanation
                    operation["explanation_executor"] = result.get("__urace_route__", {})
                    operation["explained_at"] = now(); save_state(config, state)
                    generated = True
            except RuntimeError as error:
                print(f"urace: {error}", file=sys.stderr); return 2
        payload = {"change_id": args.id, "decision": operation.get("decision"), "executor": operation.get("executor", {}), "changed_files": operation.get("changed_files", []), "validation": operation.get("status"), "explanation": explanation, "generated_now": generated}
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else f"Change {args.id}\nExecutor: {payload['executor'].get('executor_id', 'unknown')}\nFiles: {', '.join(payload['changed_files']) or 'none'}\nValidation: {payload['validation']}\n\n{explanation}")
        return 0
    if args.command == "update":
        if args.action == "help":
            return _help_action("""URACE Update Guide
═══════════════════
Safely upgrade the URACE specification and runtime.

  urace update                -- orchestrated sequence: download → explain → apply
  urace update download       -- download candidate spec update
  urace update explain        -- compare accepted vs candidate; show diff
  urace update apply          -- apply the candidate update
  urace update resolve        -- resolve a checkpointed update conflict

Key options:
  --opt-in-constructs AP8,AP14  limit update scope to specific constructs or APs
  --opt-in-constructs @community-inbox  use a named bundle as scope shorthand
  --decision <text>             required for resolve; stored as DecisionRecord
  --json                        machine-readable output""", args)
        config = load_config()
        update_state_root = state_path(config).parent
        _opt_in_raw = [p.strip() for p in (args.opt_in_constructs or "").split(",") if p.strip()]
        _opt_in: list[str] = []
        for _token in _opt_in_raw:
            if _token.startswith("@"):
                _bname = _token[1:]
                if _bname not in BUILTIN_BUNDLES:
                    print(f"urace: unknown bundle '@{_bname}' in --opt-in-constructs. Use `urace derive --list-bundles` to see available bundles.", file=sys.stderr)
                    return 2
                _opt_in.extend(BUILTIN_BUNDLES[_bname])
            else:
                _opt_in.append(_token)
        if args.action is None:
            source=args.update_source or config.get('updates',{}).get('source') or updater.URACE_RUNTIME_RELEASE_URL
            try:
                downloaded=updater.download(ROOT,update_state_root,source,expected_hash=args.expected_hash) if args.expected_hash else updater.download(ROOT,update_state_root,source)
                report=updater.explain(ROOT,update_state_root,downloaded['sha256'])
                if report['status']=='NO_CHANGE':result={'status':'NO_CHANGE','candidate_sha256':downloaded['sha256'],'explanation':report}
                else:
                    confirmed=args.yes
                    if not confirmed and not args.json:
                        print(json.dumps(report,indent=2))
                        try:confirmed=input('Queue the validated migration? [y/N] ').strip().lower() in {'y','yes'}
                        except (EOFError,KeyboardInterrupt):confirmed=False
                    if not confirmed:result={'status':'REVIEW_REQUIRED','candidate_sha256':downloaded['sha256'],'explanation':report,'next':'update apply, or repeat update --source SOURCE --yes'}
                    else:
                        if config.get('self_evolution_policy',{}).get('mode','DISABLED').upper()=='DISABLED':raise ValueError('Migration requires enabled self-evolution policy')
                        payload=updater.migration_payload(ROOT,update_state_root,downloaded['sha256'])
                        if _opt_in:payload['opted_in_patterns']=_opt_in
                        queued=queue_input(config,'goal',payload);result={'status':'QUEUED','input':queued['id'],'candidate_sha256':payload['update_candidate']['sha256'],'next':'The autonomous owner validates and activates at a safe boundary'}
                print(json.dumps(result,indent=2,sort_keys=True));return 0
            except (OSError,RuntimeError,ValueError) as error:
                print(json.dumps({'status':'error','error':str(error)}) if args.json else 'Update failed: '+str(error),file=sys.stdout if args.json else sys.stderr);return 2
        try:
            if args.action == "download":
                if not args.reference:
                    parser.error("update download requires an HTTPS URL or local specification path")
                result = updater.download(ROOT, update_state_root, args.reference, expected_hash=args.expected_hash) if args.expected_hash else updater.download(ROOT, update_state_root, args.reference)
                # r98: --hash verification
                if getattr(args, "expected_hash", None):
                    import hashlib as _hashlib
                    _candidate_path = result.get("candidate") or result.get("candidate_path") or result.get("path")
                    _candidate_bytes: bytes | None = None
                    if _candidate_path:
                        try:
                            _candidate_bytes = Path(_candidate_path).read_bytes()
                        except OSError:
                            _candidate_bytes = None
                    if _candidate_bytes is not None:
                        _actual_hash = _hashlib.sha256(_candidate_bytes).hexdigest()
                        if _actual_hash != args.expected_hash.lower():
                            _hash_state = load_state_for_read(config) or {}
                            _emit_gap(_hash_state, "spec-update-hash-mismatch", "BLOCKING",
                                      f"hash mismatch: expected {args.expected_hash} got {_actual_hash}")
                            save_state(config, _hash_state)
                            print(f"ERROR: hash mismatch: expected {args.expected_hash} got {_actual_hash}", file=sys.stderr)
                            return 1
                # Stale manifest + construct set detection on download
                _dl_state = load_state_for_read(config)
                if _dl_state and (_dl_state.get("derived_manifest_refs") or _dl_state.get("construct_set_refs")):
                    _candidate_ver = result.get("candidate_spec_version") or result.get("sha256", "unknown")
                    _stale = _check_stale_derived_manifests(_dl_state, _candidate_ver)
                    if _stale:
                        save_state(config, _dl_state)
                        result["stale_derived_manifests"] = [
                            s.get("manifest_id") or s.get("construct_set_id") for s in _stale
                        ]
                    # r46: new-construct suggestions + update detection
                    _derive_updates = _suggest_derive_updates(_dl_state)
                    if any(_derive_updates.values()):
                        result["derive_updates"] = _derive_updates
            elif args.action == "explain":
                result = updater.explain(ROOT, update_state_root, args.reference)
                if _opt_in:
                    result["opted_in_constructs"] = _opt_in
                    _all_known = {**pattern_catalog_module.PATTERN_CATALOG, **pattern_catalog_module.CONSTRUCT_CATALOG}
                    _affected = [pid for pid in _opt_in if pid in _all_known]
                    result["opted_in_constructs_affected"] = _affected
                    result["opted_in_constructs_outside_scope"] = [pid for pid in _opt_in if pid not in _all_known]
                # r46: new-construct suggestions + update detection
                _ex_state = load_state_for_read(config)
                if _ex_state and (_ex_state.get("construct_set_refs") or _ex_state.get("derivation_refs") or _ex_state.get("derived_manifest_refs")):
                    _ex_updates = _suggest_derive_updates(_ex_state)
                    if any(_ex_updates.values()):
                        result["derive_updates"] = _ex_updates
            elif args.action == "resolve":
                if not str(args.decision or "").strip():
                    parser.error("update resolve requires --decision")
                state = load_state_for_read(config)
                if state is None:
                    return 2
                candidates = [goal for goal in state.get("objectives", []) if goal.get("status") == "awaiting_operator_decision" and goal.get("update_candidate")]
                if args.reference:
                    candidates = [goal for goal in candidates if goal.get("id") == args.reference or str(goal["update_candidate"].get("sha256", "")).startswith(args.reference)]
                if len(candidates) != 1:
                    parser.error("update resolve requires exactly one matching checkpointed conflict; provide its goal id or candidate hash prefix")
                queued = queue_input(config, "goal_control", {"action": "resolve-update", "id": candidates[0]["id"], "decision": args.decision.strip()})
                result = {"status": "QUEUED", "input": queued["id"], "goal": candidates[0]["id"], "candidate_sha256": candidates[0]["update_candidate"]["sha256"], "next": "the autonomous owner will resume the same candidate and repeat compatibility and validation"}
            else:
                policy = config.get("self_evolution_policy", {}).get("mode", "DISABLED").upper()
                if policy == "DISABLED":
                    parser.error("update apply requires self-evolution policy NECESSARY_ONLY or CONTINUOUS")
                payload = updater.migration_payload(ROOT, update_state_root, args.reference)
                if args.expected_hash and (not re.fullmatch('[0-9a-fA-F]{64}',args.expected_hash) or args.expected_hash.lower()!=payload['update_candidate']['sha256']):
                    print('ERROR: candidate does not match requested SHA-256',file=sys.stderr);return 1
                # r103/r104: --verify on apply — default-on unless --no-verify
                if not getattr(args, "no_verify", False):
                    import hashlib as _avhashlib
                    _av_sha = payload.get("update_candidate", {}).get("sha256", "")
                    if not _av_sha:
                        print("Note: candidate has no stored sha256; --verify skipped.", file=sys.stderr)
                    else:
                        try:
                            _av_candidate, _av_manifest = updater.resolve_candidate(update_state_root, args.reference)
                            _av_bytes = _av_candidate.read_bytes()
                            _av_computed = _avhashlib.sha256(_av_bytes).hexdigest()
                            if _av_computed != _av_sha:
                                _av_state = load_state_for_read(config) or {}
                                _emit_gap(_av_state, "spec-update-hash-mismatch", "BLOCKING",
                                          f"apply --verify: hash mismatch: expected {_av_sha} got {_av_computed}")
                                save_state(config, _av_state)
                                print(f"ERROR: candidate hash mismatch: expected {_av_sha} got {_av_computed}", file=sys.stderr)
                                return 1
                            else:
                                if not args.json:print(f"Candidate verified: {_av_sha}")
                        except (OSError, RuntimeError, ValueError) as _av_err:
                            print(f"ERROR: could not verify candidate: {_av_err}", file=sys.stderr)
                            return 2
                if _opt_in:
                    payload["opted_in_patterns"] = _opt_in
                # Stale manifest + construct set detection on apply
                _apply_state = load_state_for_read(config)
                _stale_apply: list[dict] = []
                if _apply_state and (_apply_state.get("derived_manifest_refs") or _apply_state.get("construct_set_refs")):
                    _candidate_ver_apply = payload.get("update_candidate", {}).get("sha256", "unknown")
                    _stale_apply = _check_stale_derived_manifests(_apply_state, _candidate_ver_apply)
                    if _stale_apply:
                        save_state(config, _apply_state)
                queued = queue_input(config, "goal", payload)
                result = {"status": "QUEUED", "input": queued["id"], "candidate_sha256": payload["update_candidate"]["sha256"], "next": "the autonomous owner will build and validate the isolated migration candidate at a safe boundary"}
                if _opt_in:
                    result["opted_in_patterns"] = _opt_in
                if _stale_apply:
                    result["stale_derived_manifests"] = [
                        s.get("manifest_id") or s.get("construct_set_id") for s in _stale_apply
                    ]
        except (OSError, RuntimeError, ValueError) as error:
            print(f"Update {args.action} failed: {error}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.action == "download":
            print(f"Downloaded candidate {result['sha256']} from {result['source']}; accepted implementation unchanged")
            for _mid in result.get("stale_derived_manifests", []):
                print(f"  warning: derived manifest {_mid} is stale — re-run `urace derive --constructs ... --save` after update")
            _print_derive_update_suggestions(result.get("derive_updates", {}))
        elif args.action == "explain":
            revision = result.get("source_revision") or {}
            provenance = f" | commit={revision.get('commit', '')[:12]} {revision.get('message', '')}" if revision else ""
            print(f"Candidate {result['candidate_sha256']}: {result['status']} | +{result['added_lines']} -{result['removed_lines']} | local={result['local_customizations']['status']}{provenance} | report={result['report']}")
            if _opt_in:
                print(f"  opt-in scope: {', '.join(_opt_in)} | affected: {', '.join(result.get('opted_in_constructs_affected', [])) or 'none detected'}")
            _print_derive_update_suggestions(result.get("derive_updates", {}))
        elif args.action == "resolve":
            print(f"Queued attributable resolution for {result['goal']} and candidate {result['candidate_sha256']}; no files changed")
        else:
            _scope_note = f" | opt-in: {', '.join(_opt_in)}" if _opt_in else ""
            print(f"Queued update migration {result['input']} for candidate {result['candidate_sha256']}; accepted implementation unchanged until validated activation{_scope_note}")
            for _mid in result.get("stale_derived_manifests", []):
                print(f"  warning: derived manifest {_mid} is stale — re-run `urace derive --constructs ... --save` after update")
        return 0
    if args.command == 'export':
        try: _exp_cfg = load_config()
        except Exception: _exp_cfg = {}
        _exp_sp = state_path(_exp_cfg)
        _session_file = _exp_sp.parent / "session_context.jsonl"
        _rows = []
        if _session_file.exists():
            for _line in _session_file.read_text(encoding="utf-8").splitlines():
                try: _rows.append(json.loads(_line))
                except json.JSONDecodeError: pass
        _out = Path(args.out)
        _payload = {"schema": "urace-aps-v1", "exported_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), "turns": _rows}
        _out.write_text(json.dumps(_payload, indent=2), encoding="utf-8")
        if args.json: print(json.dumps({"status": "ok", "file": str(_out), "turns": len(_rows)}))
        else: print(f"Exported {len(_rows)} turn(s) to {_out}")
        return 0
    if args.command == 'import':
        _src = Path(args.file)
        if not _src.exists(): print(f"File not found: {_src}", file=sys.stderr); return 1
        _payload = json.loads(_src.read_text(encoding="utf-8"))
        _turns = _payload.get("turns", [])
        try: _imp_cfg = load_config()
        except Exception: _imp_cfg = {}
        _imp_sp = state_path(_imp_cfg)
        _session_file = _imp_sp.parent / "session_context.jsonl"
        _session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(_session_file, "w", encoding="utf-8", newline="\n") as _f:
            for _t in _turns: _f.write(json.dumps(_t) + "\n")
        if args.json: print(json.dumps({"status": "ok", "turns": len(_turns)}))
        else: print(f"Imported {len(_turns)} turn(s) from {_src}")
        return 0
    if args.command == 'report' and getattr(args, 'action', None) is None:
        try: _rep_cfg = load_config()
        except Exception: _rep_cfg = {}
        _rep_state_path = state_path(_rep_cfg)
        _rep_state = {}
        if _rep_state_path.exists():
            try: _rep_state = json.loads(_rep_state_path.read_text(encoding="utf-8"))
            except Exception: pass
        _rep_out = Path(getattr(args, 'out', 'urace_report.html'))
        _rep_rows = []
        _rep_ledger = _rep_state_path.parent / "ledger.jsonl"
        if _rep_ledger.exists():
            for _line in _rep_ledger.read_text(encoding="utf-8").splitlines()[-100:]:
                try: _rep_rows.append(json.loads(_line))
                except Exception: pass
        _rep_html = _render_report_html(_rep_state, _rep_rows)
        _rep_out.write_text(_rep_html, encoding="utf-8", newline="\n")
        if args.json: print(json.dumps({"status": "ok", "file": str(_rep_out)}))
        else: print(f"Report written to {_rep_out}")
        return 0
    if args.command == 'audit':
        try: _aud_cfg = load_config()
        except Exception: _aud_cfg = {}
        _aud_log = state_path(_aud_cfg).parent / "audit.jsonl"
        if not _aud_log.exists():
            if args.json: print(json.dumps({"status": "no_audit_log"}))
            else: print("No audit log found.")
            return 0
        _aud_records = []
        for _line in _aud_log.read_text(encoding="utf-8").splitlines():
            try: _aud_records.append(json.loads(_line))
            except Exception: pass
        if getattr(args, 'verify', False):
            from ..peer_exchange import verify_audit_chain
            _ok, _broken = verify_audit_chain(_aud_records)
            if args.json: print(json.dumps({"status": "ok" if _ok else "chain_broken", "broken_at": _broken, "records": len(_aud_records)}))
            else: print(f"Audit chain: {'OK' if _ok else f'BROKEN at record {_broken}'} ({len(_aud_records)} records)")
        else:
            if args.json: print(json.dumps({"records": _aud_records[-20:], "total": len(_aud_records)}))
            else:
                for _r in _aud_records[-20:]:
                    print(f"  {_r.get('kind','?')} | {_r.get('operation','?')} | {_r.get('at','?')}")
        return 0
    config = load_config()
    path = state_path(config)
    if getattr(args, 'resume', False):
        _session_turns = _load_session_context(config)
        config["_resume_session"] = True
        if _session_turns:
            _logger.debug("Resumed %d session turns", len(_session_turns))
    if args.command in {"auto", "autonomous"} and config.get("execution_workflow", "core") == "specification-trial":
        if getattr(args, "force_discovery", False): parser.error("specification-trial does not bypass acceptance, availability or allocation guards")
        from ..trial import run_workflow
        explicit_interval = any(a == "--interval" or a.startswith("--interval=") for a in raw_args)
        return run_workflow(args.cycles, dry_run=args.dry_run, interval=args.interval if explicit_interval else 5, json_mode=args.json, quiet=args.quiet)
    if args.command=="init":
        from .. import bootstrap
        if args.ready:
            return bootstrap.complete(sys.modules[__name__],config)
        if not getattr(sys.modules[__name__], '_INIT_AUTO_ACTIVE', False):
            sys.modules[__name__]._INIT_AUTO_ACTIVE = True
            try:
                return bootstrap.auto_complete(sys.modules[__name__],config)
            except KeyboardInterrupt:
                return 130
            finally:
                sys.modules[__name__]._INIT_AUTO_ACTIVE = False
        # re-entrant call from inside auto_complete — fall through to state init
    if args.command == "commands":
        catalog = command_catalog()
        catalog["by_concern"] = command_surface.catalog(parser)
        if args.json:
            print(json.dumps(catalog, indent=2, sort_keys=True))
        else:
            for group, entries in catalog.items():
                if group=="by_concern":
                    for concern,commands in entries.items():
                        print(concern+": "+", ".join(item["command"] for item in commands))
                    continue
                print(group.replace("_", " ").title() + ":")
                for entry in entries:
                    print(f"  {entry['command']}: {entry['purpose']}")
        return 0
    if args.command == "portfolio":
        helper = RUNTIME_ROOT / "urace" / "portfolio.py"
        if not helper.exists():
            parser.error("portfolio helper is not installed in this deployment")
        forwarded = (["--help"] if args.portfolio_help else []) + args.portfolio_args
        try:
            return command_surface.forward([sys.executable,str(helper),*forwarded],ROOT)
        except KeyboardInterrupt:
            return 130
    if args.command == "report":
        if args.action == "status":
            capability = analytics.capabilities()
            if args.json: print(json.dumps(capability, indent=2, sort_keys=True))
            else:
                print(f"Portable CSV/HTML: {capability['portable_csv_html']['status']} ({capability['portable_csv_html']['dependency']})")
                print(f"Native XLSX: {capability['native_xlsx']['status']} (optional dependency: {capability['native_xlsx']['dependency']})")
                print("Canonical control dependency: NONE")
            return 0
        state = load_state_for_read(config)
        if state is None:
            return 2
        output = Path(args.output)
        if not output.is_absolute(): output = ROOT / output
        try:
            manifest = analytics.export_portable(ROOT, state, vitals_snapshot(config, state), output, include_xlsx=args.xlsx)
        except RuntimeError as error:
            parser.error(str(error))
        if args.json: print(json.dumps({"output": str(output), **manifest}, indent=2, sort_keys=True))
        else: print(f"Portable analytics exported atomically to {output}\nFormats: {', '.join(manifest['formats'])}; state version: {manifest['state_version']}")
        return 0
    if args.command in {"auto","autonomous"} and args.dry_run:
        state=load_state_for_read(config)
        if state is None:return 2
        payload={"mode":"dry-run","lifecycle":state.get("lifecycle_state"),"objectives":[{k:o.get(k) for k in ("id","title","status")} for o in state.get("objectives",[]) if o.get("status") in {"active","planned"}],"cycles_run":0,"executor_calls":0,"writes":0,"note":"Snapshot preview only; eligibility and future outcomes are not simulated."}
        print(json.dumps(payload,indent=2) if args.json else "Dry-run: no cycles, writes, network or Executor calls.\nLifecycle: "+str(payload["lifecycle"])+"\nExisting objectives: "+str(len(payload["objectives"])))
        return 0
    if args.command == "autonomous":args.command="auto"
    if args.command == "github":
        import os as _os
        _gh_action = getattr(args, "github_action", None)
        _token = _os.environ.get(getattr(args, "token_env", None) or "URACE_GITHUB_TOKEN", "")
        _repo = getattr(args, "repo", None) or config.get("github", {}).get("repo")
        _json_out = getattr(args, "json", False) or getattr(args, "format", None) == "json"
        def _gh_api(path, *, method="GET", body=None):
            import urllib.request as _ur
            _url = f"https://api.github.com/{path.lstrip('/')}"
            _data = json.dumps(body).encode() if body else None
            _req = _ur.Request(_url, data=_data, method=method,
                headers={"Accept": "application/vnd.github+json",
                         "User-Agent": "urace-github/1",
                         **({"Authorization": f"Bearer {_token}"} if _token else {})})
            with _ur.urlopen(_req, timeout=15) as _r:  # noqa: S310
                return json.loads(_r.read().decode())
        if _gh_action == "status":
            _result = {"github_token_set": bool(_token), "repo": _repo}
            if _repo and _token:
                try:
                    _info = _gh_api(f"repos/{_repo}")
                    _result.update({"connected": True, "default_branch": _info.get("default_branch"), "open_issues": _info.get("open_issues_count"), "visibility": _info.get("visibility"), "url": _info.get("html_url")})
                except Exception as _ge:
                    _result.update({"connected": False, "error": str(_ge)})
            elif not _token:
                _result["hint"] = "Set URACE_GITHUB_TOKEN env var to connect"
            elif not _repo:
                _result["hint"] = "Run: urace github connect owner/repo"
            if _json_out:
                print(json.dumps(_result, indent=2))
            else:
                print(f"GitHub: {'connected' if _result.get('connected') else 'not connected'}")
                if _repo:
                    print(f"  repo: {_repo}")
                for k in ("default_branch", "open_issues", "visibility", "url", "hint", "error"):
                    if k in _result:
                        print(f"  {k}: {_result[k]}")
            return 0
        if _gh_action == "connect":
            _new_repo = getattr(args, "repo", None)
            if not _new_repo or _new_repo.count("/") != 1:
                _err = {"status": "error", "error": "repo must be in owner/repo format"}
                print(json.dumps(_err) if _json_out else f"Error: {_err['error']}"); return 1
            _token_env = getattr(args, "token_env", "URACE_GITHUB_TOKEN")
            with state_lock(CONFIG_PATH):
                config = load_config()
                config.setdefault("github", {}).update({"repo": _new_repo, "token_env": _token_env})
                save_config(config)
            _res = {"status": "connected", "repo": _new_repo, "token_env": _token_env}
            print(json.dumps(_res, indent=2) if _json_out else f"Connected to {_new_repo} (token via ${_token_env})")
            return 0
        if _gh_action == "push-goals":
            if not (_repo and _token):
                _err = {"status": "error", "error": "GitHub not configured; run: urace github connect owner/repo"}
                print(json.dumps(_err) if _json_out else f"Error: {_err['error']}"); return 1
            state = load_state_for_read(config)
            _objectives = [o for o in (state or {}).get("objectives", []) if o.get("status") != "DONE"]
            _dry = getattr(args, "dry_run", False)
            _created = []
            for _obj in _objectives[:20]:
                _title = (_obj.get("text") or _obj.get("id") or "")[:256]
                _obj_id = _obj.get("id", "")
                _obj_text = _obj.get("text", "")
                _body_md = f"**Objective ID**: `{_obj_id}`\n\n{_obj_text}\n\n*Created by URACE push-goals*"
                if _dry:
                    _created.append({"dry_run": True, "title": _title})
                else:
                    try:
                        _issue = _gh_api(f"repos/{_repo}/issues", method="POST", body={"title": _title, "body": _body_md, "labels": ["urace"]})
                        _created.append({"issue": _issue.get("number"), "url": _issue.get("html_url"), "title": _title})
                    except Exception as _ie:
                        _created.append({"error": str(_ie), "title": _title})
            _res = {"status": "ok", "dry_run": _dry, "objectives_pushed": len(_created), "issues": _created}
            print(json.dumps(_res, indent=2) if _json_out else f"Pushed {len(_created)} objectives as issues" + (" (dry-run)" if _dry else ""))
            return 0
        if _gh_action == "trigger-workflow":
            if not (_repo and _token):
                _err = {"status": "error", "error": "GitHub not configured; run: urace github connect owner/repo"}
                print(json.dumps(_err) if _json_out else f"Error: {_err['error']}"); return 1
            _wf = getattr(args, "workflow", "")
            _ref = getattr(args, "ref", "main")
            _inputs_raw = getattr(args, "inputs", None)
            _inputs = {}
            if _inputs_raw:
                try:
                    _inputs = json.loads(_inputs_raw)
                except json.JSONDecodeError as _je:
                    print(json.dumps({"status": "error", "error": f"Invalid inputs JSON: {_je}"}) if _json_out else "Error: invalid --inputs JSON"); return 1
            try:
                _gh_api(f"repos/{_repo}/actions/workflows/{_wf}/dispatches", method="POST", body={"ref": _ref, "inputs": _inputs})
                _res = {"status": "triggered", "repo": _repo, "workflow": _wf, "ref": _ref}
            except Exception as _we:
                _res = {"status": "error", "error": str(_we)}
            print(json.dumps(_res, indent=2) if _json_out else (f"Triggered {_wf} on {_ref}" if _res.get("status") == "triggered" else f"Error: {_res.get('error')}"))
            return 0 if _res.get("status") == "triggered" else 1
    if args.command == "git":
        import subprocess as _sp
        _git_args = getattr(args, "git_args", [])
        # argparse REMAINDER captures --json before argparse can parse it; strip it here
        _json_out_flag = "--json" in _git_args
        if _json_out_flag:
            _git_args = [a for a in _git_args if a != "--json"]
        # Use SYSTEM_ROOT (the actual git checkout root) when ROOT has no .git dir
        _git_cwd = str(ROOT) if (ROOT / ".git").is_dir() else str(SYSTEM_ROOT)
        _res = _sp.run(["git"] + _git_args, cwd=_git_cwd, text=True, capture_output=True)
        _json_out = _json_out_flag or getattr(args, "json", False) or getattr(args, "format", None) == "json"
        if _json_out:
            print(json.dumps({"returncode": _res.returncode, "stdout": _res.stdout, "stderr": _res.stderr}))
        else:
            if _res.stdout:
                print(_res.stdout, end="")
            if _res.stderr:
                print(_res.stderr, end="", file=__import__("sys").stderr)
        return _res.returncode
    if args.command == "gh":
        import subprocess as _sp, shutil as _sh
        _json_out_flag_gh = "--json" in getattr(args, "gh_args", [])
        _json_out = _json_out_flag_gh or getattr(args, "json", False) or getattr(args, "format", None) == "json"
        if not _sh.which("gh"):
            _err = {"status": "error", "error": "gh CLI not found; install from https://cli.github.com"}
            print(json.dumps(_err) if _json_out else f"Error: {_err['error']}"); return 1
        _gh_args = getattr(args, "gh_args", [])
        _gh_cwd = str(ROOT) if (ROOT / ".git").is_dir() else str(SYSTEM_ROOT)
        _res = _sp.run(["gh"] + _gh_args, cwd=_gh_cwd, text=True, capture_output=True)
        if _json_out:
            print(json.dumps({"returncode": _res.returncode, "stdout": _res.stdout, "stderr": _res.stderr}))
        else:
            if _res.stdout:
                print(_res.stdout, end="")
            if _res.stderr:
                print(_res.stderr, end="", file=__import__("sys").stderr)
        return _res.returncode
    if args.command == "run":
        # alias: run one improvement cycle (urace auto --cycles 1)
        return main(["auto", "--cycles", "1"] + (["--json"] if getattr(args,"json",False) else []))

    if args.command == "start":
        from .. import bootstrap as _bs, _daemon as _dm
        import argparse as _ap
        # init if not yet done
        _bs.auto_complete(sys.modules[__name__], config)
        # reload config after init
        try:
            import json as _j
            from .._common import CONFIG_PATH as _cp
            config = _j.loads(_cp.read_text())
        except Exception:
            pass
        # start daemon (which now also starts P2P serve)
        _start_args = _ap.Namespace(command='daemon', daemon_action='start',
                                     json=getattr(args,'json',False),
                                     format=getattr(args,'format',None),
                                     interval_minutes=getattr(args,'interval_minutes',30.0),
                                     max_cycles=0, cycles=0)
        return _dm.dispatch(_start_args, config)

    if args.command == "stop":
        from .. import _daemon as _dm
        import argparse as _ap
        _stop_args = _ap.Namespace(command='daemon', daemon_action='stop',
                                    json=getattr(args,'json',False),
                                    format=getattr(args,'format',None))
        return _dm.dispatch(_stop_args, config)

    if args.command in ("shell", "dashboard"):
        if args.command == "dashboard":
            from .. import tui as _tui
            return _tui.launch(config, SYSTEM_ROOT)
        from .. import shell as _shell
        return _shell.run_shell(config)

    if args.command == "daemon":
        from .. import _daemon
        return _daemon.dispatch(args, config)
    if args.command == "m2m":
        import sys as _sys
        _body = None
        if getattr(args, 'stdin', False):
            _body = _sys.stdin.read().strip()
        elif getattr(args, 'schema', None):
            _body = args.schema
        if not _body:
            _err = {'status':'error','error':'Provide JSON body as positional arg or via --stdin'}
            print(json.dumps(_err)); return 1
        try:
            _req = json.loads(_body)
        except json.JSONDecodeError as _je:
            print(json.dumps({'status':'error','error':f'Invalid JSON: {_je}'})); return 1
        _cmd = _req.get('command','')
        _params = _req.get('params', {})
        if not _cmd:
            print(json.dumps({'status':'error','error':'Missing "command" field'})); return 1
        _argv = _cmd.split() + [f'--{k.replace("_","-")}={v}' if not isinstance(v,bool) else (f'--{k.replace("_","-")}' if v else '') for k,v in _params.items() if not isinstance(v,bool) or v]
        _argv = [a for a in _argv if a]
        _argv.append('--json')
        return main(_argv)
    if args.command == "evidence":
        state = load_state_for_read(config)
        if state is None:
            return 2
        records = list(reversed(state.get("evidence", [])))
        if args.kind:
            records = [r for r in records if r.get("kind") == args.kind]
        return _inspect_list(records, args,
            fmt=lambda r: f"{r.get('id','?')}: {r.get('kind','?')} at={r.get('at','?')} {str(r.get('summary', r.get('kind','')))[:60]}",
            empty_msg="No evidence records.")
    if args.command == "blocker":
        if args.action == "list":
            state = load_state_for_read(config)
            if state is None:
                return 2
            blockers = state.get("blockers", [])
            if not args.resolved:
                blockers = [b for b in blockers if b.get("resolved_at") is None]
            if args.scope:
                blockers = [b for b in blockers if b.get("scope") == args.scope]
            return _inspect_list(blockers, args,
                fmt=lambda b: f"{b.get('id','?')}: scope={b.get('scope','?')} count={b.get('count',1)} [{b.get('classification','?')}] last_at={b.get('last_at','?')}",
                empty_msg="No active blockers.",
                time_field=None)
        if args.action == "resolve":
            if not args.blocker_id:
                parser.error("blocker resolve requires a blocker_id")
            state_rw = load_state(config)
            blockers = state_rw.get("blockers", [])
            blocker = next((b for b in blockers if b.get("id") == args.blocker_id), None)
            if blocker is None:
                result = {"blocker_id": args.blocker_id, "status": "not-found", "error": "no blocker with that ID"}
                print(json.dumps(result, indent=2) if args.json else f"error: blocker {args.blocker_id} not found")
                return 1
            if blocker.get("resolved_at"):
                result = {"blocker_id": args.blocker_id, "status": "error", "error": "already resolved"}
                print(json.dumps(result, indent=2) if args.json else f"error: blocker {args.blocker_id} already resolved")
                return 1
            blocker["resolved_at"] = now()
            blocker["resolved_by"] = "operator"
            note = getattr(args, "note", None) or ""
            state_rw.setdefault("evidence", []).append({
                "id": identifier("evidence"), "at": now(),
                "kind": "blocker-operator-resolved",
                "summary": f"Blocker {args.blocker_id} cleared by operator; note={note}",
                "blocker_id": args.blocker_id,
            })
            _emit_trace(state_rw, "OPERATION", f"blocker {args.blocker_id} resolved by operator")
            save_state(config, state_rw)
            result = {"blocker_id": args.blocker_id, "status": "resolved", "resolved_at": blocker["resolved_at"]}
            print(json.dumps(result, indent=2) if args.json else f"blocker {args.blocker_id}: resolved")
            return 0
    if args.command == "decision":
        from .. import decision_feedback as df
        if args.action=='assess':
            if not args.decision_id:parser.error('decision assess requires a decision ID')
            try:
                with state_lock(state_path(config)):
                    state=load_state(config);record=next((r for r in reversed(state.get('decision_records',[])) if r.get('id')==args.decision_id),None)
                    if record is None:raise ValueError('Decision not found')
                    if args.forecast:
                        if len(args.forecast.encode())>12288:raise ValueError('Forecast exceeds 12KiB')
                        forecast=json.loads(args.forecast)
                        # Validate references before recording an owner forecast.
                        bottleneck=forecast.get('bottleneck_id') if isinstance(forecast,dict) else None
                        if bottleneck and not any(v.get('id')==bottleneck for group in ('integrity_gaps','blockers','progress_observations') for v in state.get(group,[])):raise ValueError('Bottleneck must reference a detected gap or blocker')
                        df.register_forecast(state,record,forecast)
                        save_state(config,state) # Persist the prediction before any optional inference.
                    result=df.assess(config,state,record);df.refresh(config,state);save_state(config,state)
                print(json.dumps(result,indent=2,sort_keys=True));return 0
            except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:parser.error(str(error))
        state = load_state_for_read(config)
        if state is None:
            return 2
        if args.action == "list":
            records = list(reversed(state.get("decision_records", [])))
            if df.settings(config)["enabled"]:
                indexed=df.indexes(state);records=[{**r,"benefit_evaluation":df.compact(df.view(config,state,r,indexed))} for r in records]
            if args.stale:
                records = [r for r in records if r.get("provenance_revised")]
            if args.scope:
                records = [r for r in records if r.get("scope") == args.scope]
            return _inspect_list(records, args,
                fmt=lambda r: f"{r.get('id','?')}: outcome={r.get('outcome','?')} status={r.get('benefit_evaluation',{}).get('status','UNASSESSED')} score={r.get('benefit_evaluation',{}).get('expected_benefit_score')} action={r.get('benefit_evaluation',{}).get('action_recommendation')} decided_at={r.get('decided_at') or r.get('at','?')}{' [STALE]' if r.get('provenance_revised') else ''}",
                empty_msg="No decision records.",
                time_field=None)
        if args.action == "inspect":
            if not args.decision_id:
                parser.error("decision inspect requires a decision_id")
            record = next((r for r in state.get("decision_records", []) if r.get("id") == args.decision_id), None)
            if record is None:
                print(json.dumps({"error": f"decision {args.decision_id} not found"}, indent=2) if args.json else f"error: decision {args.decision_id} not found")
                return 1
            if df.settings(config)["enabled"]:record={**record,"benefit_evaluation":df.view(config,state,record)}
            print(json.dumps(record, indent=2, sort_keys=True) if args.json else "\n".join(f"{k}: {v}" for k, v in record.items()))
            return 0
    if args.command == "integrity-signal":
        state = load_state_for_read(config)
        if state is None:
            return 2
        signals = state.get("integrity_signals", [])
        if not args.resolved:
            signals = [s for s in signals if not s.get("resolved_at")]
        if args.signal_type:
            signals = [s for s in signals if s.get("signal_type") == args.signal_type]
        if args.severity:
            signals = [s for s in signals if s.get("severity") == args.severity]
        if args.json:
            print(json.dumps(signals, indent=2, sort_keys=True))
        else:
            for s in signals:
                print(f"{s.get('id', '?')}: type={s.get('signal_type', '?')} severity={s.get('severity', '?')} at={s.get('at', '?')}")
        return 0
    if args.command == "govern":
        if args.action == "list-gates":
            state = load_state_for_read(config)
            if state is None:
                return 2
            gaps = state.get("integrity_gaps", [])
            gates = [g for g in gaps if g.get("active", True) is not False and g.get("severity") == "BLOCKING"]
            if args.json:
                print(json.dumps(gates, indent=2, sort_keys=True))
            else:
                for g in gates:
                    print(f"{g.get('id', '?')}: kind={g.get('kind', '?')} detail={g.get('detail', '')} created_at={g.get('at', '?')}")
            return 0
        if args.action == "clear":
            if not args.gap_id:
                parser.error("govern clear requires a gap_id")
            state_rw = load_state(config)
            gaps = state_rw.get("integrity_gaps", [])
            gap = next((g for g in gaps if g.get("id") == args.gap_id or g.get("kind") == args.gap_id), None)
            if gap is None:
                result = {"gap_id": args.gap_id, "status": "not-found", "error": "no integrity gap with that ID or kind"}
                print(json.dumps(result, indent=2) if args.json else f"error: gap {args.gap_id} not found")
                return 1
            if gap.get("active") is False:
                result = {"gap_id": args.gap_id, "status": "error", "error": "gap already cleared"}
                print(json.dumps(result, indent=2) if args.json else f"error: gap {args.gap_id} already cleared")
                return 1
            gap["active"] = False
            gap["cleared_at"] = now()
            gap["cleared_by"] = "operator"
            gap["clearance_note"] = getattr(args, "note", None)
            state_rw.setdefault("evidence", []).append({
                "id": identifier("evidence"), "at": now(),
                "kind": "operator-gate-cleared",
                "summary": f"Gap {args.gap_id} cleared by operator",
                "gap_id": gap.get("id"),
            })
            save_state(config, state_rw)
            result = {"gap_id": gap.get("id"), "kind": gap.get("kind"), "cleared_at": gap["cleared_at"], "status": "cleared"}
            print(json.dumps(result, indent=2) if args.json else f"gap {gap.get('id')}: cleared")
            return 0
    if args.command == "inbox":
        if args.action == "help":
            return _help_action("""URACE Inbox Guide
══════════════════
Manage community patch proposals.

  urace inbox list                       -- list pending patch proposals
  urace inbox status <id>                -- inspect a specific proposal
  urace inbox apply <proposal_id>        -- approve and apply a proposal
  urace inbox reject <proposal_id> [--reason <text>] -- reject a proposal""", args)
        if args.action in {"apply", "reject"}:
            proposal_id = args.input_id
            if not proposal_id:
                parser.error(f"inbox {args.action} requires a proposal_id")
            state_rw = load_state(config)
            proposals = state_rw.get("patch_proposals", [])
            prop = next((p for p in proposals if p.get("id") == proposal_id), None)
            if not prop:
                result = {"proposal_id": proposal_id, "status": "not-found", "error": "no PatchProposal with that ID"}
                print(json.dumps(result, indent=2) if args.json else f"error: proposal {proposal_id} not found")
                return 1
            if prop.get("status") != "PENDING":
                result = {"proposal_id": proposal_id, "status": prop.get("status"), "error": "proposal is not in PENDING state"}
                print(json.dumps(result, indent=2) if args.json else f"error: proposal {proposal_id} is {prop.get('status')}, not PENDING")
                return 1
            if args.action == "apply":
                prop["status"] = "APPROVED"
                prop["resolved_at"] = now()
                prop["resolved_by"] = "operator"
                prop["updated_at"] = now()
                _emit_trace(state_rw, "DECISION", f"proposal {proposal_id} APPROVED by operator")
                save_state(config, state_rw)
                result = {"proposal_id": proposal_id, "status": "APPROVED"}
                print(json.dumps(result, indent=2) if args.json else f"proposal {proposal_id}: APPROVED")
            else:
                prop["status"] = "REJECTED"
                prop["resolved_at"] = now()
                prop["rejection_reason"] = args.reason or "operator rejected"
                prop["updated_at"] = now()
                _emit_trace(state_rw, "DECISION", f"proposal {proposal_id} REJECTED by operator")
                save_state(config, state_rw)
                result = {"proposal_id": proposal_id, "status": "REJECTED", "rejection_reason": prop["rejection_reason"]}
                print(json.dumps(result, indent=2) if args.json else f"proposal {proposal_id}: REJECTED")
            return 0
        if args.action == "status":
            input_id = args.input_id
            if not input_id:
                parser.error("inbox status requires an input_id")
            pending_ids: set[str] = set()
            for _p in input_directory(config).glob("*.json"):
                try:
                    _pid = json.loads(_p.read_text(encoding="utf-8")).get("id")
                    if _pid:
                        pending_ids.add(_pid)
                except (OSError, json.JSONDecodeError):
                    pass
            state_ro = load_state_for_read(config)
            processed_ids = list(state_ro.get("processed_input_ids", [])) if state_ro else []
            evidence_records = [e for e in (state_ro or {}).get("evidence", []) if e.get("source_input") == input_id or e.get("input") == input_id]
            if input_id in processed_ids:
                status_val = "consumed"
            elif input_id in pending_ids:
                status_val = "pending"
            else:
                rejected = [e for e in evidence_records if e.get("kind") == "authoritative-input-rejected"]
                status_val = "rejected" if rejected else "not-found"
            result = {"input_id": input_id, "status": status_val, "evidence": evidence_records}
            print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"{input_id}: {status_val}")
            return 0
        items = []
        for inbox_path in sorted(input_directory(config).glob("*.json")):
            try:
                items.append(json.loads(inbox_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                items.append({"file": inbox_path.name, "status": "MALFORMED"})
        if getattr(args, "kind", None):
            items = [item for item in items if item.get("kind") == args.kind]
        if getattr(args, "status", None):
            items = [item for item in items if item.get("status", "QUEUED") == args.status]
        if getattr(args, "limit", None) is not None:
            items = items[:args.limit]
        print(json.dumps(items, indent=2, sort_keys=True) if args.json else ("\n".join(f"{item.get('id', item.get('file'))}: {item.get('kind', 'unknown')} {item.get('status', 'QUEUED')}" for item in items) or "Inbox empty"))
        return 0
    if args.command == "onboard":
        config_ro = load_config()  # already loaded above as `config`
        state_ro = load_state_for_read(config_ro)
        product_name = config_ro.get("product", "")
        onboard_records = (state_ro or {}).get("onboard_records", [])
        active_record = next(
            (r for r in onboard_records
             if r.get("product_name") == product_name and not r.get("superseded_at")),
            None
        )

        if args.action == "help":
            return _help_action("""URACE Onboard Guide
═══════════════════

Products can reside anywhere — subdirectory, sibling folder, absolute path, or spread
across multiple locations. URACE is agnostic to folder structure; product_files accepts
any readable path (relative to bootstrap root or absolute).

Step 1 — Bootstrap URACE
  Give URACE.md to a capable Executor and say "Bootstrap."
  URACE creates the urace/ system files and activates the `urace` command.

Step 2 — Configure your Product
  Edit urace/config.json:
    product        → a name for your product  (e.g. "my-app")
    product_files  → list of readable file paths, any layout, any location
    state_path     → where this product's state lives  (e.g. "urace/state.json")
    intent.purpose → what you want URACE to improve

Step 3 — Check onboard gates
  urace onboard status

Step 4 — Confirm and activate
  urace onboard confirm

Multiple Products:
  urace product register <name> --state-path <path> --product-files <files>
  urace product switch <name>
  urace onboard confirm
  urace fleet run        <- run all products in parallel

Tip: run `urace onboard status --scan` to detect potential unregistered products nearby.""", args)

        if args.action == "status":
            # Evaluate gates without mutating state
            gates = []
            # Gate 1
            missing = []
            if not config_ro.get("product"): missing.append("product")
            if not config_ro.get("intent", {}).get("purpose"): missing.append("intent.purpose")
            gates.append({"name": "config-completeness", "status": "PASS" if not missing else "FAIL",
                          "detail": f"missing: {missing}" if missing else "ok"})
            # Gate 2
            import os as _os
            pfiles = config_ro.get("product_files", [])
            unreadable = [p for p in pfiles if not _os.access(str(ROOT / p), _os.R_OK)]
            gates.append({"name": "product-files-readable", "status": "PASS" if not unreadable else "FAIL",
                          "detail": f"unreadable: {unreadable}" if unreadable else "ok"})
            # Gate 3
            has_intent = bool(config_ro.get("intent", {}).get("purpose"))
            gates.append({"name": "intent-anchored", "status": "PASS" if has_intent else "FAIL",
                          "detail": "ok" if has_intent else "intent.purpose is empty"})
            # Gate 4 (WARNING)
            has_env = bool(config_ro.get("capability_envelope"))
            gates.append({"name": "capability-envelope-declared", "status": "PASS" if has_env else "WARN",
                          "detail": "ok" if has_env else "missing — will be unconstrained"})
            # Gate 5 (INFO)
            has_policy = bool(config_ro.get("self_evolution_policy"))
            gates.append({"name": "self-evolution-policy-recorded", "status": "PASS" if has_policy else "INFO",
                          "detail": "ok" if has_policy else "absent — NECESSARY_ONLY will be applied as default"})

            blocking_fail = any(g["status"] == "FAIL" for g in gates[:3])
            overall = "BLOCKED" if blocking_fail else ("AWAITING_CONFIRM" if not active_record else "ONBOARDED")
            current_digest = product_digest(config_ro)
            digest_match = active_record.get("config_digest") == current_digest if active_record else None

            result = {
                "product": product_name,
                "lifecycle_state": (state_ro or {}).get("lifecycle_state", "UNKNOWN"),
                "onboard_status": overall,
                "active_record": {"id": active_record["id"], "confirmed_at": active_record.get("confirmed_at"),
                                  "config_digest_match": digest_match} if active_record else None,
                "gates": gates,
            }
            # --scan: heuristic detection of potential unregistered products nearby
            scan_hints: list[dict] = []
            if getattr(args, "scan", False):
                import os as _os
                cwd = _os.getcwd()
                parent = _os.path.dirname(cwd)
                _PRODUCT_MARKERS = {
                    "package.json", "Cargo.toml", "go.mod", "pyproject.toml",
                    "setup.py", "pom.xml", "build.gradle", "Makefile", "README.md",
                }
                _CODE_EXTS = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".cpp", ".c", ".cs", ".php"}
                registry = config_ro.get("product_registry", [])
                registered_roots: set[str] = set()
                for entry in registry:
                    sp = entry.get("state_path", "")
                    if sp:
                        registered_roots.add(_os.path.normpath(_os.path.dirname(_os.path.abspath(sp))))
                    for pf in entry.get("product_files", []):
                        registered_roots.add(_os.path.normpath(_os.path.abspath(pf) if _os.path.isabs(pf) else _os.path.join(cwd, pf)))
                registered_roots.add(_os.path.normpath(cwd))
                candidates: list[str] = []
                try:
                    for entry in _os.scandir(parent):
                        if entry.is_dir() and not entry.name.startswith(".") and entry.name not in {"urace", "node_modules", "__pycache__", ".git"}:
                            candidates.append(entry.path)
                except PermissionError:
                    pass
                try:
                    for entry in _os.scandir(cwd):
                        if entry.is_dir() and not entry.name.startswith(".") and entry.name not in {"urace", "node_modules", "__pycache__", ".git"}:
                            candidates.append(entry.path)
                except PermissionError:
                    pass
                for candidate in candidates:
                    norm = _os.path.normpath(candidate)
                    if norm in registered_roots:
                        continue
                    looks_like_product = False
                    try:
                        for item in _os.scandir(candidate):
                            if item.is_file():
                                if item.name in _PRODUCT_MARKERS:
                                    looks_like_product = True
                                    break
                                if _os.path.splitext(item.name)[1] in _CODE_EXTS:
                                    looks_like_product = True
                                    break
                    except PermissionError:
                        pass
                    if looks_like_product:
                        hint = {
                            "kind": "onboard-unregistered-product-hint",
                            "severity": "INFO",
                            "path": candidate,
                            "suggestion": f"urace product register {_os.path.basename(candidate)} --state-path {candidate}/urace_state.json --product-files {candidate}",
                        }
                        scan_hints.append(hint)
            result["scan_hints"] = scan_hints
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Product: {product_name}")
                print(f"Status:  {overall}")
                if active_record:
                    match_str = "MATCH" if digest_match else "DIVERGED"
                    print(f"OnboardRecord: {active_record['id']} (confirmed {active_record.get('confirmed_at','?')}) config_digest={match_str}")
                print("Gates:")
                for g in gates:
                    print(f"  [{g['status']:4s}] {g['name']}: {g['detail']}")
                if scan_hints:
                    print("\nPotential unregistered products detected nearby:")
                    for h in scan_hints:
                        print(f"  [INFO] {h['path']}")
                        print(f"         → {h['suggestion']}")
            return 0

        if args.action == "confirm":
            # Re-evaluate gates; if BLOCKING fail, exit 1
            import os as _os
            missing = []
            if not config_ro.get("product"): missing.append("product")
            if not config_ro.get("intent", {}).get("purpose"): missing.append("intent.purpose")
            pfiles = config_ro.get("product_files", [])
            unreadable = [p for p in pfiles if not _os.access(str(ROOT / p), _os.R_OK)]
            has_intent = bool(config_ro.get("intent", {}).get("purpose"))
            if missing or unreadable or not has_intent:
                errors = []
                if missing: errors.append(f"config-incomplete: {missing}")
                if unreadable: errors.append(f"unreadable-files: {unreadable}")
                if not has_intent: errors.append("intent-unanchored")
                msg = f"Onboard BLOCKED: {'; '.join(errors)} — fix config and retry"
                print(json.dumps({"status": "blocked", "errors": errors}) if args.json else msg)
                return 1

            # All BLOCKING gates pass — write OnboardRecord and confirm
            state_rw = load_state(config_ro)
            existing_records = state_rw.setdefault("onboard_records", [])
            confirmed_at = now()
            # Supersede prior record for same product
            for prior in existing_records:
                if prior.get("product_name") == product_name and not prior.get("superseded_at"):
                    prior["superseded_at"] = confirmed_at
            new_record = {
                "id": identifier("onb-"),
                "created_at": confirmed_at,
                "product_name": product_name,
                "confirmed_by": "operator",
                "confirmed_at": confirmed_at,
                "config_digest": product_digest(config_ro),
                "gates_passed": ["config-completeness", "product-files-readable", "intent-anchored"],
                "notes": args.note,
            }
            if not config_ro.get("capability_envelope"):
                new_record["capability_envelope_waived"] = True
            existing_records.append(new_record)
            # Write ONBOARD_COMPLETE checkpoint
            state_rw.setdefault("checkpoints", []).append({
                "id": identifier("checkpoint"),
                "at": confirmed_at,
                "kind": "ONBOARD_COMPLETE",
                "digest": product_digest(config_ro),
            })
            # Clear all onboard-* gaps
            for gap in state_rw.get("integrity_gaps", []):
                if gap.get("kind", "").startswith("onboard-") and gap.get("active", True):
                    gap["active"] = False
                    gap["cleared_at"] = confirmed_at
                    gap["cleared_by"] = "operator-onboard-confirm"
            # Set lifecycle to DORMANT
            state_rw["lifecycle_state"] = "DORMANT"
            state_rw.setdefault("evidence", []).append({
                "id": identifier("ev-"),
                "kind": "onboard-complete",
                "at": confirmed_at,
                "summary": f"Product onboarding confirmed by operator; product={product_name}; record={new_record['id']}",
            })
            save_state(config_ro, state_rw)
            result = {"status": "confirmed", "onboard_record_id": new_record["id"],
                      "product": product_name, "confirmed_at": confirmed_at, "lifecycle_state": "DORMANT"}
            print(json.dumps(result, indent=2) if args.json else f"Onboarding confirmed. Record: {new_record['id']}. Lifecycle: DORMANT. Autonomous cycles authorized.")
            return 0

    if args.command == "product":
        if args.action == "help":
            return _help_action("""URACE Product Guide
════════════════════
Register and manage multiple Products in a single URACE installation.

  urace product register <name> --state-path <path> [--product-files <f1> <f2>]
  urace product list               -- list normal registered products
  urace product improvements list  -- inspect automation controls
  urace product improvements enable|disable PRODUCT_ID -- control improvement work
  urace product status             -- show active product diagnostics
  urace product switch <name>      -- switch active product
  urace onboard confirm            -- confirm onboard after switch""", args)
        if args.action == "list":
            state_ro = load_state_for_read(config)
            registry = config.get("product_registry", [])
            active = config.get("active_product") or config.get("product", "")
            onboard_records = (state_ro or {}).get("onboard_records", []) if state_ro else []
            entries = []
            for entry in registry:
                name = entry.get("name", "")
                has_onboard = any(
                    r.get("product_name") == name and not r.get("superseded_at")
                    for r in onboard_records
                )
                entries.append({
                    "name": name,
                    "status": entry.get("status", "ACTIVE"),
                    "active": name == active,
                    "registered_at": entry.get("registered_at"),
                    "last_active_at": entry.get("last_active_at"),
                    "onboarded": has_onboard,
                })
            if args.json:
                print(json.dumps(entries, indent=2))
            else:
                if not entries:
                    print("No products registered. Use `urace product register <name>` to add one.")
                for e in entries:
                    marker = "* " if e["active"] else "  "
                    onb = "onboarded" if e["onboarded"] else "not onboarded"
                    print(f"{marker}{e['name']} [{e['status']}] {onb} registered={e['registered_at']}")
            return 0

        if args.action == "status":
            state_ro = load_state_for_read(config)
            active = config.get("active_product") or config.get("product", "")
            registry = config.get("product_registry", [])
            entry = next((e for e in registry if e.get("name") == active), None)
            onboard_records = (state_ro or {}).get("onboard_records", []) if state_ro else []
            active_record = next(
                (r for r in onboard_records if r.get("product_name") == active and not r.get("superseded_at")),
                None
            )
            lifecycle = (state_ro or {}).get("lifecycle_state", "UNKNOWN") if state_ro else "UNKNOWN"
            current_digest = product_digest(config)
            digest_match = active_record.get("config_digest") == current_digest if active_record else None
            result = {
                "active_product": active,
                "lifecycle_state": lifecycle,
                "registry_entry": entry,
                "onboard_record": {"id": active_record["id"], "confirmed_at": active_record.get("confirmed_at"),
                                   "config_digest_match": digest_match} if active_record else None,
            }
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Active product: {active}")
                print(f"Lifecycle:      {lifecycle}")
                if active_record:
                    match_str = "MATCH" if digest_match else "DIVERGED"
                    print(f"OnboardRecord:  {active_record['id']} (config_digest={match_str})")
                else:
                    print("OnboardRecord:  none (run `urace onboard confirm`)")
                if entry:
                    print(f"Registry:       state_path={entry.get('state_path')} status={entry.get('status', 'ACTIVE')}")
                else:
                    print("Registry:       not registered (using Config.state_path directly)")
            return 0

        if args.action == "switch":
            if not args.name:
                parser.error("product switch requires a <name>")
            target = args.name
            registry = config.get("product_registry", [])
            target_entry = next((e for e in registry if e.get("name") == target), None)
            if not target_entry or target_entry.get("status", "ACTIVE") != "ACTIVE":
                _emit_result = {"status": "error", "error": f"product '{target}' not found in registry or not ACTIVE"}
                print(json.dumps(_emit_result, indent=2) if args.json else f"error: product '{target}' not in registry or not ACTIVE")
                return 1
            current = config.get("active_product") or config.get("product", "")
            if current == target:
                result = {"status": "no-op", "message": f"product '{target}' is already active"}
                print(json.dumps(result, indent=2) if args.json else f"'{target}' is already the active product")
                return 0
            # Step 2: write SwitchRecord to current state
            try:
                state_rw = load_state(config)
            except RuntimeError:
                state_rw = None
            switch_id = identifier("swrec-")
            switched_at = now()
            switch_record = {
                "id": switch_id, "from_product": current, "to_product": target,
                "switched_at": switched_at, "switched_by": "operator",
                "reason": args.reason,
            }
            if state_rw is not None:
                state_rw.setdefault("switch_records", []).append(switch_record)
                target_entry["last_active_at"] = switched_at
                save_state(config, state_rw)
            # Step 3: update Config.active_product and persist
            config["active_product"] = target
            save_config(config)
            result = {"status": "switched", "from": current, "to": target, "switch_record_id": switch_id,
                      "message": "run `urace onboard confirm` to authorize autonomous cycles for the new product"}
            print(json.dumps(result, indent=2) if args.json else
                  f"Switched: {current} → {target}\nSwitchRecord: {switch_id}\nNext: run `urace onboard confirm`")
            return 0

        if args.action == "register":
            if not args.name:
                parser.error("product register requires a <name>")
            github_repo = getattr(args, 'product_github', None)
            clone_to = getattr(args, 'product_clone_to', None)
            if not github_repo and not args.product_state_path:
                parser.error("product register requires --state-path or --github OWNER/REPO")
            if github_repo and (github_repo.count('/') != 1 or github_repo.startswith('/')):
                result = {"status": "error", "error": "invalid --github format; use 'owner/repo'"}
                print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                return 1
            name = args.name
            registry = config.setdefault("product_registry", [])
            if any(e.get("name") == name for e in registry):
                result = {"status": "error", "error": f"product '{name}' already in registry"}
                print(json.dumps(result, indent=2) if args.json else f"error: '{name}' already registered")
                return 1
            # Clone GitHub repo if --clone-to provided
            cloned_path = None
            if github_repo and clone_to:
                from .. import portfolio_github as _pgh
                _rc, _out, _err = _pgh.clone_repo(github_repo, clone_to)
                if _rc != 0:
                    result = {"status": "error", "error": f"git clone failed: {_err or _out}"}
                    print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                    return 1
                cloned_path = str(Path(clone_to).resolve())
            # Derive entry_state_path
            if args.product_state_path:
                entry_state_path = args.product_state_path
            elif cloned_path:
                entry_state_path = str(Path(cloned_path) / 'urace_state.json')
            else:
                entry_state_path = None
            # §62p State Isolation Contract: duplicate state_path MUST be rejected
            if entry_state_path and any(e.get("state_path") == entry_state_path for e in registry):
                try:
                    _dup_state = load_state(config)
                except RuntimeError:
                    _dup_state = None
                if _dup_state is not None:
                    _emit_gap(_dup_state, "product-registry-duplicate-state-path", "WARNING",
                              f"state_path '{entry_state_path}' is already used by another product entry")
                    save_state(config, _dup_state)
                result = {"status": "error", "error": f"state_path '{entry_state_path}' already in use"}
                print(json.dumps(result, indent=2) if args.json else "error: state_path already used by another product")
                return 1
            entry = {
                "id": identifier("prod-"),
                "name": name,
                "state_path": entry_state_path,
                "product_files": args.product_files,
                "intent_purpose": args.intent_purpose,
                "registered_at": now(),
                "last_active_at": None,
                "status": "ACTIVE",
                "product_type": getattr(args, "product_type", "software") or "software",
            }
            if github_repo:
                entry["kind"] = "github"
                entry["github_repo"] = github_repo
                if cloned_path:
                    entry["clone_path"] = cloned_path
            registry.append(entry)
            save_config(config)
            result = {"status": "registered", "name": name, "id": entry["id"]}
            if github_repo:
                result["github_repo"] = github_repo
                if cloned_path:
                    result["clone_path"] = cloned_path
            print(json.dumps(result, indent=2) if args.json else
                  f"Registered product '{name}' (id={entry['id']})" + (f" github={github_repo}" if github_repo else ""))
            return 0

        if args.action == "git":
            from .. import portfolio_github as _pgh
            name = args.name
            git_args = list(getattr(args, 'git_args', []))
            if git_args and git_args[0] == '--':
                git_args = git_args[1:]
            # Strip URACE output flags that REMAINDER may have captured before git args
            _urace_flags = {'--json', '--format'}
            _clean = []
            _i = 0
            while _i < len(git_args):
                if git_args[_i] in _urace_flags:
                    if git_args[_i] == '--format' and _i + 1 < len(git_args):
                        _i += 2
                    else:
                        if git_args[_i] == '--json':
                            args.json = True
                        _i += 1
                else:
                    _clean.append(git_args[_i])
                    _i += 1
            git_args = _clean
            registry = config.get("product_registry", [])
            entry = next((e for e in registry if e.get("name") == name), None)
            if entry is None:
                result = {"status": "error", "error": f"product '{name}' not found in registry"}
                print(json.dumps(result, indent=2) if args.json else f"error: '{name}' not found in registry")
                return 1
            if entry.get("kind") != "github":
                result = {"status": "error", "error": f"'product git' requires a GitHub product; '{name}' is kind={entry.get('kind', 'local')}"}
                print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                return 1
            github_repo = entry.get("github_repo", "")
            clone_path = entry.get("clone_path")
            # Special subcommand: clone
            if git_args and git_args[0] == "clone":
                target = git_args[1] if len(git_args) > 1 else clone_path
                if not target:
                    result = {"status": "error", "error": "clone requires a path argument or register with --clone-to"}
                    print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                    return 1
                if Path(target).is_dir() and list(Path(target).iterdir()):
                    result = {"status": "error", "error": f"target path '{target}' already exists and is not empty"}
                    print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                    return 1
                _rc, _out, _err = _pgh.clone_repo(github_repo, target)
                if _rc != 0:
                    result = {"status": "error", "error": f"git clone failed: {_err or _out}"}
                    print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                    return _rc
                resolved = str(Path(target).resolve())
                entry["clone_path"] = resolved
                if not entry.get("state_path"):
                    entry["state_path"] = str(Path(resolved) / 'urace_state.json')
                save_config(config)
                result = {"status": "cloned", "product": name, "clone_path": resolved, "github_repo": github_repo}
                print(json.dumps(result, indent=2) if args.json else f"Cloned {github_repo} → {resolved}")
                return 0
            # All other subcommands require an existing clone_path
            if not clone_path:
                result = {"status": "error", "error": f"'{name}' has no clone_path; run: urace product git {name} clone <path>"}
                print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                return 1
            if not Path(clone_path).is_dir():
                result = {"status": "error", "error": f"clone_path '{clone_path}' not found; run: urace product git {name} clone"}
                print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                return 1
            err_msg = _pgh.validate_subcommand(git_args)
            if err_msg:
                result = {"status": "error", "error": err_msg}
                print(json.dumps(result, indent=2) if args.json else f"error: {result['error']}")
                return 1
            rc, out, git_stderr = _pgh.run_git(clone_path, git_args)
            if args.json:
                result = {"status": "ok" if rc == 0 else "error", "exit_code": rc, "stdout": out, "stderr": git_stderr, "product": name, "clone_path": clone_path}
                print(json.dumps(result, indent=2))
            else:
                if out:
                    print(out)
                if git_stderr:
                    print(git_stderr, file=sys.stderr)
            return rc

        if args.action == "remove":
            if not args.name:
                parser.error("product remove requires a <name>")
            name = args.name
            active = config.get("active_product") or config.get("product")
            if name == active:
                try:
                    _state_rw = load_state(config)
                except RuntimeError:
                    _state_rw = None
                if _state_rw is not None:
                    _emit_gap(_state_rw, "product-remove-active-blocked", "BLOCKING",
                              f"Cannot remove active product '{name}'; switch to a different product first")
                    save_state(config, _state_rw)
                result = {"status": "error", "error": f"'{name}' is the active product; switch first"}
                print(json.dumps(result, indent=2) if args.json else f"error: '{name}' is the active product; switch first")
                return 1
            registry = config.get("product_registry", [])
            entry = next((e for e in registry if e.get("name") == name), None)
            if entry is None:
                result = {"status": "error", "error": f"product '{name}' not found in registry"}
                print(json.dumps(result, indent=2) if args.json else f"error: '{name}' not found in registry")
                return 1
            if not args.force and not args.json:
                confirm = input(f"Remove product '{name}' from registry? State file is NOT deleted. [y/N] ").strip().lower()
                if confirm != "y":
                    print("Aborted.")
                    return 0
            config["product_registry"] = [e for e in registry if e.get("name") != name]
            save_config(config)
            result = {"status": "removed", "name": name}
            print(json.dumps(result, indent=2) if args.json else f"Removed product '{name}' from registry")
            return 0

        if args.action == "deactivate":
            if not args.name:
                parser.error("product deactivate requires a <name>")
            name = args.name
            active = config.get("active_product") or config.get("product")
            if name == active:
                try:
                    _state_rw = load_state(config)
                except RuntimeError:
                    _state_rw = None
                if _state_rw is not None:
                    _emit_gap(_state_rw, "product-deactivate-active-blocked", "BLOCKING",
                              f"Cannot deactivate active product '{name}'; switch to a different product first")
                    save_state(config, _state_rw)
                result = {"status": "error", "error": f"'{name}' is the active product; switch first"}
                print(json.dumps(result, indent=2) if args.json else f"error: '{name}' is the active product; switch first")
                return 1
            registry = config.get("product_registry", [])
            entry = next((e for e in registry if e.get("name") == name), None)
            if entry is None:
                result = {"status": "error", "error": f"product '{name}' not found in registry"}
                print(json.dumps(result, indent=2) if args.json else f"error: '{name}' not found in registry")
                return 1
            entry["status"] = "INACTIVE"
            save_config(config)
            result = {"status": "deactivated", "name": name}
            print(json.dumps(result, indent=2) if args.json else f"Product '{name}' deactivated (status=INACTIVE)")
            return 0

        if args.action == "activate":
            if not args.name:
                parser.error("product activate requires a <name>")
            name = args.name
            registry = config.get("product_registry", [])
            entry = next((e for e in registry if e.get("name") == name), None)
            if entry is None:
                result = {"status": "error", "error": f"product '{name}' not found in registry"}
                print(json.dumps(result, indent=2) if args.json else f"error: '{name}' not found in registry")
                return 1
            entry["status"] = "ACTIVE"
            save_config(config)
            result = {"status": "activated", "name": name}
            print(json.dumps(result, indent=2) if args.json else f"Product '{name}' activated (status=ACTIVE)")
            return 0

    if args.command == "fleet":
        if args.action == "help":
            return _help_action("""URACE Fleet Guide
══════════════════
Run all registered Products in parallel.

  urace fleet run        -- launch all products in parallel
  urace fleet status     -- inspect current fleet state
  urace fleet stop <name>-- stop a specific product
  urace fleet broadcast  -- send a signal to all fleet members""", args)
        fleet_cfg = config.get("fleet", {})
        members = fleet_cfg.get("members", [])
        registry = config.get("product_registry", [])

        if args.action == "status":
            results = []
            for name in members:
                entry = next((e for e in registry if e.get("name") == name), None)
                member_config = dict(config)
                member_config["active_product"] = name
                try:
                    member_state = load_state_for_read(member_config)
                    lc = (member_state or {}).get("lifecycle_state", "UNKNOWN")
                    last_cycle = (member_state or {}).get("last_cycle")
                    onboard_records = (member_state or {}).get("onboard_records", [])
                    onboarded = any(r.get("product_name") == name and not r.get("superseded_at") for r in onboard_records)
                except Exception:
                    lc, last_cycle, onboarded = "UNREADABLE", None, False
                results.append({"product": name, "lifecycle_state": lc, "last_cycle": last_cycle, "onboarded": onboarded, "state_path": entry.get("state_path") if entry else None})
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                for r in results:
                    onb = "onboarded" if r["onboarded"] else "not onboarded"
                    print(f"  {r['product']:30s} [{r['lifecycle_state']:20s}] {onb}")
            return 0

        if args.action == "broadcast":
            min_conf = fleet_cfg.get("broadcast_min_confidence", 0.75)
            exclusion = {"bootstrap", "onboard-complete", "onboard-policy-defaulted"}
            broadcast_count = 0
            member_evidence: dict[str, list] = {}
            for name in members:
                member_config = dict(config)
                member_config["active_product"] = name
                try:
                    ms = load_state_for_read(member_config)
                    ev_list = (ms or {}).get("evidence", [])
                    qualifying = [e for e in ev_list[-20:] if e.get("kind") not in exclusion and float(e.get("confidence_score", 1.0)) >= min_conf]
                    member_evidence[name] = qualifying
                except Exception:
                    member_evidence[name] = []
            for source_name, ev_list in member_evidence.items():
                for target_name in members:
                    if target_name == source_name:
                        continue
                    target_config = dict(config)
                    target_config["active_product"] = target_name
                    inbox_dir = input_directory(target_config)
                    try:
                        inbox_dir.mkdir(parents=True, exist_ok=True)
                    except OSError:
                        continue
                    for ev in ev_list:
                        broadcast_input = {
                            "id": identifier("inp-"),
                            "kind": "authoritative-context",
                            "source": "fleet-broadcast",
                            "from_product": source_name,
                            "content": ev.get("summary", ""),
                            "evidence_id": ev.get("id"),
                            "confidence_score": float(ev.get("confidence_score", 1.0)),
                            "at": now(),
                        }
                        (inbox_dir / f"{broadcast_input['id']}.json").write_text(
                            json.dumps(broadcast_input, indent=2), encoding="utf-8"
                        )
                        broadcast_count += 1
            result = {"broadcast_count": broadcast_count, "members": list(member_evidence.keys())}
            print(json.dumps(result, indent=2) if args.json else f"Broadcast {broadcast_count} signals across {len(members)} members")
            return 0

        if args.action == "run":
            if not members:
                print(json.dumps({"status": "error", "error": "Config.fleet.members is empty"}) if args.json else "error: Config.fleet.members is empty — register products first")
                return 1
            seen_paths: set[str] = set()
            for name in members:
                entry = next((e for e in registry if e.get("name") == name), None)
                if not entry:
                    print(f"error: fleet member '{name}' not in product_registry" if not args.json else json.dumps({"error": f"member {name} not in registry"}))
                    return 1
                sp = entry.get("state_path", "")
                if sp in seen_paths:
                    print(f"error: duplicate state_path '{sp}' — fleet-duplicate-state-path" if not args.json else json.dumps({"error": f"duplicate state_path {sp}"}))
                    return 1
                seen_paths.add(sp)
            if args.dry_run:
                result = {"would_start": members, "signal_broadcast": fleet_cfg.get("signal_broadcast", False)}
                print(json.dumps(result, indent=2) if args.json else f"Would start: {', '.join(members)}")
                return 0
            import subprocess as _sp
            import signal as _signal
            import time as _time
            procs: dict[str, "_sp.Popen[bytes]"] = {}
            crash_counts: dict[str, int] = {}

            def _start_member(mname: str) -> "_sp.Popen[bytes]":
                member_env = dict(os.environ)
                member_env["URACE_ACTIVE_PRODUCT"] = mname
                cmd = [sys.executable, sys.argv[0], "auto", "--quiet"]
                kwargs: dict = {} if args.verbose else {"stdout": _sp.DEVNULL, "stderr": _sp.DEVNULL}
                return _sp.Popen(cmd, env=member_env, **kwargs)

            for mname in members:
                procs[mname] = _start_member(mname)
                crash_counts[mname] = 0
                if not args.json:
                    print(f"started: {mname} (pid={procs[mname].pid})", flush=True)
            if not args.json:
                print(f"Fleet running ({len(procs)} members). Ctrl-C to stop.")

            def _stop_all(signum=None, frame=None):
                for p in procs.values():
                    try:
                        p.terminate()
                    except Exception:
                        pass

            _signal.signal(_signal.SIGTERM, _stop_all)
            try:
                while procs:
                    _time.sleep(5)
                    for mname in list(procs.keys()):
                        rc = procs[mname].poll()
                        if rc is not None and rc != 0:
                            crash_counts[mname] = crash_counts.get(mname, 0) + 1
                            if crash_counts[mname] <= 3:
                                _time.sleep(30)
                                procs[mname] = _start_member(mname)
                            else:
                                del procs[mname]
                                if not args.json:
                                    print(f"member {mname}: ERROR after 3 crashes — manual restart required", flush=True)
                        elif rc == 0:
                            del procs[mname]
            except KeyboardInterrupt:
                _stop_all()
            return 0

        if args.action == "stop":
            target_members = [args.name] if args.name else members
            for name in target_members:
                target_config = dict(config)
                target_config["active_product"] = name
                inbox_dir = input_directory(target_config)
                inbox_dir.mkdir(parents=True, exist_ok=True)
                stop_input = {"id": identifier("inp-"), "kind": "lifecycle-pause", "source": "fleet-stop", "at": now()}
                (inbox_dir / f"{stop_input['id']}.json").write_text(json.dumps(stop_input), encoding="utf-8")
            result = {"stopped": target_members}
            print(json.dumps(result, indent=2) if args.json else f"Stop signal sent to: {', '.join(target_members)}")
            return 0

        if args.action == "capacity":
            executor_settings = config.get("executor", {})
            pool_state = config.get("executor_pool_state", {})
            per_member = []
            for mname in members:
                entry = next((e for e in registry if e.get("name") == mname), None)
                member_exec = dict(executor_settings)
                if entry and entry.get("executor"):
                    member_exec.update(entry["executor"])
                avail = intelligent_executor.pool_availability(member_exec, pool_state, "execution")
                providers = avail.get("providers", [])
                available_count = sum(1 for p in providers if p.get("available"))
                calls_remaining = sum(
                    max(0, (p.get("limit_24h") or 999) - (p.get("calls_24h") or 0))
                    for p in providers if p.get("available")
                )
                per_member.append({
                    "name": mname,
                    "available": avail.get("available"),
                    "selected_provider": avail.get("selected_provider"),
                    "provider_count": len(providers),
                    "available_providers": available_count,
                    "calls_remaining_24h": calls_remaining,
                    "bottleneck": not avail.get("available"),
                })
            fleet_available = sum(1 for m in per_member if m["available"])
            total_calls = sum(m["calls_remaining_24h"] for m in per_member)
            parallel_capacity = fleet_available
            result = {
                "status": "ok",
                "fleet_size": len(members),
                "fleet_available": fleet_available,
                "parallel_capacity": parallel_capacity,
                "total_calls_remaining_24h": total_calls,
                "bottleneck_members": [m["name"] for m in per_member if m["bottleneck"]],
                "members": per_member,
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.action == "config-push":
            key = getattr(args, 'config_key', None)
            value_raw = getattr(args, 'config_value', None)
            if not key or value_raw is None:
                print(json.dumps({"status": "error", "error": "--config-key and --config-value are required"}))
                return 1
            try:
                value = json.loads(value_raw)
            except Exception:
                value = value_raw
            import json as _jm
            _base = _jm.loads(CONFIG_PATH.read_text())
            parts = key.split('.')
            node = _base
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
            CONFIG_PATH.write_text(_jm.dumps(_base, indent=2, sort_keys=True) + "\n")
            result = {"status": "ok", "key": key, "value": value, "affected_members": members}
            print(json.dumps(result, indent=2) if args.json else f"Config pushed: {key}={value!r} to {len(members)} fleet members")
            return 0

    if args.command == "data":
        if args.data_action in {"list", "inspect", "status"} or (
            args.data_action == "credential" and getattr(args, "credential_action", None) == "inspect"
        ):
            state = load_state_for_read(config)
            if state is None:
                print("URACE is not initialized; run `urace init`", file=sys.stderr)
                return 1
            return _handle_data_command(args, state, config)
        with state_lock(state_path(config)):
            state = load_state(config)
            before=json.dumps(state,sort_keys=True)
            result = _handle_data_command(args, state, config)
            if json.dumps(state,sort_keys=True)!=before:save_state(config, state)
        return result

    if args.command == "trace":
        if args.action == "help":
            return _help_action("""URACE Trace Guide
══════════════════
Query the lifecycle audit trail.

  urace trace list                          -- list trace records
  urace trace list --kind CYCLE             -- filter by kind
  urace trace list --since <ISO> --until <ISO>
  urace trace inspect <trace_id>            -- inspect a specific record""", args)
        state_ro = load_state_for_read(config)
        records = list(reversed((state_ro or {}).get("trace_records", [])))  # most recent first

        if args.action == "inspect":
            if not args.trace_id:
                parser.error("trace inspect requires a <trace-id>")
            rec = next((r for r in records if r.get("id") == args.trace_id), None)
            if not rec:
                print(json.dumps({"error": "not found"}) if args.json else f"trace {args.trace_id}: not found")
                return 1
            print(json.dumps(rec, indent=2) if args.json else "\n".join(f"  {k}: {v}" for k, v in rec.items()))
            return 0

        # list action — apply InspectionContract filters
        if args.kind:
            records = [r for r in records if r.get("kind") == args.kind]
        if args.cycle_id:
            records = [r for r in records if r.get("cycle_id") == args.cycle_id]
        return _inspect_list(records, args,
            fmt=lambda r: f"{r.get('id')}: [{r.get('kind')}] {r.get('at','')} — {r.get('summary','')}",
            empty_msg="No trace records.")

    if args.command == "schema":
        if args.action == "help":
            return _help_action("""URACE Schema Guide
═══════════════════
Inspect the output schema registry (OutputSchemaRegistry §62l).

  urace schema list                         -- list all registered --json output schemas
  urace schema inspect <command>            -- inspect the schema for a specific command
  urace schema export                       -- export all schema registries
  urace schema export --target output-schemas  -- export only output schemas
  urace schema export --target bundles      -- export only feature bundles

Example:
  urace schema inspect "check"     -- show the stable fields for urace check --json""", args)
        if args.action == "list":
            schemas = [{"command": cmd, "schema_version": info["version"], "stable_since": info["stable_since"]}
                       for cmd, info in sorted(OUTPUT_SCHEMA_REGISTRY.items())]
            if args.json:
                print(json.dumps({"schema_version": "1.0", "schemas": schemas}, indent=2, sort_keys=True))
            else:
                for s in schemas:
                    print(f"{s['command']:25s}  v{s['schema_version']}  (since {s['stable_since']})")
            return 0

        elif args.action == "inspect":
            cmd_name = " ".join(args.schema_command)
            info = OUTPUT_SCHEMA_REGISTRY.get(cmd_name)
            if not info:
                print(f"No registered schema for command: {cmd_name}", file=sys.stderr)
                return 1
            payload = {"schema_version": "1.0", "command": cmd_name,
                       "output_schema_version": info["version"],
                       "stable_since": info["stable_since"],
                       "fields": info["fields"]}
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(f"Command:        {cmd_name}")
                print(f"Schema version: {info['version']}")
                print(f"Stable since:   {info['stable_since']}")
                print(f"Fields:         {', '.join(info['fields'])}")
            return 0

        elif args.action == "export":
            from urace import schema_export as _sch_exp
            target = getattr(args, "target", "all")
            if target == "output-schemas":
                payload = _sch_exp.export_output_schemas()
            elif target == "bundles":
                payload = _sch_exp.export_feature_bundles()
            else:
                payload = _sch_exp.export_all()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                if target in ("output-schemas", "all"):
                    schemas = payload.get("output_schemas", payload.get("schemas", []))
                    print(f"Output schemas ({len(schemas)}):")
                    for s in schemas:
                        print(f"  {s['command']:25s}  v{s['schema_version']}  (since {s['stable_since']})")
                if target in ("bundles", "all"):
                    bundles = payload.get("feature_bundles", payload.get("bundles", []))
                    print(f"Feature bundles ({len(bundles)}):")
                    for b in bundles:
                        print(f"  {b['name']:30s}  {b['spec_version']:6s}  [{b['source']}]")
            return 0

    if args.command == "feedback":
        if args.action == "help":
            return _help_action("""URACE Feedback Guide
═════════════════════
Submit and inspect outcome feedback to close the learning loop.

  urace feedback submit <obj-id> --signal POSITIVE|NEGATIVE|NEUTRAL
  urace feedback submit <dec-id> --signal NEGATIVE --detail "reason"
  urace feedback list              -- list all feedback records
  urace feedback list --signal NEGATIVE --target <id>""", args)
        if args.action == "list":
            state_ro = load_state_for_read(config)
            fbk_records = list(reversed((state_ro or {}).get("outcome_feedback_records", [])))
            # Apply domain filters (OutcomeFeedbackContract §62l clause 5)
            if getattr(args, "filter_target", None):
                fbk_records = [r for r in fbk_records if r.get("target_id") == args.filter_target]
            if getattr(args, "signal", None):
                fbk_records = [r for r in fbk_records if r.get("signal") == args.signal]
            return _inspect_list(fbk_records, args,
                fmt=lambda r: f"{r.get('id')}: [{r.get('signal','?')}] target={r.get('target_kind','?')}:{r.get('target_id','?')} — {r.get('detail','')}",
                empty_msg="No feedback records.",
                envelope=True,
                time_field=None)

        elif args.action == "submit":
            if not args.target_id:
                print("feedback submit requires a <target_id>", file=sys.stderr)
                return 1
            # --input-json: read fields from JSON file/stdin
            if getattr(args, "input_json", None):
                import sys as _sys
                src = args.input_json
                try:
                    raw = (_sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8"))
                    _params = json.loads(raw)
                except Exception as exc:
                    result = {"status": "error", "error": f"--input-json read failed: {exc}"}
                    print(json.dumps(result, indent=2) if args.json else result["error"], file=_sys.stderr)
                    return 1
                if "signal" not in _params:
                    result = {"status": "error", "error": "--input-json must include 'signal' field"}
                    print(json.dumps(result, indent=2) if args.json else result["error"], file=_sys.stderr)
                    return 1
                args.signal = _params["signal"]
                if "detail" in _params:
                    args.detail = _params["detail"]
                if "evidence" in _params:
                    args.evidence_id = _params["evidence"]
            # Prefix validation (OutcomeFeedbackContract §62l clause 1)
            if not (args.target_id.startswith("obj-") or args.target_id.startswith("dec-")):
                print(f"Invalid target_id '{args.target_id}': must start with obj- or dec-", file=sys.stderr)
                return 1
            fbk_signal = (args.signal or "NEUTRAL").upper()
            state = load_state(config)
            target_kind = "OBJECTIVE" if args.target_id.startswith("obj-") else "DECISION"
            rec: dict[str, Any] = {
                "id": identifier("ofbk-"),
                "at": now(),
                "recorded_by": "operator",
                "event_kind": "OUTCOME_FEEDBACK",
                "target_id": args.target_id,
                "target_kind": target_kind,
                "signal": fbk_signal,
            }
            if getattr(args, "detail", None):
                rec["detail"] = args.detail
            if getattr(args, "evidence_id", None):
                rec["evidence_id"] = args.evidence_id
            rec["processed"] = False
            state.setdefault("outcome_feedback_records", []).append(rec)
            _emit_trace(state, "OPERATION", f"feedback {rec['id']} submitted: {fbk_signal} for {args.target_id}")
            save_state(config, state)
            if args.json:
                print(json.dumps({"schema_version": "1.0", "id": rec["id"], "signal": fbk_signal}, indent=2))
            else:
                print(f"Feedback {rec['id']} recorded: {fbk_signal} for {target_kind} {args.target_id}")
            return 0

    if args.command == "api":
        if args.action == "protocols":
            from ..protocol_catalog import describe
            print(json.dumps(describe(),indent=2));return 0
        if args.action == "help":
            return _help_action("""URACE External Interface Guide (EIP §62w)
══════════════════════════════════════════
Machine interface for external tools and automation systems.

Output surface: API calls wrap every installed command in a stable JSON envelope; streaming uses NDJSON.

Input surface:
  urace api commands  -- discover the complete installed grammar
  urace api call --command <cmd> [--params <json>] [--stream]
  urace api call --argv <JSON-string-array> [--stream]
  urace api batch --input-json <path|-> [--continue-on-error] [--json]

Examples:
  urace api call --command "product switch" --params '{"name":"ProductB"}' --json
  urace api batch --input-json batch.json --json
  echo '[{"command":"check","params":{}}]' | urace api batch --input-json - --json

Machine feedback:
  urace feedback submit <id> --input-json params.json --json
  (params.json: {"signal":"POSITIVE","detail":"optional"})""", args)

        if args.action == "commands":
            print(json.dumps(api_interface.metadata(parser),indent=2));return 0
        if args.action == "serve":
            if args.transport == "a2a":
                from ..a2a_server import serve as serve_a2a
                return serve_a2a(parser, policy_path=args.policy, port=args.port, token_env=args.token_env)
            from ..mcp_server import serve
            return serve(parser, policy_path=args.policy)
        if args.action == "call":
            if not args.api_command and not args.argv:
                print(json.dumps({"schema_version":"1.0","status":"error","exit_code":1,"error":"api call requires --command or --argv","output":None}));return 1
            try:
                params=json.loads(args.params) if args.params else None
                argv=json.loads(args.argv) if args.argv else None
                result=api_interface.execute(parser,main,args.api_command,params,argv,stream=args.stream)
            except (ValueError,TypeError) as error:
                result={"schema_version":"1.0","status":"error","exit_code":2,"output":None,"error":str(error)}
            print(json.dumps(result));return result['exit_code']

        if args.action == "watch":
            config = load_config()
            state = load_state_for_read(config)
            records = (state or {}).get("trace_records", [])
            kinds_filter = [k.strip() for k in args.kinds.split(",") if k.strip()] if args.kinds else []
            since_ts = args.since or ""
            filtered = [r for r in records if (not kinds_filter or r.get("kind") in kinds_filter) and r.get("at", "") >= since_ts]
            filtered.sort(key=lambda r: r.get("at", ""))
            for r in filtered:
                print(json.dumps(r))
            if args.follow:
                seen_ids = {r.get("id") for r in filtered}
                while True:
                    time.sleep(2)
                    st2 = load_state_for_read(config)
                    for r in (st2 or {}).get("trace_records", []):
                        if r.get("id") not in seen_ids:
                            if not kinds_filter or r.get("kind") in kinds_filter:
                                print(json.dumps(r), flush=True)
                                seen_ids.add(r.get("id"))
            return 0

        if args.action == "version":
            config = load_config()
            spec_ver = config.get("spec_version", "unknown")
            out = {"spec_version": spec_ver, "api_version": "1", "schema_version": "1"}
            if args.json:
                print(json.dumps(out, indent=2))
            else:
                print(f"spec_version: {spec_ver}\napi_version: 1")
            return 0

        if args.action == "batch":
            try:
                if not args.input_json:
                    print(json.dumps({"schema_version":"1.0","status":"error","exit_code":1,"error":"api batch requires --input-json"}));return 1
                if args.input_json=='-':raw=sys.stdin.read()
                else:raw=Path(args.input_json).read_text()
                entries=json.loads(raw)
                if not isinstance(entries,list):raise ValueError("batch input must be an array")
            except (ValueError,OSError) as error:
                print(json.dumps({"schema_version":"1.0","status":"error","exit_code":2,"error":str(error)}));return 2
            results=[];final_rc=0
            for entry in entries:
                if not isinstance(entry,dict):result={"schema_version":"1.0","status":"error","exit_code":2,"output":None,"error":"batch entry must be an object"}
                elif set(entry)-{'command','params','argv'}:result={"schema_version":"1.0","status":"error","exit_code":2,"output":None,"error":"unknown batch entry keys"}
                else:result=api_interface.execute(parser,main,entry.get('command'),entry.get('params'),entry.get('argv'),stream=args.stream)
                results.append(result)
                if result['exit_code']:
                    final_rc=result['exit_code']
                    if not args.continue_on_error:break
            print(json.dumps({"schema_version":"1.0","status":"ok" if not final_rc else "error","results":results,"exit_code":final_rc}));return final_rc

    if args.command == "resource":
        if args.action == "help":
            return _help_action("""URACE Resource Budget Guide
═══════════════════════════════

URACE tracks cost and ROI per product. Configure product_budget in urace/config.json:

  "product_budget": {
    "max_cost": 10.0,           -- max currency cost per period
    "max_executor_calls": 100,  -- max Executor calls per period
    "roi_floor": 0.5,           -- warn if ROI falls below this
    "cost_per_executor_call": 0.01,
    "hourly_rate": 0.0,
    "quality_weight": 0.4,      -- alpha weight for quality improvement
    "capability_weight": 0.4,   -- beta  weight for capability progress
    "metrics_weight": 0.2       -- gamma weight for metrics improvement
  }

ROI verification:
  Structural quality/capability counts and external observations are diagnostic.
  ROI is unknown until independently verified real-user benefit and observed costs exist.
  ROI = (verified gross benefit - observed total cost) / observed total cost.
  Estimates remain labeled and never establish positive net user value.

Commands:
  urace resource status   -- current period utilization and ROI
  urace resource report   -- historical ROI snapshots
  urace resource help     -- this guide""", args)
        config_ro = load_config()
        state_data = load_state(config_ro)
        if args.action == "status":
            ledger = state_data.get("resource_ledger", [])
            snapshots = state_data.get("roi_snapshots", [])
            period_start = snapshots[-1].get("period_end", state_data.get("created_at", "unknown")) if snapshots else state_data.get("created_at", "unknown")
            current = ledger[-1] if ledger else {}
            gaps = [g for g in state_data.get("integrity_gaps", []) if "budget" in g.get("kind", "") or "roi" in g.get("kind", "") or "efficiency" in g.get("kind", "")]
            result = {
                "schema_version": "1.0",
                "period_start": period_start,
                "executor_calls": current.get("executor_calls", 0),
                "time_hours": current.get("time_hours", 0),
                "total_cost": current.get("total_cost", 0),
                "roi": current.get("roi"), "cost_basis": current.get("cost_basis", "unknown"), "roi_basis": current.get("roi_basis", "UNVERIFIED"),
                "gaps": [{"kind": g.get("kind"), "severity": g.get("severity")} for g in gaps],
            }
            if getattr(args, "json", False):
                print(json.dumps(result, indent=2))
            else:
                roi_str = f"{result['roi']:.4f}" if result["roi"] is not None else "UNVERIFIED (outcome or cost evidence incomplete)"
                print(f"Period start:     {result['period_start']}")
                print(f"Executor calls:   {result['executor_calls']}")
                print(f"Time hours:       {result['time_hours']:.2f}")
                print(f"Total cost:       {result['total_cost']:.4f}")
                print(f"ROI:              {roi_str}")
                if result["gaps"]:
                    print("Resource gaps:")
                    for g in result["gaps"]:
                        print(f"  [{g['severity']}] {g['kind']}")
            return 0
        if args.action == "report":
            snapshots = state_data.get("roi_snapshots", [])
            snapshots_sorted = sorted(snapshots, key=lambda x: x.get("at", ""), reverse=True)
            if getattr(args, "since", None):
                snapshots_sorted = [s for s in snapshots_sorted if s.get("at", "") >= args.since]
            if getattr(args, "until", None):
                snapshots_sorted = [s for s in snapshots_sorted if s.get("at", "") <= args.until]
            total = len(snapshots_sorted)
            page = snapshots_sorted[args.offset:args.offset + args.limit]
            if getattr(args, "json", False):
                print(json.dumps({"schema_version": "1.0", "snapshots": page, "total": total}, indent=2))
            else:
                if not page:
                    print("No ROI snapshots yet.")
                for s in page:
                    roi_str = f"{s['computed_roi']:.4f}" if s.get("computed_roi") is not None else "N/A"
                    flag = " [BELOW FLOOR]" if s.get("below_floor") else ""
                    print(f"{s.get('period_start','?')} to {s.get('period_end','?')}  ROI={roi_str}  cost={s.get('total_cost',0):.4f}{flag}")
            return 0

    if args.command == "derive":
        # --source runtime (default): full CONSTRUCT_CATALOG covering all runtime-implemented kinds
        # --source spec: restrict to PATTERN_CATALOG for backward compat with legacy spec-only derive
        _derive_src = getattr(args, 'derive_source', 'runtime')
        if _derive_src == 'spec':
            catalog = pattern_catalog_module.PATTERN_CATALOG
        else:
            catalog = {**pattern_catalog_module.PATTERN_CATALOG, **pattern_catalog_module.CONSTRUCT_CATALOG}
        intent_text: str = getattr(args, "intent", "") or ""
        if intent_text:
            try:
                _validate_freeform_query(intent_text, max_bytes=4096)
            except ValueError as _ierr:
                parser.error(str(_ierr))

        # r62: --list-bundles
        if getattr(args, "list_bundles", False):
            if getattr(args, "json", False):
                print(json.dumps({"bundles": {k: {"construct_ids": v} for k, v in BUILTIN_BUNDLES.items()}}, indent=2, sort_keys=True))
            else:
                print("Built-in FeatureBundles (use with --bundle <name>):")
                for bname, bids in BUILTIN_BUNDLES.items():
                    print(f"  {bname:30s}  constructs: {', '.join(bids)}")
            return 0

        from .. import derived_artifacts
        _explicit_verify = getattr(args, "verify", False)
        _expected = getattr(args, "derive_expected_hash", None)
        if _explicit_verify or _expected:
            _verify_cfg=load_config();_verify_state=load_state_for_read(_verify_cfg)
            if _verify_state is None:
                print(json.dumps({'status':'error','error':'No initialized state; saved artifacts required'}) if args.json else 'ERROR: no initialized state found',file=sys.stdout if args.json else sys.stderr);return 1
            _refs=derived_artifacts.saved_refs(_verify_state)
            if _expected:_refs=[r for r in _refs if str(r.get('content_hash','')).startswith(_expected.lower().strip())]
            if args.manifest_id:_refs=[r for r in _refs if (r.get('manifest_id') or r.get('construct_set_id'))==args.manifest_id]
            if (_expected or args.manifest_id) and len(_refs)!=1:
                print(json.dumps({'status':'error','error':'No unique matching saved artifact'}) if args.json else 'ERROR: no unique matching saved artifact',file=sys.stdout if args.json else sys.stderr);return 1
            _checks=[derived_artifacts.verify(r,_verify_cfg) for r in _refs]
            _bad=any(r['status']!='VERIFIED' for r in _checks)
            if any(r['status']=='MISMATCH' for r in _checks):
                with state_lock(state_path(_verify_cfg)):
                    _latest=load_state_for_read(_verify_cfg)
                    if _latest is None:return 2
                    for _check in _checks:
                        if _check['status']=='MISMATCH':_emit_gap(_latest,'manifest-hash-mismatch','WARNING',str(_check))
                    save_state(_verify_cfg,_latest)
            if args.json:print(json.dumps({'status':'error' if _bad else 'ok','verification':_checks},indent=2))
            else:
                for _check in _checks:print(f"{_check['status']}: {_check['id']} — {_check.get('reason',_check.get('computed_hash',''))}")
                if not _checks:print('No saved manifests to verify.')
            return 1 if _bad else 0
        if not args.no_verify:
            _vcfg=load_config();_vstate=load_state_for_read(_vcfg)
            if _vstate is not None:
                _failed=[r for r in (derived_artifacts.verify(ref,_vcfg) for ref in derived_artifacts.saved_refs(_vstate)) if r['status']=='MISMATCH']
                if _failed:
                    with state_lock(state_path(_vcfg)):
                        _latest=load_state_for_read(_vcfg)
                        if _latest is None:return 2
                        for _check in _failed:_emit_gap(_latest,'manifest-hash-mismatch','WARNING',str(_check))
                        save_state(_vcfg,_latest)
                    for _check in _failed:print('WARNING: '+str(_check),file=sys.stderr)

        # r62: --bundle resolution — merge bundle construct_ids with --constructs
        _bundle_name = getattr(args, "bundle", None)
        if _bundle_name:
            if _bundle_name not in BUILTIN_BUNDLES:
                print(f"Unknown bundle '{_bundle_name}'. Use --list-bundles to see available bundles.", file=sys.stderr)
                return 1
            if getattr(args, "refresh", False):
                print("Warning: --bundle is ignored when used with --refresh (refresh requires a saved manifest reference).", file=sys.stderr)
                _bundle_name = None
            else:
                _bundle_ids = BUILTIN_BUNDLES[_bundle_name]
                _existing = [p.strip() for p in (args.constructs or "").split(",") if p.strip()]
                _merged = list(dict.fromkeys(_bundle_ids + [c for c in _existing if c not in set(_bundle_ids)]))
                args.constructs = ",".join(_merged)
                # force --kind all so bundle constructs of any kind are resolved
                if not getattr(args, "kind", None) or args.kind == "pattern":
                    args.kind = "all"

        # r41: parse --kind into a set of active kinds (default: "all" for full runtime scope)
        _kind_raw = (getattr(args, "kind", "all") or "all").strip().lower()
        if _kind_raw == "all":
            _active_kinds = set(pattern_catalog_module.ALL_KINDS)
        else:
            _active_kinds = {k.strip() for k in _kind_raw.split(",") if k.strip()}
        _pattern_only = _active_kinds == {"pattern"}

        if not _active_kinds or not _active_kinds <= set(pattern_catalog_module.ALL_KINDS):parser.error('Unknown construct kind')
        if args.refresh and (intent_text or args.constructs):parser.error('Refresh uses saved intent and construct IDs; omit new intent/constructs')
        if not _pattern_only and (args.exclude or args.apply_capabilities or args.derive_capabilities or args.derive_milestone):parser.error('Pattern capability/exclusion options require --kind pattern')
        if args.show_delta and not args.refresh:parser.error('--show-delta requires --refresh')
        if args.manifest_id and not (args.refresh or args.verify or args.derive_expected_hash):parser.error('--manifest-id requires --refresh or verification')
        if getattr(args,'refresh',False):
            _cfg=load_config()
            with state_lock(state_path(_cfg)):
                _rstate=load_state_for_read(_cfg)
                if _rstate is None:print('No initialized state to refresh',file=sys.stderr);return 1
                _results=[]
                if 'pattern' in _active_kinds:_results+=_refresh_derived_manifests(_rstate,_cfg,args.manifest_id,args.show_delta)
                if _active_kinds-{'pattern'}:_results+=_refresh_derived_construct_sets(_rstate,_cfg,args.manifest_id,args.show_delta)
                save_state(_cfg,_rstate)
            # When a manifest-id filter is given across multiple active kinds, not_found
            # from one kind just means the ID belongs to a different kind — only fail if
            # every result is not_found (nothing matched) or any result is 'error'.
            _has_error=any(r.get('status')=='error' for r in _results)
            _all_not_found=bool(_results) and all(r.get('status')=='not_found' for r in _results)
            _failed=_has_error or _all_not_found
            if args.out:atomic_write_json(Path(args.out),{'results':_results})
            if args.json:print(json.dumps({'status':'error' if _failed else 'ok','results':_results},indent=2,sort_keys=True))
            else:
                for row in _results:print(json.dumps(row,sort_keys=True))
            return 1 if _failed else 0

        # --from-goals: derive suggestions from Goals in state (kind-aware)
        if getattr(args, "from_goals", False):
            _fg_cfg = load_config()
            _fg_state = load_state_for_read(_fg_cfg)
            goals_list = (_fg_state or {}).get("objectives", []) or (_fg_state or {}).get("goals", [])
            if not goals_list:
                print("No Goals found in state — initialize with `urace run` first or add goals via `urace add`.", file=sys.stderr)
                return 1
            if _pattern_only:
                suggestions = pattern_catalog_module.patterns_from_goals(goals_list, top_n=8)
                _id_key = "pattern_id"
            else:
                _goal_text = " ".join(
                    str(g.get("title", "")) + " " + str(g.get("description", ""))
                    for g in goals_list
                )
                suggestions = pattern_catalog_module.suggest_constructs_from_intent(_goal_text, kinds=_active_kinds, top_n=8)
                _id_key = "construct_id"
            if not suggestions:
                print("No construct matches found for current Goals.")
                return 0
            if args.json:
                print(json.dumps({"source": "goals", "suggestions": suggestions}, indent=2, sort_keys=True))
            else:
                _kind_label = "pattern" if _pattern_only else "construct"
                print(f"{_kind_label.capitalize()} suggestions derived from Goals:")
                for s in suggestions:
                    _cid = s.get(_id_key, s.get("construct_id", s.get("pattern_id", "?")))
                    _tier = s.get("tier", s.get("kind", ""))
                    print(f"  {_cid:16s} [{_tier:13s}]  {s['name']:45s}  score: {s['score']}")
                _ids_str = ",".join(s.get(_id_key, "") for s in suggestions)
                print(f"\nTo build a set:  urace derive --constructs {_ids_str}" if _pattern_only
                      else f"\nTo build a set:  urace derive --constructs {_ids_str} --kind {_kind_raw}")
            return 0

        # --from-constraints: derive from HardConstraints in state
        if getattr(args, "from_constraints", False):
            _fc_cfg = load_config()
            _fc_state = load_state_for_read(_fc_cfg)
            constraints_list = (_fc_state or {}).get("hard_constraints", [])
            if not constraints_list:
                print("No HardConstraints found in state — add constraints via `urace add` first.", file=sys.stderr)
                return 1
            suggestions = pattern_catalog_module.constructs_from_constraints(constraints_list, top_n=8)
            if not suggestions:
                print("No construct matches found for current HardConstraints.")
                return 0
            if args.json:
                print(json.dumps({"source": "constraints", "suggestions": suggestions}, indent=2, sort_keys=True))
            else:
                print(f"Construct suggestions derived from {len(constraints_list)} HardConstraint(s):")
                for s in suggestions:
                    print(f"  {s['construct_id']:16s} [{s['kind']:13s}]  {s['name']:45s}  score: {s['score']}")
                _ids_str = ",".join(s["construct_id"] for s in suggestions)
                print(f"\nTo build a set:  urace derive --constructs {_ids_str} --kind {','.join(sorted({s['kind'] for s in suggestions}))}")
            return 0

        # --from-inspection: derive from InspectionSurface blocking+warning gaps
        if getattr(args, "from_inspection", False):
            _fi_cfg = load_config()
            _fi_state = load_state_for_read(_fi_cfg)
            surface = _build_inspection_surface(_fi_state or {}, _fi_cfg)
            all_gaps = surface.get("blocking_gaps", []) + surface.get("warning_gaps", [])
            if not all_gaps:
                print("No blocking or warning gaps found in current InspectionSurface — system is healthy.")
                return 0
            suggestions = pattern_catalog_module.constructs_for_gaps(all_gaps, top_n=8)
            if not suggestions:
                print("No construct matches found for current gaps.")
                return 0
            if args.json:
                print(json.dumps({"source": "inspection", "gap_count": len(all_gaps), "suggestions": suggestions}, indent=2, sort_keys=True))
            else:
                print(f"Construct suggestions for {len(all_gaps)} gap(s) found in InspectionSurface:")
                for s in suggestions:
                    print(f"  {s['construct_id']:16s} [{s['kind']:13s}]  {s['name']:45s}  score: {s['score']}")
                _ids_str = ",".join(s["construct_id"] for s in suggestions)
                print(f"\nTo build a set:  urace derive --constructs {_ids_str} --kind {','.join(sorted({s['kind'] for s in suggestions}))}")
            return 0

        # --suggest: dry-run intent matching, no manifest (kind-aware)
        if getattr(args, "suggest", False):
            if not intent_text:
                parser.error("--suggest requires an intent argument: urace derive 'your intent' --suggest")
            if _pattern_only:
                suggestions = pattern_catalog_module.suggest_patterns_from_intent(intent_text, top_n=8)
                _id_key = "pattern_id"
            else:
                suggestions = pattern_catalog_module.suggest_constructs_from_intent(intent_text, kinds=_active_kinds, top_n=8)
                _id_key = "construct_id"
            if not suggestions:
                print(json.dumps({"intent":intent_text,"suggestions":[]}) if args.json else "No matches for that intent — try different keywords.")
                return 0
            if args.json:
                print(json.dumps({"intent": intent_text, "suggestions": suggestions}, indent=2, sort_keys=True))
            else:
                _kind_label = "Pattern" if _pattern_only else "Construct"
                print(f"{_kind_label} suggestions for: \"{intent_text}\"")
                print()
                for s in suggestions:
                    _cid = s.get(_id_key, s.get("construct_id", s.get("pattern_id", "?")))
                    _tier = s.get("tier", s.get("kind", ""))
                    print(f"  {_cid:16s} [{_tier:13s}]  {s['name']}")
                    print(f"  {'':16s}   {s['summary']}")
                _ids_str = ",".join(s.get(_id_key, "") for s in suggestions)
                print(f"\nTo build:  urace derive \"{intent_text}\"" if _pattern_only
                      else f"\nTo build:  urace derive \"{intent_text}\" --kind {_kind_raw}")
            return 0

        # intent-first + explicit --patterns/--constructs merge (kind-aware)
        explicit_from_args = [p.strip() for p in (args.constructs or "").split(",") if p.strip()]

        if not _pattern_only:
            # Non-pattern or mixed kinds: use construct path
            if intent_text and not explicit_from_args:
                _sugg = pattern_catalog_module.suggest_constructs_from_intent(intent_text, kinds=_active_kinds, top_n=6)
                if not _sugg:
                    _freeform_flag = config.get('capability_flags', {}).get('freeform_enabled', True)
                    _executor_on = config.get('executor', {}).get('enabled', False)
                    if _executor_on and _freeform_flag:
                        print(f"No catalog matches. Try: `urace \"{intent_text}\"` to route via AI.")
                    else:
                        print("No construct matches for that intent — try different keywords or use --constructs.", file=sys.stderr)
                    return 1
                _requested_constructs = [s["construct_id"] for s in _sugg]
                if not args.json:
                    print(f"Intent: \"{intent_text}\"")
                    print(f"Suggested constructs ({', '.join(_active_kinds)}): {', '.join(_requested_constructs)}")
                    print()
                # Also show P2P free-use features that match this intent (zero borrow cost)
                try:
                    from .. import freeform_routing as _fr
                    _p2p_free = _fr._p2p_free_features(config)
                    if _p2p_free:
                        _intent_lower = intent_text.lower()
                        _p2p_matches = [f for f in _p2p_free if _intent_lower in (f.get('description','')+'|'+'|'.join(f.get('tags',[]))).lower() or any(t in _intent_lower for t in f.get('tags',[]))]
                        if _p2p_matches and not args.json:
                            print("P2P free-use features matching intent (borrow at zero cost):")
                            for _pf in _p2p_matches[:5]:
                                print(f"  {_pf.get('feature_id','?'):30s}  {_pf.get('description','')[:60]}")
                            print("  Use: urace exchange equity fill-listing <feature_id>")
                            print()
                        elif _p2p_matches and args.json:
                            _sugg = list(_sugg) + [{"construct_id": f["feature_id"], "name": f.get("description",""), "kind": "p2p_free", "score": 1.0, "summary": "P2P free-use feature"} for f in _p2p_matches[:5]]
                except Exception:
                    pass
            elif explicit_from_args:
                if intent_text:
                    _sugg = pattern_catalog_module.suggest_constructs_from_intent(intent_text, kinds=_active_kinds, top_n=6)
                    _sugg_ids = [s["construct_id"] for s in _sugg]
                    _requested_constructs = list(dict.fromkeys(explicit_from_args + [c for c in _sugg_ids if c not in set(explicit_from_args)]))
                    if not args.json:
                        _comp = [c for c in _sugg_ids if c not in set(explicit_from_args)]
                        if _comp:
                            print(f"Complementary suggestions from intent: {', '.join(_comp)}")
                else:
                    _requested_constructs = explicit_from_args
            else:
                # catalog browse for the requested kinds
                lines = [f"Available URACE constructs ({', '.join(sorted(_active_kinds))}):", ""]
                for cid, entry in pattern_catalog_module.CONSTRUCT_CATALOG.items():
                    if entry.get("kind") not in _active_kinds:
                        continue
                    lines.append(f"  {cid:16s} [{entry['kind']:10s}]  {entry['name']:45s}")
                    lines.append(f"  {'':16s}             {entry.get('summary', '')}")
                lines.append("")
                lines.append(f"Tip: describe what you need — urace derive 'quality tracking resilience' --kind {_kind_raw}")
                if args.json:print(json.dumps({'kinds':sorted(_active_kinds),'constructs':{cid:entry for cid,entry in pattern_catalog_module.CONSTRUCT_CATALOG.items() if entry.get('kind') in _active_kinds}},indent=2,sort_keys=True))
                else:print("\n".join(lines))
                return 0
            try:
                _cset = pattern_catalog_module.build_derived_construct_set(
                    construct_ids=_requested_constructs,
                    intent=intent_text or f"derived constructs: {','.join(_requested_constructs)}",
                    spec_version=_current_spec_version(),
                )
            except ValueError as err:
                parser.error(str(err))
            if args.out:
                out_path = Path(args.out)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(_cset, indent=2, sort_keys=True), encoding="utf-8")
                if not args.json:
                    print(f"DerivedConstructSet written to {out_path}")
            if getattr(args, "save", False):
                _s_config = load_config()
                _s_state = load_state_for_read(_s_config)
                if _s_state is not None:
                    _csr_adopted_ids = [r["construct_id"] for r in _cset.get("adopted_constructs", [])]
                    _csr_ref = {
                        "id": identifier("csr"),
                        "construct_set_id": _cset["construct_set_id"],
                        "spec_version": _cset["spec_version"],
                        "generated_at": _cset["generated_at"],
                        "adopted_construct_ids": _csr_adopted_ids,
                        "kinds_present": _cset.get("kinds_present", []),
                        "intent": _cset["intent"],
                        "construct_digests": pattern_catalog_module.construct_digests_for_ids(_csr_adopted_ids),
                    }
                    _csr_ref=derived_artifacts.seal(_csr_ref,_cset,_s_config)
                    _cset["content_hash"]=_csr_ref["content_hash"]
                    if args.out:atomic_write_json(Path(args.out),_cset)
                    _s_state.setdefault("construct_set_refs", [])
                    _s_state["construct_set_refs"] = [
                        r for r in _s_state["construct_set_refs"]
                        if r.get("construct_set_id") != _csr_ref["construct_set_id"]
                    ] + [_csr_ref]
                    with state_lock(state_path(_s_config)):
                        _latest=load_state_for_read(_s_config)
                        if _latest is None:return 2
                        _latest['construct_set_refs']=[r for r in _latest.get('construct_set_refs',[]) if r.get('construct_set_id')!=_csr_ref['construct_set_id']]+[_csr_ref]
                        save_state(_s_config,_latest)
                    if not args.json:
                        print(f"ConstructSetRef saved to state (id={_csr_ref['construct_set_id']})")
                else:
                    print("ERROR: --save requires initialized state", file=sys.stderr);return 2
            if args.json:
                print(json.dumps(_cset, indent=2, sort_keys=True))
            else:
                print(pattern_catalog_module.render_construct_set_human(_cset))
            if getattr(args, "refresh", False):
                _cfg = load_config()
                _rstate = load_state_for_read(_cfg)
                if _rstate is None:
                    print("warning: no initialized state found; --refresh skipped", file=sys.stderr)
                    return 1
                _cset_results = _refresh_derived_construct_sets(
                    _rstate, _cfg,
                    construct_set_id_filter=getattr(args, "manifest_id", None),
                    show_delta=getattr(args, "show_delta", False),
                )
                with state_lock(state_path(_cfg)):
                    save_state(_cfg, _rstate)
                if args.json:
                    print(json.dumps(_cset_results, indent=2, sort_keys=True))
                else:
                    for _r in _cset_results:
                        if _r.get("status") == "refreshed":
                            print(f"  refreshed: {_r['old_construct_set_id']} → {_r['new_construct_set_id']} (spec {_r['spec_was']} → {_r['spec_now']})")
                            if _r.get("delta"):
                                if _r["delta"].get("added_constructs"):
                                    print(f"    added:   {', '.join(_r['delta']['added_constructs'])}")
                                if _r["delta"].get("removed_constructs"):
                                    print(f"    removed: {', '.join(_r['delta']['removed_constructs'])}")
                        else:
                            print(f"  {_r.get('status')}: {_r.get('detail', '')}")
            return 0

        # pattern-only path (existing r40 logic unchanged)
        if intent_text and not explicit_from_args:
            suggestions = pattern_catalog_module.suggest_patterns_from_intent(intent_text, top_n=6)
            if not suggestions:
                print("No pattern matches for that intent — try different keywords or use --constructs.", file=sys.stderr)
                return 1
            suggested_ids = [s["pattern_id"] for s in suggestions]
            if not args.json:
                print(f"Intent: \"{intent_text}\"")
                print(f"Suggested patterns: {', '.join(suggested_ids)}")
                print()
            requested = suggested_ids
        elif intent_text and explicit_from_args:
            suggestions = pattern_catalog_module.suggest_patterns_from_intent(intent_text, top_n=6)
            suggested_ids = [s["pattern_id"] for s in suggestions]
            requested = list(dict.fromkeys(explicit_from_args + [p for p in suggested_ids if p not in explicit_from_args]))
            if not args.json:
                complementary = [p for p in suggested_ids if p not in set(explicit_from_args)]
                if complementary:
                    print(f"Complementary suggestions from intent: {', '.join(complementary)}")
        elif explicit_from_args:
            requested = explicit_from_args
        else:
            # no intent, no --patterns → catalog browse
            lines = ["Available URACE architectural patterns (§62j):", ""]
            for pid, entry in catalog.items():
                deps = ", ".join(entry["requires"]) if entry["requires"] else "none"
                lines.append(f"  {pid:5s} [{entry['tier']:13s}]  {entry['name']:45s}  requires: {deps}")
            lines.append("")
            lines.append("Tip: describe what you're building — urace derive 'resilient event log system'")
            lines.append("     or explore other kinds:  urace derive --kind mechanism|schema|protocol|contract|all")
            if args.json:print(json.dumps({'patterns':catalog},indent=2,sort_keys=True))
            else:print("\n".join(lines))
            return 0

        excluded_deps: list[dict] = []
        if args.exclude:
            if not args.exclude_reason:
                parser.error("--exclude requires --exclude-reason to acknowledge the exclusion")
            for eid in [e.strip() for e in args.exclude.split(",") if e.strip()]:
                excluded_deps.append({"pattern_id": eid, "override_reason": args.exclude_reason})
        try:
            manifest = pattern_catalog_module.build_derived_manifest(
                pattern_ids=requested,
                intent=intent_text or f"derived from URACE patterns: {','.join(requested)}",
                spec_version=_current_spec_version(),
                excluded_deps=excluded_deps or None,
            )
        except ValueError as err:
            parser.error(str(err))
        _derive_pattern_ids = [r["pattern_id"] for r in manifest.get("adopted_patterns", []) if isinstance(r, dict)]
        # r35: pattern-capability-gap detection
        if manifest.get("adopted_patterns"):
            _adopted_ids = [r.get("pattern_id", "") for r in manifest["adopted_patterns"] if isinstance(r, dict)]
            _cfg = load_config()
            _env = _cfg.get("capability_envelope", {})
            _existing_ids = {c.get("id", "") for c in _env.get("capabilities", []) if isinstance(c, dict)}
            _drafts = _derive_capabilities_from_patterns(_adopted_ids, _existing_ids)
            if _drafts:
                manifest["capability_drafts"] = _drafts
                manifest["pattern_capability_gaps"] = [
                    f"{d['_source_pattern']} provides '{d['name']}' — no CapabilityStatement declared"
                    for d in _drafts
                ]
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
            if not args.json:
                print(f"DerivedSystemManifest written to {out_path}")
        if getattr(args, "save", False):
            import hashlib as _hashlib
            _content_hash = derived_artifacts.content_hash(manifest)
            manifest["content_hash"] = _content_hash
            _config = load_config()
            _save_state = load_state_for_read(_config)
            if _save_state is not None:
                _ref_adopted_pids = [r["pattern_id"] for r in manifest["adopted_patterns"]]
                ref = {
                    "manifest_id": manifest["manifest_id"],
                    "spec_version": manifest["spec_version"],
                    "generated_at": manifest["generated_at"],
                    "adopted_pattern_ids": _ref_adopted_pids,
                    "intent": manifest["intent"],
                    "pattern_digests": pattern_catalog_module.pattern_digests_for_ids(_ref_adopted_pids),
                    "content_hash": _content_hash,
                }
                ref=derived_artifacts.seal(ref,manifest,_config)
                if args.out:atomic_write_json(Path(args.out),manifest)
                _save_state.setdefault("derived_manifest_refs", [])
                _save_state["derived_manifest_refs"] = [
                    r for r in _save_state["derived_manifest_refs"]
                    if r.get("manifest_id") != ref["manifest_id"]
                ] + [ref]
                # r36: also write to formal derivation_refs
                dmr_ref = {
                    "id": identifier("dmr"),
                    **ref,
                }
                _save_state.setdefault("derivation_refs", [])
                _save_state["derivation_refs"] = [
                    r for r in _save_state["derivation_refs"]
                    if r.get("manifest_id") != dmr_ref["manifest_id"]
                ] + [dmr_ref]
                with state_lock(state_path(_config)):
                    _latest=load_state_for_read(_config)
                    if _latest is None:return 2
                    for _key,_newref in [('derived_manifest_refs',ref),('derivation_refs',dmr_ref)]:
                        _latest[_key]=[r for r in _latest.get(_key,[]) if r.get('manifest_id')!=ref['manifest_id']]+[_newref]
                    save_state(_config,_latest)
                if not args.json:
                    print(f"Manifest reference saved to state (id={ref['manifest_id']})")
            else:
                print("ERROR: --save requires initialized state", file=sys.stderr);return 2
        # r36: DerivationRecord for MANIFEST kind
        _drv_state = load_state_for_read(load_config())
        if _drv_state is not None:
            _drv_rec = {
                "id": identifier("drv"),
                "kind": "MANIFEST",
                "manifest_id": manifest["manifest_id"],
                "pattern_ids": _derive_pattern_ids,
                "spec_version": manifest["spec_version"],
                "derived_at": manifest["generated_at"],
            }
            _drv_cfg = load_config()
            with state_lock(state_path(_drv_cfg)):
                _latest=load_state_for_read(_drv_cfg)
                if _latest is None:return 2
                _latest.setdefault('derivation_records',[]).append(_drv_rec)
                save_state(_drv_cfg,_latest)
        if args.json:
            print(json.dumps(manifest, indent=2, sort_keys=True))
        else:
            print(pattern_catalog_module.render_manifest_human(manifest))

        # r36: --refresh
        if getattr(args, "refresh", False):
            _cfg = load_config()
            _rstate = load_state_for_read(_cfg)
            if _rstate is None:
                print("warning: no initialized state found; --refresh skipped", file=sys.stderr)
                return 1
            _results = _refresh_derived_manifests(
                _rstate,
                _cfg,
                manifest_id_filter=getattr(args, "manifest_id", None),
                show_delta=getattr(args, "show_delta", False),
            )
            with state_lock(state_path(_cfg)):
                save_state(_cfg, _rstate)
            if args.json:
                print(json.dumps(_results, indent=2, sort_keys=True))
            else:
                for _r in _results:
                    if _r.get("status") == "refreshed":
                        print(f"refreshed: {_r['old_manifest_id']} -> {_r['new_manifest_id']} (spec {_r['spec_was']} -> {_r['spec_now']})")
                        if _r.get("delta"):
                            d = _r["delta"]
                            if d.get("added_patterns"):
                                print(f"  new patterns available: {', '.join(d['added_patterns'])}")
                            if d.get("removed_patterns"):
                                print(f"  patterns removed from dep graph: {', '.join(d['removed_patterns'])}")
                    elif _r.get("status") == "no_saved_manifests":
                        print(_r["detail"])
                    elif _r.get("status") == "not_found":
                        print(_r["detail"])
                    else:
                        print(f"error refreshing {_r.get('manifest_id')}: {_r.get('detail')}")
            return 0

        # r36: --apply-capabilities
        if getattr(args, "apply_capabilities", False):
            if not getattr(args, "constructs", None) and not getattr(args, "derive_capabilities", False):
                parser.error("--apply-capabilities requires --constructs or --derive-capabilities")
            _cfg = load_config()
            _astate = load_state_for_read(_cfg) or {}
            _ap_ids = list(_derive_pattern_ids)
            _env = _cfg.get("capability_envelope", {})
            _existing_ids = {c.get("id", "") for c in _env.get("capabilities", []) if isinstance(c, dict)}
            _existing_names = {c.get("name", "").lower() for c in _env.get("capabilities", []) if isinstance(c, dict)}
            _drafts = _derive_capabilities_from_patterns(_ap_ids, _existing_ids)
            _new_caps = [d for d in _drafts if d.get("name", "").lower() not in _existing_names]
            applied = 0
            if _new_caps:
                with state_lock(CONFIG_PATH):
                    _fresh_cfg=load_config()
                    if state_path(_fresh_cfg)!=state_path(_cfg):parser.error('Active product changed during capability application')
                    _fresh_env=_fresh_cfg.setdefault('capability_envelope',{})
                    _fresh_names={c.get('name','').lower() for c in _fresh_env.get('capabilities',[])}
                    _new_caps=[d for d in _drafts if d.get('name','').lower() not in _fresh_names]
                    for d in _new_caps:_fresh_env.setdefault('capabilities',[]).append({k:v for k,v in d.items() if not k.startswith('_')})
                    applied=len(_new_caps);save_config(_fresh_cfg);_cfg=_fresh_cfg
            drv_rec = {
                "id": identifier("drv"),
                "kind": "CAPABILITY_APPLY",
                "pattern_ids": _ap_ids,
                "spec_version": _current_spec_version(),
                "derived_at": _utcnow(),
                "capabilities_applied": applied,
            }
            with state_lock(state_path(_cfg)):
                _latest=load_state_for_read(_cfg)
                if _latest is None:return 2
                _latest.setdefault('derivation_records',[]).append(drv_rec)
                save_state(_cfg,_latest)
            if args.json:
                print(json.dumps({"capabilities_applied": applied, "capability_names": [d["name"] for d in _new_caps]}, indent=2))
            else:
                print(f"Applied {applied} capability draft(s) to Config.capability_envelope")
                for d in _new_caps:
                    print(f"  + {d['name']} (id={d['id']}, tier={d['tier']})")
                if not _new_caps:
                    print("No new capabilities to apply — all already declared")
            return 0

        # r36: --derive-milestone
        if getattr(args, "derive_milestone", False):
            _cfg = load_config()
            _mstate = load_state_for_read(_cfg) or {}
            _draft_ms = _derive_milestone_from_state(_mstate, _cfg)
            drv_rec = {
                "id": identifier("drv"),
                "kind": "MILESTONE_DRAFT",
                "pattern_ids": [],
                "spec_version": _current_spec_version(),
                "derived_at": _utcnow(),
                "milestone_drafted": _draft_ms is not None,
            }
            with state_lock(state_path(_cfg)):
                _latest=load_state_for_read(_cfg)
                if _latest is None:return 2
                _latest.setdefault('derivation_records',[]).append(drv_rec)
                save_state(_cfg,_latest)
            if _draft_ms is None:
                msg = {"status": "no_gaps", "detail": "All declared capabilities are CAPABLE or better — no milestone draft needed"}
                if args.json:
                    print(json.dumps(msg, indent=2))
                else:
                    print(msg["detail"])
                return 0
            if args.json:
                print(json.dumps(_draft_ms, indent=2, sort_keys=True))
            else:
                print("Draft ProductMilestone (NOT saved — operator review required):")
                print(f"  id:     {_draft_ms['id']}")
                print(f"  name:   {_draft_ms['name']}")
                print(f"  version: {_draft_ms['version']}")
                print(f"  capability_gates ({len(_draft_ms['capability_gates'])}):")
                for g in _draft_ms["capability_gates"]:
                    print(f"    - {g}")
                print("")
                print("Add this milestone to Config.capability_envelope.milestones after review.")
            return 0

        return 0
    if args.command == "context":
        state = load_state_for_read(config)
        if state is None:
            return 2
        if args.action in {"graph","attention"}:
            from ..context_relations import from_state,related,attention
            try:
                graph=from_state(state)
                if not 1<=args.limit<=100 or not 0<=args.depth<=3:raise ValueError("Context views require limit 1–100 and depth 0–3")
                if args.action=="attention":
                    view=attention(graph);rows=view['ordered_nodes'];view.update(ordered_nodes=rows[:args.limit],nodes_total=len(rows),more_available=len(rows)>args.limit)
                elif args.context_node_id:view=related(graph,args.context_node_id,args.depth,args.limit)
                else:
                    selected=dict(list(graph['nodes'].items())[:args.limit]);view={**graph,'nodes':selected,'edges':[e for e in graph['edges'] if e['from'] in selected and e['to'] in selected],'nodes_total':len(graph['nodes']),'edges_total':len(graph['edges']),'more_available':len(selected)<len(graph['nodes'])}
                print(json.dumps(view,indent=2));return 0
            except ValueError as error:parser.error(str(error))
        view = context_view(state)
        if args.json:
            print(json.dumps(view, indent=2, sort_keys=True))
        else:
            print(f"Intent: {view['governing']['intent'].get('purpose')}")
            print(f"Constraints: {len(view['governing']['constraints'])}")
            print(f"User-supplied context: {len(view['user_supplied'])}")
            for item in view["user_supplied"]:
                print(f"  {item['id']}: {item.get('text', '')} (source={item.get('source')} origin={item['origin']})")
            derived = view["urace_derived"]
            print(f"URACE-derived: objectives={len(derived['objectives'])} hypotheses={len(derived['reasoning_hypotheses'])} external-observations={len(derived['external_observations'])}")
            print(view["provenance_note"])
        return 0
    if args.command == "executor" and args.action == "status":
        settings = config.get("executor", {})
        state = load_state_for_read(config) or {}
        pool = state.get("executor_state", {}).get("provider_pool", {})
        health = intelligent_executor.pool_availability(settings, pool) if settings.get("enabled") else {"available": False, "reason": "detached", "providers": []}
        print(json.dumps({"attached": bool(settings.get("enabled")), **health,
                          "workflow_observations":state.get('executor_state',{}).get('workflow_observations',{}),
                          "availability_scope":"Generic execution readiness; workflow observations describe actual artifact-only calls separately"}, indent=2))
        return 0
    if args.command in {"check", "vitals"}:
        state = load_state_for_read(config)
        if state is None:
            return 2
        if args.command == "check" and getattr(args, "migration_dry_run", False):
            # StateSchemaMigrationProtocol (§62l r116) dry-run mode
            current_spec = state.get("spec_version", "unknown")
            candidate_spec = config.get("spec_version", current_spec)
            transforms = state.get("schema_migration_records", [])
            pending = [t for t in transforms if t.get("status") == "PENDING"]
            report = {
                "mode": "dry-run",
                "current_spec_version": current_spec,
                "candidate_spec_version": candidate_spec,
                "pending_transforms": len(pending),
                "transforms": [{"id": t.get("id"), "description": t.get("description", ""), "fields_added": t.get("fields_added", []), "fields_removed": t.get("fields_removed", [])} for t in pending],
                "projected_result": "SUCCESS" if not pending else "PARTIAL",
                "note": "Dry-run: no State changes written. Run without --migration-dry-run to apply.",
            }
            print(json.dumps(report, indent=2, sort_keys=True) if args.format == "json" else "\n".join([
                f"migration-dry-run: current={current_spec} candidate={candidate_spec}",
                f"pending_transforms: {len(pending)}",
                f"projected_result:   {report['projected_result']}",
                "No changes written.",
            ]))
            return 0
        if args.command == "check":
            surface = _build_inspection_surface(state, config)
            surface['preflight_hints'] = _preflight_hints
            _lw = _ledger_size_warning(state_path(config))
            if _lw is not None:
                surface['ledger_health'] = _lw
            _check_query = getattr(args, 'query', None)
            if _check_query:
                _q = _check_query.lower()
                def _matches(v: object) -> bool:
                    return _q in str(v).lower()
                surface = {k: v for k, v in surface.items() if _matches(k) or _matches(v)}
            if args.json:
                print(json.dumps(surface, indent=2, sort_keys=True))
            else:
                print(f"lifecycle_state: {surface['lifecycle_state']}")
                print(f"summary:         {surface['summary']}")
                blocking = surface.get("blocking_gaps", [])
                if blocking:
                    print(f"blocking_gaps:   {len(blocking)}")
                    for g in blocking:
                        print(f"  [{g.get('kind')}] {g.get('detail', '')}")
                warning = surface.get("warning_gaps", [])
                if warning:
                    print(f"warning_gaps:    {len(warning)}")
                    for g in warning:
                        print(f"  [{g.get('kind')}] {g.get('detail', '')}")
                if _preflight_hints:
                    print(f"preflight_hints: {len(_preflight_hints)}")
                    for _h in _preflight_hints:
                        print(f"  [{_h['level']}] {_h['message']} — {_h['action']}")
            if args.fail_on:
                severity_order = {"INFO": 0, "WARNING": 1, "BLOCKING": 2}
                threshold = severity_order.get(args.fail_on, 999)
                active_gaps = [g for g in state.get("integrity_gaps", []) if g.get("active", True)]
                has_threshold = any(severity_order.get(g.get("severity", "INFO"), 0) >= threshold for g in active_gaps)
                if has_threshold:
                    return 1
        else:
            snapshot = vitals_snapshot(config, state)
            print(json.dumps(snapshot, indent=2, sort_keys=True) if args.json else render_vitals(snapshot))
            if args.fail_on:
                severity_order = {"INFO": 0, "WARNING": 1, "BLOCKING": 2}
                threshold = severity_order.get(args.fail_on, 999)
                active_gaps = [g for g in state.get("integrity_gaps", []) if g.get("active", True)]
                has_threshold = any(severity_order.get(g.get("severity", "INFO"), 0) >= threshold for g in active_gaps)
                if has_threshold:
                    return 1
        return 0
    if args.command == "quality":
        state = load_state_for_read(config)
        if state is None:
            return 2
        deltas = state.get("quality_deltas", [])
        if args.scope:
            deltas = [d for d in deltas if d.get("scope") == args.scope]
        qs_map: dict[str, Any] = state.get("quality_state", {})
        if args.scope:
            scope_entry = qs_map.get(args.scope, {})
        else:
            scope_entry = max(qs_map.values(), key=lambda e: e.get("current_streak", 0), default={})
        streak = scope_entry.get("current_streak", 0)
        best_streak = scope_entry.get("best_streak", 0)
        staleness_warnings = _check_staleness(state, config)
        payload: dict[str, Any] = {
            "quality_streak": streak,
            "best_streak": best_streak,
            "total_deltas": len(deltas),
            "improvements": sum(1 for d in deltas if d.get("classification") == "IMPROVEMENT"),
            "regressions": sum(1 for d in deltas if d.get("classification") == "REGRESSION"),
            "neutrals": sum(1 for d in deltas if d.get("classification") == "NEUTRAL"),
            "staleness_warnings": staleness_warnings,
            "deltas": deltas,
        }
        if config.get('execution_workflow')=='specification-trial':
            from ..value_discovery import execution_quality_views
            payload['native_output_quality']=execution_quality_views(SYSTEM_ROOT/'trial')
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"quality_streak: {streak}  best_streak: {best_streak}")
            print(f"total: {payload['total_deltas']}  improvements: {payload['improvements']}  regressions: {payload['regressions']}  neutral: {payload['neutrals']}")
            for w in staleness_warnings:
                print(f"  WARNING: {w}")
            for d in deltas[-10:]:
                score_str = f"{d['score_before']:.3f}→" if "score_before" in d else ""
                print(f"  {d['id']} op={d['operation_id']} scope={d['scope']} score={score_str}{d['score_after']:.3f} delta={d['delta']:+.3f} [{d['classification']}]")
        return 0
    if args.command == "compliance":
        state = load_state_for_read(config)
        if state is None:
            return 2
        import datetime as _dt
        cs_map: dict[str, Any] = state.get("compliance_state", {})
        records: list[dict] = list(state.get("compliance_records", []))
        if args.domain:
            cs_map = {k: v for k, v in cs_map.items() if k == args.domain}
            records = [r for r in records if r.get("domain") == args.domain]
        since = getattr(args, "since", None); until = getattr(args, "until", None)
        if since:
            records = [r for r in records if str(r.get("evaluated_at", "")) >= since]
        if until:
            records = [r for r in records if str(r.get("evaluated_at", "")) <= until + "Z"]
        export_path = getattr(args, "export", None)
        if export_path:
            _ep = Path(export_path)
            if _ep.suffix == ".jsonl":
                _ep.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
            else:
                _ep.write_text(json.dumps({"compliance_records": records, "exported_at": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")}, indent=2, sort_keys=True))
            print(json.dumps({"status": "ok", "exported": len(records), "file": export_path}) if args.json else f"Exported {len(records)} records to {export_path}")
            return 0
        recent = records[-args.history:]
        domains_summary = [
            {"domain": d, "status": e.get("status", "UNKNOWN"),
             "consecutive_clean": e.get("consecutive_clean", 0),
             "last_checked_at": e.get("last_checked_at"),
             "violation_refs": e.get("violation_refs", [])}
            for d, e in cs_map.items()
        ]
        non_compliant_domains = [d for d in domains_summary if d["status"] == "NON_COMPLIANT"]
        payload: dict[str, Any] = {
            "domains": domains_summary,
            "total_records": len(state.get("compliance_records", [])),
            "compliant": sum(1 for r in state.get("compliance_records", []) if r.get("status") == "COMPLIANT"),
            "non_compliant": sum(1 for r in state.get("compliance_records", []) if r.get("status") == "NON_COMPLIANT"),
            "recent_records": recent,
            "strict_pass": len(non_compliant_domains) == 0,
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            if not domains_summary:
                print("No compliance records yet.")
            else:
                for entry in domains_summary:
                    print(f"  {entry['domain']:12s}  {entry['status']:15s}  clean={entry['consecutive_clean']}  checked={entry['last_checked_at']}")
            for r in recent:
                detail = f"  [{r.get('violation_detail', '')}]" if r.get("violation_detail") else ""
                print(f"  {r['id']} domain={r['domain']} status={r['status']}{detail} at={r['evaluated_at']}")
        if getattr(args, "strict", False) and non_compliant_domains:
            if not args.json:
                print(f"STRICT: {len(non_compliant_domains)} non-compliant domain(s): {', '.join(d['domain'] for d in non_compliant_domains)}")
            return 1
        return 0
    if args.command == "milestone":
        config = load_config()
        state = load_state_for_read(config)
        if state is None:
            state = initial_state(config)
        envelope = config.get("capability_envelope", {})
        all_milestones: list[dict] = envelope.get("milestones", [])
        cap_states: dict[str, dict] = {
            e["capability_id"]: e
            for e in state.get("capability_states", [])
            if isinstance(e, dict) and "capability_id" in e
        }
        declared_caps: list[dict] = envelope.get("capabilities", [])
        cap_map: dict[str, dict] = {c["id"]: c for c in declared_caps if isinstance(c, dict) and "id" in c}
        active_ms = next((m for m in all_milestones if isinstance(m, dict) and m.get("status") == "ACTIVE"), None)
        product_versions: list[dict] = list(reversed(state.get("product_versions", [])))
        latest_assessment = (state.get("sweet_spot_assessments") or [{}])[-1]

        from ..milestone_feedback import assess as assess_milestone
        milestone_phases=[assess_milestone(config,state,m) for m in all_milestones if isinstance(m,dict)]
        active_phase=next((m for m in milestone_phases if active_ms and m['id']==active_ms.get('id')),None)

        from ..milestone_suggestions import suggestions as suggest_milestones
        suggested=suggest_milestones(config,state)
        if args.json:
            gates_status: dict[str, str] = {}
            if active_ms:
                for gid in active_ms.get("capability_gates", []):
                    entry = cap_states.get(gid, {})
                    gates_status[gid] = entry.get("status", "ABSENT")
            satisfied = sum(1 for s in gates_status.values() if s in {"CAPABLE", "OVER_ENGINEERED"})
            total_gates = len(gates_status)
            payload: dict[str, Any] = {
                "active_milestone": {
                    "id": active_ms.get("id") if active_ms else None,
                    "name": active_ms.get("name") if active_ms else None,
                    "version_target": active_ms.get("version") if active_ms else None,
                    "gates_satisfied": satisfied,
                    "gates_total": total_gates,
                    "gates": gates_status,
                } if active_ms else None,
                "milestones": milestone_phases,
                "automatic_suggestions": suggested,
                "phase_feedback": active_phase,
                "maturity_level": latest_assessment.get("maturity_level", "BOOTSTRAPPING"),
                "capability_completeness": latest_assessment.get("capability_completeness", 0.0),
                "value_density": latest_assessment.get("value_density", 0.0),
                "version_history": [
                    {"version": pv.get("version"), "achieved_at": pv.get("achieved_at"),
                     "milestone_id": pv.get("milestone_id")}
                    for pv in product_versions
                ],
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            if active_ms:
                gates_status_plain: dict[str, str] = {}
                for gid in active_ms.get("capability_gates", []):
                    entry = cap_states.get(gid, {})
                    gates_status_plain[gid] = entry.get("status", "ABSENT")
                satisfied = sum(1 for s in gates_status_plain.values() if s in {"CAPABLE", "OVER_ENGINEERED"})
                total_gates = len(gates_status_plain)
                pct = f"{satisfied}/{total_gates}" if total_gates > 0 else "0/0"
                print(f"active_milestone:  {active_ms.get('id')}  ({active_ms.get('name', '')})")
                print(f"version_target:    {active_ms.get('version', 'unset')}")
                print(f"phase:             {active_phase['phase']} | status: {active_phase['operational_status']} | canonical: {active_phase['canonical_status']}")
                print(f"gates_satisfied:   {pct}")
                for gid, status in gates_status_plain.items():
                    cap_name = cap_map.get(gid, {}).get("name", gid)
                    mark = "+" if status in {"CAPABLE", "OVER_ENGINEERED"} else "o"
                    print(f"  {mark} {cap_name}  [{status}]")
            else:
                print("active_milestone:  none")
            print(f"milestone_drafts: {len(suggested['suggestions'])} (local; use --json for drafts)")
            print(f"maturity_level:    {latest_assessment.get('maturity_level', 'BOOTSTRAPPING')}")
            if product_versions:
                print(f"current_version:   {product_versions[0].get('version', '—')}")
                print("version_history:")
                for pv in product_versions[:5]:
                    print(f"  {pv.get('version')}  achieved {pv.get('achieved_at', '')[:10]}")
            else:
                print("current_version:   none achieved yet")
        return 0
    if args.command == "source" and getattr(args, "action", None) == "add":
        return _handle_source_add_unified(args, config, parser)
    if args.command == "source" and getattr(args, "action", None) == "status":
        _sfmt = ["--json"] if getattr(args, "format", None) == "json" else []
        return main(["data", "status"] + _sfmt)
    if args.command == "source" and getattr(args, "action", None) in {"sync", "inspect"} and getattr(args, "id", None):
        _sfmt = ["--json"] if getattr(args, "format", None) == "json" else []
        return main(["data", args.action, args.id] + _sfmt)
    if args.command == "source" and getattr(args, "action", None) == "remove":
        _kind = getattr(args, "kind", None)
        _sid = getattr(args, "id", None) or getattr(args, "name", None) or ""
        _sfmt = ["--json"] if getattr(args, "format", None) == "json" else []
        if _kind in {"file", "csv", "json", "sqlite", "api"}:
            return main(["data", "remove", _sid] + _sfmt)
        if _kind == "executor":
            _argv = ["executor", "detach"]
            if _sid:
                _argv += ["--id", _sid]
            return main(_argv + _sfmt)
        if _kind == "metric":
            return main(["metric", "remove", _sid] + _sfmt)
        if _kind == "vital":
            return main(["vital", "remove", _sid] + _sfmt)
        if _kind == "github":
            with state_lock(CONFIG_PATH):
                config = load_config()
                config.pop("github", None)
                save_config(config)
            _res = {"status": "disconnected", "kind": "github"}
            print(json.dumps(_res, indent=2) if getattr(args, "format", None) == "json" else "GitHub disconnected")
            return 0
        # connector or no kind → fall through to existing source_control remove
    if args.command in {"source", "metric", "vital", "goal"}:
        state = load_state_for_read(config)
        if state is None:
            return 2
        key = {"source": "connector_sources", "metric": "metric_definitions", "vital": "vital_definitions", "goal": "objectives"}[args.command]
        if args.command == "goal" and args.action == "forecast":
            report = goal_portfolio(state)
            if args.json: print(json.dumps(report, indent=2, sort_keys=True))
            else:
                for item in report["goals"]:
                    window = item["forecast"]
                    completion = f"{window['earliest']} .. {window['latest']}" if window["earliest"] else "unscheduled"
                    print(f"{item['rank']}. {item['id']}: {item['title']} [{item['status']}] score={item['score']:.2f} completion={completion} confidence={item['estimate']['confidence']}\n   why: {item['priority_reason']}")
            return 0
        if args.command == "goal" and args.action == "inspect":
            if not args.id: parser.error("goal inspect requires an identifier")
            goal = next((entry for entry in state.get("objectives", []) if entry.get("id") == args.id), None)
            if goal is None: parser.error(f"goal not found: {args.id}")
            report = next(item for item in goal_portfolio(state)["goals"] if item["id"] == args.id)
            payload = {"goal": goal, "assessment": report}
            print(json.dumps(payload, indent=2, sort_keys=True) if args.json else f"{goal['id']}: {goal['title']} [{goal['status']}]\npriority: {report['score']:.2f} {report['score_breakdown']}\nforecast: {report['forecast']}\nwhy: {report['priority_reason']}")
            return 0
        if args.action == "list":
            entries = state.get(key, [])
            if args.command == "source":
                entries = list(({item["id"]: {**item, "status": "ACTIVE"} for item in config.get("external_metrics", {}).get("sources", [])} | {item["id"]: item for item in entries}).values())
            if args.command == "goal":
                status_filter = getattr(args, "status", "active")
                if status_filter and status_filter != "all":
                    entries = [e for e in entries if e.get("status", "active") == status_filter]
                limit_val = getattr(args, "limit", 20)
                if limit_val is not None:
                    entries = entries[:limit_val]
            print(json.dumps(entries, indent=2, sort_keys=True) if args.json else ("\n".join(f"{entry.get('id', entry.get('name'))}: {entry.get('name', entry.get('title', entry.get('status', 'configured')))} [{entry.get('status', 'configured')}]" for entry in entries) or f"No {args.command} entries"))
            return 0
        identifier_value = getattr(args, "id", None) or getattr(args, "name", None)
        if not identifier_value:
            parser.error(f"{args.command} {args.action} requires an identifier")
        kind = f"{args.command}_control"
        payload = {"action": args.action, "id" if args.command in {"source", "goal"} else "name": identifier_value}
        if args.command == "goal":
            if args.action == "prioritize" and args.priority is None and args.floor is None and args.ceiling is None:
                parser.error("goal prioritize requires --priority, --floor, or --ceiling")
            if args.floor is not None and args.ceiling is not None and args.floor > args.ceiling:
                parser.error("goal priority floor cannot exceed ceiling")
            if args.action == "defer" and not args.until:
                parser.error("goal defer requires --until")
            if args.action == "resolve-update" and not str(args.decision or "").strip():
                parser.error("goal resolve-update requires --decision")
            if args.action == "schedule":
                supplied = any((args.deadline, args.not_before, args.clear_deadline, args.clear_not_before, args.estimate_min_hours is not None, args.estimate_max_hours is not None, args.estimate_confidence, args.depends_on, args.clear_dependencies))
                if not supplied: parser.error("goal schedule requires a deadline, earliest start, estimate, confidence, dependencies, or a clear option")
                for label, value in (("deadline", args.deadline), ("not-before", args.not_before)):
                    if value:
                        try: datetime.fromisoformat(value)
                        except ValueError: parser.error(f"--{label} must be an ISO-8601 date/time")
                low, high = args.estimate_min_hours, args.estimate_max_hours
                if low is not None and low < 0: parser.error("--estimate-min-hours must be nonnegative")
                if high is not None and high < 0: parser.error("--estimate-max-hours must be nonnegative")
                current_goal = next((entry for entry in state.get("objectives", []) if entry.get("id") == identifier_value), {})
                current_estimate = current_goal.get("estimate", {})
                effective_low = low if low is not None else float(current_estimate.get("min_hours", 0))
                effective_high = high if high is not None else float(current_estimate.get("max_hours", effective_low))
                if effective_high < effective_low: parser.error("goal estimate requires minimum hours <= maximum hours")
                if args.depends_on and identifier_value in args.depends_on: parser.error("a goal cannot depend on itself")
            payload.update({
                "priority": args.priority, "floor": args.floor, "ceiling": args.ceiling, "until": args.until,
                "deadline": args.deadline, "not_before": args.not_before, "clear_deadline": args.clear_deadline,
                "clear_not_before": args.clear_not_before, "estimate_min_hours": args.estimate_min_hours,
                "estimate_max_hours": args.estimate_max_hours, "estimate_confidence": args.estimate_confidence,
                "dependencies": [] if args.clear_dependencies else args.depends_on, "decision": args.decision,
            })
        queued = queue_input(config, kind, payload)
        print(f"Queued {args.command} {args.action} input {queued['id']}; it will be applied at the next cycle boundary or restart")
        return 0
    if args.command == "policy":
        state = load_state_for_read(config)
        if state is None:
            return 2
        policies = {"self-evolution": state.get("self_evolution_policy", config.get("self_evolution_policy", {})), "external-metrics": {"mode": state.get("external_metric_state", {}).get("mode", config.get("external_metrics", {}).get("mode", "DISABLED"))}, "analytics-export": {"mode": config.get("analytics_export", {}).get("mode", "DISABLED")}}
        if args.action == "list":
            print(json.dumps(policies, indent=2, sort_keys=True) if args.json else "\n".join(f"{name}: {value.get('mode')}" for name, value in policies.items()))
            return 0
        allowed = {"self-evolution": {"DISABLED", "NECESSARY_ONLY", "CONTINUOUS"}, "external-metrics": {"DISABLED", "PROVIDED_ONLY", "DISCOVER_PUBLIC_AND_USE_PROVIDED"}, "analytics-export": {"DISABLED", "ON_DEMAND", "ON_CHECKPOINT"}}
        if not args.name or not args.value:
            parser.error("policy set requires NAME and VALUE")
        value = args.value.upper().replace("-", "_")
        if value not in allowed[args.name]:
            parser.error(f"invalid {args.name} policy: {args.value}")
        queued = queue_input(config, "policy_control", {"name": args.name, "value": value})
        print(f"Queued policy change {queued['id']}; it will be applied at the next cycle boundary or restart")
        return 0
    if args.command == "budget":
        settings = config.get("executor", {})
        current_budget = {"daily": settings.get("max_executor_calls_per_24h", 2), "monthly": settings.get("max_executor_calls_per_30d", 12), "unit": "model_calls"}
        if args.action == "show":
            print(json.dumps(current_budget, indent=2, sort_keys=True) if args.json else f"daily={current_budget['daily']} monthly={current_budget['monthly']} unit={current_budget['unit']}")
            return 0
        daily = args.daily if args.daily is not None else current_budget["daily"]
        monthly = args.monthly if args.monthly is not None else current_budget["monthly"]
        if (daily is not None and daily<2) or (monthly is not None and monthly<2) or (daily is not None and monthly is not None and monthly<daily):
            parser.error("budget requires daily >= 2 and monthly >= daily so discovery can reserve completion capacity")
        queued = queue_input(config, "budget_control", {"daily": daily, "monthly": monthly})
        print(f"Queued budget change {queued['id']}; it will be applied at the next cycle boundary or restart")
        return 0
    if args.command == "evaluation":
        state = load_state_for_read(config)
        if state is None:
            return 2
        settings = state.get("evaluation_system", config.get("evaluation_system", {}))
        if args.action == "show":
            report = {"configuration": settings, "current": evolution_vital(config, state), "work": work_evaluations(state)}
            if args.json:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                current = report["current"]
                print(f"evaluation-system v{current['system_version']} minimum-evidence={settings.get('minimum_evidence_units', 5)}")
                print("weights: " + ", ".join(f"{name}={value:g}" for name, value in settings.get("weights", {}).items()))
                for label, key in (("24h", "short_run_24h"), ("30d", "long_run_30d")):
                    window = current[key]
                    print(f"{label}: score={window['diagnostic_score']} confidence={window['confidence']} evidence={window['evidence_units']} components={window['components']}")
                print(f"work: goals={len(report['work']['goals'])} contexts={len(report['work']['contexts'])} action-groups={len(report['work']['actions'])}")
            return 0
        if args.action == "set-weight":
            if args.component not in settings.get("weights", {}):
                parser.error("set-weight requires an existing component name")
            if args.value is None or not 0 <= args.value <= 1:
                parser.error("set-weight VALUE must be between 0 and 1")
            if args.value == 0 and not any(value > 0 for name, value in settings.get("weights", {}).items() if name != args.component):
                parser.error("at least one evaluation weight must remain positive")
            payload = {"action": "set-weight", "component": args.component, "value": args.value}
        else:
            if args.component is None or args.value is not None:
                parser.error("set-minimum requires one positive integer value")
            try:
                minimum = int(args.component)
            except ValueError:
                parser.error("set-minimum requires one positive integer value")
            if minimum < 1:
                parser.error("set-minimum requires one positive integer value")
            payload = {"action": "set-minimum", "value": minimum}
        queued = queue_input(config, "evaluation_control", payload)
        print(f"Queued evaluation change {queued['id']}; it will be applied at the next cycle boundary or restart")
        return 0
    if args.command == "executor" and args.action == "circuit-breaker":
        from .. import circuit_breaker as _cb
        verb = getattr(args, 'cb_action', 'status')
        executor_settings = config.get("executor", {})
        pool_state = config.get("executor_pool_state", {})
        try:
            if verb == 'status':
                result = _cb.status(executor_settings, pool_state)
            elif verb == 'reset':
                pid = getattr(args, 'cb_provider', None)
                if not pid: parser.error("circuit-breaker reset requires --cb-provider <provider_id>")
                result = _cb.reset(pid, executor_settings, pool_state)
                with state_lock(CONFIG_PATH):
                    cfg = load_config()
                    cfg.setdefault("executor_pool_state", {}).update({pid: pool_state.get(pid, {})})
                    save_config(cfg)
            print(json.dumps(result, indent=2, sort_keys=True)); return 0
        except ValueError as e:
            print(json.dumps({'status':'error','error':str(e)},indent=2)); return 1
    if args.command == "executor" and args.action in {"attach", "detach", "retry-policy"}:
        if args.action == "attach" and ((args.max_calls_24h is not None and args.max_calls_24h < 1) or (args.max_calls_30d is not None and args.max_calls_30d < 1) or (args.max_calls_24h is not None and args.max_calls_30d is not None and args.max_calls_30d < args.max_calls_24h)):
            parser.error("Executor transport ceilings require max-calls-24h >= 1 and max-calls-30d >= max-calls-24h")
        if args.retry_delay_ms < 0 or args.retry_fallback_seconds < 60:
            parser.error("Executor retry policy requires nonnegative delay and fallback of at least 60 seconds")
        capability_priorities = {}
        for item in args.capability_priority:
            try:
                name, value = item.split("=", 1)
                if name not in {"discovery", "planning", "mutation", "evaluation", "execution"}: raise ValueError
                capability_priorities[name] = int(value)
            except ValueError:
                parser.error("--capability-priority requires CAPABILITY=INTEGER")
        queued = queue_input(config, "executor_control", {"action": args.action, "id": args.executor_id, "adapter": args.adapter, "command": args.executor_binary, "priority": args.priority, "capabilities": args.capability, "capability_priorities": capability_priorities, "max_calls_per_24h": args.max_calls_24h, "max_calls_per_30d": args.max_calls_30d, "mode": "automatic" if args.retry_mode == "dynamic" else args.retry_mode, "delay_ms": args.retry_delay_ms, "fallback_seconds": args.retry_fallback_seconds})
        if args.json:
            print(json.dumps({"status": "queued", "id": queued["id"], "action": args.action}, indent=2))
            return 0
        print(f"Queued executor {args.action} input {queued['id']}; it will be applied at the next cycle boundary or restart")
        return 0
    if args.command == "pause":
        config = load_config()
        with state_lock(state_path(config)):
            state = load_state(config)
            if state["lifecycle_state"] == "PAUSED":
                print("Lifecycle is already PAUSED" if not args.json else json.dumps({"status": "already_paused"}))
                return 0
            _prior_state = state["lifecycle_state"]
            state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "lifecycle-paused", "prior_state": _prior_state, "disposition": "OPERATOR_INITIATED_PAUSE"})
            state.setdefault("status_transitions", []).append({"status": "PAUSED", "from_status": _prior_state, "at": now(), "reason": "OPERATOR_INITIATED_PAUSE", "source": "cli:pause"})
            state["lifecycle_state"] = "PAUSED"
            save_state(config, state)
        print(json.dumps({"lifecycle": "PAUSED"}) if args.json else "Lifecycle PAUSED; durable state preserved. Run 'urace auto' or 'urace resume' to resume.")
        return 0
    if args.command == "resume":
        config = load_config()
        with state_lock(state_path(config)):
            state = load_state(config)
            if state["lifecycle_state"] != "PAUSED":
                print(f"Lifecycle is {state['lifecycle_state']}, not PAUSED; no action needed" if not args.json else json.dumps({"status": "not_paused", "lifecycle": state["lifecycle_state"]}))
                return 0
            state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "lifecycle-resumed", "disposition": "OPERATOR_INITIATED_RESUME"})
            state.setdefault("status_transitions", []).append({"status": "ASSESSING", "from_status": "PAUSED", "at": now(), "reason": "OPERATOR_INITIATED_RESUME", "source": "cli:resume"})
            state["lifecycle_state"] = "ASSESSING"
            save_state(config, state)
        print(json.dumps({"lifecycle": "ASSESSING"}) if args.json else "Lifecycle resumed from PAUSED; entering ASSESSING. Run 'urace auto' to continue evolution.")
        return 0
    if args.command == "classify":
        # File loading: --file or --path loads content into args.text
        if getattr(args, 'file', None) or getattr(args, 'path', None):
            _farg = getattr(args, 'file', None) or getattr(args, 'path', None)
            try:
                _fpath = Path(_farg).resolve()
                if not _fpath.exists():
                    _out_err = json.dumps({'error': f'File not found: {_farg}'}) if args.json else f'error: File not found: {_farg}'
                    print(_out_err)
                    return 1
                if _fpath.stat().st_size > 65536:
                    _out_err = json.dumps({'error': 'File too large for freeform routing (max 64KB)'}) if args.json else 'error: File too large for freeform routing (max 64KB)'
                    print(_out_err)
                    return 1
                args.text = _fpath.read_text(errors='replace')
            except Exception as _fe:
                _out_err = json.dumps({'error': str(_fe)}) if args.json else f'error: {_fe}'
                print(_out_err)
                return 1
        from ..product_creation import explicit_creation,interpret,apply_interpreted
        interpreted=interpret(args.text,config.get('product_registry',[]),config.get('active_product') or config.get('product'))
        if explicit_creation(args.text) or any(i['kind']=='new_product' for i in interpreted['intents']):
            if interpreted['status']=='INTERPRETED':
                result=apply_interpreted(sys.modules[__name__],interpreted);print(json.dumps(result,indent=2));return 0 if result['status']=='BOOTSTRAPPED_OR_QUEUED' else 2
            print(json.dumps({**interpreted,'actions_taken':[],'reason':'Resolve the shown scope/relationship ambiguity before mutation; original input retained'},indent=2));return 2
        state=load_state_for_read(config) if state_path(config).exists() else {"executor_state":{},"interpretation_only_uninitialized_product":True}
        if state is None:return 2
        return freeform_routing.route(sys.modules[__name__],args,config,state,parser)
    if args.command == "add":
        # r101: add is the canonical structured-queue command (renamed from declare r100)
        sub = getattr(args, "add_subcommand", None)
        if not sub:
            parser.error("add requires a subcommand: context, goal, source, metric, vital, evidence, principal")
        if sub == "principal":
            config = load_config()
            state = load_state_for_read(config) or initial_state(config)
            pr = {
                "id": identifier("pr"),
                "at": now(),
                "name": args.name,
                "precedence": args.precedence,
                "scope": args.scope,
                "is_active": True,
                "created_by": "operator",
            }
            state.setdefault("principal_records", []).append(pr)
            save_state(config, state)
            if args.format == "json":
                print(json.dumps({"status": "created", "id": pr["id"], "name": pr["name"], "precedence": pr["precedence"]}, indent=2))
            else:
                print(f"Created PrincipalRecord {pr['id']} — {pr['name']} (precedence={pr['precedence']}, scope={pr['scope']})")
            return 0
        config = load_config()
        if sub == "context":
            if len(args.text) > 20000:
                parser.error("context text must be 20,000 characters or fewer")
            payload = {"text": args.text, "source": args.source}
            kind = "context"
        elif sub == "goal":
            for label, value in (("expected-value", args.expected_value), ("estimated-cost", args.estimated_cost), ("risk", args.risk), ("urgency", args.urgency)):
                if not 0 <= value <= 1:
                    parser.error(f"--{label} must be between 0 and 1")
            if args.estimate_min_hours < 0 or args.estimate_max_hours < args.estimate_min_hours:
                parser.error("goal estimate requires 0 <= minimum hours <= maximum hours")
            if args.priority_floor is not None and args.priority_ceiling is not None and args.priority_floor > args.priority_ceiling:
                parser.error("goal priority floor cannot exceed ceiling")
            for label, value in (("deadline", args.deadline), ("not-before", args.not_before)):
                if value:
                    try: datetime.fromisoformat(value)
                    except ValueError: parser.error(f"--{label} must be an ISO-8601 date/time")
            payload = {"title": args.title, "success_measure": args.success_measure, "outcome_measure_id": getattr(args, "outcome_measure", None), "reason": args.reason, "target": args.target, "priority": args.priority, "expected_value": args.expected_value, "estimated_cost": args.estimated_cost, "risk": args.risk, "urgency": args.urgency, "necessity_evidence": args.necessity_evidence, "lower_impact_insufficient": args.lower_impact_insufficient, "dependencies": args.depends_on, "deadline": args.deadline, "not_before": args.not_before, "estimate": {"min_hours": args.estimate_min_hours, "max_hours": args.estimate_max_hours}, "estimate_confidence": args.estimate_confidence, "priority_floor": args.priority_floor, "priority_ceiling": args.priority_ceiling, "pinned": args.pin}
            kind = "goal"
        elif sub == "source":
            payload = {"id": args.id, "kind": args.kind, "visibility": args.visibility}
            payload["repository" if args.kind == "github_repository" else "location"] = args.location
            if args.credential_env:
                payload["credential_env"] = args.credential_env
            kind = "source"
        elif sub == "metric":
            payload = {"name": args.name, "source": args.source, "path": args.path, "direction": args.direction, "target": args.target}
            kind = "metric"
        elif sub == "vital":
            payload = {"name": args.name, "numerator": args.numerator, "denominator": args.denominator, "window": args.window, "description": args.description}
            kind = "vital"
        elif sub == "evidence":
            payload = {"kind": args.kind, "summary": args.summary, "source": args.source, "detail": args.detail}
            kind = "evidence"
        if getattr(args, "scope", None):
            payload["scope"] = args.scope
        if getattr(args, "relates_to", None):
            payload["related_ids"] = [r.strip() for r in args.relates_to.split(",") if r.strip()]
        queued = queue_input(config, kind, payload)
        if args.json:
            if kind == "context":
                json_out = {"status": "queued", "id": queued["id"], "text": args.text, "source": args.source}
            elif kind == "goal":
                json_out = {"status": "queued", "id": queued["id"], "kind": "goal", "title": args.title}
            elif kind == "source":
                json_out = {"status": "queued", "id": queued["id"], "id_arg": args.id, "kind": args.kind}
            elif kind == "metric":
                json_out = {"status": "queued", "id": queued["id"], "name": args.name, "source": args.source}
            elif kind == "evidence":
                json_out = {"status": "queued", "id": queued["id"], "kind": args.kind, "summary": args.summary}
            else:
                json_out = {"status": "queued", "id": queued["id"], "name": args.name}
            print(json.dumps(json_out, indent=2))
            return 0
        print(f"Queued {kind} input {queued['id']}; it will be applied at the next cycle boundary or restart")
        return 0
    if args.command == "declare":
        # r101: declare is a deprecated alias for add (r100 backwards compat)
        dep_sub = getattr(args, "declare_subcommand", None)
        if not dep_sub:
            print("Warning: `declare` is deprecated; use `urace add context|goal|source|metric|vital` instead.", file=sys.stderr)
            parser.error("declare requires a subcommand: context, goal, source, metric, vital")
        print(f"Warning: `declare {dep_sub}` is deprecated; use `urace add {dep_sub}` instead.", file=sys.stderr)
        # Re-dispatch to add handler via main()
        remainder = list(getattr(args, "declare_remainder", []))
        return main(["add", dep_sub] + remainder)
    if args.command in {"add-context", "add-goal", "add-source", "add-metric", "add-vital"}:
        _dep_map = {"add-context": "add context", "add-goal": "add goal", "add-source": "add source", "add-metric": "add metric", "add-vital": "add vital"}
        print(f"Warning: `{args.command}` is deprecated; use `urace {_dep_map[args.command]}` instead.", file=sys.stderr)
        if args.command == "add-context":
            if len(args.text) > 20000:
                parser.error("context text must be 20,000 characters or fewer; add a bounded source for larger material")
            payload = {"text": args.text, "source": args.source}
            kind = "context"
        elif args.command == "add-goal":
            for label, value in (("expected-value", args.expected_value), ("estimated-cost", args.estimated_cost), ("risk", args.risk), ("urgency", args.urgency)):
                if not 0 <= value <= 1:
                    parser.error(f"--{label} must be between 0 and 1")
            if args.estimate_min_hours < 0 or args.estimate_max_hours < args.estimate_min_hours:
                parser.error("goal estimate requires 0 <= minimum hours <= maximum hours")
            if args.priority_floor is not None and args.priority_ceiling is not None and args.priority_floor > args.priority_ceiling:
                parser.error("goal priority floor cannot exceed ceiling")
            for label, value in (("deadline", args.deadline), ("not-before", args.not_before)):
                if value:
                    try: datetime.fromisoformat(value)
                    except ValueError: parser.error(f"--{label} must be an ISO-8601 date/time")
            payload = {"title": args.title, "success_measure": args.success_measure, "outcome_measure_id": getattr(args, "outcome_measure", None), "reason": args.reason, "target": args.target, "priority": args.priority, "expected_value": args.expected_value, "estimated_cost": args.estimated_cost, "risk": args.risk, "urgency": args.urgency, "necessity_evidence": args.necessity_evidence, "lower_impact_insufficient": args.lower_impact_insufficient, "dependencies": args.depends_on, "deadline": args.deadline, "not_before": args.not_before, "estimate": {"min_hours": args.estimate_min_hours, "max_hours": args.estimate_max_hours}, "estimate_confidence": args.estimate_confidence, "priority_floor": args.priority_floor, "priority_ceiling": args.priority_ceiling, "pinned": args.pin}
            kind = "goal"
        elif args.command == "add-source":
            payload = {"id": args.id, "kind": args.kind, "visibility": args.visibility}
            payload["repository" if args.kind == "github_repository" else "location"] = args.location
            if args.credential_env:
                payload["credential_env"] = args.credential_env
            kind = "source"
        elif args.command == "add-metric":
            payload = {"name": args.name, "source": args.source, "path": args.path, "direction": args.direction, "target": args.target}
            kind = "metric"
        else:
            payload = {"name": args.name, "numerator": args.numerator, "denominator": args.denominator, "window": args.window, "description": args.description}
            kind = "vital"
        queued = queue_input(config, kind, payload)
        if args.json:
            if kind == "context":
                json_out = {"status": "queued", "id": queued["id"], "text": args.text, "source": args.source}
            elif kind == "goal":
                json_out = {"status": "queued", "id": queued["id"], "kind": "goal", "title": args.title}
            elif kind == "source":
                json_out = {"status": "queued", "id": queued["id"], "id_arg": args.id, "kind": args.kind}
            elif kind == "metric":
                json_out = {"status": "queued", "id": queued["id"], "name": args.name, "source": args.source}
            else:  # vital
                json_out = {"status": "queued", "id": queued["id"], "name": args.name}
            print(json.dumps(json_out, indent=2))
            return 0
        print(f"Queued {kind} input {queued['id']}; it will be applied at the next cycle boundary or restart")
        return 0
    if args.command == "intent":
        if args.action == "list":
            state = load_state_for_read(config)
            if state is None:
                return 2
            ledger = state.get("rule_ledger", {})
            entries = rule_ledger_module.active_rules(ledger, kind="DIRECTIVE", scope=None, include_inferred=args.inferred if hasattr(args, "inferred") else False, min_confidence=0.0)
            if args.json:
                print(json.dumps(entries, indent=2, sort_keys=True))
            elif not entries:
                print("No active DIRECTIVE rules")
            else:
                for r in entries:
                    print(rule_ledger_module.format_rule_compact(r))
            return 0
        if args.action in {"add", "supersede"}:
            if not args.statement:
                parser.error(f"intent {args.action} requires a statement")
            payload = {"action": args.action, "statement": args.statement, "rule_kind": "DIRECTIVE", "scope": args.scope}
            if args.action == "supersede":
                if not args.rule_id:
                    parser.error("intent supersede requires --id of the rule being superseded")
                payload["old_rule_id"] = args.rule_id
            queued = queue_input(config, "intent_control", payload)
            print(f"Queued intent {args.action} {queued['id']}; it will be applied at the next cycle boundary or restart")
            return 0
        if args.action == "deactivate":
            if not args.rule_id:
                parser.error("intent deactivate requires --id")
            queued = queue_input(config, "intent_control", {"action": "deactivate", "rule_id": args.rule_id})
            print(f"Queued intent deactivate {queued['id']}; it will be applied at the next cycle boundary or restart")
            return 0
        if args.action == "rollback":
            version = args.statement
            if not version:
                parser.error("intent rollback requires <version> — the IntentVersionRecord id to restore")
            state = load_state_for_read(config)
            if state is None:
                return 2
            ivrs = state.get("intent_version_records", [])
            target = next((r for r in ivrs if r.get("id") == version), None)
            if target is None:
                print(f"No IntentVersionRecord found with id '{version}'. Use 'urace check --json' to list intent_version_records.")
                return 1
            new_ivr = {
                "id": identifier("ivr"),
                "at": now(),
                "spec_version": state.get("spec_version", ""),
                "mutation_reason": f"intent-rollback-to-{version}",
                "directive_snapshot": target.get("directive_snapshot", []),
                "goal_snapshot": target.get("goal_snapshot", []),
            }
            state.setdefault("intent_version_records", []).append(new_ivr)
            queued = queue_input(config, "intent_control", {"action": "rollback", "version": version, "ivr_id": new_ivr["id"]})
            if args.format == "json":
                print(json.dumps({"queued": queued["id"], "ivr_id": new_ivr["id"], "target_version": version}, indent=2))
            else:
                print(f"Queued intent rollback to {version} ({queued['id']}); IntentVersionRecord {new_ivr['id']} created. Changes applied at next cycle boundary.")
            return 0
    if args.command == "constraint":
        if args.action == "list":
            state = load_state_for_read(config)
            if state is None:
                return 2
            ledger = state.get("rule_ledger", {})
            prohibitions = rule_ledger_module.active_rules(ledger, kind="PROHIBITION", scope=None, include_inferred=False, min_confidence=0.0)
            permissions = rule_ledger_module.active_rules(ledger, kind="PERMISSION", scope=None, include_inferred=False, min_confidence=0.0)
            entries = prohibitions + permissions
            return _inspect_list(entries, args,
                fmt=rule_ledger_module.format_rule_compact,
                empty_msg="No active constraint rules",
                time_field=None)
        if args.action == "add":
            if not args.statement:
                parser.error("constraint add requires a statement")
            rule_kind = "PERMISSION" if args.allow else "PROHIBITION"
            queued = queue_input(config, "constraint_control", {"action": "add", "statement": args.statement, "rule_kind": rule_kind, "scope": args.scope})
            print(f"Queued constraint add {queued['id']}; it will be applied at the next cycle boundary or restart")
            return 0
        if args.action == "deactivate":
            if not args.rule_id:
                parser.error("constraint deactivate requires --id")
            queued = queue_input(config, "constraint_control", {"action": "deactivate", "rule_id": args.rule_id})
            print(f"Queued constraint deactivate {queued['id']}; it will be applied at the next cycle boundary or restart")
            return 0
    if args.command == "explain":
        # r113 ExplanationProtocol (§62l) — synthesize human-readable DecisionRecord explanation
        state = load_state_for_read(config)
        if state is None:
            return 2
        target_id = args.id
        decision_records = state.get("decision_records", [])
        dr = next((r for r in decision_records if r.get("id") == target_id), None)
        if dr is None:
            print(f"No DecisionRecord found with id '{target_id}'. Use 'urace check --json' to list decision_records.", file=sys.stderr)
            return 1
        existing = next((r for r in state.get("explanation_records", []) if r.get("decision_id") == target_id), None)
        if existing:
            exr = existing
        else:
            exr = {
                "id": identifier("exr"),
                "at": now(),
                "decision_id": target_id,
                "plain_language": (
                    f"Decision {target_id} was taken at {dr.get('at', 'unknown')} "
                    f"with rationale: {dr.get('rationale', dr.get('summary', 'no rationale recorded'))}. "
                    f"Authority basis: {dr.get('authority_basis', 'not specified')}. "
                    f"Outcome: {dr.get('outcome', 'not recorded')}."
                ),
                "chain_completeness": 0.5,
                "causal_model_id": None,
                "lookahead_plan_id": None,
            }
        if args.format == "json":
            print(json.dumps(exr, indent=2, sort_keys=True))
        else:
            print(f"Explanation for {target_id}:")
            print(exr["plain_language"])
            print(f"Chain completeness: {exr['chain_completeness']:.0%}")
        return 0
    if args.command == "rules":
        state = load_state_for_read(config)
        if state is None:
            return 2
        ledger = state.get("rule_ledger", {})
        if not ledger:
            print("Rule Ledger not yet seeded — run 'urace init' or restart the autonomous owner" if not args.json else json.dumps({"status": "no_ledger"}))
            return 0
        if args.action == "list":
            kind_filter = args.kind.upper() if args.kind else None
            entries = rule_ledger_module.active_rules(ledger, kind=kind_filter, scope=args.scope, include_inferred=args.inferred, min_confidence=0.0)
            since_filter = getattr(args, "since", None)
            until_filter = getattr(args, "until", None)
            if since_filter:
                entries = [r for r in entries if (r.get("established_at") or r.get("created_at") or "") >= since_filter]
            if until_filter:
                entries = [r for r in entries if (r.get("established_at") or r.get("created_at") or "") <= until_filter]
            return _inspect_list(entries, args,
                fmt=rule_ledger_module.format_rule_compact,
                empty_msg="No active rules match the filter",
                time_field=None)
        if args.action == "inspect":
            if not args.id:
                parser.error("rules inspect requires a rule ID")
            rule = rule_ledger_module.get_rule(ledger, args.id)
            if rule is None:
                parser.error(f"rule not found: {args.id}")
            if args.json:
                print(json.dumps(rule, indent=2, sort_keys=True))
            else:
                print(rule_ledger_module.format_rule_full(rule, ledger))
            return 0
        if args.action == "graph":
            all_active = rule_ledger_module.active_rules(ledger, kind=None, scope=None, include_inferred=True, min_confidence=0.0)
            if args.json:
                graph = {"rules": all_active, "relationships": ledger.get("relationships", [])}
                print(json.dumps(graph, indent=2, sort_keys=True))
            else:
                print(f"Rule Ledger — {len(all_active)} active rules | digest: {rule_ledger_module.snapshot_digest(ledger)[:12]}")
                for r in all_active:
                    print(rule_ledger_module.format_rule_compact(r))
                rels = ledger.get("relationships", [])
                if rels:
                    print(f"\nRelationships ({len(rels)}):")
                    for rel in rels:
                        print(f"  {rel['from_id']} --[{rel['type']}]--> {rel['to_id']}")
            return 0
        if args.action == "conflicts":
            conflicts = rule_ledger_module.detect_conflicts(ledger)
            if args.json:
                print(json.dumps(conflicts, indent=2, sort_keys=True))
            elif not conflicts:
                print("No conflicts detected")
            else:
                for c in conflicts:
                    print(f"CONFLICT: {c['rule_a']} vs {c['rule_b']} — {c.get('kind', 'keyword overlap')}")
            return 0
        if args.action == "changes":
            if not args.id:
                parser.error("rules changes requires a rule ID")
            change_ids = rule_ledger_module.changes_for_rule(ledger, args.id)
            if args.json:
                print(json.dumps({"rule_id": args.id, "change_ids": change_ids}, indent=2, sort_keys=True))
            elif not change_ids:
                print(f"No changes recorded for rule {args.id}")
            else:
                print(f"Changes governed by rule {args.id}:")
                for cid in change_ids:
                    print(f"  {cid}")
            return 0
    if args.command in {"compact", "decompact", "amend", "why", "crc"}:
        from .. import compaction as _compaction_module
        from .. import cognitive_resume as _crc_module

        def _resolve_product_targets(cfg: dict, product_single, products_multi):
            """Return [(name, state_root_str), ...] in dependency order, or None on error.

            r106: --product and --products share dest="product"; product_single may hold
            a comma-separated list or 'all' (formerly only products_multi).
            """
            registry = cfg.get("product_registry", [])
            by_name = {e["name"]: e for e in registry if "name" in e}
            # products_multi is now effectively unused (dest collapsed), but kept for
            # backward compat with code that passes it directly.
            combined = products_multi or product_single
            if combined:
                if combined.strip().lower() == "all":
                    names = list(by_name.keys())
                elif "," in combined:
                    names = [n.strip() for n in combined.split(",") if n.strip()]
                else:
                    names = [combined.strip()]
            else:
                return None  # caller uses default active product
            # validate
            missing = [n for n in names if n not in by_name]
            if missing:
                return [("__error__", f"products not in registry: {', '.join(missing)}")]
            # build deps_map: n -> list of its dependencies within the selected set
            sel = set(names)
            deps_map = {n: [d for d in (by_name[n].get("depends_on") or []) if d in sel] for n in names}
            # build reverse adjacency: dep -> list of nodes that depend on dep
            rev = {n: [] for n in names}
            for n in names:
                for dep in deps_map[n]:
                    rev[dep].append(n)
            # Kahn's topological sort
            in_degree = {n: len(deps_map[n]) for n in names}
            queue = [n for n in names if in_degree[n] == 0]
            order = []
            while queue:
                n = queue.pop(0)
                order.append(n)
                for dependant in rev[n]:
                    in_degree[dependant] -= 1
                    if in_degree[dependant] == 0:
                        queue.append(dependant)
            if len(order) != len(names):
                return [("__cycle__", "cycle detected in product depends_on graph")]
            result = []
            for n in order:
                sp_path = by_name[n].get("state_path", "")
                if sp_path:
                    result.append((n, str(Path(sp_path).parent)))
                else:
                    result.append((n, "__missing__"))
            return result

        config = load_config()
        sp = str(state_path(config).parent)

        # r106: --product / --products collapsed; --product accepts ID[,...]|all
        _prod_single = getattr(args, "product", None)
        _prod_multi = None  # legacy: products_multi arg kept for compat; now always None
        _prod_targets = _resolve_product_targets(config, _prod_single, _prod_multi)
        if _prod_targets and _prod_targets[0][0] in ("__error__", "__cycle__"):
            _err_kind = _prod_targets[0][0]
            _err_msg = _prod_targets[0][1]
            if _err_kind == "__cycle__":
                _err_state = load_state_for_read(config) or {}
                _emit_gap(_err_state, "multi-product-compact-cycle", "BLOCKING", _err_msg)
                save_state(config, _err_state)
            print(f"ERROR: {_err_msg}", file=sys.stderr)
            return 1
        if _prod_targets and len(_prod_targets) == 1 and args.command in {"compact", "decompact", "amend", "crc"}:
            # single-product override
            _target_sp = _prod_targets[0][1]
            if _target_sp == "__missing__":
                print(f"ERROR: product '{_prod_targets[0][0]}' has no state_path in registry", file=sys.stderr)
                return 1
            sp = _target_sp
        elif _prod_targets and len(_prod_targets) > 1 and args.command in {"compact", "decompact", "crc"}:
            _overall_rc = 0
            for _mp_name, _mp_sp in _prod_targets:
                if _mp_sp == "__missing__":
                    print(f"  WARNING: product '{_mp_name}': no state_path registered; skipping", file=sys.stderr)
                    continue
                # Build args for single-product invocation
                _mp_argv = [args.command]
                _mp_fmt = getattr(args, "format", "json")
                if args.command == "compact":
                    _mp_argv += [args.field_path]
                    if getattr(args, "dry_run", False): _mp_argv.append("--dry-run")
                    if getattr(args, "mode", None): _mp_argv += ["--mode", args.mode]
                    if getattr(args, "json", False): _mp_argv.append("--json")
                    if _mp_fmt == "xml": _mp_argv += ["--format", "xml"]
                    _mp_argv += ["--product", _mp_name]
                elif args.command == "decompact":
                    _mp_argv += [args.compaction_event_id]
                    if getattr(args, "field_path", None): _mp_argv += ["--field-path", args.field_path]
                    if getattr(args, "record_id", None): _mp_argv += ["--record-id", args.record_id]
                    if getattr(args, "json", False): _mp_argv.append("--json")
                    if _mp_fmt == "xml": _mp_argv += ["--format", "xml"]
                    _mp_argv += ["--product", _mp_name]
                elif args.command == "crc":
                    _mp_argv += [args.action]
                    if getattr(args, "json", False): _mp_argv.append("--json")
                    if _mp_fmt == "xml": _mp_argv += ["--format", "xml"]
                    _mp_argv += ["--product", _mp_name]
                print(f"  [{_mp_name}]")
                _rc = main(_mp_argv)
                if _rc != 0:
                    _overall_rc = _rc
            return _overall_rc

        if args.command == "crc":
            state = load_state_for_read(config) or {}
            if args.action == "show":
                existing = _crc_module.load(sp)
                if existing is None:
                    msg = {"status": "no_crc", "detail": "No CognitiveResumeContext on disk; will be generated at next cycle boundary"}
                else:
                    stale = _crc_module.is_stale(existing, state)
                    msg = {"status": "stale" if stale else "current", "crc": existing}
                _fmt = getattr(args, "format", "json")
                if getattr(args, "json", False) or _fmt == "xml":
                    _print_fmt(msg, _fmt)
                else:
                    if existing is None:
                        print("No CognitiveResumeContext on disk.")
                    else:
                        print(f"CRC id: {existing['id']}")
                        print(f"  phase: {existing['cycle_phase']}")
                        print(f"  generated_at: {existing['generated_at']}")
                        print(f"  stale: {_crc_module.is_stale(existing, state)}")
                        print(f"  blocking_gaps: {len(existing['blocking_gaps'])}")
                        print(f"  pending_validations: {len(existing['pending_validations'])}")
                return 0
            if args.action == "regenerate":
                fresh = _crc_module.generate(state)
                _crc_module.save(sp, fresh)
                _fmt = getattr(args, "format", "json")
                if getattr(args, "json", False) or _fmt == "xml":
                    _print_fmt({"status": "regenerated", "crc": fresh}, _fmt)
                else:
                    print(f"CognitiveResumeContext regenerated: {fresh['id']}")
                    print(f"  phase: {fresh['cycle_phase']}")
                return 0

        if args.command == "compact":
            from ..compaction import _DEFAULT_GOVERNANCE, _PROHIBITED_FIELDS, get_compaction_status
            state = load_state_for_read(config) or {}

            if getattr(args, "status", False):
                _status = get_compaction_status(sp)
                if args.json:
                    _print_fmt(_status, _fmt or "json")
                else:
                    print("Compaction status:")
                    print(f"  manifest: {'present' if _status['has_manifest'] else 'none'}")
                    print(f"  events: {_status['event_count']}")
                    print(f"  last_compacted_at: {_status['last_compacted_at'] or 'never'}")
                    for _fp, _cnt in _status["archive_counts"].items():
                        print(f"  archives/{_fp}: {_cnt} file(s)")
                return 0

            # Resolve field_path from --target or positional
            _target_str = getattr(args, "target", None)
            _field_path = args.field_path

            if _target_str == "all":
                # Queue compaction for all governed non-PROHIBITED fields
                _fields_all = [fp for fp, pol in _DEFAULT_GOVERNANCE.items()
                               if pol.get("compaction_mode") != "PROHIBITED"]
                _policies_all = {fp: {"id": identifier("rtp"), "target_field": fp, **_DEFAULT_GOVERNANCE[fp]}
                                 for fp in _fields_all}
                queued = []
                errs = []
                for fp in _fields_all:
                    try:
                        inp = queue_input(config, "compact", {"kind": "compact", "field_path": fp,
                                                               "policy": _policies_all[fp]})
                        queued.append(fp)
                    except Exception as exc:
                        errs.append({"field": fp, "error": str(exc)})
                result = {"status": "batch_queued", "queued": queued, "errors": errs}
                if args.json:
                    _print_fmt(result, _fmt or "json")
                else:
                    print(f"Compact --target all: {len(queued)} field(s) queued, {len(errs)} error(s).")
                return 0

            if _target_str and not _field_path:
                _resolved = _resolve_scope_target(_target_str, sp)
                if _resolved.get("error"):
                    print(f"urace compact: --target resolution error: {_resolved['error']}", file=sys.stderr)
                    return 1
                _field_path = _resolved.get("field") or _field_path

            if not _field_path:
                print("urace compact: field_path required (positional or --target FIELD)", file=sys.stderr)
                return 1

            policy_override: dict | None = None
            if args.mode:
                if _field_path in _PROHIBITED_FIELDS:
                    print(f"urace compact: field '{_field_path}' is PROHIBITED", file=sys.stderr)
                    return 1
                default = _DEFAULT_GOVERNANCE.get(_field_path, {})
                policy_override = {
                    "id": identifier("rtp"),
                    "target_field": _field_path,
                    "compaction_mode": args.mode,
                    "max_entries": default.get("max_entries", 1),
                }
                if args.mode == "ARCHIVE":
                    policy_override["archive_subpath"] = default.get(
                        "archive_subpath", f"archives/{_field_path.replace('.', '-')}"
                    )

            engine = _compaction_module.CompactionEngine(sp)
            default_policy = _DEFAULT_GOVERNANCE.get(_field_path)
            if default_policy is None and policy_override is None:
                print(f"urace compact: no governance policy for field '{_field_path}'", file=sys.stderr)
                return 1

            policy = policy_override or {
                "id": identifier("rtp"),
                "target_field": _field_path,
                **default_policy,
            }
            if policy.get("compaction_mode") == "PROHIBITED":
                print(f"urace compact: field '{_field_path}' is PROHIBITED", file=sys.stderr)
                return 1

            if args.dry_run:
                report = engine.dry_run(state, _field_path, policy)
                if args.json:
                    _print_fmt(report, _fmt or "json")
                else:
                    print(f"Compact dry-run: {_field_path}")
                    print(f"  records: {report['record_count']}, eligible: {report['eligible_count']}")
                    print(f"  would compact: {report['would_compact']}, mode: {report['mode']}")
                return 0

            inp = queue_input(config, "compact", {
                "kind": "compact",
                "field_path": _field_path,
                "policy": policy,
            })
            if args.json:
                _print_fmt({"status": "queued", "input_id": inp["id"]}, _fmt or "json")
            else:
                print(f"Compact queued (input {inp['id']}); will execute at next safe lifecycle boundary.")
            return 0

        if args.command == "decompact":
            engine = _compaction_module.CompactionEngine(sp)

            # Resolve compaction_event_id from --target if provided
            _target_str = getattr(args, "target", None)
            _event_id = args.compaction_event_id
            if _target_str and not _event_id:
                _resolved = _resolve_scope_target(_target_str, sp)
                if _resolved.get("error"):
                    print(f"urace decompact: --target resolution error: {_resolved['error']}", file=sys.stderr)
                    return 1
                _event_id = _resolved.get("resolved_id")
                if not _event_id:
                    print(f"urace decompact: --target '{_target_str}' did not resolve to an event", file=sys.stderr)
                    return 1

            if not _event_id:
                print("urace decompact: compaction_event_id required (positional or --target FIELD:latest)", file=sys.stderr)
                return 1

            if args.record_id:
                # Incremental decompaction: extract single record, read-only
                try:
                    record = engine.decompact_record(_event_id, args.record_id)
                except ValueError as exc:
                    print(f"urace decompact: {exc}", file=sys.stderr)
                    return 1
                if args.json:
                    _print_fmt({"status": "found", "record": record}, _fmt or "json")
                else:
                    print(f"Record '{args.record_id}' from event '{_event_id}':")
                    for k, v in record.items():
                        print(f"  {k}: {v}")
                return 0

            # Full decompaction: restore all records at next safe boundary
            field_path = getattr(args, "field_path", None)
            if field_path is None:
                manifest = _compaction_module.load_manifest(sp)
                if manifest is None:
                    print("urace decompact: no CompactionManifest found", file=sys.stderr)
                    return 1
                event = next(
                    (e for e in manifest["events"] if e.get("event_id") == _event_id or e.get("id") == _event_id),
                    None,
                )
                if event is None:
                    print(f"urace decompact: event '{_event_id}' not found", file=sys.stderr)
                    return 1
                field_path = event.get("field_path") or event.get("target_field")
            inp = queue_input(config, "decompact", {
                "kind": "decompact",
                "compaction_event_id": _event_id,
                "field_path": field_path,
            })
            if args.json:
                _print_fmt({"status": "queued", "input_id": inp["id"], "field_path": field_path}, _fmt or "json")
            else:
                print(f"Decompact queued (input {inp['id']}); '{field_path}' will be restored at next safe boundary.")
            return 0

        if args.command == "amend":
            engine = _compaction_module.CompactionEngine(sp)
            authorized_by = "operator:cli"

            # Resolve event_id + record_id from --target if provided
            _target_str = getattr(args, "target", None)
            _event_id = args.compaction_event_id
            _record_id = args.record_id
            if _target_str and (not _event_id or not _record_id):
                _resolved = _resolve_scope_target(_target_str, sp)
                if _resolved.get("error"):
                    print(f"urace amend: --target resolution error: {_resolved['error']}", file=sys.stderr)
                    return 1
                _event_id = _event_id or _resolved.get("resolved_id")
                # When --target RECORD-ID (no colon), field=record_id, predicate=None
                # When --target FIELD:RECORD-ID, predicate=record_id
                _record_id = _record_id or _resolved.get("predicate") or _resolved.get("field")

            if not _event_id or not _record_id:
                print("urace amend: compaction_event_id and record_id required (positional or --target RECORD-ID)", file=sys.stderr)
                return 1

            try:
                amendment = engine.amend_archived_record(
                    compaction_event_id=_event_id,
                    record_id=_record_id,
                    amendment_kind=args.kind,
                    amendment_note=args.notice,
                    authorized_by=authorized_by,
                    apply_fn=lambda r: {
                        **r,
                        "provenance_status": args.kind if args.kind != "CUSTOM" else r.get("provenance_status", "CURRENT"),
                        "revision_notice": args.notice,
                    },
                )
            except ValueError as exc:
                print(f"urace amend: {exc}", file=sys.stderr)
                return 1
            if args.json:
                _print_fmt({"status": "amended", "amendment": amendment}, _fmt or "json")
            else:
                print(f"Amendment written: {amendment['id']}")
                print(f"  record: {amendment['record_id']}")
                print(f"  kind: {amendment['amendment_kind']}")
            return 0

        if args.command == "why":
            from .. import decision_record as _dr_module
            config = load_config()
            state = load_state_for_read(config) or {}
            try:
                chain = _dr_module.traverse_reasoning_chain(
                    state, args.decision_id, max_depth=args.depth
                )
            except ValueError as exc:
                print(f"urace why: {exc}", file=sys.stderr)
                return 1
            why_limit = getattr(args, "limit", None)
            if why_limit is not None:
                chain = chain[:why_limit]
            if args.json:
                print(json.dumps({"chain": chain}, indent=2))
            else:
                for node in chain:
                    indent = "  " * node.get("depth", 0)
                    if node.get("cycle_detected"):
                        print(f"{indent}[cycle detected at {node['id']}]")
                    elif node.get("is_compacted"):
                        print(f"{indent}{node['id']} [compacted — use urace decompact to restore]")
                    else:
                        print(f"{indent}{node['id']} | {node.get('kind', '?')} | {node.get('decided_at', '?')[:10] if node.get('decided_at') else '?'}")
                        if node.get("subject"):
                            print(f"{indent}  subject: {node['subject']}")
                        if node.get("provenance_status") and node["provenance_status"] != "CURRENT":
                            print(f"{indent}  provenance: {node['provenance_status']}")
                        if node.get("reasoning_step_count", 0) > 0:
                            print(f"{indent}  reasoning_steps: {node['reasoning_step_count']}")
            return 0

    try:
        with state_lock(path):
            recovery = reconcile_transaction(config)
            if args.command == "init":
                if path.exists():
                    print("URACE already initialized")
                    return 0
                state = initial_state(config)
                from ..product_type_detector import detect_product_types, normalize_types
                raw_types = getattr(args, "product_type", None)
                if raw_types:
                    product_types = normalize_types(raw_types)
                else:
                    product_types = detect_product_types(Path.cwd())
                # backward-compat: also set product_type as first element for old readers
                product_type = product_types[0] if product_types else "software"
                _ptype = product_type
                if product_types != ["software"] or True:
                    import json as _jm
                    _base = _jm.loads(CONFIG_PATH.read_text())
                    _base["product_type"] = _ptype
                    _base["product_types"] = product_types
                    if _ptype in ("content", "media"):
                        _base.setdefault("default_metrics", ["engagement_rate", "quality_score", "reach"])
                        _base.setdefault("executor", {}).setdefault("context_hints", [])
                        _base["executor"]["context_hints"] = list({*_base["executor"].get("context_hints", []), f"product_type:{_ptype}", "quality_gate:score_delta>0", "content_pipeline:true"})
                    elif _ptype == "model":
                        _base.setdefault("default_metrics", ["accuracy", "latency_ms", "memory_mb"])
                    elif _ptype == "data":
                        _base.setdefault("default_metrics", ["completeness", "accuracy", "freshness"])
                    CONFIG_PATH.write_text(_jm.dumps(_base, indent=2, sort_keys=True) + "\n")
                save_state(config, state)
                write_stable_snapshot(config)
                write_runtime_snapshot(config)
                _types_label = ", ".join(product_types)
                print(f"Initialized {config['product']} at {path}" + (f" (types: {_types_label})" if product_types != ["software"] else ""))
                return 0
            state = load_state(config)
            if recovery:
                state = load_state(config)
            state.setdefault("metric_system", {"version": 1, "last_review_at": None, "last_assessment": "awaiting executor review", "change_needed": False, "change_history": []})
            state.setdefault("evaluation_system", {**config.get("evaluation_system", {}), "last_review_at": None, "last_assessment": "awaiting executor review", "change_needed": False, "change_history": []})
            state.setdefault("operator_patterns", config.get("operator_patterns", []))
            state.setdefault("pattern_memory", {})
            state.setdefault("reasoning_memory", [])
            if "self_evolution_policy" not in state:
                # §74: policy absent from durable state → MUST default to NECESSARY_ONLY
                # and MUST surface as a material named limitation pending operator confirmation.
                recovered_policy = config.get("self_evolution_policy", {
                    "mode": "NECESSARY_ONLY",
                    "source": "recovery default",
                    "provenance": "policy absent from durable state; NECESSARY_ONLY applied per §74 recovery requirement",
                })
                state["self_evolution_policy"] = recovered_policy
                state.setdefault("evidence", []).append({
                    "id": identifier("evidence"), "at": now(), "kind": "self-evolution-policy-migration",
                    "outcome": "RECORDED", "policy": state["self_evolution_policy"],
                })
                state.setdefault("blockers", []).append({
                    "at": now(), "last_at": now(), "scope": "self_evolution_policy",
                    "reason": "self-evolution policy was absent from durable state; NECESSARY_ONLY applied per §74 recovery requirement; confirm or explicitly set policy via urace configuration",
                    "count": 1,
                })
                save_state(config, state)
            if args.command == "reset":
                if not getattr(args, 'release_clean', False):
                    _out({"error": "specify --release-clean to reset state; future sub-commands will be added"})
                    return 2
                if not getattr(args, 'yes', False) and not getattr(args, 'json', False):
                    try:
                        _confirm = input("This will reset all state, disable improvement queues, and flush non-default settings.\nContinue? [y/N] ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        _confirm = "n"
                    if _confirm not in {"y", "yes"}:
                        print("Aborted.")
                        return 0
                # 1. Reset runtime state to initial defaults
                fresh_state = initial_state(config)
                save_state(config, fresh_state)
                # 2. Disable product improvement on all registered products
                try:
                    import json as _json_mod
                    _base = _json_mod.loads(CONFIG_PATH.read_text())
                    _improved_count = 0
                    for _entry in _base.get("product_registry", []):
                        if _entry.get("improvement_enabled", True):
                            _entry["improvement_enabled"] = False
                            _improved_count += 1
                    _atomic_json = lambda p, v: (p.parent.mkdir(parents=True, exist_ok=True), p.write_text(_json_mod.dumps(v, indent=2, sort_keys=True) + "\n"))
                    CONFIG_PATH.write_text(_json_mod.dumps(_base, indent=2, sort_keys=True) + "\n")
                except Exception:
                    _improved_count = 0
                _out({"status": "reset", "state_reset": True, "improvement_disabled_products": _improved_count, "note": "P2P exchange data is stored separately; use 'exchange reset --yes' to clear peer balances and listings"})
                return 0
            if args.command == "controls":
                _ctrl_verb = getattr(args, "controls_verb", None)
                _ctrl_cfg = load_config()
                _ctrl_caps = _ctrl_cfg.get("capability_flags", {})
                _ALL_CAP_KEYS = ("executor_enabled", "freeform_enabled", "machine_interface_enabled", "compress_enabled", "decompress_enabled", "p2p_mint_enabled", "p2p_sell_enabled", "p2p_borrow_enabled", "context_mint_enabled", "context_mint_objectives", "context_mint_evidence", "context_mint_decisions", "context_mint_operations", "context_mint_checkpoints", "compliance_mode")
                if _ctrl_verb == "show":
                    _show = {
                        "executor_enabled": _ctrl_cfg.get("executor", {}).get("enabled", False),
                        "freeform_enabled": _ctrl_caps.get("freeform_enabled", True),
                        "machine_interface_enabled": _ctrl_caps.get("machine_interface_enabled", True),
                        "compress_enabled": _ctrl_caps.get("compress_enabled", True),
                        "decompress_enabled": _ctrl_caps.get("decompress_enabled", True),
                        "p2p_mint_enabled": _ctrl_caps.get("p2p_mint_enabled", False),
                        "p2p_sell_enabled": _ctrl_caps.get("p2p_sell_enabled", False),
                        "p2p_borrow_enabled": _ctrl_caps.get("p2p_borrow_enabled", True),
                        "context_mint_enabled": _ctrl_caps.get("context_mint_enabled", False),
                        "context_mint_objectives": _ctrl_caps.get("context_mint_objectives", False),
                        "context_mint_evidence": _ctrl_caps.get("context_mint_evidence", False),
                        "context_mint_decisions": _ctrl_caps.get("context_mint_decisions", False),
                        "context_mint_operations": _ctrl_caps.get("context_mint_operations", False),
                        "context_mint_checkpoints": _ctrl_caps.get("context_mint_checkpoints", False),
                        "product_id_scope": getattr(args, "product_id", None),
                        "executor_id_scope": getattr(args, "executor_id", None),
                        "data_source_id_scope": getattr(args, "data_source_id", None),
                    }
                    _out(_show)
                    return 0
                # controls set
                _changed = {}
                for _k in _ALL_CAP_KEYS:
                    _v = getattr(args, _k, None)
                    if _v is not None:
                        _changed[_k] = _v
                if _changed:
                    import json as _jm
                    _base = _jm.loads(CONFIG_PATH.read_text())
                    if "executor_enabled" in _changed:
                        _base.setdefault("executor", {})["enabled"] = _changed.pop("executor_enabled")
                    _caps = _base.setdefault("capability_flags", {})
                    _caps.update(_changed)
                    CONFIG_PATH.write_text(_jm.dumps(_base, indent=2, sort_keys=True) + "\n")
                    # Item 3: governance audit trail
                    _state = load_state_for_read(_ctrl_cfg)
                    if _state is not None:
                        _state.setdefault("evidence", []).append({
                            "id": identifier("evidence"),
                            "at": now(),
                            "kind": "config-capability-change",
                            "changed": _changed,
                            "product_id_scope": getattr(args, "product_id", None),
                            "executor_id_scope": getattr(args, "executor_id", None),
                        })
                        save_state(_ctrl_cfg, _state)
                _out({"status": "updated", "changed": _changed})
                return 0
            if args.command == "doctor":
                # Item 4: urace doctor — system health check
                _dr_checks = []
                def _dr_check(name, status, detail=""):
                    _dr_checks.append({"check": name, "status": status, "detail": detail})
                # 1. Config loads without error
                try:
                    _dr_cfg = load_config()
                    _dr_check("config_loads", "OK")
                except Exception as _e:
                    _dr_check("config_loads", "ERROR", str(_e))
                    _dr_cfg = {}
                # 2. State initializable
                try:
                    _dr_state = load_state_for_read(_dr_cfg)
                    _dr_check("state_initializable", "OK" if _dr_state is not None else "WARN", "state is None" if _dr_state is None else "")
                except Exception as _e:
                    _dr_check("state_initializable", "ERROR", str(_e))
                # 3. Executor attached?
                _dr_exec_cfg = _dr_cfg.get("executor", {})
                if _dr_exec_cfg.get("enabled", False):
                    try:
                        _dr_exec = intelligent_executor.load(config=_dr_cfg)
                        _dr_check("executor_available", "OK" if _dr_exec else "WARN", "no executor returned" if not _dr_exec else "")
                    except Exception as _e:
                        _dr_check("executor_available", "WARN", str(_e))
                else:
                    _dr_check("executor_available", "WARN", "executor disabled")
                # 4. Exchange enabled? Identity exists?
                _dr_exch_cfg = _dr_cfg.get("exchange", {})
                if _dr_exch_cfg.get("enabled", False):
                    try:
                        from .. import peer_exchange as _dr_pe
                        _dr_xch = _dr_pe.Exchange(_dr_pe.directory(_dr_cfg))
                        _dr_id = _dr_xch.identity()
                        _dr_check("exchange_identity", "OK" if _dr_id.get("peer_id") else "WARN", "" if _dr_id.get("peer_id") else "no peer_id")
                    except Exception as _e:
                        _dr_check("exchange_identity", "WARN", str(_e))
                else:
                    _dr_check("exchange_identity", "WARN", "exchange disabled")
                # 5. capability_flags defaults sane
                _dr_caps = _dr_cfg.get("capability_flags", {})
                _dr_caps_ok = isinstance(_dr_caps, dict)
                _dr_check("capability_flags_sane", "OK" if _dr_caps_ok else "ERROR", "" if _dr_caps_ok else "capability_flags is not a dict")
                # 6. P2P exchange root dir accessible
                _dr_exch_root = _dr_exch_cfg.get("root") or str(ROOT / "exchange")
                if _dr_exch_cfg.get("enabled", False):
                    try:
                        _dr_exch_path = Path(_dr_exch_root)
                        if _dr_exch_path.exists():
                            _dr_check("exchange_root_accessible", "OK")
                        else:
                            _dr_check("exchange_root_accessible", "WARN", f"{_dr_exch_root!r} does not exist yet")
                    except Exception as _e:
                        _dr_check("exchange_root_accessible", "WARN", str(_e))
                else:
                    _dr_check("exchange_root_accessible", "WARN", "exchange disabled")
                # 7. Ledger size
                try:
                    _dr_lw = _ledger_size_warning(state_path(_dr_cfg))
                    if _dr_lw is not None:
                        _dr_check("ledger_size", "WARN", f"{_dr_lw['size_mb']} MB — {_dr_lw['action']}")
                    else:
                        _dr_check("ledger_size", "OK")
                except Exception as _e:
                    _dr_check("ledger_size", "INFO", str(_e))
                _dr_overall = "ERROR" if any(c["status"] == "ERROR" for c in _dr_checks) else ("WARN" if any(c["status"] == "WARN" for c in _dr_checks) else "OK")
                _dr_result = {"overall": _dr_overall, "checks": _dr_checks}
                if getattr(args, "doctor_json", False):
                    import json as _drj
                    print(_drj.dumps(_dr_result, indent=2))
                else:
                    print(f"doctor: {_dr_overall}")
                    for _c in _dr_checks:
                        _detail = f" — {_c['detail']}" if _c['detail'] else ""
                        print(f"  [{_c['status']:5s}] {_c['check']}{_detail}")
                return 0 if _dr_overall in ("OK", "WARN") else 1
            if args.command == "search":
                import re as _sre
                _entries = []
                _target_kind = getattr(args, "kind", None)
                _q = getattr(args, "query", None)
                try:
                    _q = _validate_freeform_query(_q, max_bytes=4096)
                except ValueError as _qerr:
                    _out({"error": str(_qerr)}); return 1
                _searched_at = now()
                if _target_kind == "p2p":
                    # Route to P2P audit ledger search
                    _xch_dir = config.get("exchange", {}).get("root") or str(ROOT / "exchange")
                    try:
                        from .. import peer_exchange as _pxc
                        _xch = _pxc.Exchange(_xch_dir)
                        _p2p_rows = _xch.audit_rows()
                        # include compressed archives
                        import zlib as _zl, base64 as _bl
                        _arch_dir = Path(_xch_dir) / "p2p_audit_archives"
                        if _arch_dir.exists():
                            for _af in sorted(_arch_dir.glob("*.json")):
                                try:
                                    _arch = json.loads(_af.read_text())
                                    _payload = _arch.get("payload")
                                    if _payload:
                                        _p2p_rows = json.loads(_zl.decompress(_bl.b64decode(_payload))) + _p2p_rows
                                except Exception:
                                    pass
                    except Exception:
                        _p2p_rows = []
                    if _q:
                        _fv2 = _sre.match(r'^(\w+)=(.+)$', _q.strip())
                        if _fv2:
                            _f2, _v2 = _fv2.group(1), _fv2.group(2)
                            _p2p_rows = [r for r in _p2p_rows if str(r.get(_f2, '')).lower() == _v2.lower()]
                        else:
                            _ql2 = _q.lower()
                            _p2p_rows = [r for r in _p2p_rows if _ql2 in json.dumps(r, sort_keys=True).lower()]
                    _p2p_rows = _p2p_rows[-args.limit:]
                    # redact context_snapshot from P2P equity grant rows — show only context_kinds_included
                    _safe_p2p_rows = []
                    for _pr in _p2p_rows:
                        if "context_snapshot" in _pr and not getattr(args, "detail", False):
                            _pr = dict(_pr); _pr.pop("context_snapshot", None)
                        _safe_p2p_rows.append(_pr)
                    _qhash = hashlib.sha256(_q.encode()).hexdigest() if _q else None
                    _out({"query": _q, "kind": "p2p", "kind_searched": "p2p", "entries": _safe_p2p_rows, "count": len(_safe_p2p_rows), "searched_at": _searched_at, "traceable": True, "auditable": True, "includes_archives": True})
                    # Audit CONTEXT_SEARCH event
                    if _q:
                        state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": _searched_at, "kind": "context-search", "query_hash": _qhash, "kind_searched": "p2p", "result_count": len(_safe_p2p_rows)})
                        save_state(config, state)
                    return 0
                _SEARCH_KINDS = {
                    "objective": state.get("objectives", []),
                    "operation": state.get("operations", []),
                    "evidence": state.get("evidence", []),
                    "decision": state.get("decision_records", []),
                    "checkpoint": state.get("checkpoints", []),
                    "blocker": state.get("blockers", []),
                }
                _sources = {_target_kind: _SEARCH_KINDS[_target_kind]} if _target_kind and _target_kind in _SEARCH_KINDS else _SEARCH_KINDS
                _kind_searched = _target_kind or "all"
                for _kind_name, _items in _sources.items():
                    for _item in (_items or []):
                        _item_copy = dict(_item)
                        _item_copy.setdefault("_kind", _kind_name)
                        _entries.append(_item_copy)
                if _q:
                    _fv = _sre.match(r'^(\w+)=(.+)$', _q.strip())
                    if _fv:
                        _f, _v = _fv.group(1), _fv.group(2)
                        _entries = [e for e in _entries if str(e.get(_f, '')).lower() == _v.lower()]
                    else:
                        _ql = _q.lower()
                        _entries = [e for e in _entries if _ql in json.dumps(e, sort_keys=True).lower()]
                _since = getattr(args, "since_date", None)
                if _since:
                    _entries = [e for e in _entries if str(e.get("at", e.get("created_at", ""))) >= _since]
                _search_scope = getattr(args, "search_scope", None)
                if _search_scope:
                    _entries = [e for e in _entries if e.get("scope") == _search_scope]
                _entries = _entries[-args.limit:]
                _qhash2 = hashlib.sha256(_q.encode()).hexdigest() if _q else None
                _out({"query": _q, "kind_searched": _kind_searched, "entries": _entries, "count": len(_entries), "searched_at": _searched_at, "traceable": True, "auditable": True})
                # Audit CONTEXT_SEARCH event
                if _q:
                    state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": _searched_at, "kind": "context-search", "query_hash": _qhash2, "kind_searched": _kind_searched, "result_count": len(_entries)})
                    save_state(config, state)
                return 0
            if args.command == "repair-controller":
                fault = {"component": args.component, "code": args.code, "phase": args.phase, "exception_class": args.exception_class}
                disposition = attempt_core_auto_repair(config, state, fault, confirmed_recurrence=args.confirmed_recurrence)
                print(json.dumps({"repair": disposition, "fault": fault}, sort_keys=True))
                return 75 if disposition == "ACTIVATE" else (0 if disposition in {"COMPLETE", "DEDUPLICATED"} else 2)
            if args.command == "executor-capacity":
                executor_state = state.setdefault("executor_state", {})
                if args.action == "defer":
                    retry_at = args.retry_at or datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + float(config.get("executor", {}).get("capacity_fallback_seconds", 18000)), timezone.utc).isoformat()
                    datetime.fromisoformat(retry_at)
                    executor_state.update({"available": False, "capacity_status": "WAITING_PROVIDER_CAPACITY", "capacity_retry_at": retry_at, "capacity_category": "PROVIDER_CAPACITY", "capacity_stage": args.stage, "availability_reason": "provider capacity window unavailable"})
                    disposition = "WAITING_PROVIDER_CAPACITY"
                else:
                    executor_state.pop("capacity_retry_at", None)
                    executor_state.update({"available": True, "capacity_status": "AVAILABLE", "availability_reason": "checkpointed Executor stage completed after capacity retry"})
                    disposition = "AVAILABLE"
                state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "executor-capacity-state", "status": disposition, "stage": args.stage})
                save_state(config, state)
                print(json.dumps({"executor_capacity": disposition}, sort_keys=True))
                return 0
            if args.command == "executor":
                settings = config.setdefault("executor", {})
                if args.action == "status":
                    health = intelligent_executor.availability(settings) if settings.get("enabled") else {"available": False, "reason": "detached"}
                    print(json.dumps({"kind": settings.get("kind"), "command": settings.get("command"), "attached": bool(settings.get("enabled")), **health}, indent=2))
                    return 0
                if args.action == "attach":
                    settings["enabled"] = True
                    if args.executor_binary:
                        settings["command"] = args.executor_binary
                    disposition = "ATTACHED"
                else:
                    settings["enabled"] = False
                    disposition = "DETACHED"
                atomic_write_json(CONFIG_PATH, config)
                state.setdefault("evidence", []).append({
                    "id": identifier("evidence"), "at": now(), "kind": "executor-configuration",
                    "outcome": disposition, "executor_kind": settings.get("kind"), "command": settings.get("command"),
                    "provenance": "repository owner CLI action",
                })
                save_state(config, state)
                write_runtime_snapshot(config)
                print(f"Executor {disposition.lower()}: {settings.get('kind')} ({settings.get('command')})")
                return 0
            restored = ensure_stable_product(config, state)
            if restored:
                state["lifecycle_state"] = "ASSESSING"
                save_state(config, state)
            if recovery == "ROLLED_FORWARD":
                write_stable_snapshot(config)
            if not (runtime_stable_path(config) / "manifest.json").exists():
                write_runtime_snapshot(config)
            if os.environ.get("URACE_POST_UPGRADE") == "1" and state.get("pending_runtime_activation"):
                state.setdefault("evidence", []).append({
                    "id": identifier("evidence"), "at": now(), "kind": "runtime-activation-health",
                    "transaction": state["pending_runtime_activation"]["transaction"], "outcome": "HEALTHY",
                })
                state["pending_runtime_activation"] = None
                state["restart_requested"] = False
                save_state(config, state)
                write_runtime_snapshot(config)
            if args.command == "check":
                surface = _build_inspection_surface(state, config)
                surface['preflight_hints'] = _preflight_hints
                if args.json:
                    print(json.dumps(surface, indent=2, sort_keys=True))
                else:
                    print(f"lifecycle_state: {surface['lifecycle_state']}")
                    print(f"summary:         {surface['summary']}")
                    blocking = surface.get("blocking_gaps", [])
                    if blocking:
                        print(f"blocking_gaps:   {len(blocking)}")
                        for g in blocking:
                            print(f"  [{g.get('kind')}] {g.get('detail', '')}")
                    warning = surface.get("warning_gaps", [])
                    if warning:
                        print(f"warning_gaps:    {len(warning)}")
                        for g in warning:
                            print(f"  [{g.get('kind')}] {g.get('detail', '')}")
                    if _preflight_hints:
                        print(f"preflight_hints: {len(_preflight_hints)}")
                        for _h in _preflight_hints:
                            print(f"  [{_h['level']}] {_h['message']} — {_h['action']}")
                if args.fail_on:
                    _severity_order = {"INFO": 0, "WARNING": 1, "BLOCKING": 2}
                    _threshold = _severity_order.get(args.fail_on, 999)
                    _active_gaps = [g for g in state.get("integrity_gaps", []) if g.get("active", True)]
                    if any(_severity_order.get(g.get("severity", "INFO"), 0) >= _threshold for g in _active_gaps):
                        return 1
                return 0
            if args.command == "vitals":
                snapshot = vitals_snapshot(config, state)
                print(json.dumps(snapshot, indent=2, sort_keys=True) if args.json else render_vitals(snapshot))
                if args.fail_on:
                    _severity_order = {"INFO": 0, "WARNING": 1, "BLOCKING": 2}
                    _threshold = _severity_order.get(args.fail_on, 999)
                    _active_gaps = [g for g in state.get("integrity_gaps", []) if g.get("active", True)]
                    if any(_severity_order.get(g.get("severity", "INFO"), 0) >= _threshold for g in _active_gaps):
                        return 1
                return 0
            count = 1 if args.command == "plan" else args.cycles
            portfolio_owner = None
            portfolio_restart_after = 0.0
            if args.command == "auto":
                emit_auto_startup(args.json, args.quiet)
            _apply_customizations(state, config)
            if args.command == "auto" and state.get("lifecycle_state") == "PAUSED":
                state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(), "kind": "lifecycle-resumed", "disposition": "AUTONOMOUS_RESUME_FROM_PAUSED"})
                state.setdefault("status_transitions", []).append({"status": "ASSESSING", "from_status": "PAUSED", "at": now(), "reason": "AUTONOMOUS_RESUME_FROM_PAUSED", "source": "cli:auto"})
                state["lifecycle_state"] = "ASSESSING"
                save_state(config, state)
            if args.command == "auto":
                _manifest = state.get("executor_state", {}).get("recovery_manifest")
                if _manifest:
                    print(
                        f"[recovery] resuming from manifest {_manifest['manifest_id']} "
                        f"(cause: {_manifest['emission_cause']}, "
                        f"progress: {_manifest.get('progress_at_emit')}, "
                        f"delta: {_manifest.get('goal_delta', 'unknown')})",
                        file=sys.stderr,
                    )
            if args.command == "auto" and args.force_discovery:
                force_id = identifier("manual")
                state.setdefault("executor_state", {})["discovery_trigger"] = {"reason": "manual force-discovery", "signature": force_id}
                state["executor_state"]["last_discovery_at"] = None
                state.setdefault("evidence", []).append({
                    "id": identifier("evidence"), "at": now(), "kind": "force-discovery-override",
                    "trigger_signature": force_id,
                    "attribution": "operator invoked --force-discovery; bypasses DISCOVERY_YIELD_EXHAUSTED gate for one cycle; streak not reset",
                    "disposition": "ATTRIBUTED_OPERATOR_OVERRIDE",
                })
            outcomes = []
            last_outcome = None
            index = 0
            last_persisted_at = datetime.fromisoformat(state.get("updated_at", now())).timestamp()
            _report_enabled = args.command == "auto" and getattr(args, "report", False)
            if _report_enabled:
                _report_before = {
                    "operations": len(state.get("operations", [])),
                    "active_objectives": len([o for o in state.get("objectives", []) if o.get("status") == "active"]),
                    "version": state.get("version", 0),
                    "cache_hits": state.get("executor_state", {}).get("cache_hits", 0),
                    "executor_calls": len(state.get("executor_state", {}).get("executor_calls", [])),
                }
            while count == 0 or index < count:
                if args.command == "auto" and count == 0 and time.monotonic() >= portfolio_restart_after and (portfolio_owner is None or portfolio_owner.poll() is not None):
                    portfolio_owner = start_default_portfolio_owner(config, quiet=args.quiet, json_mode=args.json)
                    portfolio_restart_after = time.monotonic() + 300
                    if portfolio_owner is not None and not args.quiet:
                        print("Adaptive portfolio comparison is attached; it will run only while its expected value justifies the added cost.", file=sys.stderr, flush=True)
                before_material = material_state_signature(state)
                _cycle_start_at = now()
                consumed_inputs = consume_inputs(config, state)
                # AP18 — check scheduled tasks
                _check_scheduled_tasks(state, config)
                # Check P2P free-use features as potential implementations before executing
                if args.command == "auto" and config.get('capability_flags', {}).get('p2p_borrow_enabled', True):
                    try:
                        _p2p_ctx = freeform_routing._p2p_free_features(config)
                        if _p2p_ctx:
                            state.setdefault('context_inputs', []).append({
                                'id': identifier('context'),
                                'at': now(),
                                'kind': 'p2p-free-feature-hint',
                                'features': [f['feature_id'] for f in _p2p_ctx[:10]],
                                'note': 'Free-use P2P features available — consider borrowing before executor use',
                            })
                    except Exception:
                        pass
                last_outcome = cycle(config, state, allow_execution=args.command != "plan")
                portfolio_activity = attached_portfolio_activity(config, portfolio_owner)
                if last_outcome.get("outcome") == "dormant" and portfolio_activity:
                    state["lifecycle_state"] = "ACTIVE"
                    last_outcome = {
                        "outcome": "delegated_portfolio",
                        "reason": "adaptive portfolio comparison is actively planning, mutating or evaluating",
                        "portfolio": portfolio_activity,
                    }
                    state["last_cycle"] = {"at": now(), **last_outcome}
                if count:
                    outcomes.append(last_outcome)
                efficiency_state = state.setdefault("runtime_efficiency", {"cycles": 0, "durable_writes": 0, "suppressed_writes": 0})
                efficiency_state["cycles"] = int(efficiency_state.get("cycles", 0)) + 1
                heartbeat = float(config.get("efficiency", {}).get("dormant_state_heartbeat_seconds", 300))
                material_changed = before_material != material_state_signature(state)
                persist_cycle = bool(count or consumed_inputs or material_changed or time.time() - last_persisted_at >= heartbeat)
                if persist_cycle:
                    efficiency_state["durable_writes"] = int(efficiency_state.get("durable_writes", 0)) + 1
                    # AP12 — emit OrchestratorRecord for this cycle
                    try:
                        from urace._common import orchestrator_record as _orch_record
                        from urace import primitives as _prim_orch
                        _orch = _orch_record(
                            "cycle", _cycle_start_at, ["cycle"], "COMPLETED",
                            completed_at=now(), postconditions_met=True,
                        )
                        _prim_orch.validate_orchestrator_record(_orch)
                        state.setdefault("evidence", []).append({
                            "id": identifier("evidence"),
                            "at": now(),
                            "kind": "orchestrator-completed",
                            "source": "cli:cycle",
                            "detail": "cycle orchestrator completed",
                        })
                    except Exception:
                        pass
                    _update_progress_vector(state)
                    save_state(config, state)
                    _crc_to_save = state.get("cognitive_resume_context")
                    if _crc_to_save:
                        try:
                            cognitive_resume_module.save(str(state_path(config).parent), _crc_to_save)
                        except Exception:
                            pass
                    refresh_analytics(config, state)
                    cleanup_consumed_inputs(consumed_inputs)
                    last_persisted_at = time.time()
                else:
                    efficiency_state["suppressed_writes"] = int(efficiency_state.get("suppressed_writes", 0)) + 1
                journal_path = transaction_path(config)
                if journal_path.exists():
                    journal = json.loads(journal_path.read_text(encoding="utf-8"))
                    if transaction_is_accepted(state, journal["id"]):
                        write_stable_snapshot(config)
                finalize_committed_transaction(config, state)
                emit_cycle_feedback(
                    state, last_outcome, index + 1,
                    bool(getattr(args, "json", False)),
                    bool(getattr(args, "quiet", False)),
                    bool(getattr(args, "verbose", False)),
                )
                if state.get("restart_requested"):
                    return 75
                try:
                    from urace.telemetry import emit_cycle_span
                    from urace.resource_usage import product_identity as _pid
                    emit_cycle_span(
                        outcome=str(last_outcome.get("outcome", "unknown")),
                        index=index + 1,
                        product_id=_pid(config),
                        cycles_total=count,
                        version=int(state.get("version", 0)),
                        cache_hits=int(state.get("executor_state", {}).get("cache_hits", 0)),
                        executor_calls=len(state.get("executor_state", {}).get("executor_calls", [])),
                    )
                except Exception:
                    pass
                index += 1
                interval = getattr(args, "interval", 0)
                if interval and (count == 0 or index < count):
                    time.sleep(interval)
            payload: Any = outcomes[0] if len(outcomes) == 1 else outcomes
            if _report_enabled:
                _report_after = {
                    "operations": len(state.get("operations", [])),
                    "active_objectives": len([o for o in state.get("objectives", []) if o.get("status") == "active"]),
                    "version": state.get("version", 0),
                    "cache_hits": state.get("executor_state", {}).get("cache_hits", 0),
                    "executor_calls": len(state.get("executor_state", {}).get("executor_calls", [])),
                }
                _improvement_report = {
                    "schema": "urace-improvement-report-v1",
                    "cycles_completed": index,
                    "before": _report_before,
                    "after": _report_after,
                    "delta": {k: _report_after[k] - _report_before[k] for k in _report_before},
                }
                print(json.dumps(_improvement_report, ensure_ascii=False))
            if args.json:
                print(json.dumps({"type": "autonomous_run_complete", "cycles": len(outcomes), "outcomes": payload}, sort_keys=True))
            else:
                print(render(state))
            return 0
    except KeyboardInterrupt:
        try:
            _stop_config = load_config()
            _stop_state = load_state_for_read(_stop_config)
            _unresolved = len(_stop_state.get("unresolved_effects", [])) if _stop_state else 0
            _inbox_files = sorted(input_directory(_stop_config).glob("*.json")) if _stop_state else []
            print("\nURACE stopped; completed cycles are durable", file=sys.stderr)
            if _unresolved:
                print(f"  unresolved effects: {_unresolved} (will remain blocked until reconciled)", file=sys.stderr)
            if _inbox_files:
                print(f"  queued inbox inputs: {len(_inbox_files)} (will be applied on next start)", file=sys.stderr)
                for _f in _inbox_files[:10]:
                    print(f"    {_f.name}", file=sys.stderr)
        except Exception:
            print("\nURACE stopped; completed cycles are durable", file=sys.stderr)
        return 130
    except Exception as error:
        fault = core_fault_descriptor(error, getattr(args, "command", "unknown"))
        if fault is not None:
            try:
                repair_state = load_state(config)
                disposition = attempt_core_auto_repair(config, repair_state, fault)
                print(f"urace: trusted controller fault {fault['code']}; recovery={disposition}", file=sys.stderr)
                if disposition == "RETRY":
                    return 76
                if disposition == "ACTIVATE":
                    return 75
                if disposition == "FAILED" and getattr(args, "command", None) == "auto":
                    _emit_recovery_manifest(repair_state, "repair-exhausted", "auto")
                    repair_state["lifecycle_state"] = "DORMANT"
                    save_state(config, repair_state)
                    print("urace: repair-exhausted in auto mode; RecoveryManifest emitted; next urace auto will resume", file=sys.stderr)
                    return 0
            except Exception as recovery_error:
                print(f"urace: controller recovery failed closed ({type(recovery_error).__name__})", file=sys.stderr)
        print(f"urace: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
