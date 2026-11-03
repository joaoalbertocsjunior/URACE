"""Orchestration/fault-injection tests; these fixtures are not native-use evidence."""
import json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import executable_workflow as w
import workflow_tasks as tasks
from executable_cases import public_cases,corpus
from execution_contract import fingerprint,analysis_fingerprint

SOURCE='\n'.join('def '+name+'(*args):\n    return None' for name in ['quality_delta','evidence_verdict','ready_operations','aggregate_records'])+'\n'
class RepairProtocol(unittest.TestCase):
 def invoke(self,folder,sources,prompts):
  def native(provider,prompt,d,label):
   prompts.append(prompt);source=sources[len(prompts)-1];(Path(d)/(label+'-native.json')).write_text(json.dumps({'id':'receipt-'+str(len(prompts)),'tokens':10,'wall_seconds':1,'requested_model':'m','effort':'medium'}));return {'python_source':source}
  return native
 def execute(self,path,cases):return {'status':'EXECUTED','results':[{'id':c['id'],**({'error':c['error']} if c.get('error') else {'value':c['expected']})} for c in cases]}
 def test_one_compiler_repair_keeps_first_failure_and_both_costs(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(w,'execute',side_effect=self.execute):
   prompts=[];result=w.run('codex','task',Path(directory),corpus(),self.invoke(directory,['not python !',SOURCE],prompts),lambda:None,{'model':'m','native_effort':'medium'})
   self.assertTrue(result['grade']['validated_delivery']);self.assertFalse(result['first_pass']['public_passed']);self.assertEqual(result['repairs'],1);self.assertEqual(result['tokens'],20);self.assertEqual(len(result['native_receipt_ids']),2);self.assertIn('SyntaxError',prompts[1]);self.assertFalse(result['held_out_feedback_disclosed'])
 def test_hidden_failure_never_triggers_repair_or_enters_prompt(self):
  def execute(path,cases):
   out=self.execute(path,cases)
   if any(c['id']=='SECRET-HIDDEN-CASE' for c in cases):out['results'][0]={'id':'SECRET-HIDDEN-CASE','value':'wrong'}
   return out
  private=[{'id':'SECRET-HIDDEN-CASE','workflow':'quality_delta','function':'quality_delta','args':[0,1],'expected':{'delta':1},'error':None}]
  with tempfile.TemporaryDirectory() as directory,patch.object(w,'execute',side_effect=execute):
   prompts=[];result=w.run('codex','task',Path(directory),private,self.invoke(directory,[SOURCE],prompts),lambda:None,{'model':'m','native_effort':'medium'})
   self.assertFalse(result['grade']['validated_delivery']);self.assertEqual(len(prompts),1);self.assertNotIn('SECRET-HIDDEN-CASE',prompts[0])
 def test_repair_admission_failure_preserves_prior_receipt(self):
  calls=[]
  def admit():
   calls.append(1)
   if len(calls)>1:raise RuntimeError('owner paused')
  with tempfile.TemporaryDirectory() as directory:
   prompts=[];result=w.run('codex','task',Path(directory),corpus(),self.invoke(directory,['bad !'],prompts),admit,{'model':'m','native_effort':'medium'})
   self.assertIsNone(result['grade']);self.assertEqual(result['tokens'],10);self.assertEqual(len(prompts),1)
 def test_repair_limit_cannot_be_expanded(self):
  with self.assertRaises(ValueError):w.run('codex','task',Path('/unused'),[],None,None,{},max_repairs=5)

class EvidenceVersioning(unittest.TestCase):
 def copy(self,d):
  root=Path(__file__).parent
  for name in ['executable_sandbox.py','executable_workflow.py','providers.py','stream_usage.py','executable_benchmark.py','executable_scores.py','spec_trial.py']:shutil.copyfile(root/name,Path(d)/name)
 def test_presentation_revision_reuses_execution_contract_but_changes_analysis_hash(self):
  with tempfile.TemporaryDirectory() as directory:
   self.copy(directory);root=Path(directory);before=fingerprint(root);analysis=analysis_fingerprint(root);p=root/'executable_scores.py';p.write_text(p.read_text().replace('def render(result):','def render(result):\n    presentation_only=True'))
   self.assertEqual(fingerprint(root),before);self.assertNotEqual(analysis_fingerprint(root),analysis)
 def test_raw_grading_change_invalidates_execution_contract(self):
  with tempfile.TemporaryDirectory() as directory:
   self.copy(directory);root=Path(directory);before=fingerprint(root);p=root/'executable_scores.py';p.write_text(p.read_text().replace('abs(a-b)<=1e-9','abs(a-b)<=1e-6'));self.assertNotEqual(fingerprint(root),before)

class StudyWorkloads(unittest.TestCase):
 def test_public_examples_have_nontrivial_positive_and_negative_cases(self):
  for family in tasks.FAMILIES:
   public,hidden=tasks.cases(family,True),tasks.cases(family);self.assertEqual(len(public),6 if family=='project_navigation' else 4);self.assertEqual(len(hidden),64);self.assertTrue(set(c['id'] for c in public).isdisjoint(c['id'] for c in hidden));self.assertEqual(tasks.manifest(family),tasks.manifest(family))
 def test_provider_failover_is_independent(self):
  p={'id':'codex','enabled':True,'available':False,'retry_at':999,'estimated_tokens':1,'quality':1,'seconds':1};q={**p,'id':'claude','available':True,'retry_at':0};self.assertEqual(tasks.expected('executor_failover',[[p,q],100,None]),'claude')
 def test_project_completion_requires_current_criteria_and_project(self):
  req=[{'id':'build','project_id':'p','criteria':'new','dependencies':[],'priority':1}];self.assertEqual(tasks.expected('project_navigation',[req,[{'id':'build','project_id':'p','criteria':'old'}],'p']),'build')
 def test_recovery_retains_external_edits(self):
  self.assertEqual(tasks.expected('transaction_recovery',[{'before':{'p':'base'},'after':{'p':'candidate'}},False,{'p':'owner edit'}]),{'action':'CONFLICT','writes':{}})
 def test_study_is_disabled_until_explicitly_enabled_and_settings_are_bounded(self):
  from workflow_study import validate_settings,status
  with tempfile.TemporaryDirectory() as directory:self.assertEqual(status(Path(directory))['status'],'NOT_CONFIGURED')
  for count in [0,101,True]:
   with self.assertRaises(ValueError):validate_settings({'enabled':True,'repetitions':count,'efforts':['medium']})

class MatchedStudyIntegration(unittest.TestCase):
 def environment(self,root):
  import workflow_study as study,hashlib,time
  base=root/'trial';base.mkdir();core=root/'runtime/urace';core.mkdir(parents=True)
  source=Path(study.__file__).parent.parent/'runtime/urace'
  for name in ['auto_goals.py','authority.py','validation.py']:shutil.copyfile(source/name,core/name)
  (base/'qualified.py').write_text('# qualified fixture')
  (base/'harness-manifest.json').write_text(json.dumps({'qualified.py':hashlib.sha256((base/'qualified.py').read_bytes()).hexdigest()}))
  (base/'trial-clock.json').write_text(json.dumps({'trial_id':'fault-injection','ends_unix':time.time()+3600}))
  study.configure(base,enabled=True,repetitions=1,efforts=['medium'])
  controls={'paused':False,'executor_enabled':True,'auto_goals':True,'executors':{p:{'enabled':True,'model':'fixture-'+p} for p in ['codex','claude']}}
  return study,base,controls
 def generated(self,provider,prompt,folder,label,profile_override=None,job_id=None):
  self.assertIn('PUBLIC TRAINING EXAMPLES',prompt);self.assertNotIn('hidden-0',prompt);self.assertTrue((folder/'sealed-cases.json').exists())
  (folder/(label+'-native.json')).write_text(json.dumps({'id':job_id,'tokens':10,'wall_seconds':.01,'requested_model':'fixture-'+provider,'effort':profile_override['native_effort']}))
  return {'python_source':'def next_goal(*args): return None'}
 def execute(self,path,cases):return {'status':'EXECUTED','results':[{'id':c['id'],'value':c['expected']} for c in cases]}
 def test_available_provider_runs_both_arms_with_actual_core_acceptance_and_unique_receipts(self):
  import spec_trial
  with tempfile.TemporaryDirectory() as directory:
   study,base,controls=self.environment(Path(directory))
   with patch.object(study,'effective',return_value=controls),patch.object(spec_trial,'eligible',return_value=(['claude'],{'codex':'capacity'})),patch.object(spec_trial,'native',side_effect=self.generated),patch.object(w,'execute',side_effect=self.execute):
    result=study.run_one(base);self.assertEqual(result['completed_workflows'],2);self.assertEqual(result['unique_native_calls'],2);self.assertEqual(result['known_tokens_including_deferred'],20);self.assertEqual(len(result['matched_pairs']),1);self.assertEqual(result['matched_pairs'][0]['provider'],'claude');self.assertFalse(result['routing_recommendations'])
    root,identity,_=study.plan(base);managed=json.loads(next(root.glob('*/urace/result.json')).read_text());self.assertTrue(managed['core_accepted']);snapshot=Path(managed['artifact_directory'])/'versions/v000001/metadata.json';self.assertTrue(snapshot.exists());self.assertFalse(result['real_user_value_proven'])
    study.configure(base,enabled=False);paused,_,_=study.plan(base);self.assertEqual(paused,root);self.assertEqual(study.run_one(base)['status'],'DISABLED')
 def test_integrity_failure_prevents_native_call(self):
  import spec_trial
  with tempfile.TemporaryDirectory() as directory:
   study,base,controls=self.environment(Path(directory));(base/'qualified.py').write_text('changed')
   with patch.object(study,'effective',return_value=controls),patch.object(spec_trial,'eligible',return_value=(['claude'],{})),patch.object(spec_trial,'native') as native:
    result=study.run_one(base);native.assert_not_called();self.assertEqual(result['completed_workflows'],0)
 def test_retry_preserves_previous_run_artifacts_and_accumulates_deferred_cost(self):
  import spec_trial
  with tempfile.TemporaryDirectory() as directory:
   study,base,controls=self.environment(Path(directory))
   def unavailable(provider,prompt,folder,label,profile_override=None,job_id=None):
    (folder/(label+'-native.json')).write_text(json.dumps({'id':job_id+'-failed','tokens':5,'wall_seconds':.01,'requested_model':'fixture-'+provider,'effort':'medium','failure':{'kind':'capacity'}}));raise RuntimeError('capacity')
   with patch.object(study,'effective',return_value=controls),patch.object(spec_trial,'eligible',return_value=(['claude'],{})),patch.object(spec_trial,'native',side_effect=unavailable):
    result=study.run_one(base);self.assertEqual(result['known_tokens_including_deferred'],5)
   with patch.object(study,'effective',return_value=controls):root,_,_=study.plan(base)
   original=next(root.glob('*/direct/runs/000000-*/implementation-native.json'));before=original.read_bytes()
   with patch.object(study,'effective',return_value=controls),patch.object(spec_trial,'eligible',return_value=(['claude'],{})),patch.object(spec_trial,'native',side_effect=self.generated),patch.object(w,'execute',side_effect=self.execute):
    result=study.run_one(base);self.assertEqual(original.read_bytes(),before);self.assertEqual(result['known_tokens_including_deferred'],25);self.assertEqual(result['unique_native_calls'],3);self.assertEqual(result['completed_workflows'],2)

 def test_crash_receipt_is_attributed_without_inventing_completion_or_timing(self):
  with tempfile.TemporaryDirectory() as directory:
   study,base,controls=self.environment(Path(directory))
   with patch.object(study,'effective',return_value=controls):
    root,_,_=study.plan(base);folder=root/'claude-medium-project_navigation-0/direct/runs/interrupted';folder.mkdir(parents=True);(folder/'implementation-native.json').write_text(json.dumps({'id':'durable-orphan','provider':'claude','effort':'medium','tokens':17,'wall_seconds':3}))
    result=study.status(base);group=result['providers']['claude']['medium'];self.assertEqual(result['completed_workflows'],0);self.assertEqual(result['known_tokens_including_deferred'],17);self.assertEqual(group['known_tokens'],17);self.assertEqual(group['uncheckpointed_receipts'],1);self.assertFalse(group['timing_complete']);self.assertFalse(result['routing_recommendations'])
