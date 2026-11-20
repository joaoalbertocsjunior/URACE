from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from urace._common import (
    ROOT, CONFIG_PATH, SYSTEM_ROOT,
    load_config, load_state, load_state_for_read, save_config, save_state,
    state_lock, now, identifier, input_directory,
)
from urace import command_surface
from urace import executor as intelligent_executor
from urace.cli_emit import _emit_gap
from urace.cli_helpers import _help_action
from urace.cli_state import product_digest


def _cmd_content(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "content":
        from urace import content_store as _cs
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


def _cmd_product_work(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "product" and args.action == "work":
        if args.name=='clarify':
            if _unknown:parser.error('Unknown clarification arguments: '+' '.join(_unknown))
            sys.path.insert(0,str(SYSTEM_ROOT/'trial'));from project_work import clarify
            try:print(json.dumps(clarify(args.project,args.requirement_id,args.answer,SYSTEM_ROOT/'trial'),indent=2));return 0
            except (ValueError,OSError) as error:parser.error(str(error))
        if args.name not in ('init','run','status') or not args.project:parser.error('Use product work init|run|status --project PATH')
        from urace.trial import main as trial_main
        route=['work',args.name,'--project',args.project,'--template',args.template,'--executor',args.work_executor,'--execution-mode',args.execution_mode,'--max-seconds',str(args.max_seconds),'--adaptive',args.adaptive,'--json']
        if args.run_id:route+=['--run-id',args.run_id]
        return trial_main(route)


def _cmd_product_improvements(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_product(args, parser, config, state, fmt, _unknown, raw_args):
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
                from urace import portfolio_github as _pgh
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
            from urace import portfolio_github as _pgh
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


def _cmd_fleet(args, parser, config, state, fmt, _unknown, raw_args):
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
