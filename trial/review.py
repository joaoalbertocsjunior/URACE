"""Evidence review and bounded cadence adaptation; never edits source or acceptance gates."""
from datetime import datetime,timezone
import json
import subprocess
import time
from common import BASE,atomic,events

DELAYS={'low':60,'medium':15,'high':5}

def recommend(rows,jobs,controls):
    recommendations={}
    for provider in ('codex','claude'):
        mode=controls['executors'][provider]['resource_effort']
        work=[j for j in jobs if j.get('proposer_provider')==provider][-20:]
        receipts=[r for r in rows if r.get('kind')=='finished' and r.get('provider')==provider][-40:]
        accepted=sum(j.get('outcome')=='ACCEPTED_EDITORIAL_IMPROVEMENT' for j in work)
        justified=(len(work)>=20 and accepted>=5 and len(receipts)>=20
                   and all(r.get('tokens') is not None and not r.get('failure') for r in receipts))
        delay={'low':15,'medium':5,'high':1}[mode] if justified else DELAYS[mode]
        recommendations[provider]={'mode':mode,'delay_seconds':delay,'observed_tasks':len(work),
            'accepted_editorial_improvements':accepted,'usage_complete':bool(receipts) and all(r.get('tokens') is not None for r in receipts),
            'reason':'Reduce optional idle after sufficient accepted editorial work and complete successful transport receipts' if justified else 'Keep operator baseline; insufficient complete evidence to justify faster cadence',
            'quality_scope':'Editorial acceptance proxy; no causal improvement, user-benefit or optimality claim'}
    return recommendations

def main():
    import spec_trial as worker
    from controls import effective
    from snapshot_metadata import inspect_snapshot
    from source_integrity import matches
    from period_feedback import compare
    from core_resources import events as core_events
    now=time.time();clock=worker.load(BASE/'trial-clock.json');state=worker.load(BASE/'state.json',{'jobs':[]})
    jobs=[j for j in state['jobs'] if j.get('trial_id')==clock['trial_id']]
    product_id=worker.load(BASE/'contract.json',{}).get('product_id')
    rows=[r for r in events() if r.get('trial_id')==clock['trial_id'] and (not product_id or r.get('product_id') in (None,product_id))]
    contract=worker.load(BASE/'contract.json')
    rows+=core_events(BASE,contract.get('product_id'),clock['trial_id'],clock.get('started_unix'))
    from accounting import reconcile,pending_status
    reconciliation=reconcile(BASE);evidence_warnings=[];issues=[];checked=[]
    for name,expected in worker.load(BASE/'harness-manifest.json',{}).items():
        if not matches(BASE/name,expected):issues.append('Harness integrity mismatch: '+name)
    for folder in sorted(worker.version(0).parent.glob('v*')):
        try:
            result=inspect_snapshot(folder);checked.append({'version':result['manifest']['version'],'integrity_verified':True})
        except (OSError,ValueError,RuntimeError,KeyError) as error:issues.append(str(folder)+': '+type(error).__name__)
    health={}
    from trial_supervisor import active as supervisor_active
    units=('urace-spec-trial.service',) if supervisor_active() else ('urace-spec-trial.service','urace-spec-trial.timer','urace-spec-trial-watchdog.timer','urace-executor-availability.timer','urace-value-benchmark.service','urace-value-benchmark.timer')
    for unit in units:
        result=subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','-p','Result'],capture_output=True,text=True,timeout=10)
        value=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line);health[unit]=value
        if result.returncode or value.get('ActiveState')=='failed' or value.get('Result') not in (None,'success'):issues.append('Unhealthy service: '+unit)
        if unit.endswith('.timer') and now<clock['ends_unix'] and value.get('ActiveState')!='active':issues.append('Inactive timer: '+unit)
    if any(r.get('kind')=='finished' and r.get('tokens') is None for r in rows):evidence_warnings.append('Incomplete native usage in this scope; all-cost efficiency withheld')
    operational_issues=list(issues);issues+=evidence_warnings
    from quality_audit import audit
    quality=audit(BASE)
    controls=effective(BASE)
    decisions=recommend(rows,jobs,controls)
    observation={'at':datetime.now(timezone.utc).isoformat(),'trial_id':clock['trial_id'],
        'expires_unix':now+10800,'providers':decisions,'source_edits':0,'additional_inference_calls':0,
        'authority':'Derived optional idle only; operator effort, quotas, safety and acceptance remain authoritative'}
    if not issues:atomic(BASE/'allocation-observation.json',observation)
    report={'at':observation['at'],'trial_id':clock['trial_id'],'review_pass':not issues,'runtime_integrity_pass':not operational_issues,'accounting_complete':not evidence_warnings,'evidence_warnings':evidence_warnings,'issues':issues,'usage_reconciliation':reconciliation,'pending_reservations':pending_status(rows,now),'measurement_scope':{'trial_id':clock['trial_id'],'product_id':product_id,'complete_matched_cohorts_assessable_independently':True},
            'executable_evaluation':worker.load(BASE/'executable-benchmark-latest.json',{'available':False}),'quality_audit':quality,'downstream_diagnostic':worker.load(BASE/'benchmark-latest.json',{'available':False}),'services':health,'versions_checked':checked,'completed_tasks':len(jobs),'adaptation':observation,
            'period_comparison':compare(rows,jobs,now,'3h'),
            'longitudinal_period_comparisons':{period:compare(rows,jobs,now,period) for period in ('day','week','month')},
            'limitations':'Engineering integrity and editorial acceptance; no real-user, market-fit or indefinite reliability proof'}
    from assessment_evidence import assess
    from project_work import engine_hash
    from snapshot_metadata import engine_snapshot
    report['comprehensive_assessment']=assess(BASE,rows,now,engine_sha256=engine_hash(),execution_sha256=engine_snapshot(BASE)['code_fingerprint'])
    atomic(BASE/'reports/trials'/clock['trial_id']/'operational-reviews'/('review-'+str(time.time_ns())+'.json'),report)
    atomic(BASE/'operational-review-latest.json',report)
    print(json.dumps(report));return 0 if not issues else 1

if __name__=='__main__':raise SystemExit(main())
