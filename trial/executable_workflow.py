"""Bounded compile/public-example repair. Held-out feedback never enters prompts."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,time
from common import atomic
from executable_cases import public_cases
from executable_sandbox import validate_source,execute,SandboxInfrastructureError
from executable_scores import grade

def run(provider,prompt,folder,held_out,invoke,admit,profile,max_repairs=1,training=None):
    if type(max_repairs) is not int or not 0<=max_repairs<=1:raise ValueError('At most one compiler/public-example repair')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);training=public_cases() if training is None else training;required={c['function'] for c in [*training,*held_out]};attempts=[];receipts=[];first=None;last_error=None;source=None;public_result=None
    started=time.monotonic()
    for attempt in range(max_repairs+1):
        label='implementation' if attempt==0 else 'repair-1'
        instruction=prompt+'\nPUBLIC TRAINING EXAMPLES (not held-out acceptance): '+json.dumps(training,sort_keys=True)
        if attempt:
            instruction+='\nCorrect your prior module using only this compiler/public-example feedback. Return a complete replacement module. Do not change the task.\nPRIOR_SOURCE='+json.dumps(source)+'\nPUBLIC_FEEDBACK='+json.dumps(last_error)
        receipt={};attempt_started=time.monotonic();item={'index':attempt,'label':label}
        try:
            admit()
            answer=invoke(provider,instruction,folder,label)
            receipt=json.loads((folder/(label+'-native.json')).read_text())
            if receipt.get('requested_model')!=profile['model'] or receipt.get('effort')!=profile['native_effort']:raise RuntimeError('Native profile changed during generation')
            if set(answer)!={'python_source'}:raise ValueError('Expected python_source JSON field')
            source=answer['python_source'];path=folder/('attempt-'+str(attempt)+'.py');path.write_text(source)
            validate_source(source,required);public_result=execute(path,training);atomic(folder/('attempt-'+str(attempt)+'-public-execution.json'),public_result)
            public_grade=grade(public_result,training);item['public_grade']=public_grade
            if not public_grade['validated_delivery']:
                failed={key for key,ok in public_grade['case_results'].items() if not ok}
                observed={r['id']:r for r in public_result['results']}
                last_error={'kind':'PUBLIC_EXAMPLE_FAILURE','examples':[{'case':c,'observed':observed[c['id']]} for c in training if c['id'] in failed]}
            else:last_error=None
        except Exception as error:
            if (folder/(label+'-native.json')).exists():receipt=json.loads((folder/(label+'-native.json')).read_text())
            item['error']=type(error).__name__+': '+str(error)[:500]
            last_error={'kind':type(error).__name__,'detail':str(error)[:500]}
            if isinstance(error,SandboxInfrastructureError) or receipt.get('failure') or not receipt or str(error).startswith('Native profile changed'):
                item['nonrepairable']=True
        item['seconds']=time.monotonic()-attempt_started;item['receipt_id']=receipt.get('id');attempts.append(item)
        if receipt:receipts.append(receipt)
        if first is None:first={'public_passed':bool(item.get('public_grade',{}).get('validated_delivery')),'public_grade':item.get('public_grade'),'error':item.get('error'),'source':str(folder/'attempt-0.py') if (folder/'attempt-0.py').exists() else None}
        atomic(folder/'workflow-progress.json',{'attempts':attempts,'first_pass':first,'repair_limit':max_repairs,'held_out_feedback_disclosed':False})
        if item.get('nonrepairable') or last_error is None:break
    result={'grade':None,'status':'DEFERRED_OR_TRANSPORT_FAILURE','first_pass':first,'attempts':attempts,'repairs':max(0,len(attempts)-1),'native_receipts':receipts,'held_out_feedback_disclosed':False}
    if attempts[-1].get('nonrepairable'):
        result['error']=attempts[-1]['error']
        if result['error'].startswith('SandboxInfrastructureError:'):result['status']='EVALUATION_INFRASTRUCTURE_FAILURE'
    else:
        try:
            validate_source(source,required);path=folder/'solution.py';path.write_text(source)
            # Evaluate the final, unchanged artifact. No hidden result can trigger repair.
            public_result=execute(path,training);hidden_result=execute(path,held_out)
            atomic(folder/'public-execution.json',public_result);atomic(folder/'execution.json',hidden_result)
            combined={'status':'EXECUTED','results':public_result['results']+hidden_result['results']}
            result.update(grade=grade(combined,training+held_out),held_out_grade=grade(hidden_result,held_out),status='EVALUATED',source_sha256=hashlib.sha256(source.encode()).hexdigest())
        except SandboxInfrastructureError as error:result.update(error=str(error),status='EVALUATION_INFRASTRUCTURE_FAILURE')
        except Exception as error:result.update(error=type(error).__name__+': '+str(error)[:500],status='INVALID_DELIVERED_ARTIFACT',grade=grade({'status':'INVALID_DELIVERED_ARTIFACT'},training+held_out))
    known=all(type(r.get('tokens')) is int and r['tokens']>=0 for r in receipts)
    result.update(tokens=sum(r['tokens'] for r in receipts) if receipts and known else None,
                  native_seconds=sum(r.get('wall_seconds') or 0 for r in receipts),native_receipt_id=receipts[-1].get('id') if receipts else None,
                  native_receipt_ids=[r['id'] for r in receipts if r.get('id')],native_failure=receipts[-1].get('failure') if receipts else None,
                  end_to_end_seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat())
    atomic(folder/'workflow-result.json',result);return result
