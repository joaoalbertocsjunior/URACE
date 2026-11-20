from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from urace import analytics, command_surface
from urace._common import (
    ROOT, RUNTIME_ROOT, load_config, state_path,
    load_state, load_state_for_read,
)
from urace.inspection import command_catalog, top_level_help, vitals_snapshot
from urace.cli_output import _render_report_html


def _cmd_usage(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_cost(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_help(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "help":
        if not args.operation:
            if args.json:
                print(json.dumps({"schema_version": "1.0", "command": "help", "guide": "Use 'urace help <operation>' to get help for a specific operation. Use 'urace commands' for a full command catalog."}, indent=2))
                return 0
            print(top_level_help())
            print("\n  urace commands            full command catalog")
            return 0
        # 'urace help --all' or 'urace help all' → show full command catalog
        if list(args.operation) in (['--all'], ['all']):
            catalog = command_catalog()
            catalog["by_concern"] = command_surface.catalog(parser)
            if args.json:
                print(json.dumps(catalog, indent=2, sort_keys=True))
            else:
                for group, entries in catalog.items():
                    if group == "by_concern":
                        for concern, commands in entries.items():
                            print(concern + ": " + ", ".join(item["command"] for item in commands))
                        continue
                    print(group.replace("_", " ").title() + ":")
                    for entry in entries:
                        print(f"  {entry['command']}: {entry['purpose']}")
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


def _cmd_export(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_import(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_report_bare(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_audit(args, parser, config, state, fmt, _unknown, raw_args):
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
            from urace.peer_exchange import verify_audit_chain
            _ok, _broken = verify_audit_chain(_aud_records)
            if args.json: print(json.dumps({"status": "ok" if _ok else "chain_broken", "broken_at": _broken, "records": len(_aud_records)}))
            else: print(f"Audit chain: {'OK' if _ok else f'BROKEN at record {_broken}'} ({len(_aud_records)} records)")
        else:
            if args.json: print(json.dumps({"records": _aud_records[-20:], "total": len(_aud_records)}))
            else:
                for _r in _aud_records[-20:]:
                    print(f"  {_r.get('kind','?')} | {_r.get('operation','?')} | {_r.get('at','?')}")
        return 0


def _cmd_commands(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_portfolio(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "portfolio":
        helper = RUNTIME_ROOT / "urace" / "portfolio.py"
        if not helper.exists():
            parser.error("portfolio helper is not installed in this deployment")
        forwarded = (["--help"] if args.portfolio_help else []) + args.portfolio_args
        try:
            return command_surface.forward([sys.executable,str(helper),*forwarded],ROOT)
        except KeyboardInterrupt:
            return 130


def _cmd_report(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_auto_dry_run(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command in {"auto","autonomous"} and args.dry_run:
        state=load_state_for_read(config)
        if state is None:return 2
        payload={"mode":"dry-run","lifecycle":state.get("lifecycle_state"),"objectives":[{k:o.get(k) for k in ("id","title","status")} for o in state.get("objectives",[]) if o.get("status") in {"active","planned"}],"cycles_run":0,"executor_calls":0,"writes":0,"note":"Snapshot preview only; eligibility and future outcomes are not simulated."}
        print(json.dumps(payload,indent=2) if args.json else "Dry-run: no cycles, writes, network or Executor calls.\nLifecycle: "+str(payload["lifecycle"])+"\nExisting objectives: "+str(len(payload["objectives"])))
        return 0
