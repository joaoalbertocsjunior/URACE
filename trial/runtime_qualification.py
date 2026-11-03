"""Source-bound candidate qualification. Only trusted controller receipts authorize deployment."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,time,uuid,zipfile
from common import atomic
import runtime_evaluation as ev

SCHEMA='runtime-qualification-v1'

def test_manifest(base):
 root=Path(base).parent
 result={str(p.relative_to(root)):ev.sha(p) for folder in ('runtime/tests','trial') for p in sorted((root/folder).glob('*.py')) if not p.is_symlink()}
 for rel in ('runtime/README.md','runtime/pyproject.toml','runtime/portfolio-workflow.template.json'):
  artifact=root/rel
  if artifact.is_symlink():raise ValueError('Qualification support artifact symlink')
  if artifact.is_file():result[rel]=ev.sha(artifact)
 template=Path(base)/'runtime-qualification-config.json'
 if template.is_file() and not template.is_symlink():result['trial/runtime-qualification-config.json']=ev.sha(template)
 dependency=Path(base)/'qualification-dependencies.json'
 if dependency.is_file():
  result['trial/qualification-dependencies.json']=ev.sha(dependency)
  for name,expected in json.loads(dependency.read_text())['wheels'].items():
   if Path(name).name!=name or not name.endswith('.whl'):raise ValueError('Invalid qualification wheel name')
   wheel=Path(base)/'qualification-wheels'/name
   if wheel.is_symlink() or ev.sha(wheel)!=expected:raise ValueError('Qualification dependency changed')
   result['trial/qualification-wheels/'+name]=expected
 return result

def trusted_hashes(base):
 base=Path(base)
 return {n:ev.sha(base/n) for n in ('runtime_evaluation.py','runtime_qualification.py','runtime_cycle.py','runtime_trial.py','runtime_quality_gate.py','peer_runtime.py')}

def purpose(base):
 from source_integrity import projected
 base=Path(base);root=base.parent
 normative=root.parent/'URACE.md'
 contract=base/'contract.json'
 if normative.is_symlink() or contract.is_symlink():raise ValueError('Purpose source symlink')
 return ev.digest({'owner_contract':projected(root/'runtime/urace/config.json'),'normative_product_sha256':ev.sha(normative) if normative.exists() else None,'trial_contract_sha256':ev.sha(contract)})

def installation_ready(base):
 base=Path(base);p=base/'runtime-cycle-installation.json'
 try:
  data=json.loads(p.read_text())
  return data.get('qualified') is True and data.get('controllers')==trusted_hashes(base) and data.get('suite_sha256')==ev.digest(ev.contract()) and data.get('tests')==test_manifest(base)
 except (OSError,ValueError,KeyError):return False

def prepare_regression(base,candidate,destination):
 base=Path(base);destination=Path(destination);root=base.parent
 for rel in ('runtime/tests','trial'):
  for p in (root/rel).glob('*.py'):
   if p.is_symlink():raise ValueError('Acceptance source symlink')
   target=destination/'urace'/rel/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 dependency=base/'qualification-dependencies.json'
 if dependency.is_file():
  shutil.copyfile(dependency,destination/'urace/trial/qualification-dependencies.json')
  wheels=destination/'urace/trial/qualification-wheels';wheels.mkdir()
  for name,expected in json.loads(dependency.read_text())['wheels'].items():
   source=base/'qualification-wheels'/name
   if source.is_symlink() or ev.sha(source)!=expected:raise ValueError('Qualification dependency mismatch')
   shutil.copyfile(source,wheels/name)
   # Native dependency libraries are mapped from the immutable input bind mount,
   # not executable writable temporary storage. No network or installer hooks.
   dependencies=destination/'security-deps';dependencies.mkdir(exist_ok=True)
   with zipfile.ZipFile(source) as archive:
    for entry in archive.infolist():
     part=Path(entry.filename)
     if part.is_absolute() or '..' in part.parts or (entry.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe dependency archive path')
     archive.extract(entry,dependencies)
 ev.snapshot(candidate,destination/'urace/runtime/urace')
 template=base/'runtime-qualification-config.json'
 if template.is_symlink() or not template.is_file():raise ValueError('No sealed sanitized qualification configuration')
 shutil.copyfile(template,destination/'urace/runtime/urace/config.json')
 for rel in ('runtime/README.md','runtime/pyproject.toml','runtime/portfolio-workflow.template.json'):
  p=root/rel
  if p.is_file() and not p.is_symlink():shutil.copyfile(p,destination/'urace'/rel)
 for n in ('URACE.md','README.md','LICENSE'):
  p=root.parent/n
  if p.exists():
   if p.is_symlink():raise ValueError('Qualification document symlink')
   shutil.copyfile(p,destination/n)

REGRESSION_RUNNER=r'''
import os,sys,shutil,json,unittest,time,subprocess,hashlib
from pathlib import Path
shutil.copytree('/input','/tmp/product',ignore=shutil.ignore_patterns('security-deps'));os.environ['HOME']='/tmp';os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['PYTHONPATH']='/tmp/product/urace/runtime';os.chdir('/tmp/product/urace/runtime');sys.path.insert(0,os.getcwd())
dependency=Path('/tmp/product/urace/trial/qualification-dependencies.json')
if dependency.exists():
 manifest=json.loads(dependency.read_text());wheels=dependency.parent/'qualification-wheels'
 for name,expected in manifest['wheels'].items():
  assert hashlib.sha256((wheels/name).read_bytes()).hexdigest()==expected,'Dependency integrity failure'
 sys.path.insert(0,'/input/security-deps');os.environ['PYTHONPATH']='/input/security-deps:'+os.environ['PYTHONPATH']
 import cryptography
 assert cryptography.__version__==manifest['cryptography'],'Dependency version mismatch'
from urace import cli,_common
config=_common.load_config();path=_common.state_path(config);_common.atomic_write_json(path,cli.initial_state(config));before=path.read_bytes()
suite=unittest.defaultTestLoader.discover('tests',pattern='test*.py');expected=suite.countTestCases();start=time.monotonic()
with _common.state_lock(path):result=unittest.TextTestRunner(verbosity=0).run(suite)
summary={'tests':result.testsRun,'expected_tests':expected,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'wall_seconds':time.monotonic()-start,'installation_state_unchanged':path.read_bytes()==before}
os.chdir('/tmp/product/urace/trial');sys.path.insert(0,os.getcwd());trial_suite=unittest.defaultTestLoader.discover('.',pattern='test*.py');trial_expected=trial_suite.countTestCases();trial=unittest.TextTestRunner(verbosity=0).run(trial_suite);summary.update(trial_tests=trial.testsRun,trial_expected=trial_expected,trial_failures=len(trial.failures),trial_errors=len(trial.errors),trial_skipped=len(trial.skipped))
print('RUNTIME_REGRESSION_RESULT='+json.dumps(summary));sys.exit(0 if result.wasSuccessful() and trial.wasSuccessful() and summary['installation_state_unchanged'] else 1)
'''

def regression(base,candidate,folder):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);project=folder/'regression-input';project.mkdir();before=test_manifest(base);prepare_regression(base,candidate,project)
 name='urace-runtime-regression-'+uuid.uuid4().hex
 cmd=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--env','TZ=America/Sao_Paulo','--user',f'{os.getuid()}:{os.getgid()}','--pids-limit','128','--memory','1g','--memory-swap','1g','--cpus','1','--tmpfs','/tmp:rw,nosuid,size=256m','--mount',f'type=bind,src={project.resolve()},dst=/input,readonly',ev.IMAGE,'python3','-c',REGRESSION_RUNNER]
 log=folder/'regression.log';start=time.monotonic()
 try:
  with log.open('w') as stream:completed=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,timeout=900)
 except BaseException:
  subprocess.run(['docker','kill',name],capture_output=True,timeout=10);raise
 if before!=test_manifest(base):raise ValueError('Sealed regression source changed')
 rows=[json.loads(line.split('=',1)[1]) for line in log.read_text().splitlines() if line.startswith('RUNTIME_REGRESSION_RESULT=')]
 if len(rows)!=1:raise ValueError('Incomplete regression receipt')
 result=rows[0]
 result.update(returncode=completed.returncode,log_sha256=ev.sha(log),wall_seconds=time.monotonic()-start)
 result['passed']=completed.returncode==0 and result['failures']==result['errors']==0 and result['tests']==result['expected_tests'] and result['tests']>=1900 and result['skipped']<=1 and result['installation_state_unchanged'] is True and result['trial_tests']==result['trial_expected'] and result['trial_tests']>=354 and result['trial_failures']==result['trial_errors']==0 and result['trial_skipped']<=4
 return result

def qualify(base,before,candidate,baseline_id,proposal_receipt=None):
 base=Path(base);baseline=ev.load_receipt(base,baseline_id)
 if baseline['sources']!=ev.inventory(before):raise ValueError('Runtime baseline source is stale')
 files=ev.validate_sources(before,candidate)
 purpose_sha=purpose(base);manifest=test_manifest(base);controllers=trusted_hashes(base);suite=ev.digest(ev.contract());candidate_result=ev.measure(base,candidate,'candidate');public_candidate=ev.measure(base,candidate,'candidate_public',public=True)
 lost=[name for name,passed in baseline['case_results'].items() if passed and not candidate_result['case_results'][name]]
 from urace.tokenomics import canonical_fingerprint,outcome_fingerprint
 canon_fp=canonical_fingerprint({name:(candidate/name).read_text() for name in files})
 outcome_fp=outcome_fingerprint(baseline['engine_sha256'],files,candidate_result['score']-baseline['score'])
 result={'schema':SCHEMA,'id':'qualification-'+uuid.uuid4().hex,'at':ev.now(),'baseline_id':baseline_id,'candidate_id':candidate_result['id'],'candidate_public_id':public_candidate['id'],'before_sources':baseline['sources'],'candidate_sources':candidate_result['sources'],'files_changed':files,'suite_sha256':suite,'purpose_sha256':purpose_sha,'controllers':controllers,'tests':manifest,'baseline_score':baseline['score'],'candidate_score':candidate_result['score'],'delta':candidate_result['score']-baseline['score'],'lost_baseline_cases':lost,'proposal_receipt_id':proposal_receipt.get('id') if proposal_receipt else None,'proposal_receipt_sha256':ev.digest(proposal_receipt) if proposal_receipt else None,'regression':None,'accepted_evidence':False,'regression_reason':None,'canonical_fingerprint':canon_fp,'outcome_fingerprint':outcome_fp}
 folder=base/'runtime-qualifications'/result['id'];folder.mkdir(parents=True)
 if candidate_result['all_pass'] and public_candidate['all_pass'] and public_candidate['deterministic'] and candidate_result['deterministic'] and not lost:
  result['regression']=regression(base,candidate,folder)
  result['accepted_evidence']=result['regression']['passed']
 else:result['regression_reason']='Candidate private functional/robustness/determinism/nonregression contract did not pass'
 if purpose_sha!=purpose(base) or manifest!=test_manifest(base) or controllers!=trusted_hashes(base):raise ValueError('Qualification conditions changed during evaluation')
 result['sealed_candidate']='candidate';ev.snapshot(candidate,folder/'candidate');atomic(folder/'receipt.json',result)
 return result

def load_qualification(base,identifier):
 base=Path(base)
 if not isinstance(identifier,str) or not identifier.startswith('qualification-') or not identifier.replace('-','').isalnum():raise ValueError('Invalid qualification reference')
 folder=base/'runtime-qualifications'/identifier
 if folder.is_symlink() or (folder/'receipt.json').is_symlink():raise ValueError('Qualification symlink')
 result=json.loads((folder/'receipt.json').read_text())
 if result.get('schema')!=SCHEMA or result.get('id')!=identifier or result.get('suite_sha256')!=ev.digest(ev.contract()) or result.get('purpose_sha256')!=purpose(base) or result.get('controllers')!=trusted_hashes(base) or result.get('tests')!=test_manifest(base):raise ValueError('Runtime qualification conditions stale or incomplete')
 if (folder/'consumed.json').exists():raise ValueError('Qualification already used')
 baseline=ev.load_receipt(base,result['baseline_id']);candidate=ev.load_receipt(base,result['candidate_id']);public_candidate=ev.load_receipt(base,result['candidate_public_id'],public=True)
 if public_candidate['sources']!=candidate['sources'] or not public_candidate['all_pass'] or not public_candidate['deterministic']:raise ValueError('Public development contract did not pass')
 if result.get('before_sources')!=baseline['sources'] or result.get('candidate_sources')!=candidate['sources'] or ev.inventory(folder/'candidate')!=candidate['sources']:raise ValueError('Candidate/baseline source link mismatch')
 if result.get('baseline_score')!=baseline['score'] or result.get('candidate_score')!=candidate['score'] or result.get('delta')!=candidate['score']-baseline['score']:raise ValueError('Qualification score mismatch')
 if not candidate['all_pass'] or not candidate['deterministic'] or any(passed and not candidate['case_results'][name] for name,passed in baseline['case_results'].items()):raise ValueError('Candidate acceptance failed')
 regression_result=result.get('regression') or {};log=folder/'regression.log'
 if result.get('accepted_evidence') is not True or regression_result.get('passed') is not True or regression_result.get('returncode')!=0 or regression_result.get('failures')!=0 or regression_result.get('errors')!=0 or not log.is_file() or log.is_symlink() or ev.sha(log)!=regression_result.get('log_sha256'):raise ValueError('Missing immutable passing regression evidence')
 # Recheck the sealed machine result in the retained log instead of trusting passed=True.
 records=[json.loads(line.split('=',1)[1]) for line in log.read_text().splitlines() if line.startswith('RUNTIME_REGRESSION_RESULT=')]
 if len(records)!=1 or any(records[0].get(k)!=regression_result.get(k) for k in ('tests','expected_tests','failures','errors','skipped','installation_state_unchanged','trial_tests','trial_expected','trial_failures','trial_errors','trial_skipped')) or records[0]['tests']!=records[0]['expected_tests'] or records[0]['tests']<1900 or records[0]['skipped']>1 or records[0]['installation_state_unchanged'] is not True or records[0]['trial_tests']!=records[0]['trial_expected'] or records[0]['trial_tests']<354 or records[0]['trial_failures']!=0 or records[0]['trial_errors']!=0 or records[0]['trial_skipped']>4:raise ValueError('Regression transcript does not support qualification')
 if not result.get('proposal_receipt_id'):raise ValueError('Attributed runtime proposal receipt required for automatic deployment')
 if result.get('proposal_receipt_id'):
  path=base/'transport'/(result['proposal_receipt_id']+'.json')
  if path.is_symlink():raise ValueError('Proposal receipt symlink')
  proposal=json.loads(path.read_text())
  if ev.digest(proposal)!=result.get('proposal_receipt_sha256') or proposal.get('failure') or type(proposal.get('tokens')) is not int or proposal['tokens']<0 or proposal.get('role') not in ('RUNTIME_PROPOSAL','PEER_CANDIDATE') or proposal.get('product_id')!='urace-runtime:'+str(base.parent.resolve()):raise ValueError('Proposal resource/scope evidence incomplete')
 if proposal.get('role')=='PEER_CANDIDATE':
  from peer_runtime import validate_receipt
  validate_receipt(base,proposal)
 return result
