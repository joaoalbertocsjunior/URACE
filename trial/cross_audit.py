"""Sampled second-provider revalidation; never rewrites historical verdicts."""
from pathlib import Path
from datetime import datetime,timezone
import json,time,uuid
from common import BASE,atomic
from quality_policy import blind_review_prompt,normalize_review,quality_pass,preserve_decision_contract

def run(base=BASE,sample_size=3):
    import spec_trial as worker
    from controls import effective
    base=Path(base);clock=worker.load(base/'trial-clock.json');state=worker.load(base/'state.json',{'jobs':[]})
    history=worker.load(base/'cross-audit-latest.json',{})
    prior=history.get('results',[]) if history.get('trial_id')==clock['trial_id'] else []
    from quality_restore import withdrawn_versions
    seen={r['version'] for r in prior}|withdrawn_versions(base);results=list(prior);attempts=0
    def priority(job):
        proposal=worker.load(base/'runs'/clock['trial_id']/job['id']/'proposal.json',{})
        risk=False
        try:preserve_decision_contract(proposal.get('old',''),proposal.get('new',''))
        except ValueError:risk=True
        return (not risk,-job.get('accepted_version',0))
    for job in sorted(state['jobs'],key=priority):
        if job.get('trial_id')!=clock['trial_id']:continue
        if job.get('outcome')!='ACCEPTED_EDITORIAL_IMPROVEMENT' or job.get('accepted_version') in seen:continue
        if attempts>=sample_size:break
        version=job['accepted_version'];folder=base/'runs'/clock['trial_id']/job['id']
        proposal=worker.load(folder/'proposal.json',{})
        static_risk=None
        try:preserve_decision_contract(proposal['old'],proposal['new'])
        except (ValueError,KeyError) as error:static_risk=str(error)
        controls=effective(base);eligible,_=worker.eligible()
        choices=[p for p in eligible if p!=job.get('proposer_provider') and controls['executors'][p]['enabled']]
        if controls['paused'] or not controls['executor_enabled'] or not choices:break
        provider=choices[0];attempts+=1;identifier='cross-audit-'+uuid.uuid4().hex;audit_folder=base/'cross-audits'/clock['trial_id']/identifier;audit_folder.mkdir(parents=True)
        parent,_=worker.read_version(job['parent_version']);candidate,_=worker.read_version(version)
        # Retrieve the producing context from immutable prompt artifacts, then
        # apply only that proposal. This does not disclose the proposer rationale.
        contexts=worker.sections(parent);before=next((p for p in contexts if worker.digest(p)==job['context_sha256']),None)
        item={'version':version,'provider':provider,'proposer_provider':job.get('proposer_provider'),'artifact':str(audit_folder),'static_risk':static_risk}
        try:
            if before is None:raise ValueError('Original context unavailable')
            after=before.replace(proposal['old'],proposal['new'],1)
            prompt,swapped=blind_review_prompt(before,after,identifier)
            prompt+='\nRetained owner constraints: '+json.dumps(job.get('operator_context',{}).get('value',{}))
            raw=worker.native(provider,prompt,audit_folder,'review');review=normalize_review(raw,swapped,before,after);atomic(audit_folder/'review.json',review)
            item['status']='CROSS_PROVIDER_REVALIDATED_EDITORIAL' if quality_pass(review) and worker.review_pass(review) and review.get('preserves_operator_constraints') is True else 'CROSS_PROVIDER_DISAGREEMENT'
            if static_risk and item['status']=='CROSS_PROVIDER_REVALIDATED_EDITORIAL':item['status']='MODEL_EQUIVALENCE_JUDGED_WITH_STATIC_RISK'
            item['review']=review
        except Exception as error:item.update(status='AUDIT_INCOMPLETE',error=type(error).__name__+': '+str(error))
        # Incomplete native attempts remain retryable on a later audit; never
        # fabricate a disagreement from a transport failure.
        if item['status']!='AUDIT_INCOMPLETE':results.append(item)
        atomic(audit_folder/'report.json',item)
    record={'schema':'cross-provider-audit-v1','at':datetime.now(timezone.utc).isoformat(),'trial_id':clock['trial_id'],
      'results':results,'current_native_attempts':attempts,'sampling':'Static semantic risks first, newest first within each group; not representative or random',
      'revalidated_versions':sum(r['status']=='CROSS_PROVIDER_REVALIDATED_EDITORIAL' for r in results),
      'disagreements':sum(r['status']=='CROSS_PROVIDER_DISAGREEMENT' for r in results),
      'semantically_flagged':sum(bool(r.get('static_risk')) for r in results),
      'claim':'Independent model editorial revalidation, not customer-value or executable equivalence proof'}
    atomic(base/'cross-audit-latest.json',record);return record
