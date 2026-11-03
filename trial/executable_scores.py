"""Versioned functional scorecards and matched deltas; no hidden composite weights."""
from pathlib import Path
from statistics import mean,median
import json,math
from common import BASE

SCORING='executable-score-v1'

def equal(a,b):
    if type(b) in (int,float):return type(a) in (int,float) and math.isfinite(a) and abs(a-b)<=1e-9
    if isinstance(b,dict):return isinstance(a,dict) and set(a)==set(b) and all(equal(a[k],b[k]) for k in b)
    if isinstance(b,list):return isinstance(a,list) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return type(a) is type(b) and a==b

def grade(evaluation,cases):
    executed=evaluation.get('status')=='EXECUTED';rows={r['id']:r for r in evaluation.get('results',[])}
    outcomes={};groups={}
    for c in cases:
        r=rows.get(c['id'],{})
        passed=executed and (r.get('error')==c['error'] if c.get('error') else 'error' not in r and equal(r.get('value'),c['expected']))
        outcomes[c['id']]=bool(passed);g=groups.setdefault(c['workflow'],{'passed':0,'total':0});g['total']+=1;g['passed']+=bool(passed)
    quality=100*mean(g['passed']/g['total'] for g in groups.values())
    complete=sum(g['passed']==g['total'] for g in groups.values())
    return {'scoring_schema':SCORING,'quality_score':quality,'effectiveness_pct':100*int(complete==len(groups)),
      'validated_delivery':complete==len(groups),'fully_working_workflows':complete,'workflow_count':len(groups),
      'workflow_results':groups,'case_results':outcomes,'tests_executed':len(cases) if executed else 0,
      'execution_status':evaluation.get('status'),'score_rule':'Equal weight per workflow; invalid or non-completing delivered artifacts score0, with zero tests claimed executed',
      'quality_scope':'Functional correctness on this fixed corpus, not all features, users or market fit'}

def aggregate(entries,repetitions):
    measured=[e for e in entries if e.get('grade') is not None];complete=len(measured)==repetitions
    times=[e['end_to_end_seconds'] for e in entries if type(e.get('end_to_end_seconds')) in (int,float) and math.isfinite(e['end_to_end_seconds']) and e['end_to_end_seconds']>=0]
    timing_complete=bool(entries) and len(times)==len(entries)
    tokens=[e['tokens'] for e in entries if type(e.get('tokens')) is int and e['tokens']>=0];usage_complete=len(tokens)==len(entries) and len(entries)>0
    valid=sum(e['grade']['validated_delivery'] for e in measured)
    return {'requested_repetitions':repetitions,'measured_implementations':len(measured),'complete':complete,
      'quality_score':mean(e['grade']['quality_score'] for e in measured) if complete else None,
      'observed_quality_score':mean(e['grade']['quality_score'] for e in measured) if measured else None,
      'effectiveness_pct':100*valid/repetitions if complete else None,'validated_deliveries':valid,
      'median_end_to_end_seconds':median(times) if timing_complete else None,'total_end_to_end_seconds':sum(times) if timing_complete else None,
      'known_end_to_end_seconds':sum(times),'timing_complete':timing_complete,'missing_timing_observations':len(entries)-len(times),
      'known_tokens':sum(tokens),'usage_complete':usage_complete,
      'tokens_per_validated_delivery':sum(tokens)/valid if valid and usage_complete else None,
      'validated_deliveries_per_hour':3600*valid/sum(times) if timing_complete and sum(times)>0 else None,
      'validated_deliveries_per_million_tokens':1e6*valid/sum(tokens) if usage_complete and sum(tokens)>0 else None,
      'sampling':'Repeated implementations of four benchmark workflows; not distinct user deliveries or independent user samples'}

def delta(before,after):
    def change(key,lower=False):
        a,b=before.get(key),after.get(key)
        return {'baseline':a,'candidate':b,'difference':b-a if a is not None and b is not None else None,
                'improvement_pct':(100*((a-b) if lower else (b-a))/a) if a not in (None,0) and b is not None else None}
    return {'quality_percentage_points':after['quality_score']-before['quality_score'] if before['quality_score'] is not None and after['quality_score'] is not None else None,
      'effectiveness_percentage_points':after['effectiveness_pct']-before['effectiveness_pct'] if before['effectiveness_pct'] is not None and after['effectiveness_pct'] is not None else None,
      'time':change('median_end_to_end_seconds',True),'tokens_per_delivery':change('tokens_per_validated_delivery',True),
      'productivity':change('validated_deliveries_per_hour'),'token_efficiency':change('validated_deliveries_per_million_tokens')}

def summarize(record):
    from execution_contract import analysis_fingerprint
    result={'schema':SCORING,'analysis_sha256':analysis_fingerprint(),'job_id':record['id'],'trial_id':record['trial_id'],'candidate_version':record['candidate_version'],
      'baseline_version':record['baseline_version'],'suite':record['suite'],'providers':{},'comparison_kind':record.get('comparison_kind','INDEPENDENT_MATCHED_IMPLEMENTATIONS'),
      'interpretation':'Scores and deltas describe this fixed functional corpus. Small repeated samples are descriptive; no statistical superiority, user-value or optimal-allocation guarantee.',
      'score_semantics':'quality_score measures delivered artifacts; functional-gain flags require paired executed tests. Formatting recovery is reported as delivery gain.',
      'resources':'End-to-end includes native generation, artifact handling and sandbox evaluation; tokens include failed attempts. Subscription credit charges are unknown.'}
    for provider in record['providers']:
        rows=[e for e in record['runs'] if e['provider']==provider];a=[e for e in rows if e['variant']=='baseline'];b=[e for e in rows if e['variant']=='candidate']
        before=aggregate(a,record['repetitions']);after=aggregate(b,record['repetitions']);regressions=improvements=0;paired=0;executed_pairs=0
        for repeat in range(record['repetitions']):
            av=next((e for e in a if e['repeat']==repeat and e.get('grade')),None);bv=next((e for e in b if e['repeat']==repeat and e.get('grade')),None)
            if not av or not bv:continue
            paired+=1
            if av['grade'].get('tests_executed',0)>0 and bv['grade'].get('tests_executed',0)>0:executed_pairs+=1
            ac,bc=av['grade']['case_results'],bv['grade']['case_results']
            regressions+=sum(ac[k] and not bc[k] for k in ac);improvements+=sum(not ac[k] and bc[k] for k in ac)
        complete=before['complete'] and after['complete'];d=delta(before,after)
        input_reference=record.get('comparison_kind')=='IDENTICAL_INPUT_REFERENCE'
        if input_reference:paired=0
        result['providers'][provider]={'baseline':before,'candidate':after,'delta':d,'paired_repetitions':paired,
          'comparison_basis':'same measured artifacts for identical selected input' if input_reference else 'independently generated matched implementations',
          'implementations_per_input':before['measured_implementations'] if input_reference else None,
          'case_regressions':regressions if complete else None,'newly_passing_cases':improvements if complete else None,
          'observed_nonregressing_delivery_gain':bool(not input_reference and complete and regressions==0 and d['quality_percentage_points']>0),
          'observed_nonregressing_quality_gain':bool(not input_reference and complete and executed_pairs==record['repetitions'] and regressions==0 and d['quality_percentage_points']>0),
          'executed_test_pairs':executed_pairs if not input_reference else 0,
          'quality_gain_limit':'Delivery recovery alone is not evidence that the specification improved functional correctness; both sides require executed tests',
          'first_pass_public_successes':sum(bool(e.get('first_pass',{}).get('public_passed')) for e in b),
          'repair_calls':sum(e.get('repairs',0) for e in b),
          'availability':record.get('waits',{}).get(provider) or next((e.get('native_failure') or e.get('error') for e in rows if e.get('grade') is None),None),'matched_profile':record['profiles'][provider]}
    result['overall_quality_score']=mean(v['candidate']['quality_score'] for v in result['providers'].values()) if result['providers'] and all(v['candidate']['complete'] for v in result['providers'].values()) else None
    return result

def view(base=BASE,version=None,executor='all',history=False,compare='baseline',limit=20):
    from executable_benchmark import context,read_versions
    base=Path(base)
    if compare not in ('baseline','parent','previous') and (not compare.isdigit() or int(compare)<0):raise ValueError('Comparison must be baseline, parent, previous, or a nonnegative version')
    if not (base/'trial-clock.json').exists():return {'schema':SCORING,'status':'NOT_CONFIGURED','quality_score':None,'reason':'No specification trial is configured; no evaluation data exists'}
    clock=json.loads((base/'trial-clock.json').read_text());active=json.loads((base/'active-version.json').read_text())['version']
    paths=sorted((base/'executable-evaluations'/clock['trial_id']).glob('*/report.json'),key=lambda p:p.stat().st_mtime) if (base/'executable-evaluations'/clock['trial_id']).exists() else []
    reports=[json.loads(p.read_text()) for p in paths]
    invalidated=json.loads((base/'evaluation-invalidations.json').read_text()).get('invalidated_suites',{}) if (base/'evaluation-invalidations.json').exists() else {}
    valid_paths=[p for p,r in zip(paths,reports) if r.get('suite',{}).get('suite') not in invalidated]
    reports=[r for r in reports if r.get('suite',{}).get('suite') not in invalidated];paths=valid_paths
    target=active if version is None else version
    if history:
        return {'schema':SCORING,'trial_id':clock['trial_id'],'active_version':active,'history':[view(base,v,executor,False,compare,limit) for v in read_versions(base)[-limit:]]}
    if type(target) is not int or target<0:raise ValueError('Nonnegative version required')
    import spec_trial as worker
    text,m=worker.read_version(target);signature=context(text)[1]
    from executable_cases import corpus,manifest
    current_suite=manifest(corpus())
    matching=[r for r in reports if any(r['contexts'][variant]['sha256']==signature for variant in ('candidate','baseline')) and r['suite']==current_suite]
    baseline_reference=bool(matching and (target==0 or matching[-1]['contexts']['candidate']['sha256']!=signature))
    if not matching:return {'schema':SCORING,'trial_id':clock['trial_id'],'version':target,'active_version':active,'status':'NOT_MEASURED','quality_score':None,'reason':'No executable implementation evaluation for this selected contract input yet'}
    r=matching[-1];s=summarize(r)
    if baseline_reference:
        for row in s['providers'].values():
            row['candidate']=dict(row['baseline']);row['delta']=delta(row['baseline'],row['baseline']);row['case_regressions']=0 if row['baseline']['complete'] else None;row['newly_passing_cases']=0 if row['baseline']['complete'] else None;row['observed_nonregressing_quality_gain']=False;row['observed_nonregressing_delivery_gain']=False;row['paired_repetitions']=0;row['executed_test_pairs']=0;row['comparison_basis']='baseline evidence reference; no independent candidate comparison'
        s['comparison_kind']='IDENTICAL_INPUT_REFERENCE'
        s['candidate_version']=0
        s['overall_quality_score']=mean(row['candidate']['quality_score'] for row in s['providers'].values()) if all(row['candidate']['quality_score'] is not None for row in s['providers'].values()) else None
    if executor!='all' and executor not in s['providers']:return {'schema':SCORING,'version':target,'status':'NOT_MEASURED','quality_score':None,'reason':'No measurements for requested executor '+executor}
    if executor!='all':s['providers']={k:v for k,v in s['providers'].items() if k==executor};s['overall_quality_score']=next(iter(s['providers'].values()))['candidate']['quality_score'] if s['providers'] else None
    measured_version=0 if baseline_reference or r.get('comparison_kind')=='IDENTICAL_INPUT_REFERENCE' else r['candidate_version']
    result={'schema':SCORING,'trial_id':clock['trial_id'],'version':target,'active_version':active,'measured_version':measured_version,
      'status':('MEASURED' if all(row['candidate']['complete'] for row in s['providers'].values()) else 'PARTIAL_OR_DEFERRED') if measured_version==target else 'IDENTICAL_EVALUATED_INPUT_REFERENCE',
      'new_execution_for_this_version':measured_version==target and any(e.get('grade',{}).get('tests_executed',0)>0 for e in r['runs'] if e.get('grade')),'scorecard':s,'artifact_report':str(paths[reports.index(r)]),
      'coverage':'Selected four contract workflows only; identical selected inputs do not establish equivalence of the entire specification'}
    if compare not in ('baseline','0'):
        versions=[v for v in read_versions(base) if v<target]
        reference=m.get('parent_version',0) if compare=='parent' else (versions[-1] if versions else 0) if compare=='previous' else int(compare)
        other=view(base,reference,executor,False,'baseline',limit);result['comparison_version']=reference;result['version_delta']={}
        if 'scorecard' in other:
            for p,row in s['providers'].items():
                prev=other['scorecard']['providers'].get(p)
                if prev and other['scorecard']['suite']==s['suite'] and prev['matched_profile']==row['matched_profile']:
                    result['version_delta'][p]=delta(prev['candidate'],row['candidate'])
        result['version_comparison_limit']='Across distinct evaluation sessions; task corpus/profile matching checked, temporal effects remain. Baseline deltas above are within-session pairs.'
    return result

def render(result):
    if 'history' in result:return '\n'.join(render(r) for r in result['history'])
    if 'scorecard' not in result:return ('v'+str(result['version'])+': ' if 'version' in result else '')+result.get('status','NOT_MEASURED')+' — '+result.get('reason','No executable measurements')
    s=result['scorecard'];lines=['v'+str(result['version'])+' ['+result['status']+']; measured v'+str(result['measured_version'])+'; '+s['suite']['suite']+'; '+str(s['suite']['case_count'])+' cases / '+str(len(s['suite']['workflow_counts']))+' workflows']
    for p,r in s['providers'].items():
        a,b=r['baseline'],r['candidate'];d=r['delta'];q=lambda x:'pending' if x is None else f'{x:.2f}'
        lines.append(p+': delivery quality '+q(a['quality_score'])+' → '+q(b['quality_score'])+'/100; Δ '+q(d['quality_percentage_points'])+' pp; effectiveness '+q(b['effectiveness_pct'])+'%; regressions '+str(r['case_regressions'])+'; pairs '+str(r['paired_repetitions']))
        if r.get('observed_nonregressing_delivery_gain') and not r.get('observed_nonregressing_quality_gain'):lines.append('  Delivery gain only; paired executed tests do not establish a functional correctness gain.')
        if not b['complete']:lines.append('  observed quality '+q(b['observed_quality_score'])+' from '+str(b['measured_implementations'])+'/'+str(b['requested_repetitions'])+' implementations; '+str(r.get('availability') or 'awaiting data'))
        lines.append('  median attempt seconds '+q(b['median_end_to_end_seconds'])+'; tokens/validated delivery '+q(b['tokens_per_validated_delivery'])+'; validated deliveries/hour '+q(b['validated_deliveries_per_hour']))
    if s.get('comparison_kind')=='IDENTICAL_INPUT_REFERENCE':lines.append('Identical selected contract input: candidate scores reference the same tested implementations; no independent candidate execution or measured resource gain.')
    lines.append('Functional benchmark evidence only; repeated samples are descriptive. See --json for corpus, provenance and resource deltas.')
    return '\n'.join(lines)
