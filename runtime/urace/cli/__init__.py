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
    _render_report_html, _print_fmt,
    _validate_freeform_query, _resolve_scope_target,
)
from ..cli_error import cli_error
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
    _routing_decision, cycle, emit_cycle_feedback, emit_auto_startup,
)

# ── Reporting commands (extracted) ───────────────────────────────────────────
from .commands.reporting import (
    _cmd_usage, _cmd_cost, _cmd_help,
    _cmd_export, _cmd_import, _cmd_report_bare, _cmd_audit,
    _cmd_commands, _cmd_portfolio, _cmd_report, _cmd_auto_dry_run,
)

# ── Config commands (extracted) ───────────────────────────────────────────────
from .commands.config import (
    _cmd_executor_skills_config, _cmd_runtime_improvement_config,
    _cmd_github_workflow_config, _cmd_auto_milestones_config,
    _cmd_decision_feedback_config, _cmd_value_discovery_config,
    _cmd_executor_options, _cmd_auto_goals_effort,
    _cmd_configuration_self_evolution, _cmd_schema,
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
    "start", "stop", "run", "reload",
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
    # P2P network (primary) and legacy alias
    "network", "exchange",
    # github / git / gh integration
    "github", "git", "gh",
    # binary content references
    "content",
    # usage analytics
    "usage",
}

_KNOWN_TOP_COMMANDS -= command_surface.PHANTOMS

_SEVERITY_ORDER: dict[str, int] = {"INFO": 0, "WARNING": 1, "BLOCKING": 2}

def _lev1(a: str, b: str) -> bool:
    """True if Damerau-Levenshtein distance between a and b is exactly 1."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diffs = [i for i, (x, y) in enumerate(zip(a, b, strict=False)) if x != y]
        if len(diffs) == 1:
            return True
        # adjacent transposition: "relaod" ↔ "reload"
        if (len(diffs) == 2 and diffs[1] == diffs[0] + 1
                and a[diffs[0]] == b[diffs[1]] and a[diffs[1]] == b[diffs[0]]):
            return True
        return False
    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    i = j = diff = 0
    while i < len(shorter) and j < len(longer):
        if shorter[i] != longer[j]:
            diff += 1
            if diff > 1:
                return False
            j += 1
        else:
            i += 1; j += 1
    return True

# Genuine synonym/redirect table — trivial tokenizations removed (handled by
# space-split normalization + Tier 1b).  Only real redirects live here.
_SD_SYNONYMS: dict[str, list[str]] = {
    # bare commands → default subcommand
    "feedback": ["feedback", "list"],
    "rules":    ["rules",    "list"],
    # extra-word disambiguation
    "vitals check":  ["vitals"],
    "check status":  ["check"],
    # Note: declare aliases are intentionally NOT in _SD_SYNONYMS so that
    # `declare context/goal/etc.` passes through argparse to _cmd_declare,
    # which prints the deprecation warning before re-dispatching to add.
}

# _SD_TRUE_EXACT: superset mapping used by tests for introspection.
# Contains all canonical two-word exact routes (SD=True) and deprecated aliases.
_SD_TRUE_EXACT: dict[str, list[str]] = {
    # single-word direct mappings
    "check":   ["check"],
    "vitals":  ["vitals"],
    "pause":   ["pause"],
    "resume":  ["resume"],
    "help":    ["help"],
    "rules":   ["rules", "list"],
    "status":  ["status"],
    "stop":    ["pause"],
    "start":   ["resume"],
    # two-word exact patterns
    "rules list":       ["rules", "list"],
    "rules graph":      ["rules", "graph"],
    "rules conflicts":  ["rules", "conflicts"],
    "change list":      ["change", "list"],
    "goal list":        ["goal", "list"],
    "vitals check":     ["vitals"],
    "check status":     ["check"],
    # onboard / product / fleet exact patterns
    "onboard status":   ["onboard", "status"],
    "onboard confirm":  ["onboard", "confirm"],
    "product list":     ["product", "list"],
    "product status":   ["product", "status"],
    "fleet status":     ["fleet", "status"],
    "fleet run":        ["fleet", "run"],
    "fleet stop":       ["fleet", "stop"],
    "fleet broadcast":  ["fleet", "broadcast"],
    # r73 new commands
    "evidence list":          ["evidence", "list"],
    "blocker list":           ["blocker", "list"],
    "blocker resolve":        ["blocker", "resolve"],
    "decision list":          ["decision", "list"],
    "decision inspect":       ["decision", "inspect"],
    "integrity-signal list":  ["integrity-signal", "list"],
    "govern list-gates":      ["govern", "list-gates"],
    "govern clear":           ["govern", "clear"],
    # r75 trace
    "trace list":    ["trace", "list"],
    "trace inspect": ["trace", "inspect"],
    # r77 schema + feedback
    "schema list":    ["schema", "list"],
    "schema inspect": ["schema", "inspect"],
    "schema export":  ["schema", "export"],
    "feedback list":  ["feedback", "list"],
    # r85 resource budget
    "resource status": ["resource", "status"],
    "resource report": ["resource", "report"],
    "resource help":   ["resource", "help"],
    # r86 help subcommand routing
    "inbox help":    ["inbox", "help"],
    "onboard help":  ["onboard", "help"],
    "product help":  ["product", "help"],
    "fleet help":    ["fleet", "help"],
    "trace help":    ["trace", "help"],
    "feedback help": ["feedback", "help"],
    "update help":   ["update", "help"],
    "schema help":   ["schema", "help"],
    # r93 api command routing
    "api help":  ["api", "help"],
    "api call":  ["api", "call"],
    "api batch": ["api", "batch"],
    # r98 api extensions
    "api watch":   ["api", "watch"],
    "api version": ["api", "version"],
    # r101: add subcommands (canonical)
    "add context":  ["add", "context"],
    "add goal":     ["add", "goal"],
    "add source":   ["add", "source"],
    "add metric":   ["add", "metric"],
    "add vital":    ["add", "vital"],
    "add evidence": ["add", "evidence"],
    # backwards compat: declare aliases → add (r100 deprecated forms)
    "declare context": ["add", "context"],
    "declare goal":    ["add", "goal"],
    "declare source":  ["add", "source"],
    "declare metric":  ["add", "metric"],
    "declare vital":   ["add", "vital"],
}

_INTENT_KEYWORDS: dict[str, frozenset[str]] = {
    "status decisions": frozenset({"decision", "decisions", "decide", "chose", "choice", "choices", "why", "changed"}),
    "status goals":     frozenset({"goal", "goals", "objective", "objectives", "aim", "aims", "target", "targets"}),
    "status vitals":    frozenset({"vital", "vitals", "metric", "metrics", "health", "credit", "score", "scores"}),
    "status blockers":  frozenset({"blocked", "blocker", "blockers", "blocking", "stuck", "obstacle", "obstacles"}),
    "status plan":      frozenset({"plan", "plans", "planning", "next", "strategy", "roadmap", "scheduled"}),
    "status watch":     frozenset({"watch", "watching", "activity", "happening", "working", "live", "current"}),
}

def _match_intent(tokens: list[str]) -> list[str] | None:
    """Token-overlap intent scoring — no LLM, no library.

    Returns the best-matching argparse route if ≥50% of meaningful query
    tokens match a known intent's keyword set. Returns None to fall through
    to Tier 2 (LLM classify) if ambiguous.
    """
    # Only fire for multi-token inputs that look like NL (not bare commands)
    if len(tokens) < 2:
        return None
    lower_tokens = [t.lower() for t in tokens]
    # Exclude question/filler words from scoring denominator
    _FILLERS = {"what", "show", "me", "my", "are", "is", "the", "a", "an", "i", "list", "get",
                "recent", "latest", "current", "today", "now", "all", "see", "tell"}
    meaningful = [t for t in lower_tokens if t not in _FILLERS and t.isalpha()]
    if not meaningful:
        return None
    best_route, best_score = None, 0.0
    for route, kws in _INTENT_KEYWORDS.items():
        hits = sum(1 for t in meaningful if t in kws)
        score = hits / len(meaningful)
        if score > best_score:
            best_score, best_route = score, route
    if best_score >= 0.5 and best_route:
        return best_route.split()
    return None

_RE_SEPARATORS = __import__('re').compile(r'[/_]+')
_RE_LEADING_SPECIAL = __import__('re').compile(r'^[@#!]+')

def _preprocess_args(raw_args: list[str]) -> list[str]:
    """NLP routing — deterministic fast path, LLM fallback.

    Tier 0:   /command               → direct, zero cost
    Tier 1b:  exact known command    → argparse pass-through (bare → default expansion)
    Tier 1:   SD synonym match       → direct route
    Tier 1c:  normalization          → case, punct, separators, leading chars, concat split
    Tier 1.5: intent scoring         → NL status queries, no LLM
    Tier 1d:  fuzzy match            → Lev-1 + Damerau transposition + prefix on first token
    Tier 2:   everything else        → executor classify (LLM)
    """
    if len(raw_args) >= 2 and raw_args[0] in ('status', '/status') and raw_args[1] == 'scores':
        return ['trial', 'status', 'scores', *raw_args[2:]]
    if not raw_args or (raw_args[0].startswith("-") and raw_args[0] not in {"--json", "--format"}
                        and not raw_args[0].startswith("--format=")):
        return raw_args
    first = raw_args[0]
    rest = list(raw_args[1:])

    # Peel leading --json/--format flags and re-enter
    if first in {"--json", "--format"} or first.startswith("--format="):
        prefix = []
        remaining = list(raw_args)
        while remaining:
            if remaining[0] == "--json" or remaining[0].startswith("--format="):
                prefix.append(remaining.pop(0))
            elif remaining[0] == "--format" and len(remaining) > 1:
                prefix.extend([remaining.pop(0), remaining.pop(0)])
            else:
                break
        return prefix + _preprocess_args(remaining) if remaining else raw_args

    # Space-split: single arg containing spaces → split and re-enter.
    # Guard: only when first token is a known command and string has ≤3 tokens total,
    # preventing NL prose like "pause the task if the deploy fails" being split.
    if not rest and ' ' in first and not first.startswith('/'):
        _parts = first.split()
        if (len(_parts) <= 3
                and _parts[0].lower() in _KNOWN_TOP_COMMANDS
                and all(re.match(r'^[a-zA-Z][a-zA-Z0-9\-]{0,29}$', p) for p in _parts)):
            return _preprocess_args(_parts)

    # Routing flags in prose → classify with trailing flags preserved
    if first not in _KNOWN_TOP_COMMANDS and first.lstrip("/") not in _KNOWN_TOP_COMMANDS:
        for index, token in enumerate(raw_args[1:], 1):
            if token in {"--json", "--format", "--confirm", "--selection", "--p2p-asset"} \
                    or token.startswith(("--format=", "--selection=", "--p2p-asset=")):
                text = " ".join(raw_args[:index])
                return ["classify", text[1:] if text.startswith("/") else text, *raw_args[index:]]

    # ── Tier 0: slash-prefixed ───────────────────────────────────────────────
    if first.startswith("/"):
        stripped = first[1:]
        if stripped in _KNOWN_TOP_COMMANDS:
            return [stripped] + rest
        free_text = (stripped + " " + " ".join(rest) if rest else stripped).strip()
        sd = _SD_SYNONYMS.get(free_text.lower())
        return list(sd) if sd is not None else ["classify", free_text]

    # ── Tier 1b: exact known command ─────────────────────────────────────────
    if first in _KNOWN_TOP_COMMANDS:
        if not rest:
            # bare command: check for default subcommand expansion
            _bare = _SD_SYNONYMS.get(first)
            return list(_bare) if _bare is not None else raw_args
        # check two-token synonym (e.g. "vitals check" → ["vitals"], "declare goal" → ["add", "goal"])
        _two = _SD_SYNONYMS.get(first + " " + rest[0].lower())
        if _two is not None:
            return list(_two) + list(rest[1:])
        # normalize first subcommand token (handles "Blocker List" → ["blocker", "list"])
        norm_rest = [rest[0].lower() if rest[0].isalpha() else rest[0]] + rest[1:]
        return [first] + norm_rest

    first_lower = first.lower()

    # ── Tier 1c: surface normalisation (applied to first token) ─────────────
    # 1. Strip leading special characters (@status → status, #reload → reload)
    _clean = _RE_LEADING_SPECIAL.sub('', first_lower)
    if _clean != first_lower and _clean:
        return _preprocess_args([_clean] + rest)

    # 2. Strip trailing punctuation (status! → status)
    # Guard: single-word tokens only — multi-word NL prose may end with ? . etc.
    _trail = first_lower.rstrip("!.,;:?")
    if _trail != first_lower and _trail and ' ' not in first_lower:
        return _preprocess_args([_trail] + rest)

    # 3. Mixed case (Status → status)
    if first_lower in _KNOWN_TOP_COMMANDS:
        return _preprocess_args([first_lower] + rest)

    # ── Tier 1: SD synonym match on full phrase ──────────────────────────────
    full = " ".join(raw_args).strip()
    sd = _SD_SYNONYMS.get(full.lower())
    if sd is not None:
        return list(sd)

    # 4. Separator normalization: status/goals, status_goals → status goals
    #    Only on single-token with no spaces to avoid splitting multi-word NL input
    if not rest and not first_lower.startswith("-") and ' ' not in first_lower:
        _sep_norm = _RE_SEPARATORS.sub(' ', first_lower).strip()
        if ' ' in _sep_norm:
            _parts = _sep_norm.split()
            if _parts[0] in _KNOWN_TOP_COMMANDS:
                return [_parts[0]] + _parts[1:]
            sd2 = _SD_SYNONYMS.get(_sep_norm)
            if sd2 is not None:
                return list(sd2)

    # 5. Concat split: statusnetwork → status network (only for no-space tokens)
    if not rest and len(first_lower) >= 6 and ' ' not in first_lower:
        for split in range(2, len(first_lower) - 1):
            head, tail = first_lower[:split], first_lower[split:]
            if head in _KNOWN_TOP_COMMANDS:
                return [head, tail]
            sd3 = _SD_SYNONYMS.get(head + " " + tail)
            if sd3 is not None:
                return list(sd3)

    # ── Tier 1.5: intent scoring (NL status queries, no LLM) ─────────────────
    _intent = _match_intent(raw_args)
    if _intent is not None:
        return _intent

    # ── Tier 1d: fuzzy first-token match (all arg counts) ────────────────────
    # Fires on first token whether the input is 1 or many tokens.
    # Guard: same first char + length ≥ 3 → avoids false positives on short prose words.
    if len(first_lower) >= 3 and first_lower[0].isalpha():
        # Lev-1 + Damerau transposition
        for cmd in _KNOWN_TOP_COMMANDS:
            if first_lower[0] == cmd[0] and _lev1(first_lower, cmd):
                return [cmd] + rest
        # Unambiguous prefix expansion (e.g. "sto" → "stop", "rel" → "reload")
        _prefix_matches = [cmd for cmd in _KNOWN_TOP_COMMANDS if cmd.startswith(first_lower)
                           and len(first_lower) >= 3]
        if len(_prefix_matches) == 1:
            return [_prefix_matches[0]] + rest

    # ── Tier 2: LLM executor classification ──────────────────────────────────
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








# ── Integrations commands (extracted) ───────────────────────────────────────
from .commands.integrations import (
    _cmd_features, _cmd_rollback, _cmd_peer_review, _cmd_similarity,
    _cmd_p2p, _cmd_product_create, _cmd_product_exchange, _cmd_network_exchange,
    _cmd_crypto, _cmd_qualification,
)

# ── Governance commands (extracted) ──────────────────────────────────────────
from .commands.governance import (
    _cmd_evidence, _cmd_blocker, _cmd_decision, _cmd_integrity_signal,
    _cmd_govern, _cmd_inbox, _cmd_onboard,
)

# ── Runtime commands (extracted) ─────────────────────────────────────────────
from .commands.runtime import (
    _cmd_trial, _cmd_watch, _cmd_change, _cmd_update,
    _cmd_run, _cmd_start, _cmd_stop, _cmd_reload,
    _cmd_shell_dashboard, _cmd_daemon, _cmd_m2m,
)

# ── Product commands (extracted) ─────────────────────────────────────────────
from .commands.product import (
    _cmd_content, _cmd_product_work, _cmd_product_improvements,
    _cmd_product, _cmd_fleet,
)

# ── Metrics commands (extracted) ─────────────────────────────────────────────
from .commands.metrics import (
    _cmd_data, _cmd_trace, _cmd_feedback, _cmd_resource,
    _cmd_executor_status, _cmd_check_vitals,
    _cmd_quality, _cmd_compliance, _cmd_milestone, _cmd_source_metric_vital_goal,
    _cmd_policy, _cmd_budget, _cmd_evaluation,
    _cmd_executor_circuit_breaker, _cmd_executor_attach_detach,
    _cmd_pause, _cmd_resume,
)







# ── Work commands (extracted) ─────────────────────────────────────────────
from .commands.work import (
    _cmd_github, _cmd_git, _cmd_gh, _cmd_api, _cmd_web, _cmd_derive,
    _cmd_context, _cmd_classify, _cmd_add, _cmd_declare, _cmd_add_shorthand,
    _cmd_intent, _cmd_constraint, _cmd_explain, _cmd_rules,
    _cmd_compact_decompact_amend_why_crc,
)



# Ordered list of façade handlers tried in sequence.  Each handler returns an
# int exit code when it owns the command, or None to pass through to the next.
_FACADE_HANDLERS = [
    _cmd_features,
    _cmd_rollback,
    _cmd_peer_review,
    _cmd_similarity,
    _cmd_p2p,
    _cmd_product_create,
    _cmd_product_exchange,
    _cmd_network_exchange,
    _cmd_executor_skills_config,
    _cmd_runtime_improvement_config,
    _cmd_crypto,
    _cmd_qualification,
    # config block handled inline in main() — not in this list
    _cmd_content,
    _cmd_github_workflow_config,
    _cmd_auto_milestones_config,
    _cmd_decision_feedback_config,
    _cmd_value_discovery_config,
    _cmd_product_work,
    _cmd_product_improvements,
    _cmd_trial,
]


def _run_facade_handlers(
    handlers: list,
    args: Any,
    parser: Any,
    config: dict[str, Any],
    state: dict[str, Any],
    fmt: str | None,
    unknown: list[str],
    raw_args: list[str],
) -> int | None:
    """Try each handler in order; return the first non-None result."""
    for handler in handlers:
        result = handler(args, parser, config, state, fmt, unknown, raw_args)
        if result is not None:
            return result
    return None


def main(argv: list[str] | None = None, _config: dict | None = None) -> int:
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
        # First-run guard: if URACE has never been initialized, guide the user.
        try:_bare_cfg=load_config()
        except Exception:_bare_cfg={}
        _bare_sp=state_path(_bare_cfg)
        _initialized=_bare_sp.exists() and _bare_sp.stat().st_size>10
        if not _initialized:
            from ..inspection import top_level_help as _tlh
            print(_tlh())
            print('\nURACE is not initialized. Run:  urace init')
            return 1
        if hasattr(_sys.stdout,'isatty') and _sys.stdout.isatty():
            from .. import _daemon as _dm, shell as _sh
            _pid=_dm._read_pid(_bare_cfg)
            if not _pid or not _dm._is_running(_pid):
                import argparse as _ap2, threading as _thr2, time as _t2
                _da=_ap2.Namespace(command='daemon',daemon_action='start',
                                   json=False,format=None,interval_minutes=30.0,
                                   max_cycles=0,cycles=0)
                _thr2.Thread(target=_dm.dispatch,args=(_da,_bare_cfg),daemon=True).start()
                _t2.sleep(0.3)  # let daemon write pid before shell checks status
            return _sh.run_shell(_bare_cfg)
        else:
            from .. import tui as _tui
            return _tui.launch(_bare_cfg,SYSTEM_ROOT)
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
    from .. import preflight as _preflight_module
    try:_pf_cfg=load_config()
    except Exception:_pf_cfg={}
    _preflight_hints=_preflight_module.hints(_pf_cfg,SYSTEM_ROOT)
    if not args.json and _preflight_hints:
        for _h in _preflight_hints:print(f"hint [{_h['level']}]: {_h['message']} — {_h['action']}",file=sys.stderr)
    if 'config' not in vars():
        try:
            config = _pf_cfg or load_config()
        except Exception:
            config = {}
    if 'state' not in vars():
        try:
            state = load_state_for_read(config) or {}
        except Exception:
            state = {}
    _r = _run_facade_handlers(
        _FACADE_HANDLERS[:12], args, parser, config, state, _fmt, _unknown, raw_args
    )
    if _r is not None:
        return _r
    if args.command == 'config':
        from .. import config_schema as _cs
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
        if args.config_verb == 'validate':
            import json as _jm
            _file = getattr(args, 'config_file', None)
            try:
                _raw = (_jm.loads(Path(_file).read_text()) if _file
                        else _jm.loads(CONFIG_PATH.read_text()))
            except (OSError, _jm.JSONDecodeError) as _e:
                _out = {'status': 'error', 'error': str(_e)}
                print(json.dumps(_out) if args.json else f'error: {_e}')
                return 1
            _errors = _cs.validate(_raw)
            if args.json:
                print(json.dumps({'status': 'ok' if not _errors else 'invalid', 'errors': _errors}, indent=2))
            elif _errors:
                for _err in _errors:
                    print(f"  {_err['path']}: {_err['error']}")
            else:
                print('config ok')
            return 0 if not _errors else 1
        if args.config_verb == 'get':
            _cfg = load_config()
            try:
                _val = _cs.get_value(_cfg, args.key)
            except KeyError:
                _msg = f'{args.key}: key not found'
                print(json.dumps({'status': 'error', 'error': _msg}) if args.json else _msg)
                return 1
            if args.json:
                print(json.dumps({'status': 'ok', 'key': args.key, 'value': _val}))
            else:
                print(json.dumps(_val) if not isinstance(_val, str) else _val)
            return 0
        if args.config_verb == 'set':
            import json as _jm
            _base = _jm.loads(CONFIG_PATH.read_text())
            try:
                _coerced = _cs.set_value(_base, args.key, args.value)
            except ValueError as _e:
                _msg = str(_e)
                print(json.dumps({'status': 'error', 'error': _msg}) if args.json else _msg)
                return 1
            save_config(_base)
            if args.json:
                print(json.dumps({'status': 'ok', 'key': args.key, 'value': _coerced}))
            else:
                print(f'{args.key} = {json.dumps(_coerced)}')
            return 0
        if args.config_verb == 'init':
            _out_path = getattr(args, 'config_out', None)
            _force = getattr(args, 'force', False)
            _template = _cs.init_template()
            if _out_path:
                _p = Path(_out_path)
                if _p.exists() and not _force:
                    _msg = f'{_out_path} already exists; use --force to overwrite'
                    print(json.dumps({'status': 'error', 'error': _msg}) if args.json else _msg)
                    return 1
                _p.write_text(_template)
                _msg = f'wrote {_out_path}'
                print(json.dumps({'status': 'ok', 'path': _out_path}) if args.json else _msg)
            else:
                print(_template)
            return 0
        if args.config_verb == 'fields':
            _flds = _cs.fields()
            if args.json:
                print(json.dumps({'status': 'ok', 'fields': _flds}, indent=2))
            else:
                for _f in _flds:
                    _opts = f'  [{", ".join(_f["options"])}]' if 'options' in _f else ''
                    print(f'  {_f["path"]:50s}  {_f["type"]:6s}  default={json.dumps(_f["default"])}{_opts}')
                    if _f.get('description'):
                        print(f'    {_f["description"]}')
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
    _r = _run_facade_handlers(
        _FACADE_HANDLERS[12:-2], args, parser, config, state, _fmt, _unknown, raw_args
    )
    if _r is not None:
        return _r
    if args.command=='product' and args.action!='improvements' and args.improvement_product_id is not None:parser.error('Unexpected product argument; use product improvements enable|disable PRODUCT_ID')
    if args.command=='product' and args.all_products and args.action!='improvements':parser.error('--all-products requires product improvements list')
    _r = _run_facade_handlers(
        _FACADE_HANDLERS[-2:], args, parser, config, state, _fmt, _unknown, raw_args
    )
    if _r is not None:
        return _r
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
    _r = _cmd_watch(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_usage(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_cost(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_help(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
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
    _r = _cmd_executor_options(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_auto_goals_effort(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_configuration_self_evolution(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_change(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_update(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_export(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_import(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_report_bare(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_audit(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    config = _config if _config is not None else load_config()
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
                _ac_result = bootstrap.auto_complete(sys.modules[__name__],config)
                return 0 if isinstance(_ac_result, dict) else _ac_result
            except KeyboardInterrupt:
                return 130
            finally:
                sys.modules[__name__]._INIT_AUTO_ACTIVE = False
        # re-entrant call from inside auto_complete — fall through to state init
    _r = _cmd_commands(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_portfolio(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_report(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_auto_dry_run(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    if args.command == "autonomous":args.command="auto"
    _r = _cmd_github(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_git(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_gh(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_run(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_start(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_stop(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_reload(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_shell_dashboard(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_daemon(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_m2m(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_evidence(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_blocker(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_decision(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_integrity_signal(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_govern(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_inbox(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_onboard(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_product(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_fleet(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_data(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_trace(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_schema(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_feedback(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_api(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_web(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_resource(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_derive(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_context(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_executor_status(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_check_vitals(args, parser, config, state, _fmt, _unknown, raw_args, preflight_hints=_preflight_hints)
    if _r is not None: return _r
    _r = _cmd_quality(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_compliance(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_milestone(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
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
    _r = _cmd_source_metric_vital_goal(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_policy(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_budget(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_evaluation(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_executor_circuit_breaker(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_executor_attach_detach(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_pause(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_resume(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_classify(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_add(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_declare(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_add_shorthand(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_intent(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_constraint(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_explain(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_rules(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
    _r = _cmd_compact_decompact_amend_why_crc(args, parser, config, state, _fmt, _unknown, raw_args)
    if _r is not None: return _r
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
                        "p2p_borrow_enabled": _ctrl_caps.get("p2p_borrow_enabled", False),
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
                # 8. Regression guard status
                try:
                    from .. import runtime_regression_guard as _dr_rg
                    _dr_gs = _dr_rg.guard_status(_dr_state or {})
                    _dr_gs_status = _dr_gs.get("status", "UNKNOWN")
                    if _dr_gs_status == "OK":
                        _dr_check("regression_guard", "OK", f"{_dr_gs.get('checked_scopes', 0)} scopes clean")
                    else:
                        _dr_check("regression_guard", "WARN", f"status={_dr_gs_status}")
                except Exception as _e:
                    _dr_check("regression_guard", "WARN", str(_e))
                # 9. Cost tracking available
                try:
                    from .. import cost_tracker as _dr_ct
                    _dr_snap = _dr_ct.get_default_ledger().cost_snapshot()
                    _dr_records = _dr_snap.get("records", 0)
                    _dr_check("cost_tracking", "OK", f"{_dr_records} record(s) in process ledger")
                except Exception as _e:
                    _dr_check("cost_tracking", "WARN", str(_e))
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
                # Periodic sybil gate pass (every 24h) — emit SYBIL_CANDIDATE for peers failing gate
                if args.command == "auto":
                    _sg_now = time.time()
                    if _sg_now - state.get('_sybil_gate_last_run', 0) >= 86400:
                        state['_sybil_gate_last_run'] = _sg_now
                        try:
                            from .. import reputation_categories as _rc_sg
                            _sg_exchange = getattr(args, '_exchange', None)
                            if _sg_exchange is None:
                                try:
                                    from ..peer_exchange import open_exchange
                                    _sg_exchange = open_exchange(config)
                                except Exception:
                                    _sg_exchange = None
                            if _sg_exchange is not None and hasattr(_sg_exchange, 'audit_rows') and hasattr(_sg_exchange, 'append_audit_row'):
                                _sg_rows = _sg_exchange.audit_rows()
                                _sg_peers = {r.get('peer') for r in _sg_rows if r.get('peer')} | \
                                            {r.get('replica_peer_id') for r in _sg_rows if r.get('replica_peer_id')}
                                _7d_ago = _sg_now - 604800
                                for _sg_peer in _sg_peers:
                                    if not _sg_peer or _sg_peer.startswith('__'):
                                        continue
                                    _sg_passes, _sg_failing = _rc_sg.sybil_gate(_sg_rows, _sg_peer)
                                    if not _sg_passes:
                                        _already = any(
                                            r.get('kind') == 'SYBIL_CANDIDATE'
                                            and r.get('peer') == _sg_peer
                                            and float(r.get('at_unix', 0)) > _7d_ago
                                            for r in _sg_rows
                                        )
                                        if not _already:
                                            _sg_exchange.append_audit_row({
                                                'kind': 'SYBIL_CANDIDATE',
                                                'peer': _sg_peer,
                                                'score': len(_sg_failing),
                                                'flags': _sg_failing,
                                                'at_unix': _sg_now,
                                                'at': datetime.now(timezone.utc).isoformat(),
                                            })
                                # Periodic mutual-approval cartel scan (piggybacks sybil cycle)
                                try:
                                    from .. import cartel_guard as _cg_sg
                                    _cg_results = _cg_sg.detect_mutual_approval_cartel(_sg_rows)
                                    for _cg_hit in _cg_results:
                                        _cg_members = _cg_hit.get('members', [])
                                        _already_cg = any(
                                            r.get('kind') == 'CARTEL_CANDIDATE'
                                            and set(r.get('members', [])) == set(_cg_members)
                                            and float(r.get('at_unix', 0)) > _7d_ago
                                            for r in _sg_rows
                                        )
                                        if not _already_cg:
                                            _sg_exchange.append_audit_row({
                                                'kind': 'CARTEL_CANDIDATE',
                                                'members': _cg_members,
                                                'density': _cg_hit.get('density', 0),
                                                'confidence': _cg_hit.get('confidence', 0),
                                                'at_unix': _sg_now,
                                                'at': datetime.now(timezone.utc).isoformat(),
                                            })
                                except Exception:
                                    pass
                        except Exception:
                            pass
                # Reward emission pass (every 300s) — emit CREDIT_DELTA for infra events
                if args.command == "auto":
                    _rw_now = time.time()
                    if _rw_now - state.get('_reward_last_run', 0) >= 300:
                        state['_reward_last_run'] = _rw_now
                        try:
                            _rw_ex = getattr(args, '_exchange', None)
                            if _rw_ex is None:
                                try:
                                    from ..peer_exchange import open_exchange
                                    _rw_ex = open_exchange(config)
                                except Exception:
                                    _rw_ex = None
                            if _rw_ex is not None and hasattr(_rw_ex, 'audit_rows') and hasattr(_rw_ex, 'append_audit_row'):
                                _rw_rows = _rw_ex.audit_rows()
                                _rw_peer = (_rw_ex.identity() or {}).get('peer_id')
                                if _rw_peer and not _rw_peer.startswith('__'):
                                    _rw_last = state.get('_reward_last_check_unix', _rw_now - 300)
                                    state['_reward_last_check_unix'] = _rw_now
                                    _rw_recent = [r for r in _rw_rows if float(r.get('at_unix', 0)) > _rw_last]
                                    _p2p_cfg = config.get('p2p', {})
                                    _rw_map = [
                                        ('SEAL_FINALIZED',    'seal_reward',      int(_p2p_cfg.get('seal_reward_units',      1_000_000))),
                                        ('RPC_ADMITTED',      'bootstrap_reward', int(_p2p_cfg.get('bootstrap_reward_units', 1_500_000))),
                                        ('RELAY_CREDIT_ISSUED','relay_reward',    int(_p2p_cfg.get('relay_reward_units',     1_000_000))),
                                    ]
                                    for _rw_kind, _rw_dir, _rw_amt in _rw_map:
                                        for _ in range(sum(1 for r in _rw_recent if r.get('kind') == _rw_kind)):
                                            _rw_ex.append_audit_row({
                                                'kind': 'CREDIT_DELTA',
                                                'direction': _rw_dir,
                                                'amount_units': _rw_amt,
                                                'peer': _rw_peer,
                                                'at_unix': _rw_now,
                                                'at': datetime.now(timezone.utc).isoformat(),
                                            })
                                    # llm_peer_reward: SIMILARITY_VERDICT with verdict='derived'
                                    _llm_count = sum(1 for r in _rw_recent if r.get('kind') == 'SIMILARITY_VERDICT' and r.get('verdict') == 'derived')
                                    for _ in range(_llm_count):
                                        _rw_ex.append_audit_row({
                                            'kind': 'CREDIT_DELTA',
                                            'direction': 'llm_peer_reward',
                                            'amount_units': int(_p2p_cfg.get('llm_peer_reward_units', 2_000_000)),
                                            'peer': _rw_peer,
                                            'at_unix': _rw_now,
                                            'at': datetime.now(timezone.utc).isoformat(),
                                        })
                        except Exception:
                            pass
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
