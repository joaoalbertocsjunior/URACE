"""Peer source patches enter the same sealed local qualification and single-controller deployment queue."""
from pathlib import Path
import json,time,uuid
from common import atomic
import runtime_evaluation as ev

def exchange(base):
 from urace.peer_exchange import Exchange,directory
 cfg=json.loads((Path(base).parent/'runtime/urace/config.json').read_text());return Exchange(directory(cfg))

def validate_receipt(base,receipt):
 ex=exchange(base);record=ex.inspect(receipt['bundle_id'])
 if record['location']!='quarantine':raise ValueError('Received quarantined artifact required')
 bundle=record['bundle'];ex.verify(bundle,ex.load())
 b=bundle['payload']
 if receipt.get('peer_id')!=b['sender'] or receipt.get('artifact_sha256')!=b['sha256'] or receipt.get('native_tokens_scope')!='local-only; remote production unknown':raise ValueError('Peer provenance receipt differs')
 reviews=[r for r in ex.audit_rows() if r['kind']=='OWNER_REVIEW' and r.get('bundle')==receipt['bundle_id']]
 if not reviews or reviews[-1].get('status')!='approved-for-evaluation':raise ValueError('Current owner review does not permit evaluation')
 return b

def enqueue(base,bundle_id):
 base=Path(base);ex=exchange(base);record=ex.inspect(bundle_id)
 receipt={'id':uuid.uuid4().hex,'kind':'peer-candidate','role':'PEER_CANDIDATE','provider':'peer','product_id':'urace-runtime:'+str(base.parent.resolve()),'tokens':0,'native_tokens_scope':'local-only; remote production unknown','remote_tokens':None,'bundle_id':bundle_id,'peer_id':record['bundle']['payload']['sender'],'artifact_sha256':record['bundle']['payload']['sha256'],'failure':None,'at':ev.now()}
 b=validate_receipt(base,receipt);payload=json.loads(b['artifact'])
 if not isinstance(payload,dict) or set(payload)!={'schema','module','edits'} or payload['schema']!='runtime-source-edits-v1' or payload['module'] not in ev.ALLOWED or not isinstance(payload['edits'],list) or not 1<=len(payload['edits'])<=4:raise ValueError('A bounded declared runtime helper patch is required')
 for edit in payload['edits']:
  if not isinstance(edit,dict) or set(edit)!={'old','new'} or not all(isinstance(v,str) and 0<len(v.encode())<=16384 for v in edit.values()):raise ValueError('Bounded exact source edits required')
 folder=base/'runtime-peer-requests';folder.mkdir(exist_ok=True);path=folder/(bundle_id+'.json')
 with ex.lock():
  # Recheck review/policy at the queue boundary; never widen permissions through a bundle.
  validate_receipt(base,receipt)
  if path.exists():return {'status':'ALREADY_QUEUED','bundle_id':bundle_id}
  if len(list(folder.glob('*.json')))>=10:raise ValueError('Peer evaluation queue is full')
  atomic(base/'transport'/(receipt['id']+'.json'),receipt);atomic(path,{'schema':'runtime-peer-request-v1','bundle_id':bundle_id,'receipt_id':receipt['id'],'at':ev.now()});ex.event('EVALUATION_QUEUED',bundle=bundle_id,peer=receipt['peer_id'],feature=b['feature'])
 return {'status':'QUEUED_FOR_LOCAL_QUALIFICATION','bundle_id':bundle_id,'native_model_calls':0,'applied':False}

def process_one(base,state,config,interval):
 import runtime_cycle as cycle,runtime_qualification as qualification,runtime_quality_gate as gate
 base=Path(base);paths=sorted((base/'runtime-peer-requests').glob('*.json'),key=lambda p:(p.stat().st_mtime,p.name))
 if not paths:return None
 path=paths[0];request=json.loads(path.read_text());receipt=json.loads((base/'transport'/(request['receipt_id']+'.json')).read_text());identifier='cycle-'+uuid.uuid4().hex;folder=base/'runtime-cycles'/identifier;folder.mkdir(parents=True);package=base.parent/'runtime/urace';ex=exchange(base)
 state={'id':identifier,'engine_sha256':ev.engine(package),'product_id':receipt['product_id'],'completed_cycles':state.get('completed_cycles',0),'inference_calls':0,'started_at':ev.now(),'peer_bundle_id':request['bundle_id']}
 try:
  b=validate_receipt(base,receipt);payload=json.loads(b['artifact']);before=folder/'baseline';candidate=folder/'candidate';ev.snapshot(package,before);ev.snapshot(package,candidate);module=payload['module']
  if module not in ev.ALLOWED:raise ValueError('Protected runtime module')
  text=(candidate/module).read_text()
  for edit in payload['edits']:
   if not edit['old'] or text.count(edit['old'])!=1:raise ValueError('Peer patch does not match current source exactly')
   text=text.replace(edit['old'],edit['new'],1)
  (candidate/module).write_text(text);ev.validate_sources(before,candidate)
  cycle.emit(base,state,'EVALUATING','Peer patch requires the unchanged local held-out and regression acceptance',peer_id=b['sender'])
  baseline=ev.measure(base,before,'peer_baseline')
  if baseline['score']+gate.gate_config(config)['minimum_delta']>100:raise ValueError('No score headroom under unchanged owner contract; no full regression or incorporation justified')
  atomic(base/'runtime-baseline-latest.json',{'evaluation_id':baseline['id']});cert=qualification.qualify(base,before,candidate,baseline['id'],receipt);decision=gate.gate_decision(base,config,qualification_id=cert['id'])
  if decision['decision']!='ACCEPTED':raise ValueError(decision['reason'])
  with ex.lock():validate_receipt(base,receipt);ex.event('LOCALLY_QUALIFIED',bundle=request['bundle_id'],peer=b['sender'],feature=b['feature'],qualification_id=cert['id'],remote_tokens=None)
  if config.get('runtime_workflow',{}).get('auto_deploy',True) is not True:return cycle.emit(base,state,'AWAITING_APPROVAL','Peer candidate passed local acceptance; automatic deployment disabled',qualification_id=cert['id'],proposal_reason='Owner-reviewed peer helper patch',proposal_provider='peer',next_due_unix=time.time()+interval)
  atomic(base/'runtime-deployment-pending.json',{'cycle_id':identifier,'qualification_id':cert['id'],'rationale':'Locally qualified owner-reviewed peer helper patch','proposer_provider':'peer','engine_before':ev.engine(before),'at':ev.now()})
  return cycle.emit(base,state,'READY_TO_DEPLOY','Peer candidate awaits the same drained supervisor transaction',qualification_id=cert['id'])
 except Exception as error:
  with ex.lock():ex.event('LOCAL_EVALUATION_REJECTED',bundle=request['bundle_id'],peer=receipt.get('peer_id'),reason=type(error).__name__)
  stage,reason,extra=cycle.completed(state,'REJECTED',str(error)[:500],interval);return cycle.emit(base,state,stage,reason,**extra)
 finally:
  # Preserve every attempted queue item even when no code was incorporated.
  path.rename(folder/'peer-request-completed.json')
