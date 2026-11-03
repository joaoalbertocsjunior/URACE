"""Portable, optional analytics export. Canonical control state never depends on it."""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def capabilities() -> dict[str, Any]:
    xlsx_ready = importlib.util.find_spec("openpyxl") is not None
    return {
        "portable_csv_html": {"status": "READY", "dependency": "Python standard library"},
        "native_xlsx": {"status": "READY" if xlsx_ready else "ADAPTER_REQUIRED", "dependency": "openpyxl", "required_for_lifecycle": False},
        "canonical_control_dependency": "NONE",
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_cell(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True)
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    return value


def _flatten(prefix: str, value: Any, output: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _flatten(f"{prefix}.{key}" if prefix else str(key), item, output)
    elif isinstance(value, list):
        output[prefix] = json.dumps(value, sort_keys=True)
    else:
        output[prefix] = value


def _rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for item in items:
        flat: dict[str, Any] = {}
        _flatten("", item, flat)
        result.append(flat)
    return result


def collect(root: Path, state: dict[str, Any], vitals: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {
        "overview": _rows([{"exported_at": _now(), "state_version": state.get("state_version"), "lifecycle": state.get("lifecycle_state"), "canonical_source": "durable URACE state", "control_dependency": "NONE"}]),
        "progress_metrics": _rows([{"name": name, **entry} for name, entry in vitals.get("progress_metrics", {}).items()]),
        "system_scorecard": _rows([{"name": name, **entry} for name, entry in vitals.get("system_scorecard", {}).get("dimensions", {}).items()]),
        "executor_usage": _rows(state.get("executor_state", {}).get("executor_calls", [])),
        "discovery_yield": _rows([vitals.get("executor_efficiency", {}).get("discovery_loop_yield", {})]),
        "objectives": _rows(state.get("objectives", [])),
        "work_evaluations": _rows(vitals.get("work_evaluations", {}).get("goals", []) + vitals.get("work_evaluations", {}).get("contexts", [])),
        "external_observations": _rows(state.get("external_metric_state", {}).get("latest", [])),
        "reasoning_patterns": _rows(state.get("reasoning_memory", [])),
    }
    portfolio_path = root / "state" / "portfolio" / "portfolio.json"
    if portfolio_path.exists():
        try:
            from . import portfolio as portfolio_controller
            portfolio = portfolio_controller.load()
        except SystemExit as error:
            raise RuntimeError(f"portfolio analytics refused unverified ledger: {error}") from error
        tables.update({
            "portfolio_variants": _rows(list(portfolio.get("variants", {}).values())),
            "portfolio_events": _rows(portfolio.get("events", [])),
            "agora_proposals": _rows(portfolio.get("agora", {}).get("proposals", [])),
            "agora_votes": _rows(portfolio.get("agora", {}).get("votes", [])),
            "agora_decisions": _rows(portfolio.get("agora", {}).get("decisions", [])),
        })
    return tables


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({field for row in rows for field in row}) or ["no_data"]
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _safe_cell(row.get(field, "")) for field in fields})


def _dashboard(tables: dict[str, list[dict[str, Any]]], manifest: dict[str, Any]) -> str:
    navigation = "".join(f'<a href="#{html.escape(name)}">{html.escape(name.replace("_", " ").title())}</a>' for name in tables)
    sections = []
    for name, rows in tables.items():
        fields = sorted({field for row in rows for field in row})[:12]
        body = "".join("<tr>" + "".join(f"<td>{html.escape(str(row.get(field, '')))}</td>" for field in fields) + "</tr>" for row in rows[-100:])
        head = "".join(f"<th>{html.escape(field)}</th>" for field in fields)
        sections.append(f'<section id="{html.escape(name)}"><h2>{html.escape(name.replace("_", " ").title())}</h2><p>{len(rows)} records; newest 100 shown.</p><div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>')
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>URACE analytics</title><style>body{{font:15px system-ui;max-width:1400px;margin:auto;padding:2rem;color:#17202a}}nav{{display:flex;gap:.8rem;flex-wrap:wrap}}section{{margin:2rem 0}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd1d1;padding:.4rem;text-align:left;vertical-align:top}}th{{background:#edf2f7;position:sticky;top:0}}code{{background:#f4f6f7;padding:.2rem}}</style></head><body><h1>URACE portable analytics</h1><p>Generated <code>{html.escape(manifest['exported_at'])}</code>. This report is observational. URACE control never reads decisions from it.</p><nav>{navigation}</nav>{''.join(sections)}</body></html>'''


def export_portable(root: Path, state: dict[str, Any], vitals: dict[str, Any], output: Path, include_xlsx: bool = False) -> dict[str, Any]:
    tables = collect(root, state, vitals)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = root / "urace" / "generated" / "temporary"
    temporary_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f"analytics-{output.name}-", dir=temporary_root))
    try:
        csv_dir = temporary / "csv"; csv_dir.mkdir()
        for name, rows in tables.items():
            _write_csv(csv_dir / f"{name}.csv", rows)
        manifest = {"schema_version": 1, "exported_at": _now(), "state_version": state.get("state_version"), "canonical_source": "durable URACE state", "control_dependency": "NONE", "tables": {name: len(rows) for name, rows in tables.items()}, "formats": ["csv", "html"], "spreadsheet_formula_escaping": True}
        (temporary / "dashboard.html").write_text(_dashboard(tables, manifest), encoding="utf-8")
        if include_xlsx:
            try:
                from openpyxl import Workbook  # type: ignore
            except ImportError as error:
                raise RuntimeError("XLSX_ADAPTER_REQUIRED: install openpyxl or use the portable CSV/HTML bundle") from error
            workbook = Workbook(); workbook.remove(workbook.active)
            for name, rows in tables.items():
                sheet = workbook.create_sheet(name[:31]); fields = sorted({field for row in rows for field in row}) or ["no_data"]
                sheet.append(fields)
                for row in rows: sheet.append([_safe_cell(row.get(field, "")) for field in fields])
                sheet.freeze_panes = "A2"; sheet.auto_filter.ref = sheet.dimensions
            workbook.save(temporary / "urace-analytics.xlsx"); manifest["formats"].append("xlsx")
        file_hashes = {}
        for path in sorted(temporary.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                file_hashes[str(path.relative_to(temporary))] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest["sha256"] = file_hashes
        (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        backup = output.with_name(output.name + ".previous")
        if backup.exists(): shutil.rmtree(backup)
        if output.exists(): os.replace(output, backup)
        os.replace(temporary, output)
        if backup.exists(): shutil.rmtree(backup)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
