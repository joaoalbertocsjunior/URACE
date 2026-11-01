"""Shared atomic resource reservations for managed native executor work."""
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import fcntl,hashlib,json,os,time,uuid,re,math
from common import operations_root, BASE
ROOT=operations_root()
ROOTS=('productive-native-30d-v1','accelerated-productivity-v1','productive-native-30d-v2','autonomous-maintenance-v1','productive-native-30d-v3','pretrial-calibration-v3','productive-native-30d-v4','productive-native-30d-v5','adaptive-effort-study-v1','productive-native-30d-v6','adaptive-effort-study-v2','cli-native-qualification-v1','productive-native-30d-v7','adaptive-effort-study-v3','productive-native-30d-v8','adaptive-effort-study-v4','urace-self-improvement-v1')

def external_roots(root=None):
    root=ROOT if root is None else Path(root)
    return [BASE] if root.resolve()==operations_root().resolve() else []

def registered_roots():
    path=ROOT/'resource-policy.json'
    policy=json.loads(path.read_text()) if path.exists() else {}
    names=policy.get('managed_operation_roots',[])
    if not isinstance(names,list) or any(not isinstance(n,str) or not re.fullmatch(r'(productive|adaptive)-operations-[0-9]{10}',n) for n in names):raise ValueError('Invalid operational root registry')
    return names

def records():
    reservations={};finished={}
    for name in (*ROOTS,*registered_roots(),*external_roots()):
        path=ROOT.parent/name/'ledger.jsonl'
        if not path.exists():continue
        for line in path.read_text().splitlines():
            if not line:continue
            row=json.loads(line)
            if row.get('kind')=='reserved':reservations[row['id']]=row
            elif row.get('kind')=='finished':finished[row['id']]=row
    return list(reservations.values()),finished

def debit(rows,finished,key,default):
    return sum(finished.get(r['id'],{}).get(key) if finished.get(r['id'],{}).get(key) is not None else (r.get('wall_cap_seconds',default) if key=='wall_seconds' else r.get('token_reservation',default)) for r in rows)

def capacity_failure(message):
    text=(message or '').lower()
    return any(x in text for x in ('ordinary usage unavailable before inference','hit your limit','usage limit','rate limit','rate_limit','insufficient credits','quota exceeded','credits exhausted','too many requests'))

def availability_snapshot():
    path=ROOT/'availability-latest.json'
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {}

def capacity_retry(result,observed_finish):
    """Use structured rejected-quota reset evidence; never parse prose or auth."""
    fallback=observed_finish+18900
    resets=[]
    for event in result.get('quota_events') or []:
        if not isinstance(event,dict) or event.get('status')!='rejected':continue
        reset=event.get('resetsAt')
        if type(reset) not in (int,float) or not math.isfinite(reset):continue
        if observed_finish-300<=reset<=observed_finish+604800:resets.append(reset)
    retry=max(observed_finish+60,max(resets)+60) if resets else fallback
    # A known weekly reset must not be shortened into repeated premature probes.
    # The 5h15m fallback applies only when structured reset evidence is absent.
    return {'retry_at_unix':retry,'source':'provider_rejected_quota_reset' if resets else 'fallback_5h15m','availability_proven':False}

def capacity_recovery(provider,recent,finished,snapshot,now):
    if not recent:return None
    latest=recent[-1];result=finished[latest['id']]
    end=latest['at_unix']+max(0,result.get('wall_seconds') or 0)
    if not capacity_failure(result.get('failure')):return None
    # Old native-agent receipts lost the structured failed-turn error. They are
    # unclassified failures, not evidence of an explicit transport violation.
    # A later observed capacity failure plus fresh positive quota can justify
    # one serialized verification; all explicit noncapacity failures still block.
    for previous in (finished[r['id']] for r in recent):
        failure=previous.get('failure')
        legacy_incomplete=(provider=='codex' and previous.get('turn_status')=='failed' and failure=='RuntimeError: Native agent did not complete' and not previous.get('turn_error'))
        if failure and not capacity_failure(failure) and not legacy_incomplete:return None
    if provider=='claude':
        retry=capacity_retry(result,end)
        if retry['source']=='provider_rejected_quota_reset' and now>=retry['retry_at_unix']:
            return {'supersedes_failure_id':latest['id'],'method':'one serialized retry after provider-reported reset plus margin','retry':retry}
        return None
    # Authentication is not evidence of quota. Codex requires fresh quota metadata.
    if provider!='codex' or not isinstance(snapshot,dict):return None
    try:observed=datetime.fromisoformat(snapshot['at']).timestamp()
    except (ValueError,KeyError,TypeError):return None
    if not (0<=now-observed<=1200 and observed>end and now-end>=60):return None
    if snapshot.get('codex',{}).get('ordinaryUsageAllowed') is not True:return None
    return {'metadata_at':snapshot['at'],'supersedes_failure_id':latest['id'],'method':'one serialized inference attempt after fresh positive capacity observation'}

def transport_recovery(provider,recent,finished):
    if provider!='claude' or not recent:return None
    result=finished[recent[-1]['id']]
    failed=[finished[r['id']] for r in recent if finished[r['id']].get('failure')]
    if not result.get('failure') or not failed or any(r.get('subtype')!='error_max_structured_output_retries' for r in failed):return None
    from stream_usage import claude_transport_policy
    current=claude_transport_policy()
    if result.get('transport_policy')==current:return None
    return {'supersedes_failure_id':recent[-1]['id'],'previous_policy':result.get('transport_policy'),'verified_policy':current,'method':'one serialized verification attempt after structured-output policy change; success not assumed'}

def evaluate(provider,reservations,finished,policy,now,next_wall=None,local_config=None,availability=None,bypass_failure_circuit_breaker=False):
    next_wall=next_wall if next_wall is not None else policy.get('reservation_native_seconds',180)
    reasons=[];own=[r for r in reservations if r['provider']==provider and r['at_unix']>=now-18900];daily=[r for r in reservations if r['at_unix']>=now-86400]
    checks=[('shared_total_token_guard',debit(reservations,finished,'tokens',50000)+50000,policy['total_token_guard']),('shared_daily_token_guard',debit(daily,finished,'tokens',50000)+50000,policy['daily_token_guard']),('provider_5h15m_token_guard',debit(own,finished,'tokens',50000)+50000,policy['provider_window_token_guard']),('shared_daily_native_seconds',debit(daily,finished,'wall_seconds',180)+next_wall,policy['daily_native_seconds']),('provider_5h15m_native_seconds',debit(own,finished,'wall_seconds',180)+next_wall,policy['provider_window_native_seconds'])]
    for name,value,limit in checks:
        if limit is not None and value>limit:reasons.append(name)
    # Capacity/output failures from native transport count; artifact acceptance remains independent.
    recent=sorted([r for r in reservations if r['provider']==provider and r['id'] in finished],key=lambda r:r['at_unix'])[-3:]
    capacity=capacity_recovery(provider,recent,finished,availability,now)
    transport=transport_recovery(provider,recent,finished)
    recovery=capacity or transport
    if recovery and any(r['provider']==provider and r['id'] not in finished and now-r['at_unix']<=r.get('wall_cap_seconds',480)+60 for r in reservations):
        reasons.append('capacity_recovery_inflight' if capacity else 'transport_recovery_inflight')
        capacity=transport=recovery=None
    if not bypass_failure_circuit_breaker and len(recent)==3 and all(finished[r['id']].get('failure') for r in recent) and now<recent[-1]['at_unix']+policy['failure_backoff_seconds'] and not recovery:reasons.append('three_consecutive_native_failures')
    if recent:
        last=recent[-1];result=finished[last['id']];failure=(result.get('failure') or '').lower()
        explicit_capacity=capacity_failure(failure)
        observed_finish=last['at_unix']+max(0,result.get('wall_seconds') or 0)
        if explicit_capacity and now<capacity_retry(result,observed_finish)['retry_at_unix'] and not recovery:reasons.append('reported_provider_capacity_backoff')
    same_prompt=sorted([finished[r['id']] for r in reservations if r['provider']==provider and r['id'] in finished and r['at_unix']>=now-600],key=lambda r:r.get('at',''))[-10:]
    if len(same_prompt)==10 and len({r.get('prompt_sha256') for r in same_prompt})==1:reasons.append('repeated_identical_prompt_loop')
    if now>=policy['ends_unix']:reasons.append('study_window_ended')
    if local_config:
        executor=local_config.get('executor',{})
        product=local_config.get('resource_product_id')
        local=[r for r in reservations if product and r.get('product_id')==product]
        limits=[('runtime',local,executor,'max_executor_calls_per_24h','max_executor_calls_per_30d')]
        for entry in executor.get('providers',[]):
            adapter=entry.get('adapter',executor.get('kind','codex-cli'))
            if adapter==provider+'-cli':
                limits.append(('provider',[r for r in local if r['provider']==provider],entry,'max_calls_per_24h','max_calls_per_30d'))
        for label,records,settings,daily,monthly in limits:
            for key,seconds in [(daily,86400),(monthly,2592000)]:
                limit=settings.get(key)
                if limit is not None and sum(r['at_unix']>=now-seconds for r in records)>=limit:reasons.append(label+'_'+key)
    return {'eligible':not reasons,'reasons':reasons,'budget_checks':{name:{'including_next_reservation':value,'ceiling':limit} for name,value,limit in checks},'provider':provider,'capacity_recovery':capacity,'transport_recovery':transport,'capacity_retry':capacity_retry(finished[recent[-1]['id']],recent[-1]['at_unix']+max(0,finished[recent[-1]['id']].get('wall_seconds') or 0)) if recent and capacity_failure(finished[recent[-1]['id']].get('failure')) else None}

def status(provider,next_wall=None):
    with guard():
        policy=json.loads((ROOT/'resource-policy.json').read_text());rows,finished=records()
        return evaluate(provider,rows,finished,policy,time.time(),next_wall=next_wall,local_config=local_configuration(),availability=availability_snapshot())

def local_configuration():
    path=BASE.parent/'runtime/urace/config.json'
    return json.loads(path.read_text()) if path.exists() else None

@contextmanager
def guard():
    with (ROOT/'shared-resource.guard').open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX);yield

def reserve(base,provider,product_override=None,request=None,bypass_failure_circuit_breaker=False):
    if provider not in ('codex','claude'):raise ValueError('Unsupported executor')
    if (BASE.parent/'.migration-in-progress').exists():raise RuntimeError('Owner pause suspends native executor launches')
    if product_override is not None and (not isinstance(product_override,dict) or set(product_override)!={'product_id','product'} or any(not isinstance(v,str) or not v or len(v)>500 for v in product_override.values())):raise ValueError('Invalid declared product identity')
    base=Path(base).resolve()
    if base not in [ROOT.parent/'productive-native-30d-v2',ROOT.parent/'autonomous-maintenance-v1',ROOT.parent/'productive-native-30d-v3',ROOT.parent/'pretrial-calibration-v3',ROOT.parent/'productive-native-30d-v4',ROOT.parent/'productive-native-30d-v5',ROOT.parent/'adaptive-effort-study-v1',ROOT.parent/'productive-native-30d-v6',ROOT.parent/'adaptive-effort-study-v2',ROOT.parent/'cli-native-qualification-v1',ROOT.parent/'productive-native-30d-v7',ROOT.parent/'adaptive-effort-study-v3',ROOT.parent/'productive-native-30d-v8',ROOT.parent/'adaptive-effort-study-v4',ROOT.parent/'urace-self-improvement-v1']+external_roots()+[ROOT.parent/n for n in registered_roots()]:raise ValueError('Unsupported managed worker')
    with guard():
        policy=json.loads((ROOT/'resource-policy.json').read_text());rows,finished=records();now=time.time();wall=int(request['wall'] if request is not None else os.environ.get('URACE_NATIVE_WALL_SECONDS','300'))
        if not 60<=wall<=480:raise ValueError('Invalid native wall allowance')
        local=local_configuration()
        if product_override and local:local={**local,'resource_product_id':product_override['product_id']}
        decision=evaluate(provider,rows,finished,policy,now,next_wall=wall,local_config=local,availability=availability_snapshot(),bypass_failure_circuit_breaker=bypass_failure_circuit_breaker)
        blocking=[r for r in decision.get('reasons',[]) if not bypass_failure_circuit_breaker or r!='three_consecutive_native_failures']
        if blocking:raise RuntimeError('Shared resource guard deferred native launch: '+','.join(blocking))
        identifier=uuid.uuid4().hex
        row={'kind':'reserved','id':identifier,'provider':provider,'logical_job_id':request.get('job_id') if request is not None else os.environ.get('URACE_TRIAL_JOB_ID'),'at_unix':now,'token_reservation':50000,'wall_cap_seconds':wall,'contract_sha256':hashlib.sha256((base/'contract.json').read_bytes()).hexdigest(),'resource_policy_sha256':hashlib.sha256((ROOT/'resource-policy.json').read_bytes()).hexdigest()}
        row['owner_pid']=os.getpid()
        try:row['owner_start_ticks']=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
        except (OSError,IndexError):row['owner_start_ticks']=None
        if decision.get('capacity_recovery'):row['capacity_recovery']=decision['capacity_recovery']
        if decision.get('transport_recovery'):row['transport_recovery']=decision['transport_recovery']
        contract=json.loads((base/'contract.json').read_text())
        if contract.get('product_id'):row.update(product_id=contract['product_id'],product=contract.get('target_product'))
        if product_override:row.update(product_override)
        if contract.get('trial_id'):row['trial_id']=contract['trial_id']
        from urace.authenticated_journal import append_row
        append_row(base/'ledger.jsonl',row)
        return identifier

if __name__=='__main__':
    policy=json.loads((ROOT/'resource-policy.json').read_text());rows,done=records();print(json.dumps({p:evaluate(p,rows,done,policy,time.time()) for p in ('codex','claude')},indent=2))
