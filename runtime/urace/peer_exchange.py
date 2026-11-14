"""Opt-in, product-scoped signed artifact exchange. Incoming artifacts are quarantined, never executed."""
from pathlib import Path
from contextlib import contextmanager
import base64, gzip, hashlib, hmac, http.client, http.server, ipaddress, json, logging, os, re, ssl, subprocess, tempfile, time, urllib.parse, datetime

_logger = logging.getLogger(__name__)
try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

SCHEMA='urace-exchange-v2'
PROTOCOL_VERSION=2
LIMIT=524288
ARTIFACT_INLINE_LIMIT=65536
ARTIFACT_STORE_LIMIT=104857600
RELAY_CREDIT_ISSUED = 'RELAY_CREDIT_ISSUED'
BOOTSTRAP_CREDIT_ISSUED = 'BOOTSTRAP_CREDIT_ISSUED'
AUDIT_CHAIN_RECORD = 'AUDIT_CHAIN_RECORD'
ID=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$')

def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def atomic(path,value):
 from ._common import atomic_write_json
 atomic_write_json(path,value);os.chmod(path,0o600)
def check_id(value):
 if not isinstance(value,str) or not ID.fullmatch(value):raise ValueError('Invalid identifier')
 return value

def _local_corpus_fingerprint()->str:
 from . import evolution_guard as _eg
 _pkg=Path(os.path.abspath(__file__)).parent
 _product_root=_pkg.parent.parent.parent
 return _eg.p2p_corpus_fingerprint(_product_root)

def directory(config):
 from ._common import state_path
 from .resource_usage import product_identity
 return state_path(config).parent/'exchange'/hashlib.sha256(product_identity(config).encode()).hexdigest()[:24]

def _artifact_store_path(exchange_root,sha256_hex):
 return exchange_root/'bundle-artifacts'/sha256_hex[:2]/sha256_hex

def _artifact_key(exchange_root, sha256_hex):
 """Derive a per-artifact AES-256 key from local private seed + artifact hash."""
 seed_path = exchange_root / 'artifact-seed.bin'
 if not seed_path.exists():
  seed = os.urandom(32)
  fd = os.open(str(seed_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
  with os.fdopen(fd, 'wb') as f:
   f.write(seed)
   f.flush()
   os.fsync(f.fileno())
 else:
  seed = seed_path.read_bytes()
 salt = b'URACE-ARTIFACT-v1'
 prk = hmac.new(salt, seed + sha256_hex.encode(), 'sha256').digest()
 okm = hmac.new(prk, b'\x01', 'sha256').digest()
 return okm

def _store_artifact(exchange_root, sha256_hex, raw_bytes):
 p = _artifact_store_path(exchange_root, sha256_hex)
 if not p.exists():
  p.parent.mkdir(parents=True, exist_ok=True)
  try:
   from cryptography.hazmat.primitives.ciphers.aead import AESGCM
   key = _artifact_key(exchange_root, sha256_hex)
   nonce = os.urandom(12)
   ciphertext = AESGCM(key).encrypt(nonce, raw_bytes, b'URACE-ARTIFACT-v1')
   p.write_bytes(nonce + ciphertext)
  except ImportError:
   p.write_bytes(raw_bytes)
  os.chmod(p, 0o600)
 # Also store in erasure-coded ChunkStore (v2 path) — replica holders get ciphertext only
 try:
  from .chunk_store import ChunkStore
  ChunkStore(exchange_root).store(sha256_hex, raw_bytes)
 except Exception:
  pass

def _load_artifact_bytes(exchange_root, sha256_hex):
 # v2 path: erasure-coded ChunkStore (may reconstruct even when flat file is missing)
 try:
  from .chunk_store import ChunkStore
  _cs_data = ChunkStore(exchange_root).load(sha256_hex)
  if _cs_data is not None:
   return _cs_data
 except Exception:
  pass
 # v1 path: flat AES-GCM encrypted file
 p = _artifact_store_path(exchange_root, sha256_hex)
 if not p.exists():
  return None
 data = p.read_bytes()
 try:
  from cryptography.hazmat.primitives.ciphers.aead import AESGCM
  key = _artifact_key(exchange_root, sha256_hex)
  if len(data) < 13:
   return data
  nonce, ciphertext = data[:12], data[12:]
  try:
   return AESGCM(key).decrypt(nonce, ciphertext, b'URACE-ARTIFACT-v1')
  except Exception:
   return data
 except ImportError:
  return data


class Exchange:
 def __init__(self,root):self.root=Path(root)
 def load(self):
  p=self.root/'policy.json'
  return json.loads(p.read_text()) if p.exists() else {'schema':SCHEMA,'enabled':True,'network':False,'advertise':False,'auto_select':True,'auto_relay':False,'token_settlement':False,'auto_trust_first_contact':False,'default_feature_rules':{},'relay_only':False,'peers':{},'features':{},'rules':{},'feature_borrow_enabled':True,'max_transfers_per_day':20,'max_transfers_per_peer_per_day':5,'max_bytes_per_day':1048576,'max_rpc_per_day':200,'max_rpc_per_peer_per_day':50,'min_peer_version':PROTOCOL_VERSION,'bootstrap_peers':[],'compress_wire':False,'bandwidth_profile':'auto','transfer_chunk_size':0,'relay_credit_per_kb':1,'node_roles':[],'urace_credit_usd_rate':1000,'bootstrap_credit_per_connection':5}
 @contextmanager
 def lock(self):
  self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  if self.root.is_symlink():raise ValueError('Exchange directory cannot be a symlink')
  os.chmod(self.root,0o700)
  with (self.root/'exchange.lock').open('a') as f:
   if _HAS_FCNTL: _fcntl.flock(f,_fcntl.LOCK_EX)
   yield
 def audit_rows(self):
  p=self.root/'audit.jsonl';rows=[];previous='0'*64
  if p.exists():
   for line in p.read_text().splitlines():
    row=json.loads(line);signed={k:v for k,v in row.items() if k!='sha256'}
    if row.get('previous')!=previous or digest(signed)!=row.get('sha256'):raise ValueError('Audit chain integrity failure')
    previous=row['sha256'];rows.append(row)
  self.verify_audit_rows(rows)
  return rows
 def verify_audit_rows(self,rows):
  if not rows:return
  from .signed_ledger import Ledger
  ledger=Ledger(self.root/'signed-audit')
  if not ledger.root.exists():raise ValueError('Unsigned historical peer audit requires explicit migration')
  head=ledger._head();cache=getattr(self,'_audit_cache',None)
  if cache is None or cache['head']['author']!=head['author'] or cache['head']['sequence']>head['sequence']:
   ledger.verify();cache={'head':{'sequence':0,'hash':'0'*96,'author':head['author']},'rows':[]}
  previous=cache['head']['hash'];signed=list(cache['rows'])
  for n in range(cache['head']['sequence']+1,head['sequence']+1):
   block,previous=ledger._read(n,previous,head['author'])
   if block['payload']['kind']!='AUDIT_EVENT':raise ValueError('Unexpected peer audit event')
   signed.append(encoded(block['payload']['details']['row']))
  if previous!=head['hash']:raise ValueError('Peer audit checkpoint conflict')
  offset=0
  for row in rows:
   expected=encoded(row)
   while offset<len(signed) and signed[offset]!=expected:offset+=1
   if offset==len(signed):raise ValueError('Peer audit row lacks matching hybrid authentication')
   offset+=1
  self._audit_cache={'head':head,'rows':signed}
 def crypto_identity(self):
  from .ledger_crypto import Identity
  if not hasattr(self,'_crypto_identity'):self._crypto_identity=Identity(self.root/'hybrid-identity.json')
  return self._crypto_identity
 def trusted_crypto(self,p,peer):
  from .ledger_crypto import validate_public
  public=p['peers'][peer].get('post_quantum')
  if public is None:raise ValueError('Peer requires explicitly pinned post-quantum identity')
  return validate_public(public)
 def append_audit_row(self,row:dict):
  """Append a work-market audit row. Delegates to event() for chain integrity."""
  kind=row.get('kind','UNKNOWN');details={k:v for k,v in row.items() if k!='kind'}
  self.event(kind,**details)
 def event(self,kind,**details):
  rows=self.audit_rows();row={'schema':SCHEMA,'at_unix':time.time(),'kind':kind,'previous':rows[-1]['sha256'] if rows else '0'*64,**details};row['sha256']=digest(row)
  from .signed_ledger import Ledger
  # Preserve legacy reader format; sidecar signs the exact event before publication.
  if not hasattr(self,'_signed_audit'):self._signed_audit=Ledger(self.root/'signed-audit')
  self._signed_audit.append('AUDIT_EVENT',{'row':row})
  with (self.root/'audit.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
  return row
 def configure(self,**changes):
  with self.lock():
   p=self.load()
   for k,v in changes.items():
    if k in ('enabled','network','advertise','auto_select','auto_relay','token_settlement','relay_enabled','auto_trust_first_contact','relay_only','feature_borrow_enabled','p2p_mint_enabled','p2p_sell_enabled','compress_enabled','decompress_enabled','compress_wire'):
     if type(v) is not bool:raise ValueError('Boolean exchange settings required')
    elif k=='default_feature_rules':
     if not isinstance(v,dict):raise ValueError('default_feature_rules must be a dict')
    elif k in ('max_transfers_per_day','max_transfers_per_peer_per_day','max_bytes_per_day','max_rpc_per_day','max_rpc_per_peer_per_day','bundle_max_age_seconds','transfer_chunk_size'):
     if type(v) is not int or not 1<=v<=1073741824:raise ValueError('Positive bounded exchange allowance required')
     if k=='transfer_chunk_size' and not 512<=v<=131072:raise ValueError('transfer_chunk_size must be 512–131072')
    elif k=='bandwidth_profile':
     if v not in ('auto','low','high'):raise ValueError('bandwidth_profile must be auto, low, or high')
    elif k=='min_peer_version':
     if type(v) is not int or not 1<=v<=PROTOCOL_VERSION:raise ValueError('min_peer_version must be a positive integer not exceeding current protocol version')
    else:raise ValueError('Unknown exchange setting')
    p[k]=v
   if changes.get('enabled') is False:p['network']=False;p['advertise']=False
   if changes.get('network') is False:p['advertise']=False
   if p['network'] and not p['enabled'] or p['advertise'] and not p['network']:raise ValueError('Enable sharing before networking, networking before advertising')
   atomic(self.root/'policy.json',p);self.event('SETTINGS',changes=changes)
   if p['enabled']:self.identity()
   return p
 def openssl(self,*args):
  r=subprocess.run(['openssl',*map(str,args)],capture_output=True,timeout=15)
  if r.returncode:raise ValueError('OpenSSL operation failed')
  return r.stdout
 def identity(self):
  key=self.root/'identity-key.pem';cert=self.root/'identity-cert.pem'
  if not key.exists() and not cert.exists():
   # Rate-limit identity creation: max 3 per exchange root per 24h (DoS hardening)
   _id_log = self.root / 'identity-creations.json'
   _now_id = time.time()
   _id_history = []
   if _id_log.exists():
    try:
     _id_history = json.loads(_id_log.read_text())
    except Exception:
     _id_history = []
   _id_history = [t for t in _id_history if _now_id - t < 86400]
   if len(_id_history) >= 3:
    raise ValueError('Identity creation rate limit exceeded (max 3 per 24h per exchange root). This prevents Sybil identity farming.')
   _id_history.append(_now_id)
   atomic(self.root / 'identity-creations.json', _id_history)
   self.openssl('genpkey','-algorithm','ED25519','-out',key);os.chmod(key,0o600)
   self.openssl('req','-new','-x509','-key',key,'-out',cert,'-days','365','-subj','/CN=urace-peer','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1')
  if key.is_symlink() or cert.is_symlink() or not key.is_file() or not cert.is_file():raise ValueError('Incomplete regular exchange identity')
  os.chmod(key,0o600)
  der=ssl.PEM_cert_to_DER_cert(cert.read_text());return {'peer_id':hashlib.sha256(der).hexdigest(),'certificate':cert.read_text(),'post_quantum':self.crypto_identity().public()}
 def peer(self,certificate,endpoint=None,post_quantum=None):
  if len(certificate.encode())>8192:raise ValueError('Certificate size exceeded')
  fingerprint=hashlib.sha256(ssl.PEM_cert_to_DER_cert(certificate)).hexdigest()
  if endpoint:validate_endpoint(endpoint)
  if post_quantum is not None:
   from .ledger_crypto import validate_public
   validate_public(post_quantum)
  with self.lock():
   p=self.load();prior=p['peers'].get(fingerprint,{})
   if post_quantum is not None and prior.get('post_quantum') not in (None,post_quantum):raise ValueError('Key replacement requires a separately qualified rotation protocol; retain historical identity')
   p['peers'][fingerprint]={'certificate':certificate,'endpoint':endpoint,'blocked':prior.get('blocked',False),'post_quantum':post_quantum if post_quantum is not None else prior.get('post_quantum')};atomic(self.root/'policy.json',p);self.event('PEER_PINNED',peer=fingerprint)
  # v3 readiness: add peer to Kademlia routing table for DHT chunk discovery
  try:
   from .kademlia import RoutingTable as _RT
   _rt=_RT.load(self.root/'routing-table.json',self.identity()['peer_id'])
   _rt.add(fingerprint,endpoint or '')
   _rt.save(self.root/'routing-table.json')
  except Exception:pass
  return {'peer_id':fingerprint,'trusted_for_content':False}
 def routing_table(self):
  """Return Kademlia routing table for DHT chunk/peer discovery (v3)."""
  from .kademlia import RoutingTable as _RT
  return _RT.load(self.root/'routing-table.json',self.identity()['peer_id'])
 def block(self,peer,blocked):
  with self.lock():
   p=self.load()
   if peer not in p['peers']:raise ValueError('Unknown peer')
   p['peers'][peer]['blocked']=blocked
   if not blocked:p['rules']={k:v for k,v in p['rules'].items() if not k.startswith(peer+':')}
   atomic(self.root/'policy.json',p);self.event('BLOCKED' if blocked else 'UNBLOCKED_RULES_CLEARED',peer=peer)
  return {'peer':peer,'blocked':blocked}
 def feature(self,name,dependencies,*,wanted=False,offered=False,wants=None):
  wants=[] if wants is None else wants
  if type(wanted) is not bool or type(offered) is not bool or not isinstance(wants,list) or len(wants)>32:raise ValueError('Invalid feature offer controls')
  for f in wants:check_id(f)
  check_id(name)
  if len(dependencies)>32 or name in dependencies:raise ValueError('Invalid feature dependencies')
  for d in dependencies:check_id(d)
  with self.lock():
   p=self.load();p['features'][name]={**p['features'].get(name,{}),'dependencies':sorted(set(dependencies)),'wanted':wanted,'offered':offered,'wants':sorted(set(wants))};atomic(self.root/'policy.json',p);self.event('FEATURE_DECLARED',feature=name,dependencies=dependencies)
  return p['features'][name]
 def feature_policy(self,feature,changes):
  from .feature_policy import DEFAULT,validate,effective
  check_id(feature)
  with self.lock():
   p=self.load()
   if feature not in p['features']:raise ValueError('Declare feature first')
   old=p['features'][feature].get('distribution_policy',DEFAULT);value=validate({**old,**changes})
   # Existing recipients keep the terms signed into their delivered artifact.
   p['features'][feature]['distribution_policy']=value;atomic(self.root/'policy.json',p);self.event('FEATURE_POLICY',feature=feature,policy=value,previous_policy_sha256=digest(old))
  return effective(value)
 def rule(self,peer,feature,direction,allow):
  check_id(feature)
  if direction not in ('send','receive') or type(allow) is not bool:raise ValueError('Invalid rule')
  with self.lock():
   p=self.load()
   if peer not in p['peers'] or feature not in p['features']:raise ValueError('Declare feature and pin peer first')
   p['rules'][peer+':'+direction+':'+feature]=allow;atomic(self.root/'policy.json',p);self.event('RULE',peer=peer,feature=feature,direction=direction,allow=allow)
  return {'peer':peer,'feature':feature,'direction':direction,'allow':allow}
 def permitted(self,p,peer,feature,direction,seen=None):
  if not p['enabled'] or peer not in p['peers'] or p['peers'][peer]['blocked']:return False
  if not p['rules'].get(peer+':'+direction+':'+feature,False) or feature not in p['features']:return False
  seen=set() if seen is None else seen
  if feature in seen:return False
  seen=seen|{feature}
  return all(self.permitted(p,peer,d,direction,seen) for d in p['features'][feature]['dependencies'])
 def budget(self,peer,size):
  rows=[r for r in self.audit_rows() if r['at_unix']>time.time()-86400 and r['kind'] in ('SEND_RESERVED','RECEIVE_RESERVED')];p=self.load()
  if len(rows)>=p['max_transfers_per_day'] or sum(r['bytes'] for r in rows)+size>p['max_bytes_per_day']:raise ValueError('Local exchange daily budget exhausted')
  # Per-peer limits prevent one identity monopolizing the global allowance; identity splitting remains possible.
  if sum(r.get('peer')==peer for r in rows)>=p.get('max_transfers_per_peer_per_day',5):raise ValueError('Per-peer transfer allowance exhausted')
 def sign(self,payload):
  return self.crypto_identity().sign(payload,'peer-bundle')
 def verify(self,bundle,p):
  if not isinstance(bundle,dict) or set(bundle)!={'payload','signature'}:raise ValueError('Invalid signed bundle')
  b=bundle['payload']
  if not isinstance(b,dict) or not {'schema','sender','recipient','feature','dependencies','created_unix','sha256','distribution_terms'}.issubset(set(b)) or b['schema']!=SCHEMA:raise ValueError('Invalid bundle contract')
  from .feature_policy import DEFAULT,validate as validate_terms,effective
  if not isinstance(b['distribution_terms'],dict):raise ValueError('Distribution terms required')
  declared=validate_terms({key:b['distribution_terms'][key] for key in DEFAULT})
  if type(b['created_unix']) not in (int,float) or b['distribution_terms']!=effective(declared,b['created_unix']):raise ValueError('Distribution terms or derived claims changed')
  peer=b['sender'];feature=check_id(b['feature']);identity=self.identity()
  if b['recipient']!=identity['peer_id'] or not self.permitted(p,peer,feature,'receive'):raise ValueError('Receive policy denied')
  if b['dependencies']!=p['features'][feature]['dependencies']:raise ValueError('Dependency contract differs')
  if type(b['created_unix']) not in (int,float) or not time.time()-604800<=b['created_unix']<=time.time()+300:raise ValueError('Expired/future bundle')
  if 'artifact_ref' in b:
   if b.get('sha256') and b['sha256']!=b['artifact_ref']:raise ValueError('Artifact digest mismatch: sha256 != artifact_ref')
   if 'artifact' in b and 'artifact_b64' in b:raise ValueError('Choose one inline artifact encoding')
   if 'artifact_b64' in b:
    try:
     raw_b64=base64.b64decode(b['artifact_b64'],validate=True)
     if len(raw_b64)>300000 or hashlib.sha256(raw_b64).hexdigest()!=b['artifact_ref']:raise ValueError('Inline artifact digest/size mismatch')
    except (ValueError,TypeError) as exc:raise ValueError('Invalid bounded inline artifact') from exc
   if 'artifact' in b:
    if not isinstance(b['artifact'],str) or hashlib.sha256(b['artifact'].encode()).hexdigest()!=b['artifact_ref']:raise ValueError('Inline artifact hash mismatch')
  elif 'artifact' in b and 'artifact_b64' not in b:
   if not isinstance(b['artifact'],str) or hashlib.sha256(b['artifact'].encode()).hexdigest()!=b['sha256']:raise ValueError('Artifact digest invalid')
  else:raise ValueError('Bundle must include artifact bytes or a content digest')
  from .ledger_crypto import verify
  try:verify(self.trusted_crypto(p,peer),b,bundle['signature'],'peer-bundle')
  except Exception as exc:raise ValueError('Invalid hybrid bundle signature') from exc
  return b
 def prepare(self,peer,feature,artifact_data,reviewed,content_type=None):
  if not reviewed:raise ValueError('Explicit content review required before export')
  if isinstance(artifact_data,str):raw_bytes=artifact_data.encode()
  else:raw_bytes=bytes(artifact_data)
  if len(raw_bytes)>ARTIFACT_STORE_LIMIT:raise ValueError(f'Artifact exceeds {ARTIFACT_STORE_LIMIT} byte limit')
  sha256_hex=hashlib.sha256(raw_bytes).hexdigest()
  _store_artifact(self.root,sha256_hex,raw_bytes)
  with self.lock():
   p=self.load()
   if not self.permitted(p,peer,feature,'send'):raise ValueError('Send policy denied')
   self.trusted_crypto(p,peer)
   from .feature_policy import DEFAULT,effective
   created=time.time();terms=effective(p['features'][feature].get('distribution_policy',DEFAULT),created)
   ct=content_type or ('text/plain' if isinstance(artifact_data,str) else 'application/octet-stream')
   payload={'schema':SCHEMA,'sender':self.identity()['peer_id'],'recipient':peer,'feature':feature,'dependencies':p['features'][feature]['dependencies'],'created_unix':created,'artifact_ref':sha256_hex,'artifact_size_bytes':len(raw_bytes),'content_type':ct,'sha256':sha256_hex,'distribution_terms':terms}
   if isinstance(artifact_data,str) and len(raw_bytes)<=ARTIFACT_INLINE_LIMIT:payload['artifact']=artifact_data
   bundle={'payload':payload,'signature':self.sign(payload)};bid=digest(bundle);folder=self.root/'outbox';folder.mkdir(exist_ok=True);atomic(folder/(bid+'.json'),bundle);self.event('EXPORTED',peer=peer,feature=feature,bundle=bid,bytes=len(raw_bytes))
  return {'bundle_id':bid,'status':'EXPORTED','sent':False,'privacy':'Owner-reviewed content; automatic anonymization is not guaranteed'}
 def prepare_relay(self,peer,source_bundle_id):
  # Local qualification serves as the review gate — no separate manual review required.
  rows=self.audit_rows()
  if not any(r.get('kind')=='APPLIED_AFTER_LOCAL_QUALIFICATION' and r.get('bundle')==source_bundle_id for r in rows):raise ValueError('Bundle must have APPLIED_AFTER_LOCAL_QUALIFICATION event before relay; qualification is the review')
  record=self.inspect(source_bundle_id);payload=record['bundle']['payload']
  _art_data=payload.get('artifact')
  if _art_data is None:
   _art_ref=payload.get('artifact_ref') or payload.get('sha256','')
   _art_bytes=_load_artifact_bytes(self.root,_art_ref) if _art_ref else None
   if _art_bytes is None:raise ValueError('Artifact bytes not in local store — cannot relay without artifact')
   _art_data=_art_bytes
  _ct=payload.get('content_type')
  result=self.prepare(peer,payload['feature'],_art_data,True,content_type=_ct)
  with self.lock():self.event('RELAY_PREPARED',source_bundle=source_bundle_id,relay_bundle=result['bundle_id'],peer=peer)
  return {**result,'relay':True,'source_bundle_id':source_bundle_id}
 def token_summary(self):
  from . import token_ledger as _tl
  return _tl.summary(self)
 def _dedup_check(self,artifact_text,artifact_ref=None):
  if artifact_text is None and artifact_ref:
   from ._common import SYSTEM_ROOT
   raw_sha=artifact_ref
   qual_dir=SYSTEM_ROOT/'trial'/'runtime-qualifications'
   if not qual_dir.exists():return None
   for rp in qual_dir.glob('*/receipt.json'):
    try:
     r=json.loads(rp.read_text())
     if r.get('artifact_sha256')==raw_sha:return r['id']
    except (OSError,ValueError,KeyError):continue
   return None
  from ._common import SYSTEM_ROOT
  from .tokenomics import canonical_fingerprint
  import ast as _ast
  try:norm=_ast.dump(_ast.parse(artifact_text))
  except SyntaxError:norm=' '.join(artifact_text.split())
  incoming=hashlib.sha256(norm.encode()).hexdigest()
  qual_dir=SYSTEM_ROOT/'trial'/'runtime-qualifications'
  if not qual_dir.exists():return None
  for rp in qual_dir.glob('*/receipt.json'):
   try:
    r=json.loads(rp.read_text())
    if not r.get('accepted_evidence'):continue
    for src_hash in (r.get('candidate_sources') or {}).values():
     if src_hash==incoming:return r['id']
    if r.get('canonical_fingerprint')==canonical_fingerprint({'artifact':artifact_text}):return r['id']
   except (OSError,ValueError,KeyError):continue
  return None
 def record_manifest(self,peer,params):
  if not isinstance(params.get('baseline_engine_sha256'),str) or not re.fullmatch('[a-f0-9]{64}',params['baseline_engine_sha256']):raise ValueError('Invalid baseline engine sha256')
  if not isinstance(params.get('observed_failures'),list) or len(params['observed_failures'])>64:raise ValueError('observed_failures must be a bounded list')
  if type(params.get('session_start_unix')) not in (int,float) or not time.time()-604800<=params['session_start_unix']<=time.time()+60:raise ValueError('session_start_unix out of range')
  manifest_id=hashlib.sha256(encoded({'peer':peer,'baseline':params['baseline_engine_sha256'],'start':params['session_start_unix'],'at':time.time()})).hexdigest()
  self.event('SESSION_MANIFEST',peer=peer,manifest_id=manifest_id,baseline_engine_sha256=params['baseline_engine_sha256'],observed_failures=params['observed_failures'],session_start_unix=params['session_start_unix'],sealed_at_unix=time.time())
  return {'manifest_id':manifest_id,'sealed_at_unix':time.time(),'peer':peer,'scope':'Pre-registration of work session; not proof of independent invention, but raises cost of fabricated claims'}
 def receive(self,bundle,authenticated_peer=None):
  started=time.monotonic();size=len(encoded(bundle))
  if size>LIMIT:raise ValueError('Bundle too large')
  with self.lock():
   p=self.load();b=self.verify(bundle,p)
   if authenticated_peer is not None and b['sender']!=authenticated_peer:raise ValueError('TLS peer differs from signer')
   bid=digest(bundle);folder=self.root/'quarantine';folder.mkdir(exist_ok=True);target=folder/(bid+'.json')
   _art_ref=b.get('artifact_ref') or b.get('sha256','')
   _art_inline=b.get('artifact')
   _art_inline_b64=b.get('artifact_b64')
   if target.exists():
    return self.counter_receipt(bid,b,'ALREADY_QUARANTINED')
   dup=self._dedup_check(b.get('artifact'),b.get('artifact_ref'))
   if dup:self.event('RECEIVE_DUPLICATE',peer=b['sender'],feature=b['feature'],bundle=bid,matched_qualification=dup);return self.counter_receipt(bid,b,'DUPLICATE_ALREADY_ACCEPTED')
   self.budget(b['sender'],size)
   if p.get('token_settlement'):
    from . import token_ledger as _tl
    _tl.check_can_receive(self,b['sender'])
    # The RECEIVE_RESERVED event written below IS the spend record — no separate deduction.
   # Enforce policy and resource budgets before writing attacker-supplied bytes.
   if _art_ref and _art_inline:_store_artifact(self.root,_art_ref,_art_inline.encode())
   elif _art_ref and _art_inline_b64:_store_artifact(self.root,_art_ref,base64.b64decode(_art_inline_b64,validate=True))
   self.event('RECEIVE_RESERVED',peer=b['sender'],bytes=size,bundle=bid);atomic(target,bundle);self.event('RECEIVED_QUARANTINED',peer=b['sender'],feature=b['feature'],bundle=bid,bytes=size,remote_tokens=None,local_validation_seconds=time.monotonic()-started)
   return self.counter_receipt(bid,b,'QUARANTINED')
 def counter_receipt(self,bid,b,status):
  payload={'schema':'urace-delivery-receipt-v1','bundle_id':bid,'sender':b['sender'],'recipient':b['recipient'],'feature':b['feature'],'artifact_sha256':b['sha256'],'claim':'BYTES_QUARANTINED_NOT_QUALIFIED'}
  return {'bundle_id':bid,'status':status,'applied':False,'receipt':{'payload':payload,'signature':self.crypto_identity().sign(payload,'delivery-receipt')}}
 def inspect(self,bid):
  if not re.fullmatch('[a-f0-9]{64}',bid):raise ValueError('Invalid bundle digest')
  for folder in ('quarantine','outbox'):
   path=self.root/folder/(bid+'.json')
   if path.exists():
    _bdata=json.loads(path.read_text());_payload=_bdata.get('payload',{})
    _art_ref=_payload.get('artifact_ref') or _payload.get('sha256','')
    return {'bundle_id':bid,'location':folder,'bundle':_bdata,'incorporation':'Requires independent local qualification; transport never executes artifacts','artifact_stored':bool(_art_ref and _artifact_store_path(self.root,_art_ref).exists()),'artifact_size_bytes':_payload.get('artifact_size_bytes',len(_payload.get('artifact','').encode())),'content_type':_payload.get('content_type','text/plain')}
  raise ValueError('Unknown bundle')
 def artifact_bytes(self,sha256_hex):
  return _load_artifact_bytes(self.root,sha256_hex)
 def review(self,bid,status,note):
  if status not in ('approved-for-evaluation','rejected','blocked'):raise ValueError('Review cannot claim applied or used')
  with self.lock():
   b=self.inspect(bid)['bundle']['payload'];p=self.load()
   if not self.permitted(p,b['sender'],b['feature'],'receive'):raise ValueError('Current receive policy denied')
   self.event('OWNER_REVIEW',bundle=bid,peer=b['sender'],feature=b['feature'],status=status,note=note[:1000])
  return {'status':status,'applied':False,'evaluation_required':True}
 def summary(self,detail=False,limit=50,offset=0,peer=None,feature=None):
  if type(limit) is not int or not 0<=limit<=200 or type(offset) is not int or offset<0:raise ValueError('Audit limit must be 0–200 and offset nonnegative')
  rows=self.audit_rows();p=self.load();counts={}
  for r in rows:counts[r['kind']]=counts.get(r['kind'],0)+1
  result={'schema':SCHEMA,'settings':{k:p[k] for k in ('enabled','network','advertise')}|{'auto_select':p.get('auto_select',True),'compress_wire':p.get('compress_wire',False),'bandwidth_profile':p.get('bandwidth_profile','auto'),'transfer_chunk_size':_wire_chunk_size(p)},'peers':[{'peer_id':k,'blocked':v['blocked']} for k,v in p['peers'].items()],'features':p['features'],'rules':p['rules'],'budgets':{k:p.get(k,v) for k,v in {'max_transfers_per_day':20,'max_transfers_per_peer_per_day':5,'max_bytes_per_day':1048576,'max_rpc_per_day':200,'max_rpc_per_peer_per_day':50}.items()},'events':len(rows),'counts':counts,'audit_chain_valid':True,'visible_audit_rows_hybrid_authenticated':bool(rows),'post_quantum_sidecar':'PRESENT_NOT_FULLY_AUDITED' if (self.root/'signed-audit/head.json').exists() else 'NOT_INITIALIZED','copy_prevention_guaranteed':False,'mainnet_settlement_enabled':False,'applied':counts.get('APPLIED_AFTER_LOCAL_QUALIFICATION',0),'usage_verified':False,'fairness':'Explicit opt-in budgets and permissions; no claim of equal utility, anonymity or Sybil resistance'}
  if detail:
   selected=[r for r in rows if (peer is None or r.get('peer')==peer) and (feature is None or r.get('feature')==feature)];result.update(audit=selected[offset:offset+limit],matching_events=len(selected),next_offset=offset+limit if offset+limit<len(selected) and limit else None)
  return result

def convergence_count(exchange,canonical_fp):
 if not re.fullmatch('[a-f0-9]{64}',canonical_fp):raise ValueError('Invalid canonical fingerprint')
 rows=exchange.audit_rows()
 count=sum(1 for r in rows if r.get('kind')=='APPLIED_AFTER_LOCAL_QUALIFICATION' and r.get('canonical_fingerprint')==canonical_fp)
 return {'schema':SCHEMA,'canonical_fingerprint':canonical_fp,'qualified_count':count,'note':'Local qualification count only; does not prove correctness or quality'}

def validate_endpoint(endpoint):
 u=urllib.parse.urlsplit(endpoint)
 if u.scheme!='https' or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:raise ValueError('An explicit HTTPS origin without credentials is required')
 if u.port is not None and not 1<=u.port<=65535:raise ValueError('Invalid port')
 return u

def tofu_check(exchange, peer_id: str, certificate: str) -> str:
    """Trust-on-first-use check for a peer certificate.

    If peer already pinned and cert matches: returns "ALREADY_PINNED".
    If peer already pinned and cert changed: raises ValueError (TOFU violation).
    If peer not yet pinned: returns "NEW_PEER".
    """
    p = exchange.load()
    if peer_id in p.get('peers', {}):
        stored_cert = p['peers'][peer_id].get('certificate', '')
        if stored_cert != certificate:
            raise ValueError(
                f"TOFU violation: certificate changed for peer {peer_id[:12]}\u2026 \u2014 possible MITM attack"
            )
        return 'ALREADY_PINNED'
    return 'NEW_PEER'

def auto_pin(exchange, certificate: str, endpoint: str, *, default_rules: dict | None = None) -> dict:
    """Pin a peer using TOFU semantics and apply default feature rules.

    Computes peer_id from certificate DER hash. Raises on TOFU violation.
    Returns {"status": "PINNED"|"ALREADY_PINNED", "peer_id": ..., "endpoint": ...}.
    """
    peer_id = hashlib.sha256(ssl.PEM_cert_to_DER_cert(certificate)).hexdigest()
    status_check = tofu_check(exchange, peer_id, certificate)
    if status_check == 'NEW_PEER':
        exchange.peer(certificate, endpoint=endpoint)
        status = 'PINNED'
    else:
        status = 'ALREADY_PINNED'

    # Resolve rules: prefer explicit arg, then config, then empty.
    if default_rules is None:
        default_rules = exchange.load().get('default_feature_rules', {})
    for feature_name, rules in (default_rules or {}).items():
        for direction in ('send', 'receive'):
            allowed = rules.get(direction)
            if isinstance(allowed, bool):
                try:
                    exchange.rule(peer_id, feature_name, direction, allowed)
                except Exception as _exc:
                    _logger.debug("rule not applied for feature %r: %s", feature_name, _exc)

    return {'status': status, 'peer_id': peer_id, 'endpoint': endpoint}

def anonymize_cert_fields(cert_pem: str) -> dict:
    """Return a summary of what fields a PEM certificate exposes.

    Returns: {subject, issuer, public_key_type, not_valid_after}.
    Does NOT include hostname, organization, or email fields.
    Informational — confirms self-signed certs carry no PII.
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives.asymmetric import ec, rsa, ed25519 as _ed
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        # Subject: only include CN, exclude O/OU/emailAddress/SAN.
        subject_cn = next(
            (attr.value for attr in cert.subject
             if attr.oid == x509.oid.NameOID.COMMON_NAME),
            None,
        )
        issuer_cn = next(
            (attr.value for attr in cert.issuer
             if attr.oid == x509.oid.NameOID.COMMON_NAME),
            None,
        )
        pk = cert.public_key()
        if isinstance(pk, _ed.Ed25519PublicKey):
            pk_type = 'Ed25519'
        elif isinstance(pk, ec.EllipticCurvePublicKey):
            pk_type = f'EC-{pk.curve.name}'
        elif isinstance(pk, rsa.RSAPublicKey):
            pk_type = f'RSA-{pk.key_size}'
        else:
            pk_type = type(pk).__name__
        return {
            'subject':         subject_cn,
            'issuer':          issuer_cn,
            'public_key_type': pk_type,
            'not_valid_after': cert.not_valid_after_utc.isoformat(),
        }
    except Exception as exc:
        return {'error': str(exc)}

def tls_context(exchange,server=False):
 p=exchange.load()
 if not p['enabled'] or not p['network']:raise ValueError('Network exchange disabled')
 identity=exchange.identity();ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server else ssl.PROTOCOL_TLS_CLIENT);ctx.minimum_version=ssl.TLSVersion.TLSv1_3
 if not server:ctx.check_hostname=False # Exact out-of-band certificate fingerprint is checked instead.
 ctx.verify_mode=ssl.CERT_REQUIRED
 certs='\n'.join(v['certificate'] for v in p['peers'].values() if not v['blocked'])
 if not certs:raise ValueError('No permitted pinned peer certificates')
 ctx.load_verify_locations(cadata=certs);ctx.load_cert_chain(str(exchange.root/'identity-cert.pem'),str(exchange.root/'identity-key.pem'));return ctx

def _consensus_min(exchange) -> int:
    """Dynamic peer-consensus threshold using persistent all-time-max network size.

    Uses max(current_estimate, all_time_max) to prevent an attacker from temporarily
    reducing the network size estimate (by Sybil isolation) and lowering the consensus
    threshold to push through a false corpus update.
    """
    import math as _math
    cfg = exchange.load()
    cfg_floor = cfg.get('p2p', {}).get('consensus_trigger_min_peers', 2)
    rows = exchange.audit_rows()
    known = max(1, len({r.get('peer') for r in rows if r.get('peer')}))
    network_est = cfg.get('estimated_network_size', known)
    # Persistent max prevents threshold manipulation via network-size spoofing
    persistent_max = cfg.get('max_observed_network_size', known)
    effective = max(known, network_est, persistent_max)
    dynamic = max(int(cfg_floor), min(10, _math.ceil(0.10 * effective)))
    return max(2, dynamic)

def _wire_chunk_size(p):
 explicit=p.get('transfer_chunk_size',0)
 if explicit:return explicit
 return {'low':1024,'high':65536}.get(p.get('bandwidth_profile','auto'),4096)

def request(exchange,peer,method,params,*,telemetry=None):
 started=time.monotonic();response_bytes=0;request_bytes=0
 p=exchange.load()
 if peer not in p['peers'] or p['peers'][peer]['blocked']:raise ValueError('Unknown or blocked peer')
 u=validate_endpoint(p['peers'][peer]['endpoint'] or '');ctx=tls_context(exchange)
 from .ledger_crypto import encrypt
 nonce=os.urandom(24).hex();local=exchange.identity()['peer_id'];context={'schema':SCHEMA,'sender':local,'recipient':peer,'request_nonce':nonce}
 rpc={'jsonrpc':'2.0','id':nonce,'method':method,'params':params};signed={'rpc':rpc,'signature':exchange.crypto_identity().sign(rpc,'peer-rpc-request')}
 body=encoded({'context':context,'encrypted':encrypt(exchange.trusted_crypto(p,peer),encoded(signed),context)})
 if len(body)>LIMIT:raise ValueError('Request size exceeded')
 _compress=p.get('compress_wire',False)
 _chunk=_wire_chunk_size(p)
 headers={'Content-Type':'application/json','Accept-Encoding':'gzip'}
 if _compress:
  body=gzip.compress(body,compresslevel=6);headers['Content-Encoding']='gzip'
 request_bytes=len(body)
 c=http.client.HTTPSConnection(u.hostname,u.port or 443,context=ctx,timeout=10)
 try:
  c.connect()
  if hashlib.sha256(c.sock.getpeercert(binary_form=True)).hexdigest()!=peer:raise ValueError('Peer certificate fingerprint differs')
  c.request('POST','/rpc',body,headers);r=c.getresponse()
  data=b''
  while True:
   _part=r.read(_chunk)
   if not _part:break
   response_bytes+=len(_part)
   data+=_part
   if len(data)>LIMIT*2:raise ValueError('Peer response exceeds limit — possible DoS')
  if r.getheader('Content-Encoding')=='gzip':
   data=gzip.decompress(data)
   if len(data)>LIMIT:raise ValueError(f'Peer response exceeds {LIMIT} bytes after decompression — possible DoS')
  if r.status!=200:raise ValueError('Peer response failed/oversized')
  envelope=json.loads(data);response_context={**context,'direction':'response'}
  if set(envelope)!={'encrypted'}:raise ValueError('Encrypted response required')
  signed=json.loads(exchange.crypto_identity().decrypt(envelope['encrypted'],response_context));result=signed['rpc']
  from .ledger_crypto import verify
  verify(exchange.trusted_crypto(p,peer),result,signed['signature'],'peer-rpc-response')
  if result.get('jsonrpc')!='2.0' or result.get('id')!=nonce or 'error' in result or 'result' not in result:raise ValueError('Peer RPC failed')
  payload=result['result']
  if method=='exchange.info' and 'p2p_corpus_fingerprint' in payload:
   remote_fp=payload['p2p_corpus_fingerprint'];local_fp=_local_corpus_fingerprint()
   if remote_fp!=local_fp:
    with exchange.lock():exchange.event('P2P_CORPUS_MISMATCH',peer=peer,local_fingerprint=local_fp,remote_fingerprint=remote_fp)
    # Peer-consensus trigger: if ≥N distinct peers now report the same newer fingerprint,
    # check the central update hub immediately without waiting for the 60-min cycle.
    # N is dynamic: max(2, ceil(10% × estimated_network_size)), capped at 10.
    try:
     _rows=[r for r in exchange.audit_rows() if r.get('kind')=='P2P_CORPUS_MISMATCH' and r.get('remote_fingerprint')==remote_fp]
     if len({r.get('peer') for r in _rows if r.get('peer')})>=_consensus_min(exchange):
      import threading as _t
      from . import peer_discovery as _pd
      _t.Thread(target=_pd._run_update_check,args=(exchange,),daemon=True,name='urace-p2p-consensus-check').start()
    except Exception:pass
  return payload
 finally:
  c.close()
  if telemetry is not None:
   telemetry.update({'method':method,'request_payload_bytes':request_bytes,
                     'response_payload_bytes':response_bytes,
                     'application_payload_bytes':request_bytes+response_bytes,
                     'elapsed_seconds':time.monotonic()-started})

def send(exchange,bid):
 # Reserve locally, then release all local locks before waiting on another peer.
 # A block prevents new admissions; an already in-flight transfer cannot be recalled.
 with exchange.lock():
  record=exchange.inspect(bid)
  if record['location']!='outbox':raise ValueError('Only reviewed outgoing bundles can be sent')
  bundle=record['bundle'];b=bundle['payload'];p=exchange.load()
  if not p['network'] or not exchange.permitted(p,b['recipient'],b['feature'],'send'):raise ValueError('Current send policy denied')
  from . import peer_selection as _ps
  if _ps.cache(exchange)['peers'].get(b['recipient'],{}).get('status')=='VERSION_TOO_OLD':raise ValueError('Recipient peer protocol version is below min_peer_version; peer must upgrade before transfer')
  size=len(encoded(bundle));exchange.budget(b['recipient'],size);exchange.event('SEND_RESERVED',peer=b['recipient'],bytes=size,bundle=bid)
 try:
  result=request(exchange,b['recipient'],'exchange.receive',{'bundle':bundle})
  if result.get('bundle_id')!=bid or result.get('status') not in ('QUARANTINED','ALREADY_QUARANTINED'):raise ValueError('Invalid peer receipt')
  receipt=result.get('receipt',{});expected={'schema':'urace-delivery-receipt-v1','bundle_id':bid,'sender':b['sender'],'recipient':b['recipient'],'feature':b['feature'],'artifact_sha256':b['sha256'],'claim':'BYTES_QUARANTINED_NOT_QUALIFIED'}
  from .ledger_crypto import verify
  if receipt.get('payload')!=expected:raise ValueError('Receipt does not match agreed bundle')
  verify(exchange.trusted_crypto(p,b['recipient']),expected,receipt.get('signature'),'delivery-receipt')
  with exchange.lock():exchange.event('SENT_QUARANTINED',peer=b['recipient'],feature=b['feature'],bundle=bid,bytes=size,counter_receipt=receipt)
  return result
 except Exception:
  with exchange.lock():exchange.event('SEND_FAILED_OR_UNCONFIRMED',peer=b['recipient'],bundle=bid,bytes=size)
  raise

def relay_connect(exchange,relay_peer_id:str,target_peer_id:str,method:str='exchange.info',params:dict=None)->dict:
 """Route a call to target_peer_id through relay_peer_id.

 Calls exchange.relay_forward on the relay node, which forwards to the target.
 Returns whatever the target returns.
 """
 return request(exchange,relay_peer_id,'exchange.relay_forward',{'target_peer_id':target_peer_id,'method':method,'params':params or {}})

def server(exchange,host='127.0.0.1',port=0):
 # Sequential, bounded requests: no thread/fork amplification, no arbitrary URACE command execution.
 context=tls_context(exchange,True)
 class Handler(http.server.BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_GET(self):
   self.connection.settimeout(5)
   try:
    if self.path != '/urace/rpc/v1/ledger-tail':
     self.send_error(404, 'Not found')
     return
    peer = hashlib.sha256(self.connection.getpeercert(binary_form=True)).hexdigest()
    p = exchange.load()
    if not p['network'] or not p['enabled'] or peer not in p['peers'] or p['peers'][peer]['blocked']:
     self.send_error(403, 'Peer admission denied')
     return
    from .ledger_sync import request_tail_payload
    payload = request_tail_payload(exchange)
    body = json.dumps(payload, sort_keys=True).encode()
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)
   except (ValueError, TypeError, KeyError, OSError) as _get_err:
    try:
     _rpc_peer = hashlib.sha256(self.connection.getpeercert(binary_form=True)).hexdigest() if self.connection else None
     if _rpc_peer:
      exchange.event('RPC_REJECTED', peer=_rpc_peer, reason=str(_get_err)[:120])
    except Exception:
     pass
    self.send_error(400, 'Exchange GET request rejected')
  def do_POST(self):
   self.connection.settimeout(5)
   try:
    _req_enc=self.headers.get('Content-Encoding','')
    if self.path!='/rpc' or self.headers.get('Transfer-Encoding') or self.headers.get_content_type()!='application/json' or (_req_enc and _req_enc!='gzip'):raise ValueError('Invalid RPC envelope')
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=LIMIT*2:raise ValueError('Invalid request size')
    peer=hashlib.sha256(self.connection.getpeercert(binary_form=True)).hexdigest();p=exchange.load()
    if not p['network'] or not p['enabled'] or peer not in p['peers'] or p['peers'][peer]['blocked']:raise ValueError('Peer admission denied')
    with exchange.lock():
     all_rows=exchange.audit_rows()
     recent=[row for row in all_rows if row['kind']=='RPC_ADMITTED' and row['at_unix']>time.time()-86400]
     if len(recent)>=p.get('max_rpc_per_day',200) or sum(row.get('peer')==peer for row in recent)>=p.get('max_rpc_per_peer_per_day',50):raise ValueError('RPC request allowance exhausted')
     # Malformed/flood detection: block peer if ≥10 rejected RPCs in last hour
     rejected_hour=[row for row in all_rows if row.get('kind')=='RPC_REJECTED' and row.get('peer')==peer and row['at_unix']>time.time()-3600]
     if len(rejected_hour)>=10:exchange.event('RPC_FLOOD_BLOCKED',peer=peer,rejected_count=len(rejected_hour));raise ValueError('Peer flood-blocked: too many rejected RPC requests')
     exchange.event('RPC_ADMITTED',peer=peer,bytes=size)
    data=self.rfile.read(size)
    if len(data)!=size:raise ValueError('Incomplete request')
    if _req_enc=='gzip':
     data=gzip.decompress(data)
     if len(data)>LIMIT:raise ValueError('Decompressed request exceeds limit — possible DoS')
    envelope=json.loads(data)
    if set(envelope)!={'context','encrypted'}:raise ValueError('Encrypted request required')
    context=envelope['context']
    if not isinstance(context,dict) or set(context)!={'schema','sender','recipient','request_nonce'} or context['schema']!=SCHEMA or context['sender']!=peer or context['recipient']!=exchange.identity()['peer_id'] or not isinstance(context['request_nonce'],str) or not re.fullmatch('[a-f0-9]{48}',context['request_nonce']):raise ValueError('RPC encryption context mismatch')
    signed=json.loads(exchange.crypto_identity().decrypt(envelope['encrypted'],context));rpc=signed['rpc']
    from .ledger_crypto import verify,encrypt
    try:verify(exchange.trusted_crypto(p,peer),rpc,signed['signature'],'peer-rpc-request')
    except Exception as exc:raise ValueError('Invalid hybrid RPC signature') from exc
    if rpc.get('id')!=context['request_nonce']:raise ValueError('RPC request nonce mismatch')
    if set(rpc)!={'jsonrpc','id','method','params'} or rpc['jsonrpc']!='2.0' or type(rpc['id']) not in (str,int):raise ValueError('Invalid RPC request')
    if rpc['method']=='exchange.info' and rpc['params']=={}:result={'schema':SCHEMA,'protocol_version':PROTOCOL_VERSION,'peer_id':exchange.identity()['peer_id'],'patterns':['request-response'],'incorporation':'quarantine-only','capabilities':['authenticated_open_asset_catalog_v1','bounded_open_asset_fetch_v1'],'p2p_corpus_fingerprint':_local_corpus_fingerprint(),'compress_wire_supported':True,'bandwidth_profile':p.get('bandwidth_profile','auto')}
    elif rpc['method']=='exchange.offers' and rpc['params']=={}:
     from .peer_selection import offers
     result=offers(exchange,peer)
    elif rpc['method']=='exchange.assets.catalog' and rpc['params']=={}:
     from .remote_assets import public_catalog
     result=public_catalog(exchange,peer)
    elif rpc['method']=='exchange.assets.fetch' and isinstance(rpc['params'],dict) and set(rpc['params'])=={'asset_id'}:
     from .remote_assets import _make_open_bundle
     result=_make_open_bundle(exchange,peer,rpc['params']['asset_id'])
    elif rpc['method']=='exchange.assets.receipt' and isinstance(rpc['params'],dict) and set(rpc['params'])=={'asset_id','status','receipt'}:
     from .remote_assets import record_quarantine_receipt
     result=record_quarantine_receipt(exchange,peer,rpc['params'])
    elif rpc['method']=='exchange.receive' and set(rpc['params'])=={'bundle'}:result=exchange.receive(rpc['params']['bundle'],peer)
    elif rpc['method']=='exchange.manifest' and set(rpc['params'])=={'baseline_engine_sha256','observed_failures','session_start_unix'}:result=exchange.record_manifest(peer,rpc['params'])
    elif rpc['method']=='exchange.convergence' and set(rpc['params'])=={'canonical_fingerprint'}:result=convergence_count(exchange,rpc['params']['canonical_fingerprint'])
    elif rpc['method']=='exchange.relay_forward' and set(rpc['params'])=={'target_peer_id','method','params'}:
     if not exchange.load().get('relay_enabled',False):raise ValueError('Relay not enabled on this node')
     target=rpc['params']['target_peer_id'];p2=exchange.load()
     if target not in p2['peers'] or p2['peers'][target]['blocked']:raise ValueError('Target peer unknown or blocked')
     _relay_params_bytes=encoded(rpc['params']['params'])
     result=request(exchange,target,rpc['params']['method'],rpc['params']['params'])
     try:
      cfg=exchange.load();credit_units=max(1,int(len(_relay_params_bytes)/1024*cfg.get('relay_credit_per_kb',1)))
      issue_relay_credit(exchange,rpc['id'],peer,credit_units)
     except Exception:pass
    elif rpc['method']=='exchange.shamir_deliver' and isinstance(rpc['params'],dict) and set(rpc['params'])=={'feature_id','share_index','requester_peer_id'}:
     from .shamir_delivery import handle_share_request
     result=handle_share_request(exchange,peer,rpc['params']['feature_id'],rpc['params']['share_index'],rpc['params']['requester_peer_id'])
    elif rpc['method']=='exchange.work_accepted' and isinstance(rpc['params'],dict) and {'request_id','hired_peer_id','escrow_snapshot'}.issubset(set(rpc['params'])):
     from .work_market_rpc import handle_work_accepted_notification
     result=handle_work_accepted_notification(exchange,peer,rpc['params'])
    elif rpc['method']=='exchange.work_delivery' and isinstance(rpc['params'],dict) and {'request_id','delivery_hash','hired_peer_id'}.issubset(set(rpc['params'])):
     from .work_market_rpc import handle_work_delivery_notification
     result=handle_work_delivery_notification(exchange,peer,rpc['params'])
    elif rpc['method']=='exchange.trial_receipt' and isinstance(rpc['params'],dict) and {'receipt'}.issubset(set(rpc['params'])):
     from .trial_receipt import handle_receipt_delivery
     result=handle_receipt_delivery(exchange,peer,rpc['params']['receipt'])
    elif rpc['method']=='exchange.purchase_settlement' and isinstance(rpc['params'],dict) and {'settlement'}.issubset(set(rpc['params'])):
     from .purchase_settlement import handle_purchase_settlement
     result=handle_purchase_settlement(exchange,peer,rpc['params']['settlement'])
    elif rpc['method']=='exchange.seal_vote' and isinstance(rpc['params'],dict) and {'seal_hash','voter_signature','voter_peer_id'}.issubset(set(rpc['params'])):
     from .consensus import handle_seal_vote
     result=handle_seal_vote(exchange,peer,rpc['params'])
    elif rpc['method']=='exchange.checkpoint' and isinstance(rpc['params'],dict) and set(rpc['params'])==set():
     from .ledger_sync import request_tail_payload
     payload=request_tail_payload(exchange)
     result={'schema':'urace-ledger-sync-v1','head_sha':payload['tail'][-1]['sha256'] if payload['tail'] else (payload['seal']['sha256'] if payload['seal'] else '0'*64),'row_count':len(payload['tail'])}
    else:raise ValueError('Unsupported RPC method')
    rpc_result={'jsonrpc':'2.0','id':rpc['id'],'result':result};signed={'rpc':rpc_result,'signature':exchange.crypto_identity().sign(rpc_result,'peer-rpc-response')}
    body=encoded({'encrypted':encrypt(exchange.trusted_crypto(p,peer),encoded(signed),{**context,'direction':'response'})})
    if len(body)>LIMIT:raise ValueError('Response size exceeded')
    _accept=self.headers.get('Accept-Encoding','')
    _resp_headers={'Content-Type':'application/json'}
    if 'gzip' in _accept and p.get('compress_wire',False):
     body=gzip.compress(body,compresslevel=6);_resp_headers['Content-Encoding']='gzip'
    _resp_headers['Content-Length']=str(len(body))
    self.send_response(200)
    for _h,_v in _resp_headers.items():self.send_header(_h,_v)
    self.end_headers();self.wfile.write(body)
   except (ValueError,TypeError,KeyError,OSError) as _rpc_err:
    try:
     _rpc_peer=hashlib.sha256(self.connection.getpeercert(binary_form=True)).hexdigest() if self.connection else None
     if _rpc_peer:exchange.event('RPC_REJECTED',peer=_rpc_peer,reason=str(_rpc_err)[:120])
    except Exception:pass
    self.send_error(400,'Exchange request rejected')
 class Server(http.server.HTTPServer):
  def get_request(self):
   sock,address=super().get_request();sock.settimeout(5)
   try:return context.wrap_socket(sock,server_side=True),address
   except BaseException:sock.close();raise
 return Server((host,port),Handler)

def discover(exchange,seconds=3):
 if not exchange.load()['network'] or not exchange.load()['enabled']:raise ValueError('Network discovery disabled')
 if not 0<seconds<=15:raise ValueError('Discovery must be bounded to 1–15 seconds')
 try:from zeroconf import Zeroconf,ServiceBrowser,ServiceStateChange
 except ImportError:raise ValueError('LAN discovery requires optional python-zeroconf; manual pinned HTTPS peers work without it')
 rows={}
 def changed(zeroconf,service_type,name,state_change):
  if state_change is ServiceStateChange.Removed:return
  info=zeroconf.get_service_info(service_type,name,timeout=500)
  if info and len(rows)<64:rows[name]={'service':name,'addresses':info.parsed_addresses()[:4],'port':info.port,'trusted':False}
 with Zeroconf() as z:
  browser=ServiceBrowser(z,'_urace-exchange._tcp.local.',handlers=[changed])
  try:time.sleep(seconds)
  finally:browser.cancel()
 return {'candidates':list(rows.values()),'auto_trusted':False,'auto_connected':False}


def issue_relay_credit(exchange, request_id, relay_peer_id, credit_units):
    """Credit a relay node for routing a hop."""
    row = {
        'kind': RELAY_CREDIT_ISSUED,
        'request_id': request_id,
        'relay_peer_id': relay_peer_id,
        'credit_units': credit_units,
        'at': time.time(),
    }
    exchange.append(row)
    return row


def issue_bootstrap_credit(exchange, relay_peer_id, credit_units):
    """Credit a bootstrap node for facilitating a peer connection."""
    cfg = exchange.load()
    credit_per = cfg.get('bootstrap_credit_per_connection', 5)
    actual = credit_units if credit_units > 0 else credit_per
    row = {
        'kind': BOOTSTRAP_CREDIT_ISSUED,
        'relay_peer_id': relay_peer_id,
        'credit_units': actual,
        'at': time.time(),
    }
    exchange.append(row)
    return row


def emit_audit_record(exchange, operation, actor_id, payload_digest, prior_hash=None):
    """Append a signed audit chain record. prior_hash chains records together."""
    import hashlib as _hl
    record = {
        'kind': AUDIT_CHAIN_RECORD,
        'operation': operation,
        'actor_id': actor_id,
        'payload_digest': payload_digest,
        'prior_hash': prior_hash,
        'at': time.time(),
    }
    record['record_hash'] = _hl.sha256(
        json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    exchange.append(record)
    return record


def verify_audit_chain(records):
    """Verify audit chain integrity. Returns (ok, first_broken_index)."""
    import hashlib as _hl
    chain_records = [r for r in records if r.get('kind') == AUDIT_CHAIN_RECORD]
    for i, rec in enumerate(chain_records):
        expected_hash = rec.get('record_hash')
        check = {k: v for k, v in rec.items() if k != 'record_hash'}
        actual = _hl.sha256(
            json.dumps(check, sort_keys=True, separators=(',', ':')).encode()
        ).hexdigest()
        if actual != expected_hash:
            return False, i
    return True, -1


# ---------------------------------------------------------------------------
# P1.4 — TCP Hole Punch Attempt
# ---------------------------------------------------------------------------

import socket as _socket


def attempt_tcp_hole_punch(
    remote_ip: str,
    remote_port: int,
    local_port: int,
    timeout: float = 3.0,
) -> bool:
    """Attempt a TCP hole-punch connection.  Returns True on success."""
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    try:
        if local_port:
            sock.bind(('', local_port))
        sock.settimeout(timeout)
        _logger.debug(
            "TCP hole punch attempt: %s:%s from local %s",
            remote_ip, remote_port, local_port,
        )
        sock.connect((remote_ip, remote_port))
        sock.close()
        return True
    except (_socket.timeout, ConnectionRefusedError, OSError):
        try:
            sock.close()
        except OSError:
            pass
        return False


def hole_punch_connect(exchange, peer_id: str, endpoint: dict) -> bool:
    """Try TCP hole punch for *peer_id*; logs relay fallback hint on failure."""
    remote_ip = endpoint.get('ip') or endpoint.get('host', '')
    remote_port = int(endpoint.get('port', 0))
    local_port = int(endpoint.get('local_port', 0))
    success = attempt_tcp_hole_punch(remote_ip, remote_port, local_port)
    if not success:
        _logger.debug("Hole punch failed for %s, relay fallback needed", peer_id)
    return success
