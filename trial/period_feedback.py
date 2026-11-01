"""Descriptive period comparisons; never turn sparse editorial proxies into value proof."""
from datetime import datetime

PERIODS={'3h':10800,'day':86400,'week':604800,'month':2592000}

def percentiles(values):
    values=sorted(values)
    def at(p):
        i=(len(values)-1)*p;lower=int(i)
        return values[lower]+(values[min(lower+1,len(values)-1)]-values[lower])*(i-lower)
    return {'samples':len(values),'p50':at(.5) if len(values)>=5 else None,
            'p90':at(.9) if len(values)>=20 else None,'p95':at(.95) if len(values)>=40 else None,
            'method':'Linear interpolation; sparse percentiles withheld; descriptive, not causal'}

def compare(rows,jobs,now,period='3h'):
    seconds=PERIODS[period]
    def window(start,end):
        selected=[r for r in rows if r.get('kind')=='finished' and r.get('at') and start<=datetime.fromisoformat(r['at']).timestamp()<end]
        done=[j for j in jobs if j.get('finished_at') and start<=datetime.fromisoformat(j['finished_at']).timestamp()<end]
        tokens=[r['tokens'] for r in selected if r.get('tokens') is not None]
        wall=[r['wall_seconds'] for r in selected if r.get('wall_seconds') is not None]
        accepted=sum(j.get('outcome')=='ACCEPTED_EDITORIAL_IMPROVEMENT' for j in done)
        return {'finished_native_calls':len(selected),'completed_tasks':len(done),'accepted_editorial_improvements':accepted,
                'known_tokens':sum(tokens),'unknown_usage_calls':len(selected)-len(tokens),
                'known_executor_seconds':sum(wall),'token_percentiles':percentiles(tokens),
                'executor_seconds_percentiles':percentiles(wall),
                'tokens_per_accepted_improvement':sum(tokens)/accepted if accepted and len(tokens)==len(selected) else None,
                'accepted_improvements_per_hour':3600*accepted/seconds if done else None}
    current=window(now-seconds,now);previous=window(now-2*seconds,now-seconds)
    profiles={}
    fields=('product_id','provider','requested_model','effort','client_version')
    identities={tuple(r.get(k,'UNKNOWN') for k in fields) for r in rows if r.get('kind')=='finished'}
    for identity in sorted(identities,key=str):
        selected=[r for r in rows if r.get('kind')=='finished' and tuple(r.get(k,'UNKNOWN') for k in fields)==identity]
        def inventory(start,end):
            rs=[r for r in selected if r.get('at') and start<=datetime.fromisoformat(r['at']).timestamp()<end]
            known=[r['tokens'] for r in rs if type(r.get('tokens')) is int and r['tokens']>=0]
            wall=[r['wall_seconds'] for r in rs if type(r.get('wall_seconds')) in (int,float) and r['wall_seconds']>=0]
            return {'finished_attempts':len(rs),'failed_attempts':sum(bool(r.get('failure')) for r in rs),
                    'known_tokens':sum(known),'total_tokens':sum(known) if rs and len(known)==len(rs) else None,
                    'unknown_usage_attempts':len(rs)-len(known),'known_native_seconds':sum(wall),
                    'token_percentiles':percentiles(known),'credit_decrement':None}
        profiles[str(identity)]={'requested_identity':dict(zip(('product_id','provider','model','effort','client_version'),identity)),
                'current':inventory(now-seconds,now),'previous':inventory(now-2*seconds,now-seconds),
                'qualified_gain_claim':False,'runtime_identity':'Not bound by period inventory; use frozen study cohorts'}
    deltas={}
    for key in ('accepted_editorial_improvements','known_tokens','known_executor_seconds','tokens_per_accepted_improvement','accepted_improvements_per_hour'):
        a,b=current[key],previous[key]
        deltas[key]={'current':a,'previous':b,'change_pct':100*(a-b)/b if a is not None and b not in (None,0) else None}
    return {'schema':'operational-period-feedback-v2','by_requested_profile':profiles,'qualified_gain_claim':False,'aggregate_token_totals_are_profile_qualified':False,'period':period,'window_seconds':seconds,'current':current,'previous':previous,'deltas':deltas,
            'window_attribution':'Native receipts by recorded start time; tasks by completion. Boundary overlap and task mix prevent causal inference.',
            'scope':'Operational inventory of supplied rows, potentially spanning models, efforts, clients and execution versions. Aggregate consumption changes are not qualified efficiency gains. Use frozen matched per-profile studies; editorial acceptance is not functional or real-user benefit.'}
