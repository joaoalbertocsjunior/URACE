"""Phase H — work commands extracted from urace.cli.__init__."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from urace._common import (
    ROOT, CONFIG_PATH, SYSTEM_ROOT,
    load_config, load_state, load_state_for_read, save_config, save_state,
    state_path, state_lock, now, identifier, atomic_write_json,
)
from urace.inputs import queue_input
from urace import api_interface, freeform_routing
from urace import patterns as pattern_catalog_module
from urace import rules as rule_ledger_module
from urace.cli_emit import _emit_gap
from urace.cli_helpers import (
    _help_action, _inspect_list,
    _refresh_derived_manifests, _refresh_derived_construct_sets,
    _derive_capabilities_from_patterns, _derive_milestone_from_state,
    _build_inspection_surface,
)
from urace.cli_state import _current_spec_version
from urace.cli_output import (
    _validate_freeform_query, _resolve_scope_target, _print_fmt, _utcnow,
)
from urace.cli_state import initial_state
from urace.inspection import context_view
# NOTE: main, BUILTIN_BUNDLES from urace.cli used lazily inside functions


def _cmd_github(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_git(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_gh(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_api(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "api":
        if args.action == "protocols":
            from urace.protocol_catalog import describe
            print(json.dumps(describe(),indent=2));return 0
        if args.action == "help":
            return _help_action("""URACE External Interface Guide (EIP §62w)
    ══════════════════════════════════════════
    Machine interface for external tools and automation systems.

    Single-call JSON interface (identical envelope, two syntaxes):
      urace m2m '{"command":"status","params":{}}'
      urace api call --command status [--params <json>] [--stream]
      urace api call --argv <JSON-string-array> [--stream]

    All calls return: {"schema_version","command","status","exit_code","output","stderr","streamed"}
      See: urace api schema  (full field documentation)

    Discovery and batch:
      urace api commands           -- complete installed grammar with argument types
      urace api schema             -- M2M envelope schema and protocol reference
      urace api batch --input-json <path|-> [--continue-on-error]

    Persistent server:
      urace api serve              -- MCP stdio (default)
      urace api serve --transport a2a --port 8765 --token-env URACE_A2A_TOKEN

    Config management via M2M:
      urace m2m '{"command":"config get","params":{"path":"executor.enabled"}}'
      urace m2m '{"command":"config set","params":{"path":"executor.enabled","value":"true"}}'
      urace m2m '{"command":"reload"}'

    Machine feedback:
      urace feedback submit <id> --input-json params.json --json
      (params.json: {"signal":"POSITIVE","detail":"optional"})""", args)

        if args.action == "commands":
            print(json.dumps(api_interface.metadata(parser),indent=2));return 0
        if args.action == "schema":
            _m2m_schema = {
                "schema_version": "1.0",
                "protocol": "URACE M2M v1",
                "request": {
                    "description": "JSON object sent to urace m2m or as --params to api call",
                    "fields": {
                        "command": {"type": "string", "required": "one of command/argv", "description": "Space-separated command path, e.g. \"config set\" or \"status\""},
                        "params":  {"type": "object", "required": False, "description": "Named arguments; positional args mapped by parser; omit for commands that take no arguments"},
                        "argv":    {"type": "array",  "required": "one of command/argv", "description": "Exact CLI argument array, alternative to command+params"},
                    }
                },
                "response": {
                    "description": "JSON envelope returned by every M2M call",
                    "fields": {
                        "schema_version": {"type": "string", "value": "1.0"},
                        "command":    {"type": "string|array", "description": "Echo of the request command or argv"},
                        "status":     {"type": "string", "values": ["ok", "error"], "description": "ok when exit_code==0"},
                        "exit_code":  {"type": "integer", "description": "0=success, 1=warning/not-found, 2=bad-input/error"},
                        "output":     {"type": "object|array|string|null", "description": "Parsed JSON from command stdout, or raw string"},
                        "stderr":     {"type": "string", "description": "Captured stderr text; empty on success"},
                        "streamed":   {"type": "boolean", "description": "True when --stream was used; output is null and events arrive as NDJSON"},
                        "error":      {"type": "string", "description": "Human-readable error when status==error and input was invalid"},
                    }
                },
                "config_paths": "urace api commands | python3 -c \"import json,sys; [print(c['command']) for c in json.load(sys.stdin)['commands']]\"",
                "examples": [
                    {"request": {"command": "status"}, "note": "lifecycle + health snapshot"},
                    {"request": {"command": "config get", "params": {"path": "executor.enabled"}}, "note": "read one config field"},
                    {"request": {"command": "config set", "params": {"path": "executor.enabled", "value": "true"}}, "note": "write one config field"},
                    {"request": {"command": "config fields"}, "note": "all schema-defined fields with types and defaults"},
                    {"request": {"command": "reload"}, "note": "hot-reload config.json without restart"},
                ],
            }
            print(json.dumps(_m2m_schema, indent=2)); return 0
        if args.action == "serve":
            if args.transport == "a2a":
                from urace.a2a_server import serve as serve_a2a
                return serve_a2a(parser, policy_path=args.policy, port=args.port, token_env=args.token_env)
            from urace.mcp_server import serve
            return serve(parser, policy_path=args.policy)
        if args.action == "call":
            if not args.api_command and not args.argv:
                print(json.dumps({"schema_version":"1.0","status":"error","exit_code":1,"error":"api call requires --command or --argv","output":None}));return 1
            try:
                params=json.loads(args.params) if args.params else None
                argv=json.loads(args.argv) if args.argv else None
                import urace.cli as _cli_mod
                result=api_interface.execute(parser,_cli_mod.main,args.api_command,params,argv,stream=args.stream)
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
            import urace.cli as _cli_mod
            for entry in entries:
                if not isinstance(entry,dict):result={"schema_version":"1.0","status":"error","exit_code":2,"output":None,"error":"batch entry must be an object"}
                elif set(entry)-{'command','params','argv'}:result={"schema_version":"1.0","status":"error","exit_code":2,"output":None,"error":"unknown batch entry keys"}
                else:result=api_interface.execute(parser,_cli_mod.main,entry.get('command'),entry.get('params'),entry.get('argv'),stream=args.stream)
                results.append(result)
                if result['exit_code']:
                    final_rc=result['exit_code']
                    if not args.continue_on_error:break
            print(json.dumps({"schema_version":"1.0","status":"ok" if not final_rc else "error","results":results,"exit_code":final_rc}));return final_rc


def _cmd_web(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "web":
        from urace.web.server import serve, capabilities
        caps = capabilities()
        if caps["status"] != "READY":
            missing = caps.get("missing", [])
            msg = f"web deps missing: {', '.join(missing)}. Install with: pip install 'urace[web]'"
            print(json.dumps({"status": "error", "error": msg}) if getattr(args, 'json', False) else msg, file=sys.stderr)
            return 1
        host = getattr(args, "host", "127.0.0.1") or "127.0.0.1"
        port = getattr(args, "port", 7475) or 7475
        token = getattr(args, "token", None)
        return serve(config, host=host, port=port, token=token)


def _cmd_derive(args, parser, config, state, fmt, _unknown, raw_args):
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
            import urace.cli as _cli_mod
            if getattr(args, "json", False):
                print(json.dumps({"bundles": {k: {"construct_ids": v} for k, v in _cli_mod.BUILTIN_BUNDLES.items()}}, indent=2, sort_keys=True))
            else:
                print("Built-in FeatureBundles (use with --bundle <name>):")
                for bname, bids in _cli_mod.BUILTIN_BUNDLES.items():
                    print(f"  {bname:30s}  constructs: {', '.join(bids)}")
            return 0

        from urace import derived_artifacts
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
        import urace.cli as _cli_mod
        BUILTIN_BUNDLES = _cli_mod.BUILTIN_BUNDLES
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
                    from urace import freeform_routing as _fr
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


def _cmd_context(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "context":
        state = load_state_for_read(config)
        if state is None:
            return 2
        if args.action in {"graph","attention"}:
            from urace.context_relations import from_state,related,attention
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


def _cmd_classify(args, parser, config, state, fmt, _unknown, raw_args):
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
        from urace.product_creation import explicit_creation,interpret,apply_interpreted
        interpreted=interpret(args.text,config.get('product_registry',[]),config.get('active_product') or config.get('product'))
        if explicit_creation(args.text) or any(i['kind']=='new_product' for i in interpreted['intents']):
            if interpreted['status']=='INTERPRETED':
                import urace.cli as _cli_mod
                result=apply_interpreted(_cli_mod,interpreted);print(json.dumps(result,indent=2));return 0 if result['status']=='BOOTSTRAPPED_OR_QUEUED' else 2
            print(json.dumps({**interpreted,'actions_taken':[],'reason':'Resolve the shown scope/relationship ambiguity before mutation; original input retained'},indent=2));return 2
        state=load_state_for_read(config) if state_path(config).exists() else {"executor_state":{},"interpretation_only_uninitialized_product":True}
        if state is None:return 2
        import urace.cli as _cli_mod
        return freeform_routing.route(_cli_mod,args,config,state,parser)


def _cmd_add(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_declare(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "declare":
        # r101: declare is a deprecated alias for add (r100 backwards compat)
        dep_sub = getattr(args, "declare_subcommand", None)
        if not dep_sub:
            print("Warning: `declare` is deprecated; use `urace add context|goal|source|metric|vital` instead.", file=sys.stderr)
            parser.error("declare requires a subcommand: context, goal, source, metric, vital")
        print(f"Warning: `declare {dep_sub}` is deprecated; use `urace add {dep_sub}` instead.", file=sys.stderr)
        # Re-dispatch to add handler via main()
        remainder = list(getattr(args, "declare_remainder", []))
        import urace.cli as _cli_mod
        return _cli_mod.main(["add", dep_sub] + remainder)


def _cmd_add_shorthand(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_intent(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_constraint(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_explain(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_rules(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_compact_decompact_amend_why_crc(args, parser, config, state, fmt, _unknown, raw_args):
    _fmt = getattr(args, "format", None) or fmt
    if args.command in {"compact", "decompact", "amend", "why", "crc"}:
        from urace import compaction as _compaction_module
        from urace import cognitive_resume as _crc_module

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
                    if _mp_fmt == "json": _mp_argv += ["--format", "json"]
                    _mp_argv += ["--product", _mp_name]
                elif args.command == "decompact":
                    _mp_argv += [args.compaction_event_id]
                    if getattr(args, "field_path", None): _mp_argv += ["--field-path", args.field_path]
                    if getattr(args, "record_id", None): _mp_argv += ["--record-id", args.record_id]
                    if getattr(args, "json", False): _mp_argv.append("--json")
                    if _mp_fmt == "json": _mp_argv += ["--format", "json"]
                    _mp_argv += ["--product", _mp_name]
                elif args.command == "crc":
                    _mp_argv += [args.action]
                    if getattr(args, "json", False): _mp_argv.append("--json")
                    if _mp_fmt == "json": _mp_argv += ["--format", "json"]
                    _mp_argv += ["--product", _mp_name]
                print(f"  [{_mp_name}]")
                import urace.cli as _cli_mod
                _rc = _cli_mod.main(_mp_argv)
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
            from urace.compaction import _DEFAULT_GOVERNANCE, _PROHIBITED_FIELDS, get_compaction_status
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
            from urace import decision_record as _dr_module
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
