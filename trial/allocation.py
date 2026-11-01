"""Provisional resource allocation: measured feedback and explicit heuristic headroom."""
from pathlib import Path
from datetime import datetime,timezone
import json,time
from common import operations_root
ROOT=operations_root()

def decide(snapshot,now):
    try:age=now-datetime.fromisoformat(snapshot['at']).timestamp()
    except (KeyError,ValueError,TypeError):return {'eligible':False,'reason':'Missing or malformed quota snapshot'}
    if not 0<=age<=6*3600:return {'eligible':False,'reason':'Stale quota metadata; wait for metadata-only refresh'}
    quota=snapshot.get('codex',{})
    if quota.get('ordinaryUsageAllowed') is not True:return {'eligible':False,'reason':'Ordinary usage unavailable or unknown'}
    rates=quota.get('rateLimits',{})
    for label in ('primary','secondary'):
        window=rates.get(label) or {};used=window.get('usedPercent')
        if not isinstance(used,(int,float)) or isinstance(used,bool) or not 0<=used<=100:return {'eligible':False,'reason':'Unknown quota headroom: '+label}
        if used>=97:return {'eligible':False,'reason':'Preserve provisional 5% account headroom: '+label,'used_percent':used}
    return {'eligible':True,'reason':'Headroom allows optional maintenance, subject to task value, cooldown and existing budgets'}

def build():
    marker=ROOT/'comparison-current.json'
    active=json.loads(marker.read_text()) if marker.exists() else {}
    if active.get('kind')=='urace_spec_improvement':
        trial=Path(active['root']);state=json.loads((trial/'status.json').read_text());comparison=json.loads((trial/'version-comparisons.json').read_text())
        report={'at':datetime.now(timezone.utc).isoformat(),'target':'URACE.md','cohort_root':str(trial),'optimal_allocation_established':False,'accepted_versions':state['accepted_improvements'],'version_chain':comparison,'known_tokens':state['known_tokens'],'missing_usage':state['missing_usage'],'known_executor_seconds':state['known_executor_seconds'],'waits':state['waits'],'quality_interpretation':'Editorial model judgments plus structural preservation checks; no executable or customer-value proof','next_learning_step':'Compare accepted specification versions to their parent and committed baseline; preserve rejected work and all costs','shared_resource_policy':json.loads((ROOT/'resource-policy.json').read_text())}
        temp=ROOT/'allocation-latest.json.tmp';temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(ROOT/'allocation-latest.json');print(json.dumps(report,indent=2));return
    trial=ROOT.parent/'productive-native-30d-v1';maintenance=ROOT.parent/'autonomous-maintenance-v1'
    marker=ROOT/'comparison-current.json'
    if marker.exists():trial=Path(json.loads(marker.read_text())['root'])
    snapshot=json.loads((ROOT/'availability-latest.json').read_text());receipts=[json.loads(p.read_text()) for p in (trial/'receipts').glob('*-job.json')]
    ledger_path=trial/'ledger.jsonl'
    ledger=[json.loads(line) for line in ledger_path.read_text().splitlines() if line] if ledger_path.exists() else []
    providers={}
    from statistics import median
    for provider in ('codex','claude'):
        rows=[r for r in receipts if r['provider']==provider];usage=[r for r in ledger if r['kind']=='finished' and r['provider']==provider]
        accepted=sum(bool(r['accepted']) for r in rows);tokens=sum(r.get('tokens') or 0 for r in usage)
        providers[provider]={'attempts':len(rows),'accepted':accepted,'acceptance_pct':100*accepted/len(rows) if rows else None,'known_tokens':tokens,'missing_usage':sum(r.get('tokens') is None for r in usage),'tokens_per_accepted_result':tokens/accepted if accepted and all(r.get('tokens') is not None for r in usage) else None,'median_acceptance_seconds':median([r.get('wall_seconds') or 0 for r in rows if r['accepted']]) if accepted else None,'total_end_to_end_seconds':sum(r.get('end_to_end_wall_seconds',r.get('wall_seconds')) or 0 for r in rows)}
    matched=[]
    reservations={r['id']:r for r in ledger if r['kind']=='reserved'}
    usage_by_job={}
    for r in ledger:
        if r['kind']=='finished':
            job=reservations.get(r['id'],{}).get('logical_job_id')
            if job:usage_by_job.setdefault(job,[]).append(r)
    for stage in range(3,8):
        pair={p:next((r for r in receipts if r['provider']==p and r.get('stage')==stage and r['accepted']),None) for p in ('codex','claude')}
        if not all(pair.values()):continue
        costs={p:sum(u.get('tokens') or 0 for u in usage_by_job.get(r['id'],[])) for p,r in pair.items()}
        times={p:r.get('wall_seconds') for p,r in pair.items()}
        matched.append({'stage':stage,'independent_cases':{p:r['validation']['cases'] for p,r in pair.items()},'known_native_tokens':costs,'wall_seconds':times,'claude_job_wall_time_less_pct':100*(1-times['claude']/times['codex']) if times['codex'] and times['claude'] is not None else None,'claude_token_count_fewer_pct':100*(1-costs['claude']/costs['codex']) if costs['codex'] and costs['claude'] else None,'interpretation':'Descriptive matched feature stage, not causal quality superiority; tokenizers differ, credit billing unknown; stage input snapshots may differ'})
    comparison=None
    c=providers['codex'];a=providers['claude']
    if c['attempts']==a['attempts']==1 and c['accepted']==a['accepted']==1 and c['known_tokens']>0 and not c['missing_usage'] and not a['missing_usage'] and c['total_end_to_end_seconds']>0:
        comparison={'claude_tokens_fewer_pct':100*(1-a['known_tokens']/c['known_tokens']),'claude_end_to_end_time_less_pct':100*(1-a['total_end_to_end_seconds']/c['total_end_to_end_seconds']),'n_per_provider':1,'interpretation':'Descriptive one-case comparison across different tokenizers; insufficient for optimal routing, statistical superiority or billed-cost comparison'}
    report={'at':datetime.now(timezone.utc).isoformat(),'cohort_root':str(trial),'optimal_allocation_established':False,'policy_kind':'Provisional constrained heuristic, not empirically optimized','codex_optional_maintenance':decide(snapshot,time.time()),'thresholds':{'minimum_headroom_pct':5,'maximum_metadata_age_hours':6,'rationale':'Initial conservative owner-capacity reserve; sensitivity and utility tradeoffs unmeasured'},'observed_productive_results':providers,'single_case_comparison':comparison,'matched_feature_samples':matched,'allocation_objective':'Validated quality and coverage gained per elapsed time and resource; higher spending permitted for justified gains; low consumption alone is never success','priority_order':['Preserve current project intent, paired comparison and independent acceptance','Use independent non-inference validation and archived real inputs','Repair substantiated defects and qualify rejected fixes before expanding features','Run bounded matched-task comparisons only when a decision remains unresolved and headroom permits'],'shared_resource_policy':json.loads((ROOT/'resource-policy.json').read_text()),'current_protocol_preserved_by_allocator':True,'next_learning_step':'Qualify the rejected maintenance proposal within existing cooldown/budget; obtain matched task repetitions before changing provider allocation','stop_rule':'Do not spend merely to fill a utilization target; stop added exploration when it produces no decision-relevant information','limitations':['Quota is account-wide and does not establish per-job billing','Quality is constrained by independent acceptance; self-reported improvements do not count','Available samples cannot establish a global optimum','Low token consumption alone proves neither efficiency nor under-allocation']}
    temp=ROOT/'allocation-latest.json.tmp';temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(ROOT/'allocation-latest.json');print(json.dumps(report,indent=2))
if __name__=='__main__':build()
