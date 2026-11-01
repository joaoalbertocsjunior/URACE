"""Product-scoped resource reporting; zero inference calls, append-only provenance."""
from datetime import datetime,timezone
from common import BASE,events
from spec_trial import load,resource_metrics

def efficiency(metrics,accepted,completed,elapsed):
    complete=not metrics['missing_usage'];tokens=metrics['known_tokens']
    return {'completed_tasks':completed,'accepted_improvements':accepted,'acceptance_rate_pct':100*accepted/completed if completed else None,'tokens_per_accepted_improvement':tokens/accepted if accepted and complete else None,'accepted_improvements_per_million_tokens':1e6*accepted/tokens if tokens and complete else None,'elapsed_seconds_per_accepted_improvement':elapsed/accepted if accepted else None,'accepted_improvements_per_elapsed_hour':3600*accepted/elapsed if elapsed>0 and completed else None,'completed_review_tasks_per_elapsed_hour':3600*completed/elapsed if elapsed>0 and completed else None,'usage_complete':complete,'measurement_limit':'Acceptance is bounded editorial review, not independently proven user benefit. Compare matched tasks with fixed validation; per-executor token units differ. Rejected-attempt costs are included.'}

def report(product,scope='epoch',executor='all',*,_snapshot=None):
    if executor not in ('all','codex','claude'):raise ValueError('Unknown executor: '+executor)
    registry=_snapshot['registry'] if _snapshot is not None else load(BASE/'products.json',{})
    matches=[p for p in registry.get('products',[]) if product in (p['id'],p['name'])]
    if len(matches)!=1:raise ValueError('Unknown or ambiguous product: '+product)
    item=matches[0];rows=(list(_snapshot['by_product'].get(item['id'],[]))+list(_snapshot['by_product'].get(None,[])) if item.get('legacy_ledger_binding') else list(_snapshot['by_product'].get(item['id'],[]))) if _snapshot is not None else events();selected=[];legacy=0
    from core_resources import events as core_events
    clock=_snapshot['clock'] if _snapshot is not None else load(BASE/'trial-clock.json',{})
    epoch_for_core=_snapshot['epoch'] if _snapshot is not None else load(BASE/'accounting-epoch.json',{})
    rows += core_events(BASE,item['id'],clock.get('trial_id') if scope=='trial' else None,
                        epoch_for_core.get('started_unix') if scope in ('trial','epoch') else None)
    for row in rows:
        identity=row.get('product_id')
        if identity==item['id']:selected.append(row)
        elif identity is None and item.get('legacy_ledger_binding'):
            # This ledger was created solely for this target; report inferred attribution.
            selected.append(row);legacy+=1
    if executor!='all':
        ids={r['id'] for r in selected if r.get('kind')=='reserved' and r['provider']==executor}
        selected=[r for r in selected if r.get('id') in ids]
    clock=_snapshot['clock'] if _snapshot is not None else load(BASE/'trial-clock.json',{})
    if scope=='trial':
        if not clock.get('trial_id'):raise ValueError('No identified current trial')
        selected=[r for r in selected if r.get('trial_id')==clock['trial_id']]
    legacy=sum(r.get('product_id') is None for r in selected)
    epoch=(_snapshot['epoch'] if _snapshot is not None else load(BASE/'accounting-epoch.json')) if scope in ('epoch','trial') else None
    if epoch and epoch.get('product_id') not in (None,item['id']):epoch=None
    jobs=list(_snapshot['jobs']) if _snapshot is not None else load(BASE/'state.json',{'jobs':[]})['jobs']
    if item.get('work_root'):
        from pathlib import Path
        work=Path(item['work_root']).resolve()
        if not work.is_relative_to((BASE/'project-work').resolve()):raise ValueError('Work record directory escaped')
        jobs += [load(p) for p in work.glob('runs/*/result.json') if load(p).get('complete')]
    if scope=='lifetime':
        if _snapshot is not None:all_jobs=dict(_snapshot['historical_jobs'])
        else:
            archived=sorted(set((BASE/'history').glob('state*.json')) | set((BASE/'history').glob('state.json.before-*')))
            all_jobs={j['id']:j for p in archived if p.is_file() for j in load(p,{'jobs':[]}).get('jobs',[])}
        all_jobs.update({j['id']:j for j in jobs});jobs=list(all_jobs.values())
    if scope=='trial':jobs=[j for j in jobs if j.get('trial_id')==clock['trial_id']]
    if epoch:jobs=[j for j in jobs if j['id'] not in epoch['excluded_jobs'] and j.get('started_at','')>=epoch['started_at']]
    jobs=[j for j in jobs if j.get('product_id',registry.get('state_product_id'))==item['id']]
    if executor!='all':
        logical=[r.get('logical_job_id','') for r in selected if r.get('kind')=='reserved']
        jobs=[j for j in jobs if any(str(x or '').startswith(j['id']+'-') or str(x or '').startswith('project:'+j['id']+':') for x in logical)]
    from quality_restore import withdrawn_versions
    withdrawn=_snapshot['withdrawn'] if _snapshot is not None else withdrawn_versions(BASE)
    historical=sum(j.get('outcome') in ('ACCEPTED_EDITORIAL_IMPROVEMENT','VALIDATED_PROJECT_WORK') for j in jobs)
    metrics=resource_metrics(selected,epoch);accepted=sum(j.get('outcome') in ('ACCEPTED_EDITORIAL_IMPROVEMENT','VALIDATED_PROJECT_WORK') and not (j.get('trial_id')==clock.get('trial_id') and j.get('accepted_version') in withdrawn) for j in jobs)
    starts=[r['at_unix'] for r in selected if r.get('kind')=='reserved'];now=datetime.now(timezone.utc);started=epoch['started_unix'] if epoch else min(starts,default=now.timestamp());elapsed=max(0,now.timestamp()-started)
    output_quality=__import__('output_quality').summary(jobs)
    return {'output_correctness_pct':output_quality['mean_primary_correctness_pct_on_measured'] if not output_quality['quality_unmeasured_workflows'] else None,'output_robustness_pct':output_quality['mean_robustness_pct_on_measured'] if not output_quality['quality_unmeasured_workflows'] else None,'quality_gated_delivery_rate_pct':100*output_quality['quality_gated_deliveries']/len(jobs) if jobs else None,'at':now.isoformat(),'product_id':item['id'],'product':item['name'],'executor':executor,'scope':scope,'trial_id':clock.get('trial_id') if scope=='trial' else None,'accounting_epoch':epoch,'elapsed_seconds':elapsed,**metrics,'completed_tasks':len(jobs),'accepted_improvements':accepted,'historical_accepted_improvements':historical,'withdrawn_editorial_versions':sorted(withdrawn),'rejected_or_deferred':sum(j.get('outcome')=='REJECTED_OR_DEFERRED' for j in jobs),'output_quality':output_quality,'quality_scope':'Product run/phase records; matched study comparisons remain separate','efficiency':efficiency(metrics,accepted,len(jobs),elapsed),'tokens_per_accepted_improvement':metrics['known_tokens']/accepted if accepted and not metrics['missing_usage'] else None,'legacy_events_attributed_by_explicit_ledger_binding':legacy,'counter_interpretation':'Current-trial scope excludes prior trials. Lifetime explicitly includes archived trials. Measured native tokens include rejected attempts; unknown usage remains missing; not subscription billing. Executor-filtered tasks mean participation, not causal credit; provider task counts may overlap.','historical_ledgers_preserved':True}

def overall(scope='epoch',executor='all'):
    registry=load(BASE/'products.json',{});items=registry.get('products',[])
    if len({p['id'] for p in items})!=len(items):raise ValueError('Duplicate product identity in registry')
    if sum(bool(p.get('legacy_ledger_binding')) for p in items)>1:raise ValueError('Ambiguous legacy ledger binding')
    # Freeze shared reporting inputs once; never cache authoritative admission.
    from quality_restore import withdrawn_versions
    by_product={}
    for row in events():by_product.setdefault(row.get('product_id'),[]).append(row)
    context={'registry':registry,'by_product':by_product,'clock':load(BASE/'trial-clock.json',{}),'epoch':load(BASE/'accounting-epoch.json',{}),'jobs':load(BASE/'state.json',{'jobs':[]})['jobs'],'withdrawn':withdrawn_versions(BASE),'historical_jobs':{}}
    if scope=='lifetime':
        archived=sorted(set((BASE/'history').glob('state*.json')) | set((BASE/'history').glob('state.json.before-*')))
        context['historical_jobs']={j['id']:j for path in archived if path.is_file() for j in load(path,{'jobs':[]}).get('jobs',[])}
    reports=[report(p['id'],scope,executor,_snapshot=context) for p in items]
    keys=('native_calls','known_tokens','missing_usage','known_executor_seconds','inflight_calls','finished_unknown_usage','reported_tokens_lower_bound','completed_tasks','accepted_improvements','rejected_or_deferred')
    totals={k:sum(p[k] for p in reports) for k in keys}
    providers={name:{k:sum(p['providers'][name][k] for p in reports) for k in ('native_calls','known_tokens','missing_usage','known_executor_seconds','inflight_calls','finished_unknown_usage','reported_tokens_lower_bound')} for name in ('codex','claude')}
    elapsed=max([p['elapsed_seconds'] for p in reports],default=0)
    return {'at':datetime.now(timezone.utc).isoformat(),'product':'All registered products','product_count':len(reports),'executor':executor,'scope':scope,'elapsed_seconds':elapsed,**totals,'providers':providers,'products':reports,'output_quality_by_product':{p['product_id']:p['output_quality'] for p in reports},'efficiency':efficiency(totals,totals['accepted_improvements'],totals['completed_tasks'],elapsed),'tokens_per_accepted_improvement':totals['known_tokens']/totals['accepted_improvements'] if totals['accepted_improvements'] and not totals['missing_usage'] else None,'coverage':'Registered products in the specification-trial ledger; earlier external trials remain separately archived, not silently attributed','historical_ledgers_preserved':True}
