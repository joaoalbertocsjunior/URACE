"""Self-contained version evidence and explicitly scoped runtime/product rollups."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,platform,resource,sys,time,os
from common import atomic, evidence_path

SCHEMA='urace-analysis-v1'
FEATURES={
 'product_identity':'identity','version_lineage':'lineage','product_changes':'changes',
 'quality_validation':'validation','source_context':'task','goal_selection':'task',
 'executor_transport':'executors','resource_accounting':'resources','time_accounting':'timing',
 'runtime_implementation':'engine','configuration':'configuration','authority_policy':'configuration',
 'scoring_methodology':'efficiency','custom_metrics':'efficiency','scheduler_supervision':'operations',
 'publication_recovery':'publication','environment':'environment','rejected_work':'trial_outcomes',
}

def load(p,default=None):return json.loads(p.read_text()) if p.exists() else default
def sha(data):return hashlib.sha256(data).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()

def durable_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())

def verify_engine(reference):
    root=evidence_path(reference['path']);manifest=load(root/'manifest.json')
    if sha((root/'manifest.json').read_bytes())!=reference['manifest_sha256']:raise RuntimeError('Engine manifest corruption')
    for item in manifest['files']:
        path=(root/item['snapshot_file']).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path.read_bytes())!=item['sha256']:raise RuntimeError('Engine evidence corruption')
    return True

def engine_snapshot(base):
    from source_integrity import matches
    raw=(base/'harness-manifest.json').read_bytes();expected=json.loads(raw)
    actual={name:sha((base/name).read_bytes()) for name in expected}
    identifier=sha(json.dumps({'harness':sha(raw),'actual':actual},sort_keys=True).encode());root=base/'engine-versions'/identifier
    for name,value in expected.items():
        if not matches(base/name,value):raise RuntimeError('Engine source changed before capture: '+name)
    if (root/'manifest.json').exists():
        manifest=load(root/'manifest.json')
        for entry in manifest['files']:
            if sha((root/entry['snapshot_file']).read_bytes())!=entry['sha256']:raise RuntimeError('Engine snapshot corruption')
        return {'id':identifier,'path':str(root),'manifest_sha256':sha((root/'manifest.json').read_bytes()),'code_fingerprint':manifest['code_fingerprint']}
    root.mkdir(parents=True,exist_ok=True);files=[]
    for i,(name,value) in enumerate(sorted(expected.items())):
        source=base/name;data=source.read_bytes()
        if not matches(source,value) or sha(data)!=actual[name]:raise RuntimeError('Engine source changed before snapshot: '+name)
        target='files/'+str(i)+'-'+source.name;durable_write(root/target,data)
        files.append({'original_path':str(source),'snapshot_file':target,'sha256':sha(data),'bytes':len(data),'integrity_contract':value})
    code={f['original_path']:f['sha256'] for f in files if Path(f['original_path']).suffix in ('.py','.service','.timer') or Path(f['original_path']).name=='urace'}
    durable_write(root/'harness-manifest.json',raw);atomic(root/'manifest.json',{'schema':SCHEMA,'created_at':now(),'files':files,'code_fingerprint':sha(json.dumps(code,sort_keys=True).encode())})
    return {'id':identifier,'path':str(root),'manifest_sha256':sha((root/'manifest.json').read_bytes()),'code_fingerprint':sha(json.dumps(code,sort_keys=True).encode())}

def trial_resources(base,trial_id,product_id=None):
    path=base/'ledger.jsonl';rows=[json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []
    from core_resources import events as core_events
    contract=load(base/'contract.json',{})
    additional=core_events(base,product_id or contract.get('product_id'),trial_id,load(base/'trial-clock.json',{}).get('started_unix'))
    rows += additional
    rows=[r for r in rows if r.get('trial_id')==trial_id and (product_id is None or r.get('product_id')==product_id)];reserved={r['id']:r for r in rows if r.get('kind')=='reserved'};done={r['id']:r for r in rows if r.get('kind')=='finished'}
    def totals(ids):return {'calls':len(ids),'known_tokens':sum(done.get(i,{}).get('tokens') or 0 for i in ids),'unknown_usage_calls':sum(done.get(i,{}).get('tokens') is None for i in ids),'known_executor_wall_seconds':sum(done.get(i,{}).get('wall_seconds') or 0 for i in ids),'inflight_calls':sum(i not in done for i in ids)}
    return {'ledger_filtered_event_count':len(rows),'ledger_filtered_sha256':sha(json.dumps(rows,sort_keys=True).encode()),'ledger_replay_method':'Filter by trial/product, take first recorded event count, verify canonical JSON SHA256; rejected and unfinished attempts retained',**totals(reserved),'providers':{p:totals([i for i,r in reserved.items() if r['provider']==p]) for p in ('codex','claude')},'scope':'Current trial only; all attempts included, including rejected work','subscription_credit_charge':None,'subscription_credit_charge_reason':'Native tokens do not establish actual subscription billing','controller_chat_and_operator_tokens':None,'controller_chat_and_operator_tokens_reason':'Not observable by the managed executor ledger'}

def create(base,folder,manifest,task=None):
    base=Path(base);folder=Path(folder);task=task or {};contract=load(base/'contract.json',{});clock=load(base/'trial-clock.json',{});epoch=load(base/'accounting-epoch.json',{});state=load(base/'state.json',{'jobs':[]});trial=clock.get('trial_id');engine=engine_snapshot(base)
    metadata={'schema':SCHEMA,'recorded_at':now(),'scope':'one product version and its producing runtime','identity':{'product':contract.get('target_product','URACE.md'),'product_id':contract.get('product_id'),'trial_id':trial,'baseline_commit':manifest['baseline_commit'],'version':manifest['version'],'content_sha256':manifest['sha256']},'lineage':{'parent_version':manifest.get('parent_version'),'parent_sha256':manifest.get('parent_sha256'),'baseline_sha256':manifest.get('baseline_sha256'),'version_series':load(base/'version-series.json',{'root':'versions'})},'changes':manifest.get('comparison',{'classification':'exact committed baseline; no improvement'}),'validation':{'model_review':manifest.get('validation'),'method':('Exact earlier immutable source restoration after independent audit disagreement; not a new quality gain' if manifest.get('restoration') else 'Static preserved requirements/headings/code examples; model-supported failure case, material gain and no dimension regression'),'scope':'Bounded editorial correctness and quality judgments; not executed product behavior or customer evidence','quality_policy':task.get('quality_policy','legacy-editorial'), 'customer_value_proven':False,'market_fit_proven':False},'task':task,'executors':[],'resources':{'producing_task':manifest.get('resources',{}),'trial_to_capture':trial_resources(base,trial,contract.get('product_id'))},'timing':{'captured_at':now(),'trial_started_at':clock.get('started_at'),'task_started_at':task.get('started_at'),'snapshot_prepared_at':manifest.get('accepted_at'),'trial_elapsed_seconds':max(0,time.time()-clock.get('started_unix',time.time())),'task_final_completion_at':None,'task_final_completion_reason':'Snapshot captured before final worker journal commit; completion receipt is linked separately'},'engine':engine,'configuration':{'contract':contract,'settings':load(base/'settings.json',{}),'accounting_epoch':epoch,'shared_resource_policy':'Frozen in engine bundle; no aggregate spending caps unless explicitly configured'},'efficiency':{'score_configuration':load(base/'efficiency-config.json',{'profiles':{}}),'interpretation':'User-defined formulas are provisional; missing usage and sparse samples limit inference','held_out_calibration':None,'held_out_calibration_reason':'Not established'},'operations':{'last_observed_status':load(base/'status.json',{}),'scheduler_configuration':'Frozen service/timer files in engine bundle','current_host_failover_guaranteed':False},'publication':{'method':'Prepared snapshot directory then atomic rename, followed by atomic active pointer','current_task_journal_finalized':False},'environment':{'python':sys.version,'platform':platform.platform(),'controller_user_cpu_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime,'controller_system_cpu_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_stime,'controller_max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'cpu_scope':'Snapshot publisher process only; remote model CPU/GPU not observable'},'trial_outcomes':{'completed_tasks_before_this_publication':len([j for j in state['jobs'] if j.get('trial_id')==trial]),'outcomes_before_publication':[{'id':j['id'],'outcome':j['outcome']} for j in state['jobs'] if j.get('trial_id')==trial]},'artifacts':[]}
    from controls import effective
    metadata['configuration']['operator_controls']=effective(base)
    # Never embed old-trial operational results into the new trial's snapshot.
    status=metadata['operations']['last_observed_status']
    if status.get('clock',{}).get('trial_id')!=trial:metadata['operations']['last_observed_status']={'available':False,'reason':'No current-trial observation at capture'}
    if manifest['version']==0:
        metadata['timing']['task_final_completion_reason']='Exact committed baseline; no executor task produced this version'
        metadata['publication']['current_task_journal_finalized']=True
    job=Path(manifest['job']) if manifest.get('job') else None
    if job and job.is_dir():
        for source in sorted(job.iterdir()):
            if not source.is_file() or source.suffix not in ('.json','.txt'):continue
            data=source.read_bytes();target=folder/'evidence'/source.name;target.parent.mkdir(exist_ok=True);target.write_bytes(data)
            metadata['artifacts'].append({'path':str(target.relative_to(folder)),'sha256':sha(data),'bytes':len(data)})
            if source.name.endswith('-native.json'):metadata['executors'].append(load(source))
    current_metrics=[];custom=base/'custom-metrics.jsonl'
    if custom.exists():current_metrics=[r for line in custom.read_text().splitlines() if line for r in [json.loads(line)] if r.get('product_id')==contract.get('product_id') and r.get('accounting_epoch_id')==epoch.get('id')]
    metadata['efficiency']['custom_metrics']=current_metrics
    from core_resources import events as core_events
    metadata['resources']['additional_core_receipts'] = core_events(base,contract.get('product_id'),trial,clock.get('started_unix'))
    schema={'id':SCHEMA,'required_sections':sorted(set(FEATURES.values())),'required_feature_inventory':FEATURES,'unknown_values_policy':'Null plus explicit reason; never infer successful outcomes or missing resource usage'}
    atomic(folder/'metadata-schema.json',schema)
    for name in ('URACE.md','parent.diff','baseline.diff','metadata-schema.json'):
        path=folder/name
        if path.exists():metadata['artifacts'].append({'path':name,'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size})
    metadata['feature_coverage']={name:{'section':section,'present':section in metadata,'evidence_status':'recorded_or_explicitly_unavailable'} for name,section in FEATURES.items()}
    metadata['scope_index']={'product_results':['identity','lineage','changes','validation','task','trial_outcomes','artifacts'],'runtime_operation':['executors','resources','timing','engine','configuration','efficiency','operations','publication','environment']}
    metadata['schema_fields']=sorted(set(FEATURES.values()));validate(metadata);atomic(folder/'metadata.json',metadata)
    return sha((folder/'metadata.json').read_bytes())

def validate(metadata):
    if metadata.get('schema')!=SCHEMA:raise ValueError('Unknown metadata schema')
    for name,section in FEATURES.items():
        if section not in metadata or name not in metadata.get('feature_coverage',{}):raise ValueError('Missing metadata feature: '+name)
    return True

def finalize(base,folder,report):
    folder=Path(folder);record={'schema':SCHEMA,'version':load(folder/'manifest.json')['version'],'metadata_sha256':sha((folder/'metadata.json').read_bytes()),'task_id':report['id'],'task_finished_at':report['finished_at'],'task_outcome':report['outcome'],'report':report,'recorded_at':now()}
    path=folder/'completion.json'
    if path.exists():
        if load(path).get('task_id')!=report['id']:raise RuntimeError('Snapshot completion identity conflict')
        return
    record['record_sha256']=sha(json.dumps(record,sort_keys=True).encode())
    atomic(path,record)

def executable_measurement_view(base):
    """Separate retained historical measurements from current compatible evidence."""
    base=Path(base);record=load(base/'executable-benchmark-latest.json',{})
    if not record.get('suite'):
        return {'available':False,'status':'NOT_MEASURED','reason':'No executable implementation evaluation yet'},None
    from executable_cases import corpus,manifest
    reasons=[]
    if record['suite']!=manifest(corpus()):reasons.append('EVALUATOR_OR_CORPUS_CHANGED')
    if not reasons:
        try:
            from executable_benchmark import context,profiles
            from controls import effective
            active=load(base/'active-version.json')['version']
            series=(base/load(base/'version-series.json')['root']).resolve()
            if not series.is_relative_to((base/'versions').resolve()):raise ValueError('Version storage escape')
            text=(series/f'v{active:06d}'/'URACE.md').read_text()
            signature=context(text)[1]
            if not any(v.get('sha256')==signature for v in record.get('contexts',{}).values()):reasons.append('PRODUCT_CONTEXT_CHANGED')
            if record.get('profiles')!=profiles(effective(base)):reasons.append('EXECUTOR_PROFILE_CHANGED')
        except (OSError,KeyError,ValueError,TypeError):reasons.append('CURRENT_CONTEXT_OR_PROFILE_UNAVAILABLE')
    if reasons:
        return {'available':False,'status':'STALE_MEASUREMENT','reason':reasons,'historical_evaluation_id':record.get('id'),'current_quality_score':None},record
    # The active input can match the baseline rather than the recorded candidate.
    # Use the canonical version-aware projection instead of relabeling that candidate.
    from executable_scores import view
    current=view(base=base)
    if 'scorecard' not in current:
        return {'available':False,'status':'NOT_MEASURED','reason':'No compatible current scorecard','historical_evaluation_id':record.get('id')},record
    matched={name:row['matched_profile'] for name,row in current['scorecard']['providers'].items()}
    if matched!=record.get('profiles'):
        return {'available':False,'status':'STALE_MEASUREMENT','reason':['EXECUTOR_PROFILE_CHANGED'],'historical_evaluation_id':record.get('id')},record
    return {**record,'available':True,'current_compatible_measurement':True,
            'scorecard':current['scorecard'],'active_version_projection':{k:current.get(k) for k in ('version','measured_version','status','new_execution_for_this_version','artifact_report')}},None

def rollups(base, period='3h'):
    from product_resources import report,overall
    from efficiency_score import score
    base=Path(base);contract=load(base/'contract.json');clock=load(base/'trial-clock.json');root=base/'reports/trials'/clock['trial_id'];root.mkdir(parents=True,exist_ok=True)
    product=report(contract['product_id'],'trial');runtime=overall('trial');engine=engine_snapshot(base)
    state=load(base/'state.json',{'jobs':[]});jobs=[j for j in state['jobs'] if j.get('trial_id')==clock['trial_id']];rows=[];ledger=base/'ledger.jsonl'
    if ledger.exists():rows=[r for line in ledger.read_text().splitlines() if line for r in [json.loads(line)] if r.get('trial_id')==clock['trial_id']]
    from core_resources import events as core_events
    from period_feedback import compare
    rows += core_events(base,contract.get('product_id'),clock['trial_id'],clock.get('started_unix'))
    feedback=compare(rows,jobs,time.time(),period)
    outcomes={name:sum(j['outcome']==name for j in jobs) for name in sorted({j['outcome'] for j in jobs})}
    receipt_index=[{**{k:r.get(k) for k in ('id','provider','tokens','wall_seconds','failure','effort','client_version')},'raw_receipt':r.get('receipt_source') or str(base/'transport'/(r['id']+'.json')),'semantic_sha256':sha(json.dumps(r,sort_keys=True).encode())} for r in rows if r.get('kind')=='finished']
    artifacts=[]
    for job in jobs:
        p=base/'runs'/clock['trial_id']/job['id']/'report.json'
        if p.exists():artifacts.append({'task_id':job['id'],'path':str(p),'sha256':sha(p.read_bytes())})
    executable,historical_executable=executable_measurement_view(base)
    from assessment_evidence import assess
    from project_work import engine_hash
    comprehensive=assess(base,rows,time.time(),engine_sha256=engine_hash(),execution_sha256=engine['code_fingerprint'])
    for scope,value in (('product-overall',product),('runtime-overall',runtime)):
        value.update(primary_measurement='executable workflows',executable_evaluation=executable,historical_executable_evaluation=historical_executable,downstream_diagnostic=load(base/'benchmark-latest.json',{'available':False,'reason':'No native paired diagnostic yet'}),quality_audit=load(base/'quality-audit-latest.json',{'available':False,'reason':'No audit yet'}),metadata_schema=SCHEMA,analysis_scope=scope,trial_id=clock['trial_id'],engine=engine,efficiency_score=score(value),feature_inventory=FEATURES,version_comparisons=load(base/'version-comparisons.json',{}),period_comparison=feedback,data_scope='Current trial only; lifetime/history requires explicit request')
        value['comprehensive_assessment']=comprehensive
        scoped_jobs=[j for j in jobs if scope=='runtime-overall' or j.get('product_id')==value.get('product_id')]
        scoped_receipts=[r for r in rows if r.get('kind')=='finished' and (scope=='runtime-overall' or r.get('product_id')==value.get('product_id'))]
        scoped_ids={j['id'] for j in scoped_jobs};scoped_artifacts=[a for a in artifacts if a['task_id'] in scoped_ids]
        scoped_receipt_ids={r['id'] for r in scoped_receipts};scoped_index=[item for item in receipt_index if item['id'] in scoped_receipt_ids]
        value['analysis_metadata']={'schema':SCHEMA,'identity':{'scope':scope,'trial_id':clock['trial_id'],'product_id':value.get('product_id'),'registered_products':load(base/'products.json',{})},'lineage':value['version_comparisons'],'changes':{'accepted_improvements':value['accepted_improvements'],'active_version':load(base/'active-version.json',{})},'validation':{'acceptance_contract':contract.get('acceptance'),'model_judgments_are_not_real_user_proof':True,'quality_policy':'See per-task source-bound metadata', 'customer_value_proven':False,'held_out_calibration':None,'unavailable_reason':'External outcome validation not collected'},'task':{'completed':len(scoped_jobs),'inflight':state.get('inflight'),'task_reports':scoped_artifacts},'executors':{'receipt_index':scoped_index,'provider_metrics':value['providers']},'resources':trial_resources(base,clock['trial_id'],value.get('product_id') if scope=='product-overall' else None),'timing':{'clock':clock,'elapsed_seconds':value['elapsed_seconds'],'task_intervals':[{'id':j['id'],'started_at':j.get('started_at'),'finished_at':j.get('finished_at')} for j in scoped_jobs]},'engine':engine,'configuration':{'contract':contract,'settings':load(base/'settings.json',{}),'accounting_epoch':load(base/'accounting-epoch.json',{})},'efficiency':value['efficiency_score'],'operations':{'status':load(base/'status.json',{}),'unit_configuration':'Captured in engine bundle'},'publication':{'active_version':load(base/'active-version.json',{}),'incomplete_staging_directories':[str(p) for p in (base/'versions').rglob('*.pending')]},'environment':{'python':sys.version,'platform':platform.platform(),'remote_model_cpu_gpu':None,'unavailable_reason':'Not reported by native providers'},'trial_outcomes':{name:sum(j['outcome']==name for j in scoped_jobs) for name in outcomes},'artifacts':scoped_artifacts,'feature_coverage':{name:{'section':section,'present':True,'evidence_status':'recorded_or_explicitly_unavailable'} for name,section in FEATURES.items()}}
        validate(value['analysis_metadata'])
        atomic(root/(scope+'.json'),value)
    return {'product_overall':str(root/'product-overall.json'),'runtime_overall':str(root/'runtime-overall.json')}

def inspect_snapshot(folder):
    folder=Path(folder);manifest=load(folder/'manifest.json');metadata=load(folder/'metadata.json')
    if metadata is None:raise ValueError('Snapshot predates full metadata; original manifest is preserved in history')
    validate(metadata)
    if sha((folder/'URACE.md').read_bytes())!=manifest['sha256']:raise RuntimeError('Snapshot content hash mismatch')
    if sha((folder/'metadata.json').read_bytes())!=manifest['metadata_sha256']:raise RuntimeError('Snapshot metadata hash mismatch')
    for item in metadata['artifacts']:
        path=(folder/item['path']).resolve()
        if not path.is_relative_to(folder.resolve()) or sha(path.read_bytes())!=item['sha256']:raise RuntimeError('Snapshot evidence corruption')
    completion=load(folder/'completion.json')
    if completion and completion['metadata_sha256']!=manifest['metadata_sha256']:raise RuntimeError('Completion metadata linkage mismatch')
    if completion and sha(json.dumps({k:v for k,v in completion.items() if k!='record_sha256'},sort_keys=True).encode())!=completion.get('record_sha256'):raise RuntimeError('Completion record corruption')
    verify_engine(metadata['engine'])
    return {'manifest':manifest,'metadata':metadata,'completion':completion,'integrity_verified':True,'resolved_references':{'snapshot':str(folder.resolve()),'engine':str(evidence_path(metadata['engine']['path'])),'producing_task':str(evidence_path(manifest['job'])) if manifest.get('job') else None}}
