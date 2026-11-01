"""Cheap, advisory decision forecasts. Authority and acceptance remain separate."""
from __future__ import annotations
import copy,hashlib,json,math,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

SCHEMA='decision-benefit-feedback-v1'
DEFAULTS={'enabled':True,'mode':'auto','executor':'auto','cache_seconds':18900}

def settings(config):
    raw=config.get('decision_feedback',{})
    if not isinstance(raw,dict) or set(raw)-set(DEFAULTS):raise ValueError('Unknown decision feedback setting')
    result={**DEFAULTS,**raw}
    if type(result['enabled']) is not bool or result['mode'] not in ('auto','executor') or result['executor'] not in ('auto','codex','claude'):raise ValueError('Invalid decision feedback mode/executor')
    if type(result['cache_seconds']) is not int or not 60<=result['cache_seconds']<=2592000:raise ValueError('Invalid decision feedback cache interval')
    return result

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def numeric(value):return type(value) in (int,float) and math.isfinite(value)
def now():return datetime.now(timezone.utc).isoformat()

def validate_forecast(value):
    if not isinstance(value,dict) or set(value)-{'benefits','cost','risk','uncertainty','evidence_refs','bottleneck_id','recommended_action','weights','expected_score'}:raise ValueError('Invalid forecast fields')
    result=copy.deepcopy(value)
    refs=result.get('evidence_refs',[])
    if not isinstance(refs,list) or any(not isinstance(v,str) or not v or len(v)>500 for v in refs):raise ValueError('Evidence references must be bounded strings')
    benefits=result.get('benefits',[])
    if not isinstance(benefits,list) or len(benefits)>20:raise ValueError('At most 20 forecast dimensions')
    names=set()
    for item in benefits:
        if not isinstance(item,dict) or set(item)!={'metric','unit','baseline','expected','direction','target_gain'}:raise ValueError('Benefit requires metric/unit/baseline/expected/direction/target_gain')
        if not all(isinstance(item[k],str) and item[k] and len(item[k])<=100 for k in ('metric','unit')) or item['metric'] in names:raise ValueError('Unique bounded metric names/units required')
        names.add(item['metric'])
        if item['direction'] not in ('higher','lower') or not all(item[k] is None or numeric(item[k]) for k in ('baseline','expected','target_gain')) or item['target_gain'] is not None and item['target_gain']<=0:raise ValueError('Finite forecast values and positive target_gain required')
    weights=result.get('weights',{})
    if not isinstance(weights,dict) or set(weights)-names or any(not numeric(v) or v<=0 for v in weights.values()):raise ValueError('Positive owner weights must reference forecast dimensions')
    if weights and not math.isfinite(sum(weights.values())):raise ValueError('Nonfinite weight sum')
    if 'expected_score' in result and (not numeric(result['expected_score']) or not 0<=result['expected_score']<=100):raise ValueError('Explicit provisional score must be 0..100')
    if len(json.dumps(result).encode())>12288:raise ValueError('Forecast exceeds 12KiB; select relevant explicit evidence')
    for k in ('bottleneck_id','recommended_action','uncertainty'):
        if k in result and (not isinstance(result[k],str) or len(result[k])>2000):raise ValueError('Bounded text required')
    return result

def score(forecast):
    values=forecast.get('benefits',[]);weights=forecast.get('weights',{})
    if not forecast.get('evidence_refs'):return {'value':None,'reason':'Missing attributable evidence','calibrated':False}
    if values and weights and set(weights)=={v['metric'] for v in values}:
        if any(not all(numeric(item[k]) for k in ('baseline','expected','target_gain')) for item in values):return {'value':None,'reason':'Unknown forecast baseline, expected value or owner target; no imputation','calibrated':False}
        components=[]
        for item in values:
            gain=(item['expected']-item['baseline'])*(1 if item['direction']=='higher' else -1)
            components.append({'metric':item['metric'],'unit':item['unit'],'expected_gain':gain,'target_gain':item['target_gain'],'weight':weights[item['metric']],'normalized':max(-1,min(1,gain/item['target_gain']))})
        value=100*sum(c['weight']*c['normalized'] for c in components)/sum(weights.values())
        return {'value':value,'range':[-100,100],'components':components,'reason':'Owner-weighted forecast target attainment; provisional and uncalibrated','calibrated':False}
    if 'expected_score' in forecast:return {'value':forecast['expected_score'],'range':[0,100],'reason':'Explicit owner estimate; uncalibrated, not measured benefit','calibrated':False}
    return {'value':None,'reason':'No explicit score or complete owner-defined dimensions/weights','calibrated':False}

def indexes(state):
    objectives={v.get('id'):v for v in state.get('objectives',[])}
    by_id={v.get('id'):v for v in state.get('operations',[])}
    by_objective={v.get('objective_reference'):v for v in state.get('operations',[]) if v.get('objective_reference')}
    evidence={}
    for v in state.get('evidence',[]):
        key=v.get('id')
        if key in evidence and evidence[key]!=v:evidence[key]=None
        else:evidence[key]=v
    bottlenecks={v.get('id'):v for group in ('integrity_gaps','blockers','progress_observations') for v in state.get(group,[]) if v.get('id')}
    return objectives,by_id,by_objective,evidence,bottlenecks

def context(state,record,indexed=None):
    objective_id=record.get('objective_ref',record.get('objective'))
    objectives,by_id,by_objective=(indexed or indexes(state))[:3]
    return objectives.get(objective_id,{}),by_id.get(record.get('operation_ref'),by_objective.get(objective_id,{}))

def context_binding(state,record,objective):
    return digest({'objective':{k:objective.get(k) for k in ('id','title','reason','success_measure','scope','target','outcome_measure_id','project_id','project_requirement','project_source_sha256')},
                   'decision':{k:record.get(k) for k in ('id','subject','governing_intent_ref','validity_conditions')},
                   'intent':state.get('intent'),'constraints':state.get('constraints')})

def existing_prior(state,objective,indexed=None):
    ref=objective.get('metadata',{}).get('forecast_evidence_ref')
    if not ref:return None
    evidence=(indexed or indexes(state))[3].get(ref)
    matches=[evidence] if evidence and evidence.get('kind')=='executor-proposal' else []
    if len(matches)!=1:return None
    evidence=matches[0];proposal=evidence.get('proposal',{});value=proposal.get('expected_value')
    if not numeric(value) or not 0<=value<=1 or any(proposal.get(k)!=objective.get(k) for k in ('title','reason','success_measure')):return None
    return {'value':100*value,'range':[0,100],'source_ref':ref,'source_at':evidence.get('at'),'reason':'Existing executor-provided expected_value rescaled from 0..1; uncalibrated forecast, not observed benefit','calibrated':False,'estimated_cost':proposal.get('estimated_cost'),'risk':proposal.get('risk'),'reported_bottleneck':proposal.get('necessity_evidence') or proposal.get('reason')}

def view(config,state,record,indexed=None):
    if not record.get('id'):raise ValueError('Decision record requires an id')
    cfg=settings(config);objective,operation=context(state,record,indexed)
    stored=state.get('decision_forecasts',{}).get(record['id'],{})
    forecast=stored.get('forecast',{});forecast_current=not stored or stored.get('context_sha256')==context_binding(state,record,objective);prior=existing_prior(state,objective,indexed)
    action=(forecast.get('recommended_action') if forecast_current else None) or objective.get('title') or record.get('subject') or record.get('decision')
    refs=[forecast.get('bottleneck_id'),objective.get('bottleneck_id'),objective.get('gap_id'),objective.get('metadata',{}).get('bottleneck_id'),objective.get('metadata',{}).get('bottleneck_observation_ref'),record.get('bottleneck_id'),*record.get('evidence_refs',[])]
    refs=list(dict.fromkeys(r for r in refs if isinstance(r,str) and r))
    bottlenecks=(indexed or indexes(state))[4]
    candidates=[bottlenecks[ref] for ref in refs if ref in bottlenecks]
    linked=[{'id':v.get('id'),'description':v.get('description') or v.get('detail') or v.get('reason'),'resolved':bool(v.get('resolved') or v.get('resolved_at')),'observation_results':copy.deepcopy(v.get('results'))} for v in candidates]
    if objective:
        from .authority import resolve
        resolution=resolve(objective,config,state)
    else:resolution={'outcome':record.get('outcome'),'basis':record.get('basis',record.get('authority_basis'))}
    outcome=resolution['outcome'];status={'AUTONOMOUSLY_AUTHORIZED':'APPROVED','DENIED':'BLOCKED','REQUIRES_AUTHORITATIVE_DECISION':'AWAITING_APPROVAL','UNRESOLVED':'UNRESOLVED'}.get(outcome,'UNRESOLVED')
    blockers=[v for v in state.get('blockers',[]) if not v.get('resolved_at') and (v.get('id') in refs or (objective and v.get('scope')==objective.get('id')))]
    if blockers or objective.get('status') in ('blocked','policy_blocked','awaiting_operator_decision') or objective.get('drift_blocked'):status='BLOCKED'
    if record.get('provenance_status') in ('SUPERSEDED','PROVENANCE_REVISED') or record.get('provenance_revised'):status='STALE'
    authority_status=status
    if not forecast_current:status='STALE'
    if status=='APPROVED' and objective.get('status') in ('deferred','deferred_budget'):status='DEFERRED'
    if status=='APPROVED' and objective.get('status')=='completed':status='COMPLETED'
    before=operation.get('before_metrics',{});after=operation.get('after_metrics',{});observed=[]
    for expected in (forecast.get('benefits',[]) if forecast_current else []):
        metric=expected['metric'];a=before.get(metric);z=after.get(metric)
        if numeric(a) and numeric(z):observed.append({'metric':metric,'declared_unit':expected['unit'],'observed_before':a,'observed_after':z,'forecast_error':z-expected['expected'] if numeric(expected['expected']) else None,'attribution':'Observed operation metrics; unit equivalence and causal attribution need independent verification'})
    from .resource_usage import product_identity
    predicted=score(forecast) if forecast else prior or score({})
    if not forecast_current:predicted={'value':None,'reason':'Forecast belongs to an earlier intent/task contract; explicit reconfirmation required','calibrated':False}
    result={'product_id':product_identity(config),'schema':SCHEMA,'decision_id':record['id'],'enabled':cfg['enabled'],'mode':cfg['mode'],'assessment_executor':cfg['executor'],
            'executor_profile_configuration':{k:copy.deepcopy(config.get('executor',{}).get(k)) for k in ('model','effort','kind','native_options')},
            'status':status,'authority_status':authority_status,'authority_outcome':outcome,'status_basis':resolution.get('basis'),'historical_decision_outcome':record.get('outcome'),
            'execution_status':operation.get('status',objective.get('status','UNOBSERVED')),
            'detected_bottlenecks':linked,'bottleneck_status':'LINKED' if linked else 'REPORTED_UNVERIFIED' if prior and prior.get('reported_bottleneck') else 'UNKNOWN',
            'action_recommendation':action,'expected_benefits':copy.deepcopy(forecast.get('benefits',[])),
            'expected_benefit_score':predicted if cfg['enabled'] else {'value':None,'reason':'Disabled','calibrated':False},
            'forecast_id':stored.get('id'),'forecast_status':'CURRENT' if stored and forecast_current else 'STALE_CONTEXT' if stored else 'UNRECORDED','forecast_timing':stored.get('timing','UNRECORDED'),
            'existing_executor_prior':prior,'expected_benefit_description':objective.get('success_measure') or record.get('justification_summary'),'reported_bottleneck':prior.get('reported_bottleneck') if prior else None,
            'expected_cost':forecast.get('cost',{'value':prior.get('estimated_cost'),'unit':'unverified heuristic 0..1'} if prior else None),'risk':forecast.get('risk',prior.get('risk') if prior else None),'uncertainty':forecast.get('uncertainty','Uncalibrated; insufficient evidence'),
            'observed_feedback':{'operation_id':operation.get('id'),'metrics':observed,'outcome':copy.deepcopy(operation.get('outcome',{})),'benefit_verified':False},
            'additional_model_calls':0,'affects_authority_or_acceptance':False,
            'approval_scope':'Authority status only; native admission, owner pause and independent acceptance still apply',
            'limitations':'Forecasts are advisory, not acceptance or a universal worth score. Missing evidence stays unknown. Lifecycle completion is separate from realized user benefit.'}
    fingerprint=copy.deepcopy(result)
    outcome_snapshot=fingerprint['observed_feedback']['outcome']
    if isinstance(outcome_snapshot,dict):outcome_snapshot.pop('evaluated_at',None)
    result['input_sha256']=digest(fingerprint)
    advice=state.get('decision_executor_assessments',{}).get(record['id'])
    if advice:
        current=advice.get('input_sha256')==result['input_sha256']
        try:fresh=0<=(datetime.now(timezone.utc)-datetime.fromisoformat(advice['at'])).total_seconds()<=cfg['cache_seconds']
        except (KeyError,ValueError,TypeError):fresh=False
        result['executor_assessment']={**copy.deepcopy(advice),'current_and_fresh':current and fresh,'provisional':True}
    return result

def register_forecast(state,record,forecast,*,at=None):
    forecast=validate_forecast(forecast);at=at or now();objective,operation=context(state,record);binding=context_binding(state,record,objective);identifier='forecast-'+digest({'decision_id':record['id'],'forecast':forecast,'context_sha256':binding})[:24]
    existing=state.setdefault('decision_forecasts',{}).get(record['id'])
    if existing and existing.get('id')==identifier:return existing
    _,operation=context(state,record)
    timing='RETROSPECTIVE' if operation.get('attempted_at') or operation.get('accepted_at') or operation.get('status') in ('ACCEPTED','REJECTED','COMPLETED') else 'PRE_EXECUTION_UNVERIFIED_TIMESTAMP'
    item={'id':identifier,'decision_id':record['id'],'forecast':forecast,'at':at,'timing':timing,'context_sha256':binding,'source':'explicit owner input','immutable_history':True}
    state.setdefault('decision_forecast_history',[]).append(copy.deepcopy(item));state['decision_forecasts'][record['id']]=item;return item

def refresh(config,state):
    cfg=settings(config)
    if not cfg['enabled']:return {'schema':SCHEMA,'enabled':False,'additional_model_calls':0}
    latest=state.setdefault('decision_assessments',{});changed=0;indexed=indexes(state)
    # Legacy authority records may repeat an ID; evaluate its latest snapshot once.
    records={r['id']:r for r in state.get('decision_records',[]) if r.get('id')}
    for record in records.values():
        item=view(config,state,record,indexed);old=latest.get(record['id'])
        if old and old.get('input_sha256')==item['input_sha256']:
            latest[record['id']]=item;continue
        state.setdefault('decision_assessment_history',[]).append(copy.deepcopy(item));latest[record['id']]=item;changed+=1
    return {'schema':SCHEMA,'enabled':True,'mode':cfg['mode'],'decisions':len(latest),'changed':changed,'additional_model_calls':0,'executor_mode_rule':'Only explicit decision assess commands may request advisory inference; background refresh never invokes a model'}

def assess(config,state,record,*,invoke=None):
    result=view(config,state,record);cfg=settings(config)
    if not cfg['enabled'] or cfg['mode']=='auto':return result
    old=result.get('executor_assessment',{})
    if old.get('current_and_fresh') and old.get('status')!='DEFERRED':result['cache_hit']=True;return result
    if result['status']=='STALE':result['executor_assessment']={'status':'DEFERRED','reason':'Stale decision context requires revalidation','inference_calls':0};return result
    packet={k:v for k,v in result.items() if k!='executor_assessment'}
    payload={'schema':SCHEMA,'packet':packet,'executor':cfg['executor']}
    raw=json.dumps(payload,separators=(',',':'),allow_nan=False)
    if len(raw.encode())>16384:result['executor_assessment']={'status':'DEFERRED','reason':'Selected decision packet exceeds 16KiB; no truncation','inference_calls':0};return result
    if invoke is None:
        worker=Path(__file__).resolve().parents[2]/'trial/decision_assessor.py'
        def invoke(value):
            import os,signal
            proc=subprocess.Popen([sys.executable,str(worker)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
            try:
                stdout,stderr=proc.communicate(json.dumps(value),timeout=160)
                return json.loads(stdout)
            except BaseException:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.communicate(timeout=10)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.communicate()
                raise
    try:advice=invoke(payload)
    except (OSError,ValueError,subprocess.TimeoutExpired) as error:advice={'status':'FAILED','failure':type(error).__name__,'inference_calls':None}
    if not isinstance(advice,dict):advice={'status':'FAILED','failure':'Invalid advisory response','inference_calls':None}
    if advice.get('status')=='ADVISORY_COMPLETE':
        receipt=advice.get('receipt',{});body=advice.get('advice',{});number=body.get('expected_benefit_score') if isinstance(body,dict) else None
        valid=isinstance(body,dict) and set(body)=={'expected_benefit_score','explanation','recommended_action','uncertainty'} and (number is None or numeric(number) and 0<=number<=100) and all(isinstance(body.get(k),str) and body[k].strip() and len(body[k])<=2000 for k in ('explanation','recommended_action','uncertainty'))
        valid=valid and receipt.get('kind')=='finished' and receipt.get('inference_requested') is True and receipt.get('failure') is None and receipt.get('product_id')==result['product_id'] and receipt.get('decision_id')==record['id'] and receipt.get('provider') in ('codex','claude') and receipt.get('role')=='DECISION_EVALUATION_ONLY' and bool(receipt.get('requested_model')) and receipt.get('effort') in ('low','medium','high') and bool(receipt.get('id'))
        if not valid:advice={**advice,'status':'FAILED','advice':None,'failure':'Invalid advisory output or missing attributable receipt'}
    elif 'advice' in advice:advice['advice']=None
    stored={'at':now(),'input_sha256':result['input_sha256'],**advice}
    state.setdefault('decision_executor_assessments',{})[record['id']]=stored
    state.setdefault('decision_executor_assessment_history',[]).append(copy.deepcopy(stored))
    result['executor_assessment']=stored;result['additional_executor_invocations']=advice.get('inference_calls');result['additional_model_calls']=0 if advice.get('inference_calls')==0 else None;result['call_count_scope']='Exact provider-internal model-call count is unknown; attributable receipt includes reported usage';return result


def compact(result):
    return {'status':result['status'],'expected_benefit_score':result['expected_benefit_score']['value'],
            'bottleneck_ids':[v['id'] for v in result['detected_bottlenecks']], 'bottleneck_status':result['bottleneck_status'],
            'bottleneck_source_ref':(result.get('existing_executor_prior') or {}).get('source_ref'),
            'action_recommendation':result['action_recommendation'],
            'detail_command':'decision inspect '+result['decision_id']}
