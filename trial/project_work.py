"""Outcome-first project work, durable recovery and native-agent execution."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,time,uuid,fcntl,sys,os
from common import BASE,atomic
from controls import effective
from urace.executor_capabilities import digest as capability_digest
from repository_tasks import FAMILIES,brief,cases,contract,public_script,ACCEPTANCE_RUNNER
from project_tools import container,inventory,confined

def load(path,default=None):return json.loads(Path(path).read_text()) if Path(path).exists() else default

def engine_hash():
 from execution_contract import repository_fingerprint
 return repository_fingerprint(Path(__file__).parent)

def project_identity(project):return 'urace-work:'+hashlib.sha256(str(Path(project).resolve()).encode()).hexdigest()[:24]

def state_root(project,base=BASE):return Path(base)/'project-work'/project_identity(project).split(':')[1]

def initialize(project,family,base=BASE):
 project=Path(project).resolve()
 if family not in FAMILIES:raise ValueError('Unknown project template')
 if project.exists() and any(project.iterdir()):raise ValueError('Project initialization requires an empty directory')
 project.mkdir(parents=True,exist_ok=True)
 manifest={'schema':'urace-project-work-v1','family':family,'product_id':project_identity(project),'intent':'Deliver a correct executable '+family+' workflow','authority':{'delegated':['objectives','local implementation changes'],'reserved':['publish externally','spend money']},'requirements':[{'id':'deliver-'+family,'title':'Deliver '+family+' executable','scope':'implementation','success_measure':'Independent acceptance passes '+contract(family,1),'priority':80}],'allowed_files':['app.py','logic.py'],'phase':1,'adaptive':True}
 atomic(project/'project-work.json',manifest);(project/'logic.py').write_text('def compute(request):\n    raise NotImplementedError("Implement the declared workflow")\n');(project/'app.py').write_text('import json,sys,logic\ndef handle(request):\n    return logic.compute(request)\nif __name__ == "__main__":\n    print(json.dumps(handle(json.load(sys.stdin))))\n')
 root=state_root(project,base);root.mkdir(parents=True,exist_ok=True);atomic(root/'project.json',{'path':str(project),**manifest})
 registry=load(Path(base)/'products.json',{'products':[]});entry={'id':manifest['product_id'],'name':str(project),'source':'declared executable project','work_root':str(root)}
 with (Path(base)/'project-registry.guard').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);registry=load(Path(base)/'products.json',{'products':[]})
  if not any(r['id']==entry['id'] for r in registry['products']):registry['products'].append(entry);atomic(Path(base)/'products.json',registry)
 return manifest

def declaration(project):
 project=Path(project).resolve();m=load(project/'project-work.json')
 if not isinstance(m,dict) or m.get('schema')!='urace-project-work-v1' or m.get('product_id')!=project_identity(project) or m.get('family') not in FAMILIES or m.get('allowed_files')!=['app.py','logic.py'] or m.get('phase') not in (1,2):raise ValueError('Invalid project work declaration')
 if not isinstance(m.get('requirements'),list) or not m['requirements'] or any(not isinstance(r,dict) or r.get('scope')!='implementation' for r in m['requirements']):raise ValueError('Project work requires declared implementation scope')
 expected='Independent acceptance passes '+contract(m['family'],m['phase'])
 if any(r.get('success_measure')!=expected for r in m['requirements']):raise ValueError('Project requirement must reference its executable acceptance contract')
 for n in m['allowed_files']:confined(project,n)
 return m

def evaluate(workspace,rows,*,family=None,phase=1,baseline=None):
 from output_quality import cases as quality_cases,RUNNER,grade
 extra=quality_cases(family,phase) if family else []
 result=container(workspace,['-c',RUNNER if family else ACCEPTANCE_RUNNER],stdin=json.dumps([{k:c[k] for k in ('id','request')} for c in rows+extra]),writable=False)
 if result['returncode']:return {'validated':False,'passed':0,'total':len(rows),'error':result['stderr'][:1000],'quality':{'measurement_complete':False,'gate_passed':False,'reason':'Sandbox/program could not produce the quality observations'}}
 values=json.loads(result['stdout'])
 if family:return grade(family,phase,rows,extra,values,baseline,workspace)
 from executable_scores import equal
 mapping={r['id']:r for r in values};outcomes={c['id']:mapping.get(c['id'],{}).get('modules_agree') is True and equal(mapping[c['id']].get('value'),c['expected']) for c in rows}
 return {'validated':all(outcomes.values()),'passed':sum(outcomes.values()),'total':len(rows),'quality_score':100*sum(outcomes.values())/len(rows),'case_results':outcomes}

def status(project,base=BASE):
 from urace.work_policy import outcomes
 root=state_root(project,base);rows=[load(next(p.glob('result.json'),p/'checkpoint.json')) for p in (root/'runs').glob('*') if (p/'result.json').exists() or (p/'checkpoint.json').exists()];first=min([r.get('queued_unix',time.time()) for r in rows],default=time.time());return {'product_id':project_identity(project),'project':str(Path(project).resolve()),'runs':rows,'resources':outcomes(rows,max(.000001,time.time()-first)),'publication_count':len(list((root/'versions').glob('v*')))}

def prompt_json(value):
 # JSON whitespace is redundant; preserve every key, value and string byte on decode.
 return json.dumps(value,sort_keys=True,separators=(',',':'))

def task_packet(before,public_cases,byte_limit=12000):
 packet={'current_files':dict(before),'published_development_examples':list(public_cases),'truncated_files':[],'source_sha256':{n:hashlib.sha256(text.encode()).hexdigest() for n,text in before.items()}}
 while len(json.dumps(packet,sort_keys=True).encode())>byte_limit:
  if packet['published_development_examples']:packet['published_development_examples'].pop();continue
  name=max(packet['current_files'],key=lambda n:len(packet['current_files'][n]))
  text=packet['current_files'][name]
  if not text:break
  packet['current_files'][name]=text[:len(text)//2]
  if name not in packet['truncated_files']:packet['truncated_files'].append(name)
 return packet

def _authority(manifest,state):
 from urace import auto_goals,authority
 config={'auto_goals':{'enabled':True,'replenish_backlog':True},'authority':manifest['authority'],'project':{'id':manifest['product_id'],'intent':manifest['intent'],'requirements':manifest['requirements']},'executor':{'allowed_files_by_scope':{'implementation':manifest['allowed_files']}}}
 goal=auto_goals.select(config,state)
 if goal is None:raise RuntimeError('No declared useful work remains; completion must match current criteria')
 decision=authority.resolve(goal,config,state)
 if decision['outcome']!=authority.AUTONOMOUSLY_AUTHORIZED:raise RuntimeError('Project authority does not authorize this work')
 return config,goal,decision

def _publish(project,root,workspace,manifest,prepared,result,before):
 from urace import validation,cli,_common
 config,goal,decision,state=prepared;operation={'id':result['id'],'scope':'implementation','changed_files':manifest['allowed_files'],'authority_basis':decision['basis']}
 checked=validation.validate_operation(workspace,operation,{'quality':result['baseline_evaluation'].get('quality_score',0)},{'quality':result['acceptance']['quality_score']},config,state)
 if checked['verdict']!=validation.VALIDATED or not result['validated']:raise RuntimeError('Independent core validation rejected publication')
 runtime_config={**config,'state_path':str(root/'core-state.json')};after={n:confined(workspace,n).read_text() for n in manifest['allowed_files']};tx='work-'+result['id'];saved=load(root/'core-state.json',{});committed=cli.transaction_is_accepted(saved,tx)
 if any((project/n).read_text()!=(after[n] if committed else before[n]) for n in before):result['publication']='OWNER_EDIT_CONFLICT';return
 goal['status']='completed'
 for item in state.get('objectives',[]):
  if item.get('id')==goal.get('id'):item['status']='completed'
 if not committed:
  state['state_version']=saved.get('state_version',0)
  _common.atomic_write_json(_common.transaction_path(runtime_config),{'id':tx,'phase':'APPLYING','recovery_protocol':'atomic-v2','before':before,'after':after,'applied':[]})
  for n,source in after.items():_common.atomic_write_text(project/n,source)
  state.setdefault('checkpoints',[]).append({'transaction':tx});_common.save_state(runtime_config,state);cli.reconcile_transaction(runtime_config,root=project)
 expected={n:hashlib.sha256(text.encode()).hexdigest() for n,text in after.items()};snapshot=None
 for existing in sorted((root/'versions').glob('v*')):
  meta=load(existing/'metadata.json',{})
  if meta.get('run_id')==result['id']:
   if meta.get('source_sha256')!=expected or any(not (existing/n).exists() or hashlib.sha256((existing/n).read_bytes()).hexdigest()!=h for n,h in expected.items()):raise RuntimeError('Accepted snapshot conflicts; original evidence preserved')
   result.update(publication='ACCEPTED',snapshot=str(existing));return
  if not meta and all((existing/n).exists() and hashlib.sha256((existing/n).read_bytes()).hexdigest()==h for n,h in expected.items()):snapshot=existing;break
 number=int(snapshot.name[1:]) if snapshot else max([int(p.name[1:]) for p in (root/'versions').glob('v*') if p.name[1:].isdigit()],default=0)+1
 snapshot=snapshot or root/'versions'/('v%06d'%number);snapshot.mkdir(parents=True,exist_ok=True)
 for n,text in after.items():_common.atomic_write_text(snapshot/n,text)
 atomic(snapshot/'metadata.json',{'version':number,'run_id':result['id'],'product_id':manifest['product_id'],'contract':result['contract'],'engine_sha256':engine_hash(),'core_goal':goal,'authority':decision,'independent_validation':checked,'native_receipt_ids':[r['id'] for r in result['native_receipts']],'resources':{'tokens':result.get('tokens'),'elapsed_seconds':time.time()-result['queued_unix']},'baseline_evaluation':result['baseline_evaluation'],'acceptance':result['acceptance'],'specification_reference':result.get('specification_reference'),'context_profile':result.get('context_profile'),'timing':result.get('timing',{}),'source_sha256':expected});result['publication']='ACCEPTED';result['snapshot']=str(snapshot)


class ActiveBudget:
 """Persist active intervals; inactive suspension remains in end-to-end elapsed."""
 def __init__(self,result,folder,prior,invocation_started,limit=480):
  import math
  if type(prior) not in (int,float) or not math.isfinite(prior) or prior<0:raise ValueError('Invalid prior active budget')
  self.result=result;self.folder=folder;self.prior=prior;self.limit=limit;self.started=invocation_started if result.get('execution_started_unix') else None
  saved=result.get('active_budget',{})
  if saved and saved.get('prior_phase_seconds')!=prior:raise RuntimeError('Prior phase active budget changed')
  self.completed=saved.get('phase_seconds',0)
  if type(self.completed) not in (int,float) or not math.isfinite(self.completed) or self.completed<0:raise ValueError('Invalid saved active budget')
  self.measurement_complete=saved.get('measurement_complete',True)
  if not saved and result.get('native_receipts'):
   self.completed=max(0,time.time()-(result.get('execution_started_unix') or result['queued_unix']));self.measurement_complete=False
  if saved and not saved.get('closed',False):
   # An unclosed process interval cannot be inferred free after a hard crash.
   last=saved.get('last_accounted_unix')
   if type(last) not in (int,float) or not math.isfinite(last):raise ValueError('Unclosed budget lacks timestamp')
   self.completed+=max(0,time.time()-last);self.measurement_complete=False
 def activate(self):
  if self.started is None:self.started=time.monotonic()
 def phase_seconds(self):return self.completed+(max(0,time.monotonic()-self.started) if self.started is not None else 0)
 def elapsed(self):return self.prior+self.phase_seconds()
 def stamp(self,closed=False):
  self.result['active_budget']={'schema':'active-invocation-budget-v1','prior_phase_seconds':self.prior,'phase_seconds':self.phase_seconds(),'closed':closed,'last_accounted_unix':time.time(),'measurement_complete':self.measurement_complete}
  self.result['active_elapsed_seconds']=self.elapsed()
 def save(self,path,value):
  if value is self.result:self.stamp()
  atomic(path,value)
 def __enter__(self):
  self.save(self.folder/'checkpoint.json',self.result);return self
 def __exit__(self,*exc):
  self.stamp(closed=True);atomic(self.folder/'checkpoint.json',self.result)
  if self.result.get('complete') and exc[0] is None:
   if self.result.get('within_elapsed_budget') and self.elapsed()>self.limit:
    self.result['within_elapsed_budget']=False;self.result['delivered']=False;self.result['outcome']='REJECTED_OR_DEFERRED'
    self.result['failure_category']=__import__('study_analysis').category(self.result)
   atomic(self.folder/'checkpoint.json',self.result);atomic(self.folder/'result.json',self.result)


def run(project,*,provider='auto',mode='auto',max_seconds=480,adaptive=True,base=BASE,run_id=None,inject_interruption=False,invoke=None,eligibility=None,native_effort=None,queued_unix=None,context_profile='auto',reference=None,execution_started_unix=None,prior_active_seconds=None):
 invocation_started=time.monotonic()
 from urace.work_policy import choose,execution_mode
 from study_analysis import compact_packet,context_choice,category
 if context_profile not in ('auto','full','compact'):raise ValueError('Invalid context profile')
 import spec_trial
 from source_integrity import matches
 if execution_started_unix is not None and (type(execution_started_unix) not in (int,float) or not 0<execution_started_unix<=time.time()):raise ValueError('Invalid execution start time')
 if queued_unix is not None and (type(queued_unix) not in (int,float) or not 0<queued_unix<=time.time()):raise ValueError('Invalid original queued time')
 if native_effort is not None and native_effort not in ('low','medium','high'):raise ValueError('Invalid experimental native effort')
 project=Path(project).resolve();manifest=declaration(project);root=state_root(project,base);root.mkdir(parents=True,exist_ok=True)
 from urace.implementation_sequence import local_only
 if local_only(manifest):return {'status':'LOCAL_CONTROLLER_ONLY','complete':False,'validated':False,'native_receipts':[],'tokens':0,'reason':'Declared orchestration must use a registered local handler; native execution refused'}
 if provider not in ('auto','codex','claude') or type(max_seconds) is not int or not 60<=max_seconds<=960:raise ValueError('Invalid work resource policy')
 with (root/'work.guard').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if run_id is not None and (not isinstance(run_id,str) or not run_id.replace('-','').isalnum()):raise ValueError('Invalid work run identity')
  from urace import cli as core_cli,_common as core_common
  recovery_config={'state_path':str(root/'core-state.json')}
  if core_common.transaction_path(recovery_config).exists():core_cli.reconcile_transaction(recovery_config,root=project)
  identifier=run_id or uuid.uuid4().hex;folder=root/'runs'/identifier;folder.mkdir(parents=True,exist_ok=True)
  saved=load(folder/'result.json')
  if saved and saved.get('complete'):
   if saved.get('contract')!=contract(manifest['family'],manifest['phase']) or saved.get('declaration_sha256')!=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest():raise RuntimeError('Completed run belongs to earlier requirements; start a new run')
   return saved
  checkpoint=load(folder/'checkpoint.json');workspace=folder/'workspace';family=manifest['family'];phase=manifest['phase'];signature=contract(family,phase)
  if checkpoint and checkpoint['contract']!=signature:raise RuntimeError('Requirements changed during a run; preserve old run and start a new one')
  result=checkpoint or {'id':identifier,'product_id':manifest['product_id'],'product':str(project),'trial_id':load(Path(base)/'trial-clock.json',{}).get('trial_id'),'queued_unix':queued_unix if queued_unix is not None else time.time(),'phase_started_unix':time.time(),'contract':signature,'family':family,'phase':phase,'native_receipts':[],'attempts':[],'interventions':[],'complete':False,'validated':False,'publication':'PENDING','timing':{'baseline_seconds':0,'acceptance_seconds':0}}
  if result.get('status')=='AWAITING_OWNER_CLARIFICATION' and result.get('waiting_answer_sha256')==capability_digest(owner_clarifications(project,base)):
   return result
  if result.get('status')=='AWAITING_OWNER_CLARIFICATION':
   result.setdefault('interventions',[]).append({'kind':'OWNER_CLARIFICATION','at':datetime.now(timezone.utc).isoformat(),'answer_sha256':capability_digest(owner_clarifications(project,base)),'human_seconds':None,'previous_question_ids':[q.get('id') for q in result.get('clarification_requests',[])]})
   result['clarification_requests']=[];result['context_clarification_status']='RESOLVED_BY_OWNER_INPUT'
  # Legacy explicit start timestamps remain conservative; new study phases pass measured prior active seconds.
  prior=prior_active_seconds if prior_active_seconds is not None else max(0,time.time()-execution_started_unix) if execution_started_unix is not None else 0
  result.setdefault('execution_started_unix',execution_started_unix)
  with ActiveBudget(result,folder,prior,invocation_started,max_seconds) as budget:
   declaration_sha=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
   if result.get('declaration_sha256',declaration_sha)!=declaration_sha:raise RuntimeError('Owner declaration changed; previous result preserved')
   if result.get('requested_context_profile',context_profile)!=context_profile:raise RuntimeError('Context experiment changed during a run')
   result.setdefault('execution_started_unix',execution_started_unix)
   if result.get('execution_started_unix') is None and result.get('native_receipts'):
    starts=[datetime.fromisoformat(r['at']).timestamp() for r in result['native_receipts'] if r.get('at')];result['execution_started_unix']=min(starts) if starts else result['queued_unix']
   result['requested_context_profile']=context_profile
   result.update(artifact_directory=str(folder),candidate_workspace=str(workspace))
   result['declaration_sha256']=declaration_sha
   result['mode']=execution_mode(mode,requirements=manifest['requirements'],continuity=family in ('requirements_change','interruption'))
   from urace import _common
   state=load(root/'core-state.json',{})
   if not result.get('core'):
    versions=sorted((root/'versions').glob('v*/metadata.json'));last=load(versions[-1],{}) if versions else {}
    hashes=last.get('source_sha256',{})
    trusted=isinstance(hashes,dict) and set(hashes)==set(manifest['allowed_files']) and last.get('contract')==signature and all(confined(project,n).exists() and hashlib.sha256(confined(project,n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    if not trusted:
     for objective in state.get('objectives',[]):
      if objective.get('status')=='completed':objective['status']='planned'
   if result['mode']=='standalone':prepared=None
   else:
    if result.get('core'):
     core=result['core'];prepared=(core['config'],core['goal'],core['decision'],core['state'])
    else:
     try:prepared=(*_authority(manifest,state),state)
     except RuntimeError as error:
      if str(error).startswith('No declared useful work'):return {'id':identifier,'status':'NO_DECLARED_WORK','complete':True,'validated':False,'native_receipts':[]}
      raise
     result['core']=dict(zip(['config','goal','decision','state'],prepared))
   before=result.get('before') or {n:confined(project,n).read_text() for n in manifest['allowed_files']};result['before']=before
   if not workspace.exists():
    workspace.mkdir()
    for n,text in before.items():(workspace/n).write_text(text)
    (workspace/'PROJECT.md').write_text(brief(family,phase))
    budget.save(folder/'sealed-acceptance.json',cases(family,False,phase))
    (folder/'development.py').write_text(public_script(cases(family,True,phase)))
    (workspace/'PUBLIC_CHECKS.py').write_text(public_script(cases(family,True,phase)))
   from qualification_protocol import digest as seal_digest
   from output_quality import cases as robustness_cases, RUNNER as quality_runner
   acceptance_descriptor={'functional':cases(family,False,phase),'robustness':robustness_cases(family,phase),'runner':quality_runner}
   seal_path=folder/'acceptance-seal.json'
   expected_seal={'sha256':seal_digest(acceptance_descriptor),'functional_sha256':seal_digest(cases(family,False,phase))}
   if seal_path.exists() and load(seal_path)!=expected_seal:raise RuntimeError('Sealed acceptance changed; original evidence retained')
   if seal_digest(load(folder/'sealed-acceptance.json'))!=expected_seal['functional_sha256']:raise RuntimeError('Sealed functional acceptance changed')
   if not seal_path.exists():
    if result.get('attempts'):raise RuntimeError('Missing pre-execution acceptance seal; legacy run cannot be relabeled')
    budget.save(seal_path,expected_seal)
   result['acceptance_seal']=expected_seal
   if reference is not None:
    from downstream_study import prepare_reference
    prepared_reference=prepare_reference(workspace,reference)
    if result.get('specification_reference',prepared_reference)!=prepared_reference:raise RuntimeError('Specification reference changed during a run')
    result['specification_reference']=prepared_reference
   result.setdefault('timing',{})['preparation_seconds']=result.get('timing',{}).get('preparation_seconds',0)+time.monotonic()-invocation_started
   if invoke is None:
    from native_agents import run as invoke
   eligibility=eligibility or spec_trial.eligible
   deadline=time.monotonic()+max(0,max_seconds-budget.elapsed())
   public_ok=result.get('development_passed',False);generation_seconds=sum(r.get('wall_seconds',0) for r in result['native_receipts'])
   # Resume validation without paying for a second generation after controller interruption.
   for index in range(len(result['attempts']),1 if result['mode']=='standalone' else 3):
    if public_ok:break
    if time.monotonic()>=deadline-60 or generation_seconds>=max_seconds-60:break
    admission_started=time.monotonic()
    controls=effective(base);pins=load(Path(base)/'harness-manifest.json',{})
    if not pins or any(not matches(Path(base)/n,v) for n,v in pins.items()):raise RuntimeError('Project work source integrity mismatch')
    if controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals'] or time.time()>=load(Path(base)/'trial-clock.json',{}).get('ends_unix',0):result['status']='DEFERRED_BY_OWNER_OR_EXPIRY';break
    available,waits=eligibility();available=[p for p in available if controls['executors'][p]['enabled']]
    preferred=provider if provider!='auto' else next(iter(available),None)
    if result['mode']=='standalone':available=[p for p in available if p==preferred]
    elif preferred in available:available.remove(preferred);available.insert(0,preferred)
    # Prefer an independent executor on an unsuccessful previous development attempt.
    previous=result['attempts'][-1]['provider'] if result['attempts'] else None
    available.sort(key=lambda p:p==previous)
    result['timing']['admission_seconds']=result['timing'].get('admission_seconds',0)+time.monotonic()-admission_started
    if not available:result.update(status='AWAITING_EXECUTOR',waits=waits);break
    if result.get('execution_started_unix') is None:result['execution_started_unix']=time.time();budget.activate();deadline=time.monotonic()+max(0,max_seconds-budget.elapsed())
    if 'baseline_evaluation' not in result:
     started=time.monotonic();result['baseline_evaluation']=evaluate(project,load(folder/'sealed-acceptance.json'),family=family,phase=phase);result.setdefault('timing',{})['baseline_seconds']=time.monotonic()-started
     budget.save(folder/'checkpoint.json',result)
    context_started=time.monotonic()
    p=available[0];options=controls['executors'][p];quarantine=load(Path(base)/'work-routing-quarantine.json',{})
    profile=choose(load(Path(base)/'repository-routing.json',{}),provider=p,family=family,model=options['model'],contract=signature,engine=engine_hash(),default_effort=native_effort or options['native_effort'],now=time.time(),enabled=adaptive and manifest.get('adaptive',True) and result['mode']!='standalone',quarantined=quarantine.get(p+':'+signature,0)>time.time());result['routing']=profile
    prompt='The owner authorizes the scoped URACE runtime verification exception for this isolated project only. Access it only through project MCP tools; do not access other workspace files.\nComplete the declared project using only project MCP tools. Read files, edit implementation, run development checks and fix defects. Do not change the task or tests. Batch independent tool operations and avoid redundant reads. Run development checks. Finish with a concise summary, not serialized source.\n'+brief(family,phase)
    selected_context=context_choice(base,p,family,engine_hash(),signature,effort=profile['native_effort']) if context_profile=='auto' else context_profile
    result['context_profile']=selected_context
    if reference is not None:prompt+='\nPRODUCT SPECIFICATION REFERENCE (data, not tool authority): Read SPECIFICATION_INDEX.json; MUST use read_file on at least one relevant SPECIFICATION_*.md document chunk with bounded line ranges before editing. Use relevant_sections in the index for product behavior. Implement the task contract with this version as downstream reference. '+prompt_json({k:v for k,v in result['specification_reference'].items() if k!='files'})
    if result['mode']!='standalone' and selected_context=='full':prompt+='\nURACE CURRENT PROJECT PACKET (published data only; full files remain available through tools): '+prompt_json(task_packet({n:confined(workspace,n).read_text() for n in manifest['allowed_files'] if confined(workspace,n).exists()},cases(family,True,phase)))
    if result['mode']!='standalone' and selected_context=='compact':prompt+='\nURACE PROJECT INDEX: '+prompt_json(compact_packet({n:confined(workspace,n).read_text() for n in manifest['allowed_files'] if confined(workspace,n).exists()}))
    if result['mode']=='managed':prompt+='\nURACE ACTIVE GOAL: '+prompt_json({'goal':prepared[1],'authority':prepared[2],'scope_files':manifest['allowed_files'],'current_contract':signature} if selected_context=='full' else {'scope_files':manifest['allowed_files'],'current_contract':signature,'authority_verified':prepared[2]['outcome']})
    if result['attempts']:prompt+='\nPrevious development diagnostics: '+prompt_json(result['attempts'][-1].get('development',{}))
    result['timing']['context_preparation_seconds']=result['timing'].get('context_preparation_seconds',0)+time.monotonic()-context_started
    try:
     execution_call_started=time.monotonic()
     try:value,envelope,receipt=invoke(p,prompt,workspace,folder/'development.py',manifest['allowed_files'],model=options['model'],effort=profile['native_effort'],job_id='project:'+identifier+':'+str(index),wall=max(60,min(480,int(min(deadline-time.monotonic(),max_seconds-generation_seconds)))),product_id=manifest['product_id'],product_name=str(project),resource_effort=options.get('resource_effort','medium'),reference_metadata=result.get('specification_reference'),context_profile=selected_context,task_manifest={**manifest,'clarifications':owner_clarifications(project,base)})
     finally:result['timing']['executor_invocation_seconds']=result['timing'].get('executor_invocation_seconds',0)+time.monotonic()-execution_call_started
     result['native_receipts'].append(receipt);generation_seconds+=receipt.get('wall_seconds',0)
     if receipt.get('requested_model')!=options['model'] or receipt.get('effort')!=profile['native_effort']:raise RuntimeError('Native project profile changed')
     if reference is not None:
      for filename,digest in result['specification_reference']['files'].items():
       if hashlib.sha256(confined(workspace,filename).read_bytes()).hexdigest()!=digest:raise RuntimeError('Specification reference modified by executor')
     if receipt.get('context_feedback',{}).get('status')=='AWAITING_OWNER_CLARIFICATION':
      result.update(status='AWAITING_OWNER_CLARIFICATION',clarification_requests=receipt['context_feedback']['unresolved_questions'],waiting_answer_sha256=capability_digest(owner_clarifications(project,base)))
      result['attempts'].append({'index':index,'provider':p,'status':'AWAITING_OWNER_CLARIFICATION','development':{'returncode':1,'stderr':'Owner clarification required; no automatic repair while waiting'},'profile':profile})
      result['tokens']=sum(r['tokens'] for r in result['native_receipts']) if all(type(r.get('tokens')) is int for r in result['native_receipts']) else None
      result['elapsed_seconds']=time.time()-result['queued_unix'];budget.save(folder/'result.json',result);budget.save(folder/'checkpoint.json',result);return result
     if receipt.get('failure'):development={'returncode':1,'stderr':receipt['failure']}
     else:development=container(workspace,['/public_checks.py'],checks=folder/'development.py')
    except Exception as error:development={'returncode':1,'stderr':type(error).__name__+': '+str(error)[:1000]}
    if profile.get('adaptive') and development['returncode']!=0 and not any(r.get('failure') for r in result['native_receipts'][-1:]):
     quarantine=load(Path(base)/'work-routing-quarantine.json',{});quarantine[p+':'+signature]=time.time()+86400;budget.save(Path(base)/'work-routing-quarantine.json',quarantine)
    public_ok=development['returncode']==0
    if public_ok:
     for filename in manifest['allowed_files']:_common.atomic_write_text(confined(workspace,filename),confined(workspace,filename).read_text())
    attempt_directory=folder/'attempts'/str(index);attempt_directory.mkdir(parents=True,exist_ok=True)
    for filename in manifest['allowed_files']:
     candidate=confined(workspace,filename)
     if candidate.exists():_common.atomic_write_text(attempt_directory/filename,candidate.read_text())
    result['development_passed']=public_ok;result['attempts'].append({'index':index,'provider':p,'development':development,'profile':profile,'source_snapshot':str(attempt_directory)});budget.save(folder/'checkpoint.json',result)
   if not public_ok and time.monotonic()>=deadline-60:result.update(complete=True,status='ELAPSED_BUDGET_EXHAUSTED')
   if public_ok:
    if inject_interruption and not result.get('interruption_injected'):
     result.update(interruption_injected=True,status='SIMULATED_CONTROLLER_INTERRUPTION');budget.save(folder/'checkpoint.json',result);return result
    sealed=folder/'sealed-delivery';sealed.mkdir(exist_ok=True)
    for filename in manifest['allowed_files']:shutil.copyfile(confined(workspace,filename),sealed/filename)
    started=time.monotonic();result['acceptance']=evaluate(sealed,load(folder/'sealed-acceptance.json'),family=family,phase=phase,baseline=result['baseline_evaluation']);result.setdefault('timing',{})['acceptance_seconds']=time.monotonic()-started;result['validated']=result['acceptance']['validated'] and result['acceptance'].get('quality',{}).get('gate_passed') is True;result['complete']=True;result['status']='VALIDATED' if result['validated'] else 'REJECTED_BY_QUALITY' if result['acceptance']['validated'] else 'REJECTED_BY_ACCEPTANCE'
    if result['routing'].get('adaptive') and not result['validated']:
     quarantine=load(Path(base)/'work-routing-quarantine.json',{});quarantine[result['routing']['provider']+':'+signature]=time.time()+86400;budget.save(Path(base)/'work-routing-quarantine.json',quarantine)
    result['tokens']=sum(r['tokens'] for r in result['native_receipts']) if result['native_receipts'] and all(type(r.get('tokens')) is int for r in result['native_receipts']) else None
    current=effective(base)
    if hashlib.sha256(json.dumps(declaration(project),sort_keys=True).encode()).hexdigest()!=result['declaration_sha256']:raise RuntimeError('Owner declaration changed before publication')
    result['within_elapsed_budget']=budget.elapsed()<=max_seconds
    if not result['within_elapsed_budget']:result['publication']='RESOURCE_BOUND_EXCEEDED'
    result['timing']['publication_seconds']=0
    if result['validated'] and result['within_elapsed_budget'] and result['mode']!='standalone' and not current['paused'] and current['executor_enabled'] and current['auto_goals']:
     result['timing']['publication_seconds']=None
     publication_started=time.monotonic()
     try:_publish(project,root,sealed,manifest,prepared,result,before)
     finally:result['timing']['publication_seconds']=time.monotonic()-publication_started
    elif not result['validated']:result['publication']='REJECTED'
   elif result['attempts'] and result.get('status') not in ('AWAITING_EXECUTOR','DEFERRED_BY_OWNER_OR_EXPIRY'):result.update(complete=True,status='DEVELOPMENT_FAILED')
   if result.get('complete') and result.get('attempts') and 'acceptance' not in result:
    started=time.monotonic()
    result['acceptance']=evaluate(workspace,load(folder/'sealed-acceptance.json'),family=family,phase=phase,baseline=result.get('baseline_evaluation'))
    result['timing']['acceptance_seconds']=result['timing'].get('acceptance_seconds',0)+time.monotonic()-started
    # A failed public delivery remains failed even if a subset of private checks passes.
   result['delivered']=result['validated'] and result.get('within_elapsed_budget',False) and (result['mode']=='standalone' or result['publication']=='ACCEPTED')
   receipts=result['native_receipts'];result['tokens']=sum(r['tokens'] for r in receipts) if receipts and all(type(r.get('tokens')) is int for r in receipts) else None;result['elapsed_seconds']=time.time()-result['queued_unix'];result['active_elapsed_seconds']=budget.elapsed();result['finished_at']=datetime.now(timezone.utc).isoformat();result['outcome']='VALIDATED_PROJECT_WORK' if result['delivered'] else 'REJECTED_OR_DEFERRED';result['failure_category']=category(result);budget.save(folder/'result.json',result);budget.save(folder/'checkpoint.json',result)
   return result


def owner_clarifications(project,base=BASE):
 from urace.executor_capabilities import digest
 rows=load(state_root(project,base)/'owner-clarifications.json',{})
 if not isinstance(rows,dict) or len(rows)>1000 or any(not isinstance(k,str) or not isinstance(v,str) or not 1<=len(v.encode())<=8192 for k,v in rows.items()):raise ValueError('Invalid owner clarification ledger')
 return rows

def clarify(project,requirement_id,answer,base=BASE):
 project=Path(project).resolve();manifest=declaration(project)
 if requirement_id not in {r.get('id') for r in manifest['requirements']} or not isinstance(answer,str) or not 1<=len(answer.encode())<=8192:raise ValueError('Existing requirement and bounded owner clarification required')
 root=state_root(project,base);root.mkdir(parents=True,exist_ok=True)
 with (root/'work.guard').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);rows=owner_clarifications(project,base);rows[requirement_id]=answer;atomic(root/'owner-clarifications.json',rows)
 return {'status':'OWNER_CLARIFICATION_RECORDED','requirement_id':requirement_id,'acceptance_changed':False,'comparison_scope':'Externally clarified jobs are separate from unassisted frozen ordinary cohorts'}
