"""Append-only audit of historical editorial risks and matched strategy observations."""
from pathlib import Path
from collections import Counter
import hashlib,json,time
from common import atomic
from quality_policy import preserve_decision_contract,POLICY

def load(path,default=None):return json.loads(path.read_text()) if path.exists() else default

def audit(base):
    base=Path(base);clock=load(base/'trial-clock.json',{});state=load(base/'state.json',{'jobs':[]})
    jobs=[j for j in state['jobs'] if j.get('trial_id')==clock.get('trial_id')];risks=[]
    for j in jobs:
        if j.get('outcome')!='ACCEPTED_EDITORIAL_IMPROVEMENT':continue
        folder=base/'runs'/clock['trial_id']/j['id'];proposal=load(folder/'proposal.json',{})
        try:
            if not proposal:raise ValueError('Proposal unavailable for semantic re-audit')
            preserve_decision_contract(proposal['old'],proposal['new'])
        except (ValueError,KeyError) as error:
            risks.append({'version':j.get('accepted_version'),'job_id':j['id'],'reason':str(error),
                          'old':proposal.get('old'),'new':proposal.get('new'),'classification':'Requires revalidation; flag is not proof of a semantic defect'})
    # Group by context, provider, model and native effort. Unmatched task mix
    # is reported but never used to proclaim a winning allocation strategy.
    ledger=base/'ledger.jsonl';rows=[json.loads(l) for l in ledger.read_text().splitlines() if l] if ledger.exists() else []
    done=[r for r in rows if r.get('trial_id')==clock.get('trial_id') and r.get('kind')=='finished'];groups={}
    task_policies={j['id']:j.get('quality_policy','legacy-editorial') for j in jobs}
    for r in done:
        identifier=r.get('job_id','')
        policy=next((value for key,value in task_policies.items() if identifier.startswith(key+'-')),'auxiliary-diagnostics')
        key=(r.get('provider'),r.get('requested_model'),r.get('effort'),policy)
        group=groups.setdefault(key,{'calls':0,'known_tokens':0,'unknown_usage':0,'executor_seconds':0,'failures':0})
        group['calls']+=1;group['known_tokens']+=r.get('tokens') or 0;group['unknown_usage']+=r.get('tokens') is None
        group['executor_seconds']+=r.get('wall_seconds') or 0;group['failures']+=bool(r.get('failure'))
    from quality_restore import withdrawn_versions
    withdrawn=withdrawn_versions(base)
    for risk in risks:risk['withdrawn']=risk['version'] in withdrawn
    accepted=[j for j in jobs if j.get('outcome')=='ACCEPTED_EDITORIAL_IMPROVEMENT']
    record={'schema':'editorial-evidence-audit-v1','trial_id':clock.get('trial_id'),'recorded_unix':time.time(),
       'current_policy':POLICY,'accepted_versions':len(accepted),'withdrawn_editorial_versions':sorted(withdrawn),'unresolved_semantic_risks':sum(not r['withdrawn'] for r in risks),'historical_risk_flags':risks,
       'cross_provider_accepted':sum(j.get('different_provider_review') is True for j in accepted),
       'new_policy_accepted':sum(j.get('quality_policy')==POLICY for j in accepted),
       'strategy_observations':[dict(provider=k[0],model=k[1],native_effort=k[2],quality_policy=k[3],**v) for k,v in groups.items()],
       'allocation_conclusion':'Descriptive only; use paired contract diagnostics before preferring a strategy. No validated global optimum.',
       'mutation':'No historical snapshot, verdict or receipt rewritten',
       'coverage':{'observed_workflow':'URACE.md editorial evolution','unique_contexts':len({j.get('context_sha256') for j in jobs}),
                   'all_runtime_features_live_proven':False,'all_runtime_features_reason':'Use regression qualification and separate representative integration/operational scenarios; this Product does not exercise every feature.'}}
    atomic(base/'reports/trials'/clock['trial_id']/'quality-audits'/('audit-'+str(time.time_ns())+'.json'),record)
    atomic(base/'quality-audit-latest.json',record);return record
