"""Exact corrective restoration of a rejected contiguous editorial tail.

No historical version or verdict is deleted. Restoration is not an improvement
claim and cannot introduce content absent from an earlier immutable snapshot.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,uuid,fcntl,sys
from common import BASE,atomic

def withdrawn_versions(base):
    base=Path(base);p=base/'withdrawn-acceptances.json';clock=json.loads((base/'trial-clock.json').read_text()) if (base/'trial-clock.json').exists() else {}
    if not p.exists():return set()
    r=json.loads(p.read_text());return set(r.get('versions',[])) if r.get('trial_id')==clock.get('trial_id') else set()

def inverse_source(version,text):
    import spec_trial as worker
    from snapshot_metadata import inspect_snapshot
    folder=worker.version(version);checked=inspect_snapshot(folder)
    if checked['manifest'].get('restoration'):raise ValueError('Cannot withdraw a corrective event as an editorial gain')
    proposal=worker.load(folder/'evidence/proposal.json',{})
    old,new=proposal.get('old'),proposal.get('new')
    if not isinstance(old,str) or not isinstance(new,str) or not old or not new or old==new:raise ValueError('Sealed proposal unavailable')
    published,_=worker.read_version(version);parent,_=worker.read_version(checked['manifest']['parent_version'])
    if published.count(new)!=1 or published.replace(new,old,1)!=parent:raise ValueError('Sealed edit is not uniquely reversible')
    if text.count(new)!=1:raise ValueError('Current source no longer has a unique exact replacement; overlapping work requires revalidation')
    return text.replace(new,old,1)

def verify(base,parent,text,restoration,audit_path=None):
    import spec_trial as worker
    base=Path(base)
    source=Path(audit_path) if audit_path is not None else base/'cross-audit-latest.json'
    if audit_path is not None and not source.resolve().is_relative_to((base/'runs').resolve()):raise ValueError('Corrective audit path escapes Product results')
    audit=worker.load(source,{})
    if hashlib.sha256(source.read_bytes()).hexdigest()!=restoration.get('audit_sha256'):raise ValueError('Corrective audit changed')
    if audit.get('trial_id')!=worker.load(base/'trial-clock.json')['trial_id']:raise ValueError('Wrong trial audit')
    rejects={r['version'] for r in audit.get('results',[]) if r.get('status')=='CROSS_PROVIDER_DISAGREEMENT' and r.get('provider')!=r.get('proposer_provider')}
    required=restoration.get('withdrawn_versions',[])
    if not required or any(type(v) is not int or not 0<v<=parent for v in required) or len(set(required))!=len(required) or not set(required)<=rejects:raise ValueError('Every reverted edit needs independent disagreement')
    if restoration.get('mode')=='EXACT_INVERSE_EDITS':
        result,_=worker.read_version(parent)
        for version in sorted(required,reverse=True):result=inverse_source(version,result)
        if result!=text:raise ValueError('Correction must be the exact inverse of sealed rejected edits')
        return
    target=restoration.get('target_version')
    if type(target) is not int or not 0<=target<parent:raise ValueError('Invalid exact restore target')
    if set(required)!=set(range(target+1,parent+1)):raise ValueError('Every reverted tail version needs second-provider disagreement')
    restored,manifest=worker.read_version(target)
    if text!=restored:raise ValueError('Restoration must exactly match earlier immutable source')
    for version in sorted(required):
        _,m=worker.read_version(version)
        if m.get('parent_version')!=version-1:raise ValueError('Restoration tail lineage mismatch')
    return manifest

def record_withdrawals(base,manifest):
    base=Path(base);record=manifest.get('restoration')
    if not record:return
    clock=json.loads((base/'trial-clock.json').read_text())
    if manifest.get('trial_id')!=clock['trial_id']:raise ValueError('Restoration withdrawal trial mismatch')
    prior=withdrawn_versions(base)
    atomic(base/'withdrawn-acceptances.json',{'trial_id':clock['trial_id'],
      'versions':sorted(prior|set(record['withdrawn_versions'])),'corrective_snapshot':manifest['version'],'audit_sha256':record['audit_sha256'],
      'history':'Original snapshots and contemporaneous verdicts retained; these gains are withdrawn from current efficiency totals'})

def run(base=BASE):
    import spec_trial as worker
    from source_integrity import matches
    from controls import effective
    from snapshot_metadata import finalize,inspect_snapshot
    base=Path(base)
    sys.path.insert(0,str(base.parent/'runtime'))
    from urace.workflow_state import boundary
    state=worker.load(base/'state.json');clock=worker.load(base/'trial-clock.json');pointer=worker.load(base/'active-version.json')
    if state.get('inflight'):raise RuntimeError('Wait for task boundary')
    controls=effective(base)
    if controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals']:raise RuntimeError('Owner disabled automatic Product changes')
    if any(not matches(base/k,v) for k,v in worker.load(base/'harness-manifest.json').items()):raise RuntimeError('Source integrity mismatch')
    audit=worker.load(base/'cross-audit-latest.json',{});rejects={r['version'] for r in audit.get('results',[]) if r.get('status')=='CROSS_PROVIDER_DISAGREEMENT' and r.get('provider')!=r.get('proposer_provider')}
    parent=pointer['version'];text,_=worker.read_version(parent);selected=[];conflicts=[]
    for version in sorted(rejects-withdrawn_versions(base),reverse=True):
        if version>parent:continue
        try:text=inverse_source(version,text);selected.append(version)
        except (ValueError,OSError,KeyError,RuntimeError) as error:conflicts.append({'version':version,'reason':str(error)})
    if not selected:return {'status':'NO_UNAMBIGUOUS_REJECTED_EDITS','additional_native_calls':0,'requires_revalidation':conflicts}
    record={'mode':'EXACT_INVERSE_EDITS','withdrawn_versions':sorted(selected),
       'audit_sha256':hashlib.sha256((base/'cross-audit-latest.json').read_bytes()).hexdigest(),
       'method':'Exact inverses of sealed independently rejected editorial edits; unrelated accepted work retained; not a new quality gain',
       'requires_revalidation':conflicts}
    verify(base,parent,text,record)
    folder=base/'runs'/clock['trial_id']/('spec-'+uuid.uuid4().hex);folder.mkdir(parents=True);atomic(folder/'restoration.json',record)
    (folder/'supporting-audits.json').write_bytes((base/'cross-audit-latest.json').read_bytes())
    support=[]
    for entry in audit.get('results',[]):
        if entry.get('version') not in record['withdrawn_versions']:continue
        receipt=worker.load(Path(entry['artifact'])/'review-native.json',{})
        if receipt:
            atomic(folder/('supporting-call-'+str(entry['version'])+'.json'),receipt)
            support.append({'id':receipt.get('id'),'tokens':receipt.get('tokens'),'wall_seconds':receipt.get('wall_seconds'),'scope':'Pre-existing supporting audit call; not a new launch by restoration'})
    job={'id':folder.name,'trial_id':clock['trial_id'],'product_id':worker.load(base/'contract.json')['product_id'],
       'product':'URACE.md','parent_version':parent,'started_at':worker.utc(),'section':'Corrective exact-content restoration',
       'proposer_provider':'system-exact-restore','quality_policy':'corrective-restore-v1','restoration':record,
       'engine_manifest_sha256':hashlib.sha256((base/'harness-manifest.json').read_bytes()).hexdigest(),
       'outcome':'CORRECTIVE_RESTORE','quality_improvement_claimed':False,'supporting_audit_receipts':support}
    state['inflight']=job;atomic(base/'state.json',state)
    manifest=worker.publish(parent,text,folder,{'method':record['method'],'restoration':record},job,restoration=record)
    job.update(accepted_version=manifest['version'],finished_at=worker.utc());atomic(folder/'report.json',job)
    finalize(base,worker.version(manifest['version']),job)
    state['jobs'].append(job);state.pop('inflight',None);atomic(base/'state.json',state)
    record_withdrawals(base,manifest)
    boundary(base,assess=False)
    inspect_snapshot(worker.version(manifest['version']));return {'status':'RESTORED','new_version':manifest['version'],**record}

if __name__=='__main__':
    with (BASE/'trial.guard').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);print(json.dumps(run(),indent=2))
