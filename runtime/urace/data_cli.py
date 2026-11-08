"""Data-source CLI handlers, isolated from the main command dispatcher."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from . import data_transport


def handle_data_credential_command(args: Any, state: dict, fmt: str, *, identifier) -> None:
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

def handle_data_command(args: Any, state: dict, config: dict, *, identifier, emit_gap, state_path) -> int:
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
        emit_gap(state, gap, "WARNING" if direction is None else "BLOCKING", message,
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
            emit_gap(state, "data-source-direction-violation", "BLOCKING",
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
            emit_gap(state, "data-source-direction-violation", "BLOCKING",
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
        handle_data_credential_command(args,state,fmt,identifier=identifier)
        return 1 if missing else 0

    else:
        _out({"error": "data action required: add|update|remove|list|sync|push|inspect|verify|status|credential"})
        return 1
