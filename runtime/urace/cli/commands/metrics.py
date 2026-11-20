from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from urace._common import (
    ROOT, CONFIG_PATH, SYSTEM_ROOT,
    load_config, load_state, load_state_for_read, save_config, save_state,
    state_path, state_lock, now, identifier,
)
from urace.inputs import queue_input
from urace import executor as intelligent_executor
from urace.cli_emit import _emit_trace
from urace.cli_state import initial_state
from urace.cli_helpers import (
    _help_action, _inspect_list, _check_staleness,
    _build_inspection_surface, _ledger_size_warning,
)
from urace.inspection import (
    vitals_snapshot, render_vitals, evolution_vital, work_evaluations, goal_portfolio,
)
# NOTE: _handle_data_command and _SEVERITY_ORDER from urace.cli are accessed
# lazily inside the functions to avoid circular imports.


def _cmd_data(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "data":
        import urace.cli as _cli_mod
        if args.data_action in {"list", "inspect", "status"} or (
            args.data_action == "credential" and getattr(args, "credential_action", None) == "inspect"
        ):
            state = _cli_mod.load_state_for_read(config)
            if state is None:
                print("URACE is not initialized; run `urace init`", file=sys.stderr)
                return 1
            return _cli_mod._handle_data_command(args, state, config)
        with state_lock(state_path(config)):
            state = _cli_mod.load_state(config)
            before=json.dumps(state,sort_keys=True)
            result = _cli_mod._handle_data_command(args, state, config)
            if json.dumps(state,sort_keys=True)!=before:save_state(config, state)
        return result


def _cmd_trace(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_feedback(args, parser, config, state, fmt, _unknown, raw_args):
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
                    raw = (_sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8"))
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


def _cmd_resource(args, parser, config, state, fmt, _unknown, raw_args):
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
        import urace.cli as _cli_mod
        config_ro = _cli_mod.load_config()
        state_data = _cli_mod.load_state(config_ro)
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


def _cmd_executor_status(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "executor" and args.action == "status":
        settings = config.get("executor", {})
        state = load_state_for_read(config) or {}
        pool = state.get("executor_state", {}).get("provider_pool", {})
        health = intelligent_executor.pool_availability(settings, pool) if settings.get("enabled") else {"available": False, "reason": "detached", "providers": []}
        print(json.dumps({"attached": bool(settings.get("enabled")), **health,
                          "workflow_observations":state.get('executor_state',{}).get('workflow_observations',{}),
                          "availability_scope":"Generic execution readiness; workflow observations describe actual artifact-only calls separately"}, indent=2))
        return 0


def _cmd_check_vitals(args, parser, config, state, fmt, _unknown, raw_args, preflight_hints=()):
    if args.command in {"check", "vitals"}:
        import urace.cli as _cli_mod
        _SEVERITY_ORDER = _cli_mod._SEVERITY_ORDER
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
            surface['preflight_hints'] = list(preflight_hints)
            _lw = _ledger_size_warning(state_path(config))
            if _lw is not None:
                surface['ledger_health'] = _lw
            _check_query = getattr(args, 'query', None)
            if _check_query:
                _q = _check_query.lower()
                def _matches(v: object) -> bool:
                    return _q in str(v).lower()
                surface = {k: v for k, v in surface.items() if _matches(k) or _matches(v)}
            # ── network section ───────────────────────────────────────────────
            _net_section: dict = {'status': 'not_initialized'}
            try:
                from urace import peer_exchange as _pex_s
                _exch_root = SYSTEM_ROOT / 'exchange'
                _policy_path = _exch_root / 'policy.json'
                if _policy_path.exists():
                    _exc_s = _pex_s.Exchange(_exch_root)
                    _policy = _exc_s.load()
                    _peers = _policy.get('peers', {})
                    _active_tunnel = _policy.get('active_tunnel_endpoint')
                    _net_section = {
                        'status': 'initialized',
                        'mode': _policy.get('network_mode', _policy.get('mode', 'hybrid')),
                        'roles': _policy.get('node_roles', []),
                        'peers': len(_peers),
                        'tunnel': 'up' if _active_tunnel else 'down',
                    }
                    if _active_tunnel:
                        _net_section['tunnel_url'] = _active_tunnel
                    _id_cert = _exch_root / 'identity-cert.pem'
                    if _id_cert.exists():
                        import hashlib as _hl, ssl as _ssl
                        _der = _ssl.PEM_cert_to_DER_cert(_id_cert.read_text())
                        _net_section['peer_id'] = _hl.sha256(_der).hexdigest()[:16] + '…'
            except Exception:
                _net_section = {'status': 'error'}
            # ── executor section ──────────────────────────────────────────────
            _exc_section: dict = {}
            try:
                _exc_cfg = config.get('executor', {})
                _exc_providers = _exc_cfg.get('providers', [])
                _exc_avail = [p for p in _exc_providers if p.get('enabled', True)]
                _now_ts = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).timestamp()
                _calls_24h = [c for c in state.get('executor_state', {}).get('executor_calls', [])
                              if _now_ts - __import__('datetime').datetime.fromisoformat(c['at']).timestamp() < 86400]
                _exc_section = {
                    'enabled': bool(_exc_cfg.get('enabled')),
                    'providers': len(_exc_providers),
                    'available': len(_exc_avail),
                    'calls_24h': len(_calls_24h),
                    'ids': [p.get('id') for p in _exc_avail],
                }
            except Exception:
                pass
            # ── goals section ─────────────────────────────────────────────────
            _goals_section: dict = {}
            try:
                _objs = state.get('objectives', [])
                _goals_section = {
                    'active': len([o for o in _objs if o.get('status') == 'active']),
                    'pending': len([o for o in _objs if o.get('status') == 'PENDING']),
                    'blocked': len([o for o in _objs if o.get('status') == 'blocked']),
                    'total': len(_objs),
                    'auto_goals': config.get('auto_goals', {}).get('enabled', False),
                }
            except Exception:
                pass
            # ── config section ────────────────────────────────────────────────
            _cfg_section: dict = {}
            try:
                from urace._common import CONFIG_PATH as _cfgp
                _cfg_section = {
                    'path': str(_cfgp),
                    'effort': config.get('resources', {}).get('effort', 'medium'),
                    'self_evolution': config.get('self_evolution_policy', {}).get('mode', 'auto'),
                    'auto_goals': config.get('auto_goals', {}).get('enabled', False),
                    'capability_envelope_waived': bool(config.get('capability_envelope_waived')),
                }
                if _cfgp.exists():
                    import os as _os
                    _cfg_section['modified'] = __import__('datetime').datetime.fromtimestamp(
                        _os.path.getmtime(_cfgp), tz=__import__('datetime').timezone.utc
                    ).strftime('%Y-%m-%dT%H:%M:%SZ')
            except Exception:
                pass
            surface['network'] = _net_section
            surface['executor'] = _exc_section
            surface['goals'] = _goals_section
            surface['config'] = _cfg_section
            # ── dedup gaps by (kind, detail) for display ──────────────────────
            def _dedup_gaps(gaps: list) -> list:
                seen: dict = {}
                for g in gaps:
                    key = (g.get('kind', ''), g.get('detail', ''))
                    if key not in seen:
                        seen[key] = {**g, '_count': 1}
                    else:
                        seen[key]['_count'] += 1
                return list(seen.values())
            # ── group gaps by kind for display ────────────────────────────────
            def _group_gaps(gaps: list) -> dict:
                groups: dict = {}
                for g in gaps:
                    k = g.get('kind', 'unknown')
                    groups.setdefault(k, []).append(g)
                return groups
            if args.json:
                # JSON: deduplicate, add _count, keep structured
                surface['blocking_gaps'] = _dedup_gaps(surface.get('blocking_gaps', []))
                surface['warning_gaps'] = _dedup_gaps(surface.get('warning_gaps', []))
                print(json.dumps(surface, indent=2, sort_keys=True))
            else:
                _verbose = getattr(args, 'verbose', False)
                _lc = surface['lifecycle_state']
                _blk_raw = surface.get("blocking_gaps", [])
                _wrn_raw = surface.get("warning_gaps", [])
                _blk = _dedup_gaps(_blk_raw)
                _wrn = _dedup_gaps(_wrn_raw)
                _health = "OK" if not _blk else "BLOCKED"
                from urace.version import RUNTIME_VERSION as _rv
                print(f"urace {_rv} — {_lc}")
                print(f"lifecycle:  {_lc:<14}  health: {_health}  blocking: {len(_blk_raw)}  warnings: {len(_wrn_raw)}")
                # network
                _ns = _net_section.get('status', 'unknown')
                if _ns == 'not_initialized':
                    print("network:    not_initialized")
                elif _ns == 'error':
                    print("network:    error reading policy")
                else:
                    _roles_str = ','.join(_net_section.get('roles', [])) or 'none'
                    _tunnel_str = _net_section.get('tunnel_url', _net_section.get('tunnel', 'down'))
                    print(f"network:    mode={_net_section.get('mode','?')}  roles={_roles_str}  peers={_net_section.get('peers',0)}  tunnel={_tunnel_str}")
                # executor
                if _exc_section:
                    _ids_str = ','.join(_exc_section.get('ids', [])) or 'none'
                    print(f"executor:   enabled={_exc_section.get('enabled',False)}  providers={_ids_str}  calls_24h={_exc_section.get('calls_24h',0)}")
                # goals
                if _goals_section:
                    print(f"goals:      active={_goals_section.get('active',0)}  pending={_goals_section.get('pending',0)}  blocked={_goals_section.get('blocked',0)}  auto={_goals_section.get('auto_goals',False)}")
                # config
                if _cfg_section:
                    _ce = '(waived)' if _cfg_section.get('capability_envelope_waived') else 'not set'
                    print(f"config:     effort={_cfg_section.get('effort','?')}  self_evolution={_cfg_section.get('self_evolution','?')}  capability_envelope={_ce}")
                # blocking gaps — always show, deduplicated
                if _blk:
                    _blk_total = len(_blk_raw)
                    _blk_unique = len(_blk)
                    _extra = f"  ({_blk_total} total, {_blk_unique} unique)" if _blk_total != _blk_unique else ''
                    print(f"\nBLOCKING{_extra}:")
                    for g in _blk:
                        _cnt = g.get('_count', 1)
                        _sfx = f"  ×{_cnt}" if _cnt > 1 else ''
                        print(f"  [{g.get('kind')}] {g.get('detail', '')}{_sfx}")
                        # actionable hint
                        if g.get('kind') == 'onboard-config-incomplete':
                            print("    → add missing fields to config.json, then: urace reload")
                        elif g.get('kind') == 'onboard-no-readable-product-files':
                            print("    → check product_files paths in config.json")
                # warnings — grouped by kind, capped unless --verbose
                if _wrn:
                    _wrn_groups = _group_gaps(_wrn_raw)
                    _wrn_kinds = len(_wrn_groups)
                    _wrn_total = len(_wrn_raw)
                    print(f"\nWARNINGS ({_wrn_total} total, {_wrn_kinds} kind{'s' if _wrn_kinds != 1 else ''}):")
                    for kind, items in _wrn_groups.items():
                        if len(items) == 1:
                            print(f"  [{kind}] {items[0].get('detail', '')}")
                        else:
                            sample = items[0].get('detail', '')[:60]
                            print(f"  [{kind}] ×{len(items)}  e.g. {sample}")
                            if _verbose:
                                for item in items[1:]:
                                    print(f"    {item.get('detail', '')}")
                    if not _verbose and any(len(v) > 1 for v in _wrn_groups.values()):
                        print("  → urace status --verbose  for full list")
                # preflight hints
                if preflight_hints:
                    print("\npreflight_hints:")
                    for _h in preflight_hints:
                        print(f"  [{_h['level']}] {_h['message']} — {_h['action']}")
            if args.fail_on and any(_SEVERITY_ORDER.get(g.get("severity", "INFO"), 0) >= _SEVERITY_ORDER.get(args.fail_on, 999) for g in state.get("integrity_gaps", []) if g.get("active", True)):
                return 1
        else:
            snapshot = vitals_snapshot(config, state)
            if args.json:
                if preflight_hints:
                    snapshot['hints'] = list(preflight_hints)
                print(json.dumps(snapshot, indent=2, sort_keys=True))
            else:
                print(render_vitals(snapshot))
            if args.fail_on and any(_SEVERITY_ORDER.get(g.get("severity", "INFO"), 0) >= _SEVERITY_ORDER.get(args.fail_on, 999) for g in state.get("integrity_gaps", []) if g.get("active", True)):
                return 1
        return 0


def _cmd_quality(args, parser, config, state, fmt, _unknown, raw_args):
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
            from urace.value_discovery import execution_quality_views
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


def _cmd_compliance(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "compliance":
        state = load_state_for_read(config)
        if state is None:
            return 2
        import datetime as _dt
        cs_map: dict[str, Any] = state.get("compliance_state", {})
        records: list[dict] = list(state.get("compliance_records", []))
        if args.domain:
            cs_map = {k: v for k, v in cs_map.items() if k == args.domain}
            records = [r for r in records if r.get("domain") == args.domain]
        since = getattr(args, "since", None); until = getattr(args, "until", None)
        if since:
            records = [r for r in records if str(r.get("evaluated_at", "")) >= since]
        if until:
            records = [r for r in records if str(r.get("evaluated_at", "")) <= until + "Z"]
        export_path = getattr(args, "export", None)
        if export_path:
            _ep = Path(export_path)
            if _ep.suffix == ".jsonl":
                _ep.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
            else:
                _ep.write_text(json.dumps({"compliance_records": records, "exported_at": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")}, indent=2, sort_keys=True))
            print(json.dumps({"status": "ok", "exported": len(records), "file": export_path}) if args.json else f"Exported {len(records)} records to {export_path}")
            return 0
        recent = records[-args.history:]
        domains_summary = [
            {"domain": d, "status": e.get("status", "UNKNOWN"),
             "consecutive_clean": e.get("consecutive_clean", 0),
             "last_checked_at": e.get("last_checked_at"),
             "violation_refs": e.get("violation_refs", [])}
            for d, e in cs_map.items()
        ]
        non_compliant_domains = [d for d in domains_summary if d["status"] == "NON_COMPLIANT"]
        payload: dict[str, Any] = {
            "domains": domains_summary,
            "total_records": len(state.get("compliance_records", [])),
            "compliant": sum(1 for r in state.get("compliance_records", []) if r.get("status") == "COMPLIANT"),
            "non_compliant": sum(1 for r in state.get("compliance_records", []) if r.get("status") == "NON_COMPLIANT"),
            "recent_records": recent,
            "strict_pass": len(non_compliant_domains) == 0,
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
        if getattr(args, "strict", False) and non_compliant_domains:
            if not args.json:
                print(f"STRICT: {len(non_compliant_domains)} non-compliant domain(s): {', '.join(d['domain'] for d in non_compliant_domains)}")
            return 1
        return 0


def _cmd_milestone(args, parser, config, state, fmt, _unknown, raw_args):
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

        from urace.milestone_feedback import assess as assess_milestone
        milestone_phases=[assess_milestone(config,state,m) for m in all_milestones if isinstance(m,dict)]
        active_phase=next((m for m in milestone_phases if active_ms and m['id']==active_ms.get('id')),None)

        from urace.milestone_suggestions import suggestions as suggest_milestones
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


def _cmd_source_metric_vital_goal(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_policy(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_budget(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_evaluation(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_executor_circuit_breaker(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "executor" and args.action == "circuit-breaker":
        from urace import circuit_breaker as _cb
        verb = getattr(args, 'cb_action', 'status')
        executor_settings = config.get("executor", {})
        pool_state = config.get("executor_pool_state", {})
        try:
            if verb == 'status':
                result = _cb.status(executor_settings, pool_state)
            elif verb == 'reset':
                pid = getattr(args, 'cb_provider', None)
                if not pid: parser.error("circuit-breaker reset requires --cb-provider <provider_id>")
                result = _cb.reset(pid, executor_settings, pool_state)
                with state_lock(CONFIG_PATH):
                    cfg = load_config()
                    cfg.setdefault("executor_pool_state", {}).update({pid: pool_state.get(pid, {})})
                    save_config(cfg)
            print(json.dumps(result, indent=2, sort_keys=True)); return 0
        except ValueError as e:
            print(json.dumps({'status':'error','error':str(e)},indent=2)); return 1


def _cmd_executor_attach_detach(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_pause(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == "pause":
        config = load_config()
        try:
            _state_path = state_path(config)
        except Exception:
            print(json.dumps({"status": "not_running", "note": "URACE is not initialized; nothing to stop"}) if getattr(args, 'json', False) else "URACE is not initialized; nothing to stop.")
            return 0
        with state_lock(_state_path):
            try:
                state = load_state(config)
            except RuntimeError:
                print(json.dumps({"status": "not_running", "note": "URACE is not initialized; nothing to stop"}) if getattr(args, 'json', False) else "URACE is not initialized; nothing to stop.")
                return 0
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


def _cmd_resume(args, parser, config, state, fmt, _unknown, raw_args):
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
