"""Prespecified output-quality dimensions; engineering tests are not user-value proof."""
import ast,copy,hashlib,json,random
from pathlib import Path
from repository_tasks import answer,MAP

RUBRIC='executable-output-quality-v1'

def cases(family,phase=1):
    rng=random.Random(718391+sum(map(ord,family))*29+phase*17);requests=[]
    for i in range(48):
        if family=='receipts':
            usage=[{'total_tokens':0},{'total_tokens':True},{'total_tokens':-1,'input_tokens':2,'output_tokens':3},{'input_tokens':7,'output_tokens':3,'cached_input_tokens':7},{},None]
            records=[{'id':str(rng.randrange(6)),'product':rng.choice(['p','p','other']),'provider':rng.choice(['codex','claude']),'stage':rng.choice(['native','specification_adapter']),'usage':rng.choice(usage)} for _ in range(i%13)]
            requests.append({'product':'p','records':records})
        elif MAP[family]=='project_navigation':
            req=[{'id':str(j),'project_id':rng.choice(['p','p','other']),'priority':rng.randrange(4),'estimated_tokens':rng.randrange(4),'dependencies':[str(k) for k in range(j) if rng.random()<.4]+(['unknown'] if i%11==0 else []),'criteria':'r'+str(rng.randrange(3))} for j in range(i%9)]
            done=[{'id':r['id'],'project_id':rng.choice(['p','other']),'criteria':rng.choice([r['criteria'],'stale'])} for r in req if rng.random()<.7];requests.append([req,done,'p'])
        elif MAP[family]=='executor_failover':
            providers=[{'id':p,'enabled':rng.choice([True,False]),'available':rng.choice([True,False,None]),'retry_at':rng.choice([0,100,101]),'estimated_tokens':rng.choice([0,1,100]),'quality':rng.choice([0,.5,1]),'seconds':rng.choice([1,2,10])} for p in ['codex','claude']];requests.append([providers,100,rng.choice([None,0,1,100])])
        else:
            before={'a':'old','b':'base'};after={'a':'new','b':'next'}
            if i%7==0:before['/absolute']='old';after['/absolute']='new'
            if i%11==0:after['extra']='unexpected'
            current={k:rng.choice([v,after.get(k,v),'owner edit']) for k,v in before.items()};current['preserve']='unrelated';requests.append([{'before':before,'after':after},i%2==0,current])
    return [{'id':'quality-'+str(i),'request':r,'expected':answer(family,r,phase)} for i,r in enumerate(requests)]

RUNNER="""import sys,json,copy
sys.path.insert(0,'/workspace')
import app,logic
out=[]
for c in json.load(sys.stdin):
 try:
  request=copy.deepcopy(c['request']);original=copy.deepcopy(request)
  value=app.handle(request);other=logic.compute(copy.deepcopy(original));repeated=app.handle(copy.deepcopy(original))
  out.append({'id':c['id'],'value':value,'modules_agree':value==other,'repeat_equal':value==repeated,'input_mutated':request!=original})
 except Exception as e:out.append({'id':c['id'],'error':type(e).__name__})
print(json.dumps(out,allow_nan=False))
"""

def contract(family,phase=1):
    return hashlib.sha256(json.dumps({'rubric':RUBRIC,'cases':cases(family,phase),'runner':RUNNER},sort_keys=True).encode()).hexdigest()

def diagnostics(workspace):
    result={}
    for name in ('app.py','logic.py'):
        try:
            text=(Path(workspace)/name).read_text()
            if len(text.encode())>200000:result[name]={'parseable':None,'reason':'Source diagnostics size allowance; quality remains uncalibrated'};continue
            tree=ast.parse(text);functions=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
            result[name]={'lines':len(text.splitlines()),'functions':len(functions),'branch_nodes':sum(isinstance(n,(ast.If,ast.For,ast.While,ast.Try,ast.BoolOp)) for n in ast.walk(tree)),'documented_functions':sum(ast.get_docstring(n) is not None for n in functions),'parseable':True}
        except (OSError,SyntaxError,RecursionError):result[name]={'parseable':False}
    return {'source_diagnostics':result,'maintainability_quality':None,'interpretation':'Counts are review aids, not calibrated maintainability or user-value scores'}

def grade(family,phase,primary,quality_rows,values,baseline=None,workspace=None):
    from executable_scores import equal
    mapped={v['id']:v for v in values};primary_results={c['id']:mapped.get(c['id'],{}).get('modules_agree') is True and equal(mapped[c['id']].get('value'),c['expected']) for c in primary}
    robust={c['id']:mapped.get(c['id'],{}).get('modules_agree') is True and equal(mapped[c['id']].get('value'),c['expected']) for c in quality_rows};allrows=primary+quality_rows
    deterministic={c['id']:mapped.get(c['id'],{}).get('repeat_equal') is True for c in allrows};agreement={c['id']:mapped.get(c['id'],{}).get('modules_agree') is True for c in allrows}
    prior=baseline or {};before={**prior.get('case_results',{}),**prior.get('quality',{}).get('robustness_case_results',{})};after={**primary_results,**robust};regressions=[key for key,value in before.items() if value and not after.get(key,False)]
    full=all(primary_results.values()) and all(robust.values()) and all(deterministic.values()) and all(agreement.values()) and not regressions
    pct=lambda rows:100*sum(rows.values())/len(rows) if rows else None
    q={'measurement_complete':True,'rubric':RUBRIC,'contract_sha256':contract(family,phase),'primary_correctness_pct':pct(primary_results),'robustness_pct':pct(robust),'determinism_pct':pct(deterministic),'module_agreement_pct':pct(agreement),'robustness_case_results':robust,'regressed_case_ids':regressions,'newly_passing_cases':sum(not before.get(k,False) and v for k,v in after.items()) if baseline is not None else None,'gate_passed':full,'covered_cases':len(allrows),'independent_human_review':None,'usability':None,'maintainability':None,'observed_user_benefit':None,'market_fit':None,'unknown_dimensions':['independent_human_review','usability','maintainability','observed_user_benefit','market_fit'],'input_mutation_cases':sum(bool(v.get('input_mutated')) for v in values),'evidence_class':'prespecified_engineering_execution','limitations':'Independent of generated code, but fixed synthetic scenarios share the task oracle. Passing cannot establish uncovered behavior or real user benefit.'}
    if workspace is not None:q.update(diagnostics(workspace))
    return {'validated':all(primary_results.values()),'passed':sum(primary_results.values()),'total':len(primary),'quality_score_scope':'Primary functional correctness only; see quality dimensions','quality_score':pct(primary_results),'case_results':primary_results,'quality':q}

def summary(rows):
    measured=[r for r in rows if r.get('acceptance',{}).get('quality',{}).get('measurement_complete') is True];qualities=[r['acceptance']['quality'] for r in measured]
    return {'editorial_model_review':{'accepted_editorial_outputs':sum(r.get('outcome')=='ACCEPTED_EDITORIAL_IMPROVEMENT' for r in rows),'different_provider_reviewed_outputs':sum(r.get('outcome')=='ACCEPTED_EDITORIAL_IMPROVEMENT' and r.get('different_provider_review') is True for r in rows),'quality_policies':sorted({r['quality_policy'] for r in rows if r.get('quality_policy')}),'overall_editorial_quality_score':None,'scope':'Bounded editorial/model review is distinct from executable correctness, human usability and observed benefit'},'rubric':RUBRIC,'workflows':len(rows),'quality_measured_workflows':len(measured),'quality_unmeasured_workflows':len(rows)-len(measured),'quality_gated_deliveries':sum(q.get('gate_passed') is True and r.get('delivered',r.get('validated')) is True for r,q in zip(measured,qualities)),'mean_primary_correctness_pct_on_measured':sum(q['primary_correctness_pct'] for q in qualities)/len(qualities) if qualities else None,'mean_robustness_pct_on_measured':sum(q['robustness_pct'] for q in qualities)/len(qualities) if qualities else None,'regressed_cases':sum(len(q.get('regressed_case_ids',[])) for q in qualities),'unmeasured_dimensions':['independent_human_review','usability','maintainability','observed_user_benefit','market_fit'],'quality_gate_failed_workflows':sum(r.get('acceptance',{}).get('quality',{}).get('gate_passed') is False for r in rows),'all_workflow_delivery_rate_pct':100*sum(r.get('delivered',r.get('validated')) is True for r in rows)/len(rows) if rows else None,'quality_not_equivalent_to_tokens_or_time':True}
