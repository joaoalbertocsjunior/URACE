"""Network sub-module for exchange_cli: network guide, port analysis, bootstrap, node, peer."""
from pathlib import Path
import json


def _build_network_guide(cap: dict) -> dict:
 """Given nat_check capability dict, determine scenario and return actionable guidance."""
 import shutil
 from pathlib import Path
 nat_type=cap.get('nat_type','unknown')
 upnp=cap.get('upnp_available',False)
 from . import tunnel_install as _ti
 has_cf=bool(_ti.find_cloudflared())
 has_cert=(Path.home()/'.cloudflared'/'cert.pem').exists()
 has_ssh=bool(shutil.which('ssh'))
 if nat_type=='direct':
  scenario='vps_direct';label='VPS / server with public IP'
  recommendation='Direct inbound — no tunnel needed. Most reliable bootstrap+relay.'
  commands=['urace network serve --host 0.0.0.0 --port 7301']
  pf_alt=None
 elif nat_type in ('cone','symmetric') and nat_type=='cone' and upnp:
  scenario='cone_upnp';label='Home router (cone NAT + UPnP)'
  recommendation='UPnP opened the port automatically. Direct inbound works.'
  commands=['urace network serve --host 0.0.0.0 --port 7301']
  pf_alt='Alternative for more stability: urace network setup-port-forward'
 elif has_cf and has_cert:
  scenario='cloudflare_named';label='cloudflared authenticated (permanent URL)'
  recommendation='Named tunnel gives a permanent URL that survives reboots. Best option for home nodes.'
  commands=['urace network serve --tunnel auto --port 7301']
  pf_alt=None
 elif has_cf and not has_cert:
  scenario='cloudflare_needs_login';label='cloudflared installed — needs login'
  recommendation='One browser login → permanent URL forever. Strongly recommended before serving.'
  commands=['cloudflared tunnel login','urace network serve --tunnel auto --port 7301']
  pf_alt='Alternative without Cloudflare account: urace network setup-port-forward'
 elif has_ssh:
  scenario='localhost_run';label='SSH tunnel via localhost.run (no install needed)'
  recommendation='Zero install, zero account. URL changes on reconnect; peers notified automatically. Good for testing; cloudflared login gives a permanent URL.'
  commands=['urace network serve --tunnel auto --port 7301']
  pf_alt='For permanent URL without Cloudflare: urace network setup-port-forward'
 else:
  scenario='intranet_only';label='No internet tunnel available'
  recommendation='Install cloudflared or ensure SSH is available for internet-facing node. For LAN use, intranet mode is fine.'
  commands=['urace network settings set --network-mode intranet','urace network serve --host 0.0.0.0 --port 7301']
  pf_alt=None
 guide={'scenario':scenario,'label':label,'recommendation':recommendation,'commands':commands,'doc':'docs/exchange/network.md#nat-traversal'}
 if scenario=='intranet_only':guide['warning']='This node cannot act as bootstrap or relay for the internet network. Only LAN peers will be reachable.'
 if pf_alt:guide['port_forward_alternative']=pf_alt
 return guide


def _print_network_guide(guide: dict) -> None:
 """Print human-readable network setup guidance to stdout."""
 print('\n── Network Setup Guide ──────────────────────────────')
 print(f"  Situation : {guide['label']}")
 print(f"  Advice    : {guide['recommendation']}")
 print( '  Run       :')
 for cmd in guide.get('commands',[]):
  print(f'    {cmd}')
 if guide.get('port_forward_alternative'):
  print(f"  Alternative: {guide['port_forward_alternative']}")
 if guide.get('warning'):
  print(f"  WARNING   : {guide['warning']}")
 print(f"  Docs      : {guide['doc']}")
 print('─────────────────────────────────────────────────────\n')


def _port_to_internet_analysis(exchange, settings):
    """Analyze intranet state and return what's worth porting."""
    from . import stun_client as _stun
    result = {
        "public_address": None,
        "stun_available": False,
        "features": [],
        "network_mode": settings.get("network_mode", "intranet"),
        "already_internet": False,
    }
    if result["network_mode"] in ("internet", "hybrid"):
        result["already_internet"] = True
        return result
    addr = _stun.get_public_address()
    if addr:
        result["public_address"] = addr
        result["stun_available"] = True
    try:
        rows = exchange.audit_rows()
    except Exception:
        rows = []
    minted = {}
    for row in rows:
        if row.get("kind") == "FEATURE_MINTED" or row.get("kind") == "EQUITY_GRANT":
            fid = row.get("feature_id") or row.get("id", "")
            if fid and fid not in minted:
                minted[fid] = {"feature_id": fid, "description": row.get("description", ""), "positive": 0, "negative": 0, "neutral": 0}
        if row.get("kind") == "FEATURE_RATING":
            fid = row.get("feature_id", "")
            if fid in minted:
                outcome = row.get("outcome", "neutral")
                minted[fid][outcome] = minted[fid].get(outcome, 0) + 1
    for fid, info in minted.items():
        total = info["positive"] + info["negative"] + info["neutral"]
        kpi_score = (info["positive"] - info["negative"]) / max(total, 1)
        result["features"].append({
            "feature_id": fid,
            "description": info["description"][:80],
            "kpi_score": round(kpi_score, 3),
            "total_ratings": total,
            "positive": info["positive"],
            "negative": info["negative"],
        })
    result["features"].sort(key=lambda f: f["kpi_score"], reverse=True)
    return result


def _select_features_for_port(analysis, args):
    """Select which features to port based on args."""
    if getattr(args, "features", None):
        ids = {f.strip() for f in args.features.split(",") if f.strip()}
        return [f for f in analysis["features"] if f["feature_id"] in ids]
    min_kpi = float(getattr(args, "min_kpi_score", 0.5))
    min_ratings = int(getattr(args, "min_ratings", 2))
    return [
        f for f in analysis["features"]
        if f["kpi_score"] >= min_kpi and f["total_ratings"] >= min_ratings
    ]


def _format_port_report(report):
    addr = report.get("public_address", {}) or {}
    print("\nPort-to-internet analysis:")
    print(f"  Public address : {addr.get('ip')}:{addr.get('port')}")
    print(f"  Recommended mode: {report.get('recommended_mode', 'hybrid')}")
    print(f"\n  Features to port ({len(report['features_to_port'])}):")
    for f in report["features_to_port"]:
        print(f"    \u2022 {f['feature_id'][:16]} \u2014 kpi={f['kpi_score']:+.2f} ({f['positive']}\u2191/{f['negative']}\u2193) \u2014 {f['description'][:50]}")
    if report["features_skipped"]:
        print(f"\n  Features skipped ({len(report['features_skipped'])}) \u2014 below quality threshold:")
        for f in report["features_skipped"]:
            print(f"    \u25cb {f['feature_id'][:16]} \u2014 kpi={f['kpi_score']:+.2f} ({f['total_ratings']} ratings)")


def _run_network_audit(exchange, args, config, verb):
 P2P_KINDS={'CATALOG_CHECK','P2P_CORPUS_MISMATCH','RPC_ADMITTED','RPC_REJECTED','RPC_FLOOD_BLOCKED','HOLE_PUNCH_ATTEMPTED','DHT_BOOTSTRAP','PEER_CONNECTED','DHT_BOOTSTRAP_SKIPPED'}
 try:rows=exchange.audit_rows()
 except Exception:rows=[]
 rows=[r for r in rows if r.get('kind') in P2P_KINDS]
 if getattr(args,'kind',None):rows=[r for r in rows if r.get('kind')==args.kind]
 if getattr(args,'peer',None):rows=[r for r in rows if r.get('peer')==args.peer]
 result=rows[-args.limit:]
 return result


def _run_bootstrap(exchange, args, config, verb, pe):
 result = None
 cfg=exchange.load()
 peers_list=cfg.get('bootstrap_peers',[])
 if verb=='list':result={'bootstrap_peers':peers_list,'count':len(peers_list)}
 elif verb=='add':
  endpoint=args.endpoint.strip()
  if not endpoint.startswith('https://'):raise ValueError('Bootstrap peer endpoint must start with https://')
  if endpoint in peers_list:result={'status':'already_present','endpoint':endpoint}
  else:
   peers_list=peers_list+[endpoint]
   with exchange.lock():
    cfg=exchange.load();cfg['bootstrap_peers']=peers_list
    import json as _jsn
    (exchange.root/'policy.json').write_text(_jsn.dumps(cfg,indent=2))
   result={'status':'added','endpoint':endpoint,'total':len(peers_list)}
 elif verb=='remove':
  endpoint=args.endpoint.strip()
  if endpoint not in peers_list:result={'status':'not_found','endpoint':endpoint}
  else:
   peers_list=[p for p in peers_list if p!=endpoint]
   with exchange.lock():
    cfg=exchange.load();cfg['bootstrap_peers']=peers_list
    import json as _jsn
    (exchange.root/'policy.json').write_text(_jsn.dumps(cfg,indent=2))
   result={'status':'removed','endpoint':endpoint,'total':len(peers_list)}
 elif verb=='announce':
  from . import stun_client as _stun
  _ep=getattr(args,'endpoint',None)
  if not _ep:
   _addr=_stun.get_public_address('stun.l.google.com',19302)
   if not _addr:result={'status':'error','error':'STUN failed — provide --endpoint explicitly'};_ep=None
   else:_ep=f"https://{_addr['ip']}:{_addr.get('port',7301)}"
  if _ep:
   # F7-lite: ensure address book is loaded for gossip
   from . import peer_address_book as _pab_ann
   _book_ann=_pab_ann.get_address_book()
   if _book_ann is None:
    _pab_ann.init_address_book(exchange.root/'peer_address_book.json')
    _book_ann=_pab_ann.get_address_book()
   _bp_list=exchange.load().get('bootstrap_peers',[])
   _announced=[]
   for _bep in _bp_list[:5]:
    try:
     _r=pe.request(exchange,None,'bootstrap.announce',{'endpoint':_ep,'peer_id':exchange.identity().get('peer_id','')},bootstrap_endpoint=_bep)
     _announced.append({'bootstrap':_bep,'status':'ok' if isinstance(_r,dict) and _r.get('status')!='error' else 'error'})
     # F7-lite: request address book from bootstrap peer (authenticated path not available; skip)
    except Exception as _ae:
     _announced.append({'bootstrap':_bep,'status':'error','error':str(_ae)})
   _cfg3=exchange.load()
   _bp3=_cfg3.setdefault('bootstrap_peers',[])
   if _ep not in _bp3:_bp3.insert(0,_ep);_cfg3['bootstrap_peers']=_bp3
   from ._common import atomic_write_json;atomic_write_json(exchange.root/'policy.json',_cfg3)
   result={'status':'ok','endpoint_announced':_ep,'peers_notified':_announced,'added_to_local_peers':True}
 else:raise ValueError(f'Unknown bootstrap verb: {verb!r}')
 return result


def _run_node(exchange, args, config, verb):
 from . import nat_check as _nc
 cfg=exchange.load()
 result = None
 if verb=='check':
  cap=_nc.check_node_capability(timeout=getattr(args,'timeout',5.0))
  result={**cap,'status':'ok'}
 elif verb=='roles':
  if getattr(args,'roles_value',None):
   roles=[r.strip() for r in args.roles_value.split(',') if r.strip()]
   with exchange.lock():
    _cfg=exchange.load();_cfg['node_roles']=roles
    from ._common import atomic_write_json
    atomic_write_json(exchange.root/'policy.json',_cfg)
   result={'status':'ok','node_roles':roles}
  else:
   result={'node_roles':cfg.get('node_roles',[]),'status':'ok'}
 else:raise ValueError(f'Unknown node verb: {verb!r}')
 return result


def _run_peer(exchange, args, config, verb):
 result = None
 if verb=='list':result=exchange.summary()['peers']
 elif verb=='identity':
  if not exchange.load()['enabled']:raise ValueError('Sharing disabled; enable explicitly before creating an identity')
  result=exchange.identity()
 elif verb=='add':
  from pathlib import Path as _Path
  def _bf(name, limit):
   path = _Path(name)
   if '..' in path.parts: raise ValueError('Parent traversal prohibited')
   for candidate in (path, path.resolve()):
    if any(part.startswith('.') for part in candidate.parts if part != '.'): raise ValueError('Protected file path prohibited')
   probe = _Path(path.anchor or '.')
   for part in path.parts[1:] if path.is_absolute() else path.parts:
    probe = probe / part
    if probe.is_symlink(): raise ValueError('Symlink path prohibited')
   if not path.is_file() or path.stat().st_size > limit: raise ValueError('Bounded regular file required')
   return path.read_text()
  result=exchange.peer(_bf(args.certificate,8192),args.endpoint,json.loads(_bf(args.post_quantum_identity,16384)) if args.post_quantum_identity else None)
 elif verb=='rotate':
  from pathlib import Path as _Path
  def _bf2(name, limit):
   path = _Path(name)
   if '..' in path.parts: raise ValueError('Parent traversal prohibited')
   for candidate in (path, path.resolve()):
    if any(part.startswith('.') for part in candidate.parts if part != '.'): raise ValueError('Protected file path prohibited')
   probe = _Path(path.anchor or '.')
   for part in path.parts[1:] if path.is_absolute() else path.parts:
    probe = probe / part
    if probe.is_symlink(): raise ValueError('Symlink path prohibited')
   if not path.is_file() or path.stat().st_size > limit: raise ValueError('Bounded regular file required')
   return path.read_text()
  new_cert_pem=_bf2(args.new_certificate,8192)
  new_result=exchange.peer(new_cert_pem)
  new_peer_id=new_result.get('peer_id','')
  cfg=exchange.load()
  old_rules={k:v for k,v in cfg.get('rules',{}).items() if k.startswith(args.old_peer_id+':')}
  for rule_key,allow in old_rules.items():
   parts=rule_key.split(':')
   if len(parts)==3 and parts[0]==args.old_peer_id:
    exchange.rule(new_peer_id,parts[2],parts[1],allow)
  exchange.block(args.old_peer_id,True)
  result={'status':'rotated','old_peer_id':args.old_peer_id,'new_peer_id':new_peer_id,'rules_migrated':len(old_rules)}
 elif verb=='role':
  pid=getattr(args,'peer_id',None);role_val=getattr(args,'role_value',None)
  p2p_cfg=exchange.load();peers_map=p2p_cfg.get('peers',{})
  if role_val is not None:
   if pid not in peers_map:result={'status':'error','error':f'Unknown peer: {pid!r}'}
   else:
    peers_map[pid]['role']=role_val
    from ._common import atomic_write_json;atomic_write_json(exchange.root/'policy.json',p2p_cfg)
    result={'status':'ok','peer_id':pid,'role':role_val}
  else:
   if pid:result={'peer_id':pid,'role':peers_map.get(pid,{}).get('role','operator')}
   else:result={'peers':{p:peers_map[p].get('role','operator') for p in peers_map}}
 else:result=exchange.block(args.peer_id,verb=='block')
 return result
