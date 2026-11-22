from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

from urace._common import (
    ROOT, SYSTEM_ROOT, load_config, load_state, save_config, save_state, state_path,
    atomic_write_text, now, identifier,
)
from urace.cli_state import stable_path
from urace import command_surface
from urace.cli_error import cli_error
from urace.cli_helpers import _inspect_list


def _cmd_features(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='features':
        from urace import runtime_features as _rf
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


def _cmd_rollback(args, parser, config, state, fmt, _unknown, raw_args):
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


def _cmd_peer_review(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == 'peer-review':
        from urace import peer_improvement as _pi
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


def _cmd_similarity(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == 'similarity':
        from urace import product_similarity as _ps
        from urace import peer_exchange as _pe
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


def _cmd_p2p(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command == 'p2p':
        import os as _os
        from pathlib import Path as _p2p_Path
        _p2p_action = getattr(args, 'action', None)
        if _p2p_action == 'keygen':
            from urace.evolution_guard import p2p_keygen as _p2p_keygen
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
            from urace.evolution_guard import build_p2p_update_bundle as _p2p_build_fn
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as _Ed
            from cryptography.hazmat.primitives.serialization import Encoding as _Enc, PublicFormat as _PF
            _sign_fns = []
            for _kp in (args.keys or []):
                _kpath = _p2p_Path(_kp)
                if not _kpath.exists():
                    return cli_error(f'key file not found: {_kpath}', as_json=getattr(args, 'json', False))
                try:
                    _priv_raw = bytes.fromhex(_kpath.read_text().strip())
                except ValueError:
                    return cli_error(f'{_kpath} must contain 64 hex chars', as_json=getattr(args, 'json', False))
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
                    print("  opentimestamps: anchored to Bitcoin calendar")
            return 0
        if _p2p_action == 'publish-update':
            from urace.peer_discovery import p2p_update_publish as _p2p_pub_fn
            _key_path = _p2p_Path(args.key)
            if not _key_path.exists():
                return cli_error(f'key file not found: {_key_path}', as_json=getattr(args, 'json', False))
            _bundle_path = _p2p_Path(args.bundle)
            if not _bundle_path.exists():
                return cli_error(f'bundle file not found: {_bundle_path}', as_json=getattr(args, 'json', False))
            _priv_raw = bytes.fromhex(_key_path.read_text().strip())
            _bundle   = json.loads(_bundle_path.read_text())
            _result   = _p2p_pub_fn(_bundle, _priv_raw, bundle_url=getattr(args, 'url', ''))
            if getattr(args, 'json', False):
                print(json.dumps(_result, indent=2))
            else:
                if _result.get("status") == "PUBLISHED":
                    print("  status:      PUBLISHED")
                    print(f"  dht_key:     {_result['dht_key']}")
                    print(f"  fingerprint: {_result['corpus_fingerprint']}")
                    print(f"  bundle_url:  {_result.get('bundle_url') or '(none)'}")
                    print(f"  announced:   {_result['announced_to']} nodes")
                else:
                    print(f"error: {_result.get('error')}", file=sys.stderr)
                    return 1
            return 0
        if _p2p_action == 'check-update':
            from urace.evolution_guard import RELEASE_AUTHORITY_PUB_KEY_HEX as _ra_key
            if not _ra_key:
                print("error: RELEASE_AUTHORITY_PUB_KEY_HEX not configured in evolution_guard.py",
                      file=sys.stderr); return 1
            try:
                _p2p_cfg  = load_config()
                _p2p_state = load_state(_p2p_cfg)
                from urace import peer_exchange as _pex
                _p2p_exch = _pex.Exchange(SYSTEM_ROOT / "urace" / "p2p")
                _p2p_exch.configure(enabled=True, network=True)
            except Exception as _e:
                return cli_error(str(_e), as_json=getattr(args, 'json', False))
            from urace.peer_discovery import p2p_update_check as _p2p_chk
            _chk = _p2p_chk(_p2p_exch, _ra_key)
            if getattr(args, 'json', False):
                print(json.dumps(_chk, indent=2))
            else:
                if _chk.get("available"):
                    print("  UPDATE AVAILABLE")
                    print(f"  remote fingerprint: {_chk['corpus_fingerprint']}")
                    print(f"  local  fingerprint: {_chk['local_fingerprint']}")
                    print(f"  bundle_url:         {_chk.get('bundle_url') or '(none)'}")
                    print("  Apply with: urace p2p apply-update --bundle <downloaded-bundle.json>")
                else:
                    print(f"  no update available  (local fingerprint: {_chk.get('local_fingerprint','')})")
            return 0
        if _p2p_action == 'apply-update':
            _bundle_path = _p2p_Path(args.bundle)
            if not _bundle_path.exists():
                return cli_error(f'bundle file not found: {_bundle_path}', as_json=getattr(args, 'json', False))
            _bundle = json.loads(_bundle_path.read_text())
            from urace.evolution_guard import apply_p2p_update_bundle as _p2p_apply_fn, verify_release_signature as _vrs2
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
        if _p2p_action == 'settle':
            _as_json = getattr(args, 'json', False)
            _peer = getattr(args, 'peer', '') or ''
            _action = getattr(args, 'settle_action', 'earn')
            _units = getattr(args, 'units', 0) or 0
            _reason = getattr(args, 'reason', 'manual') or 'manual'
            _op_id = getattr(args, 'operation_id', '') or ''
            if not _peer or not isinstance(_units, int) or _units <= 0:
                _err = {"status": "error", "error": "peer and positive units required"}
                print(json.dumps(_err) if _as_json else f"Error: {_err['error']}"); return 1
            try:
                from urace import peer_exchange as _pex
                _p2p_exch = _pex.Exchange(SYSTEM_ROOT / "urace" / "p2p")
                from urace.exchange_endpoint import handle_credit_settlement, SCHEMA
                _payload = {"schema": SCHEMA, "action": _action, "peer_id": _peer,
                            "units": _units, "reason": _reason, "operation_id": _op_id}
                _result = handle_credit_settlement(_p2p_exch, _peer, _payload)
            except Exception as _se:
                _result = {"status": "error", "error": str(_se)}
            print(json.dumps(_result, indent=2) if _as_json else
                  (f"Settlement {_action} {_units} units to {_peer}: {_result.get('status')}"
                   if _result.get("status") == "ok" else f"Error: {_result.get('error')}"))
            return 0 if _result.get("status") == "ok" else 1


def _cmd_product_create(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='product' and args.action=='create':
        if _unknown:parser.error('Unknown product creation arguments: '+' '.join(_unknown))
        from urace.product_creation import create
        import urace.cli as _cli_mod
        try:print(json.dumps(create(_cli_mod,args.description,args.creation_name),indent=2));return 0
        except (ValueError,OSError) as error:parser.error(str(error))


def _cmd_product_exchange(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='product' and args.action=='exchange':
        if _unknown:parser.error('Unrecognized exchange arguments: '+' '.join(_unknown))
        from urace.exchange_cli import run as run_exchange
        try:return run_exchange(args,load_config())
        except (ValueError,OSError) as error:parser.error(str(error))


def _cmd_network_exchange(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command in ('network', 'exchange'):
        if _unknown:parser.error('Unrecognized network arguments: '+' '.join(_unknown))
        from urace.exchange_cli import run as run_exchange
        try:return run_exchange(args,load_config())
        except (ValueError,OSError) as error:parser.error(str(error))


def _cmd_crypto(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='crypto':
        from urace import crypto_wallet as _cw
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized crypto arguments: '+' '.join(_unknown))
        try:
            verb=getattr(args,'wallet_verb',None)
            if verb=='init':
                result=_cw.wallet_init(wallet_dir=args.wallet_dir,overwrite=args.overwrite)
            elif verb=='show':
                result=_cw.wallet_show(wallet_dir=args.wallet_dir)
            elif verb=='sign':
                result=_cw.wallet_sign(payload=args.payload,wallet_dir=args.wallet_dir)
            elif verb=='rotate':
                _backup=getattr(args,'backup_dir',None)
                _bdir=Path(_backup) if _backup else None
                result=_cw.wallet_rotate(wallet_dir=args.wallet_dir,backup_dir=_bdir)
            else:
                parser.error('Unknown crypto wallet verb: '+str(verb))
            print(json.dumps(result,indent=2,sort_keys=True));return 0
        except FileExistsError as e:
            print(json.dumps({'status':'error','error':str(e)},indent=2));return 1
        except FileNotFoundError as e:
            print(json.dumps({'status':'error','error':str(e)},indent=2));return 1
        except (OSError,ValueError) as error:parser.error(str(error))


def _cmd_qualification(args, parser, config, state, fmt, _unknown, raw_args):
    if args.command=='qualification':
        command_surface.validate(args,raw_args,parser)
        if _unknown:parser.error('Unrecognized qualification arguments: '+' '.join(_unknown))
        try:
            action=getattr(args,'qualification_action',None)
            try:
                config=load_config();state=load_state(config)
            except RuntimeError as _e:
                if action=='list':
                    print(json.dumps({'status':'ok','evidence':[]},indent=2));return 0
                print(json.dumps({'status':'error','error':str(_e)},indent=2));return 1
            if action=='list':
                kind_filter=getattr(args,'evidence_kind',None)
                limit=getattr(args,'limit',20)
                evidence=state.get('evidence',[])
                if kind_filter:evidence=[e for e in evidence if e.get('kind')==kind_filter]
                result={'status':'ok','evidence':[{'id':e['id'],'kind':e.get('kind','unknown'),'at':e.get('at',''),'has_proposal':bool(e.get('proposal'))} for e in evidence[-limit:]]}
            elif action=='replay':
                eid=args.evidence_id
                evidence=state.get('evidence',[])
                record=next((e for e in evidence if e.get('id')==eid),None)
                if not record:
                    print(json.dumps({'status':'error','error':f'Evidence not found: {eid}'},indent=2));return 1
                # Find associated decisions
                decisions=state.get('decisions',[])
                linked_decisions=[d for d in decisions if d.get('evidence_id')==eid or eid in d.get('provenance_ids',[])]
                # Hash-verify proposal integrity
                import hashlib as _hl
                proposal=record.get('proposal',{})
                proposal_str=json.dumps(proposal,sort_keys=True)
                replay_hash=_hl.sha256(proposal_str.encode()).hexdigest()
                stored_hash=record.get('content_hash')
                # Re-assess score from stored evidence fields
                stored_score=None
                replayed_score=None
                for d in linked_decisions:
                    if d.get('score_delta') is not None:
                        stored_score=d['score_delta']
                        break
                # Re-compute score
                replay_mode=getattr(args,'replay_mode','estimate')
                criteria_drift=None
                evaluation_weights_current=None
                evaluation_weights_at_qualification=None
                if proposal:
                    import math as _math
                    desc_len=len(str(proposal.get('description',''))+str(proposal.get('changes','')))
                    replayed_score=round(min(1.0,_math.log2(1+desc_len/200)),4)
                if replay_mode=='full':
                    # Full mode: use evaluation_system weights to detect criteria drift
                    ev_sys=config.get('evaluation_system',{})
                    evaluation_weights_current=ev_sys.get('weights',{})
                    # Find stored weights from the linked decision (if it recorded them)
                    stored_weights=next((d.get('evaluation_weights') for d in linked_decisions if d.get('evaluation_weights')),None)
                    evaluation_weights_at_qualification=stored_weights
                    if stored_weights is not None:
                        criteria_drift=evaluation_weights_current!=stored_weights
                        if not criteria_drift and stored_score is not None:
                            replayed_score=stored_score  # deterministically reproducible
                        else:
                            criteria_drift=True
                    else:
                        criteria_drift=None  # unknown — weights not stored in original decision
                    # Weighted re-score from proposal assessment fields
                    if evaluation_weights_current:
                        assessment=str(proposal.get('evaluation_assessment',''))
                        weights=list(evaluation_weights_current.values())
                        total_weight=sum(weights)
                        if total_weight>0 and assessment:
                            # Heuristic: each component contributes proportionally if mentioned in assessment
                            component_scores=[]
                            for component,w in evaluation_weights_current.items():
                                mentioned=component.lower() in assessment.lower()
                                component_scores.append(w*(1.0 if mentioned else 0.5))
                            replayed_score=round(sum(component_scores)/total_weight,4)
                integrity='verified' if (stored_hash and stored_hash==replay_hash) else ('no_stored_hash' if not stored_hash else 'mismatch')
                result={
                    'status':'ok',
                    'evidence_id':eid,
                    'kind':record.get('kind','unknown'),
                    'at':record.get('at',''),
                    'replay_mode':replay_mode,
                    'integrity':integrity,
                    'replay_hash':replay_hash,
                    'linked_decisions':len(linked_decisions),
                    'stored_score_delta':stored_score,
                    'replayed_score_estimate':replayed_score,
                    'score_match': stored_score is not None and replayed_score is not None and abs(stored_score-replayed_score)<0.5,
                    'decision_outcomes':[d.get('outcome') for d in linked_decisions],
                    'proposal_summary':{
                        'has_description':bool(proposal.get('description')),
                        'has_changes':bool(proposal.get('changes')),
                        'field_count':len(proposal),
                    },
                }
                if replay_mode=='full':
                    result['evaluation_weights_current']=evaluation_weights_current
                    result['evaluation_weights_at_qualification']=evaluation_weights_at_qualification
                    result['criteria_drift']=criteria_drift
            else:
                parser.error('Unknown qualification action: '+str(action))
            print(json.dumps(result,indent=2,sort_keys=True));return 0
        except FileNotFoundError:
            return cli_error('State not found — run urace init first', hint='urace init', as_json=args.json)
        except (OSError,ValueError,KeyError) as error:parser.error(str(error))
