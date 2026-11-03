"""Matched, tool-enabled native-agent study with an explicit user-benefit gate."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,time,fcntl,sys
from common import BASE,atomic
from controls import effective
import project_work as work
from repository_tasks import FAMILIES,contract

def configure(base=BASE,enabled=None,repetitions=None,efforts=None):
 base=Path(base);settings=work.load(base/'repository-study-settings.json',{'enabled':False,'repetitions':18,'efforts':['low','medium','high']})
 if enabled is not None:
  if type(enabled) is not bool:raise ValueError('Enabled must be boolean')
  settings['enabled']=enabled
 if repetitions is not None:
  if type(repetitions) is not int or not 1<=repetitions<=100:raise ValueError('Repetitions must be1..100')
  settings['repetitions']=repetitions
 if efforts is not None:
  if not isinstance(efforts,list) or not efforts or len(efforts)!=len(set(efforts)) or set(efforts)-{'low','medium','high'}:raise ValueError('Invalid native efforts')
  settings['efforts']=efforts
 atomic(base/'repository-study-settings.json',settings);return settings

def plan(base=BASE):
 base=Path(base);settings=work.load(base/'repository-study-settings.json',{'enabled':False,'repetitions':18,'efforts':['low','medium','high']});controls=effective(base)
 identity={'measurement_sha256':__import__('execution_contract').measurement_fingerprint(Path(__file__).parent),'product_scope':{'primary_product':'URACE.md','baseline_commit':work.load(base/'contract.json',{}).get('baseline_commit'),'measured_treatment':'runtime orchestration infrastructure; no specification text supplied in ordinary arms','per_version_textual_gain_proven':False},'qualification_protocol':__import__('qualification_protocol').protocol(base),'native_clients':__import__('qualification_protocol').native_clients(controls),'resource_efforts':{p:r.get('resource_effort') for p,r in controls['executors'].items() if r['enabled']},'schema':'native-agent-benefit-v2','settings':{k:v for k,v in settings.items() if k!='enabled'},'models':{p:r['model'] for p,r in controls['executors'].items() if r['enabled']},'contracts':{f:contract(f) for f in FAMILIES},'phase2_contract':contract('requirements_change',2),'engine_sha256':work.engine_hash(),'trial_id':work.load(base/'trial-clock.json',{}).get('trial_id'),'arms':['standalone','urace'],'same_tools':True,'study_protocol_sha256':hashlib.sha256(__import__('execution_contract').selected_source(Path(__file__),{'run_one'}).encode()).hexdigest(),'same_active_budget_per_arm':480,'queued_latency_includes_waits':True,'scope':'Tool-enabled native coding agents on prespecified URACE workflow repositories; not market-fit or real-user adoption'}
 cohort=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24];root=base/'repository-studies'/cohort;root.mkdir(parents=True,exist_ok=True)
 if not (root/'plan.json').exists():atomic(root/'plan.json',identity)
 return root,identity,settings,controls

def _qualify(rows,identity):
 # Conservative deployment qualification; no extrapolation to other contracts.
 recommendations=[]
 for provider in identity['models']:
  for family in FAMILIES:
   if family=='requirements_change':continue
   relevant=[r for r in rows if r['provider']==provider and r['family']==family]
   baseline=[r for r in relevant if r['effort']=='medium']
   if any(not __import__('qualification_protocol').compatible(r,identity) or not __import__('qualification_protocol').reconcile(r)['all_cost_known'] or not __import__('qualification_protocol').reconcile(r)['cached_tokens_match'] for r in relevant):continue
   for effort in identity['settings']['efforts']:
    candidate=[r for r in relevant if r['effort']==effort];keys=lambda rs:{(r['repeat'],r['arm']) for r in rs}
    if effort=='medium' or any(r.get('actual_providers')!=[provider] for r in candidate+baseline) or len(candidate)<35 or keys(candidate)!=keys(baseline) or not all(r['validated'] and r.get('tokens') is not None and r.get('acceptance',{}).get('quality',{}).get('gate_passed') is True for r in candidate+baseline):continue
    t=sum(r['elapsed_seconds'] for r in candidate)/sum(r['elapsed_seconds'] for r in baseline);k=sum(r['tokens'] for r in candidate)/max(1,sum(r['tokens'] for r in baseline))
    if min(t,k)<=.8 and max(t,k)<=1.05:recommendations.append({'provider':provider,'family':family,'native_effort':effort,'samples':len(candidate),'quality_nonregressing':True,'usage_complete':True,'timing_complete':True,'time_ratio':t,'token_ratio':k,'scope':'This exact executable contract; descriptive allocation evidence, not global optimality'})
 return recommendations

def status(base=BASE):
 base=Path(base)
 if not (base/'repository-study-settings.json').exists():return {'status':'NOT_CONFIGURED'}
 root,identity,settings,controls=plan(base);rows=[work.load(p) for p in root.glob('*/*/study-result.json')];pairs=[]
 for cell in root.iterdir():
  if not cell.is_dir():continue
  a,z=[work.load(cell/arm/'study-result.json',{}) for arm in ['standalone','urace']]
  if a and z:pairs.append({'provider':a['provider'],'family':a['family'],'effort':a['effort'],'repeat':a['repeat'],'standalone_valid':a['validated'],'urace_valid':z['validated'],'validated_delivery_delta':int(z['validated'])-int(a['validated']),'elapsed_seconds_delta':z['elapsed_seconds']-a['elapsed_seconds'],'tokens_delta':z['tokens']-a['tokens'] if a.get('tokens') is not None and z.get('tokens') is not None else None})
 from urace.work_policy import outcomes
 elapsed=max(.000001,time.time()-min([r['queued_unix'] for r in rows],default=time.time()));metrics={provider+':'+effort:{arm:outcomes([r for r in rows if r['arm']==arm and r['provider']==provider and r['effort']==effort and r['family']!='failover'],elapsed) for arm in ['standalone','urace']} for provider in identity['models'] for effort in identity['settings']['efforts']}
 paired_keys={(p['provider'],p['family'],p['effort'],p['repeat']) for p in pairs}
 matched=[r for r in rows if (r['provider'],r['family'],r['effort'],r['repeat']) in paired_keys]
 matched_metrics={provider+':'+effort:{arm:outcomes([r for r in matched if r['arm']==arm and r['provider']==provider and r['effort']==effort and r['family']!='failover'],elapsed) for arm in ['standalone','urace']} for provider in identity['models'] for effort in identity['settings']['efforts']}
 qualification_progress=__import__('qualification_protocol').progress(root,identity)
 qualification=_qualify(rows,identity) if qualification_progress['status']=='READY' else [];atomic(base/'repository-routing.json',{'cohort':root.name,'models':identity['models'],'contracts':identity['contracts'],'engine_sha256':identity['engine_sha256'],'expires_unix':min(max((r['queued_unix']+r['elapsed_seconds'] for r in rows),default=0)+86400,work.load(base/'trial-clock.json',{}).get('ends_unix',0)),'recommendations':qualification})
 wins=sum(p['validated_delivery_delta']>0 for p in pairs);losses=sum(p['validated_delivery_delta']<0 for p in pairs)
 from study_analysis import assessment,quarantine_contracts
 quarantine_contracts(base,rows,identity['contracts']);analysis=assessment(rows)
 for profile,comparison in analysis['ordinary_by_profile'].items():
  if qualification_progress['profiles'].get(profile,{}).get('status')!='READY':comparison['observed_bounded_advantage']=False
 for comparison in analysis['ordinary_by_provider'].values():comparison['observed_bounded_advantage']=False;comparison['interpretation']='Provider rollup is diagnostic; advantage requires a qualified native-effort profile, never pooled efforts'
 observed=qualification_progress['status']=='READY' and bool(analysis['ordinary_by_profile']) and all(v['observed_bounded_advantage'] for v in analysis['ordinary_by_profile'].values());mixes_comparable=None
 result={'qualification_progress':qualification_progress,'cohort':root.name,'status':'DISABLED' if not settings['enabled'] else 'COMPLETE' if len(rows)==len(identity['models'])*len(FAMILIES)*len(settings['efforts'])*settings['repetitions']*2 else 'RUNNING_OR_DEFERRED','plan':identity,'completed_workflows':len(rows),'matched_pairs':pairs,'resources':metrics,'matched_resources':matched_metrics,'resource_scope':'Complete workflow windows; complete per-product billing, including pending attempts, is separately available in product resources','routing_recommendations':qualification,'output_quality':__import__('output_quality').summary(rows),'measurement_contract_sha256':__import__('execution_contract').measurement_fingerprint(base),'forecast':{'per_profile_deficits':qualification_progress['profiles'],'hours_to_full_assessment':None,'basis':'Insufficient stable per-profile throughput; time alone never qualifies'},'assessment':analysis,'downstream_studies':__import__('downstream_study').status(base),'benefit':{'observed_bounded_advantage':observed,'stronger_real_user_claim_established':False,'provider_mix_comparable':mixes_comparable,'comparability':'Ordinary efficiency is qualified separately per actual provider; injected continuity never grants efficiency success','operational_outage_wins':[p for p in pairs if p['family']=='failover' and p['urace_valid'] and not p['standalone_valid']],'outage_measurement':'Injected dispatch unavailability with real alternate-executor completion; not an observed account outage','paired_delivery_wins':wins,'paired_delivery_losses':losses,'interpretation':'Prespecified matched engineering scenarios; actual-use and independent replication still required. Unknown resources or quality regressions withhold advantage.'}}
 atomic(root/'summary.json',result);atomic(base/'repository-study-latest.json',result);return result

def run_one(base=BASE):
 from trial_supervisor import external_owner
 if external_owner(base):return {'status':'OWNED_BY_SINGLE_SUPERVISOR'}
 import spec_trial
 base=Path(base)
 with (base/'repository-study.guard').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);root,identity,settings,controls=plan(base)
  if not settings['enabled'] or controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals']:return status(base)
  if time.time()>=work.load(base/'trial-clock.json',{}).get('ends_unix',0):return {**status(base),'status':'TRIAL_ENDED'}
  eligible,waits=spec_trial.eligible()
  from qualification_protocol import cells,digest
  for provider,effort,family,repeat,cell,completed_arms in cells(root,{**identity,'settings':settings},eligible):
      if family not in FAMILIES:continue
      fi=FAMILIES.index(family)
      quarantine=work.load(base/'task-contract-quarantine.json',{}).get(contract(family),{})
      if quarantine.get('expires_unix',0)>time.time():continue
      cell=root/(provider+'-'+effort+'-'+family+'-'+str(repeat));cell.mkdir(exist_ok=True);did_work=False
      if not (cell/'pair-launch.json').exists():atomic(cell/'pair-launch.json',{'queued_unix':time.time(),'provider':provider,'effort':effort,'family':family,'repeat':repeat,'cohort_identity_sha256':digest(identity),'arm_order':['standalone','urace'] if (repeat+fi)%2==0 else ['urace','standalone']})
      for arm in (['standalone','urace'] if (repeat+fi)%2==0 else ['urace','standalone']):
       directory=cell/arm;directory.mkdir(exist_ok=True)
       if not (directory/'arm-launch.json').exists():atomic(directory/'arm-launch.json',{'queued_unix':time.time()})
       if (directory/'study-result.json').exists():continue
       did_work=True
       project=directory/'project'
       if not project.exists():work.initialize(project,family,base)
       while True:
        manifest=work.declaration(project)
        from native_agents import run as native
        # Ordinary arms keep the same provider even during outer repairs.
        # Only the separately labeled failover family permits provider switching.
        def invoke(p,prompt,workspace,checks,allowed,**kwargs):return native(p,prompt,workspace,checks,allowed,**kwargs)
        def admission():
         ready,reasons=spec_trial.eligible()
         return ([p for p in ready if p!=provider],{**reasons,provider:'SIMULATED_PROVIDER_UNAVAILABLE'}) if family=='failover' else ([p for p in ready if p==provider],reasons)
        phase=manifest['phase'];original_queued=work.load(work.state_root(project,base)/'runs/phase-1/result.json',{}).get('queued_unix') if phase==2 else work.load(directory/'arm-launch.json')['queued_unix']
        execution_start=work.load(work.state_root(project,base)/'runs/phase-1/result.json',{}).get('execution_started_unix') if phase==2 else None
        result=work.run(project,provider=provider,mode='standalone' if arm=='standalone' else 'managed',adaptive=False,base=base,run_id='phase-'+str(phase),inject_interruption=family=='interruption',invoke=invoke,native_effort=effort,context_profile='full',eligibility=admission,queued_unix=original_queued,execution_started_unix=execution_start,prior_active_seconds=work.load(work.state_root(project,base)/'runs/phase-1/result.json',{}).get('active_elapsed_seconds') if phase==2 else 0)
        if family=='failover':
         result['fault_injection']={'kind':'provider_unavailable_at_dispatch','blocked_provider':provider,'real_quota_metadata_modified':False,'simulation':True}
         if arm=='standalone' and not result['native_receipts']:
          result.update(complete=True,validated=False,delivered=False,tokens=0,status='SIMULATED_FIXED_PROVIDER_OUTAGE',elapsed_seconds=time.time()-result['queued_unix'])
        if not result.get('complete'):return status(base)
        if family=='requirements_change' and phase==1 and result.get('delivered'):
         import shutil
         original=work.state_root(project,base)/'runs/phase-1/workspace'
         for filename in manifest['allowed_files']:shutil.copyfile(original/filename,project/filename)
         manifest['phase']=2;manifest['requirements'][0]['success_measure']='Independent acceptance passes '+contract(family,2);atomic(project/'project-work.json',manifest);continue
        phase_rows=[work.load(p) for p in work.state_root(project,base).glob('runs/*/result.json')];receipt_rows=[r for row in phase_rows for r in row.get('native_receipts',[])];receipts={r['id']:r for r in receipt_rows};first=min(r['queued_unix'] for r in phase_rows)
        result['timing']={key:sum(row.get('timing',{}).get(key,0) for row in phase_rows) for key in ('baseline_seconds','acceptance_seconds')}
        for stage in ('preparation_seconds','admission_seconds','context_preparation_seconds','executor_invocation_seconds','publication_seconds'):
         values=[row.get('timing',{}).get(stage) for row in phase_rows]
         result['timing'][stage]=sum(values) if all(type(value) in (int,float) for value in values) else None
        result['attempts']=[{**attempt,'phase':row.get('phase')} for row in phase_rows for attempt in row.get('attempts',[])]
        result['phases']=[{key:row.get(key) for key in ('phase','id','status','phase_started_unix','execution_started_unix','finished_at','baseline_evaluation','acceptance','tokens','timing','artifact_directory')} for row in phase_rows]
        result.update(__import__('study_analysis').phase_telemetry(phase_rows))
        final={**result,'functional_validated':result['validated'],'validated':result.get('delivered',False),'actual_providers':sorted({r.get('provider') for r in receipts.values() if r.get('provider')}),'arm':arm,'provider':provider,'effort':effort,'repeat':repeat,'family':family,'queued_unix':first,'elapsed_seconds':time.time()-first,'native_receipts':receipt_rows,'tokens':sum(r['tokens'] for r in receipts.values()) if all(type(r.get('tokens')) is int for r in receipts.values()) else None,'comparison_scope':identity['scope'],'protocol_sha256':digest(identity['qualification_protocol']),'cohort_identity_sha256':digest(identity),'execution_conditions':{'requested_model':identity['models'][provider],'requested_effort':effort,'served_model_identity':'UNVERIFIED','active_wall_budget_seconds':480,'same_tools':True,'same_public_tests':True,'arm_order':work.load(cell/'pair-launch.json')['arm_order'],'treatment':identity['qualification_protocol']['arms'][arm],'ordinary_provider_fixed':family!='failover'}};final['active_budget']={**final.get('active_budget',{}),'measurement_complete':all(row.get('active_budget',{}).get('measurement_complete',True) for row in phase_rows)};final['resource_reconciliation']=__import__('qualification_protocol').reconcile(final,base);final['failure_category']=__import__('study_analysis').category(final);atomic(directory/'study-result.json',final)
        break
      if did_work:return status(base)
  return status(base)
if __name__=='__main__':
 sys.path.insert(0,str(BASE.parent/'runtime'));print(json.dumps(run_one(),indent=2))
