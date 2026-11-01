"""Bounded diagnostic, separately attributed; never productive qualification proof."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,subprocess,sys,time,fcntl
from common import BASE,atomic

INTERVAL=18900
PRODUCT={'product_id':'urace-qualification-preflight','product':'Claude qualification transport preflight'}

def step(base=BASE):
    base=Path(base)
    with (base/'claude-preflight.guard').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=base/'claude-preflight-latest.json'
        previous=json.loads(state.read_text()) if state.exists() else {}
        if time.time()<previous.get('next_due_unix',0):return previous
        # Run in a subprocess: provider environment overrides must not race other workers.
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--probe'],capture_output=True,text=True,timeout=150)
        try:value=json.loads(result.stdout)
        except ValueError:value={'status':'FAILED','failure':'Preflight subprocess returned no valid diagnostic','returncode':result.returncode,'inference_calls':None}
        value.update(next_due_unix=time.time()+INTERVAL,assessment_evidence=False)
        atomic(state,value);return value

def reusable_receipt(rows,model,effort,now):
    candidates=[]
    for row in rows:
        if row.get('provider')!='claude' or row.get('requested_model')!=model or row.get('effort')!=effort:continue
        try:at=datetime.fromisoformat(row['at']).timestamp()
        except (KeyError,ValueError,TypeError):continue
        if 0<=now-at<=INTERVAL:candidates.append((at,row))
    if not candidates:return None
    latest=max(candidates,key=lambda x:x[0])[1]
    return latest if latest.get('failure') is None and latest.get('inference_requested') is True and latest.get('returncode')==0 and latest.get('is_error') is False and latest.get('subtype')=='success' else None

def probe():
    import resource_governor as governor
    from controls import effective
    from accounting import settle,metadata_safe
    import providers
    controls=effective(BASE)
    if controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals'] or not controls['executors']['claude']['enabled']:
        return {'status':'DEFERRED','reasons':['OWNER_CONTROLS'],'inference_calls':0}
    decision=governor.status('claude',next_wall=120)
    if not decision['eligible']:return {'status':'DEFERRED','reasons':decision.get('reasons',[]),'inference_calls':0}
    from spec_trial import eligible
    admitted,waits=eligible()
    if 'claude' not in admitted:return {'status':'DEFERRED','reasons':[waits.get('claude','ORDINARY_ADMISSION')],'inference_calls':0}
    model=controls['executors']['claude']['model'];effort=controls['executors']['claude']['native_effort']
    with governor.guard():_,finished=governor.records()
    existing=reusable_receipt(finished.values(),model,effort,time.time())
    if existing:return {'status':'VERIFIED_EXISTING_NATIVE_TRANSPORT','receipt_id':existing['id'],'receipt_product_id':existing.get('product_id'),'inference_calls':0,'assessment_evidence':False,'scope':'Reuses a recent successful exact requested-profile native receipt; no relabeling or duplicate accounting'}
    prompt='Diagnostic transport preflight only. No tools. Return the required JSON object with source exactly URACE_PREFLIGHT_OK and notes exactly diagnostic only. Do not perform other work.'
    identifier=governor.reserve(BASE,'claude',product_override=PRODUCT,request={'job_id':'claude-preflight','wall':120})
    work=BASE/'work'/identifier;work.mkdir()
    record={'kind':'finished','id':identifier,'provider':'claude',**PRODUCT,'trial_id':json.loads((BASE/'trial-clock.json').read_text())['trial_id'],'at':datetime.now(timezone.utc).isoformat(),'requested_model':model,'effort':effort,'role':'DIAGNOSTIC_ONLY','tokens':None,'failure':None,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'wall_limit_seconds':120}
    os.environ['URACE_TRIAL_MODEL']=model;os.environ['URACE_NATIVE_WALL_SECONDS']='120'
    started=time.monotonic();value=None
    try:
        value,envelope=providers.claude(prompt,work,record)
        if value!={'source':'URACE_PREFLIGHT_OK','notes':'diagnostic only'}:raise ValueError('Preflight output mismatch')
    except Exception as error:record['failure']=type(error).__name__+': '+str(error)[:300]
    finally:
        record['wall_seconds']=time.monotonic()-started;settle(record,'claude');record=metadata_safe(record);atomic(BASE/'transport'/(identifier+'.json'),record)
        with governor.guard():
            from urace.authenticated_journal import append_row
            append_row(BASE/'ledger.jsonl',record)
    return {'status':'VERIFIED' if not record['failure'] else 'FAILED','receipt':record,'inference_calls':int(record.get('inference_requested') is True),'assessment_evidence':False}

if __name__=='__main__':
    try:print(json.dumps(probe()))
    except (OSError,ValueError,RuntimeError) as error:print(json.dumps({'status':'DEFERRED_OR_ERROR','error':str(error)[:300],'inference_calls':None}))
