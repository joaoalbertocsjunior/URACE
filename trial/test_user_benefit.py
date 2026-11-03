"""Fault-injection orchestration tests; not real-user or native performance evidence."""
from pathlib import Path
import json,tempfile,time,unittest,hashlib,os
from unittest.mock import patch
import project_work as work,project_tools as tools,repository_tasks as tasks,repository_study as study
from urace.work_policy import choose,execution_mode,outcomes

class PolicyTests(unittest.TestCase):
 def policy(self):return {'cohort':'qualified-fixture','models':{'codex':'m'},'contracts':{'f':'c'},'engine_sha256':'e','expires_unix':100,'recommendations':[{'provider':'codex','family':'f','samples':40,'native_effort':'low','quality_nonregressing':True,'usage_complete':True,'timing_complete':True,'time_ratio':.75,'token_ratio':.9}]}
 def select(self,p,**kwargs):return choose(p,provider='codex',family='f',model='m',contract='c',engine='e',default_effort='medium',now=50,**kwargs)
 def test_only_qualified_exact_contract_can_change_profile(self):self.assertEqual(self.select(self.policy())['native_effort'],'low')
 def test_expired_or_mismatched_evidence_cannot_change_profile(self):
  for key,value in [('engine_sha256','different'),('expires_unix',40),('models',{'codex':'other'}),('contracts',{'f':'changed'})]:
   p=self.policy();p[key]=value;self.assertFalse(self.select(p)['adaptive'])
 def test_quality_regression_or_incomplete_usage_withholds_adaptation(self):
  for key,value in [('quality_nonregressing',False),('usage_complete',False),('samples',3),('token_ratio',1.2)]:
   p=self.policy();p['recommendations'][0][key]=value;self.assertFalse(self.select(p)['adaptive'])
 def test_quarantine_and_owner_disable_are_authoritative(self):
  self.assertFalse(self.select(self.policy(),quarantined=True)['adaptive']);self.assertFalse(self.select(self.policy(),enabled=False)['adaptive'])
 def test_simple_tasks_use_lightweight_path(self):
  self.assertEqual(execution_mode('auto',requirements=[{'id':'one'}]),'lightweight');self.assertEqual(execution_mode('auto',requirements=[{'id':'one'}],continuity=True),'managed')
 def test_elapsed_throughput_includes_waiting_and_failed_costs(self):
  rows=[{'complete':True,'validated':True,'native_receipts':[{'id':'a','tokens':10}]},{'complete':True,'validated':False,'native_receipts':[{'id':'b','tokens':20}]}];r=outcomes(rows,7200);self.assertEqual(r['validated_per_elapsed_hour'],.5);self.assertEqual(r['tokens_per_validated_delivery'],30);self.assertIsNone(r['human_seconds'])
 def test_unknown_usage_is_not_zero_cost(self):self.assertIsNone(outcomes([{'complete':True,'validated':True,'native_receipts':[{'id':'a','tokens':None}]}],1)['tokens_per_validated_delivery'])

class ToolBoundaryTests(unittest.TestCase):
 def test_escape_and_symlink_read_are_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'workspace';root.mkdir();(root/'bad').symlink_to(Path(d)/'outside')
   for name in ['../outside','/etc/passwd','bad']:
    with self.assertRaises(ValueError):tools.confined(root,name)
 def test_write_scope_is_enforced(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):tools.call({'workspace':d,'allowed_files':['logic.py']},'write_file',{'path':'owner.txt','content':'overwrite'})
 def test_acceptance_is_distinct_and_sealed_before_generation(self):
  for f in tasks.FAMILIES:
   self.assertTrue({r['id'] for r in tasks.cases(f,True)}.isdisjoint(r['id'] for r in tasks.cases(f,False)));self.assertEqual(len(tasks.cases(f,False)),96);self.assertEqual(tasks.contract(f),tasks.contract(f))
 def test_requirement_revision_changes_executable_contract(self):self.assertNotEqual(tasks.contract('requirements_change',1),tasks.contract('requirements_change',2))

class ProjectWorkTests(unittest.TestCase):
 def setup_project(self,d):
  root=Path(d);base=root/'trial';base.mkdir();project=root/'project';manifest=work.initialize(project,'navigation',base);(base/'trial-clock.json').write_text(json.dumps({'trial_id':'fixture','ends_unix':time.time()+3600}));(base/'qualified.py').write_text('# qualified fixture');(base/'harness-manifest.json').write_text(json.dumps({'qualified.py':hashlib.sha256((base/'qualified.py').read_bytes()).hexdigest()}));controls={'paused':False,'executor_enabled':True,'auto_goals':True,'executors':{p:{'enabled':True,'model':'fixture','native_effort':'medium'} for p in ['codex','claude']}};return base,project,controls
 def invoke(self,p,prompt,workspace,checks,allowed,**kwargs):
  self.assertNotIn('acceptance-',prompt);self.assertFalse((workspace/'sealed-acceptance.json').exists());self.assertTrue(checks.exists());self.calls.append(p)
  (workspace/'logic.py').write_text('def compute(request): return None\n');return {},None,{'id':'receipt-'+str(len(self.calls)),'provider':p,'tokens':10,'wall_seconds':1,'requested_model':kwargs['model'],'effort':kwargs['effort']}
 def execute(self,*args,**kwargs):return {'returncode':0,'stdout':'{}','stderr':''}
 def acceptance(self,*args,**kwargs):return {'validated':True,'quality_score':100,'passed':96,'total':96,'quality':{'gate_passed':True,'measurement_complete':True,'primary_correctness_pct':100,'robustness_pct':100,'regressed_case_ids':[]}}
 def run_work(self,project,base,**kwargs):return work.run(project,base=base,invoke=self.invoke,eligibility=lambda:(['codex','claude'],{}),**kwargs)
 def test_success_publishes_actual_core_validated_snapshot_and_costs(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):result=self.run_work(project,base)
   self.assertTrue(result['validated']);self.assertEqual(result['publication'],'ACCEPTED');self.assertTrue(Path(result['snapshot']).exists());self.assertEqual(json.loads((Path(result['snapshot'])/'metadata.json').read_text())['resources']['tokens'],10)
 def test_standalone_baseline_does_not_use_urace_planning(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'_authority',side_effect=AssertionError('baseline must not use URACE planning')),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):result=self.run_work(project,base,mode='standalone',provider='codex')
   self.assertTrue(result['delivered']);self.assertNotEqual(result['publication'],'ACCEPTED')
 def test_snapshot_uses_measured_baseline_instead_of_assuming_zero(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[];before={'validated':False,'quality_score':25,'passed':24,'total':96}
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=[before,self.acceptance()]):result=self.run_work(project,base)
   metadata=json.loads((Path(result['snapshot'])/'metadata.json').read_text());self.assertEqual(metadata['baseline_evaluation']['quality_score'],25)
 def test_development_repair_can_failover_without_private_feedback(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[];responses=[{'returncode':1,'stderr':'published development check failed'},self.execute()]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=responses),patch.object(work,'evaluate',side_effect=self.acceptance):result=self.run_work(project,base,provider='codex')
   self.assertEqual(self.calls,['codex','claude']);self.assertEqual(result['tokens'],20)
 def test_acceptance_failure_never_repairs_or_publishes(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[];before=(project/'logic.py').read_bytes()
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',return_value={'validated':False,'quality_score':90,'passed':90,'total':96}):result=self.run_work(project,base)
   self.assertEqual(len(self.calls),1);self.assertFalse(result['validated']);self.assertEqual((project/'logic.py').read_bytes(),before);self.assertEqual(result['publication'],'REJECTED')
 def test_controller_interruption_resumes_without_repeating_inference(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    result=self.run_work(project,base,run_id='resume',inject_interruption=True);self.assertFalse(result['complete']);result=self.run_work(project,base,run_id='resume',inject_interruption=True)
   self.assertTrue(result['validated']);self.assertEqual(len(self.calls),1)
 def test_completed_declared_work_is_not_repeated(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    self.run_work(project,base);result=self.run_work(project,base)
   self.assertEqual(result['status'],'NO_DECLARED_WORK');self.assertEqual(len(self.calls),1)
 def test_crash_after_commit_recovers_snapshot_without_repeating_inference(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[];original=work.atomic;failed=[]
   def fault(path,value):
    if Path(path).name=='metadata.json' and not failed:failed.append(True);raise OSError('injected checkpoint crash')
    return original(path,value)
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    with patch.object(work,'atomic',side_effect=fault):
     with self.assertRaises(OSError):self.run_work(project,base,run_id='commit-crash')
    recovered=self.run_work(project,base,run_id='commit-crash')
   self.assertTrue(recovered['delivered']);self.assertEqual(len(self.calls),1);self.assertEqual(len(list((work.state_root(project,base)/'versions').glob('*/metadata.json'))),1)
 def test_owner_edit_is_preserved_on_publication(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   def edit(*args,**kwargs): (project/'logic.py').write_text('owner edit');return self.acceptance()
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=edit):result=self.run_work(project,base)
   self.assertEqual(result['publication'],'OWNER_EDIT_CONFLICT');self.assertEqual((project/'logic.py').read_text(),'owner edit')
 def test_preferred_provider_outage_does_not_block_available_executor(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    blocked=work.run(project,base=base,provider='codex',mode='standalone',eligibility=lambda:(['claude'],{'codex':'injected outage'}),invoke=self.invoke)
    self.assertFalse(blocked['complete']);self.assertFalse(self.calls)
    delivered=work.run(project,base=base,provider='codex',mode='managed',eligibility=lambda:(['claude'],{'codex':'injected outage'}),invoke=self.invoke)
   self.assertTrue(delivered['delivered']);self.assertEqual(self.calls,['claude'])
 def test_no_available_executor_is_preserved_as_pending(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls):result=work.run(project,base=base,eligibility=lambda:([],{'all':'quota'}),invoke=self.invoke)
   self.assertFalse(result['complete']);self.assertEqual(len(self.calls),0)
 def test_documentation_authority_cannot_authorize_code_writes(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);m=work.declaration(project);m['requirements'][0]['scope']='documentation';(project/'project-work.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):work.declaration(project)
 def test_completed_run_cannot_satisfy_revised_requirements(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    self.run_work(project,base,run_id='same');m=work.declaration(project);m['phase']=2;m['requirements'][0]['success_measure']='Independent acceptance passes '+tasks.contract('navigation',2);(project/'project-work.json').write_text(json.dumps(m))
    with self.assertRaises(RuntimeError):self.run_work(project,base,run_id='same')
 def test_changed_accepted_source_reopens_validation(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    self.run_work(project,base);(project/'logic.py').write_text('# owner changed implementation');result=self.run_work(project,base)
   self.assertTrue(result['delivered']);self.assertEqual(len(self.calls),2)
 def test_new_acceptance_revision_creates_new_explicit_work(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    self.run_work(project,base);m=work.declaration(project);m['phase']=2;m['requirements'][0]['success_measure']='Independent acceptance passes '+tasks.contract('navigation',2);(project/'project-work.json').write_text(json.dumps(m));result=self.run_work(project,base)
   self.assertTrue(result['delivered']);self.assertEqual(len(self.calls),2)
 def test_initialization_cannot_overwrite_owner_files(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'existing';p.mkdir();(p/'keep').write_text('owner')
   with self.assertRaises(ValueError):work.initialize(p,'navigation',Path(d))

class SingleSupervisorTests(unittest.TestCase):
 def test_owner_pid_reuse_is_rejected(self):
  import trial_supervisor as s
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'trial-supervisor.json').write_text(json.dumps({'pid':os.getpid(),'start_ticks':'wrong'}));self.assertIsNone(s.active(p))
 def test_valid_single_owner_is_recognized(self):
  import trial_supervisor as s
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19];(p/'trial-supervisor.json').write_text(json.dumps({'pid':os.getpid(),'start_ticks':ticks}));self.assertEqual(s.active(p)['pid'],os.getpid());self.assertIsNone(s.external_owner(p))

 def test_kernel_lock_prevents_a_second_supervisor(self):
  import trial_supervisor as s,fcntl
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   with (p/'supervisor.guard').open('a') as lock,patch.object(s,'BASE',p),patch.object(s.signal,'signal'):
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with self.assertRaises(BlockingIOError):s.main()

class NativeToolConfigurationTests(unittest.TestCase):
 def test_codex_project_tools_keep_the_required_code_mode_host_enabled(self):
  import native_agents as agents
  commands=[]
  def capture(command,*args,**kwargs):commands.append(command);raise RuntimeError('stop before native startup')
  with tempfile.TemporaryDirectory() as d,patch.object(agents,'Transport',side_effect=capture):
   with self.assertRaises(RuntimeError):agents.codex('task',Path(d),{'wall_limit_seconds':300},Path(d)/'context.json')
  command=commands[0];self.assertIn(['--enable','code_mode_host'],[command[i:i+2] for i in range(len(command)-1)]);self.assertNotIn(['--disable','code_mode_host'],[command[i:i+2] for i in range(len(command)-1)]);self.assertIn(['--disable','shell_tool'],[command[i:i+2] for i in range(len(command)-1)])

class ContextPacketTests(unittest.TestCase):
 def test_packet_is_bounded_and_preserves_source_identity(self):
  before={'app.py':'x'*30000,'logic.py':'y'*30000};packet=work.task_packet(before,[{'id':'published','expected':1}]);self.assertLessEqual(len(json.dumps(packet,sort_keys=True).encode()),12000);self.assertTrue(packet['truncated_files']);self.assertEqual(packet['source_sha256']['app.py'],hashlib.sha256(before['app.py'].encode()).hexdigest())

class StudyProgressTests(unittest.TestCase):
 def test_completed_first_pair_advances_to_other_executor(self):
  import spec_trial,trial_supervisor
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);root=base/'cohort';root.mkdir();(base/'trial-clock.json').write_text(json.dumps({'ends_unix':time.time()+3600}))
   for arm in ('standalone','urace'):
    directory=root/'codex-low-requirements_change-0'/arm;directory.mkdir(parents=True);(directory/'study-result.json').write_text('{}')
   controls={'paused':False,'executor_enabled':True,'auto_goals':True};identity={'models':{'codex':'model','claude':'model'}};settings={'enabled':True,'repetitions':1,'efforts':['low']}
   def next_work(project,**kwargs):
    self.assertIn(kwargs['provider'],('codex','claude'));self.assertNotEqual(project.parent.parent.name,'codex-low-requirements_change-0');raise RuntimeError('reached next executor')
   with patch.object(study,'plan',return_value=(root,identity,settings,controls)),patch.object(spec_trial,'eligible',return_value=(['codex','claude'],{})),patch.object(trial_supervisor,'external_owner',return_value=None),patch.object(study,'status',return_value={}),patch.object(work,'run',side_effect=next_work):
    with self.assertRaisesRegex(RuntimeError,'reached next executor'):study.run_one(base)

class ActiveInterruptionBudgetTests(unittest.TestCase):
 setup_project=ProjectWorkTests.setup_project
 invoke=ProjectWorkTests.invoke
 execute=ProjectWorkTests.execute
 acceptance=ProjectWorkTests.acceptance
 run_work=ProjectWorkTests.run_work
 def test_long_suspension_keeps_elapsed_cost_without_consuming_active_allowance(self):
  for mode in ('standalone','managed'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    base,project,controls=self.setup_project(d);self.calls=[]
    with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
     first=self.run_work(project,base,run_id='resume',mode=mode,inject_interruption=True)
     self.assertFalse(first['complete']);self.assertTrue(first['active_budget']['closed'])
     checkpoint=work.state_root(project,base)/'runs/resume/checkpoint.json';saved=json.loads(checkpoint.read_text());saved['queued_unix']-=20000;saved['execution_started_unix']-=20000;checkpoint.write_text(json.dumps(saved))
     second=self.run_work(project,base,run_id='resume',mode=mode,inject_interruption=True)
    self.assertTrue(second['delivered']);self.assertEqual(len(self.calls),1);self.assertGreater(second['elapsed_seconds'],19000);self.assertLess(second['active_elapsed_seconds'],60)
 def test_real_active_exhaustion_is_not_reset_on_resume(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    self.run_work(project,base,run_id='resume',inject_interruption=True)
    checkpoint=work.state_root(project,base)/'runs/resume/checkpoint.json';saved=json.loads(checkpoint.read_text());saved['active_budget']['phase_seconds']=481;checkpoint.write_text(json.dumps(saved));second=self.run_work(project,base,run_id='resume',inject_interruption=True)
   self.assertFalse(second['delivered']);self.assertFalse(second['within_elapsed_budget']);self.assertEqual(len(self.calls),1)
 def test_prior_phase_allowance_cannot_be_renewed(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[]
   with patch.object(work,'effective',return_value=controls):second=self.run_work(project,base,mode='standalone',prior_active_seconds=481)
   self.assertEqual(self.calls,[]);self.assertFalse(second.get('delivered',False))
 def test_hard_crash_interval_is_conservative_and_measurement_marked_incomplete(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);r={'execution_started_unix':time.time()-10000,'active_budget':{'prior_phase_seconds':0,'phase_seconds':12,'closed':False,'last_accounted_unix':time.time()-1000,'measurement_complete':True}}
   with work.ActiveBudget(r,folder,0,time.monotonic()) as budget:self.assertGreater(budget.elapsed(),1000)
   self.assertFalse(r['active_budget']['measurement_complete'])

class ActiveBudgetConservativeTests(unittest.TestCase):
 def test_legacy_attempts_cannot_be_silently_given_a_new_budget(self):
  with tempfile.TemporaryDirectory() as d:
   r={'native_receipts':[{'id':'old'}],'execution_started_unix':time.time()-1000,'queued_unix':time.time()-2000}
   with work.ActiveBudget(r,Path(d),0,time.monotonic()) as b:self.assertGreater(b.elapsed(),990)
   self.assertFalse(r['active_budget']['measurement_complete'])
 def test_prior_phase_and_current_invocation_both_consume_the_same_allowance(self):
  with patch.object(work.time,'monotonic',return_value=100):
   b=work.ActiveBudget({'execution_started_unix':1},Path('.'),450,90);self.assertEqual(b.elapsed(),460)
 def test_publication_overrun_keeps_actual_publication_but_withholds_delivery_credit(self):
  with tempfile.TemporaryDirectory() as d:
   r={'execution_started_unix':1,'complete':True,'publication':'ACCEPTED','within_elapsed_budget':True,'delivered':True,'validated':True,'active_budget':{'prior_phase_seconds':0,'phase_seconds':481,'closed':True}}
   with work.ActiveBudget(r,Path(d),0,time.monotonic()):pass
   self.assertFalse(r['delivered']);self.assertFalse(r['within_elapsed_budget']);self.assertEqual(r['publication'],'ACCEPTED')

class ClarificationContinuityTests(unittest.TestCase):
 setup_project=ProjectWorkTests.setup_project
 invoke=ProjectWorkTests.invoke
 execute=ProjectWorkTests.execute
 acceptance=ProjectWorkTests.acceptance
 def test_owner_question_pauses_without_repeated_inference_and_resumes_after_answer(self):
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=self.setup_project(d);self.calls=[];real=self.invoke
   def request(p,prompt,workspace,checks,allowed,**kwargs):
    value,envelope,receipt=real(p,prompt,workspace,checks,allowed,**kwargs)
    if not kwargs.get('task_manifest',{}).get('clarifications'):receipt.update(failure='Context protocol: AWAITING_OWNER_CLARIFICATION',context_feedback={'status':'AWAITING_OWNER_CLARIFICATION','unresolved_questions':[{'id':'deliver-navigation','question':'Please confirm intended boundary','status':'NEEDS_OWNER_CLARIFICATION'}]})
    return value,envelope,receipt
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=self.execute),patch.object(work,'evaluate',side_effect=self.acceptance):
    first=work.run(project,base=base,run_id='clarification',invoke=request,eligibility=lambda:(['codex','claude'],{}));self.assertEqual(first['status'],'AWAITING_OWNER_CLARIFICATION');self.assertEqual(first['tokens'],10);self.assertEqual(len(self.calls),1)
    second=work.run(project,base=base,run_id='clarification',invoke=request,eligibility=lambda:(['codex','claude'],{}));self.assertEqual(second['status'],'AWAITING_OWNER_CLARIFICATION');self.assertEqual(len(self.calls),1)
    work.clarify(project,'deliver-navigation','Use the existing published contract without changing acceptance',base)
    third=work.run(project,base=base,run_id='clarification',invoke=request,eligibility=lambda:(['codex','claude'],{}));self.assertTrue(third['delivered']);self.assertEqual(len(self.calls),2);self.assertEqual(third['tokens'],20)
