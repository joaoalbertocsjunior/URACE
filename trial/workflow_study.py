"""Resumable, matched native-effort and URACE-assisted/direct artifact study.

Both arms receive identical tasks, public feedback and repair allowances. The
managed arm additionally uses actual core navigation, authority and acceptance.
This is a bounded engineering comparison, not adoption or market-fit evidence.
"""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,time,uuid,sys
from common import BASE,atomic
from workflow_tasks import FAMILIES,BRIEFS,cases,manifest
from executable_workflow import run as workflow
from controls import effective

def load(p,default=None):return json.loads(Path(p).read_text()) if Path(p).exists() else default

def validate_settings(settings):
 if not isinstance(settings,dict) or set(settings)!={'enabled','repetitions','efforts'} or type(settings['enabled']) is not bool:raise ValueError('Invalid study settings')
 if type(settings['repetitions']) is not int or not 1<=settings['repetitions']<=100:raise ValueError('Repetitions must be1..100')
 efforts=settings['efforts']
 if not isinstance(efforts,list) or not efforts or any(not isinstance(e,str) for e in efforts) or len(set(efforts))!=len(efforts) or set(efforts)-{'low','medium','high'}:raise ValueError('Invalid native efforts')
 return settings

def configure(base=BASE,enabled=None,repetitions=None,efforts=None):
 base=Path(base);settings=load(base/'study-settings.json',{'enabled':False,'repetitions':3,'efforts':['low','medium','high']})
 if enabled is not None:
  if type(enabled) is not bool:raise ValueError('Enabled must be boolean')
  settings['enabled']=enabled
 if repetitions is not None:
  if type(repetitions) is not int or not 1<=repetitions<=100:raise ValueError('Repetitions must be1..100 per matched cell, not a productive call cap')
  settings['repetitions']=repetitions
 if efforts is not None:
  if not efforts or len(set(efforts))!=len(efforts) or set(efforts)-{'low','medium','high'}:raise ValueError('Invalid native efforts')
  settings['efforts']=efforts
 validate_settings(settings);atomic(base/'study-settings.json',settings);return settings

def plan(base=BASE):
 base=Path(base);settings=load(base/'study-settings.json',{'enabled':False,'repetitions':3,'efforts':['low','medium','high']});controls=effective(base)
 validate_settings(settings)
 profiles={p:v['model'] for p,v in controls['executors'].items() if v['enabled']}
 identity={'trial_id':load(base/'trial-clock.json',{}).get('trial_id'),'settings':settings,'models':profiles,'workloads':{f:manifest(f) for f in FAMILIES},'arms':['direct','urace'],'repair_allowance_per_arm':1,'scope':'Matched artifact workflows; not full real-user product or market fit'}
 from execution_contract import selected_source
 core=base.parent/'runtime/urace'
 series=load(base/'version-series.json',{}).get('root')
 if series:
  version_root=(base/series).resolve()
  if not version_root.is_relative_to((base/'versions').resolve()):raise ValueError('Study source version directory escaped')
  identity['source_product']=load(version_root/'v000000/manifest.json',{})
 identity['core_engine_sha256']=hashlib.sha256(b''.join((core/n).read_bytes() for n in ('auto_goals.py','authority.py','validation.py'))).hexdigest()
 identity['workflow_protocol_sha256']=hashlib.sha256(selected_source(Path(__file__),{'_core_prepare','_core_finish','run_one'}).encode()).hexdigest()
 execution_identity={**identity,'settings':{k:v for k,v in settings.items() if k!='enabled'}}
 cohort=hashlib.sha256(json.dumps(execution_identity,sort_keys=True).encode()).hexdigest()[:24];root=base/'workflow-studies'/cohort;root.mkdir(parents=True,exist_ok=True)
 if not (root/'plan.json').exists():atomic(root/'plan.json',identity)
 return root,identity,controls

def _core_prepare(folder,family):
 sys.path.insert(0,str(BASE.parent/'runtime'));from urace import auto_goals,authority
 project={'id':'study-'+family,'intent':'Produce a validated executable companion for the declared core workflow','requirements':[{'id':'source-contract','status':'completed'},{'id':family,'title':family.replace('_',' '),'scope':'documentation','success_measure':'All independently authored acceptance cases pass','dependencies':['source-contract'],'priority':80}]}
 config={'authority':{'delegated':['objectives','local implementation changes'],'reserved':['publish externally','spend money']},'project':project,'executor':{'allowed_files_by_scope':{'documentation':['solution.py']}}}
 state={};goal=auto_goals.select(config,state)
 if goal is None:raise RuntimeError('Core did not select declared work')
 decision=authority.resolve(goal,config,state)
 if decision['outcome']!=authority.AUTONOMOUSLY_AUTHORIZED:raise RuntimeError('Core authority denied comparison work')
 atomic(folder/'core-before.json',{'configuration':config,'state':state,'goal':goal,'authority':decision});return config,state,goal,decision

def _core_finish(folder,prepared,result):
 from urace import validation
 config,state,goal,decision=prepared;operation={'id':folder.name,'scope':'documentation','changed_files':['solution.py'],'authority_basis':decision['basis']}
 quality=(result.get('grade') or {}).get('quality_score',0)/100
 checked=validation.validate_operation(folder,operation,{'quality':0},{'quality':quality},config,state)
 accepted=checked['verdict']==validation.VALIDATED and bool((result.get('grade') or {}).get('validated_delivery'))
 operation.update(status='ACCEPTED' if accepted else 'REJECTED',independent_validation=checked,native_receipt_ids=result.get('native_receipt_ids',[]),user_value_proven=False)
 goal['status']='completed' if accepted else 'awaiting_validation';state['operations']=[operation]
 atomic(folder/'core-after.json',state)
 if accepted:
  data=(folder/'solution.py').read_bytes();snapshot=folder/'versions/v000001';snapshot.mkdir(parents=True,exist_ok=True);(snapshot/'solution.py').write_bytes(data)
  atomic(snapshot/'metadata.json',{'version':1,'sha256':hashlib.sha256(data).hexdigest(),'goal':goal,'authority':decision,'validation':checked,'resources':{'tokens':result.get('tokens'),'seconds':result.get('end_to_end_seconds')},'first_pass':result.get('first_pass'),'repairs':result.get('repairs'),'scope':'Controlled engineering comparison; not real-user benefit'})
 return accepted

def run_one(base=BASE):
 from trial_supervisor import external_owner
 if external_owner(base):return {'status':'OWNED_BY_SINGLE_SUPERVISOR'}
 import spec_trial as native
 from source_integrity import matches
 base=Path(base)
 with (base/'workflow-study.guard').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  root,identity,controls=plan(base)
  if not identity['settings']['enabled']:return {'status':'DISABLED'}
  if time.time()>=load(base/'trial-clock.json',{}).get('ends_unix',0):return {**status(base),'status':'TRIAL_ENDED'}
  if controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals']:return {'status':'PAUSED_BY_OPERATOR'}
  pins=load(base/'harness-manifest.json',{})
  if not pins:raise RuntimeError('Study requires a qualified source manifest')
  if any(not matches(base/name,value) for name,value in pins.items()):return {'status':'SOURCE_INTEGRITY_FAILURE','completed_workflows':0}
  available,waits=native.eligible()
  for repeat in range(identity['settings']['repetitions']):
   for family in FAMILIES:
    efforts=identity['settings']['efforts'];offset=(repeat+FAMILIES.index(family))%len(efforts)
    for effort in efforts[offset:]+efforts[:offset]:
     for provider in identity['models']:
      cell=root/(provider+'-'+effort+'-'+family+'-'+str(repeat));cell.mkdir(exist_ok=True)
      arms=['direct','urace'] if (repeat+FAMILIES.index(family))%2==0 else ['urace','direct']
      pending=[a for a in arms if not load(cell/a/'result.json',{}).get('complete')]
      if not pending or provider not in available:continue
      for arm in pending:
       arm_root=cell/arm;arm_root.mkdir(exist_ok=True);history=load(arm_root/'history.json',[])
       folder=arm_root/'runs'/('%06d-'%len(history)+uuid.uuid4().hex[:12]);folder.mkdir(parents=True,exist_ok=False)
       atomic(folder/'sealed-cases.json',{'manifest':identity['workloads'][family],'public':cases(family,True),'held_out':cases(family)})
       profile={'model':identity['models'][provider],'native_effort':effort}
       def admit():
        if time.time()>=load(base/'trial-clock.json',{}).get('ends_unix',0):raise RuntimeError('Trial ended before native admission')
        current=effective(base);eligible,reasons=native.eligible()
        if not load(base/'study-settings.json',{}).get('enabled') or current['paused'] or not current['executor_enabled'] or not current['auto_goals'] or provider not in eligible or not current['executors'][provider]['enabled'] or current['executors'][provider]['model']!=profile['model']:raise RuntimeError('Study deferred by current controls/capacity: '+str(reasons))
        if any(not matches(base/name,value) for name,value in pins.items()):raise RuntimeError('Study source integrity changed')
       def invoke(p,prompt,d,label):return native.native(p,prompt,d,label,profile_override=profile,job_id='study:'+root.name+':'+cell.name+':'+arm+':'+folder.name+':'+label)
       started=time.monotonic()
       prepared=_core_prepare(folder,family) if arm=='urace' else None
       task='Implement a Python3 pure standard-library module. Return serialized JSON {"python_source":"complete source"}. No tools, I/O, introspection, classes or decorators. Allowed imports: math, collections, functools, itertools, heapq, typing, __future__.\nDECLARED PROJECT REQUIREMENT:\n'+BRIEFS[family]
       try:result=workflow(provider,task,folder,cases(family),invoke,admit,profile,training=cases(family,True))
       except Exception as error:result={'grade':None,'status':'DEFERRED','error':type(error).__name__+': '+str(error),'native_receipts':[]}
       result.update(artifact_directory=str(folder),provider=provider,native_effort=effort,model=profile['model'],family=family,arm=arm,repeat=repeat,complete=result.get('grade') is not None,cohort=root.name,comparison_scope=identity['scope'],wall_seconds=time.monotonic()-started)
       if prepared and result.get('grade') is not None:
        current=effective(base)
        if current['paused'] or not current['executor_enabled'] or not current['auto_goals'] or not load(base/'study-settings.json',{}).get('enabled'):
         result['core_accepted']=False;result['publication_deferred_by_owner']=True
        else:result['core_accepted']=_core_finish(folder,prepared,result)
       result['wall_seconds']=time.monotonic()-started;result['core_overhead_seconds']=max(0,result['wall_seconds']-result.get('end_to_end_seconds',result['wall_seconds']))
       result['started_at']=datetime.fromtimestamp(time.time()-result['wall_seconds'],timezone.utc).isoformat();result['finished_at']=datetime.now(timezone.utc).isoformat();result['human_intervention_seconds']=None
       history.append(result);atomic(arm_root/'history.json',history);atomic(arm_root/'result.json',result)
       if not result['complete']:return status(base)
      return status(base)
  return status(base)

def status(base=BASE):
 base=Path(base)
 if not (base/'study-settings.json').exists():return {'status':'NOT_CONFIGURED','scope':'No controlled comparison configured'}
 root,identity,controls=plan(base);rows=[load(p) for p in root.glob('*/*/result.json')];complete=[r for r in rows if r.get('complete')]
 histories=[attempt for p in root.glob('*/*/history.json') for attempt in load(p,[])]
 receipts={receipt['id']:receipt for attempt in histories for receipt in attempt.get('native_receipts',[]) if receipt.get('id')}
 # A controller crash after a durable native receipt must not erase its cost.
 orphaned=[]
 for path in root.glob('*/*/runs/*/*-native.json'):
  receipt=load(path,{})
  if receipt.get('id') and receipt['id'] not in receipts:orphaned.append(str(path));receipts[receipt['id']]=receipt
 pairs=[];groups={}
 for cell in root.iterdir():
  if not cell.is_dir():continue
  a,b=load(cell/'direct/result.json',{}),load(cell/'urace/result.json',{})
  if a.get('complete') and b.get('complete'):
   pairs.append({'provider':a['provider'],'effort':a['native_effort'],'family':a['family'],'direct_valid':a['grade']['validated_delivery'],'urace_valid':b['grade']['validated_delivery'],'quality_delta_pp':b['grade']['quality_score']-a['grade']['quality_score'],'known_token_delta':b['tokens']-a['tokens'] if a.get('tokens') is not None and b.get('tokens') is not None else None,'seconds_delta':b['wall_seconds']-a['wall_seconds']})
 for provider in identity['models']:
  groups[provider]={}
  for effort in identity['settings']['efforts']:
   rs=[r for r in complete if r['provider']==provider and r['native_effort']==effort]
   attempts=[r for r in histories if r['provider']==provider and r['native_effort']==effort]
   group_receipts={r['id']:r for attempt in attempts for r in attempt.get('native_receipts',[]) if r.get('id')}
   recovered=[load(Path(path)) for path in orphaned if load(Path(path)).get('provider')==provider and load(Path(path)).get('effort')==effort]
   for receipt in recovered:group_receipts[receipt['id']]=receipt
   known=bool(rs) and all(r.get('tokens') is not None for r in attempts) and all(type(r.get('tokens')) is int and r['tokens']>=0 for r in group_receipts.values())
   groups[provider][effort]={'samples':len(rs),'validated':sum(r['grade']['validated_delivery'] for r in rs),'first_pass_public_successes':sum(bool(r.get('first_pass',{}).get('public_passed')) for r in rs),'repair_calls':sum(r.get('repairs',0) for r in rs),'known_tokens':sum(r.get('tokens') or 0 for r in group_receipts.values()),'usage_complete':known,'known_seconds':sum(r.get('wall_seconds') or 0 for r in attempts),'uncheckpointed_receipts':len(recovered),'timing_complete':bool(rs) and not recovered,'uncheckpointed_native_seconds':sum(r.get('wall_seconds') or 0 for r in recovered)}
 # Recommendations are scoped to these task families; no global/native defaults are changed.
 recommendations=[]
 for provider,efforts in groups.items():
  baseline=efforts.get('medium',{})
  for effort,candidate in efforts.items():
   n=candidate['samples']
   baseline_keys={(r['family'],r['repeat'],r['arm']) for r in complete if r['provider']==provider and r['native_effort']=='medium'}
   candidate_keys={(r['family'],r['repeat'],r['arm']) for r in complete if r['provider']==provider and r['native_effort']==effort}
   baseline_attempt_keys={(r['family'],r['repeat'],r['arm']) for r in histories if r['provider']==provider and r['native_effort']=='medium'}
   candidate_attempt_keys={(r['family'],r['repeat'],r['arm']) for r in histories if r['provider']==provider and r['native_effort']==effort}
   if baseline_keys!=candidate_keys or baseline_attempt_keys!=baseline_keys or candidate_attempt_keys!=candidate_keys or {key[0] for key in candidate_keys}!=set(FAMILIES):continue
   if orphaned:continue
   if effort=='medium' or n<30 or baseline.get('samples')!=n or candidate['validated']!=n or baseline.get('validated')!=n or not candidate['usage_complete'] or not baseline.get('usage_complete'):continue
   if n/(n+3.841458820694124)<.9:continue
   faster=candidate['known_seconds']<=baseline['known_seconds']*.8;cheaper=candidate['known_tokens']<=baseline['known_tokens']*.8
   noninfer=candidate['known_tokens']<=baseline['known_tokens']*1.05 and candidate['known_seconds']<=baseline['known_seconds']*1.05
   if (faster or cheaper) and noninfer:recommendations.append({'provider':provider,'native_effort':effort,'scope':'These measured task families only','samples':n,'reason':'Observed nonregressing quality with >=20% resource/time gain and <=5% loss on the other resource','delivery_wilson95_lower':n/(n+3.841458820694124),'statistical_superiority_proven':False})
 from execution_contract import selected_source
 result={'analysis_sha256':hashlib.sha256(selected_source(Path(__file__),{'status'}).encode()).hexdigest(),'cohort':root.name,'status':'DISABLED' if not identity['settings']['enabled'] else 'COMPLETE' if len(complete)==len(identity['models'])*len(identity['settings']['efforts'])*len(FAMILIES)*identity['settings']['repetitions']*2 else 'RUNNING_OR_DEFERRED','plan':identity,'completed_workflows':len(complete),'matched_pairs':pairs,'providers':groups,'unique_native_calls':len(receipts),'known_tokens_including_deferred':sum(r.get('tokens') or 0 for r in receipts.values()),'missing_usage':sum(r.get('tokens') is None for r in receipts.values()),'routing_recommendations':recommendations,'invalidated_cohorts':load(base/'study-invalidations.json',{}),'uncheckpointed_receipts':orphaned,'native_defaults_mutated':False,'real_user_value_proven':False,'scope':identity['scope']}
 atomic(root/'summary.json',result);atomic(base/'workflow-study-latest.json',result)
 atomic(base/'workflow-study-routing.json',{'cohort':root.name,'models':identity['models'],'workloads':identity['workloads'],'core_engine_sha256':identity['core_engine_sha256'],'expires_unix':min(time.time()+86400,load(base/'trial-clock.json',{}).get('ends_unix',0)),'recommendations':recommendations,'global_native_defaults_changed':False})
 return result

if __name__=='__main__':print(json.dumps(run_one(),indent=2))
