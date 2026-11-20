from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path

from urace._common import (
    ROOT, CONFIG_PATH, SYSTEM_ROOT,
    load_config, load_state, load_state_for_read, save_config, save_state,
    state_path, state_lock, now, identifier,
)
from urace.inputs import queue_input
from urace import command_surface, updater
from urace import executor as intelligent_executor
from urace import patterns as pattern_catalog_module
from urace.cli_emit import _emit_gap
from urace.cli_helpers import (
    _help_action, _inspect_list,
    _suggest_derive_updates, _print_derive_update_suggestions,
)
from urace.cli_lifecycle import (
    _check_stale_derived_manifests,
)
# NOTE: main and BUILTIN_BUNDLES from urace.cli are imported lazily inside
# _cmd_run, _cmd_m2m, and _cmd_update to avoid circular imports.


def _cmd_trial(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "trial":
        from urace.trial import main as trial_main
        trial_args = raw_args[raw_args.index("trial") + 1:]
        if fmt and trial_args[:2] in (["status", "resources"], ["status", "scores"]) and "--json" not in trial_args:
            trial_args.append("--json")
        return trial_main(trial_args)


def _cmd_watch(args, parser, config, state, fmt, _unknown, raw_args):
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
            from urace.cli_error import cli_error
            return cli_error(f'runtime improvement modules not found: {_e}', as_json=args.json)
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


def _cmd_change(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_update(args, parser, config, state, fmt, _unknown, raw_args):
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
        import urace.cli as _cli_mod
        config = load_config()
        update_state_root = state_path(config).parent
        _opt_in_raw = [p.strip() for p in (args.opt_in_constructs or "").split(",") if p.strip()]
        _opt_in: list[str] = []
        for _token in _opt_in_raw:
            if _token.startswith("@"):
                _bname = _token[1:]
                if _bname not in _cli_mod.BUILTIN_BUNDLES:
                    print(f"urace: unknown bundle '@{_bname}' in --opt-in-constructs. Use `urace derive --list-bundles` to see available bundles.", file=sys.stderr)
                    return 2
                _opt_in.extend(_cli_mod.BUILTIN_BUNDLES[_bname])
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
                        # Gate: customizations detected without --force
                        _orch_cust=payload.get('local_customizations',{})
                        if _orch_cust.get('status')=='LOCAL_CUSTOMIZATIONS_PRESENT' and not getattr(args,'force',False):
                            result={'status':'CUSTOMIZATION_REVIEW_REQUIRED','local_customizations':_orch_cust,'next':"re-run with --force to apply over local customizations, or run 'urace update explain' to review"}
                        else:
                            # Pre-apply backup
                            _orch_sp=state_path(config)
                            if _orch_sp.exists():
                                import datetime as _dt2
                                _bd2=_orch_sp.parent/'backups';_bd2.mkdir(exist_ok=True)
                                _ts2=_dt2.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                                (_bd2/f'state-pre-update-{_ts2}.json').write_bytes(_orch_sp.read_bytes())
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
                if args.expected_hash and (not __import__('re').fullmatch('[0-9a-fA-F]{64}',args.expected_hash) or args.expected_hash.lower()!=payload['update_candidate']['sha256']):
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
                # Gate on local customizations: warn and require --force when drift detected
                _update_local_cust = payload.get("local_customizations", {})
                if _update_local_cust.get("status") == "LOCAL_CUSTOMIZATIONS_PRESENT" and not getattr(args, "force", False) and not getattr(args, "yes", False):
                    _n_changed = len(_update_local_cust.get("changed", []))
                    _n_missing = len(_update_local_cust.get("missing", []))
                    _n_added = len(_update_local_cust.get("added", []))
                    if args.json:
                        print(json.dumps({"status": "CUSTOMIZATION_REVIEW_REQUIRED", "local_customizations": _update_local_cust, "next": "re-run with --force to apply over local customizations, or run 'urace update explain' to review"}, indent=2, sort_keys=True))
                        return 1
                    print(f"WARNING: {_n_changed} changed, {_n_missing} missing, {_n_added} added local files detected.")
                    print("The migration candidate may overwrite these. Run 'urace update explain' to review.")
                    print("Re-run with --force to apply anyway.")
                    return 1
                # Pre-apply backup: snapshot state.json before queuing the migration
                _pre_apply_state_path = state_path(config)
                if _pre_apply_state_path.exists():
                    import datetime as _dt
                    _backup_dir = _pre_apply_state_path.parent / "backups"
                    _backup_dir.mkdir(exist_ok=True)
                    _backup_ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                    _backup_target = _backup_dir / f"state-pre-update-{_backup_ts}.json"
                    _backup_target.write_bytes(_pre_apply_state_path.read_bytes())
                    if not args.json:
                        print(f"Pre-update backup: {_backup_target}")
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


def _cmd_run(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "run":
        # alias: run one improvement cycle (urace auto --cycles 1)
        import urace.cli as _cli_mod
        return _cli_mod.main(["auto", "--cycles", "1"] + (["--json"] if getattr(args,"json",False) else []))


def _cmd_start(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "start":
        from urace import bootstrap as _bs, _daemon as _dm
        import argparse as _ap
        as_json = getattr(args, 'json', False) or getattr(args, 'format', None) == 'json'
        # init + detect, suppress verbose JSON — we print our own compact banner
        # Set re-entrancy guard so cli.main(['init']) inside auto_complete doesn't recurse
        import urace.cli as _cli_mod
        _cli_mod._INIT_AUTO_ACTIVE = True
        try:
            _init_result = _bs.auto_complete(_cli_mod, config, _quiet=True)
        finally:
            _cli_mod._INIT_AUTO_ACTIVE = False
        if not isinstance(_init_result, dict):
            _init_result = {}
        # reload config after init
        try:
            import json as _j
            from urace._common import CONFIG_PATH as _cp
            config = _j.loads(_cp.read_text())
        except Exception:
            pass
        # print compact startup banner
        _nat = next((s for s in _init_result.get('steps', []) if s.get('step') == 'nat_detection'), {})
        _guide = _init_result.get('network_guide', {})
        try:
            _lifecycle = load_state(config).get('lifecycle_state', 'UNKNOWN')
        except Exception:
            _lifecycle = 'UNKNOWN'
        _banner = {
            'status': 'starting',
            'lifecycle': _lifecycle,
            'network': {
                'nat': _nat.get('nat_type', 'unknown'),
                'public_ip': _nat.get('public_ip'),
                'roles': _nat.get('recommended_roles', []),
                'mode': _nat.get('recommended_network_mode', 'hybrid'),
                'tunnel': _guide.get('scenario', 'none'),
            },
            'executor': {'providers': _init_result.get('executor_providers', 0)},
            'doctor': next((s.get('status') for s in _init_result.get('steps', []) if s.get('step') == 'doctor'), 'unknown'),
        }
        if _guide.get('scenario') == 'cloudflare_named':
            _banner['network']['note'] = 'permanent URL via cloudflared'
        print(json.dumps(_banner) if as_json else
              f"urace starting — lifecycle:{_banner['lifecycle']} nat:{_banner['network']['nat']} "
              f"roles:{','.join(_banner['network']['roles']) or 'none'} "
              f"tunnel:{_banner['network']['tunnel']} "
              f"executor:{_banner['executor']['providers']} providers")
        sys.stdout.flush()
        # start daemon (which also starts P2P serve)
        _start_args = _ap.Namespace(command='daemon', daemon_action='start',
                                     json=as_json,
                                     format=getattr(args,'format',None),
                                     interval_minutes=getattr(args,'interval_minutes',30.0),
                                     max_cycles=0, cycles=0)
        return _dm.dispatch(_start_args, config)


def _cmd_stop(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "stop":
        from urace import _daemon as _dm
        import argparse as _ap
        _stop_args = _ap.Namespace(command='daemon', daemon_action='stop',
                                    json=getattr(args,'json',False),
                                    format=getattr(args,'format',None))
        return _dm.dispatch(_stop_args, config)


def _cmd_reload(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "reload":
        from urace import _daemon as _dm
        as_json = getattr(args, 'json', False) or getattr(args, 'format', None) == 'json'
        pid = _dm._read_pid(config)
        if pid is None or not _dm._is_running(pid):
            msg = {"status": "no_daemon", "detail": "no running daemon to reload; config will be applied on next urace start"}
            print(json.dumps(msg) if as_json else "No daemon running. Config will be applied on next 'urace start'.")
            return 0
        import os as _os
        try:
            _os.kill(pid, signal.SIGHUP)
            msg = {"status": "reloading", "pid": pid, "detail": "SIGHUP sent; daemon is reloading config"}
            print(json.dumps(msg) if as_json else f"Reloading config (pid={pid})...")
            return 0
        except OSError as _e:
            msg = {"status": "error", "detail": str(_e)}
            print(json.dumps(msg) if as_json else f"Reload failed: {_e}")
            return 1


def _cmd_shell_dashboard(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command in ("shell", "dashboard"):
        if args.command == "dashboard":
            from urace import tui as _tui
            return _tui.launch(config, SYSTEM_ROOT)
        from urace import shell as _shell
        return _shell.run_shell(config)


def _cmd_daemon(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "daemon":
        from urace import _daemon
        return _daemon.dispatch(args, config)


def _cmd_m2m(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "m2m":
        import sys as _sys
        _body = None
        if getattr(args, 'stdin', False):
            _body = _sys.stdin.read().strip()
        elif getattr(args, 'schema', None):
            _body = args.schema
        if not _body:
            print(json.dumps({'schema_version':'1.0','status':'error','exit_code':2,'error':'Provide JSON body as positional arg or via --stdin'}))
            return 2
        try:
            _req = json.loads(_body)
        except json.JSONDecodeError as _je:
            print(json.dumps({'schema_version':'1.0','status':'error','exit_code':2,'error':f'Invalid JSON: {_je}'}))
            return 2
        _m2m_cmd = _req.get('command') or None
        _m2m_argv = _req.get('argv') or None
        _m2m_params = _req.get('params') or None
        if not _m2m_cmd and not _m2m_argv:
            print(json.dumps({'schema_version':'1.0','status':'error','exit_code':2,'error':'Missing "command" or "argv" field'}))
            return 2
        import urace.cli as _cli_mod
        from urace import api_interface as _ai
        _result = _ai.execute(parser, _cli_mod.main, command=_m2m_cmd, params=_m2m_params, argv=_m2m_argv)
        print(json.dumps(_result, indent=2, sort_keys=True))
        return 0 if _result.get('exit_code', 0) == 0 else _result.get('exit_code', 2)
