"""Persistent runtime improvement cycle owned by the existing single supervisor."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,json,os,signal,subprocess,sys,time,uuid
from common import BASE,atomic
import runtime_evaluation as ev

SCHEMA='runtime-cycle-v1'
TERMINAL={'NO_JUSTIFIED_CHANGE','REJECTED','FAILED','DEPLOYED','CANCELLED'}

def settings(config):
 wf=config.get('runtime_workflow',{});result={'enabled':wf.get('enabled',False),'auto_deploy':wf.get('auto_deploy',True),'interval_seconds':wf.get('interval_seconds',10800)}
 if type(result['enabled']) is not bool or type(result['auto_deploy']) is not bool or type(result['interval_seconds']) is not int or not 60<=result['interval_seconds']<=86400:raise ValueError('Invalid runtime-cycle controls')
 return result

def load(path,default):return json.loads(Path(path).read_text()) if Path(path).exists() else default

def emit(base,state,stage,reason,**extra):
 base=Path(base);state.update(schema=SCHEMA,stage=stage,status=stage,reason=reason,updated_at=ev.now(),**extra);atomic(base/'runtime-cycle-latest.json',state)
 from urace.authenticated_journal import append_row
 append_row(base/'runtime-cycle-events.jsonl',state)
 return state

def status(base=BASE):
 return load(Path(base)/'runtime-cycle-latest.json',{'schema':SCHEMA,'stage':'NOT_STARTED','status':'NOT_STARTED','reason':'No runtime cycle has started','completed_cycles':0})

def completed(state,stage,reason,interval,**extra):
 state.update(completed_at=ev.now(),completed_cycles=state.get('completed_cycles',0)+1,next_due_unix=time.time()+interval)
 return stage,reason,extra

def proposal(base,payload):
 """Subprocess isolates native transport environment and cancellation accounting."""
 process=subprocess.Popen([sys.executable,str(Path(base)/'runtime_proposal.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 try:
  stdout,stderr=process.communicate(json.dumps(payload),timeout=140)
  if process.returncode:raise RuntimeError('Proposal worker failed: '+stderr[-300:])
  return json.loads(stdout)
 except BaseException:
  if process.poll() is None:
   os.killpg(process.pid,signal.SIGTERM)
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
  raise

def source_stat(package):
 return {p.name:[p.stat().st_mtime_ns,p.stat().st_size] for p in sorted(Path(package).glob('*.py')) if p.is_file() and not p.is_symlink()}

def _pins(base):
 from source_integrity import matches
 pins=load(Path(base)/'harness-manifest.json',{})
 return bool(pins) and all(matches(Path(base)/n,h) for n,h in pins.items())

def step(base=BASE):
 base=Path(base)
 with (base/'runtime-cycle.guard').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:return _step(base)
  except Exception as error:
   state=status(base);state.update(completed_at=ev.now(),completed_cycles=state.get('completed_cycles',0)+1,next_due_unix=time.time()+10800)
   return emit(base,state,'FAILED',type(error).__name__+': '+str(error)[:500])

def _step(base):
 from controls import effective
 from product_controls import get_improvement_enabled
 import runtime_quality_gate as gate,runtime_qualification as qualification
 config=load(base.parent/'runtime/urace/config.json',{});cfg=settings(config);state=status(base);package=base.parent/'runtime/urace';pid='urace-runtime:'+str(base.parent.resolve())
 if not cfg['enabled'] or not get_improvement_enabled(pid,base):return {'status':'DISABLED','reason':'Runtime product disabled','inference_calls':0}
 controls=effective(base)
 if controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals']:return {'status':'WAITING','reason':'Owner controls','inference_calls':0}
 if time.time()>=load(base/'trial-clock.json',{}).get('ends_unix',0):return {'status':'WAITING','reason':'Original trial ended','inference_calls':0}
 if (base/'runtime-deployment-pending.json').exists():return {'status':'READY_TO_DEPLOY','reason':'Awaiting drained supervisor','inference_calls':0}
 signature=source_stat(package)
 if not any((base/'runtime-peer-requests').glob('*.json')) and state.get('stage')!='AWAITING_APPROVAL' and time.time()<state.get('next_due_unix',0) and state.get('source_stat')==signature:return {'status':'WAITING','reason':'Next scheduled runtime review; no execution or repeated content scan','next_due_unix':state['next_due_unix'],'inference_calls':0}
 if not _pins(base):return emit(base,state,'BLOCKED','SOURCE_INTEGRITY',inference_calls=0)
 # Approval waits reuse the sealed certificate; enabling deployment never repeats native work.
 if state.get('stage')=='AWAITING_APPROVAL' and state.get('engine_sha256')==ev.engine(package):
  cert=qualification.load_qualification(base,state['qualification_id'])
  decision=gate.gate_decision(base,config,qualification_id=cert['id'])
  if decision['decision']!='ACCEPTED':return emit(base,state,'BLOCKED',decision['reason'],next_due_unix=time.time()+cfg['interval_seconds'])
  if not cfg['auto_deploy']:return {'status':'AWAITING_APPROVAL','reason':'Owner disabled automatic deployment','inference_calls':0}
  atomic(base/'runtime-deployment-pending.json',{'cycle_id':state['id'],'qualification_id':cert['id'],'rationale':state['proposal_reason'],'proposer_provider':state['proposal_provider'],'engine_before':state['engine_sha256'],'at':ev.now()})
  return emit(base,state,'READY_TO_DEPLOY','Previously qualified candidate awaits native-worker drain')
 if qualification.installation_ready(base):
  from peer_runtime import process_one
  peer_result=process_one(base,state,config,cfg['interval_seconds'])
  if peer_result is not None:return peer_result
 # Baseline and public discovery are model-free, even when every executor is unavailable.
 continuing=state.get('stage') not in TERMINAL and state.get('engine_sha256')==ev.engine(package) and isinstance(state.get('id'),str) and state['id'].startswith('cycle-') and state['id'].replace('-','').isalnum()
 cycle_id=state['id'] if continuing else 'cycle-'+uuid.uuid4().hex;folder=base/'runtime-cycles'/cycle_id;folder.mkdir(parents=True,exist_ok=True);before=folder/'baseline'
 if not continuing or not before.exists():ev.snapshot(package,before)
 if ev.inventory(before)!=ev.inventory(package):raise ValueError('Runtime cycle baseline no longer matches live source')
 if not continuing:state={'id':cycle_id,'product_id':pid,'engine_sha256':ev.engine(before),'completed_cycles':state.get('completed_cycles',0),'started_at':ev.now(),'inference_calls':0,'source_stat':signature}
 emit(base,state,'BASELINE','Measuring frozen runtime contracts independently')
 cached=gate.read_latest_evaluation(base)
 baseline=cached if cached and cached['sources']==ev.inventory(before) else ev.measure(base,before,'baseline')
 atomic(base/'runtime-baseline-latest.json',{'evaluation_id':baseline['id'],'at':ev.now(),'role':'baseline'})
 emit(base,state,'DISCOVERY','Checking public development diagnostics without private-case feedback',baseline_score=baseline['score'],baseline_id=baseline['id'])
 public=None
 cached_public=load(base/'runtime-public-latest.json',{})
 if cached_public.get('evaluation_id'):
  try:
   value=ev.load_receipt(base,cached_public['evaluation_id'],public=True)
   if value['sources']==baseline['sources']:public=value
  except (OSError,ValueError,KeyError):pass
 if public is None:public=ev.measure(base,before,'public_discovery',public=True)
 atomic(base/'runtime-public-latest.json',{'evaluation_id':public['id'],'scope':'Reused only for identical source and sealed evaluator/image/input contract'})
 state['public_evaluation_id']=public['id'];failed=[name for name,passed in public['case_results'].items() if not passed]
 minimum=gate.gate_config(config)['minimum_delta']
 if not failed or baseline['score']+minimum>100:
  stage,reason,extra=completed(state,'NO_JUSTIFIED_CHANGE','No public defect with a possible gain under the frozen owner contract; no model request',cfg['interval_seconds'],public_failures=failed)
  return emit(base,state,stage,reason,**extra)
 if not qualification.installation_ready(base):return emit(base,state,'BLOCKED','Isolated deployment/recovery qualification has not been installed',next_due_unix=time.time()+60)
 # A separately selected public example identifies work; held-out observations never enter this packet.
 task={'id':'completed-objective-planning','module':'milestone_suggestions.py','bottleneck':'A completed owner objective is still proposed as unfinished milestone work','expected_benefit':'Avoid duplicate planning work after an objective has completed','action_recommendation':'Preserve known completion across native objective-status spelling','status':'AUTHORIZED_FOR_ISOLATED_CANDIDATE','expected_benefit_score':None,'public_check':next(case for case in ev.cases(public=True) if case['id']==failed[0])}
 if failed[0]!='completed-objective-planning':return emit(base,state,'BLOCKED','Public defect requires independently declared scoped work; no speculative repair')
 task['public_check'].pop('module',None)
 payload={'task':task,'source':(before/task['module']).read_text(),'engine_sha256':ev.engine(before)}
 emit(base,state,'AWAITING_EXECUTOR','Checking ordinary/shared admission for the public defect',bottleneck=task['bottleneck'],action_recommendation=task['action_recommendation'],expected_benefit=task['expected_benefit'],expected_benefit_score=None)
 prior=load(folder/'proposal-result.json',{})
 result=prior if prior.get('status')=='PROPOSAL_COMPLETE' else proposal(base,payload);atomic(folder/'proposal-result.json',result);state['inference_calls']=result.get('inference_calls')
 if result.get('status')=='DEFERRED':return emit(base,state,'WAITING',result.get('reason'),next_due_unix=time.time()+60)
 if result.get('status')!='PROPOSAL_COMPLETE':
  stage,reason,extra=completed(state,'FAILED','Runtime proposal failed; receipt retained',cfg['interval_seconds']);return emit(base,state,stage,reason,**extra)
 receipt=result['receipt'];advice=result['proposal']
 if advice.get('no_change'):
  stage,reason,extra=completed(state,'NO_JUSTIFIED_CHANGE',advice['reason'],cfg['interval_seconds']);return emit(base,state,stage,reason,**extra)
 if type(receipt.get('tokens')) is not int or receipt.get('failure'):return emit(base,state,'BLOCKED','Proposal accounting incomplete; no deployment',proposal_receipt_id=receipt.get('id'))
 candidate=folder/'candidate';ev.snapshot(before,candidate);text=(candidate/task['module']).read_text()
 for edit in advice['edits']:
  if not isinstance(edit,dict) or set(edit)!={'old','new'} or not all(isinstance(v,str) and len(v.encode())<=16384 for v in edit.values()) or not edit['old'] or text.count(edit['old'])!=1:raise ValueError('Proposal anchor outside bounded unique source')
  text=text.replace(edit['old'],edit['new'],1)
 (candidate/task['module']).write_text(text)
 try:
  ev.validate_sources(before,candidate)
  emit(base,state,'EVALUATING','Independent held-out contracts and sealed full regression',proposal_receipt_id=receipt['id'])
  cert=qualification.qualify(base,before,candidate,baseline['id'],receipt)
  decision=gate.gate_decision(base,config,qualification_id=cert['id'])
 except Exception as error:
  stage,reason,extra=completed(state,'REJECTED',type(error).__name__+': '+str(error)[:500],cfg['interval_seconds']);return emit(base,state,stage,reason,**extra)
 atomic(folder/'qualification.json',cert)
 if decision['decision']!='ACCEPTED':
  stage,reason,extra=completed(state,'REJECTED',decision['reason'],cfg['interval_seconds'],qualification_id=cert['id']);return emit(base,state,stage,reason,**extra)
 if not cfg['auto_deploy']:return emit(base,state,'AWAITING_APPROVAL','Owner disabled automatic deployment',qualification_id=cert['id'],proposal_reason=advice['reason'],proposal_provider=receipt['provider'],next_due_unix=time.time()+cfg['interval_seconds'])
 atomic(base/'runtime-deployment-pending.json',{'cycle_id':cycle_id,'qualification_id':cert['id'],'rationale':advice['reason'],'proposer_provider':receipt['provider'],'engine_before':ev.engine(before),'at':ev.now()})
 return emit(base,state,'READY_TO_DEPLOY','Qualified candidate awaits native-worker drain',qualification_id=cert['id'])

def apply_pending(base=BASE):
 import runtime_trial
 base=Path(base);path=base/'runtime-deployment-pending.json'
 if not path.exists():return False
 pending=load(path,{});state=status(base);config=load(base.parent/'runtime/urace/config.json',{});cfg=settings(config)
 emit(base,state,'DEPLOYING','All existing trial workers drained; applying qualified transaction')
 try:
  sid=runtime_trial.deploy(base,config,pending,{'qualification_id':pending['qualification_id'],'supervisor_drained':True})
  stage,reason,extra=completed(state,'DEPLOYED','Independent candidate accepted and post-deployment checks passed',cfg['interval_seconds'],snapshot_id=sid)
  emit(base,state,stage,reason,**extra)
 except Exception as error:
  stage,reason,extra=completed(state,'REJECTED',type(error).__name__+': '+str(error)[:500],cfg['interval_seconds']);emit(base,state,stage,reason,**extra)
 finally:
  # Keep the complete pending receipt as immutable cycle evidence, not a silent deletion.
  destination=base/'runtime-cycles'/pending['cycle_id']/'deployment-request-completed.json';os.replace(path,destination)
 return True
