from __future__ import annotations

import json
import sys

from urace._common import (
    ROOT, load_config, load_state, load_state_for_read, save_state, save_config,
    state_path, state_lock, now, identifier, input_directory,
)
from urace.cli_state import product_digest, initial_state
from urace.cli_helpers import _help_action
from urace.cli_emit import _emit_trace
from urace.cli_helpers import _inspect_list


def _cmd_evidence(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_blocker(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_decision(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "decision":
        from urace import decision_feedback as df
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


def _cmd_integrity_signal(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_govern(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_inbox(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_onboard(args, parser, config, state, fmt, _unknown, raw_args):
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
