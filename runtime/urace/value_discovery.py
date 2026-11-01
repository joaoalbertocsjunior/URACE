"""Project-bound value hypotheses. Suggestions and public signals never confer authority."""
from __future__ import annotations
import copy
import hashlib
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = 'value-evidence-v1'
DEFAULTS = {'enabled': True, 'external_research': False, 'ranking': False,
            'freshness_seconds': 86400, 'research_seconds': 30, 'research_sources': 5}
CLASSES = {'declared_intent', 'provided_observation', 'market_signal', 'engineering', 'real_user', 'synthetic'}
INDICATORS = {
    'correctness': {'unit': 'proportion', 'minimum':0, 'maximum':1, 'direction': 'higher', 'kind': 'quality'},
    'completion_seconds': {'unit': 'seconds', 'minimum':0, 'direction': 'lower', 'kind': 'time'},
    'tokens': {'unit': 'provider_tokens', 'minimum':0, 'direction': 'lower', 'kind': 'resource'},
    'interventions': {'unit': 'count', 'minimum':0, 'direction': 'lower', 'kind': 'user_outcome'},
    'rework': {'unit': 'count', 'minimum':0, 'direction': 'lower', 'kind': 'user_outcome'},
    'retention': {'unit': 'proportion', 'minimum':0, 'maximum':1, 'direction': 'higher', 'kind': 'market_outcome'},
}

def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def settings(config: dict) -> dict:
    raw=config.get('value_discovery',{})
    if not isinstance(raw,dict):raise ValueError('Value-discovery settings must be an object')
    result = {**DEFAULTS, **raw}
    if set(result) != set(DEFAULTS): raise ValueError('Unknown value-discovery setting')
    for name in ('enabled', 'external_research', 'ranking'):
        if type(result[name]) is not bool: raise ValueError(name+' must be boolean')
    for name, low, high in [('freshness_seconds', 60, 31536000), ('research_seconds', 1, 300), ('research_sources', 1, 50)]:
        if type(result[name]) is not int or not low <= result[name] <= high: raise ValueError('Invalid '+name)
    return result

def project(config: dict, state: dict | None = None) -> dict:
    value = (state or {}).get('project') or config.get('project') or {}
    if not isinstance(value, dict) or not isinstance(value.get('intent'), str) or not value['intent'].strip(): return {}
    return value

def identity(config: dict, state: dict | None = None) -> str:
    p = project(config, state)
    return str(p.get('id',p.get('name')) or hashlib.sha256(p['intent'].encode()).hexdigest()[:20]) if p else 'undeclared'

def store_path(config: dict, state: dict | None = None) -> Path:
    from ._common import state_path
    return state_path(config).parent / ('value-discovery-'+digest(identity(config, state))+'.json')

def empty(config: dict, state: dict | None = None) -> dict:
    return {'schema': VERSION, 'project_id': identity(config, state), 'hypotheses': [], 'observations': [],
            'research': [], 'evidence': [], 'assessments': [], 'experiments': [], 'revision': 0, 'input_hash': None}

def load(config: dict, state: dict | None = None) -> dict:
    path = store_path(config, state)
    if not path.exists():
        # Preserve evidence written before full-length project hashes were adopted.
        legacy = path.parent / ('value-discovery-'+digest(identity(config, state))[:24]+'.json')
        if legacy.exists(): path = legacy
    if path.is_symlink(): raise ValueError('Value evidence must not be a symlink')
    data = json.loads(path.read_text()) if path.exists() else empty(config, state)
    if data.get('schema') != VERSION or data.get('project_id') != identity(config, state): raise ValueError('Value evidence project/schema mismatch')
    return data

def save(config: dict, data: dict, state: dict | None = None) -> None:
    from ._common import atomic_write_json
    if data.get('project_id') != identity(config, state): raise ValueError('Value evidence belongs to another project')
    data['revision'] = data.get('revision', 0)+1
    atomic_write_json(store_path(config, state), data)

def proposed(config: dict, state: dict | None = None) -> list[dict]:
    if not settings(config)['enabled']: return []
    p = project(config, state)
    if not p: return []
    result = []
    for requirement in p.get('requirements', []):
        if not isinstance(requirement, dict) or not all(isinstance(requirement.get(k), str) and requirement[k].strip() for k in ('id', 'title', 'success_measure')): continue
        basis = {'project': identity(config, state), 'intent': p['intent'], 'requirement': requirement}
        result.append({'id': 'value-'+digest(basis)[:24], 'requirement_id': requirement['id'], 'problem': requirement['title'],
                       'declared_success': requirement['success_measure'], 'intent_revision': digest(basis),
                       'beneficiary': 'Declared project workflow; actual user population not established',
                       'indicators': copy.deepcopy({k: INDICATORS[k] for k in ('correctness', 'completion_seconds', 'tokens', 'interventions')}),
                       'status': 'PROPOSED', 'evidence_class': 'declared_intent', 'source_refs': ['project.requirements:'+requirement['id']],
                       'counterevidence': [], 'real_user_benefit_verified': False, 'market_fit_established': False})
    return result

def sync(config: dict, state: dict | None = None) -> dict:
    """Cheap unchanged-input cache; no network, executor inference or goal mutation."""
    from ._common import state_lock
    if not project(config,state):return empty(config,state)
    if not settings(config)['enabled']:return load(config,state)
    initial=load(config,state);proposals=proposed(config,state);fingerprint=digest({'settings':settings(config),'proposals':proposals})
    if initial.get('input_hash')==fingerprint:return initial
    with state_lock(store_path(config, state)):
        data = load(config, state)
        proposals = proposed(config, state); fingerprint = digest({'settings': settings(config), 'proposals': proposals})
        if data.get('input_hash') == fingerprint: return data
        current = {h['id']:h for h in proposals}; existing = {h['id']:h for h in data['hypotheses']}
        for h in data['hypotheses']:
            if h['id'] not in current and h.get('origin', 'requirement') == 'requirement': h['status'] = 'SUPERSEDED'
            elif h['id'] in current and h.get('status')=='SUPERSEDED':h['status']='PROPOSED'
        data['hypotheses'].extend(h for key,h in current.items() if key not in existing)
        data['input_hash'] = fingerprint
        save(config, data, state)
        return data

def hypothesis(data: dict, key: str) -> dict:
    matches = [h for h in data['hypotheses'] if h['id'] == key]
    if len(matches) != 1: raise ValueError('Unknown value hypothesis')
    return matches[0]

def number(value: Any) -> float:
    if type(value) not in (int,float):raise ValueError('Finite numeric measurement required')
    try:result=float(value)
    except (OverflowError,ValueError):raise ValueError('Finite numeric measurement required') from None
    if not math.isfinite(result):raise ValueError('Finite numeric measurement required')
    return result

def observe(data: dict, key: str, payload: dict, *, now: float | None = None) -> dict:
    """Record supplied data as supplied, never as independently verified user telemetry."""
    now = time.time() if now is None else now
    h = hypothesis(data, key)
    if h.get('status') == 'SUPERSEDED': raise ValueError('Hypothesis belongs to earlier intent')
    if not isinstance(payload, dict) or len(json.dumps(payload).encode()) > 1048576: raise ValueError('Bounded observation object required')
    forbidden = {'trusted', 'independent_verified', 'runtime_verified', 'real_user_value_verified', 'origin'} & payload.keys()
    if forbidden: raise ValueError('Trust/verification flags cannot be supplied through observations')
    metric = payload.get('metric')
    if metric not in h['indicators']: raise ValueError('Observation must reference a declared indicator')
    if payload.get('evidence_class', 'provided_observation') not in CLASSES: raise ValueError('Unknown evidence class')
    if h['indicators'][metric]['unit']=='provider_tokens' and payload.get('provider') not in {'codex','claude'}:raise ValueError('Token observations require a provider; token currencies cannot be pooled')
    stamp = number(payload.get('observed_unix', now))
    if stamp > now or stamp <= 0: raise ValueError('Observation cannot be future dated')
    samples = payload.get('samples')
    if not isinstance(samples, list) or not samples or len(samples)>10000: raise ValueError('Provide 1..10000 paired samples')
    ids = set()
    for sample in samples:
        if not isinstance(sample, dict) or not isinstance(sample.get('id'), str) or not sample['id'] or sample['id'] in ids: raise ValueError('Unique paired sample IDs required')
        ids.add(sample['id'])
        for name in ('before', 'after'):
            n=number(sample[name])
            if ('minimum' in h['indicators'][metric] and n<h['indicators'][metric]['minimum']) or ('maximum' in h['indicators'][metric] and n>h['indicators'][metric]['maximum']): raise ValueError('Measurement outside indicator range')
        for name in ('quality_before', 'quality_after'):
            if name in sample and not 0 <= number(sample[name]) <= 1: raise ValueError('Quality must be a proportion')
    record = {**copy.deepcopy(payload), 'hypothesis_id':key, 'observed_unix':stamp, 'provenance':'provided_data',
              'independently_verified':False, 'schema':VERSION}
    record['id']='observation-'+digest(record)[:24]
    if any(r['id']==record['id'] for r in data['observations']): return record
    prior_ids={s['id'] for r in data['observations'] if r.get('hypothesis_id')==key and r.get('metric')==metric and r.get('provider')==payload.get('provider') for s in r.get('samples',[])}
    if prior_ids & ids: raise ValueError('Sample replay across observations')
    data['observations'].append(record);h['status']='OBSERVED'
    return record

def outcome_freshness(outcome:dict,config:dict,now:float|None=None)->str:
    stamp=outcome.get('evaluated_at')
    try:
        if not isinstance(stamp,str):return 'UNKNOWN'
        parsed=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        if parsed.tzinfo is None:return 'UNKNOWN'
        age=(time.time() if now is None else now)-parsed.timestamp()
        if not math.isfinite(age) or age<0:return 'UNKNOWN'
    except (ValueError,TypeError,OverflowError,OSError):return 'UNKNOWN'
    return 'FRESH' if age<=settings(config)['freshness_seconds'] else 'STALE'

def contradicted(data:dict,h:dict)->bool:
    return bool(h.get('counterevidence')) or any(e.get('hypothesis_id')==h['id'] and e.get('stance')=='contradicts' for e in data.get('evidence',[]))

def percent_change(before:float,after:float)->float|None:
    if not before:return None
    result=100*(after/before-1)
    return result if math.isfinite(result) else None

def validate(data: dict, key: str, config: dict, *, now: float | None = None) -> dict:
    """Validate calculations; independent benefit remains the existing verifier's job."""
    now = time.time() if now is None else now; h=hypothesis(data,key); reports={}; counter=[]
    if h.get('status')=='SUPERSEDED':raise ValueError('Hypothesis belongs to earlier intent')
    metric_groups=[(metric,definition,provider) for metric,definition in h['indicators'].items() for provider in (('codex','claude') if definition['unit']=='provider_tokens' else (None,))]
    for metric, definition,provider in metric_groups:
        report_key=metric+':'+provider if provider else metric
        records=[r for r in data['observations'] if r.get('hypothesis_id')==key and r.get('metric')==metric and r.get('provider')==provider and 0<=now-r['observed_unix']<=settings(config)['freshness_seconds']]
        samples=[s for r in records for s in r['samples']]
        if not samples:reports[report_key]={'status':'UNKNOWN','samples':0};continue
        before=statistics.mean(s['before'] for s in samples);after=statistics.mean(s['after'] for s in samples);sign=1 if definition['direction']=='higher' else -1
        quality_known=all('quality_before' in s and 'quality_after' in s for s in samples)
        quality_loss=any(s.get('quality_after',0)<s.get('quality_before',0) for s in samples) if quality_known else None
        wins=sum(sign*(s['after']-s['before'])>0 for s in samples);losses=sum(sign*(s['after']-s['before'])<0 for s in samples)
        r={'status':'CALCULATION_VALIDATED_ON_PROVIDED_DATA','samples':len(samples),'baseline_mean':before,'candidate_mean':after,
           'change_pct':percent_change(before,after),'direction':definition['direction'],'unit':definition['unit'],
           'paired_wins':wins,'paired_losses':losses,'quality_regressed':quality_loss,'quality_known':quality_known,
           'benefit_observed_in_provided_data':sign*(after-before)>0 and quality_known and not quality_loss,
           'confidence':'Descriptive only; source independence and causal attribution are not established',
           'source_observation_ids':[r['id'] for r in records]}
        reports[report_key]=r
        if quality_loss or sign*(after-before)<0:counter.append({'metric':metric,'reason':'Quality or outcome regression'})
    counter += [{'evidence_id':r['id'],'reason':'Provided counterevidence requires independent resolution'} for r in data.get('evidence',[]) if r.get('hypothesis_id')==key and r.get('stance')=='contradicts']
    h['counterevidence']=counter; h['assessment']={'schema':VERSION,'at_unix':now,'indicators':reports,'independent_outcome':h.get('independent_outcome',{'status':'UNKNOWN'}),'market_fit_established':False}
    independent=h.get('independent_outcome',{});freshness=outcome_freshness(independent,config,now)
    verified=independent.get('status') in {'OUTCOME_VERIFIED','REAL_USER_VALUE_VERIFIED'} and freshness=='FRESH'
    h['status']='CONTRADICTED' if counter else 'VALIDATED_WITHIN_SCOPE' if verified else 'STALE' if freshness=='STALE' else 'OBSERVED' if any(r['samples'] for r in reports.values()) else 'UNKNOWN'
    h['real_user_benefit_verified']=verified and not counter and independent.get('real_user_value_verified') is True
    assessment=h['assessment'];assessment['id']='value-assessment-'+digest({k:v for k,v in assessment.items() if k!='at_unix'})[:24]
    if not any(a['id']==assessment['id'] for a in data.setdefault('assessments',[])):data['assessments'].append(copy.deepcopy(assessment))
    return assessment

def link_outcomes(data: dict, state: dict) -> bool:
    """Only consume outcomes already computed by outcome_verification.refresh."""
    changed=False;goals={g['id']:g for g in state.get('objectives',[])};by_requirement={}
    for operation in state.get('operations',[]):
        goal=goals.get(operation.get('objective_reference'),{})
        if operation.get('outcome') and goal.get('project_id')==data['project_id']:
            by_requirement[(goal.get('project_requirement'),goal.get('project_source_sha256'))]=operation
    for h in data['hypotheses']:
        if h.get('status')=='SUPERSEDED':continue
        latest=by_requirement.get((h.get('requirement_id'),h['intent_revision']))
        if latest is None:continue
        outcome=copy.deepcopy(latest['outcome']);value={'operation_id':latest['id'],**outcome}
        if h.get('independent_outcome')!=value:
            h['independent_outcome']=value;h['real_user_benefit_verified']=outcome.get('real_user_value_verified') is True
            if contradicted(data,h):h['status']='CONTRADICTED';h['real_user_benefit_verified']=False
            elif outcome.get('status') in {'OUTCOME_VERIFIED','REAL_USER_VALUE_VERIFIED'}:h['status']='VALIDATED_WITHIN_SCOPE'
            elif outcome.get('status')=='REGRESSED':h['status']='CONTRADICTED'
            else:h['status']='UNKNOWN'
            changed=True
    return changed

def research(root: Path, config: dict, data: dict, key: str, *, now: float | None = None) -> dict:
    from . import external_metrics
    h=hypothesis(data,key); policy=settings(config);now=time.time() if now is None else now;external=config.get('external_metrics',{})
    if not policy['enabled'] or not policy['external_research'] or external.get('mode','DISABLED')=='DISABLED':return {'status':'DISABLED','inference_calls':0,'external_calls':0}
    if 'measurement' not in config.get('authority',{}).get('delegated',[]):return {'status':'NOT_AUTHORIZED','inference_calls':0,'external_calls':0}
    sources=external.get('sources',[])
    if not sources:return {'status':'NO_CONFIGURED_SOURCES','inference_calls':0,'external_calls':0,'scope':'Configured sources only; no implicit public crawler'}
    basis=digest({'sources':sources,'policy':policy,'external_mode':external['mode']})
    prior=next((r for r in reversed(data['research']) if r['basis']==basis and now-r['at_unix']<policy['freshness_seconds']),None)
    if prior:
        if prior['id'] not in h.setdefault('research_refs',[]):h['research_refs'].append(prior['id'])
        return {**prior,'hypothesis_id':key,'status':'CACHED','additional_external_calls':0}
    start=time.monotonic();findings=[];errors=[];fetches=0
    for source in sources[:policy['research_sources']]:
        remaining=policy['research_seconds']-(time.monotonic()-start)
        if remaining<=0:break
        # Four sequential requests in github_repository; other collectors use one.
        timeout=min(float(external.get('timeout_seconds',10)),remaining/(4 if source.get('kind')=='github_repository' else 1))
        if timeout<=0:break
        if source.get('kind')=='json_file':
            p=Path(source.get('location',''));p=p if p.is_absolute() else root/p
            relative=p.resolve().relative_to(root.resolve()) if p.resolve().is_relative_to(root.resolve()) else None
            if relative is None or any(part.startswith('.') for part in relative.parts):errors.append({'source':source.get('id'),'error':'Value research requires explicit non-hidden project data sources'});continue
        observation=external_metrics.collect(root,{**external,'sources':[source],'timeout_seconds':timeout,'confine_file_sources':True});fetches+=1
        errors.extend(observation['errors'])
        for item in observation['observations']:
            findings.append({'source':item['source'],'values':item['values'],'events':item.get('events',[]),'evidence_class':'market_signal',
                             'data_sha256':digest(item),'independently_verified_user_benefit':False})
    record={'id':'research-'+digest({'basis':basis,'at':now})[:24],'basis':basis,'at_unix':now,'hypothesis_id':key,
            'status':'SIGNALS_OBSERVED' if findings else 'NO_VALID_SIGNALS','question':'Which attributable signals support or contradict '+h['declared_success']+'?',
            'findings':findings,'errors':errors,'source_fetches':fetches,'sources_considered':len(sources),'sources_skipped_by_allowance':max(0,len(sources)-fetches),
            'elapsed_seconds':time.monotonic()-start,'tokens':0,'inference_calls':0,'market_fit_established':False,
            'scope':'Configured source research, not customer discovery interviews, adoption verification or open-web search'}
    data['research'].append(record);h.setdefault('research_refs',[]).append(record['id']);return record

def experiment(data: dict, payload: dict) -> dict:
    required=('id','hypothesis_id','primary_indicator','baseline_version','candidate_version','quality_floor','resource_limit')
    if not isinstance(payload,dict) or any(k not in payload for k in required):raise ValueError('Declare experiment identity, versions, primary indicator, quality floor and resource limit before observation')
    h=hypothesis(data,payload['hypothesis_id'])
    if payload['primary_indicator'] not in h['indicators']:raise ValueError('Unknown primary indicator')
    if not 0<=number(payload['quality_floor'])<=1 or number(payload['resource_limit'])<=0:raise ValueError('Invalid experiment guardrails')
    if not all(isinstance(payload[k],str) and payload[k] for k in ('id','baseline_version','candidate_version')):raise ValueError('Experiment versions and identity must be strings')
    if any(r['id']==payload['id'] for r in data['experiments']):raise ValueError('Experiment identities are immutable')
    if any(r.get('hypothesis_id')==h['id'] for r in data['observations']):raise ValueError('Cannot prespecify an experiment after observations')
    record={**copy.deepcopy(payload),'contract_sha256':digest(payload),'registered_unix':time.time(),'status':'PRESPECIFIED'};data['experiments'].append(record);return record

def advisory_ranking(data: dict, config: dict) -> list[dict]:
    enabled=settings(config)['enabled'] and settings(config)['ranking'] and 'priority' in config.get('authority',{}).get('delegated',[])
    rows=[]
    for h in data['hypotheses']:
        outcome=h.get('independent_outcome',{})
        if h.get('status') in {'SUPERSEDED','STALE','CONTRADICTED'} or contradicted(data,h):continue
        if outcome_freshness(outcome,config)!='FRESH':continue
        if outcome.get('status') not in {'OUTCOME_VERIFIED','REAL_USER_VALUE_VERIFIED'}:continue
        rows.append({'requirement_id':h['requirement_id'],'hypothesis_id':h['id'],'net_value_delta':outcome.get('net_value_delta'),'evidence_kind':outcome.get('evidence_kind'),'eligible_for_policy':enabled,'authority':'Advisory; explicit priority remains primary'})
    return rows

def status(config: dict, state: dict | None = None) -> dict:
    data=load(config,state);hypotheses=copy.deepcopy(data['hypotheses']);current=time.time();freshness=settings(config)['freshness_seconds']
    for h in hypotheses:
        independent=h.get('independent_outcome',{});fresh=outcome_freshness(independent,config,current)
        h['outcome_freshness']=fresh
        if h.get('status')=='SUPERSEDED':h['real_user_benefit_verified']=False;continue
        if contradicted(data,h):h['status']='CONTRADICTED';h['real_user_benefit_verified']=False;continue
        verified=independent.get('status') in {'OUTCOME_VERIFIED','REAL_USER_VALUE_VERIFIED'}
        h['real_user_benefit_verified']=verified and fresh=='FRESH' and independent.get('real_user_value_verified') is True
        if verified:
            h['status']='VALIDATED_WITHIN_SCOPE' if fresh=='FRESH' else 'STALE' if fresh=='STALE' else 'UNKNOWN'
        else:
            assessment=h.get('assessment',{})
            if assessment and current-assessment.get('at_unix',0)>freshness:h['status']='STALE'
    return {'schema':VERSION,'project_id':data['project_id'],'configuration':settings(config),'hypotheses':hypotheses,
            'observations':len(data['observations']),'evidence':data.get('evidence',[]),'assessments':data.get('assessments',[]),'research':data['research'],'experiments':data['experiments'],'ranking':advisory_ranking(data,config),
            'coverage':{'proposed':len(hypotheses),'independent_outcome_verified':sum(h.get('status')=='VALIDATED_WITHIN_SCOPE' and h.get('independent_outcome',{}).get('status') in {'OUTCOME_VERIFIED','REAL_USER_VALUE_VERIFIED'} for h in hypotheses)},
            'market_fit_established':False,'limitations':'Proposals, supplied observations and public signals are distinct from independent observed benefit. Existing outcome verification owns benefit validation.'}


def define_indicator(data: dict,key: str,payload: dict)->dict:
    import re
    h=hypothesis(data,key);name=payload.get('name')
    if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}',name):raise ValueError('Indicator name must be a simple identifier')
    if name in h['indicators']:raise ValueError('Existing indicator definitions are immutable; use a new name')
    if payload.get('direction') not in {'higher','lower'} or not isinstance(payload.get('unit'),str) or not payload['unit']:raise ValueError('Indicator unit and direction required')
    if payload.get('kind') not in {'quality','time','resource','user_outcome','market_outcome'}:raise ValueError('Declare indicator kind')
    bounds={k:number(payload[k]) for k in ('minimum','maximum') if k in payload}
    if bounds.get('minimum',float('-inf'))>bounds.get('maximum',float('inf')):raise ValueError('Indicator bounds are reversed')
    h['indicators'][name]={**{k:payload[k] for k in ('unit','direction','kind')},**bounds};return h['indicators'][name]

def attach_evidence(data:dict,key:str,payload:dict)->dict:
    hypothesis(data,key)
    if not isinstance(payload,dict) or not all(isinstance(payload.get(k),str) and payload[k].strip() for k in ('claim','source_ref')):raise ValueError('Evidence requires claim and attributable source reference')
    if payload.get('stance') not in {'supports','contradicts','neutral'}:raise ValueError('Declare evidence stance')
    if len(json.dumps(payload).encode())>100000 or any(k in payload for k in ('trusted','verified','independent_verified','hypothesis_id','id','origin')):raise ValueError('Bounded supplied evidence, not a verification grant, required')
    record={'hypothesis_id':key,**copy.deepcopy(payload),'origin':'provided_evidence','independently_verified':False,'at_unix':time.time()};record['id']='evidence-'+digest({k:v for k,v in record.items() if k!='at_unix'})[:24]
    if not any(r['id']==record['id'] for r in data.setdefault('evidence',[])):data['evidence'].append(record)
    h=hypothesis(data,key)
    if payload['stance']=='contradicts':
        if h.get('status')!='SUPERSEDED':h['status']='CONTRADICTED'
        h['real_user_benefit_verified']=False
    return record

def refresh(config:dict,state:dict)->dict:
    """Integrate with existing outcome verifier; never run a second benefit oracle."""
    if not project(config,state):return {'enabled':settings(config)['enabled'],'status':'NO_DECLARED_PROJECT','hypotheses':0}
    data=sync(config,state)
    if not settings(config)['enabled']:return {'enabled':False,'status':'DISABLED','hypotheses':len(data['hypotheses'])}
    from ._common import state_lock
    with state_lock(store_path(config,state)):
        data=load(config,state)
        changed=link_outcomes(data,state)
        external=state.get('external_metric_state',{})
        if settings(config)['external_research'] and external.get('mode','DISABLED')!='DISABLED' and external.get('latest'):
            snapshot={'at':external.get('last_collection'),'observations':external['latest']};key='existing-source-'+digest(snapshot)[:24]
            if not any(r.get('id')==key for r in data['research']):
                data['research'].append({'id':key,'at_unix':time.time(),'basis':digest(snapshot),'status':'SIGNALS_OBSERVED','source_collection':snapshot,'scope':'Existing authorized collector output; market signals, not verified benefit','elapsed_seconds':None,'source_collection_time':'Not recorded by the existing collector; not inferred as zero','tokens':0,'inference_calls':0,'additional_external_calls':0,'market_fit_established':False});changed=True
        if changed:save(config,data,state)
    return {'enabled':True,'status':'SUGGESTIONS_ONLY','hypotheses':len(data['hypotheses']),'market_fit_established':False,'independent_verifier':'outcome_verification'}

def dispatch(args,config:dict,root:Path)->dict:
    from ._common import state_lock
    action=args.name or 'list'
    if action not in {'propose','list','inspect','define','observe','evidence','validate','research','rank','experiment'}:raise ValueError('Use product value propose|list|inspect|define|observe|evidence|validate|research|rank|experiment')
    if action in {'list','rank'}:
        view=status(config);return {'ranking':view['ranking']} if action=='rank' else view
    if action=='inspect':
        data=load(config);return {'hypothesis':hypothesis(status(config),args.value_id),'observations':[o for o in data['observations'] if o.get('hypothesis_id')==args.value_id],'evidence':[e for e in data.get('evidence',[]) if e.get('hypothesis_id')==args.value_id]}
    payload=json.loads(args.value_data) if getattr(args,'value_data',None) else {}
    if not isinstance(payload,dict) or len(json.dumps(payload).encode())>1048576:raise ValueError('--data must be a bounded JSON object')
    if action=='propose':data=sync(config);return {'hypotheses':data['hypotheses'],'status':'PROPOSED','inference_calls':0}
    with state_lock(store_path(config)):
        data=load(config)
        if action=='experiment':result=experiment(data,payload)
        else:
            if not args.value_id:raise ValueError('--id is required')
            fn={'define':lambda:define_indicator(data,args.value_id,payload),'observe':lambda:observe(data,args.value_id,payload),'evidence':lambda:attach_evidence(data,args.value_id,payload),'validate':lambda:validate(data,args.value_id,config),'research':lambda:research(root,config,data,args.value_id)}[action]
            result=fn()
        save(config,data)
        return result


def ranking_scores(config:dict,state:dict)->dict:
    if not settings(config)['ranking'] or not settings(config)['enabled']:return {}
    effective={**config,'authority':state.get('authority',config.get('authority',{}))}
    return {r['requirement_id']:number(r['net_value_delta']) for r in advisory_ranking(load(config,state),effective) if r['eligible_for_policy'] and type(r.get('net_value_delta')) in (int,float) and r['net_value_delta']>0}


def execution_quality_views(trial_root:Path)->dict:
    views={}
    for name,filename in [('repository','repository-study-latest.json'),('context','downstream-context-latest.json'),('specification','downstream-specification-latest.json')]:
        path=trial_root/filename
        if not path.exists():views[name]={'status':'NOT_MEASURED'};continue
        try:
            raw=path.read_bytes();value=json.loads(raw);views[name]={'status':'MEASURED' if value.get('output_quality',{}).get('quality_measured_workflows',0)>0 else 'NOT_MEASURED','cohort':value.get('cohort'),'output_quality':value.get('output_quality'),'measurement_contract_sha256':value.get('measurement_contract_sha256'),'cached_report_sha256':hashlib.sha256(raw).hexdigest(),'report_age_seconds':max(0,time.time()-path.stat().st_mtime)}
        except (OSError,ValueError):views[name]={'status':'REPORT_UNAVAILABLE'}
    return views
