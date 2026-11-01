"""Explainable local peer selection. No native model calls or global reputation claims."""
import hashlib,json,math,time
from . import peer_exchange as pe

SCHEMA='peer-selection-v1'
FRESH=3600

def offers(exchange,recipient):
 p=exchange.load()
 if recipient not in p['peers'] or p['peers'][recipient]['blocked']:raise ValueError('Peer denied')
 result=[]
 for feature,meta in sorted(p['features'].items()):
  if not meta.get('offered',False) or not exchange.permitted(p,recipient,feature,'send'):continue
  wants=meta.get('wants',[])
  if any(not exchange.permitted(p,recipient,f,'receive') for f in wants):continue
  result.append({'feature':feature,'wants':wants,'terms':'non-exclusive voluntary exchange; no automatic obligation','quality':'unverified until recipient acceptance','dependencies':meta['dependencies']})
 return {'schema':SCHEMA,'peer_id':exchange.identity()['peer_id'],'expires_unix':time.time()+FRESH,'offers':result[:64],'availability':'responded-now; not a future uptime promise'}

def validate_catalog(value,peer):
 if not isinstance(value,dict) or set(value)!={'schema','peer_id','expires_unix','offers','availability'} or value['schema']!=SCHEMA or value['peer_id']!=peer:raise ValueError('Invalid offer catalog identity')
 if type(value['expires_unix']) not in (int,float) or not time.time()<value['expires_unix']<=time.time()+FRESH+300:raise ValueError('Invalid catalog expiry')
 if not isinstance(value['offers'],list) or len(value['offers'])>64:raise ValueError('Offer count exceeded')
 seen=set()
 for offer in value['offers']:
  if not isinstance(offer,dict) or set(offer)!={'feature','wants','terms','quality','dependencies'}:raise ValueError('Invalid offer contract')
  feature=pe.check_id(offer['feature'])
  if feature in seen:raise ValueError('Duplicate offered feature')
  seen.add(feature)
  for k in ('wants','dependencies'):
   if not isinstance(offer[k],list) or len(offer[k])>32:raise ValueError('Bounded offer dependencies required')
   for f in offer[k]:pe.check_id(f)
  if any(not isinstance(offer[k],str) or len(offer[k])>256 for k in ('terms','quality')):raise ValueError('Bounded offer claims required')
 return value

def cache(exchange):
 path=exchange.root/'selection.json'
 return json.loads(path.read_text()) if path.exists() else {'schema':SCHEMA,'peers':{}}

def refresh(exchange,limit=3,now=None):
 if type(limit) is not int or not 1<=limit<=3:raise ValueError('Refresh selects 1–3 peers per round')
 p=exchange.load();now=time.time() if now is None else now
 if not p['enabled'] or not p['network']:raise ValueError('Network selection refresh disabled')
 state=cache(exchange)
 checks=[e for e in exchange.audit_rows() if e['kind']=='CATALOG_CHECK' and e['at_unix']>now-86400]
 metadata_allowance=max(1,p.get('max_rpc_per_day',200)//2)
 if len(checks)>=metadata_allowance:return {'schema':SCHEMA,'checks':[],'status':'METADATA_BUDGET_WAIT','next_due_unix':min(e['at_unix'] for e in checks)+86400,'native_model_calls':0}
 known=sum(not v['blocked'] and bool(v.get('endpoint')) for v in p['peers'].values())
 cadence=max(3600,math.ceil(86400*known/metadata_allowance),math.ceil(172800/p.get('max_rpc_per_peer_per_day',50)))
 # Earliest due / least recently checked peers first: known winners cannot starve exploration.
 candidates=[peer for peer,v in p['peers'].items() if not v['blocked'] and v.get('endpoint') and state['peers'].get(peer,{}).get('next_probe_unix',0)<=now]
 candidates.sort(key=lambda peer:(state['peers'].get(peer,{}).get('checked_unix',0),peer))
 observations=[]
 for peer in candidates[:min(limit,metadata_allowance-len(checks))]:
  old=state['peers'].get(peer,{})
  try:
   min_version=p.get('min_peer_version',pe.PROTOCOL_VERSION)
   info=pe.request(exchange,peer,'exchange.info',{});peer_version=info.get('protocol_version',1)
   if not isinstance(peer_version,int) or peer_version<min_version:
    exchange.event('VERSION_TOO_OLD',peer=peer,peer_version=peer_version,min_version=min_version)
    row={**old,'checked_unix':time.time(),'failures':0,'status':'VERSION_TOO_OLD','protocol_version':peer_version,'next_probe_unix':time.time()+cadence}
   else:
    catalog=validate_catalog(pe.request(exchange,peer,'exchange.offers',{}),peer);row={'checked_unix':time.time(),'catalog':catalog,'failures':0,'status':'AVAILABLE','protocol_version':peer_version,'next_probe_unix':time.time()+cadence}
  except (ValueError,OSError):
   failures=old.get('failures',0)+1;delay=min(21600,300*2**min(failures-1,7));jitter=int(hashlib.sha256(peer.encode()).hexdigest()[:4],16)%61
   row={**old,'checked_unix':time.time(),'failures':failures,'status':'UNAVAILABLE_OR_INVALID','next_probe_unix':time.time()+delay+jitter}
  with exchange.lock():
   latest=cache(exchange);latest['peers'][peer]=row;pe.atomic(exchange.root/'selection.json',latest);exchange.event('CATALOG_CHECK',peer=peer,status=row['status'],next_probe_unix=row['next_probe_unix'])
  state['peers'][peer]=row;observations.append({'peer_id':peer,'status':row['status'],'next_probe_unix':row['next_probe_unix']})
 return {'schema':SCHEMA,'checks':observations,'native_model_calls':0,'selection':'Oldest eligible observation first; bounded exponential backoff with finite reconsideration'}

def rank(exchange,wanted=None,now=None):
 p=exchange.load();state=cache(exchange);now=time.time() if now is None else now;wanted=set(wanted if wanted is not None else [f for f,v in p['features'].items() if v.get('wanted',False)])
 for feature in wanted:pe.check_id(feature)
 events=exchange.audit_rows();rows=[]
 for peer,config in sorted(p['peers'].items()):
  observation=state['peers'].get(peer,{});catalog=observation.get('catalog',{});fresh=catalog.get('expires_unix',0)>now;matches=[];denied=[]
  for offer in catalog.get('offers',[]):
   f=offer['feature']
   if f not in wanted:continue
   allowed=exchange.permitted(p,peer,f,'receive') and all(exchange.permitted(p,peer,v,'send') for v in offer['wants'])
   # Remote dependency declarations must match locally reviewed feature contracts.
   allowed=allowed and f in p['features'] and offer['dependencies']==p['features'][f]['dependencies']
   (matches if allowed else denied).append(f)
  qualified=[e for e in events if e.get('peer')==peer and e['kind']=='APPLIED_AFTER_LOCAL_QUALIFICATION']
  sends=[e for e in events if e.get('peer')==peer and e['kind'] in ('SENT_QUARANTINED','SEND_FAILED_OR_UNCONFIRMED')];n=len(sends);delivered=sum(e['kind']=='SENT_QUARANTINED' for e in sends)
  lower=None
  if n:
   z=1.96;rate=delivered/n;lower=(rate+z*z/(2*n)-z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n)))/(1+z*z/n)
  if config['blocked']:status='BLOCKED';reason='Owner block overrides ranking and all offers'
  elif not p['enabled']:status='DISABLED';reason='Sharing is disabled'
  elif observation.get('status')=='VERSION_TOO_OLD':status='VERSION_TOO_OLD';reason='Peer protocol version is below min_peer_version; peer must upgrade before exchange is permitted'
  elif not wanted:status='NO_DECLARED_NEED';reason='Declare wanted features before ranking utility'
  elif not fresh:status='NEEDS_REFRESH';reason='No fresh authenticated offer catalog; unknown is not bad quality'
  elif observation.get('status')!='AVAILABLE':status='TEMPORARILY_UNAVAILABLE';reason='Failed observation; reconsider after bounded backoff'
  elif not matches:status='NO_CURRENT_PERMITTED_MATCH';reason='No wanted offer with allowed reciprocal terms/dependencies; reassess when needs or offers change'
  else:status='CANDIDATE';reason='Fresh relevant offers satisfy local feature and reciprocal permissions; quality still requires local acceptance'
  rows.append({'peer_id':peer,'status':status,'reason':reason,'potential_feature_matches':sorted(matches),'denied_matches':sorted(denied),'fresh_catalog':fresh,'observed_transfers':n,'confirmed_deliveries':delivered,'delivery_lower_bound':lower,'validated_quality':{'locally_qualified_and_applied':len(qualified),'generalization_proven':False} if qualified else None,'expected_benefit_score':None,'offered_quality_claim_verified':False,'next_reconsider_unix':observation.get('next_probe_unix',now),'selection_basis':'Policy first, feature match coverage, observed delivery evidence; no token/native calls'})
 rows.sort(key=lambda r:(r['status']!='CANDIDATE',-len(r['potential_feature_matches']),-(r['delivery_lower_bound'] or 0),r['peer_id']))
 return {'schema':SCHEMA,'wanted_features':sorted(wanted),'peers':rows,'native_model_calls':0,'automatic_transfer':False,'fairness':'No reciprocity lock: requesting no return is allowed; no requirement to deliver first; no global currency or guaranteed equal utility','anti_staleness':'Freshness expiry, finite backoff, oldest-first metadata exploration, re-evaluation when needs/permissions/offers change','optimality':'Provisional explainable ordering; absolute optimum is unproven; independent local quality evidence remains required'}
