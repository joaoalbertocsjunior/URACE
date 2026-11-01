"""Maintainer-authored acceptance oracles; never sent to evaluated executors."""
import hashlib,json,random

SUITE='urace-executable-v3'
HEADINGS=['EvidenceSufficiencyGate','EvidenceSufficiencyFormula','OperationDependency','QualityDelta','CompactionSummary']
ANCHORS={
 'EvidenceSufficiencyGate':['Filter: exclude PENDING_NEXT_CYCLE and RETRACTED Evidence','operator_override present → OPERATOR_OVERRIDE'],
 'EvidenceSufficiencyFormula':['coverage_score defaults to 1.0','credibility and relevance ∈ [0.0, 1.0]; values outside range are clamped before computation','All evidence in evidence_set with credibility = 0: E_sufficient = false regardless of coverage'],
 'OperationDependency':['OperationDependency edges in a Plan MUST be acyclic.','to_id may not start until from_id is complete.'],
 'QualityDelta':['IMPROVEMENT`: delta > 0;','REGRESSION`: delta < 0.'],
 'CompactionSummary':['record_count` and `time_range` MUST be used for aggregate statistics, not skipped or treated as zero.']}
TASK="""Implement a Python3 standard-library-only module with these four pure functions. Use the supplied URACE contracts as data. No tools, files, I/O, networking, subprocesses, self-tests or external dependencies in your module. Return source as serialized JSON {"python_source":"complete module source"}; notes may contain commentary. Never return citations in source.
Public adapter contract (encoding conventions, not extra URACE requirements):
1. quality_delta(before, after): scores are finite numbers in [0,1]; before may be None. Return {"delta":float,"classification":"IMPROVEMENT|NEUTRAL|REGRESSION"}. With no predecessor return delta0 and NEUTRAL. Reject out-of-range scores with ValueError.
2. evidence_verdict(evidence, required_dimensions, threshold, override): each evidence dict has credibility, relevance, dimensions and status ACTIVE|RETRACTED|PENDING_NEXT_CYCLE. Return {"score":float,"verdict":"SUFFICIENT|OPERATOR_OVERRIDE|INSUFFICIENT"}. Inputs guarantee at least one usable positive-relevance item. Dimensions on evidence belong to required_dimensions, except when required_dimensions is empty. Use the specification's weighted mean, coverage, filtering and verdict rules. Threshold is in [0,1].
3. ready_operations(operations, edges): operations are {id,status}, status PLANNED|RUNNING|COMPLETED; edges are {from_id,to_id,kind}, kind FINISH_TO_START|START_TO_START|FINISH_TO_FINISH. These status names encode not started, started and complete. All edge endpoints exist. Return sorted IDs of PLANNED operations allowed to start. A cyclic cluster must not start; an unrelated acyclic component remains eligible. FINISH_TO_FINISH constrains completion rather than starting.
4. aggregate_records(records): records are live {type:"record",id:...} or {type:"CompactionSummary",record_count:n,...}. Return the total underlying record count. Live items count1; summaries count record_count, including0, without needing the archive. Invalid summary counts (missing, negative, bool, noninteger) must raise ValueError. This error encoding is an adapter convention.
The acceptance fixtures and expected outputs are withheld. Implement the contracts for arbitrary supported inputs, not examples. Do not assume one version is newer or preferred.
"""

def oracle_ready(ops,edges):
    ids=[o['id'] for o in ops];states={o['id']:o['status'] for o in ops}
    # Independent transitive-closure oracle, not an executor-supplied algorithm.
    reach={(a,c):False for a in ids for c in ids}
    for e in edges:reach[e['from_id'],e['to_id']]=True
    for k in ids:
        for a in ids:
            for c in ids:reach[a,c]=reach[a,c] or (reach[a,k] and reach[k,c])
    return sorted(o['id'] for o in ops if o['status']=='PLANNED' and not reach[o['id'],o['id']] and all(
      e['to_id']!=o['id'] or e['kind']=='FINISH_TO_FINISH' or
      (states[e['from_id']]=='COMPLETED' if e['kind']=='FINISH_TO_START' else states[e['from_id']] in ('RUNNING','COMPLETED')) for e in edges))

def corpus(seed=5688):
    rng=random.Random(seed);cases=[]
    def add(group,args,expected=None,error=None):
        cases.append({'id':str(len(cases)),'workflow':group,'function':group,'args':args,'expected':expected,'error':error})
    for before in [None,0,.125,.25,.5,.75,1]:
        for after in [0,.125,.25,.5,.75,1]:
            delta=0 if before is None else after-before
            add('quality_delta',[before,after],{'delta':delta,'classification':'NEUTRAL' if before is None or delta==0 else 'IMPROVEMENT' if delta>0 else 'REGRESSION'})
    for before,after in [(-1,.5),(.5,2),(None,-.1)]:add('quality_delta',[before,after],error='ValueError')
    for i in range(64):
        dims=[chr(97+j) for j in range(rng.choice([0,1,2,4]))]
        evidence=[{'credibility':rng.choice([0,.25,.5,.75,1]),'relevance':rng.randint(1,4)/4,'dimensions':rng.sample(dims,rng.randint(0,len(dims))),'status':'ACTIVE'}]
        for _ in range(rng.randint(0,6)):
            evidence.append({'credibility':rng.choice([0,.25,.5,.75,1]),'relevance':rng.randint(1,4)/4,'dimensions':rng.sample(dims,rng.randint(0,len(dims))),'status':rng.choice(['ACTIVE','RETRACTED','PENDING_NEXT_CYCLE'])})
        active=[e for e in evidence if e['status']=='ACTIVE'];covered=set().union(*(set(e['dimensions']) for e in active));coverage=len(covered)/len(dims) if dims else 1
        score=sum(e['credibility']*e['relevance'] for e in active)/sum(e['relevance'] for e in active)*coverage
        threshold=rng.choice([0,.125,.375,.5,.625,.875,1]);override=bool(i%2)
        add('evidence_verdict',[evidence,dims,threshold,override],{'score':score,'verdict':'SUFFICIENT' if score>=threshold else 'OPERATOR_OVERRIDE' if override else 'INSUFFICIENT'})
    # Explicit equality, override and zero-dimension boundaries.
    for override in [False,True]:
        e=[{'credibility':.5,'relevance':1,'dimensions':[],'status':'ACTIVE'}]
        add('evidence_verdict',[e,[],.5,override],{'score':.5,'verdict':'SUFFICIENT'})
    clamp_a=[{'credibility':2,'relevance':2,'dimensions':['a'],'status':'ACTIVE'},{'credibility':-1,'relevance':.5,'dimensions':[],'status':'ACTIVE'}]
    add('evidence_verdict',[clamp_a,['a'],.5,False],{'score':2/3,'verdict':'SUFFICIENT'});cases[-1]['domain_case']='clamp'
    clamp_b=[{'credibility':.5,'relevance':-1,'dimensions':[],'status':'ACTIVE'},{'credibility':.25,'relevance':.5,'dimensions':['a'],'status':'ACTIVE'}]
    add('evidence_verdict',[clamp_b,['a'],.5,True],{'score':.25,'verdict':'OPERATOR_OVERRIDE'});cases[-1]['domain_case']='clamp'
    for _ in range(80):
        ops=[{'id':chr(97+i),'status':rng.choice(['PLANNED','RUNNING','COMPLETED'])} for i in range(rng.randint(1,7))]
        edges=[{'from_id':rng.choice(ops)['id'],'to_id':rng.choice(ops)['id'],'kind':rng.choice(['FINISH_TO_START','START_TO_START','FINISH_TO_FINISH'])} for _ in range(rng.randint(0,10))]
        add('ready_operations',[ops,edges],oracle_ready(ops,edges))
    ops=[{'id':x,'status':'PLANNED'} for x in ['a','b','free']];edges=[{'from_id':'a','to_id':'b','kind':'START_TO_START'},{'from_id':'b','to_id':'a','kind':'FINISH_TO_START'}]
    add('ready_operations',[ops,edges],['free'])
    for _ in range(48):
        records=[{'type':'record','id':str(i)} if rng.random()<.5 else {'type':'CompactionSummary','record_count':rng.randint(0,1000),'is_decompactable':False} for i in range(rng.randint(0,20))]
        add('aggregate_records',[records],sum(1 if r['type']=='record' else r['record_count'] for r in records))
    for count in [-1,True,1.5,None]:add('aggregate_records',[[{'type':'CompactionSummary','record_count':count}]],error='ValueError')
    return cases

def public_cases():
    """Published training examples, distinct from the sealed held-out corpus."""
    def c(key,workflow,args,expected=None,error=None):return {'id':'public-'+key,'workflow':workflow,'function':workflow,'args':args,'expected':expected,'error':error}
    ops=[{'id':'cycle-left','status':'PLANNED'},{'id':'cycle-right','status':'PLANNED'},{'id':'report','status':'PLANNED'},{'id':'audit','status':'PLANNED'}]
    edges=[{'from_id':'cycle-left','to_id':'cycle-right','kind':'START_TO_START'},{'from_id':'cycle-right','to_id':'cycle-left','kind':'START_TO_START'},{'from_id':'cycle-left','to_id':'report','kind':'FINISH_TO_FINISH'}]
    return [c('delta','quality_delta',[.25,.75],{'delta':.5,'classification':'IMPROVEMENT'}),
      c('invalid-score','quality_delta',[-1,.5],error='ValueError'),
      c('evidence','evidence_verdict',[[{'credibility':.75,'relevance':1,'dimensions':['availability'],'status':'ACTIVE'}],['availability'],.6,False],{'score':.75,'verdict':'SUFFICIENT'}),
      c('isolated-cycle','ready_operations',[ops,edges],['audit','report']),
      c('counts','aggregate_records',[[{'type':'record','id':'live'},{'type':'CompactionSummary','record_count':7}]],8)]

def manifest(cases):
    from execution_contract import fingerprint
    training=public_cases();combined=[*training,*cases]
    return {'suite':SUITE,'case_count':len(combined),'held_out_case_count':len(cases),'public_case_count':len(training),
            'workflow_counts':{w:sum(c['workflow']==w for c in combined) for w in sorted({c['workflow'] for c in combined})},
            'corpus_sha256':hashlib.sha256(json.dumps(combined,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'held_out_corpus_sha256':hashlib.sha256(json.dumps(cases,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'task_sha256':hashlib.sha256((TASK+json.dumps(training,sort_keys=True)).encode()).hexdigest(),
            'evaluator_sha256':fingerprint(),'execution_protocol':'bounded-public-feedback-v1',
            'oracle_provenance':'Private maintainer-authored held-out cases sealed before generation; public examples and compiler diagnostics may guide one repair. Hidden failures are never sent to executors.',
            'coverage':'Four contract-backed implementation workflows; broader core integration scenarios reported separately; not market fit'}
