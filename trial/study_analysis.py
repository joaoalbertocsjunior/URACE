"""Outcome attribution and provider-local comparisons; never pool token currencies."""
from pathlib import Path
import json,math,time,hashlib

def category(row):
 failures=[str(r.get('failure') or '') for r in row.get('native_receipts',[])]
 text=' '.join(failures+[str(a.get('development',{}).get('stderr','')) for a in row.get('attempts',[])]).lower()
 if row.get('fault_injection'):return 'INJECTED_PROVIDER_OUTAGE'
 if row.get('waits') and not row.get('delivered',row.get('validated')):return 'ACTUAL_PROVIDER_AVAILABILITY'
 if 'specification reference protocol' in text:return 'REFERENCE_PROTOCOL_FAILURE'
 if 'specification reference modified' in text:return 'REFERENCE_MUTATION'
 if any(x in text for x in ('hit your limit','rate limit','quota','capacity','usage unavailable')):return 'ACTUAL_PROVIDER_AVAILABILITY'
 if row.get('delivered',row.get('validated')):return 'DELIVERED'
 if row.get('publication')=='OWNER_EDIT_CONFLICT':return 'OWNER_EDIT_CONFLICT'
 if row.get('publication')=='RESOURCE_BOUND_EXCEEDED' or row.get('status')=='ELAPSED_BUDGET_EXHAUSTED':return 'ELAPSED_EXHAUSTED'
 if row.get('status')=='REJECTED_BY_QUALITY':return 'OUTPUT_QUALITY_REJECTED'
 if row.get('status')=='REJECTED_BY_ACCEPTANCE':return 'HELDOUT_REJECTED'
 if any(x in text for x in ('sandbox','docker','mcp','code-mode host')):return 'TOOL_OR_SANDBOX_FAILURE'
 if failures and any(failures):return 'NATIVE_TRANSPORT_FAILURE'
 if row.get('status')=='DEVELOPMENT_FAILED':return 'DEVELOPMENT_REJECTED'
 return 'DEFERRED_OR_UNKNOWN'

def percentile(xs,p):
 if not xs:return None
 xs=sorted(xs);a=(len(xs)-1)*p;i=int(a);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(a-i)

def resources(rows):
 from urace.work_policy import outcomes
 first=min((r['queued_unix'] for r in rows),default=time.time());last=max((r['queued_unix']+r['elapsed_seconds'] for r in rows),default=first+.000001);out=outcomes(rows,max(.000001,last-first))
 from period_feedback import percentiles
 scoped_percentiles=percentiles([r['elapsed_seconds'] for r in rows])
 out.update(workflow_seconds_percentiles=scoped_percentiles,sum_workflow_seconds=sum(r['elapsed_seconds'] for r in rows),p50_workflow_seconds=scoped_percentiles['p50'],p90_workflow_seconds=scoped_percentiles['p90'],categories={k:sum(category(r)==k for r in rows) for k in sorted({category(r) for r in rows})})
 receipts={r['id']:r for row in rows for r in row.get('native_receipts',[])};parts=[]
 for r in receipts.values():
  d=r.get('accounting_details') or {};provider=r.get('provider');part={'provider':provider,'known':d.get('known',False),'native_session_seconds':r.get('wall_seconds')}
  if provider=='codex':
   total=d.get('input_tokens');cached=d.get('cached_input_tokens_included_in_input');part.update(cached_read_tokens=cached,uncached_input_tokens=total-cached if type(total) is int and type(cached) is int else None,cache_creation_tokens=0,output_tokens=d.get('output_tokens'))
  else:
   models=d.get('models',{}).values()
   for target,key in [('cached_read_tokens','cache_read_input_tokens'),('cache_creation_tokens','cache_creation_input_tokens'),('uncached_input_tokens','uncached_input_tokens'),('output_tokens','output_tokens')]:part[target]=sum(x[key] for x in models) if d.get('known') and all(type(x.get(key)) is int for x in models) else None
  parts.append(part)
 for key in ('cached_read_tokens','cache_creation_tokens','uncached_input_tokens','output_tokens','native_session_seconds'):
  values=[r.get(key) for r in parts];out[key]=sum(values) if values and all(type(v) in (int,float) for v in values) else None
 tool_totals=[]
 for r in receipts.values():
  path=Path(r.get('artifact_directory','/nonexistent'))/'tools.jsonl'
  if path.exists():tool_totals.append(sum(json.loads(line).get('seconds',0) for line in path.read_text().splitlines()))
 out['native_tool_seconds']=sum(tool_totals) if len(tool_totals)==len(receipts) and receipts else None
 out['non_tool_session_seconds']=max(0,out['native_session_seconds']-out['native_tool_seconds']) if out['native_session_seconds'] is not None and out['native_tool_seconds'] is not None else None
 out['session_timing_interpretation']='Native session includes startup, inference and tools; non-tool remainder is derived, not pure inference time'
 out['development_check_seconds']=sum(a.get('development',{}).get('seconds',0) for r in rows for a in r.get('attempts',[]));out['validation_seconds']=sum(r.get('timing',{}).get('baseline_seconds',0)+r.get('timing',{}).get('acceptance_seconds',0) for r in rows);out['validation_timing_complete']=all(all(k in r.get('timing',{}) for k in ('baseline_seconds','acceptance_seconds')) for r in rows)
 gaps=[r.get('phase_scheduling_gap_seconds') for r in rows];out['phase_scheduling_gap_seconds']=sum(gaps) if gaps and all(type(g) in (int,float) for g in gaps) else None;out['phase_timing_complete']=bool(rows) and all(r.get('phase_timing_complete') for r in rows)
 for stage in ('preparation_seconds','admission_seconds','context_preparation_seconds','executor_invocation_seconds','publication_seconds'):
  values=[r.get('timing',{}).get(stage) for r in rows];out[stage]=sum(values) if values and all(type(v) in (int,float) for v in values) else None
 out['stage_timing_interpretation']='Executor invocation contains native session and its tools; these nested times must not be summed. Other measured stages exclude that invocation; residual persistence/dispatch time remains unattributed.'
 out['credit_decrement']=None;return out

def compare(pairs,minimum=30,required_families=None):
 rows=[r for pair in pairs for r in pair];a=resources([a for a,z in pairs]);z=resources([z for a,z in pairs]);losses=sum(bool(a.get('validated')) and not z.get('validated') for a,z in pairs)
 ratio=lambda key:z[key]/a[key] if a.get(key) and z.get(key) is not None else None
 tr=ratio('known_tokens') if a['usage_complete'] and z['usage_complete'] else None;lat=ratio('sum_workflow_seconds');per=ratio('tokens_per_validated_delivery')
 from output_quality import summary as quality_summary
 quality_profiles={'standalone':quality_summary([a for a,z in pairs]),'urace':quality_summary([z for a,z in pairs])}
 quality_complete=bool(pairs) and all(r.get('acceptance',{}).get('quality',{}).get('gate_passed') is True for pair in pairs for r in pair)
 from collections import Counter
 counts=Counter(a['family'] for a,z in pairs)
 enough=len(pairs)>=minimum and (not required_families or all(counts[f]>=6 for f in required_families))
 profiles={(r.get('provider'),r.get('effort')) for r in rows}
 enough=enough and len(profiles)==1
 # Every comparison is within one actual provider; quota-contaminated pairs excluded by caller.
 quality=losses==0 and z['validated']>=a['validated'] and a['validated']>0;benefit=bool(enough and quality and quality_complete and tr is not None and lat is not None and ((tr<=.8 and lat<=1.05) or (lat<=.8 and tr<=1.05) or (z['validated']>a['validated'] and per is not None and per<=1 and lat<=1.05)))
 quality_delta={}
 for name in ('mean_primary_correctness_pct_on_measured','mean_robustness_pct_on_measured'):
  first,second=quality_profiles['standalone'].get(name),quality_profiles['urace'].get(name);quality_delta[name]=second-first if first is not None and second is not None else None
 return {'quality_delta_percentage_points':quality_delta,'pairs':len(pairs),'standalone':a,'urace':z,'token_change_pct':100*(tr-1) if tr is not None else None,'elapsed_change_pct':100*(lat-1) if lat is not None else None,'quality':quality_profiles,'quality_complete':quality_complete,'paired_delivery_losses':losses,'enough_coverage':enough,'observed_bounded_advantage':benefit,'interpretation':'Descriptive matched engineering scenarios, including failed-attempt costs; not market fit, causal credit attribution or billing'}

def assessment(rows):
 keys=lambda r:(r['provider'],r['family'],r['effort'],r['repeat']);direct={keys(r):r for r in rows if r['arm']=='standalone'};pairs=[(direct[keys(z)],z) for z in rows if z['arm']=='urace' and keys(z) in direct]
 ordinary=[(a,z) for a,z in pairs if a['family']!='failover' and a.get('actual_providers')==z.get('actual_providers')==[a['provider']]]
 groups={p:compare([(a,z) for a,z in ordinary if a['provider']==p],required_families={'navigation','receipts','recovery','requirements_change','interruption'}) for p in sorted({r['provider'] for r in rows})}
 for provider,group in groups.items():
  if len({r['effort'] for r in rows if r['provider']==provider})>1:
   group.update(token_change_pct=None,elapsed_change_pct=None,observed_bounded_advantage=False,interpretation='Mixed-effort diagnostic rollup; gains withheld. Inspect ordinary_by_profile.')
 profiles={p+':'+e:compare([(a,z) for a,z in ordinary if a['provider']==p and a['effort']==e],required_families={'navigation','receipts','recovery','requirements_change','interruption'}) for p,e in sorted({(r['provider'],r['effort']) for r in rows})}
 return {'ordinary_by_profile':profiles,'ordinary_by_provider':groups,'injected_continuity':{'pairs':sum(a['family']=='failover' for a,z in pairs),'managed_deliveries':sum(a['family']=='failover' and z.get('validated',False) for a,z in pairs),'standalone_deliveries':sum(a['family']=='failover' and a.get('validated',False) for a,z in pairs),'simulation':True},'actual_availability_pairs':sum(any(category(r)=='ACTUAL_PROVIDER_AVAILABILITY' for r in (a,z)) for a,z in pairs),'categories':{k:sum(category(r)==k for r in rows) for k in sorted({category(r) for r in rows})},'mixed_or_other_excluded_pairs':len(pairs)-len(ordinary),'resource_scope':'All matched costs retained overall; ordinary efficiency stratified by provider, excludes injected/mixed-provider pairs; actual availability failures retained in fixed-provider profiles'}

def compact_packet(before):
 return {'source_sha256':{n:hashlib.sha256(v.encode()).hexdigest() for n,v in before.items()},'files':sorted(before),'instruction':'Read source and immutable public checks through project tools as needed; do not repeat data already supplied.'}

def context_choice(base,provider,family,engine,contract,default='full',effort=None):
 p=Path(base)/'context-routing.json'
 if not p.exists():return default
 d=json.loads(p.read_text());row=d.get('recommendations',{}).get(provider+':'+family)
 from controls import effective
 options=effective(base)['executors'][provider];model=options['model'];effort=effort or options['native_effort']
 if not row or row.get('native_effort')!=effort or row.get('model')!=model or d.get('engine_sha256')!=engine or d.get('expires_unix',0)<=time.time() or row.get('contract')!=contract:return default
 from qualification_protocol import native_clients
 client=native_clients({'executors':{provider:{'enabled':True}}}).get(provider,{})
 if client.get('verified') is not True or row.get('native_client_version')!=client.get('version'):return default
 if row.get('pairs',0)<35 or row.get('quality_nonregressing') is not True:return default
 ratios=[row.get('token_ratio'),row.get('time_ratio')]
 if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in ratios) or min(ratios)>.8 or max(ratios)>1.05:return default
 return 'compact' if row.get('qualified') is True else default


def quarantine_contracts(base,rows,contracts):
 from common import atomic
 path=Path(base)/'task-contract-quarantine.json';data=json.loads(path.read_text()) if path.exists() else {}
 for family,signature in contracts.items():
  rs=[r for r in rows if r['family']==family and r.get('phase')==1 and category(r)=='HELDOUT_REJECTED']
  patterns={tuple(sorted(k for k,v in r.get('acceptance',{}).get('case_results',{}).items() if not v)) for r in rs}
  if len(rs)>=4 and len({r['provider'] for r in rs})>=2 and len(patterns)==1 and next(iter(patterns)):
   expiry=max(r['queued_unix']+r['elapsed_seconds'] for r in rs)+86400
   data.setdefault(signature,{'family':family,'reason':'Repeated identical private rejection across providers; diagnose task contract, never weaken acceptance','expires_unix':expiry,'source_runs':[r['id'] for r in rs]})
 if data:atomic(path,data)
 return data


def phase_telemetry(phases):
 """Measured controller gaps only; historical missing timestamps remain unknown."""
 from datetime import datetime
 ordered=sorted(phases,key=lambda row:row['phase']);gaps=[]
 for before,after in zip(ordered,ordered[1:]):
  try:
   end=datetime.fromisoformat(before['finished_at']).timestamp();start=after['phase_started_unix']
   if type(start) not in (int,float) or not math.isfinite(start) or start<end:raise ValueError('Invalid phase timing')
   gaps.append(start-end)
  except (KeyError,ValueError,TypeError):return {'phase_count':len(ordered),'phase_scheduling_gap_seconds':None,'phase_timing_complete':False}
 return {'phase_count':len(ordered),'phase_scheduling_gap_seconds':sum(gaps),'phase_timing_complete':True}
