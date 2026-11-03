"""Opt-in, product-scoped signed artifact exchange. Incoming artifacts are quarantined, never executed."""
from pathlib import Path
from contextlib import contextmanager
import base64, fcntl, hashlib, http.client, http.server, ipaddress, json, os, re, ssl, subprocess, tempfile, time, urllib.parse, datetime

SCHEMA='urace-exchange-v2'
PROTOCOL_VERSION=2
LIMIT=524288
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

class Exchange:
 def __init__(self,root):self.root=Path(root)
 def load(self):
  p=self.root/'policy.json'
  return json.loads(p.read_text()) if p.exists() else {'schema':SCHEMA,'enabled':True,'network':False,'advertise':False,'auto_select':True,'auto_relay':False,'token_settlement':False,'auto_trust_first_contact':False,'default_feature_rules':{},'relay_only':False,'peers':{},'features':{},'rules':{},'feature_borrow_enabled':True,'max_transfers_per_day':20,'max_transfers_per_peer_per_day':5,'max_bytes_per_day':1048576,'max_rpc_per_day':200,'max_rpc_per_peer_per_day':50,'min_peer_version':PROTOCOL_VERSION}
 @contextmanager
 def lock(self):
  self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  if self.root.is_symlink():raise ValueError('Exchange directory cannot be a symlink')
  os.chmod(self.root,0o700)
  with (self.root/'exchange.lock').open('a') as f:
   fcntl.flock(f,fcntl.LOCK_EX);yield
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
    if k in ('enabled','network','advertise','auto_select','auto_relay','token_settlement','relay_enabled','auto_trust_first_contact','relay_only','feature_borrow_enabled','p2p_mint_enabled','p2p_sell_enabled','compress_enabled','decompress_enabled'):
     if type(v) is not bool:raise ValueError('Boolean exchange settings required')
    elif k=='default_feature_rules':
     if not isinstance(v,dict):raise ValueError('default_feature_rules must be a dict')
    elif k in ('max_transfers_per_day','max_transfers_per_peer_per_day','max_bytes_per_day','max_rpc_per_day','max_rpc_per_peer_per_day','bundle_max_age_seconds'):
     if type(v) is not int or not 1<=v<=1073741824:raise ValueError('Positive bounded exchange allowance required')
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
  return {'peer_id':fingerprint,'trusted_for_content':False}
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
  if not isinstance(b,dict) or set(b)!={'schema','sender','recipient','feature','dependencies','created_unix','artifact','sha256','distribution_terms'} or b['schema']!=SCHEMA:raise ValueError('Invalid bundle contract')
  from .feature_policy import DEFAULT,validate as validate_terms,effective
  if not isinstance(b['distribution_terms'],dict):raise ValueError('Distribution terms required')
  declared=validate_terms({key:b['distribution_terms'][key] for key in DEFAULT})
  if type(b['created_unix']) not in (int,float) or b['distribution_terms']!=effective(declared,b['created_unix']):raise ValueError('Distribution terms or derived claims changed')
  peer=b['sender'];feature=check_id(b['feature']);identity=self.identity()
  if b['recipient']!=identity['peer_id'] or not self.permitted(p,peer,feature,'receive'):raise ValueError('Receive policy denied')
  if b['dependencies']!=p['features'][feature]['dependencies']:raise ValueError('Dependency contract differs')
  if type(b['created_unix']) not in (int,float) or not time.time()-604800<=b['created_unix']<=time.time()+300:raise ValueError('Expired/future bundle')
  if not isinstance(b['artifact'],str) or hashlib.sha256(b['artifact'].encode()).hexdigest()!=b['sha256']:raise ValueError('Artifact digest invalid')
  from .ledger_crypto import verify
  try:verify(self.trusted_crypto(p,peer),b,bundle['signature'],'peer-bundle')
  except Exception as exc:raise ValueError('Invalid hybrid bundle signature') from exc
  return b
 def prepare(self,peer,feature,artifact,reviewed):
  if not reviewed:raise ValueError('Explicit content review required before export')
  if not isinstance(artifact,str) or len(artifact.encode())>LIMIT//2:raise ValueError('Bounded UTF-8 artifact required')
  with self.lock():
   p=self.load()
   if not self.permitted(p,peer,feature,'send'):raise ValueError('Send policy denied')
   self.trusted_crypto(p,peer)
   from .feature_policy import DEFAULT,effective
   created=time.time();terms=effective(p['features'][feature].get('distribution_policy',DEFAULT),created)
   payload={'schema':SCHEMA,'sender':self.identity()['peer_id'],'recipient':peer,'feature':feature,'dependencies':p['features'][feature]['dependencies'],'created_unix':created,'artifact':artifact,'sha256':hashlib.sha256(artifact.encode()).hexdigest(),'distribution_terms':terms};bundle={'payload':payload,'signature':self.sign(payload)};bid=digest(bundle);folder=self.root/'outbox';folder.mkdir(exist_ok=True);atomic(folder/(bid+'.json'),bundle);self.event('EXPORTED',peer=peer,feature=feature,bundle=bid,bytes=len(encoded(bundle)))
  return {'bundle_id':bid,'status':'EXPORTED','sent':False,'privacy':'Owner-reviewed content; automatic anonymization is not guaranteed'}
 def prepare_relay(self,peer,source_bundle_id):
  # Local qualification serves as the review gate — no separate manual review required.
  rows=self.audit_rows()
  if not any(r.get('kind')=='APPLIED_AFTER_LOCAL_QUALIFICATION' and r.get('bundle')==source_bundle_id for r in rows):raise ValueError('Bundle must have APPLIED_AFTER_LOCAL_QUALIFICATION event before relay; qualification is the review')
  record=self.inspect(source_bundle_id);payload=record['bundle']['payload']
  result=self.prepare(peer,payload['feature'],payload['artifact'],True)
  with self.lock():self.event('RELAY_PREPARED',source_bundle=source_bundle_id,relay_bundle=result['bundle_id'],peer=peer)
  return {**result,'relay':True,'source_bundle_id':source_bundle_id}
 def token_summary(self):
  from . import token_ledger as _tl
  return _tl.summary(self)
 def _dedup_check(self,artifact_text):
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
   if target.exists():
    return self.counter_receipt(bid,b,'ALREADY_QUARANTINED')
   dup=self._dedup_check(b['artifact'])
   if dup:self.event('RECEIVE_DUPLICATE',peer=b['sender'],feature=b['feature'],bundle=bid,matched_qualification=dup);return self.counter_receipt(bid,b,'DUPLICATE_ALREADY_ACCEPTED')
   self.budget(b['sender'],size)
   if p.get('token_settlement'):
    from . import token_ledger as _tl
    _tl.check_can_receive(self,b['sender'])
    # The RECEIVE_RESERVED event written below IS the spend record — no separate deduction.
   self.event('RECEIVE_RESERVED',peer=b['sender'],bytes=size,bundle=bid);atomic(target,bundle);self.event('RECEIVED_QUARANTINED',peer=b['sender'],feature=b['feature'],bundle=bid,bytes=size,remote_tokens=None,local_validation_seconds=time.monotonic()-started)
   return self.counter_receipt(bid,b,'QUARANTINED')
 def counter_receipt(self,bid,b,status):
  payload={'schema':'urace-delivery-receipt-v1','bundle_id':bid,'sender':b['sender'],'recipient':b['recipient'],'feature':b['feature'],'artifact_sha256':b['sha256'],'claim':'BYTES_QUARANTINED_NOT_QUALIFIED'}
  return {'bundle_id':bid,'status':status,'applied':False,'receipt':{'payload':payload,'signature':self.crypto_identity().sign(payload,'delivery-receipt')}}
 def inspect(self,bid):
  if not re.fullmatch('[a-f0-9]{64}',bid):raise ValueError('Invalid bundle digest')
  for folder in ('quarantine','outbox'):
   path=self.root/folder/(bid+'.json')
   if path.exists():return {'bundle_id':bid,'location':folder,'bundle':json.loads(path.read_text()),'incorporation':'Requires independent local qualification; transport never executes artifacts'}
  raise ValueError('Unknown bundle')
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
  result={'schema':SCHEMA,'settings':{k:p[k] for k in ('enabled','network','advertise')}|{'auto_select':p.get('auto_select',True)},'peers':[{'peer_id':k,'blocked':v['blocked']} for k,v in p['peers'].items()],'features':p['features'],'rules':p['rules'],'budgets':{k:p.get(k,v) for k,v in {'max_transfers_per_day':20,'max_transfers_per_peer_per_day':5,'max_bytes_per_day':1048576,'max_rpc_per_day':200,'max_rpc_per_peer_per_day':50}.items()},'events':len(rows),'counts':counts,'audit_chain_valid':True,'visible_audit_rows_hybrid_authenticated':bool(rows),'post_quantum_sidecar':'PRESENT_NOT_FULLY_AUDITED' if (self.root/'signed-audit/head.json').exists() else 'NOT_INITIALIZED','copy_prevention_guaranteed':False,'mainnet_settlement_enabled':False,'applied':counts.get('APPLIED_AFTER_LOCAL_QUALIFICATION',0),'usage_verified':False,'fairness':'Explicit opt-in budgets and permissions; no claim of equal utility, anonymity or Sybil resistance'}
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
                except Exception:
                    pass  # feature not declared yet — silently skip

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

def request(exchange,peer,method,params):
 p=exchange.load()
 if peer not in p['peers'] or p['peers'][peer]['blocked']:raise ValueError('Unknown or blocked peer')
 u=validate_endpoint(p['peers'][peer]['endpoint'] or '');ctx=tls_context(exchange)
 from .ledger_crypto import encrypt
 nonce=os.urandom(24).hex();local=exchange.identity()['peer_id'];context={'schema':SCHEMA,'sender':local,'recipient':peer,'request_nonce':nonce}
 rpc={'jsonrpc':'2.0','id':nonce,'method':method,'params':params};signed={'rpc':rpc,'signature':exchange.crypto_identity().sign(rpc,'peer-rpc-request')}
 body=encoded({'context':context,'encrypted':encrypt(exchange.trusted_crypto(p,peer),encoded(signed),context)})
 if len(body)>LIMIT:raise ValueError('Request size exceeded')
 c=http.client.HTTPSConnection(u.hostname,u.port or 443,context=ctx,timeout=10)
 try:
  c.connect()
  if hashlib.sha256(c.sock.getpeercert(binary_form=True)).hexdigest()!=peer:raise ValueError('Peer certificate fingerprint differs')
  c.request('POST','/rpc',body,{'Content-Type':'application/json'});r=c.getresponse()
  data=b'';_chunk=4096
  while True:
   _part=r.read(_chunk)
   if not _part:break
   data+=_part
   if len(data)>LIMIT:raise ValueError(f'Peer response exceeds {LIMIT} bytes — possible DoS')
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
 finally:c.close()

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
  def do_POST(self):
   self.connection.settimeout(5)
   try:
    if self.path!='/rpc' or self.headers.get('Transfer-Encoding') or self.headers.get_content_type()!='application/json':raise ValueError('Invalid RPC envelope')
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=LIMIT:raise ValueError('Invalid request size')
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
    if rpc['method']=='exchange.info' and rpc['params']=={}:result={'schema':SCHEMA,'protocol_version':PROTOCOL_VERSION,'peer_id':exchange.identity()['peer_id'],'patterns':['request-response'],'incorporation':'quarantine-only','p2p_corpus_fingerprint':_local_corpus_fingerprint()}
    elif rpc['method']=='exchange.offers' and rpc['params']=={}:
     from .peer_selection import offers
     result=offers(exchange,peer)
    elif rpc['method']=='exchange.receive' and set(rpc['params'])=={'bundle'}:result=exchange.receive(rpc['params']['bundle'],peer)
    elif rpc['method']=='exchange.manifest' and set(rpc['params'])=={'baseline_engine_sha256','observed_failures','session_start_unix'}:result=exchange.record_manifest(peer,rpc['params'])
    elif rpc['method']=='exchange.convergence' and set(rpc['params'])=={'canonical_fingerprint'}:result=convergence_count(exchange,rpc['params']['canonical_fingerprint'])
    elif rpc['method']=='exchange.relay_forward' and set(rpc['params'])=={'target_peer_id','method','params'}:
     if not exchange.load().get('relay_enabled',False):raise ValueError('Relay not enabled on this node')
     target=rpc['params']['target_peer_id'];p2=exchange.load()
     if target not in p2['peers'] or p2['peers'][target]['blocked']:raise ValueError('Target peer unknown or blocked')
     result=request(exchange,target,rpc['params']['method'],rpc['params']['params'])
    else:raise ValueError('Unsupported RPC method')
    rpc_result={'jsonrpc':'2.0','id':rpc['id'],'result':result};signed={'rpc':rpc_result,'signature':exchange.crypto_identity().sign(rpc_result,'peer-rpc-response')}
    body=encoded({'encrypted':encrypt(exchange.trusted_crypto(p,peer),encoded(signed),{**context,'direction':'response'})})
    if len(body)>LIMIT:raise ValueError('Response size exceeded')
    self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
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
