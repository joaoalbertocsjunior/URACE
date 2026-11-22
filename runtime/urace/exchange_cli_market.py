"""Market sub-module for exchange_cli: market stats, feature, bundle, chunk, rule."""
from pathlib import Path
import json
import hashlib
import time as _time_mod


def _bounded_file(name, limit, artifact=False):
    """Local copy of bounded_file for use within this sub-module."""
    path = Path(name)
    if '..' in path.parts:
        raise ValueError('Parent traversal prohibited')
    for candidate in (path, path.resolve()):
        if any(part.startswith('.') for part in candidate.parts if part != '.'):
            raise ValueError('Protected file path prohibited')
    probe = Path(path.anchor or '.')
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        probe = probe / part
        if probe.is_symlink():
            raise ValueError('Symlink path prohibited')
    if artifact:
        _BLOCKED = ('credential', 'secret', '.env', 'password', 'private_key', 'id_rsa', 'id_ed25519')
        if any(word in path.name.lower() for word in _BLOCKED):
            raise ValueError('Artifact filename matches sensitive file pattern — excluded for safety')
        from ._common import SYSTEM_ROOT
        path.resolve().relative_to(SYSTEM_ROOT.resolve())
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Bounded regular file required')
    return path.read_text()


def _check_auto_delist(feature_id: str, exchange) -> dict:
    """Check if a feature should be auto-delisted due to sustained negative outcomes.

    Rule: negative_count >= 3 AND (negative_count - positive_count) >= 3.
    If triggered, writes FEATURE_AUTO_DELISTED to ledger and returns auto_delisted=True.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return {"auto_delisted": False, "reason": "audit_unavailable"}
    positive = 0
    negative = 0
    for r in rows:
        if r.get("kind") == "FEATURE_RATING" and r.get("feature_id") == feature_id:
            outcome = r.get("outcome", "")
            if outcome == "positive":
                positive += 1
            elif outcome == "negative":
                negative += 1
    if negative >= 3 and (negative - positive) >= 3:
        import time as _t
        exchange.append_audit_row({
            "kind": "FEATURE_AUTO_DELISTED",
            "feature_id": feature_id,
            "reason": "sustained_negative_outcomes",
            "negative_count": negative,
            "positive_count": positive,
            "at_unix": _t.time(),
        })
        return {"auto_delisted": True, "reason": "sustained_negative_outcomes",
                "negative_count": negative, "positive_count": positive}
    return {"auto_delisted": False, "negative_count": negative, "positive_count": positive}


def _listing_expired(listing: dict, settings: dict) -> bool:
    """Return True if a listing's listed_at age exceeds listing_ttl_days (default 90)."""
    ttl_days = int(settings.get("listing_ttl_days", 90))
    listed_at = listing.get("listed_at", "")
    if not listed_at:
        return False
    try:
        from datetime import datetime, timezone, timedelta
        age = datetime.now(timezone.utc) - datetime.fromisoformat(listed_at)
        return age > timedelta(days=ttl_days)
    except (ValueError, TypeError):
        return False


def _validate_freeform_query(q, max_bytes=4096):
    """Validate a freeform search/query string.

    Returns the cleaned query or raises ValueError with a clear message.
    Accepts None (blank = return all) and passes it through unchanged.
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


def _run_rule(exchange, args, config, verb):
 result = None
 if verb=='set':result=exchange.rule(args.peer_id,args.feature_id,args.direction,args.allow)
 elif verb=='export':
  cfg=exchange.load();rules=cfg.get('rules',{})
  payload=json.dumps(rules,indent=2,sort_keys=True)
  if getattr(args,'export_file',None):Path(args.export_file).write_text(payload);result={'status':'exported','rule_count':len(rules),'file':args.export_file}
  else:result={'rules':rules,'rule_count':len(rules)}
 elif verb=='import':
  src=Path(args.import_file)
  if not src.is_file() or src.stat().st_size>65536:raise ValueError('Invalid import file')
  new_rules=json.loads(src.read_text())
  if not isinstance(new_rules,dict):raise ValueError('Rules file must be a JSON object')
  applied=0
  for rule_key,allow in new_rules.items():
   parts=rule_key.split(':')
   if len(parts)==3:exchange.rule(parts[0],parts[2],parts[1],bool(allow));applied+=1
  result={'status':'imported','rules_applied':applied}
 else:raise ValueError(f'Unknown rule verb: {verb!r}')
 return result


def _run_market(exchange, args, config, verb):
 result = None
 if verb=='stats':
  def _escrow_stats(exchange, rows, window_sec, now_unix):
   from . import peer_work_market as _pwm
   try:
    all_reqs = _pwm.list_requests(exchange)
   except Exception:
    all_reqs = []
   active = [r for r in all_reqs if r.get('state') in ('OPEN','ACCEPTED')]
   pending_units = sum(int(r.get('budget_units',0)) for r in active if r.get('state')=='ACCEPTED')
   completed_window = [r for r in all_reqs if r.get('state')=='COMPLETED' and r.get('completed_at_unix',0)>now_unix-window_sec]
   p2p_cfg = exchange.load()
   peers_map = p2p_cfg.get('peers',{})
   # Peers capable of escrow: pinned, unblocked, with evidence of work activity
   workers = {r.get('assigned_peer') for r in all_reqs if r.get('assigned_peer')}
   known_unblocked = [pid for pid,v in peers_map.items() if not v.get('blocked')]
   escrow_capable_estimate = max(len(workers), len(known_unblocked))
   return {
    'active_escrows': len(active),
    'pending_settlement_units': pending_units,
    'completed_in_window': len(completed_window),
    'escrow_capable_peers_estimate': escrow_capable_estimate,
    'note': 'escrow_capable_peers_estimate counts unblocked pinned peers; actual escrow capability requires token balance and mutual rules',
   }
  import time as _t
  from .credit_ledger import summary as cl_summary
  window_hours = getattr(args, 'window_hours', 24)
  window_sec = window_hours * 3600
  now_unix = _t.time()
  rows = exchange.audit_rows()
  # Velocity: events in window
  recent = [r for r in rows if r.get('at_unix', 0) > now_unix - window_sec]
  mint_events = [r for r in recent if r.get('kind') == 'QUALIFY_RECEIPT']
  # Trend: compare current window vs prior window
  prior_start = now_unix - 2 * window_sec
  prior = [r for r in rows if prior_start < r.get('at_unix', 0) <= now_unix - window_sec]
  prior_mints = len([r for r in prior if r.get('kind') == 'QUALIFY_RECEIPT'])
  curr_mints = len(mint_events)
  if prior_mints == 0:
   trend = 'accelerating' if curr_mints > 0 else 'stable'
   trend_delta = 100.0 if curr_mints > 0 else 0.0
  else:
   delta_pct = (curr_mints - prior_mints) / prior_mints * 100
   trend = 'accelerating' if delta_pct > 10 else ('decelerating' if delta_pct < -10 else 'stable')
   trend_delta = round(delta_pct, 1)
  burn_events = [r for r in recent if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') in ('spend', 'burn', 'send') or (r.get('kind') == 'CREDIT_DELTA' and int(r.get('amount_units', 0)) < 0)]
  equity_sells = [r for r in recent if r.get('kind') == 'EQUITY_SELL']
  work_released = [r for r in recent if r.get('kind') == 'WORK_RELEASED']
  # Supply stats
  supply_summary = cl_summary(exchange.root)
  total_peers = len(supply_summary.get('peers', {}))
  # Feature counts from initial ledger
  from ._common import SYSTEM_ROOT
  import json as _json
  _ledger_jsonl = SYSTEM_ROOT / 'exchange' / 'initial_ledger' / 'initial_ledger.jsonl'
  _ledger_json = SYSTEM_ROOT / 'exchange' / 'initial_ledger' / 'initial_ledger.json'
  total_features = 0
  if _ledger_jsonl.exists():
   lines = [l for l in _ledger_jsonl.read_text().splitlines() if l.strip()]
   if lines:
    try:
     header = _json.loads(lines[0])
     total_features = header.get('feature_count', len(lines) - 1)
    except Exception:
     total_features = len(lines) - 1
  elif _ledger_json.exists():
   try:
    total_features = len(_json.loads(_ledger_json.read_text()).get('features', []))
   except Exception:
    pass
  revenue_fraction = 0.65
  revenue_features = max(1, int(total_features * revenue_fraction))
  free_features = total_features - revenue_features
  # Network size
  p2p_cfg = exchange.load()
  network_peer_count = len(p2p_cfg.get('peers', {}))
  result = {
   'status': 'ok',
   'window_hours': window_hours,
   'velocity': {
    'mint_events': len(mint_events),
    'burn_events': len(burn_events),
    'equity_sells': len(equity_sells),
    'work_released': len(work_released),
    'total_recent_events': len(recent),
    'trend': trend,
    'trend_delta_pct': trend_delta,
   },
   'supply': {
    'total_peers_with_balance': total_peers,
    'total_ledger_events': supply_summary.get('total_events', 0),
    'baseline_grant_units': supply_summary.get('baseline_grant_units', 0),
   },
   'features': {
    'total': total_features,
    'revenue_generating': revenue_features,
    'free_no_token_flow': free_features,
    'revenue_fraction': revenue_fraction,
   },
   'network': {
    'pinned_peers': network_peer_count,
    'exchange_enabled': p2p_cfg.get('enabled', False),
    'network_mode': p2p_cfg.get('network', False),
   },
   'escrow': _escrow_stats(exchange, rows, window_sec, now_unix),
  }
 return result


def _run_feature(exchange, args, config, verb):
 result = None
 if verb in ('catalog','declare','lifecycle'):
  from .feature_catalog import Catalog
  catalog=Catalog(exchange.root/'feature-catalog')
  if verb=='catalog':result=catalog.state()
  elif verb=='declare':result=catalog.declare(args.feature_id,json.loads(_bounded_file(args.manifest,16384)))
  else:result=catalog.lifecycle(args.atom_id,args.status,args.replacement)
 elif verb=='policy':result=exchange.feature_policy(args.feature_id,{k:getattr(args,k) for k in ('access','license_id','essential','open_after_unix','resale') if getattr(args,k,None) is not None})
 elif verb=='rate':
  import time as _t
  local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
  outcome_row={'kind':'FEATURE_RATING','feature_id':args.feature_id,'outcome':args.outcome,'score':getattr(args,'score',None),'at_unix':_t.time(),'at':str(_t.time()),'peer':local_id}
  exchange.append_audit_row(outcome_row)
  # Phase 2a: check auto-delist after every rating write
  _delist_result=_check_auto_delist(args.feature_id,exchange)
  # Phase 2c: reputation decay/boost on feature ratings
  try:
   from .credit_ledger import feature_creator_id as _fcid
   _creator=_fcid(args.feature_id,exchange) if hasattr(__import__('urace.credit_ledger',fromlist=['feature_creator_id']),'feature_creator_id') else None
  except Exception:_creator=None
  if _creator:
   _rep_delta=0.3 if args.outcome=='positive' else (-0.5 if args.outcome=='negative' else 0.0)
   if _rep_delta!=0.0:
    exchange.append_audit_row({'kind':'REPUTATION_DELTA','peer':_creator,'delta':_rep_delta,'reason':f'feature_rating_{args.outcome}','feature_id':args.feature_id,'at_unix':_t.time()})
  result={'status':'ok','feature_id':args.feature_id,'outcome':args.outcome,'recorded':True,'auto_delist':_delist_result}
 elif verb=='recommend':
  from ._common import SYSTEM_ROOT
  import json as _json
  _ledger_jsonl=SYSTEM_ROOT/'exchange'/'initial_ledger'/'initial_ledger.jsonl'
  # Build KPI scores from FEATURE_RATING audit rows
  _rating_pos: dict[str,int]={}
  _rating_neg: dict[str,int]={}
  _rating_tot: dict[str,int]={}
  try:
   for _rr in exchange.audit_rows():
    if _rr.get('kind')=='FEATURE_RATING':
     _fid=_rr.get('feature_id','')
     _oc=_rr.get('outcome','')
     _rating_tot[_fid]=_rating_tot.get(_fid,0)+1
     if _oc=='positive':_rating_pos[_fid]=_rating_pos.get(_fid,0)+1
     elif _oc=='negative':_rating_neg[_fid]=_rating_neg.get(_fid,0)+1
  except Exception:pass
  features=[]
  if _ledger_jsonl.exists():
   lines=[l for l in _ledger_jsonl.read_text().splitlines() if l.strip()][1:]
   _candidates=[]
   for line in lines[:getattr(args,'limit',5)*10]:
    try:
     f=_json.loads(line)
     if f.get('borrow_price_units',0)==0:
      _fid2=f.get('feature_id','')
      _pos=_rating_pos.get(_fid2,0);_neg=_rating_neg.get(_fid2,0);_tot=_rating_tot.get(_fid2,1)
      kpi_score=(_pos-_neg)/max(_tot,1)
      _kpi_mult=0.5 if kpi_score<-0.3 else 1.0
      _entry={'feature_id':_fid2,'kind':f.get('kind_label',''),'tags':f.get('tags',[]),'borrow_price_units':0,'kpi_score':round(kpi_score,3)}
      _candidates.append((_kpi_mult*kpi_score,_entry))
    except Exception:continue
   _candidates.sort(key=lambda x:x[0],reverse=True)
   features=[e for _,e in _candidates[:getattr(args,'limit',5)]]
  result={'status':'ok','recommended':features,'count':len(features)}
 else:
  _lang=getattr(args,'language',None)
  _feat_result=exchange.feature(args.feature_id,args.depends_on,wanted=args.wanted,offered=args.offered,wants=args.wants)
  if _lang is not None:
   with exchange.lock():
    _p=exchange.load();_p['features'][args.feature_id]['language']=_lang
    from ._common import atomic_write_json as _awj;_awj(exchange.root/'policy.json',_p)
   _feat_result['language']=_lang
  result=_feat_result
 return result


def _run_bundle(exchange, args, config, verb, pe):
 result = None
 if verb=='prepare':result=exchange.prepare(args.peer_id,args.feature_id,_bounded_file(args.file,pe.LIMIT//2,True),args.reviewed)
 elif verb=='inspect':result=exchange.inspect(args.bundle_id)
 elif verb=='send':result=pe.send(exchange,args.bundle_id)
 elif verb=='evaluate':
  from ._common import SYSTEM_ROOT
  import sys
  sys.path.insert(0,str(SYSTEM_ROOT/'trial'))
  from peer_runtime import enqueue
  result=enqueue(SYSTEM_ROOT/'trial',args.bundle_id)
 elif verb=='import':result=exchange.receive(json.loads(_bounded_file(args.file,pe.LIMIT)))
 elif verb=='manifest':
  from ._common import SYSTEM_ROOT
  import sys as _sys
  _sys.path.insert(0,str(SYSTEM_ROOT/'trial'))
  import runtime_evaluation as _ev
  receipt=_ev.load_receipt(SYSTEM_ROOT/'trial',args.baseline_evaluation_id,public=True)
  result=pe.request(exchange,args.peer_id,'exchange.manifest',{'baseline_engine_sha256':receipt['engine_sha256'],'observed_failures':[c for c,p in receipt['case_results'].items() if not p]+args.failures,'session_start_unix':__import__('time').time()})
 elif verb=='fetch-artifact':
  _fa_rec=exchange.inspect(args.bundle_id)
  _fa_sha=_fa_rec.get('bundle',{}).get('payload',{}).get('artifact_ref') or _fa_rec.get('bundle',{}).get('payload',{}).get('sha256','')
  _fa_size=_fa_rec.get('artifact_size_bytes',0)
  _fa_stored=_fa_rec.get('artifact_stored',False)
  if not _fa_sha:raise ValueError(f'Bundle {args.bundle_id!r} has no artifact reference')
  if getattr(args,'out_path',None):
   _fa_bytes=exchange.artifact_bytes(_fa_sha)
   if _fa_bytes is None:raise ValueError(f'Artifact {_fa_sha[:16]}... not in local store — request from peer first')
   import pathlib as _fap
   _fap.Path(args.out_path).write_bytes(_fa_bytes)
   result={'status':'written','sha256':_fa_sha,'size_bytes':len(_fa_bytes),'path':args.out_path}
  else:
   result={'sha256':_fa_sha,'size_bytes':_fa_size,'stored_locally':_fa_stored,'bundle_id':args.bundle_id}
 else:result=exchange.review(args.bundle_id,args.review_status,args.note)
 return result


def _run_chunk(exchange, args, config, verb):
 from .chunk_store import ChunkStore as _CS
 _cs=_CS(exchange.root)
 result = None
 if verb=='status':
  _cs_mf=_cs.manifest(args.artifact_sha256)
  if _cs_mf is None:result={'artifact_sha256':args.artifact_sha256,'stored':False}
  else:result={'artifact_sha256':args.artifact_sha256,'stored':True,'n_data':_cs_mf['n_data'],'n_total':_cs_mf['n_total'],'chunks_held':_cs.has_chunks(args.artifact_sha256),'is_reconstructable':_cs.is_reconstructable(args.artifact_sha256),'artifact_size_bytes':_cs_mf.get('artifact_size_bytes',0)}
 elif verb=='store':
  import pathlib as _csp
  _cs_raw=_csp.Path(args.input_path).read_bytes()
  import hashlib as _csh
  _cs_actual=_csh.sha256(_cs_raw).hexdigest()
  if _cs_actual!=args.artifact_sha256:raise ValueError(f'SHA256 mismatch: file={_cs_actual}, expected={args.artifact_sha256}')
  _cs_mf2=_cs.store(args.artifact_sha256,_cs_raw)
  result={'status':'stored','artifact_sha256':args.artifact_sha256,'n_total':_cs_mf2['n_total'],'size_bytes':len(_cs_raw)}
 elif verb=='find-holders':
  _rt2=exchange.routing_table()
  _holders=[{'peer_id':n.peer_id,'endpoint':n.endpoint,'last_seen':n.last_seen} for n in _rt2.chunk_holders(args.artifact_sha256,args.chunk_idx)]
  result={'artifact_sha256':args.artifact_sha256,'chunk_idx':args.chunk_idx,'closest_peers':_holders,'routing_table_size':_rt2.size(),'note':'Peers closest to chunk routing key; actual holder confirmation requires network RPC (v3 stub)'}
 return result
