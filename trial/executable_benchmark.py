"""Real native implementations, private acceptance oracles and isolated execution."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys,time,uuid
from common import BASE,atomic
from executable_cases import TASK,HEADINGS,ANCHORS,corpus,manifest
from executable_sandbox import IMAGE,check_image,execute,validate_source,SandboxInfrastructureError
from executable_scores import grade,summarize

def sha(value):return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()

def cli_smoke_score(runtime_root):
    """Run CLI smoke checks against the urace package and return a score dict."""
    import json as _json
    runtime_root = Path(runtime_root)
    cmds = [
        ([sys.executable, '-m', 'urace', '--help'], None),
        ([sys.executable, '-m', 'urace', 'watch', '--limit', '0'], None),
        ([sys.executable, '-m', 'urace', 'product', 'list', '--json'], 'json_lines'),
        ([sys.executable, '-m', 'urace', 'watch', '--guard'], None),
    ]
    results = []
    for cmd, check in cmds:
        cmd_str = ' '.join(cmd)
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=30, cwd=str(runtime_root))
            passed = proc.returncode == 0
            if passed and check == 'json_lines':
                out = proc.stdout.decode('utf-8', errors='replace').strip()
                if out:
                    try:
                        try:_json.loads(out)
                        except ValueError:
                            for line in out.splitlines():_json.loads(line)
                    except (ValueError, IndexError):
                        passed = False
            results.append({'cmd': cmd_str, 'passed': passed, 'exit_code': proc.returncode})
        except FileNotFoundError:
            results.append({'cmd': cmd_str, 'passed': False, 'exit_code': -1})
        except subprocess.TimeoutExpired:
            results.append({'cmd': cmd_str, 'passed': False, 'exit_code': -2})
    passing = sum(1 for r in results if r['passed'])
    total = len(results)
    score = (passing / total) * 100.0 if total else 0.0
    return {'cli_smoke_score': score, 'cli_smoke_passing': passing, 'cli_smoke_total': total, 'cli_smoke_results': results}
def load(path,default=None):return json.loads(Path(path).read_text()) if Path(path).exists() else default

def context(text):
    from value_benchmark import section
    sections={h:section(text,h) for h in HEADINGS}
    for h,quotes in ANCHORS.items():
        if any(q not in sections[h] for q in quotes):raise ValueError('Oracle source contract changed: '+h)
    result='\n'.join(sections.values())
    return result,sha(result)

def read_versions(base):
    base=Path(base);series=load(base/'version-series.json')['root'];root=(base/series).resolve()
    if not root.is_relative_to((base/'versions').resolve()):raise ValueError('Version directory escaped')
    return sorted(int(p.name[1:]) for p in root.glob('v[0-9]*') if p.is_dir() and p.name[1:].isdigit())

def profiles(controls):return {p:{k:v[k] for k in ('model','native_effort')} for p,v in controls['executors'].items() if v['enabled']}

def choose_version(base,suite,profile,active,available,repetitions):
    # Group all snapshot versions by their exact selected contract input.
    # Unchanged inputs can reference actual prior measurements without claiming
    # additional executions or whole-document equivalence.
    import spec_trial as worker
    reports=[load(p) for p in (Path(base)/'executable-evaluations'/load(Path(base)/'trial-clock.json')['trial_id']).glob('*/report.json')]
    epoch=datetime.now(timezone.utc).date().isoformat()
    def measured(signature,provider,fresh=False):
        return any((not fresh or r.get('measurement_epoch')==epoch) and r.get('repetitions')==repetitions and r.get('suite')==suite and r.get('profiles')==profile and any(r['contexts'][variant]['sha256']==signature and summarize(r)['providers'].get(provider,{}).get(variant,{}).get('complete') for variant in ('candidate','baseline')) for r in reports)
    groups={};incompatible=[]
    for number in read_versions(base):
        text,_=worker.read_version(number)
        try:_,signature=context(text)
        except ValueError:incompatible.append(number);continue
        groups.setdefault(signature,[]).append(number)
    text,_=worker.read_version(active);_,signature=context(text)
    if any(not measured(signature,p,True) for p in available):return active,groups,incompatible
    for signature,versions in groups.items():
        if any(not measured(signature,p) for p in available):return versions[-1],groups,incompatible
    return None,groups,incompatible

def collect(job):
    record=load(job/'plan.json');record['runs']=list(record.get('referenced_runs',[]))
    for p in record['providers']:
        record['runs']+=load(job/(p+'-progress.json'),{'runs':[]})['runs']
    # Include durably completed artifacts if a controller stopped before its progress checkpoint.
    existing={(e['provider'],e['repeat'],e['variant'],e.get('native_receipt_id')) for e in record['runs']}
    for path in job.glob('*/result.json'):
        e=load(path);key=(e['provider'],e['repeat'],e['variant'],e.get('native_receipt_id'))
        if key not in existing:record['runs'].append(e);existing.add(key)
    if record.get('comparison_kind')=='IDENTICAL_INPUT_REFERENCE':
        for e in list(record['runs']):
            if e['variant']=='baseline' and e.get('grade') is not None and not any(r['provider']==e['provider'] and r['repeat']==e['repeat'] and r['variant']=='candidate' for r in record['runs']):record['runs'].append({**e,'variant':'candidate','execution_reference':'baseline identical evaluated input; not a new native call or execution'})
    record['scorecard']=summarize(record);return record

def child(job,provider):
    import spec_trial as worker
    from controls import effective
    from source_integrity import matches
    job=Path(job).resolve();allowed=(BASE/'executable-evaluations').resolve()
    if not job.is_relative_to(allowed):raise ValueError('Evaluation outside trusted storage')
    plan=load(job/'plan.json');cases=load(job/'acceptance-private.json');entries=[]
    for repeat in range(plan['repetitions']):
        # Counterbalance labels per provider/repetition; labels never reach the model.
        reverse=(plan['providers'].index(provider)+repeat)%2
        variants=['baseline'] if plan.get('comparison_kind')=='IDENTICAL_INPUT_REFERENCE' else ['candidate','baseline'] if reverse else ['baseline','candidate']
        for variant in variants:
            if any(r['provider']==provider and r['repeat']==repeat and r['variant']==variant and r.get('grade') is not None for r in plan.get('referenced_runs',[])):continue
            controls=effective(BASE);profile=profiles(controls).get(provider);available,waits=worker.eligible()
            if controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals'] or provider not in available or profile!=plan['profiles'][provider]:
                atomic(job/(provider+'-progress.json'),{'runs':entries,'deferred':waits.get(provider,'Operator settings changed or executor disabled')});return
            if any(not matches(BASE/name,value) for name,value in plan['pins'].items()):raise RuntimeError('Evaluation source/authority changed')
            folder=job/(plan['id']+'-'+provider+'-'+str(repeat)+'-'+variant);folder.mkdir(exist_ok=True)
            entry={'provider':provider,'repeat':repeat,'variant':variant,'profile':profile,'grade':None,
                   'started_at':datetime.now(timezone.utc).isoformat(),'artifact_folder':str(folder)}
            prompt=TASK+'\nModule syntax contract: module level may contain standard-library imports from __future__, math, collections, functools, itertools, heapq, typing; function definitions; literal constants; and docstrings only. No classes, decorators, magic attributes, I/O, introspection or dynamic evaluation.\nSPECIFICATION DATA:\n'+(job/(variant+'-context.txt')).read_text()
            def admit():
                current=effective(BASE);usable,why=worker.eligible()
                if current['paused'] or not current['executor_enabled'] or not current['auto_goals'] or provider not in usable or profiles(current).get(provider)!=profile:raise RuntimeError('Evaluation admission deferred: '+str(why))
                if any(not matches(BASE/name,value) for name,value in plan['pins'].items()):raise RuntimeError('Evaluation source/authority changed')
            from executable_workflow import run as workflow
            try:entry.update(workflow(provider,prompt,folder,cases,worker.native,admit,profile))
            except Exception as error:entry.update(status='DEFERRED_OR_TRANSPORT_FAILURE',error=type(error).__name__+': '+str(error)[:500],grade=None)
            atomic(folder/'result.json',entry);entries.append(entry);atomic(job/(provider+'-progress.json'),{'runs':entries})
            if entry['grade'] is None:return

def run(base=BASE,version_number=None,repetitions=3):
    import spec_trial as worker
    from source_integrity import matches
    from controls import effective
    from snapshot_metadata import engine_snapshot
    base=Path(base)
    if type(repetitions) is not int or not 2<=repetitions<=20:raise ValueError('Use2..20 paired repetitions; this is experiment size, not a productive-call ceiling')
    pins=load(base/'harness-manifest.json',{})
    if any(not matches(base/k,v) for k,v in pins.items()):raise RuntimeError('Evaluation integrity mismatch')
    controls=effective(base)
    if controls['paused'] or not controls['executor_enabled'] or not controls['auto_goals']:raise RuntimeError('Operator disabled automatic evaluation')
    check_image();clock=load(base/'trial-clock.json');active=load(base/'active-version.json')['version'];profile=profiles(controls)
    cases=corpus();suite=manifest(cases)
    available,waits=worker.eligible()
    if version_number is None:number,groups,incompatible=choose_version(base,suite,profile,active,available,repetitions)
    else:number=version_number;groups={};incompatible=[]
    if number is None:
        record=load(base/'executable-benchmark-latest.json',{})
        return {**record,'status':'WAITING_FOR_RESOURCES' if not available else 'NO_UNMEASURED_INPUT_FOR_AVAILABLE_PROVIDERS','waits':waits,'eligible_executors':available,'availability_checked_at':datetime.now(timezone.utc).isoformat(),'additional_inference_calls':0}
    before,bm=worker.read_version(0);after,am=worker.read_version(number);bc,bh=context(before);cc,ch=context(after)
    identifier='exec-'+uuid.uuid4().hex;job=base/'executable-evaluations'/clock['trial_id']/identifier;job.mkdir(parents=True)
    atomic(job/'acceptance-private.json',cases)
    (job/'baseline-context.txt').write_text(bc);(job/'candidate-context.txt').write_text(cc)
    record={'schema':'executable-evaluation-v1','id':identifier,'trial_id':clock['trial_id'],
      'measurement_epoch':datetime.now(timezone.utc).date().isoformat(),'started_at':datetime.now(timezone.utc).isoformat(),'baseline_version':0,'candidate_version':number,'active_version_at_start':active,
      'comparison_kind':'IDENTICAL_INPUT_REFERENCE' if bh==ch else 'INDEPENDENT_MATCHED_IMPLEMENTATIONS',
      'contexts':{'baseline':{'sha256':bh,'spec_sha256':bm['sha256']},'candidate':{'sha256':ch,'spec_sha256':am['sha256']}},
      'suite':suite,'repetitions':repetitions,'providers':sorted(profile),'profiles':profile,
      'pins':pins,'harness_manifest_sha256':sha((base/'harness-manifest.json').read_bytes()),'engine':engine_snapshot(base),
      'sandbox_image':IMAGE,'version_input_groups':groups,'incompatible_versions':incompatible,'runs':[],
      'score_definition':'Quality=100 times mean of four workflow pass fractions; effectiveness=fully correct four-workflow artifacts; resource metrics retain failures. No single resource/quality blended score.',
      'oracle_independence':'Authored by controller/maintainer from contracts before implementations; not authored by evaluated executors. Private oracles never mounted in execution containers.',
      'limitations':['Selected four workflows only','Repeated implementations, not distinct user deliveries','Same corpus and requested native settings; actual served model may be unknown','Small samples are descriptive; no global optimum or real-user/market-fit proof']}
    record['waits']=waits;record['referenced_runs']=[];record['measurement_references']={}
    for old_path in sorted((base/'executable-evaluations'/clock['trial_id']).glob('*/report.json'),key=lambda p:p.stat().st_mtime):
        old=load(old_path)
        if old.get('measurement_epoch')!=record['measurement_epoch'] or old.get('suite')!=suite or old.get('profiles')!=profile or old['contexts']['candidate']['sha256']!=ch or old['repetitions']!=repetitions:continue
        for provider in record['providers']:
            # Freeze the first delivered implementation per matched cell,
            # including failed artifacts. Missing transports may be retried;
            # their previous cost/time observations remain included.
            prior=[r for r in record['referenced_runs'] if r['provider']==provider]
            seen_ids={r.get('native_receipt_id') or r.get('artifact_folder') for r in prior}
            known_cells={(r['repeat'],r['variant']) for r in prior if r.get('grade') is not None}
            for entry in old['runs']:
                if entry['provider']!=provider:continue
                identity=entry.get('native_receipt_id') or entry.get('artifact_folder')
                cell=(entry['repeat'],entry['variant'])
                if identity in seen_ids or (entry.get('grade') is not None and cell in known_cells):continue
                record['referenced_runs'].append(entry);seen_ids.add(identity)
                if entry.get('grade') is not None:known_cells.add(cell)
            if known_cells:record['measurement_references'][provider]=str(old_path)
    atomic(job/'plan.json',record)
    processes=[];started=time.monotonic()
    try:
        for provider in record['providers']:
            if provider not in available:continue
            prior=[r for r in record['referenced_runs'] if r['provider']==provider]
            if len([r for r in prior if r.get('grade') is not None])==2*repetitions:continue
            log=(job/(provider+'-controller.log')).open('w')
            proc=subprocess.Popen([sys.executable,str(base/'executable_benchmark.py'),'--child',str(job),'--provider',provider],stdout=log,stderr=subprocess.STDOUT)
            processes.append((proc,log,provider))
        last_progress=None
        while any(proc.poll() is None for proc,_,_ in processes):
            if time.monotonic()-started>3300:raise TimeoutError('Executable evaluation batch deadline')
            progress=tuple((job/(p+'-progress.json')).stat().st_mtime_ns if (job/(p+'-progress.json')).exists() else 0 for p in record['providers'])
            if progress!=last_progress:
                partial=collect(job);partial['status']='RUNNING_OR_PARTIAL';atomic(job/'report.json',partial);atomic(base/'executable-benchmark-latest.json',partial);last_progress=progress
            time.sleep(.25)
        for proc,log,provider in processes:log.close()
        record=collect(job);record['finished_at']=datetime.now(timezone.utc).isoformat();record['batch_wall_seconds']=time.monotonic()-started
        record['new_native_attempts']=len({e['native_receipt_id'] for e in record['runs'] if e.get('native_receipt_id')}-{e['native_receipt_id'] for e in record['referenced_runs'] if e.get('native_receipt_id')})
        unique={}
        for entry in record['runs']:
            receipts=entry.get('native_receipts') or ([{'id':entry['native_receipt_id'],'tokens':entry.get('tokens')}] if entry.get('native_receipt_id') else [])
            for receipt in receipts:
                if receipt.get('id'):unique[receipt['id']]=receipt
        referenced_ids={r.get('id') for e in record['referenced_runs'] for r in e.get('native_receipts',[]) if r.get('id')} | {e.get('native_receipt_id') for e in record['referenced_runs'] if e.get('native_receipt_id')}
        record['new_native_attempts']=len(set(unique)-referenced_ids)
        record['unique_measured_native_calls']=len(unique);record['unique_known_native_tokens']=sum(e.get('tokens') or 0 for e in unique.values())
        record['resource_scope_note']='Referenced runs retain original measurement costs and times; they are not new executions or new spend in this batch.'
        record['complete_pairs']=sum(v['paired_repetitions']==repetitions for v in record['scorecard']['providers'].values())
        record['complete_comparisons']=sum(v['candidate']['complete'] and v['baseline']['complete'] for v in record['scorecard']['providers'].values())
        # Blend CLI smoke score into overall_quality_score
        _cli = cli_smoke_score(base.parent/'runtime')
        _raw = record['scorecard'].get('overall_quality_score')
        record['scorecard']['cli_smoke_score'] = _cli['cli_smoke_score']
        record['scorecard']['cli_smoke_passing'] = _cli['cli_smoke_passing']
        record['scorecard']['cli_smoke_total'] = _cli['cli_smoke_total']
        record['scorecard']['cli_smoke_results'] = _cli['cli_smoke_results']
        record['scorecard']['cli_smoke_weight'] = 0.2
        record['scorecard']['raw_quality_score'] = _raw
        if _raw is not None:
            record['scorecard']['overall_quality_score'] = 0.8 * _raw + 0.2 * _cli['cli_smoke_score']
        atomic(job/'report.json',record);atomic(base/'executable-benchmark-latest.json',record)
        return record
    finally:
        for proc,log,provider in processes:
            if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
            if not log.closed:log.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--child');parser.add_argument('--provider',choices=('codex','claude'));args=parser.parse_args()
    if not args.child or not args.provider:parser.error('Internal evaluation worker requires child and provider')
    child(Path(args.child),args.provider)
