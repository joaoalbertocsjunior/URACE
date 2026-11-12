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


# ── Session context helpers ───────────────────────────────────────────────────

def _session_context_path(config):
    return state_path(config).parent / "session_context.jsonl"

def _load_session_context(config, max_turns=20):
    p = _session_context_path(config)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: pass
    return rows[-max_turns:]

def _save_session_turn(config, turn):
    p = _session_context_path(config)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(turn) + "\n")


# ── Report HTML renderer ──────────────────────────────────────────────────────

def _render_report_html(state, rows):
    import html as _html
    rows_html = "".join(
        f"<tr><td>{_html.escape(str(r.get('kind','?')))}</td>"
        f"<td>{_html.escape(str(r.get('at','?')))}</td>"
        f"<td>{_html.escape(str(r.get('id','')))}</td></tr>"
        for r in rows[-50:]
    )
    state_html = _html.escape(json.dumps(state, indent=2))
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>URACE Report</title>
<style>body{{font-family:monospace;background:#0d1117;color:#c9d1d9;padding:2rem}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #30363d;padding:6px 10px;text-align:left}}
th{{background:#161b22}}pre{{background:#161b22;padding:1rem;overflow:auto}}</style></head>
<body><h1>URACE Report</h1>
<h2>Recent Ledger Events</h2>
<table><thead><tr><th>Kind</th><th>At</th><th>ID</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>State Snapshot</h2><pre>{state_html}</pre>
<p><small>Generated {__import__('datetime').datetime.utcnow().isoformat()}Z — run <code>urace report</code> to refresh</small></p>
</body></html>"""


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


