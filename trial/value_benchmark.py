"""Paired native contract-comprehension diagnostics; not customer-value proof.

Answer keys are authored from quoted baseline contracts, never supplied to the
executor. These first cases are diagnostic calibration, not a pristine holdout.
Model/effort comparisons use identical questions and record every native cost.
"""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,time,uuid
from common import BASE,atomic

CASES=[
 ('unit-scope','BaseUnit','Two measurements are cross-system comparable only when they share the same BaseUnit and the same scope.',
  'Two measurements both use TOKENS, but have different scopes. Are they cross-system comparable under this contract?',False),
 ('override','EvidenceSufficiencyGate','sufficiency_score < threshold AND operator_override present → OPERATOR_OVERRIDE',
  'The sufficiency score is below threshold and an operator override is present. Is the verdict INSUFFICIENT?',False),
 ('cyclic-plan','OperationDependency','URACE MUST NOT schedule any operation in a cyclic cluster until the cycle is resolved.',
  'A dependency cycle remains unresolved. May URACE schedule an operation inside the cyclic cluster?',False),
 ('start-edge','OperationDependency','START_TO_START`: to_id may not start until from_id has started.',
  'With START_TO_START, from_id has started but has not finished. Does that edge require to_id to keep waiting for from_id to finish?',False),
 ('quality-unit','QualityDelta','normalized scores in [0.0, 1.0]',
  'Is a score_after value of 1.5 valid under the score unit contract?',False),
 ('quality-neutral','QualityDelta','NEUTRAL`: delta = 0 or no predecessor;',
  'There is no predecessor. Is the classification NEUTRAL?',True),
 ('archive-aggregate','CompactionSummary','record_count` and `time_range` MUST be used for aggregate statistics, not skipped or treated as zero.',
  'May an aggregate query treat a CompactionSummary representing archived records as zero records?',False),
 ('conditional-time','WakeCondition','scheduled_at` MUST always be present regardless of kind',
  'Is scheduled_at required for a CONDITIONAL registration?',True),
]

def section(text,heading):
    anchor='## '+heading+'\n'
    if text.count(anchor)!=1:raise ValueError('Benchmark section missing or ambiguous: '+heading)
    start=text.index(anchor);end=text.find('\n## ',start+len(anchor))
    return text[start:] if end<0 else text[start:end]

def fixture(before,after):
    questions=[];references=[]
    for identifier,heading,quote,question,answer in CASES:
        a,b=section(before,heading),section(after,heading)
        if quote not in a or quote not in b:raise ValueError('Benchmark oracle contract changed: '+identifier)
        questions.append({'id':identifier,'question':question})
        references.append({'id':identifier,'heading':heading,'quote':quote,'answer':answer})
    return questions,references

def score(response,keys):
    answers=response.get('answers') if isinstance(response,dict) else None
    if not isinstance(answers,dict) or set(answers)!={r['id'] for r in keys}:raise ValueError('Incomplete benchmark response')
    if any(type(v) is not bool for v in answers.values()):raise ValueError('Benchmark answers must be booleans')
    return {'correct':sum(answers[r['id']]==r['answer'] for r in keys),'total':len(keys),
            'accuracy':sum(answers[r['id']]==r['answer'] for r in keys)/len(keys),
            'case_results':{r['id']:answers[r['id']]==r['answer'] for r in keys}}

def run(base=BASE,version_number=None):
    import spec_trial as worker
    from controls import effective
    base=Path(base);clock=worker.load(base/'trial-clock.json');pointer=worker.load(base/'active-version.json')
    number=pointer['version'] if version_number is None else version_number
    before,bm=worker.read_version(0);after,am=worker.read_version(number);questions,keys=fixture(before,after)
    identity=uuid.uuid4().hex;folder=base/'benchmarks'/clock['trial_id']/('benchmark-'+identity);folder.mkdir(parents=True)
    record={'schema':'contract-diagnostic-v1','at':datetime.now(timezone.utc).isoformat(),
      'trial_id':clock['trial_id'],'id':folder.name,'baseline_sha256':bm['sha256'],'candidate_sha256':am['sha256'],
      'candidate_version':number,'answer_key_sha256':hashlib.sha256(json.dumps(keys,sort_keys=True).encode()).hexdigest(),
      'case_provenance':keys,'runs':[],
      'limitations':['Diagnostic calibration cases, not pristine held-out data','Eight contract questions do not cover all runtime features',
                    'Paired accuracy is not adoption, market fit or real-user benefit','Same-source task pairs are dependent; small samples cannot establish optimal allocation']}
    from source_integrity import matches
    pins=worker.load(base/'harness-manifest.json',{})
    if any(not matches(base/name,expected) for name,expected in pins.items()):raise RuntimeError('Benchmark source/authority integrity mismatch')
    record['harness_manifest_sha256']=hashlib.sha256((base/'harness-manifest.json').read_bytes()).hexdigest()
    record['source_pins']=pins
    if pins:
        from snapshot_metadata import engine_snapshot
        record['engine']=engine_snapshot(base)
    controls=effective(base)
    if controls['paused'] or not controls['executor_enabled']:raise RuntimeError('Operator paused or disabled executors')
    eligible,waits=worker.eligible();record['waits']=waits
    for provider in eligible:
        if not controls['executors'][provider]['enabled']:continue
        # Counterbalance invocation order by provider/run; do not show the version
        # label, expected answers, reviewer ratings or proposer failure hypothesis.
        order=['baseline','candidate']
        if int(hashlib.sha256((provider+identity).encode()).hexdigest(),16)%2:order.reverse()
        for label in order:
            current=effective(base)
            available,_=worker.eligible()
            if current!=controls or provider not in available:
                record['runs'].append({'provider':provider,'variant':label,'error':'Operator settings or availability changed; paired comparison withheld'})
                atomic(folder/'report.json',record);break
            text=before if label=='baseline' else after
            context='\n'.join(section(text,h) for h in dict.fromkeys(r['heading'] for r in keys))
            prompt=('Answer these concrete implementation decisions using only the supplied specification. '
                    'Do not improve or critique the text. Outer source must be JSON {"answers":{id:boolean,...}}. '
                    'QUESTIONS: '+json.dumps(questions)+'\nSPECIFICATION:\n'+context)
            entry={'provider':provider,'variant':label,'model':controls['executors'][provider]['model'],
                   'native_effort':controls['executors'][provider]['native_effort'],'question_count':len(keys)}
            try:
                answer=worker.native(provider,prompt,folder,provider+'-'+label)
                entry.update(score(answer,keys))
            except Exception as error:entry['error']=type(error).__name__+': '+str(error)
            receipt=worker.load(folder/(provider+'-'+label+'-native.json'),{})
            entry.update(tokens=receipt.get('tokens'),executor_seconds=receipt.get('wall_seconds'),failure=receipt.get('failure'))
            record['runs'].append(entry);atomic(folder/'report.json',record)
    record['pairs']=[]
    for provider in eligible:
        pair={r['variant']:r for r in record['runs'] if r['provider']==provider}
        if set(pair)=={'baseline','candidate'} and all('accuracy' in r for r in pair.values()):
            a,b=pair['baseline'],pair['candidate'];record['pairs'].append({'provider':provider,
                'accuracy_change_percentage_points':100*(b['accuracy']-a['accuracy']),
                'candidate_accuracy':b['accuracy'],'baseline_accuracy':a['accuracy'],
                'known_pair_tokens':sum(r['tokens'] or 0 for r in pair.values()),
                'usage_complete':all(r.get('tokens') is not None for r in pair.values()),
                'tokens_per_correct_answer':{label:(r['tokens']/r['correct'] if r.get('tokens') is not None and r['correct'] else None) for label,r in pair.items()},
                'conclusion':'Regression on these cases' if b['accuracy']<a['accuracy'] else 'No regression on these diagnostic cases; benefit not established' if b['accuracy']==a['accuracy'] else 'Observed gain on these diagnostic cases; needs independent replication'})
    record['complete_pairs']=len(record['pairs']);record['finished_at']=datetime.now(timezone.utc).isoformat()
    atomic(folder/'report.json',record);atomic(base/'benchmark-latest.json',record)
    return record

if __name__=='__main__':
    from trial_supervisor import external_owner
    if external_owner():print(json.dumps({'status':'OWNED_BY_SINGLE_SUPERVISOR'}));raise SystemExit(0)
    latest_path=BASE/'executable-benchmark-latest.json'
    if latest_path.exists():
        previous=json.loads(latest_path.read_text())
        current_clock=json.loads((BASE/'trial-clock.json').read_text())
        same_source=previous.get('harness_manifest_sha256')==hashlib.sha256((BASE/'harness-manifest.json').read_bytes()).hexdigest()
        try:age=time.time()-datetime.fromisoformat(previous['finished_at']).timestamp()
        except (KeyError,ValueError):age=1e9
        if previous.get('trial_id')==current_clock['trial_id'] and same_source and previous.get('complete_comparisons',previous.get('complete_pairs',0))>0 and 0<=age<10800:
            print(json.dumps({'status':'RECENT_DIAGNOSTIC_RETAINED','age_seconds':age,'additional_inference_calls':0}));raise SystemExit(0)
    # Implementations use immutable version snapshots; normal productive work
    # continues concurrently. Only the corrective publication needs a boundary.
    with (BASE/'benchmark.guard').open('a') as serial:
        fcntl.flock(serial,fcntl.LOCK_EX|fcntl.LOCK_NB)
        from executable_benchmark import run as executable_run
        record=executable_run()
        from cross_audit import run as audit
        record['cross_provider_audit']=audit()
        request=uuid.uuid4().hex
        atomic(BASE/'diagnostic-request.json',{'id':request,'expires_unix':time.time()+1200})
        try:
            with (BASE/'trial.guard').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                from quality_restore import run as restore
                record['corrective_restoration']=restore()
        finally:
            path=BASE/'diagnostic-request.json'
            if path.exists() and json.loads(path.read_text()).get('id')==request:path.unlink()
        record['candidate_identity_note']='Scores belong to the captured candidate version/hash; subsequent Product evolution and corrective snapshots are separate events.'
        atomic(BASE/'executable-benchmark-latest.json',record)
        print(json.dumps(record,indent=2))
