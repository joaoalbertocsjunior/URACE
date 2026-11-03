"""One supervisor's version-bound downstream and context-ablation lanes."""
from pathlib import Path
import json,hashlib,time,re,fcntl
from common import BASE,atomic
import project_work as work
from controls import effective
from repository_tasks import FAMILIES,contract
from study_analysis import compare,category

def digest(text):return hashlib.sha256(text.encode()).hexdigest()

def prepare_reference(workspace,reference):
 text=reference['text']
 if digest(text)!=reference['sha256']:raise RuntimeError('Specification source hash mismatch')
 if len(text.encode())>3000000:raise ValueError('Specification exceeds confined project budget')
 files={};chunks=[];sections=[]
 terms={'navigation':('requirement','dependenc','project','complet'),'requirements_change':('requirement','dependenc','project','criteria'),'recovery':('transaction','recovery','rollback'),'interruption':('transaction','recovery','checkpoint'),'failover':('executor','availability','resource'),'receipts':('token','usage','receipt','resource')}.get(reference.get('family'),('purpose','authority'))
 for i,offset in enumerate(range(0,len(text),64000)):
  part=text[offset:offset+64000];name='SPECIFICATION_%03d.md'%i;p=Path(workspace)/name
  if p.exists() and p.read_text()!=part:raise RuntimeError('Immutable specification chunk changed')
  if not p.exists():p.write_text(part)
  files[name]=digest(part);headings=list(re.finditer(r'^#{1,6} .+',part,re.M));chunks.append({'file':name,'first_heading':headings[0].group() if headings else None,'heading_count':len(headings),'characters':len(part)})
  for heading in headings:
   score=sum(word in heading.group().lower() for word in terms)
   if score:
    start=part[:heading.start()].count('\n')+1;sections.append({'file':name,'heading':heading.group(),'start_line':start,'end_line':min(start+79,len(part.splitlines())),'score':score})
 index={'version':reference['version'],'full_sha256':reference['sha256'],'scope':'Complete frozen specification split losslessly into readonly tool files; task contract remains independent acceptance','chunks':chunks,'relevant_sections':sorted(sections,key=lambda x:(-x['score'],x['file'],x['start_line']))[:12]};encoded=json.dumps(index,sort_keys=True);p=Path(workspace)/'SPECIFICATION_INDEX.json'
 if p.exists() and p.read_text()!=encoded:raise RuntimeError('Immutable specification index changed')
 if not p.exists():p.write_text(encoded)
 files[p.name]=digest(encoded)
 return {'version':reference['version'],'sha256':reference['sha256'],'files':files,'delivery':'Full versioned document via scoped project tools; index and bounded line reads available','source_snapshot':reference.get('source_snapshot')}

def _snapshot(base):
 pointer=work.load(base/'active-version.json',{});path=Path(pointer.get('snapshot','/nonexistent')).resolve()
 if not path.is_relative_to((base/'versions').resolve()):return None
 baseline=path.parent/'v000000'
 if not baseline.exists():return None
 refs={}
 for label,p in [('baseline',baseline),('candidate',path)]:
  m=work.load(p/'manifest.json',{});text=(p/'URACE.md').read_text()
  if digest(text)!=m.get('sha256'):raise RuntimeError('Frozen version source integrity failure')
  if m.get('metadata_sha256') and hashlib.sha256((p/'metadata.json').read_bytes()).hexdigest()!=m['metadata_sha256']:raise RuntimeError('Frozen version metadata integrity failure')
  refs[label]={'text':text,'sha256':m['sha256'],'version':m['version'],'source_snapshot':str(p)}
 if refs['candidate']['sha256']!=pointer.get('sha256'):raise RuntimeError('Active pointer/source mismatch')
 from quality_restore import withdrawn_versions
 if refs['candidate']['version'] in withdrawn_versions(base):return None
 return refs

def plan(base,lane):
 base=Path(base);controls=effective(base);settings=work.load(base/'repository-study-settings.json',{});active=work.load(base/('downstream-'+lane+'-active.json'),{})
 models={p:{'model':v['model'],'effort':v['native_effort']} for p,v in controls['executors'].items() if v['enabled'] and (lane!='context' or p=='codex')}
 identity={'native_clients':__import__('qualification_protocol').native_clients(controls),'schema':'downstream-v2','lane':lane,'engine_sha256':work.engine_hash(),'models':models,'contracts':{f:contract(f) for f in FAMILIES},'trial_id':work.load(base/'trial-clock.json',{}).get('trial_id'),'repetitions':36 if lane=='context' else settings.get('repetitions',18),'same_active_budget_per_arm':480,'queued_latency_includes_waits':True,'arms':['full','compact'] if lane=='context' else ['baseline','candidate'],'scope':'Context ablation on fixed tasks' if lane=='context' else 'Frozen URACE.md versions, same runtime/model/tools and independent executable task acceptance'}
 refs=None
 if lane=='specification':
  # Finish the frozen comparison before selecting a newer product version.
  if active.get('identity',{}).get('engine_sha256')==identity['engine_sha256'] and active['identity'].get('models')==models:
   root=base/'downstream-studies'/active['cohort'];previous=work.load(root/'summary.json',{})
   if previous.get('status') not in ('COMPLETE','FROZEN_VERSION_WITHDRAWN'):return root,active['identity'],controls
  refs=_snapshot(base)
  if not refs:return None,identity,controls
  identity['versions']={k:{n:v for n,v in r.items() if n!='text'} for k,r in refs.items()}
 cohort=digest(json.dumps(identity,sort_keys=True))[:24];root=base/'downstream-studies'/cohort;root.mkdir(parents=True,exist_ok=True)
 if not (root/'plan.json').exists():
  if refs:
   for label,ref in refs.items():(root/(label+'.md')).write_text(ref['text'])
  atomic(root/'plan.json',identity)
 atomic(base/('downstream-'+lane+'-active.json'),{'cohort':cohort,'identity':identity});return root,identity,controls

def _status(base,root,identity):
 rows=[work.load(p) for p in root.glob('*/*/result.json')];pairs=[]
 for cell in root.iterdir():
  if not cell.is_dir():continue
  a,z=[work.load(cell/arm/'result.json',{}) for arm in identity['arms']]
  if a and z:pairs.append((a,z))
 groups={}
 for provider in identity['models']:
  for family in FAMILIES:
   ps=[(a,z) for a,z in pairs if a['provider']==provider and a['family']==family]
   eligible=[(a,z) for a,z in ps if all(r.get('actual_providers')==[provider] for r in (a,z))]
   group=compare(eligible,minimum=35);group[identity['arms'][0]]=group.pop('standalone');group[identity['arms'][1]]=group.pop('urace');groups[provider+':'+family]=group
 expected=len(identity['models'])*len(FAMILIES)*identity['repetitions']*2
 result={'cohort':root.name,'lane':identity['lane'],'plan':identity,'completed_workflows':len(rows),'matched_pairs':len(pairs),'comparisons_by_provider_and_family':groups,'status':'COMPLETE' if len(rows)==expected else 'RUNNING_OR_DEFERRED','stronger_real_user_claim_established':False,'output_quality':__import__('output_quality').summary(rows),'measurement_contract_sha256':__import__('execution_contract').measurement_fingerprint(base),'fault_attribution':{k:sum(category(r)==k for r in rows) for k in sorted({category(r) for r in rows})},'arm_labels':identity['arms'],'comparison_metric_labels':'Metrics use explicit experimental arm labels; no cross-provider token pooling'}
 if identity['lane']=='context':
  recommendations={}
  for key,g in groups.items():
   provider,family=key.split(':');ps=[(a,z) for a,z in pairs if a['provider']==provider and a['family']==family]
   from qualification_protocol import reconcile
   client=identity.get('native_clients',{}).get(provider,{})
   receipts_match=client.get('verified') is True and all(reconcile(r,base)['all_cost_known'] and reconcile(r,base)['cached_tokens_match'] and all(receipt.get('requested_model')==identity['models'][provider]['model'] and receipt.get('effort')==identity['models'][provider]['effort'] and receipt.get('client_version')==client.get('version') for receipt in r.get('native_receipts',[])) for pair in ps for r in pair)
   pending=any(not all((cell/arm/'result.json').exists() for arm in identity['arms']) for cell in root.iterdir() if cell.is_dir() and cell.name.startswith(provider+'-'+family+'-'))
   if receipts_match and not pending and len(ps)>=35 and len(ps)==g['pairs'] and g['observed_bounded_advantage'] and all(a['validated'] and z['validated'] for a,z in ps):recommendations[key]={'pairs':len(ps),'qualified':True,'quality_nonregressing':True,'contract':contract(family),'model':identity['models'][provider]['model'],'native_effort':identity['models'][provider]['effort'],'native_client_version':client['version'],'token_ratio':1+g['token_change_pct']/100,'time_ratio':1+g['elapsed_change_pct']/100}
  last=max((r['queued_unix']+r['elapsed_seconds'] for r in rows),default=0);atomic(base/'context-routing.json',{'engine_sha256':identity['engine_sha256'],'expires_unix':min(last+86400,work.load(base/'trial-clock.json',{}).get('ends_unix',0)),'recommendations':recommendations})
 atomic(root/'summary.json',result);atomic(base/('downstream-'+identity['lane']+'-latest.json'),result);return result

def status(base=BASE):return {lane:work.load(Path(base)/('downstream-'+lane+'-latest.json'),{'status':'NOT_STARTED'}) for lane in ('context','specification')}

def run_one(base=BASE,lane='specification'):
 from trial_supervisor import external_owner
 if external_owner(base):return {'status':'OWNED_BY_SINGLE_SUPERVISOR'}
 if lane not in ('context','specification'):raise ValueError('Unknown downstream lane')
 base=Path(base)
 with (base/('downstream-'+lane+'.guard')).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);settings=work.load(base/'repository-study-settings.json',{});controls=effective(base)
  if not settings.get('enabled') or controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals']:return status(base)
  if time.time()>=work.load(base/'trial-clock.json',{}).get('ends_unix',0):return {'status':'TRIAL_ENDED'}
  root,identity,controls=plan(base,lane)
  if root is None:return {'status':'NO_FROZEN_SPECIFICATION'}
  import spec_trial
  available,_=spec_trial.eligible()
  for repeat in range(identity['repetitions']):
   for fi,family in enumerate(FAMILIES):
    for provider,options in identity['models'].items():
     if provider not in available:continue
     if work.load(base/'task-contract-quarantine.json',{}).get(contract(family),{}).get('expires_unix',0)>time.time():continue
     cell=root/(provider+'-'+family+'-'+str(repeat));cell.mkdir(exist_ok=True)
     for arm in (identity['arms'] if (repeat+fi)%2==0 else list(reversed(identity['arms']))):
      directory=cell/arm;directory.mkdir(exist_ok=True)
      if (directory/'result.json').exists():continue
      project=directory/'project'
      if not project.exists():work.initialize(project,family,base)
      while True:
       reference=None
       if lane=='specification':
        ref=identity['versions'][arm];reference={**ref,'text':(root/(arm+'.md')).read_text(),'family':family}
        from quality_restore import withdrawn_versions
        if ref['version'] in withdrawn_versions(base):
         withdrawn={'status':'FROZEN_VERSION_WITHDRAWN','cohort':root.name,'lane':lane,'plan':identity,'reason':'Original results retained; select a current non-withdrawn version next turn'};atomic(root/'summary.json',withdrawn);atomic(base/('downstream-'+lane+'-latest.json'),withdrawn);return withdrawn
       from native_agents import run as native
       def invoke(p,*args,**kwargs):
        if p!=provider or kwargs['model']!=options['model']:raise RuntimeError('Experimental provider/model changed')
        return native(p,*args,**kwargs)
       manifest=work.declaration(project);phase=manifest['phase'];original=work.load(work.state_root(project,base)/'runs/phase-1/result.json',{}).get('queued_unix') if phase==2 else None
       execution_start=work.load(work.state_root(project,base)/'runs/phase-1/result.json',{}).get('execution_started_unix') if phase==2 else None
       result=work.run(project,provider=provider,mode='standalone' if lane=='specification' else 'managed',adaptive=False,base=base,run_id='phase-'+str(phase),queued_unix=original,execution_started_unix=execution_start,prior_active_seconds=work.load(work.state_root(project,base)/'runs/phase-1/result.json',{}).get('active_elapsed_seconds') if phase==2 else 0,invoke=invoke,native_effort=options['effort'],context_profile=arm if lane=='context' else 'full',reference=reference,eligibility=lambda:([provider] if provider in spec_trial.eligible()[0] else [],{}))
       if not result.get('complete'):return _status(base,root,identity)
       if family=='requirements_change' and phase==1 and result.get('delivered'):
        import shutil
        for filename in manifest['allowed_files']:shutil.copyfile(Path(result['candidate_workspace'])/filename,project/filename)
        manifest['phase']=2;manifest['requirements'][0]['success_measure']='Independent acceptance passes '+contract(family,2);atomic(project/'project-work.json',manifest);continue
       phases=[work.load(p) for p in work.state_root(project,base).glob('runs/*/result.json')];receipts={r['id']:r for row in phases for r in row.get('native_receipts',[])}
       result['native_receipts']=list(receipts.values());result['tokens']=sum(r['tokens'] for r in receipts.values()) if all(type(r.get('tokens')) is int for r in receipts.values()) else None;result['queued_unix']=min(row['queued_unix'] for row in phases);result['elapsed_seconds']=time.time()-result['queued_unix'];result['timing']={key:sum(row.get('timing',{}).get(key,0) for row in phases) for key in ('baseline_seconds','acceptance_seconds')}
       for stage in ('preparation_seconds','admission_seconds','context_preparation_seconds','executor_invocation_seconds','publication_seconds'):
        if all(stage in row.get('timing',{}) for row in phases):result['timing'][stage]=sum(row['timing'][stage] for row in phases)
       result['attempts']=[{**attempt,'phase':row.get('phase')} for row in phases for attempt in row.get('attempts',[])];result['phases']=[{key:row.get(key) for key in ('phase','id','status','phase_started_unix','execution_started_unix','finished_at','baseline_evaluation','acceptance','tokens','timing','artifact_directory','specification_reference')} for row in phases]
       result.update(__import__('study_analysis').phase_telemetry(phases))
       final={**result,'validated':result.get('delivered',False),'functional_validated':result['validated'],'actual_providers':sorted({r['provider'] for r in result['native_receipts']}),'family':family,'provider':provider,'repeat':repeat,'effort':options['effort'],'arm':arm,'experiment':lane,'model':options['model']};final['active_budget']={**final.get('active_budget',{}),'measurement_complete':all(row.get('active_budget',{}).get('measurement_complete',True) for row in phases)};final['failure_category']=category(final);atomic(directory/'result.json',final);return _status(base,root,identity)
  return _status(base,root,identity)

def step(base=BASE):
 # One thread alternates bounded work units, never another coordinating process.
 p=Path(base)/'study-lane-schedule.json';value=work.load(p,{'next':0});n=value['next'];atomic(p,{'next':(n+1)%3})
 if n==0:
  from repository_study import run_one as repository
  return repository(base)
 return run_one(base,'context' if n==1 else 'specification')
