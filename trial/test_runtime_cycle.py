"""Isolated controller tests. Synthetic generation/regression receipts are NOT productive evidence."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile,time,unittest
import runtime_evaluation as ev,runtime_qualification as q,runtime_quality_gate as gate,runtime_trial as rt,runtime_cycle as cycle
from common import atomic

class Fixture:
 def __init__(self,directory,measured=True):
  self.root=Path(directory);self.root.mkdir(parents=True,exist_ok=True);self.base=self.root/'trial';self.base.mkdir();self.package=self.root/'runtime/urace';ev.snapshot(Path(__file__).parent.parent/'runtime/urace',self.package)
  self.config={'runtime_workflow':{'enabled':True,'quality_gate_minimum_score_delta':5.0},'authority':{'reserved':['change-purpose']},'state_path':str(self.root/'state.json')}
  atomic(self.package/'config.json',self.config);self.product_id='urace-runtime:'+str(self.root.resolve());atomic(self.base/'contract.json',{'product_id':'spec-fixture','target_product':'fixture','trial_id':'fixture'});atomic(self.base/'trial-clock.json',{'trial_id':'fixture','ends_unix':time.time()+3600});atomic(self.base/'products.json',{'products':[{'id':self.product_id,'kind':'runtime','improvement_enabled':True}]})
  for name in q.trusted_hashes(Path(__file__).parent):shutil.copyfile(Path(__file__).parent/name,self.base/name)
  # A deliberately defective fixture reproduces a real planning issue; it never touches live source.
  p=self.package/'milestone_suggestions.py';text=p.read_text();fixed="str(goal.get('status','')).upper() in ('ACHIEVED','COMPLETED','SUPERSEDED','CANCELLED')";old="goal.get('status') in ('ACHIEVED','COMPLETED','SUPERSEDED','CANCELLED')"
  self.fixed=text if fixed in text else text.replace(old,fixed)
  p.write_text(self.fixed.replace(fixed,old));self.before=ev.inventory(self.package);self.candidate=self.root/'candidate';ev.snapshot(self.package,self.candidate);(self.candidate/'milestone_suggestions.py').write_text(self.fixed)
  pins={'../runtime/urace/'+n:h for n,h in ev.inventory(self.package).items()};atomic(self.base/'harness-manifest.json',pins);atomic(self.base/'verification-latest.json',{'schema':'unit-fixture','source_sha256':{}})
  ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19];atomic(self.base/'trial-supervisor.json',{'pid':os.getpid(),'start_ticks':ticks});atomic(self.base/'supervisor-health.json',{'pid':os.getpid(),'running_tasks':[],'deployment_draining':True})
  atomic(self.base/'runtime-cycle-installation.json',{'qualified':True,'controllers':q.trusted_hashes(self.base),'suite_sha256':ev.digest(ev.contract()),'tests':q.test_manifest(self.base)})
  self.controls={'paused':False,'executor_enabled':True,'auto_goals':True}
  self.proposal={'id':'syntheticProposalFixture','kind':'finished','provider':'codex','role':'RUNTIME_PROPOSAL','product_id':self.product_id,'tokens':10,'wall_seconds':1,'failure':None,'evidence_class':'synthetic_unit_fixture'};atomic(self.base/'transport'/f"{self.proposal['id']}.json",self.proposal)
  self.baseline=None;self.certificate=None
  if measured:
   self.baseline=ev.measure(self.base,self.package,'baseline',runner=self.runner);atomic(self.base/'runtime-baseline-latest.json',{'evaluation_id':self.baseline['id']})
   with patch.object(ev,'container_run',side_effect=self.runner),patch.object(q,'regression',side_effect=self.regression):self.certificate=q.qualify(self.base,self.package,self.candidate,self.baseline['id'],self.proposal)
 def runner(self,package,requests):
  script=ev.RUNNER.replace("sys.path.insert(0,'/package')","sys.path.insert(0,"+repr(str(Path(package).parent))+')')
  # Package directory names differ for the candidate; the wrapper mounts it as urace.
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'urace';ev.snapshot(package,target);script=ev.RUNNER.replace("sys.path.insert(0,'/package')","sys.path.insert(0,"+repr(tmp)+')');r=subprocess.run([sys.executable,'-I','-c',script],input=json.dumps(requests),capture_output=True,text=True,check=True,timeout=15);return json.loads(r.stdout)
 def regression(self,base,candidate,folder):
  # Synthetic transcript exercises certificate parsing/transaction mechanics only.
  data={'tests':2000,'expected_tests':2000,'failures':0,'errors':0,'skipped':0,'installation_state_unchanged':True,'trial_tests':400,'trial_expected':400,'trial_failures':0,'trial_errors':0,'trial_skipped':0};log=Path(folder)/'regression.log';log.write_text('SYNTHETIC UNIT TRANSACTION FIXTURE; NOT A REAL QUALIFICATION RUN\nRUNTIME_REGRESSION_RESULT='+json.dumps(data)+'\n');return {**data,'returncode':0,'log_sha256':ev.sha(log),'passed':True,'wall_seconds':0,'evidence_class':'synthetic_unit_fixture'}
 def deploy(self):
  with patch('controls.effective',return_value=self.controls),patch.object(rt,'_update_metadata'),patch.object(rt,'_sync_snapshot'),patch.object(ev,'container_run',side_effect=self.runner):return rt.deploy(self.base,self.config,{'rationale':'Synthetic unit rollback/transaction fixture','proposer_provider':'fixture'}, {'qualification_id':self.certificate['id']})

class RuntimeEvidenceTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.fixture=Fixture(self.tmp.name)
 def test_source_bound_private_and_public_evidence(self):
  f=self.fixture;self.assertEqual(f.baseline['score'],95);r=q.load_qualification(f.base,f.certificate['id']);self.assertEqual(r['candidate_score'],100);self.assertEqual(r['delta'],5);self.assertTrue(r['accepted_evidence'])
 def test_legacy_spec_score_does_not_become_runtime_baseline(self):
  f=self.fixture;(f.base/'runtime-baseline-latest.json').unlink();atomic(f.base/'executable-benchmark-latest.json',{'scorecard':{'overall_quality_score':99}});self.assertIsNone(gate.read_latest_score(f.base))
 def test_forged_scalar_cannot_authorize(self):
  self.assertEqual(gate.gate_decision(self.fixture.base,self.fixture.config,100)['decision'],'GATE_UNAVAILABLE')
 def test_score_tamper_rejected(self):
  f=self.fixture;p=f.base/'runtime-evaluations'/f.certificate['candidate_id']/'receipt.json';r=json.loads(p.read_text());r['score']=99;atomic(p,r)
  with self.assertRaises(ValueError):q.load_qualification(f.base,f.certificate['id'])
 def test_receipt_source_tamper_rejected(self):
  f=self.fixture;p=f.base/'runtime-qualifications'/f.certificate['id']/'candidate/milestone_suggestions.py';p.write_text(p.read_text()+'\n# changed\n')
  with self.assertRaises(ValueError):q.load_qualification(f.base,f.certificate['id'])
 def test_regression_log_tamper_rejected(self):
  f=self.fixture;(f.base/'runtime-qualifications'/f.certificate['id']/'regression.log').write_text('forged')
  with self.assertRaises(ValueError):q.load_qualification(f.base,f.certificate['id'])
 def test_purpose_change_invalidates_qualification(self):
  f=self.fixture;f.config['authority']['reserved']=[];atomic(f.package/'config.json',f.config)
  with self.assertRaises(ValueError):q.load_qualification(f.base,f.certificate['id'])
 def test_caller_cannot_weaken_owner_delta(self):
  f=self.fixture;f.config['runtime_workflow']['quality_gate_minimum_score_delta']=10;atomic(f.package/'config.json',f.config)
  with self.assertRaises(rt.RuntimeDeploymentError):f.deploy()
 def test_candidate_loses_qualification_after_test_change(self):
  f=self.fixture;(f.base/'runtime_cycle.py').write_text('# changed controller')
  with self.assertRaises(ValueError):q.load_qualification(f.base,f.certificate['id'])
 def test_incomplete_proposal_usage_blocks_deployment(self):
  f=self.fixture;r={**f.proposal,'tokens':None};atomic(f.base/'transport'/f"{r['id']}.json",r)
  with self.assertRaises(ValueError):q.load_qualification(f.base,f.certificate['id'])

class RuntimeTransactionTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.fixture=Fixture(self.tmp.name)
 def test_accepted_isolated_transaction_records_and_consumes(self):
  f=self.fixture;sid=f.deploy();self.assertEqual(ev.inventory(f.package),f.certificate['candidate_sources']);self.assertEqual(rt.deployment_log(f.base)[-1]['event'],'DEPLOYED');self.assertTrue((f.base/'runtime-snapshots'/sid/'summary.json').exists())
  with self.assertRaises(ValueError):q.load_qualification(f.base,f.certificate['id'])
 def test_no_deployment_with_undrained_workers(self):
  f=self.fixture;atomic(f.base/'supervisor-health.json',{'pid':os.getpid(),'running_tasks':['study'],'deployment_draining':False})
  with self.assertRaises(rt.RuntimeDeploymentError):f.deploy()
  self.assertEqual(ev.inventory(f.package),f.before)
 def test_owner_disable_prevents_writes(self):
  f=self.fixture;atomic(f.base/'products.json',{'products':[{'id':f.product_id,'kind':'runtime','improvement_enabled':False}]})
  with self.assertRaises(rt.RuntimeDeploymentError):f.deploy()
  self.assertEqual(ev.inventory(f.package),f.before)
 def test_owner_pause_prevents_writes(self):
  f=self.fixture;f.controls['paused']=True
  with self.assertRaises(rt.RuntimeDeploymentError):f.deploy()
 def test_post_check_failure_rolls_back_only_changed_source(self):
  f=self.fixture;marker=f.root/'unrelated-owner-work.txt';marker.write_text('preserve')
  with patch.object(ev,'measure',side_effect=RuntimeError('injected post-check failure')):
   with self.assertRaises(RuntimeError):f.deploy()
  self.assertEqual(ev.inventory(f.package),f.before);self.assertEqual(marker.read_text(),'preserve');self.assertEqual(rt.deployment_log(f.base)[-1]['event'],'ROLLED_BACK')
 def test_metadata_failure_rolls_back(self):
  f=self.fixture
  with patch.object(rt,'_update_metadata',side_effect=OSError('injected metadata failure')),patch('controls.effective',return_value=f.controls),patch.object(rt,'_sync_snapshot'),patch.object(ev,'container_run',side_effect=f.runner):
   with self.assertRaises(OSError):rt.deploy(f.base,f.config,{'rationale':'fixture'},{'qualification_id':f.certificate['id']})
  self.assertEqual(ev.inventory(f.package),f.before)
 def test_rollback_preserves_unexpected_concurrent_source(self):
  f=self.fixture;name='milestone_suggestions.py';folder=f.base/'runtime-deployment-journals/transaction-fixture';(folder/'sources').mkdir(parents=True);shutil.copyfile(f.package/name,folder/'sources'/name);atomic(f.base/'runtime-deployment-transaction.json',{'id':'transaction-fixture','qualification_id':f.certificate['id'],'status':'PREPARED','files':{name:{'before':f.before[name],'after':f.certificate['candidate_sources'][name]}}});(f.package/name).write_text('# independent owner edit')
  with self.assertRaises(rt.RuntimeDeploymentError):rt.recover(f.base)
  self.assertEqual((f.package/name).read_text(),'# independent owner edit')

class RuntimeScopeTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.fixture=Fixture(self.tmp.name,False)
 def test_forbidden_module_cannot_change(self):
  f=self.fixture;(f.candidate/'authority.py').write_text('# changed')
  with self.assertRaises(ValueError):ev.validate_sources(f.package,f.candidate)
 def test_import_or_global_change_cannot_change(self):
  f=self.fixture;p=f.candidate/'milestone_suggestions.py';p.write_text('import os\n'+p.read_text())
  with self.assertRaises(ValueError):ev.validate_sources(f.package,f.candidate)
 def test_new_files_or_deletion_blocked(self):
  f=self.fixture;(f.candidate/'new.py').write_text('# new')
  with self.assertRaises(ValueError):ev.validate_sources(f.package,f.candidate)
 def test_source_symlink_blocked(self):
  f=self.fixture;p=f.candidate/'milestone_suggestions.py';p.unlink();p.symlink_to(f.package/'milestone_suggestions.py')
  with self.assertRaises(ValueError):ev.validate_sources(f.package,f.candidate)
 def test_scope_does_not_allow_self_widening_or_absolute_optimality_claim(self):
  for module in ('cli.py','authority.py','runtime_cycle.py','runtime_quality_gate.py'):self.assertNotIn(module,ev.ALLOWED)

class RuntimeSchedulerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=Fixture(self.tmp.name,False);self.stack=__import__('contextlib').ExitStack();self.addCleanup(self.stack.close);self.stack.enter_context(patch('controls.effective',return_value=self.f.controls));self.stack.enter_context(patch.object(ev,'container_run',side_effect=self.f.runner))
 def test_no_public_defect_completes_without_model_request_and_waits(self):
  f=self.f;(f.package/'milestone_suggestions.py').write_text(f.fixed);atomic(f.base/'harness-manifest.json',{'../runtime/urace/'+n:h for n,h in ev.inventory(f.package).items()})
  with patch.object(cycle,'proposal',side_effect=AssertionError('No justified native work')):
   result=cycle.step(f.base);self.assertEqual(result['status'],'NO_JUSTIFIED_CHANGE');self.assertEqual(result['completed_cycles'],1);self.assertEqual(result['inference_calls'],0);self.assertEqual(cycle.step(f.base)['status'],'WAITING')
 def test_deferred_executor_retains_cycle_and_no_failed_delivery_claim(self):
  f=self.f
  with patch.object(cycle,'proposal',return_value={'status':'DEFERRED','reason':'ordinary backoff','inference_calls':0}) as call:
   result=cycle.step(f.base);self.assertEqual(result['status'],'WAITING');self.assertEqual(result['inference_calls'],0);self.assertNotIn('completed_at',result);self.assertEqual(call.call_count,1);self.assertEqual(cycle.step(f.base)['status'],'WAITING');self.assertEqual(call.call_count,1)
 def test_disabled_product_never_evaluates_or_calls_model(self):
  f=self.f;atomic(f.base/'products.json',{'products':[{'id':f.product_id,'kind':'runtime','improvement_enabled':False}]})
  with patch.object(ev,'measure',side_effect=AssertionError('Disabled')),patch.object(cycle,'proposal',side_effect=AssertionError('Disabled')):self.assertEqual(cycle.step(f.base)['status'],'DISABLED')
 def test_owner_pause_preserves_clock_and_defers(self):
  f=self.f;before=(f.base/'trial-clock.json').read_bytes();f.controls['paused']=True;self.assertEqual(cycle.step(f.base)['status'],'WAITING');self.assertEqual((f.base/'trial-clock.json').read_bytes(),before)
 def test_approval_reuses_certificate_without_another_native_request(self):
  f=Fixture(Path(self.tmp.name)/'approval');state={'id':'cycle-fixture','stage':'AWAITING_APPROVAL','qualification_id':f.certificate['id'],'engine_sha256':ev.engine(f.package),'proposal_reason':'fixture repair','proposal_provider':'codex','next_due_unix':time.time()+10000};atomic(f.base/'runtime-cycle-latest.json',state)
  f.config['runtime_workflow']['auto_deploy']=True;atomic(f.package/'config.json',f.config)
  with patch.object(cycle,'proposal',side_effect=AssertionError('Already qualified')):
   self.assertEqual(cycle.step(f.base)['status'],'READY_TO_DEPLOY');self.assertEqual(json.loads((f.base/'runtime-deployment-pending.json').read_text())['qualification_id'],f.certificate['id'])

class RuntimeIdleCostTests(unittest.TestCase):
 def test_scheduled_idle_does_not_rehash_all_sources_or_call_executor(self):
  with tempfile.TemporaryDirectory() as d:
   f=Fixture(d,False);(f.package/'milestone_suggestions.py').write_text(f.fixed);atomic(f.base/'harness-manifest.json',{'../runtime/urace/'+n:h for n,h in ev.inventory(f.package).items()})
   with patch('controls.effective',return_value=f.controls),patch.object(ev,'container_run',side_effect=f.runner),patch.object(cycle,'proposal',side_effect=AssertionError('No defect')):self.assertEqual(cycle.step(f.base)['status'],'NO_JUSTIFIED_CHANGE')
   with patch('controls.effective',return_value=f.controls),patch.object(ev,'engine',side_effect=AssertionError('Idle must not rescan content')),patch.object(cycle,'_pins',side_effect=AssertionError('No execution while waiting')):self.assertEqual(cycle.step(f.base)['status'],'WAITING')
