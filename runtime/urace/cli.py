from __future__ import annotations

import argparse
import atexit
import copy
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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


# ── Output format helpers (--format json|xml) ────────────────────────────────

def _json_to_xml(data: object, root: str = "urace", _indent: int = 0) -> str:
    """Recursively convert a JSON-compatible Python object to XML string.

    Elements-only (no attributes). Lists use repeated <item> children.
    None becomes <null/>. Root tag wraps the entire output at indent=0.
    """
    pad = "  " * _indent
    if _indent == 0:
        inner = _json_to_xml(data, root, _indent=1)
        return f"<{root}>\n{inner}</{root}>"
    if data is None:
        return f"{pad}<null/>\n"
    if isinstance(data, bool):
        return f"{pad}<bool>{str(data).lower()}</bool>\n"
    if isinstance(data, (int, float)):
        return f"{pad}<number>{data}</number>\n"
    if isinstance(data, str):
        escaped = data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"{pad}<string>{escaped}</string>\n"
    if isinstance(data, list):
        lines = []
        for item in data:
            inner = _json_to_xml(item, root, _indent=_indent + 1)
            lines.append(f"{pad}<item>\n{inner}{pad}</item>\n")
        return "".join(lines)
    if isinstance(data, dict):
        lines = []
        for key, val in data.items():
            safe_key = re.sub(r"[^A-Za-z0-9_\-.]", "_", str(key))
            inner = _json_to_xml(val, root, _indent=_indent + 1)
            lines.append(f"{pad}<{safe_key}>\n{inner}{pad}</{safe_key}>\n")
        return "".join(lines)
    return f"{pad}<value>{data}</value>\n"


def _validate_freeform_query(q: "str | None", max_bytes: int = 4096) -> "str | None":
    """Validate a freeform search/query string.

    Returns the cleaned query (same value) or raises ValueError with a clear message.
    Accepts None (blank query = return all) and passes it through unchanged.
    Enforces:
      - must be a str if not None
      - encoded length <= max_bytes
      - no null bytes
    """
    if q is None:
        return q
    if not isinstance(q, str):
        raise ValueError("Query must be a string")
    if "\x00" in q:
        raise ValueError("Query must not contain null bytes")
    if len(q.encode("utf-8")) > max_bytes:
        raise ValueError(f"Query exceeds maximum length of {max_bytes} bytes")
    return q


def _print_fmt(data: object, fmt: str, *, root: str = "urace") -> None:
    """Print data as JSON (default) or XML based on fmt ('json' or 'xml').

    Used by command handlers that support --format json|xml.
    Graceful fallback: non-JSON-serializable data prints as JSON string.
    """
    if fmt == "xml":
        print(_json_to_xml(data, root))
    else:
        print(json.dumps(data, indent=2))


class _XmlConvertStream:
    """Stdout wrapper that converts JSON writes to XML (used when --format xml is active).

    Each call to write() is inspected: if it starts with { or [, it is parsed as JSON
    and converted to XML. Non-JSON text passes through unchanged. This allows all
    existing handlers (which call json.dumps) to produce XML output without modification.
    """

    def __init__(self, underlying: Any) -> None:
        self._u = underlying

    def write(self, s: str) -> int:
        stripped = s.strip()
        if stripped and stripped[0] in ("{", "["):
            try:
                data = json.loads(stripped)
                xml_out = _json_to_xml(data) + "\n"
                self._u.write(xml_out)
                return len(s)
            except (json.JSONDecodeError, ValueError):
                pass
        return self._u.write(s)

    def flush(self) -> None:
        self._u.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._u, name)


def _resolve_scope_target(target_expr: str | None, state_path_dir: str) -> dict:
    """Resolve --target <field>[:<predicate>] to a concrete result dict.

    Predicates:
      'latest'    → most-recent CompactionEvent for field (from manifest)
      '<event-id>'→ exact event ID match in manifest
      '<record-id>'→ scan manifest events for record_ids_covered

    Returns: {field, predicate, resolved_id, error}
    """
    if not target_expr:
        return {"field": None, "predicate": None, "resolved_id": None, "error": None}

    parts = target_expr.split(":", 1)
    field = parts[0].strip() or None
    predicate = parts[1].strip() if len(parts) > 1 else None

    if field == "all":
        return {"field": "all", "predicate": None, "resolved_id": None, "error": None}

    if not predicate:
        return {"field": field, "predicate": None, "resolved_id": None, "error": None}

    try:
        manifest = compaction_module.load_manifest(state_path_dir) or {}
    except Exception:
        manifest = {}

    events = manifest.get("events", [])

    if predicate == "latest":
        # CompactionEvent uses "target_field" for field path key
        field_events = [e for e in events if e.get("target_field") == field or e.get("field_path") == field]
        if field_events:
            latest = max(field_events, key=lambda e: e.get("compacted_at", ""))
            evt_id = latest.get("id") or latest.get("event_id")
            return {"field": field, "predicate": "latest", "resolved_id": evt_id, "error": None}
        return {"field": field, "predicate": "latest", "resolved_id": None,
                "error": f"no compaction events for field '{field}'"}

    # CompactionEvent uses "id" as event identifier
    matching_event = next(
        (e for e in events if e.get("id") == predicate or e.get("event_id") == predicate), None
    )
    if matching_event:
        return {"field": field, "predicate": predicate,
                "resolved_id": matching_event.get("id") or matching_event.get("event_id"),
                "error": None}

    for event in events:
        if predicate in event.get("record_ids_covered", []):
            _fld = field or event.get("target_field") or event.get("field_path")
            _eid = event.get("id") or event.get("event_id")
            return {"field": _fld, "predicate": predicate, "resolved_id": _eid, "error": None}

    return {"field": field, "predicate": predicate, "resolved_id": None,
            "error": f"target predicate '{predicate}' not found in manifest"}


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


def parse_cycles(value: str) -> int:
    if value.strip().lower() in {"infinity", "infinite", "inf", "forever"}:
        return 0
    try:
        cycles = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("cycles must be a non-negative integer or 'infinity'") from error
    if cycles < 0:
        raise argparse.ArgumentTypeError("cycles must be non-negative")
    return cycles


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
        "success_measure": f"metric regression resolved or unresolved_markers reduced to zero",
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


def _current_spec_version() -> str:
    """Return the current URACE spec version string, or 'unknown' if unreadable."""
    spec_path = ROOT / "URACE.md"
    try:
        return spec_audit_module.extract_spec_version(spec_path.read_text(encoding="utf-8")) or "unknown"
    except (OSError, AttributeError):
        return "unknown"


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


def _emit_gap(state: dict[str, Any], kind: str, severity: str, detail: str, **extra: Any) -> None:
    """Emit an IntegrityGap validated against IntegrityGapCatalog (§62l r39).
    Unknown kinds also emit a meta-gap warning.
    """
    try:
        from urace import primitives as _p
        canonical_sev = _p.gap_severity(kind)
        if canonical_sev is None:
            state.setdefault("integrity_gaps", []).append({
                "id": identifier("igap"),
                "kind": "unknown-gap-kind",
                "severity": "WARNING",
                "detail": f"Unregistered IntegrityGap kind '{kind}' — register in IntegrityGapCatalog (§62l)",
                "at": now(),
                "resolved": False,
            })
        used_severity = canonical_sev or severity
    except Exception:
        used_severity = severity
    state.setdefault("integrity_gaps", []).append({
        "id": identifier("igap"),
        "kind": kind,
        "severity": used_severity,
        "detail": detail,
        "at": now(),
        "resolved": False,
        **extra,
    })


def _emit_trace(
    state: dict,
    kind: str,
    summary: str,
    *,
    cycle_id: "str | None" = None,
    operation_id: "str | None" = None,
    decision_id: "str | None" = None,
    detail: "str | None" = None,
    recorded_by: str = "runtime",
) -> None:
    """Emit a TraceRecord into State.trace_records (§62r ObservabilityContract)."""
    state.setdefault("trace_records", []).append({
        "id": identifier("trace-"),
        "at": now(),
        "kind": kind,
        "cycle_id": cycle_id,
        "operation_id": operation_id,
        "decision_id": decision_id,
        "summary": summary,
        "detail": detail,
        "recorded_by": recorded_by,
    })


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


def _emit_compaction_event(state: dict[str, Any], record_type: str, dropped_count: int) -> None:
    """Emit a CompactionEvent before governed truncation of a record list."""
    event = {
        "id": identifier("cevt"),
        "record_type": record_type,
        "dropped_count": dropped_count,
        "compacted_at": now(),
        "authorized_by": "RetentionPolicy",
    }
    state.setdefault("compaction_events", []).append(event)


def _emit_compliance_record(state: dict[str, Any], domain: str, status: str,
                             operation_id: str | None = None, violation_detail: str | None = None,
                             scope: str | None = None) -> None:
    """Emit a ComplianceRecord and update ComplianceState (spec §54 compliance recording contract, r48)."""
    ts = now()
    record: dict[str, Any] = {"id": identifier("cpl"), "domain": domain, "status": status,
                               "evaluated_at": ts}
    if operation_id:
        record["operation_id"] = operation_id
    if violation_detail:
        record["violation_detail"] = violation_detail
    if scope:
        record["scope"] = scope
    state.setdefault("compliance_records", []).append(record)
    cs_map: dict[str, Any] = state.setdefault("compliance_state", {})
    entry = cs_map.setdefault(domain, {"domain": domain, "status": "UNKNOWN",
                                        "last_checked_at": ts, "violation_refs": [],
                                        "consecutive_clean": 0})
    entry["status"] = status
    entry["last_checked_at"] = ts
    if status == "COMPLIANT":
        entry["consecutive_clean"] = int(entry.get("consecutive_clean", 0)) + 1
    elif status == "NON_COMPLIANT":
        entry["consecutive_clean"] = 0
        entry.setdefault("violation_refs", []).append(record["id"])


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
    import hashlib, json as _json
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

    if total == 0:
        maturity = "BOOTSTRAPPING"
    elif completeness < completeness_target:
        maturity = "FORMING"
    elif (ceiling is not None and surface > ceiling):
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
    if relevance >= 0.40 and confidence >= 0.60:
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
        signal = rec.get("signal", "NEUTRAL")
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

    ROI threshold adapts to budget pressure so nodes running low on credits prefer
    cheaper P2P sourcing over executor calls:
        adjusted_threshold = BASE × (1 − 0.5 × budget_pressure)
    If executor token-cost factor > 2× the median P2P feature cost, threshold drops
    another 30% to strongly favour the network.

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

        # --- Enrichment 2: Executor cost factor adjustment ---
        _exec_cost = float(config.get("executor", {}).get("cost_per_call_units", _cl.UNIT))
        _candidates_with_cost = [c for c in candidates if not c.get("cold_start")]
        _median_borrow = (_cl.feature_borrow_cost_units() if not _candidates_with_cost
                          else sorted([_cl.feature_borrow_cost_units() for _ in _candidates_with_cost])[len(_candidates_with_cost) // 2])
        if _exec_cost > 2 * _median_borrow:
            adjusted *= 0.70   # further 30% reduction

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
            "estimated_cost": 0.01,
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

    # --- CRC: generate fresh cognitive resume context at cycle boundary ---
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
                    "executor_cost_factor": _routing.get('executor_cost_factor', 0.0),
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
            if token in {"--json","--format","--confirm","--selection"} or token.startswith(("--format=","--selection=")):
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


def _handle_data_credential_command(args: Any, state: dict, fmt: str) -> None:
    """Handle urace data credential add|remove|inspect."""
    def _out(payload: dict) -> None:
        print(json.dumps(data_transport.public_record(payload), indent=2))

    cred_action = getattr(args, "credential_action", None)
    if cred_action == "add":
        rec = next((r for r in state["data_source_records"] if r["name"] == args.name), None)
        if rec is None:
            _out({"error": f"data source '{args.name}' not found"})
            return
        cred = {
            "id": identifier("cred-"),
            "data_source_id": rec["id"],
            "auth_kind": args.auth_kind,
            "secret_ref": args.secret_ref,
            "expires_at": getattr(args, "expires_at", None),
        }
        state["credential_records"].append(cred)
        rec["credential_record_id"] = cred["id"]
        _out({"action": "credential-add", "record": {k: v for k, v in cred.items() if k != "secret_ref"}})
    elif cred_action == "remove":
        rec = next((r for r in state["data_source_records"] if r["name"] == args.name), None)
        if rec is None:
            _out({"error": f"data source '{args.name}' not found"})
            return
        before = len(state["credential_records"])
        state["credential_records"] = [c for c in state["credential_records"] if c["id"] != rec.get("credential_record_id")]
        rec["credential_record_id"] = None
        _out({"action": "credential-remove", "name": args.name, "removed": before - len(state["credential_records"])})
    elif cred_action == "inspect":
        rec = next((r for r in state["data_source_records"] if r["name"] == args.name), None)
        if rec is None:
            _out({"error": f"data source '{args.name}' not found"})
            return
        cred = next((c for c in state["credential_records"] if c["id"] == rec.get("credential_record_id")), None)
        if cred is None:
            _out({"error": f"no credential attached to '{args.name}'"})
            return
        # Never emit secret_ref value
        safe = {k: v for k, v in cred.items() if k != "secret_ref"}
        safe["secret_ref"] = "<redacted>"
        _out({"action": "credential-inspect", "record": safe})
    else:
        _out({"error": "credential action required: add|remove|inspect"})


def _handle_data_command(args: Any, state: dict, config: dict) -> int:
    """Handle urace data subcommands (r117 §62v DataSourceRegistry)."""
    action = getattr(args, "data_action", None)
    fmt = getattr(args, "format", "text")

    def _out(payload: dict) -> None:
        print(json.dumps(data_transport.public_record(payload), indent=2))

    def _unavailable_data_operation(rec: dict, direction: str | None, gap: str) -> int:
        # Registration is not an implemented transport. Never attest to I/O
        # that did not happen, and never log a potentially credential-bearing DSN.
        rec["status"] = "DISCONNECTED"
        rec["adapter_status"] = "ADAPTER_REQUIRED"
        message = "No data-source transport is implemented for this operation"
        _emit_gap(state, gap, "WARNING" if direction is None else "BLOCKING", message,
                  data_source_id=rec["id"])
        payload = {"action": "data-" + action, "error": "ADAPTER_REQUIRED",
                   "status": "DISCONNECTED"}
        if direction is not None:
            record = {
                "id": identifier("dsync-"), "data_source_id": rec["id"],
                "cycle": state.get("cycle", 0), "direction": direction,
                "rows_affected": 0, "evidence_ids_produced": [],
                "records_written": [], "status": "FAILED", "error_msg": message,
            }
            state["data_sync_records"].append(record)
            payload["record"] = record
        _out(payload)
        return 1

    if action == "add":
        if any(r["name"]==args.name for r in state["data_source_records"]):
            _out({"error":"duplicate-name"});return 1
        direction_map = {"read": "READ", "write": "WRITE", "both": "BIDIRECTIONAL"}
        rec = {
            "id": identifier("dsr-"),
            "name": args.name,
            "adapter_kind": args.adapter_kind,
            "direction": direction_map.get(args.direction, "READ"),
            "connection_metadata": {"dsn": args.dsn},
            "credential_record_id": None,
            "status": "PENDING",
            "last_sync_cycle": None,
            "last_push_cycle": None,
            "schema_hint": getattr(args, "schema_hint", None),
            "label": getattr(args, "label", ""),
            "auto": getattr(args, "auto", True),
        }
        state["data_source_records"].append(rec)
        _out({"action": "data-add", "record": rec})
        return 0

    elif action == "update":
        direction_map = {"read": "READ", "write": "WRITE", "both": "BIDIRECTIONAL"}
        rec = next((r for r in state["data_source_records"] if r["name"] == args.name), None)
        if rec is None:
            _out({"error": f"data source '{args.name}' not found"})
            return 1
        if getattr(args, "adapter_kind", None):
            rec["adapter_kind"] = args.adapter_kind
        if getattr(args, "dsn", None):
            rec["connection_metadata"]["dsn"] = args.dsn
            rec["status"] = "PENDING"
        if getattr(args, "direction", None):
            rec["direction"] = direction_map[args.direction]
        if getattr(args, "label", None) is not None:
            rec["label"] = args.label
        if getattr(args, "auto", None) is not None:
            rec["auto"] = args.auto
        if getattr(args, "schema_hint", None) is not None:
            rec["schema_hint"] = args.schema_hint
        _out({"action": "data-update", "record": rec})
        return 0

    elif action == "remove":
        before = len(state["data_source_records"])
        state["data_source_records"] = [r for r in state["data_source_records"] if r["name"] != args.name]
        removed = before - len(state["data_source_records"])
        _out({"action": "data-remove", "name": args.name, "removed": removed})
        return 0

    elif action == "list":
        records = state["data_source_records"]
        if getattr(args, "adapter_kind", None):
            records = [r for r in records if r["adapter_kind"] == args.adapter_kind]
        direction_map = {"read": "READ", "write": "WRITE", "both": "BIDIRECTIONAL"}
        if getattr(args, "direction", None):
            records = [r for r in records if r["direction"] == direction_map.get(args.direction, args.direction)]
        if getattr(args, "status", None):
            records = [r for r in records if r["status"] == args.status]
        _out({"action": "data-list", "records": records})
        return 0

    elif action == "sync":
        rec = next((r for r in state["data_source_records"] if r["name"] == args.name), None)
        if rec is None:
            _out({"error": f"data source '{args.name}' not found"})
            return 1
        if rec["direction"] == "WRITE":
            _emit_gap(state, "data-source-direction-violation", "BLOCKING",
                      f"source '{args.name}' is WRITE-only; cannot PULL")
            _out({"error": "direction-violation", "kind": "data-source-direction-violation"})
            return 1
        code,result=data_transport.perform("sync",rec,state,config,(state_path(config).parent if "state_path" in config else Path(".")));_out(result);return code

    elif action == "push":
        rec = next((r for r in state["data_source_records"] if r["name"] == args.name), None)
        if rec is None:
            _out({"error": f"data source '{args.name}' not found"})
            return 1
        if rec["direction"] == "READ":
            _emit_gap(state, "data-source-direction-violation", "BLOCKING",
                      f"source '{args.name}' is READ-only; cannot PUSH")
            _out({"error": "direction-violation", "kind": "data-source-direction-violation"})
            return 1
        raw=getattr(args,"data_input_json",None)
        try:rows=data_transport.input_rows(raw,config,sys.stdin)
        except (OSError,ValueError) as error:_out({"error":"invalid input JSON","detail":str(error)[:200]});return 1
        code,result=data_transport.perform("push",rec,state,config,(state_path(config).parent if "state_path" in config else Path(".")),rows);_out(result);return code

    elif action == "inspect":
        rec = next((r for r in state["data_source_records"] if r["name"] == args.name), None)
        if rec is None:
            _out({"error": f"data source '{args.name}' not found"})
            return 1
        _out({"action": "data-inspect", "record": rec})
        return 0

    elif action == "verify":
        rec = next((r for r in state["data_source_records"] if r["name"] == args.name), None)
        if rec is None:
            _out({"error": f"data source '{args.name}' not found"})
            return 1
        code,result=data_transport.perform("verify",rec,state,config,(state_path(config).parent if "state_path" in config else Path(".")));_out(result);return code

    elif action == "status":
        summary = [
            {
                "name": r["name"],
                "adapter_kind": r["adapter_kind"],
                "direction": r["direction"],
                "auto": r.get("auto", True),
                "adapter_status":r.get("adapter_status","IMPLEMENTED" if r.get("adapter_kind") in data_transport.SUPPORTED else "ADAPTER_REQUIRED"),
                "status": r["status"],
                "last_sync_cycle": r.get("last_sync_cycle"),
                "last_push_cycle": r.get("last_push_cycle"),
            }
            for r in state["data_source_records"]
        ]
        _out({"action": "data-status", "sources": summary})
        return 0

    elif action == "credential":
        rec=next((r for r in state["data_source_records"] if r["name"]==args.name),None)
        missing=rec is None or (args.credential_action=="inspect" and not any(c["id"]==rec.get("credential_record_id") for c in state["credential_records"]))
        _handle_data_credential_command(args,state,fmt)
        return 1 if missing else 0

    else:
        _out({"error": "data action required: add|update|remove|list|sync|push|inspect|verify|status|credential"})
        return 1


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


def build_parser() -> argparse.ArgumentParser:
    """One grammar for CLI, typed API and MCP; construction performs no work."""
    from .version import RUNTIME_VERSION
    parser = argparse.ArgumentParser(prog="urace")
    parser.add_argument("--version", action="version", version=f"urace {RUNTIME_VERSION}")
    parser.add_argument("--format", choices=["json", "xml"], default=None,
                        help="output format: json or xml (also available per-subcommand)")
    parser.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    help_command = sub.add_parser("help", help="show the operation catalog or contextual help without an Executor call")
    help_command.add_argument("operation", nargs="*", default=[])
    help_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    help_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    from .trial_cli import build_parser as trial_parser
    sub.add_parser("trial", parents=[trial_parser()], add_help=False, help="inspect specification-trial resources, versions and evidence")
    init_command=sub.add_parser("init",help="initialize state; --ready completes validated operator bootstrap")
    init_command.add_argument("--ready",action="store_true",help="discover installed clients and complete real onboarding; then urace auto is ready")
    check = sub.add_parser("check")
    check.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    check.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    check.add_argument("--fail-on", choices=["BLOCKING", "WARNING", "INFO"], default=None, dest="fail_on")
    check.add_argument("--migration-dry-run", action="store_true", dest="migration_dry_run", default=False, help="simulate State Document schema migration without writing (StateSchemaMigrationProtocol §62l)")
    check.add_argument("--query", default=None, metavar="TEXT", help="filter inspection surface output by keyword")
    vitals = sub.add_parser("vitals", help="show progress, credit usage, efficiency, and lifecycle health")
    vitals.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    vitals.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    vitals.add_argument("--since", default=None)
    vitals.add_argument("--until", default=None)
    vitals.add_argument("--limit", type=int, default=None)
    vitals.add_argument("--fail-on", choices=["BLOCKING", "WARNING", "INFO"], default=None, dest="fail_on")
    change_command = sub.add_parser("change", help="list accepted changes or explain one by change ID")
    change_command.add_argument("action", choices=["list", "explain"])
    change_command.add_argument("id", nargs="?")
    change_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    change_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    configuration_command = command_surface.configuration(sub)
    self_evolution_command = sub.add_parser("self-evolution", help="show or set URACE self-evolution: auto, always, or never", description="Control whether URACE may improve its own generated implementation.", epilog="status  show the current mode\nauto    evolve only when a proven necessary limitation blocks Product goals (default)\nalways  allow eligible improvements under ordinary Authority and validation\nnever   disable self-evolution while keeping Product evolution active", formatter_class=argparse.RawDescriptionHelpFormatter)
    self_evolution_command.add_argument("mode", nargs="?", default="status", choices=["status", "auto", "always", "never"])
    self_evolution_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    self_evolution_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    commands = sub.add_parser("commands", help="show immediate versus durable-input command classification")
    commands.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    commands.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    inbox = sub.add_parser("inbox", help="inspect durable pending input and manage patch proposals")
    inbox.add_argument("action", choices=["list", "status", "apply", "reject", "help"])
    inbox.add_argument("input_id", nargs="?", default=None, help="input ID (status) or proposal ID (apply/reject)")
    inbox.add_argument("--reason", default=None, help="rejection reason (for reject action)")
    inbox.add_argument("--kind", default=None)
    inbox.add_argument("--status", default=None, choices=["QUEUED", "REJECTED", "PROCESSED"])
    inbox.add_argument("--limit", type=int, default=None)
    inbox.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    inbox.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    onboard_cmd = sub.add_parser("onboard", help="inspect and confirm the Product Onboard Phase (§62o)")
    onboard_cmd.add_argument("action", choices=["status", "confirm", "help"])
    onboard_cmd.add_argument("--note", default=None, help="optional note stored in OnboardRecord.notes")
    onboard_cmd.add_argument("--scan", action="store_true", help="scan neighboring directories for potential unregistered products (status only)")
    onboard_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    onboard_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    command_surface.product(sub)
    fleet_cmd = sub.add_parser("fleet", help="run multiple products in parallel (§62q)")
    fleet_cmd.add_argument("action", choices=["run", "status", "stop", "broadcast", "help"])
    fleet_cmd.add_argument("name", nargs="?", default=None, help="product name (stop)")
    fleet_cmd.add_argument("--dry-run", dest="dry_run", action="store_true")
    fleet_cmd.add_argument("--verbose", action="store_true")
    fleet_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    fleet_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)

    # urace data — DataSourceRegistry (r117 §62v)
    data_parser = sub.add_parser("data", help="Manage structural data sources")
    data_sub = data_parser.add_subparsers(dest="data_action")

    data_add = data_sub.add_parser("add", help="Register a new data source")
    data_add.add_argument("name", help="Data source name")
    data_add.add_argument("--type", dest="adapter_kind", required=True, help="Implemented local adapters: json, json_file, csv, sqlite; other types require a transport plugin")
    data_add.add_argument("--connect", dest="dsn", required=True, help="DSN, path, or connection string")
    data_add.add_argument("--direction", choices=["read", "write", "both"], default="read", help="Data flow direction")
    data_add.add_argument("--auto", type=command_surface.boolean, default=True, help="Auto-sync changed readable local sources (default true); writes require explicit push")
    data_add.add_argument("--schema", dest="schema_hint", default=None, help="Schema hint (table, sheet, collection name)")
    data_add.add_argument("--label", default="", help="Human-readable description")
    data_add.add_argument("--format", choices=["text", "json"], default="text")

    data_update = data_sub.add_parser("update", help="Update an existing data source")
    data_update.add_argument("name", help="Data source name")
    data_update.add_argument("--type", dest="adapter_kind", default=None)
    data_update.add_argument("--connect", dest="dsn", default=None)
    data_update.add_argument("--direction", choices=["read", "write", "both"], default=None)
    data_update.add_argument("--auto", type=command_surface.boolean, default=None)
    data_update.add_argument("--schema", dest="schema_hint", default=None)
    data_update.add_argument("--label", default=None)
    data_update.add_argument("--format", choices=["text", "json"], default="text")

    data_remove = data_sub.add_parser("remove", help="Deregister a data source")
    data_remove.add_argument("name", help="Data source name")
    data_remove.add_argument("--format", choices=["text", "json"], default="text")

    data_list = data_sub.add_parser("list", help="List registered data sources")
    data_list.add_argument("--type", dest="adapter_kind", default=None)
    data_list.add_argument("--direction", choices=["read", "write", "both"], default=None)
    data_list.add_argument("--status", choices=["CONNECTED", "DISCONNECTED", "DEGRADED", "PENDING"], default=None)
    data_list.add_argument("--format", choices=["text", "json"], default="text")

    data_sync = data_sub.add_parser("sync", help="Pull evidence from a data source")
    data_sync.add_argument("name", help="Data source name")
    data_sync.add_argument("--format", choices=["text", "json"], default="text")

    data_push = data_sub.add_parser("push", help="Push URACE records to a data source")
    data_push.add_argument("name", help="Data source name")
    data_push.add_argument("--input-json",dest="data_input_json",help="explicit JSON records to push; path or - for stdin")
    data_push.add_argument("--format", choices=["text", "json"], default="text")

    data_inspect = data_sub.add_parser("inspect", help="Inspect a data source")
    data_inspect.add_argument("name", help="Data source name")
    data_inspect.add_argument("--format", choices=["text", "json"], default="text")

    data_verify = data_sub.add_parser("verify", help="Test adapter connectivity without transferring data")
    data_verify.add_argument("name", help="Data source name")
    data_verify.add_argument("--format", choices=["text", "json"], default="text")

    data_status = data_sub.add_parser("status", help="Health overview of all registered data sources")
    data_status.add_argument("--format", choices=["text", "json"], default="text")

    data_cred = data_sub.add_parser("credential", help="Manage credentials for a data source")
    data_cred_sub = data_cred.add_subparsers(dest="credential_action")
    data_cred_add = data_cred_sub.add_parser("add", help="Attach a CredentialRecord to a data source")
    data_cred_add.add_argument("name", help="Data source name")
    data_cred_add.add_argument("--auth", dest="auth_kind", required=True,
        choices=["DSN", "API_KEY", "OAUTH2", "CERT", "BASIC", "KERBEROS", "IAM_ROLE", "VAULT_PATH", "ENV_VAR"])
    data_cred_add.add_argument("--ref", dest="secret_ref", required=True, help="Pointer to secret (env var name, vault path)")
    data_cred_add.add_argument("--expires", dest="expires_at", default=None, help="ISO-8601 expiry timestamp")
    data_cred_add.add_argument("--format", choices=["text", "json"], default="text")
    data_cred_remove = data_cred_sub.add_parser("remove", help="Detach CredentialRecord from a data source")
    data_cred_remove.add_argument("name", help="Data source name")
    data_cred_remove.add_argument("--format", choices=["text", "json"], default="text")
    data_cred_inspect = data_cred_sub.add_parser("inspect", help="Show credential metadata (pointer only, never secret)")
    data_cred_inspect.add_argument("name", help="Data source name")
    data_cred_inspect.add_argument("--format", choices=["text", "json"], default="text")

    trace_cmd = sub.add_parser("trace", help="query the lifecycle trace log (§62r)")
    trace_cmd.add_argument("action", choices=["list", "inspect", "help"])
    trace_cmd.add_argument("trace_id", nargs="?", default=None)
    trace_cmd.add_argument("--kind", choices=["CYCLE", "OPERATION", "DECISION", "TRANSITION", "GAP", "ONBOARD", "SWITCH", "FLEET"], default=None)
    trace_cmd.add_argument("--cycle-id", dest="cycle_id", default=None)
    trace_cmd.add_argument("--since", default=None)
    trace_cmd.add_argument("--until", default=None)
    trace_cmd.add_argument("--limit", type=int, default=50)
    trace_cmd.add_argument("--offset", type=int, default=0)
    trace_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    trace_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    schema_cmd = sub.add_parser("schema", help="inspect output schema registry (§62t OutputSchemaRegistry)")
    schema_cmd.add_argument("action", choices=["list", "inspect", "export", "help"])
    schema_cmd.add_argument("schema_command", nargs="*", default=[])
    schema_cmd.add_argument("--target", choices=["output-schemas", "bundles", "all"], default="all",
                            help="which registry to export (default: all); used with 'export' action")
    schema_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    schema_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    feedback_cmd = sub.add_parser("feedback", help="submit or list outcome feedback (§62u OutcomeFeedbackContract)")
    feedback_cmd.add_argument("action", choices=["list", "submit", "help"])
    feedback_cmd.add_argument("target_id", nargs="?", default=None)
    feedback_cmd.add_argument("--signal", choices=["POSITIVE", "NEGATIVE", "NEUTRAL"], default=None)
    feedback_cmd.add_argument("--detail", default="")
    feedback_cmd.add_argument("--evidence", dest="evidence_id", default=None)
    feedback_cmd.add_argument("--target", dest="filter_target", default=None)
    feedback_cmd.add_argument("--limit", type=int, default=20)
    feedback_cmd.add_argument("--offset", type=int, default=0)
    feedback_cmd.add_argument("--input-json", dest="input_json", default=None, help="path or - for stdin; reads signal/evidence/detail from JSON")
    feedback_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    feedback_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    resource_cmd = sub.add_parser("resource", help="inspect per-product resource usage and ROI (§62v)")
    resource_cmd.add_argument("action", choices=["status", "report", "help"])
    resource_cmd.add_argument("--since", default=None)
    resource_cmd.add_argument("--until", default=None)
    resource_cmd.add_argument("--limit", type=int, default=20)
    resource_cmd.add_argument("--offset", type=int, default=0)
    resource_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    resource_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    derive_cmd = sub.add_parser("derive", help="describe your intent and URACE picks the right patterns — or browse/combine manually (§62j)")
    derive_cmd.add_argument("intent", nargs="?", default="", help="what you are building — URACE suggests matching patterns automatically")
    derive_cmd.add_argument("--constructs", "--patterns", dest="constructs", required=False, default=None, help="comma-separated construct or pattern IDs (e.g. AP0,AP4 or QSM,GoalRecord); complements intent-based suggestions. --patterns is a backward-compat alias")
    derive_cmd.add_argument("--kind", default="all", help="construct kind(s): pattern, mechanism, schema, protocol, contract, or all (comma-separated, default: all)")
    derive_cmd.add_argument("--source", choices=["runtime", "spec"], default="runtime", dest="derive_source", help="source for derive: runtime (introspect current implementation, default) or spec (legacy pattern catalog)")
    derive_cmd.add_argument("--suggest", action="store_true", help="show intent-matched suggestions without building a manifest")
    derive_cmd.add_argument("--from-goals", action="store_true", help="derive construct suggestions from Goals declared in current state")
    derive_cmd.add_argument("--from-constraints", action="store_true", help="derive construct suggestions from HardConstraints declared in current state")
    derive_cmd.add_argument("--from-inspection", action="store_true", help="derive construct suggestions from current InspectionSurface blocking and warning gaps")
    derive_cmd.add_argument("--exclude", default=None, help="comma-separated pattern IDs to explicitly exclude (transitive deps only); requires --exclude-reason")
    derive_cmd.add_argument("--exclude-reason", default="", help="reason for excluding transitive deps (required when --exclude is used)")
    derive_cmd.add_argument("--out", default=None, help="write DerivedSystemManifest JSON to this path")
    derive_cmd.add_argument("--save", action="store_true", help="store manifest reference in state for stale-detection by urace update")
    derive_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    derive_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    derive_cmd.add_argument("--derive-capabilities", action="store_true", help="auto-generate draft CapabilityStatements from adopted patterns' provides clauses")
    derive_cmd.add_argument("--apply-capabilities", action="store_true", help="register derived capability drafts into Config.capability_envelope (requires --derive-capabilities or --constructs)")
    derive_cmd.add_argument("--refresh", action="store_true", help="re-derive all saved manifests with latest spec version")
    derive_cmd.add_argument("--manifest-id", default=None, help="target a specific saved manifest by manifest_id (use with --refresh)")
    derive_cmd.add_argument("--show-delta", action="store_true", help="when refreshing, show what changed vs saved manifest")
    derive_cmd.add_argument("--derive-milestone", action="store_true", help="draft a ProductMilestone from current capability gaps")
    derive_cmd.add_argument("--bundle", default=None, help="resolve a named FeatureBundle to construct_ids and merge with --constructs (e.g. community-inbox)")
    derive_cmd.add_argument("--list-bundles", action="store_true", help="list all built-in FeatureBundles and exit")
    derive_cmd.add_argument("--verify", action="store_true", help="re-verify stored content_hash of a saved manifest (§62k --verify)")
    derive_cmd.add_argument("--no-verify", action="store_true", dest="no_verify", help="skip automatic hash verification during derive (§62k --no-verify)")
    derive_cmd.add_argument("--hash", dest="derive_expected_hash", default=None, metavar="SHA256", help="verify a specific saved manifest against this SHA-256 hex digest (§62k --hash)")
    context_command = sub.add_parser("context", help="inspect gathered context and its provenance")
    context_command.add_argument("action", choices=["list","graph","attention"])
    context_command.add_argument("--id",dest="context_node_id");context_command.add_argument("--depth",type=int,default=1);context_command.add_argument("--limit",type=int,default=32)
    context_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    context_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    add_context = sub.add_parser("add-context", help="durably queue authoritative context for the next cycle")
    add_context.add_argument("text")
    add_context.add_argument("--source", default="repository owner")
    add_context.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    add_context.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # r101: hidden internal classify parser (freeform executor routing, not user-facing)
    classify_cmd = sub.add_parser("classify", help=argparse.SUPPRESS)
    classify_cmd.add_argument("text", nargs="?", default="", help="freeform text to classify")
    classify_cmd.add_argument("--confirm",action="store_true",help="confirm validated non-permission sections for durable queuing")
    classify_cmd.add_argument("--selection",help="explicit alternative number or skip")
    classify_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    classify_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    classify_cmd.add_argument("--file", default=None, help="load freeform input from a file path instead of inline text")
    classify_cmd.add_argument("--path", default=None, help="load file content from path into freeform context")
    add_goal = sub.add_parser("add-goal", help="durably queue a Product or URACE goal")
    add_goal.add_argument("title")
    add_goal.add_argument("--success-measure", required=True)
    add_goal.add_argument("--reason")
    add_goal.add_argument("--target", choices=["product", "urace"], default="product")
    add_goal.add_argument("--priority", type=int, default=70)
    add_goal.add_argument("--expected-value", type=float, default=0.7)
    add_goal.add_argument("--outcome-measure", help="identifier of an authoritative independent outcome measure")
    add_goal.add_argument("--estimated-cost", type=float, default=0.5)
    add_goal.add_argument("--risk", type=float, default=0.3)
    add_goal.add_argument("--urgency", type=float, default=0.5)
    add_goal.add_argument("--depends-on", action="append", default=[])
    add_goal.add_argument("--deadline")
    add_goal.add_argument("--not-before")
    add_goal.add_argument("--estimate-min-hours", type=float, default=0)
    add_goal.add_argument("--estimate-max-hours", type=float, default=0)
    add_goal.add_argument("--estimate-confidence", choices=["low", "medium", "high"], default="low")
    add_goal.add_argument("--priority-floor", type=int)
    add_goal.add_argument("--priority-ceiling", type=int)
    add_goal.add_argument("--pin", action="store_true")
    add_goal.add_argument("--necessity-evidence")
    add_goal.add_argument("--lower-impact-insufficient", action="store_true")
    add_goal.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    add_goal.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    intent_command = sub.add_parser("intent", help="add or manage DIRECTIVE rules (durable operator intent)")
    intent_command.add_argument("action", choices=["add", "list", "supersede", "deactivate", "rollback"])
    intent_command.add_argument("statement", nargs="?", help="intent statement text or version ID for rollback")
    intent_command.add_argument("--id", dest="rule_id", help="rule ID for supersede or deactivate")
    intent_command.add_argument("--scope", default="product", help="product | runtime | all")
    intent_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    intent_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    constraint_command = sub.add_parser("constraint", help="add or manage PROHIBITION/PERMISSION rules")
    constraint_command.add_argument("action", choices=["add", "list", "deactivate"])
    constraint_command.add_argument("statement", nargs="?", help="constraint statement text")
    constraint_command.add_argument("--id", dest="rule_id", help="rule ID for deactivate")
    constraint_command.add_argument("--allow", action="store_true", help="add as PERMISSION instead of PROHIBITION")
    constraint_command.add_argument("--scope", default="product")
    constraint_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    constraint_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    rules_command = sub.add_parser("rules", help="inspect the Rule Ledger: list, inspect, graph, or conflicts")
    rules_command.add_argument("action", choices=["list", "inspect", "graph", "conflicts", "changes"])
    rules_command.add_argument("id", nargs="?", help="rule ID for inspect or changes")
    rules_command.add_argument("--kind", help="filter by rule kind (PURPOSE, DIRECTIVE, PERMISSION, PROHIBITION, OBJECTIVE, POLICY)")
    rules_command.add_argument("--scope", help="filter by scope")
    rules_command.add_argument("--inferred", action="store_true", help="include system-inferred rules")
    rules_command.add_argument("--since", default=None)
    rules_command.add_argument("--until", default=None)
    rules_command.add_argument("--limit", type=int, default=None)
    rules_command.add_argument("--offset", type=int, default=0)
    rules_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    rules_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    add_source = sub.add_parser("add-source", help="queue an external metric or Evidence connector")
    add_source.add_argument("id")
    add_source.add_argument("kind")
    add_source.add_argument("location")
    add_source.add_argument("--visibility", choices=["public", "private"], default="private")
    add_source.add_argument("--credential-env")
    add_source.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    add_source.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    add_metric = sub.add_parser("add-metric", help="queue a metric mapping onto a connector")
    add_metric.add_argument("name")
    add_metric.add_argument("--source", required=True)
    add_metric.add_argument("--path", required=True)
    add_metric.add_argument("--direction", choices=["nondecreasing", "nonincreasing"], default="nondecreasing")
    add_metric.add_argument("--target", type=float)
    add_metric.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    add_metric.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    add_vital = sub.add_parser("add-vital", help="queue a direct or ratio vital derived from named metrics")
    add_vital.add_argument("name")
    add_vital.add_argument("--numerator", required=True)
    add_vital.add_argument("--denominator")
    add_vital.add_argument("--window", default="current")
    add_vital.add_argument("--description", default="")
    add_vital.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    add_vital.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # r101: add command (canonical, replaces declare from r100)
    add_cmd = sub.add_parser("add", help="directly queue a typed record without Executor")
    add_sub = add_cmd.add_subparsers(dest="add_subcommand")
    # add context
    dc = add_sub.add_parser("context", help="queue authoritative context text")
    dc.add_argument("text", help="context text (max 20,000 chars)")
    dc.add_argument("--source", default="repository owner")
    dc.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    dc.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # add goal
    dg = add_sub.add_parser("goal", help="queue a structured goal")
    dg.add_argument("title")
    dg.add_argument("--success-measure", required=True)
    dg.add_argument("--reason", required=True)
    dg.add_argument("--target", default=None)
    dg.add_argument("--priority", type=int, default=70)
    dg.add_argument("--expected-value", type=float, default=0.5)
    dg.add_argument("--estimated-cost", type=float, default=0.3)
    dg.add_argument("--risk", type=float, default=0.3)
    dg.add_argument("--urgency", type=float, default=0.5)
    dg.add_argument("--necessity-evidence", default=None)
    dg.add_argument("--lower-impact-insufficient", action="store_true")
    dg.add_argument("--depends-on", nargs="*", default=[])
    dg.add_argument("--deadline", default=None)
    dg.add_argument("--not-before", default=None)
    dg.add_argument("--estimate-min-hours", type=float, default=0)
    dg.add_argument("--estimate-max-hours", type=float, default=0)
    dg.add_argument("--estimate-confidence", choices=["low", "medium", "high"], default="low")
    dg.add_argument("--priority-floor", type=int, default=None)
    dg.add_argument("--priority-ceiling", type=int, default=None)
    dg.add_argument("--pin", action="store_true")
    dg.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    dg.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # add source
    ds = add_sub.add_parser("source", help="queue an external connector source")
    ds.add_argument("id")
    ds.add_argument("--kind", required=True)
    ds.add_argument("--location", required=True)
    ds.add_argument("--visibility", default="private")
    ds.add_argument("--credential-env", default=None)
    ds.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    ds.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # add metric
    dm = add_sub.add_parser("metric", help="queue a metric definition")
    dm.add_argument("name")
    dm.add_argument("--source", required=True)
    dm.add_argument("--path", required=True)
    dm.add_argument("--direction", choices=["nondecreasing", "nonincreasing"], default="nondecreasing")
    dm.add_argument("--target", type=float, default=None)
    dm.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    dm.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # add vital
    dv = add_sub.add_parser("vital", help="queue a vital definition")
    dv.add_argument("name")
    dv.add_argument("--numerator", required=True)
    dv.add_argument("--denominator", default=None)
    dv.add_argument("--window", default=None)
    dv.add_argument("--description", default=None)
    dv.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    dv.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # add evidence
    de = add_sub.add_parser("evidence", help="queue an operator-provided evidence record")
    de.add_argument("--kind", required=True, help="evidence kind (e.g. test-pass, metric-observation, external-validation)")
    de.add_argument("--summary", required=True, help="short human-readable summary")
    de.add_argument("--source", default=None, help="optional source record ID")
    de.add_argument("--detail", default=None, help="optional extended detail text")
    de.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    de.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # add principal — r115 PrincipalHierarchyProtocol (§62l)
    dp = add_sub.add_parser("principal", help="create a new PrincipalRecord (requires precedence=0 principal authorization)")
    dp.add_argument("name", help="principal name or identity (e.g. org email, team ID)")
    dp.add_argument("--precedence", type=int, default=1, help="authority lattice precedence (0=root; lower wins; default 1)")
    dp.add_argument("--scope", default="product", help="authority scope: product | runtime | all")
    dp.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    dp.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # r101: declare — hidden deprecated alias for add (r100 backwards compat)
    # Handler re-dispatches to add after printing deprecation warning.
    # Subparsers accept REMAINDER so all add-subcommand flags pass through.
    declare_cmd = sub.add_parser("declare", help=argparse.SUPPRESS)
    declare_sub = declare_cmd.add_subparsers(dest="declare_subcommand")
    for _dsub in ("context", "goal", "source", "metric", "vital"):
        _dp = declare_sub.add_parser(_dsub, help=argparse.SUPPRESS, add_help=False)
        _dp.add_argument("declare_remainder", nargs=argparse.REMAINDER)
    # urace explain <id> — r113 ExplanationProtocol (§62l)
    explain_cmd = sub.add_parser("explain", help="synthesize a human-readable explanation of a DecisionRecord (§62l ExplanationProtocol)")
    explain_cmd.add_argument("id", help="DecisionRecord id to explain")
    explain_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    explain_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    source_command = sub.add_parser("source", help="list or queue control of connector sources")
    source_command.add_argument("action", choices=["list", "enable", "disable", "remove"])
    source_command.add_argument("id", nargs="?")
    source_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    source_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    metric_command = sub.add_parser("metric", help="list or queue removal of metric definitions")
    metric_command.add_argument("action", choices=["list", "remove"])
    metric_command.add_argument("name", nargs="?")
    metric_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    metric_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    vital_command = sub.add_parser("vital", help="list or queue removal of vital definitions")
    vital_command.add_argument("action", choices=["list", "remove"])
    vital_command.add_argument("name", nargs="?")
    vital_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    vital_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    goal_command = sub.add_parser("goal", help="inspect, forecast, or durably manage goals")
    goal_command.add_argument("action", choices=["list", "inspect", "forecast", "prioritize", "schedule", "pin", "unpin", "defer", "resume", "resolve-update", "disable", "cancel", "delete"])
    goal_command.add_argument("id", nargs="?")
    goal_command.add_argument("--priority", type=int)
    goal_command.add_argument("--floor", type=int)
    goal_command.add_argument("--ceiling", type=int)
    goal_command.add_argument("--until")
    goal_command.add_argument("--deadline")
    goal_command.add_argument("--not-before")
    goal_command.add_argument("--clear-deadline", action="store_true")
    goal_command.add_argument("--clear-not-before", action="store_true")
    goal_command.add_argument("--estimate-min-hours", type=float)
    goal_command.add_argument("--estimate-max-hours", type=float)
    goal_command.add_argument("--estimate-confidence", choices=["low", "medium", "high"])
    goal_command.add_argument("--depends-on", action="append")
    goal_command.add_argument("--clear-dependencies", action="store_true")
    goal_command.add_argument("--decision")
    goal_command.add_argument("--status", default="active", choices=["active", "pending", "blocked", "resolved", "cancelled", "all"])
    goal_command.add_argument("--limit", type=int, default=20)
    goal_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    goal_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    policy_command = sub.add_parser("policy", help="inspect or queue autonomy policy changes")
    policy_command.add_argument("action", choices=["list", "set"])
    policy_command.add_argument("name", nargs="?", choices=["self-evolution", "external-metrics", "analytics-export"])
    policy_command.add_argument("value", nargs="?")
    policy_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    policy_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    budget_command = sub.add_parser("budget", help="inspect or queue Executor call limits")
    budget_command.add_argument("action", choices=["show", "set"])
    budget_command.add_argument("--daily", type=int)
    budget_command.add_argument("--monthly", type=int)
    budget_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    budget_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    evaluation_command = sub.add_parser("evaluation", help="inspect or queue changes to the evolution evaluator")
    evaluation_command.add_argument("action", choices=["show", "set-weight", "set-minimum"])
    evaluation_command.add_argument("component", nargs="?")
    evaluation_command.add_argument("value", nargs="?", type=float)
    evaluation_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    evaluation_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    report_command = sub.add_parser("report", help="export optional portable analytics without changing control state")
    report_command.add_argument("action", choices=["status", "export"])
    report_command.add_argument("--output", default="urace/generated/reports/latest")
    report_command.add_argument("--xlsx", action="store_true", help="also create XLSX when the optional openpyxl adapter is installed")
    report_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    report_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    update_command = sub.add_parser("update", help="download, explain, apply, or resolve a specification update safely")
    update_command.add_argument("action", nargs="?", choices=["download", "explain", "apply", "resolve", "help"], default=None)
    update_command.add_argument("reference", nargs="?", help="download source, candidate hash prefix, or local candidate path")
    update_command.add_argument("--source", dest="update_source", help="explicit specification source for orchestrated update")
    update_command.add_argument("--yes", action="store_true", help="authorize queueing the reviewed migration without interactive confirmation")
    update_command.add_argument("--decision", help="attributable operator decision for a checkpointed update conflict")
    update_command.add_argument("--opt-in-constructs", "--opt-in-patterns", default=None, dest="opt_in_constructs", help="comma-separated construct or AP IDs to limit update scope (e.g. AP8,AP14 or QSM,GoalRecord); default: all. --opt-in-patterns is a backward-compat alias")
    update_command.add_argument("--hash", dest="expected_hash", default=None, help="expected SHA-256 hex digest of the downloaded artifact (§62k --hash)")
    update_command.add_argument("--verify", action="store_true", help="re-verify a previously hashed candidate or manifest before applying (§62k --verify)")
    update_command.add_argument("--no-verify", action="store_true", dest="no_verify", help="skip automatic hash verification on apply (§62k --no-verify)")
    update_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    update_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    portfolio_command = sub.add_parser("portfolio", help="run the optional isolated-worktree portfolio helper", add_help=False)
    portfolio_command.add_argument("--help", action="store_true", dest="portfolio_help")
    portfolio_command.add_argument("portfolio_args", nargs=argparse.REMAINDER)
    plan = sub.add_parser("plan")
    plan.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    plan.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    auto_cmd = sub.add_parser("auto")
    auto_cmd.add_argument("--dry-run", action="store_true", help="preview the current lifecycle snapshot without cycles, writes, network or Executor calls")
    auto_cmd.add_argument("--cycles", type=parse_cycles, default=0, help="cycle limit; 0 or 'infinity' keeps lifecycle ownership active")
    auto_cmd.add_argument("--interval", type=float, default=30, help="seconds between persistent assessments")
    auto_cmd.add_argument("--force-discovery", action="store_true", help="run intelligent discovery now, ignoring its cadence")
    auto_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    auto_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    auto_cmd.add_argument("--quiet", action="store_true", help="suppress human per-cycle feedback; with --json, JSON Lines remain on stdout")
    auto_cmd.add_argument("--verbose", action="store_true", help="show detailed deterministic cycle diagnostics without an extra Executor call")
    executor_command = sub.add_parser("executor", help="inspect, attach, or detach the configured Executor")
    executor_command.add_argument("action", choices=["status", "attach", "detach", "retry-policy"])
    executor_command.add_argument("--command", dest="executor_binary", help="adapter executable name or path used by attach")
    executor_command.add_argument("--id", dest="executor_id", default="codex-primary", help="stable Executor identity")
    executor_command.add_argument("--adapter", choices=["codex-cli", "claude-cli"], default="codex-cli")
    executor_command.add_argument("--priority", type=int, default=100)
    executor_command.add_argument("--capability", action="append", choices=["discovery", "planning", "mutation", "evaluation", "execution"])
    executor_command.add_argument("--capability-priority", action="append", default=[], metavar="CAPABILITY=PRIORITY", help="task-specific routing priority; repeatable")
    executor_command.add_argument("--max-calls-24h", type=command_surface.call_limit, default=None)
    executor_command.add_argument("--max-calls-30d", type=command_surface.call_limit, default=None)
    executor_command.add_argument("--retry-mode", choices=["automatic", "dynamic", "fixed"], default="automatic")
    executor_command.add_argument("--retry-delay-ms", type=int, default=60000)
    executor_command.add_argument("--retry-fallback-seconds", type=int, default=18000)
    executor_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    executor_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    reset_command = sub.add_parser("reset", help="reset URACE state to clean defaults")
    reset_command.add_argument("--release-clean", action="store_true", dest="release_clean", help="flush all personal data, improvement queues, and non-default state — prepare a clean release build")
    reset_command.add_argument("--yes", action="store_true", help="skip confirmation prompt")
    # ── controls: granular capability enable/disable ──────────────────────────────
    controls_command = sub.add_parser("controls", help="show or set system capability flags (executors, P2P, freeform, machine interface, compress)")
    controls_sub = controls_command.add_subparsers(dest="controls_verb", required=True)
    ctrl_show = controls_sub.add_parser("show", help="show all current capability flags")
    command_surface.output_options(ctrl_show)
    ctrl_set = controls_sub.add_parser("set", help="enable or disable system capabilities")
    command_surface.output_options(ctrl_set)
    for _ctrl_flag in ("executor-enabled", "freeform-enabled", "machine-interface-enabled", "compress-enabled", "decompress-enabled", "p2p-mint-enabled", "p2p-sell-enabled", "p2p-borrow-enabled", "context-mint-enabled", "context-mint-objectives", "context-mint-evidence", "context-mint-decisions", "context-mint-operations", "context-mint-checkpoints"):
        ctrl_set.add_argument(f"--{_ctrl_flag}", type=command_surface.boolean, default=None)
    ctrl_set.add_argument("--executor-id", default=None, dest="executor_id", help="target specific executor by id (all executors if omitted)")
    ctrl_set.add_argument("--data-source-id", default=None, dest="data_source_id", help="target specific data source by id")
    ctrl_set.add_argument("--product-id", default=None, dest="product_id", help="apply controls to a specific product (all products if omitted)")
    # ── search: query context ledger ──────────────────────────────────────────────
    search_command = sub.add_parser("search", help="search or query the URACE context ledger and P2P audit ledger")
    search_command.add_argument("query", nargs="?", default=None, help="freeform text query or field=value filter; omit for all")
    search_command.add_argument("--kind", default=None, help="filter by entry kind: objective, operation, evidence, decision, checkpoint, blocker, or p2p (P2P audit ledger)")
    search_command.add_argument("--since", default=None, dest="since_date", help="ISO date lower bound (YYYY-MM-DD)")
    search_command.add_argument("--limit", type=int, default=50)
    command_surface.output_options(search_command)
    # ── doctor: system health check ──────────────────────────────────────────────
    doctor_command = sub.add_parser("doctor", help="check system health and configuration")
    doctor_command.add_argument("--json", action="store_true", dest="doctor_json", help="output as JSON")
    doctor_command.add_argument("--fix", action="store_true", dest="doctor_fix", help="attempt to auto-fix detected issues")
    repair_command = sub.add_parser("repair-controller", help=argparse.SUPPRESS)
    repair_command.add_argument("--component", choices=["portfolio"], required=True)
    repair_command.add_argument("--code", choices=["ACTIVE_COHORT_ACCOUNTING", "UNEXPECTED_CONTROLLER_EXCEPTION"], required=True)
    repair_command.add_argument("--phase", choices=["IDLE", "PLANNED", "CREATED", "MUTATED", "EVALUATED", "UNKNOWN"], required=True)
    repair_command.add_argument("--exception-class", choices=["SystemExit", "AssertionError", "AttributeError", "KeyError", "TypeError"], required=True)
    repair_command.add_argument("--confirmed-recurrence", action="store_true")
    capacity_command = sub.add_parser("executor-capacity", help=argparse.SUPPRESS)
    capacity_command.add_argument("action", choices=["defer", "clear"])
    capacity_command.add_argument("--retry-at")
    capacity_command.add_argument("--stage", default="portfolio")
    api_command = sub.add_parser("api", help="machine interface for external tools (§62w ExternalInterfaceProtocol)")
    api_command.add_argument("action", choices=["call", "batch", "help", "watch", "version", "commands", "serve", "protocols"])
    api_command.add_argument("--argv", help="exact CLI argument array as JSON; alternative to command/params")
    api_command.add_argument("--transport", choices=["stdio", "a2a"], default="stdio", help="MCP stdio or opt-in A2A HTTP transport")
    api_command.add_argument("--policy", help="operator-owned integration capability policy JSON file")
    api_command.add_argument("--port", type=int, default=8765, help="A2A loopback port (0 allocates a free port)")
    api_command.add_argument("--token-env", default="URACE_A2A_TOKEN", help="Environment variable containing the A2A bearer secret")
    api_command.add_argument("--stream", action="store_true", help="emit NDJSON progress for persistent commands")
    api_command.add_argument("--command", dest="api_command", default=None)
    api_command.add_argument("--params", default=None, help="JSON object of command parameters")
    api_command.add_argument("--input-json", dest="input_json", default=None, help="path or - for stdin JSON input")
    api_command.add_argument("--continue-on-error", dest="continue_on_error", action="store_true")
    api_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    api_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    # r98: api watch flags
    api_command.add_argument("--kinds", default="", help="comma-separated TraceRecord kinds to include")
    api_command.add_argument("--since", default=None, help="ISO-8601 start timestamp")
    api_command.add_argument("--follow", action="store_true", help="tail live trace records")
    pause_command = sub.add_parser("pause", help="suspend autonomous operation; durable state is preserved intact")
    pause_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    pause_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    resume_command = sub.add_parser("resume", help="resume a PAUSED lifecycle; equivalent to urace auto resuming from preserved state")
    resume_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    resume_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    compact_command = sub.add_parser("compact", aliases=["compress"], help="queue compaction of an accumulating list field (§62f); processed at next safe lifecycle boundary")
    compact_command.add_argument("field_path", nargs="?", default=None, help="dot-path of the field to compact (e.g. decision_records); omit when using --target all or --status")
    compact_command.add_argument("--dry-run", action="store_true", help="report eligible records without committing")
    compact_command.add_argument("--mode", choices=["ARCHIVE", "ROLLING_EVICTION"], help="override compaction mode (must not be PROHIBITED)")
    compact_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    compact_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    compact_command.add_argument("--status", action="store_true", help="show compaction manifest status without queuing a new compaction")
    compact_command.add_argument("--target", default=None, metavar="FIELD[:PREDICATE]|all",
                                 help="scope: 'all' compacts all governed fields; 'FIELD' equivalent to positional field_path; 'FIELD:latest' resolves to most-recent event")
    compact_command.add_argument("--product", default=None, metavar="ID[,...]|all",
                                 help="target product(s) by name — comma-separated or 'all' (§62k --product)")
    compact_command.add_argument("--products", dest="product", default=None, help=argparse.SUPPRESS)
    compact_command.add_argument("--prompt", default=None, metavar="TEXT",
                                 help="freeform text to guide field selection (describes what to compact)")
    compact_command.add_argument("--query", default=None, metavar="TEXT",
                                 help="freeform text or field=value filter to pre-select records for compaction")
    decompact_command = sub.add_parser("decompact", aliases=["decompress"], help="restore original records from an ARCHIVE-mode CompactionEvent, or extract a single record (§62f)")
    decompact_command.add_argument("compaction_event_id", nargs="?", default=None, help="CompactionEvent id (e.g. cmp-abc1234567); omit when using --target FIELD:latest")
    decompact_command.add_argument("--field-path", help="dot-path of the field containing the CompactionSummary (inferred from manifest if omitted)")
    decompact_command.add_argument("--record-id", dest="record_id", default=None, help="extract a single record by id without restoring the full segment (read-only)")
    decompact_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    decompact_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    decompact_command.add_argument("--target", default=None, metavar="FIELD:latest|FIELD:EVENT-ID",
                                   help="auto-resolve compaction_event_id from manifest: 'FIELD:latest' picks most-recent event for field")
    decompact_command.add_argument("--product", default=None, metavar="ID[,...]|all",
                                   help="target product(s) by name (§62k --product)")
    decompact_command.add_argument("--products", dest="product", default=None, help=argparse.SUPPRESS)
    decompact_command.add_argument("--query", default=None, metavar="TEXT",
                                   help="freeform text or field=value filter to select which decompacted records to show")
    amend_command = sub.add_parser("amend", help="apply in-place amendment to an archived record without full decompaction (§62f)")
    amend_command.add_argument("compaction_event_id", nargs="?", default=None, help="CompactionEvent id containing the record to amend; omit when using --target RECORD-ID")
    amend_command.add_argument("record_id", nargs="?", default=None, help="id of the record within the archive to amend; omit when using --target RECORD-ID")
    amend_command.add_argument("--notice", required=True, help="human-readable amendment notice describing what changed and why")
    amend_command.add_argument("--kind", choices=["PROVENANCE_REVISED", "SUPERSEDED", "CUSTOM"], default="PROVENANCE_REVISED", help="amendment kind (default: PROVENANCE_REVISED)")
    amend_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    amend_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    amend_command.add_argument("--target", default=None, metavar="RECORD-ID",
                               help="auto-find the compaction event covering this record ID (replaces positional compaction_event_id + record_id)")
    amend_command.add_argument("--product", default=None, metavar="ID",
                               help="run against a specific registered product by name (§62k --product)")
    why_command = sub.add_parser("why", help="traverse the reasoning chain behind a DecisionRecord (§62g)")
    why_command.add_argument("decision_id", help="DecisionRecord id to inspect (e.g. dec-abc1234567)")
    why_command.add_argument("--depth", type=int, default=None, help="maximum traversal depth (default: unlimited)")
    why_command.add_argument("--limit", type=int, default=None, help="maximum number of reasoning entries returned")
    why_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    why_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    crc_command = sub.add_parser("crc", help="inspect or regenerate the CognitiveResumeContext (§62e)")
    crc_command.add_argument("action", choices=["show", "regenerate"])
    crc_command.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    crc_command.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    crc_command.add_argument("--product", default=None, metavar="ID[,...]|all",
                             help="target product(s) by name — comma-separated or 'all' (§62k --product)")
    crc_command.add_argument("--products", dest="product", default=None, help=argparse.SUPPRESS)
    quality_cmd = sub.add_parser("quality", help="inspect quality deltas and quality streak across operations (§62c r31)")
    quality_cmd.add_argument("--scope", default=None, help="filter by ProductScope (e.g. product, runtime, documentation)")
    quality_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    quality_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    compliance_cmd = sub.add_parser("compliance", help="inspect compliance posture and trajectory per domain (§62b r48)")
    compliance_cmd.add_argument("--domain", default=None, choices=["authority", "intent", "schema", "constraint", "governance"], help="filter to a single domain")
    compliance_cmd.add_argument("--history", type=int, default=10, help="number of recent ComplianceRecords to show (default: 10)")
    compliance_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    compliance_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    milestone_cmd = sub.add_parser("milestone", help="show milestone progress, gate status, and ProductVersion history (§62k r35)")
    milestone_cmd.add_argument("--scope", default=None)
    milestone_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    milestone_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    evidence_cmd = sub.add_parser("evidence", help="query the Evidence log")
    evidence_cmd.add_argument("action", choices=["list"])
    evidence_cmd.add_argument("--kind", default=None)
    evidence_cmd.add_argument("--since", default=None)
    evidence_cmd.add_argument("--until", default=None)
    evidence_cmd.add_argument("--limit", type=int, default=20)
    evidence_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    evidence_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    blocker_cmd = sub.add_parser("blocker", help="list and resolve active blockers")
    blocker_cmd.add_argument("action", choices=["list", "resolve"])
    blocker_cmd.add_argument("blocker_id", nargs="?", default=None)
    blocker_cmd.add_argument("--resolved", action="store_true", help="include resolved blockers")
    blocker_cmd.add_argument("--scope", default=None)
    blocker_cmd.add_argument("--note", default=None)
    blocker_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    blocker_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    decision_cmd = sub.add_parser("decision", help="inspect DecisionRecords")
    decision_cmd.add_argument("action", choices=["list", "inspect", "assess"])
    decision_cmd.add_argument("decision_id", nargs="?", default=None)
    decision_cmd.add_argument("--forecast", help="explicit forecast JSON: bottleneck_id, benefits, weights, cost, risk and evidence_refs")
    decision_cmd.add_argument("--stale", action="store_true")
    decision_cmd.add_argument("--scope", default=None)
    decision_cmd.add_argument("--limit", type=int, default=20)
    decision_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    decision_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    isig_cmd = sub.add_parser("integrity-signal", help="list IntegritySignal records")
    isig_cmd.add_argument("action", choices=["list"])
    isig_cmd.add_argument("--type", dest="signal_type", default=None)
    isig_cmd.add_argument("--severity", choices=["BLOCKING", "WARNING", "INFO"], default=None)
    isig_cmd.add_argument("--resolved", action="store_true")
    isig_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    isig_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    govern_cmd = sub.add_parser("govern", help="operator clearance for OperatorGateProtocol conditions")
    govern_cmd.add_argument("action", choices=["clear", "list-gates"])
    govern_cmd.add_argument("gap_id", nargs="?", default=None)
    govern_cmd.add_argument("--note", default=None)
    govern_cmd.add_argument("--format", choices=["json", "xml"], default=None, dest="format", help="output format: json or xml")
    govern_cmd.add_argument("--json", action="store_const", const="json", dest="format", help=argparse.SUPPRESS)
    autonomous_cmd = sub.add_parser("autonomous", parents=[auto_cmd], add_help=False, help=argparse.SUPPRESS)
    command_surface.watch(sub)
    command_surface.status(sub)
    p_features = sub.add_parser("features", help="inspect runtime feature status registry")
    sp_feat = p_features.add_subparsers(dest="action")
    sp_feat.add_parser("list", help="list all features")
    p_fs = sp_feat.add_parser("filter", help="filter features by status or tag")
    p_fs.add_argument("--status", help="filter by status (stable/complete/active/stub/stale/review/deprecated/experimental)")
    p_fs.add_argument("--tag", help="filter by tag (core/integration/optional/security/observability/delivery/self-improvement/ux)")
    sp_feat.add_parser("summary", help="show count per status")
    p_fg = sp_feat.add_parser("show", help="show detail for one feature")
    p_fg.add_argument("feature_id")
    sp_feat.add_parser("candidates", help="list stub/stale/review features sorted by priority")
    p_rollback = sub.add_parser("rollback", help="restore product files from last accepted stable snapshot")
    p_rollback.add_argument("--dry-run", action="store_true", help="show what would be restored without writing")
    p_rollback.add_argument("--json", action="store_true", help="machine-readable output")
    p_peer = sub.add_parser("peer-review", help="manage peer-contributed improvement artifacts")
    sp_peer = p_peer.add_subparsers(dest="action")
    sp_peer.add_parser("list", help="list quarantined peer artifacts")
    p_peer_eval = sp_peer.add_parser("evaluate", help="evaluate a quarantined artifact for safety")
    p_peer_eval.add_argument("bundle_id")
    p_peer_promo = sp_peer.add_parser("promote", help="promote a peer artifact into the improvement workflow")
    p_peer_promo.add_argument("bundle_id")
    p_p2p = sub.add_parser("p2p", help="operator tools for P2P security update distribution")
    sp_p2p = p_p2p.add_subparsers(dest="action", required=True)
    sp_p2p.add_parser("keygen", help="generate a new Ed25519 release keypair").add_argument(
        "--out", default="", help="path for private key hex file (default: ~/.urace/release_key.hex)")
    _p2p_build = sp_p2p.add_parser("build-update", help="build a signed update bundle from current P2P security files")
    _p2p_build.add_argument("--key", required=True, action="append", dest="keys",
                             help="path to release private key hex file (repeat for multi-sig)")
    _p2p_build.add_argument("--out", default="", help="output bundle JSON path (default: urace-update-bundle.json)")
    _p2p_build.add_argument("--log-rekor", action="store_true", help="submit to Sigstore Rekor transparency log")
    _p2p_build.add_argument("--anchor-ots", action="store_true", help="anchor to Bitcoin via OpenTimestamps")
    _p2p_pub = sp_p2p.add_parser("publish-update", help="publish update bundle metadata to DHT")
    _p2p_pub.add_argument("--bundle", required=True, help="path to bundle JSON file built by build-update")
    _p2p_pub.add_argument("--key", required=True, help="path to release private key hex file")
    _p2p_pub.add_argument("--url", default="", help="public URL where nodes can download the full bundle JSON")
    sp_p2p.add_parser("check-update", help="query DHT for an available P2P security update")
    _p2p_apply = sp_p2p.add_parser("apply-update", help="verify and apply a P2P update bundle (operator-gate)")
    _p2p_apply.add_argument("--bundle", required=True, help="path to bundle JSON file")
    _p2p_apply.add_argument("--no-tests", action="store_true", help="skip test suite gate (emergency use only)")
    similarity_cmd = sub.add_parser("similarity", help="score peer features by TF-IDF intent similarity and collaborative adoption (§product_similarity)")
    similarity_cmd.add_argument("--max-peer-age", type=float, default=86400.0, dest="max_peer_age_seconds", metavar="SECONDS", help="exclude peers last seen older than this many seconds (default: 86400)")
    similarity_cmd.add_argument("--timeout", type=float, default=5.0, dest="timeout_seconds", metavar="SECONDS", help="return partial results after this many seconds (default: 5.0)")
    similarity_cmd.add_argument("--min-score", type=float, default=0.0, dest="min_score", metavar="FLOAT", help="omit results below this score threshold (default: 0.0)")
    command_surface.finalize(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    from .runtime_product import mutation_blocker
    _blocked=mutation_blocker(SYSTEM_ROOT,raw_args)
    if _blocked:
        print(json.dumps({'status':'DEFERRED','reason':_blocked,'schema':'runtime-transaction-admission-v1'}));return 2

    if raw_args and raw_args[0] == "trial":
        from .trial import main as trial_main
        return trial_main(raw_args[1:])
    explicit_classifier=bool(raw_args and raw_args[0].lstrip("/")=="classify")
    raw_args = _preprocess_args(raw_args)
    if not raw_args:
        from . import tui as _tui
        try:_tui_cfg=load_config()
        except Exception:_tui_cfg={}
        return _tui.launch(_tui_cfg,SYSTEM_ROOT)
    if raw_args in (["help"], ["-h"], ["--help"]):
        print(top_level_help())
        return 0
    parser = build_parser()
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
    from . import preflight as _preflight_module
    try:_pf_cfg=load_config()
    except Exception:_pf_cfg={}
    _preflight_hints=_preflight_module.hints(_pf_cfg,SYSTEM_ROOT)
    if not args.json and _preflight_hints:
        for _h in _preflight_hints:print(f"hint [{_h['level']}]: {_h['message']} — {_h['action']}",file=sys.stderr)
    if args.command=='features':
        from . import runtime_features as _rf
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
        from . import peer_improvement as _pi
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
        from . import product_similarity as _ps
        from . import peer_exchange as _pe
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
            from .evolution_guard import p2p_keygen as _p2p_keygen
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
            from .evolution_guard import build_p2p_update_bundle as _p2p_build_fn, RELEASE_AUTHORITY_KEYS as _ra_keys
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
                    print(f"  opentimestamps: anchored to Bitcoin calendar")
            return 0
        if _p2p_action == 'publish-update':
            from .peer_discovery import p2p_update_publish as _p2p_pub_fn
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
                    print(f"  status:      PUBLISHED")
                    print(f"  dht_key:     {_result['dht_key']}")
                    print(f"  fingerprint: {_result['corpus_fingerprint']}")
                    print(f"  bundle_url:  {_result.get('bundle_url') or '(none)'}")
                    print(f"  announced:   {_result['announced_to']} nodes")
                else:
                    print(f"error: {_result.get('error')}", file=sys.stderr)
                    return 1
            return 0
        if _p2p_action == 'check-update':
            from .evolution_guard import RELEASE_AUTHORITY_PUB_KEY_HEX as _ra_key
            if not _ra_key:
                print("error: RELEASE_AUTHORITY_PUB_KEY_HEX not configured in evolution_guard.py",
                      file=sys.stderr); return 1
            try:
                _p2p_cfg  = load_config()
                _p2p_state = load_state(_p2p_cfg)
                from . import peer_exchange as _pex
                _p2p_exch = _pex.Exchange(SYSTEM_ROOT / "urace" / "p2p")
                _p2p_exch.configure(enabled=True, network=True)
            except Exception as _e:
                print(f"error: {_e}", file=sys.stderr); return 1
            from .peer_discovery import p2p_update_check as _p2p_chk
            _chk = _p2p_chk(_p2p_exch, _ra_key)
            if getattr(args, 'json', False):
                print(json.dumps(_chk, indent=2))
            else:
                if _chk.get("available"):
                    print(f"  UPDATE AVAILABLE")
                    print(f"  remote fingerprint: {_chk['corpus_fingerprint']}")
                    print(f"  local  fingerprint: {_chk['local_fingerprint']}")
                    print(f"  bundle_url:         {_chk.get('bundle_url') or '(none)'}")
                    print(f"  Apply with: urace p2p apply-update --bundle <downloaded-bundle.json>")
                else:
                    print(f"  no update available  (local fingerprint: {_chk.get('local_fingerprint','')})")
            return 0
        if _p2p_action == 'apply-update':
            _bundle_path = _p2p_Path(args.bundle)
            if not _bundle_path.exists():
                print(f"error: bundle file not found: {_bundle_path}", file=sys.stderr); return 1
            _bundle = json.loads(_bundle_path.read_text())
            from .evolution_guard import apply_p2p_update_bundle as _p2p_apply_fn, verify_release_signature as _vrs2
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
        from .product_creation import create
        try:print(json.dumps(create(sys.modules[__name__],args.description,args.creation_name),indent=2));return 0
        except (ValueError,OSError) as error:parser.error(str(error))
    if args.command=='product' and args.action=='exchange':
        if _unknown:parser.error('Unrecognized exchange arguments: '+' '.join(_unknown))
        from .exchange_cli import run as run_exchange
        try:return run_exchange(args,load_config())
        except (ValueError,OSError) as error:parser.error(str(error))
    if args.command in {'executor-skills-config','context-guard-config'}:
        from . import executor_capabilities as ec
        if _unknown:parser.error('Unknown capability configuration arguments: '+' '.join(_unknown))
        key='executor_skills' if args.command=='executor-skills-config' else 'context_guard';changes={k:getattr(args,k) for k in ('enabled','mode','max_selected','max_instruction_bytes') if getattr(args,k,None) is not None}
        try:
            if getattr(args,'catalog_file',None):
                from .exchange_cli import bounded_file
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
    if args.command=='auto-milestones-config':
        from . import milestone_suggestions as ms
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
        from . import decision_feedback as df
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
        from . import value_discovery as vd
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
        from .trial import main as trial_main
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
        from .trial import main as trial_main
        trial_args = raw_args[raw_args.index("trial") + 1:]
        if _fmt and trial_args[:2] in (["status", "resources"], ["status", "scores"]) and "--json" not in trial_args:
            trial_args.append("--json")
        return trial_main(trial_args)
    if getattr(args,'status_subject',None)=='scores':
        if _unknown:parser.error('unrecognized score arguments: '+' '.join(_unknown))
        from .trial import main as trial_main
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
    if args.command == "help":
        if not args.operation:
            if args.json:
                print(json.dumps({"schema_version": "1.0", "command": "help", "guide": "Use 'urace help <operation>' to get help for a specific operation."}, indent=2))
                return 0
            parser.print_help()
            return 0
        help_root=parser;help_path=list(args.operation)
        if help_path[0]=="portfolio":
            from . import portfolio as _portfolio_help
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
            from .trial import main as trial_main
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
            from .value_discovery import settings as value_settings
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
    config = load_config()
    path = state_path(config)
    if args.command in {"auto", "autonomous"} and config.get("execution_workflow", "core") == "specification-trial":
        if getattr(args, "force_discovery", False): parser.error("specification-trial does not bypass acceptance, availability or allocation guards")
        from .trial import run_workflow
        explicit_interval = any(a == "--interval" or a.startswith("--interval=") for a in raw_args)
        return run_workflow(args.cycles, dry_run=args.dry_run, interval=args.interval if explicit_interval else 5, json_mode=args.json, quiet=args.quiet)
    if args.command=="init" and args.ready:
        from . import bootstrap
        return bootstrap.complete(sys.modules[__name__],config)
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
        from . import decision_feedback as df
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
            if not args.product_state_path:
                parser.error("product register requires --state-path")
            name = args.name
            registry = config.setdefault("product_registry", [])
            if any(e.get("name") == name for e in registry):
                result = {"status": "error", "error": f"product '{name}' already in registry"}
                print(json.dumps(result, indent=2) if args.json else f"error: '{name}' already registered")
                return 1
            # §62p State Isolation Contract: duplicate state_path MUST be rejected
            if any(e.get("state_path") == args.product_state_path for e in registry):
                try:
                    _dup_state = load_state(config)
                except RuntimeError:
                    _dup_state = None
                if _dup_state is not None:
                    _emit_gap(_dup_state, "product-registry-duplicate-state-path", "WARNING",
                              f"state_path '{args.product_state_path}' is already used by another product entry")
                    save_state(config, _dup_state)
                result = {"status": "error", "error": f"state_path '{args.product_state_path}' already in use"}
                print(json.dumps(result, indent=2) if args.json else f"error: state_path already used by another product")
                return 1
            entry = {
                "id": identifier("prod-"),
                "name": name,
                "state_path": args.product_state_path,
                "product_files": args.product_files,
                "intent_purpose": args.intent_purpose,
                "registered_at": now(),
                "last_active_at": None,
                "status": "ACTIVE",
            }
            registry.append(entry)
            save_config(config)
            result = {"status": "registered", "name": name, "id": entry["id"]}
            print(json.dumps(result, indent=2) if args.json else f"Registered product '{name}' (id={entry['id']})")
            return 0

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
                    raw = (_sys.stdin.read() if src == "-" else open(src).read())
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
            from .protocol_catalog import describe
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
                from .a2a_server import serve as serve_a2a
                return serve_a2a(parser, policy_path=args.policy, port=args.port, token_env=args.token_env)
            from .mcp_server import serve
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

        from . import derived_artifacts
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
                    from . import freeform_routing as _fr
                    _p2p_free = _fr._p2p_free_features(config)
                    if _p2p_free:
                        _intent_lower = intent_text.lower()
                        _p2p_matches = [f for f in _p2p_free if _intent_lower in (f.get('description','')+'|'+'|'.join(f.get('tags',[]))).lower() or any(t in _intent_lower for t in f.get('tags',[]))]
                        if _p2p_matches and not args.json:
                            print(f"P2P free-use features matching intent (borrow at zero cost):")
                            for _pf in _p2p_matches[:5]:
                                print(f"  {_pf.get('feature_id','?'):30s}  {_pf.get('description','')[:60]}")
                            print(f"  Use: urace exchange equity fill-listing <feature_id>")
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
                print(f"Draft ProductMilestone (NOT saved — operator review required):")
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
            from .context_relations import from_state,related,attention
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
            from .value_discovery import execution_quality_views
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
        cs_map: dict[str, Any] = state.get("compliance_state", {})
        records: list[dict] = state.get("compliance_records", [])
        if args.domain:
            cs_map = {k: v for k, v in cs_map.items() if k == args.domain}
            records = [r for r in records if r.get("domain") == args.domain]
        recent = records[-args.history:]
        domains_summary = [
            {"domain": d, "status": e.get("status", "UNKNOWN"),
             "consecutive_clean": e.get("consecutive_clean", 0),
             "last_checked_at": e.get("last_checked_at"),
             "violation_refs": e.get("violation_refs", [])}
            for d, e in cs_map.items()
        ]
        payload: dict[str, Any] = {
            "domains": domains_summary,
            "total_records": len(state.get("compliance_records", [])),
            "compliant": sum(1 for r in state.get("compliance_records", []) if r.get("status") == "COMPLIANT"),
            "non_compliant": sum(1 for r in state.get("compliance_records", []) if r.get("status") == "NON_COMPLIANT"),
            "recent_records": recent,
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

        from .milestone_feedback import assess as assess_milestone
        milestone_phases=[assess_milestone(config,state,m) for m in all_milestones if isinstance(m,dict)]
        active_phase=next((m for m in milestone_phases if active_ms and m['id']==active_ms.get('id')),None)

        from .milestone_suggestions import suggestions as suggest_milestones
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
        from .product_creation import explicit_creation,interpret,apply_interpreted
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
        from . import compaction as _compaction_module
        from . import cognitive_resume as _crc_module

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
            from .compaction import _DEFAULT_GOVERNANCE, _PROHIBITED_FIELDS, get_compaction_status
            state = load_state_for_read(config) or {}

            if getattr(args, "status", False):
                _status = get_compaction_status(sp)
                if args.json:
                    _print_fmt(_status, _fmt or "json")
                else:
                    print(f"Compaction status:")
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
            from . import decision_record as _dr_module
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
                save_state(config, state)
                write_stable_snapshot(config)
                write_runtime_snapshot(config)
                print(f"Initialized {config['product']} at {path}")
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
                _ALL_CAP_KEYS = ("executor_enabled", "freeform_enabled", "machine_interface_enabled", "compress_enabled", "decompress_enabled", "p2p_mint_enabled", "p2p_sell_enabled", "p2p_borrow_enabled", "context_mint_enabled", "context_mint_objectives", "context_mint_evidence", "context_mint_decisions", "context_mint_operations", "context_mint_checkpoints")
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
                        from . import peer_exchange as _dr_pe
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
                        from . import peer_exchange as _pxc
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
                            "detail": f"cycle orchestrator completed",
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
                index += 1
                interval = getattr(args, "interval", 0)
                if interval and (count == 0 or index < count):
                    time.sleep(interval)
            payload: Any = outcomes[0] if len(outcomes) == 1 else outcomes
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
