"""Contract-bound execution choices; observations never confer authority."""
import math

def choose(policy, *, provider, family, model, contract, engine, default_effort, now, enabled=True, quarantined=False):
    if default_effort not in ('low','medium','high'):default_effort='medium'
    fallback={'provider':provider,'model':model,'native_effort':default_effort,'adaptive':False,'reason':'Owner default; no qualified matching evidence'}
    if not enabled or quarantined or not isinstance(policy,dict):return fallback
    expiry=policy.get('expires_unix')
    if type(expiry) not in (int,float) or not math.isfinite(expiry) or expiry<=now:return fallback
    if policy.get('models',{}).get(provider)!=model or policy.get('engine_sha256',policy.get('core_engine_sha256'))!=engine or policy.get('contracts',policy.get('workloads',{})).get(family)!=contract:return fallback
    for row in policy.get('recommendations',[]):
        if row.get('provider')!=provider or row.get('family',family)!=family:continue
        samples=row.get('samples',0);effort=row.get('native_effort')
        if type(samples) is not int or samples<35 or effort not in ('low','medium','high'):continue
        if row.get('quality_nonregressing') is not True or row.get('usage_complete') is not True or row.get('timing_complete') is not True:continue
        t,k=row.get('time_ratio'),row.get('token_ratio')
        if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (t,k)):continue
        if max(t,k)>1.05 or min(t,k)>.8:continue
        return {**fallback,'native_effort':effort,'adaptive':True,'reason':'Qualified evidence for this exact model/workload/engine','cohort':policy.get('cohort')}
    return fallback

def execution_mode(requested, *, requirements, continuity=False):
    if requested not in ('auto','lightweight','managed','standalone'):raise ValueError('Unknown execution mode')
    if requested!='auto':return requested
    return 'managed' if continuity or len(requirements)>1 or any(r.get('dependencies') for r in requirements) else 'lightweight'

def outcomes(rows,elapsed_seconds):
    """Whole-window throughput; waiting and failed attempts remain in the denominator."""
    if type(elapsed_seconds) not in (int,float) or not math.isfinite(elapsed_seconds) or elapsed_seconds<=0:raise ValueError('Positive elapsed measurement window required')
    completed=[r for r in rows if r.get('complete')];valid=sum(r.get('delivered',r.get('validated')) is True for r in completed)
    receipts={x['id']:x for r in rows for x in r.get('native_receipts',[]) if x.get('id')}
    tokens=[x.get('tokens') for x in receipts.values()];known=bool(tokens) and all(type(x) is int and x>=0 for x in tokens)
    total=sum(x for x in tokens if type(x) is int and x>=0)
    interventions=[e for r in rows for e in r.get('interventions',[])]
    return {'completed':len(completed),'validated':valid,'failed_or_pending':len(rows)-valid,'elapsed_seconds':elapsed_seconds,'validated_per_elapsed_hour':3600*valid/elapsed_seconds,'known_tokens':total,'usage_complete':known,'validated_per_million_tokens':1e6*valid/total if known and total else None,'tokens_per_validated_delivery':total/valid if known and valid else None,'native_calls':len(receipts),'recorded_interventions':len(interventions),'human_seconds':sum(e['seconds'] for e in interventions) if interventions and all(type(e.get('seconds')) in (int,float) for e in interventions) else None,'human_measurement':'Recorded events only; absent observations do not prove maintenance-free operation'}
