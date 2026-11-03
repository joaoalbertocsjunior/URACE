"""Count native usage without treating cached/reasoning subtotals as extra tokens."""
def metadata_safe(value):
    import math
    if type(value) is float and not math.isfinite(value):return None
    if isinstance(value,dict):return {k:metadata_safe(v) for k,v in value.items()}
    if isinstance(value,list):return [metadata_safe(v) for v in value]
    return value

def claude_usage(record):
    models=record.get('model_usage')
    provenance='native_model_usage'
    final=(record.get('partial_usage') or {}).get('final')
    if not models and isinstance(final,dict):
        models=final.get('modelUsage');provenance='retained_provider_final_model_usage'
        if not models:
            fields=('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens');usage=final.get('usage')
            messages=(record.get('partial_usage') or {}).get('completed_message_usage',{})
            zeros=isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]==0 for k in fields)
            message_zero=all(isinstance(m.get('usage'),dict) and all(type(m['usage'].get(k)) is int and m['usage'][k]==0 for k in fields) for m in messages.values())
            if zeros and message_zero and final.get('modelUsage')=={} and type(final.get('duration_api_ms')) in (int,float) and final['duration_api_ms']==0 and type(final.get('total_cost_usd')) in (int,float) and final['total_cost_usd']==0 and (record.get('partial_usage') or {}).get('all_auxiliary_usage_known') is True:
                return {'known':True,'models':{},'tokens':0,'reported_cost_usd':0,'credit_decrement':None,'provenance':'explicit_provider_final_zero_usage'}
    if not models:return {'known':False,'models':{},'tokens':None,'reported_cost_usd':record.get('provider_reported_total_cost_usd')}
    result={}
    if not isinstance(models,dict):raise ValueError('Provider model usage must be an object')
    for name,usage in models.items():
        if not isinstance(name,str) or not name or not isinstance(usage,dict):raise ValueError('Invalid model usage identity')
        fields=('inputTokens','cacheCreationInputTokens','cacheReadInputTokens','outputTokens')
        if any(type(usage.get(k)) is not int or usage[k]<0 for k in fields):raise ValueError('Missing/invalid provider model usage')
        result[name]={'uncached_input_tokens':usage['inputTokens'],'cache_creation_input_tokens':usage['cacheCreationInputTokens'],'cache_read_input_tokens':usage['cacheReadInputTokens'],'output_tokens':usage['outputTokens'],'tokens':sum(usage[k] for k in fields),'reported_api_equivalent_cost_usd':usage.get('costUSD')}
    total=sum(r['tokens'] for r in result.values());lower=partial_lower_bound(record)
    if lower is not None and total<lower:raise ValueError('Final model usage contradicts observed message counters')
    if isinstance(final,dict) and isinstance(final.get('usage'),dict):
        usage=final['usage'];fields=('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')
        if all(type(usage.get(k)) is int and usage[k]>=0 for k in fields) and sum(usage[k] for k in fields)>total:raise ValueError('Final usage contradicts model breakdown')
    return {'known':True,'models':result,'tokens':total,'reported_cost_usd':record.get('provider_reported_total_cost_usd'),'credit_decrement':None,'provenance':provenance}

def codex_usage(record):
    usage=(record.get('usage') or {}).get('total')
    if not usage:return {'known':False,'tokens':None,'reported_cost_usd':None}
    if any(type(usage.get(k)) is not int or usage[k]<0 for k in ('inputTokens','outputTokens','totalTokens')):raise ValueError('Missing/invalid Codex usage counters')
    if usage['inputTokens']+usage['outputTokens']!=usage['totalTokens']:raise ValueError('Inconsistent Codex usage totals')
    return {'known':True,'input_tokens':usage['inputTokens'],'cached_input_tokens_included_in_input':usage.get('cachedInputTokens'),'output_tokens':usage['outputTokens'],'reasoning_tokens_included_in_output':usage.get('reasoningOutputTokens'),'tokens':usage['totalTokens'],'reported_cost_usd':None,'credit_decrement':None}


MEASUREMENT_VERSION='native-usage-v2'

def partial_lower_bound(record):
    partial=record.get('partial_usage')
    if partial is not None and not isinstance(partial,dict):return None
    messages=(partial or {}).get('completed_message_usage',{})
    if not isinstance(messages,dict) or not messages:return None
    total=0
    for identity,value in messages.items():
        if not isinstance(value,dict):return None
        usage=value.get('usage',{})
        if not isinstance(usage,dict):return None
        fields=('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')
        if not isinstance(identity,str) or not identity or any(type(usage.get(k)) is not int or usage[k]<0 for k in fields):return None
        total+=sum(usage[k] for k in fields)
    return total

def projected(rows):
    """Pure derived view: original rows/ledger remain unchanged and failures stay failures."""
    import copy,hashlib,json
    result=[]
    for raw in rows:
        row=raw
        if raw.get('kind')=='finished' and raw.get('tokens') is None and raw.get('provider')=='claude' and raw.get('usage_finality')!='CONTRADICTORY_USAGE':
            row=copy.deepcopy(raw)
            try:details=claude_usage(raw)
            except (ValueError,TypeError,KeyError,AttributeError):details={'known':False}
            lower=partial_lower_bound(raw)
            try:source_hash=hashlib.sha256(json.dumps(raw,sort_keys=True,allow_nan=False).encode()).hexdigest()
            except (ValueError,TypeError):
                row.update(accounting_projection_error='Invalid nonfinite/non-JSON native record; total remains unknown',tokens_lower_bound=None);result.append(row);continue
            proof={'parser_version':MEASUREMENT_VERSION,'source_record_sha256':source_hash,'original_tokens':None,'execution_outcome_unchanged':True}
            if details.get('known'):
                row.update(tokens=details['tokens'],accounting_details=details,accounting_correction={**proof,'kind':'VERIFIED_PROVIDER_COUNTER_RECOVERY','provenance':details.get('provenance')})
            else:row.update(tokens_lower_bound=lower,accounting_correction={**proof,'kind':'INCOMPLETE_TOTAL','provenance':'Completed native message counters only; auxiliary/incomplete work may be missing'})
        result.append(row)
    return result

def reconcile(base):
    """Append idempotent correction provenance, not replacements for native receipts."""
    from pathlib import Path
    import json,fcntl,os,hashlib
    base=Path(base);path=base/'ledger.jsonl'
    if not path.exists():return {'corrections':0,'unknown_totals':0}
    rows=[json.loads(line) for line in path.read_text().splitlines() if line];views=projected(rows);audit=base/'usage-corrections.jsonl';new=0
    with (base/'usage-corrections.guard').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        existing=[json.loads(line) for line in audit.read_text().splitlines()] if audit.exists() else []
        keys={r['id'] for r in existing}
        from urace.authenticated_journal import append_row
        for row in views:
            correction=row.get('accounting_correction')
            if not correction:continue
            record={'receipt_id':row['id'],**correction,'derived_tokens':row.get('tokens'),'tokens_lower_bound':row.get('tokens_lower_bound')};record['id']=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()
            if record['id'] in keys:continue
            append_row(audit,record);keys.add(record['id']);new+=1
    return {'new_audit_records':new,'recovered_totals':sum(bool(r.get('accounting_correction')) and r.get('tokens') is not None for r in views),'unknown_totals':sum(r.get('kind')=='finished' and r.get('tokens') is None for r in views),'measurement_version':MEASUREMENT_VERSION}

def pending_status(rows,now):
    from pathlib import Path
    finished={r['id'] for r in rows if r.get('kind')=='finished'};pending=[]
    for r in rows:
        if r.get('kind')!='reserved' or r['id'] in finished:continue
        age=now-r['at_unix'];pid=r.get('owner_pid');ticks=r.get('owner_start_ticks');alive=None
        if type(pid) is int and ticks:
            try:alive=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]==ticks
            except (OSError,ValueError,IndexError):alive=False
        status='OWNER_GONE_TOTAL_UNKNOWN' if alive is False else 'LIVE_WITHIN_ALLOWANCE' if age<=r.get('wall_cap_seconds',300)+60 else 'OVERDUE_OWNER_ALIVE' if alive is True else 'OVERDUE_LEGACY_OWNER_UNKNOWN'
        pending.append({'id':r['id'],'provider':r.get('provider'),'age_seconds':age,'owner_alive':alive,'status':status,'tokens':None})
    return pending


def settle(record,provider):
    """Close native accounting without calling an interrupted counter snapshot final."""
    try:details=(claude_usage if provider=='claude' else codex_usage)(record)
    except (ValueError,TypeError,KeyError,AttributeError) as error:details={'known':False,'reason':type(error).__name__+': '+str(error)[:200]}
    if record.get('inference_requested') is False:
        lower=partial_lower_bound(record)
        contradictory=details.get('tokens') if details.get('known') else lower
        if type(contradictory) is int and contradictory>0:
            record['tokens_lower_bound']=contradictory;record['tokens']=None;record['usage_finality']='CONTRADICTORY_USAGE'
            details={'known':False,'tokens':None,'reason':'Nonzero counters contradict explicit no-inference flag','reported_tokens_lower_bound':record['tokens_lower_bound']}
        else:
            record['tokens']=0;record['usage_finality']='NO_INFERENCE_REQUESTED';details={'known':True,'tokens':0,'provenance':'Explicit adapter flag: no inference dispatch was attempted','credit_decrement':None}
    elif provider=='codex' and record.get('failure') and record.get('turn_status')!='completed':
        lower=details.get('tokens') if details.get('known') else None;record['tokens_lower_bound']=lower;record['tokens']=None;record['usage_finality']='INTERRUPTED_COUNTER_SNAPSHOT';details={**details,'known':False,'tokens':None,'reported_tokens_lower_bound':lower}
    elif details.get('known'):
        record['tokens']=details['tokens']
        record['usage_finality']='PROVIDER_FINAL_USAGE'
    else:record['usage_finality']='UNKNOWN_OR_PARTIAL'
    record['accounting_details']=details
    return record
