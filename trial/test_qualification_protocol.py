import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import qualification_protocol as q
import coverage_assessment as coverage
import repository_study as study
import project_work as work

class QualificationTests(unittest.TestCase):
 def identity(self):return {'models':{'codex':'m','claude':'c'},'settings':{'efforts':['medium'],'repetitions':8},'qualification_protocol':q.protocol(),'native_clients':{'codex':{'verified':True,'version':'fixture'},'claude':{'verified':True,'version':'fixture'}}}
 def row(self,identity,family='navigation',repeat=0,arm='standalone'):
  return {'id':arm+str(repeat)+family,'arm':arm,'provider':'codex','effort':'medium','family':family,'repeat':repeat,'actual_providers':['codex'],'protocol_sha256':q.digest(identity['qualification_protocol']),'cohort_identity_sha256':q.digest(identity),'execution_conditions':{'requested_model':'m','requested_effort':'medium','active_wall_budget_seconds':480},'complete':True,'validated':False,'tokens':10,'elapsed_seconds':3,'native_receipts':[{'id':q.digest([arm,repeat,family]),'tokens':10,'wall_seconds':1,'provider':'codex','failure':'rejected','requested_model':'m','effort':'medium','client_version':'fixture','skills_and_context_contract_sha256':identity['qualification_protocol'].get('skills_and_context_contract_sha256'),'owner_clarification_sha256':q.digest({})}],'acceptance':{'quality':{'measurement_complete':True,'gate_passed':False}}}
 def write_pair(self,root,identity,family,repeat):
  for arm in ('standalone','urace'):
   p=root/('codex-medium-'+family+'-'+str(repeat))/arm;p.mkdir(parents=True,exist_ok=True);row=self.row(identity,family,repeat,arm);(p/'study-result.json').write_text(json.dumps(row));transport=(root.parent.parent if root.parent.name=='repository-studies' else root)/'transport';transport.mkdir(exist_ok=True)
   for receipt in row['native_receipts']:(transport/(receipt['id']+'.json')).write_text(json.dumps(receipt))
 def test_protocol_freezes_required_families_profiles_tools_quality_and_treatment(self):
  p=q.protocol();self.assertEqual(p['minimum_pairs_per_family'],6);self.assertEqual(set(p['ordinary_families']),set(q.ORDINARY));self.assertNotEqual(p['arms']['standalone'],p['arms']['urace']);self.assertTrue(p['runtime']['sandbox_image'].startswith('sha256:'));self.assertEqual(len(p['quality_contracts']),5)
 def test_underrepresented_family_cannot_hide_behind_30_pairs(self):
  pairs=[]
  for i in range(30):
   a=self.row(self.identity(),q.ORDINARY[i%4],i);a['validated']=True;pairs.append((a,copy.deepcopy(a)))
  r=coverage.paired_metrics(pairs,required_families=q.ORDINARY);self.assertFalse(r['ready']);self.assertEqual(r['family_deficits']['requirements_change'],6)
 def test_bootstrap_is_invariant_under_input_permutation(self):
  pairs=[]
  for i in range(35):
   a=self.row(self.identity(),q.ORDINARY[i%5],i);a['tokens']=100+i;z=copy.deepcopy(a);z['id']='u'+a['id'];z['tokens']=i+1;pairs.append((a,z))
  self.assertEqual(coverage.paired_metrics(pairs,required_families=q.ORDINARY)['metrics'],coverage.paired_metrics(list(reversed(pairs)),required_families=q.ORDINARY)['metrics'])
 def test_scheduler_finishes_pair_before_opening_more_and_executor_independence(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'codex-medium-receipts-5/standalone';p.mkdir(parents=True);(p/'study-result.json').write_text('{}');first=q.cells(root,self.identity(),['codex'])[0];self.assertEqual(first[2:4],('receipts',5));self.assertTrue(all(v[0]=='claude' for v in q.cells(root,self.identity(),['claude']) if v[2]!='failover'))
 def test_scheduler_balances_family_deficits(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);identity=self.identity();self.write_pair(root,identity,'navigation',0);self.assertNotEqual(q.cells(root,identity,['codex'])[0][2],'navigation')
 def test_resource_conflicts_and_unknown_usage_cannot_be_cached_as_complete(self):
  r=self.row(self.identity());r['tokens']=999;self.assertFalse(q.reconcile(r)['cached_tokens_match']);r['native_receipts'].append({**r['native_receipts'][0],'tokens':20});self.assertIsNone(q.reconcile(r)['tokens']);r['native_receipts']=[{'id':'unknown','tokens':None}];self.assertFalse(q.reconcile(r)['all_cost_known'])
 def test_duplicate_receipts_count_once_and_failed_costs_stay(self):
  r=self.row(self.identity());r['native_receipts']*=2;a=q.reconcile(r);self.assertEqual(a['tokens'],10);self.assertEqual(a['failed_attempts'],1)
 def test_identity_drift_and_legacy_evidence_are_not_qualified(self):
  identity=self.identity();r=self.row(identity);self.assertTrue(q.compatible(r,identity));r['execution_conditions']['requested_model']='different';self.assertFalse(q.compatible(r,identity));self.assertFalse(q.compatible({},identity))
 def test_progress_reports_every_requested_profile_and_failed_pair(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);identity=self.identity();self.write_pair(root,identity,'receipts',0);r=q.progress(root,identity);self.assertEqual(r['status'],'INSUFFICIENT');self.assertEqual(r['profiles']['codex:medium']['eligible_pairs'],1);self.assertEqual(r['profiles']['claude:medium']['pair_deficit'],30);self.assertEqual(r['all_completed_resources_by_profile']['codex:medium']['failed_workflows'],2)
 def test_pending_launch_blocks_complete_assessment(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);identity=self.identity();identity['models']={'codex':'m'}
   for f in q.ORDINARY:
    for i in range(6):self.write_pair(root,identity,f,i)
   self.assertEqual(q.progress(root,identity)['status'],'READY');p=root/'codex-medium-navigation-6';p.mkdir();(p/'pair-launch.json').write_text('{}');self.assertEqual(q.progress(root,identity)['status'],'INSUFFICIENT')
 def test_fairness_provider_fixed_even_on_repair(self):
  import test_user_benefit as fixture
  helper=fixture.ProjectWorkTests();helper.calls=[]
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=helper.setup_project(d)
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=[{'returncode':1,'stderr':'public failure'},helper.execute()]),patch.object(work,'evaluate',side_effect=helper.acceptance):
    r=work.run(project,provider='codex',mode='managed',adaptive=False,base=base,invoke=helper.invoke,eligibility=lambda:(['codex'],{}))
   self.assertEqual(helper.calls,['codex','codex']);self.assertEqual(r['tokens'],20)
 def test_private_seal_tampering_stops_resume_before_inference(self):
  import test_user_benefit as fixture
  helper=fixture.ProjectWorkTests();helper.calls=[]
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=helper.setup_project(d)
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=helper.execute),patch.object(work,'evaluate',side_effect=helper.acceptance):
    r=work.run(project,base=base,run_id='seal',inject_interruption=True,invoke=helper.invoke,eligibility=lambda:(['codex'],{}));folder=Path(r['artifact_directory']);(folder/'sealed-acceptance.json').write_text('[]')
    with self.assertRaisesRegex(RuntimeError,'acceptance changed'):work.run(project,base=base,run_id='seal',invoke=helper.invoke)
   self.assertEqual(len(helper.calls),1)
 def test_failed_development_still_measures_private_quality_without_repair_feedback(self):
  import test_user_benefit as fixture
  helper=fixture.ProjectWorkTests();helper.calls=[]
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=helper.setup_project(d)
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',return_value={'returncode':1,'stderr':'public fail'}),patch.object(work,'evaluate',side_effect=helper.acceptance) as evaluate:
    r=work.run(project,base=base,mode='standalone',provider='codex',invoke=helper.invoke,eligibility=lambda:(['codex'],{}))
   self.assertFalse(r['delivered']);self.assertIn('acceptance',r);self.assertEqual(evaluate.call_count,2);self.assertEqual(len(helper.calls),1)
class PreflightTests(unittest.TestCase):
 def test_deferred_admission_never_invokes_or_reserves(self):
  import claude_preflight as p,resource_governor as g,providers
  controls={'paused':False,'executor_enabled':True,'auto_goals':True,'executors':{'claude':{'enabled':True}}}
  with patch('controls.effective',return_value=controls),patch.object(g,'status',return_value={'eligible':False,'reasons':['BACKOFF']}),patch.object(g,'reserve') as reserve,patch.object(providers,'claude') as call:
   result=p.probe()
  self.assertEqual(result['status'],'DEFERRED');self.assertEqual(result['inference_calls'],0);reserve.assert_not_called();call.assert_not_called()
 def test_scheduled_cooldown_survives_controller_restart(self):
  import claude_preflight as p,time
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);(base/'claude-preflight-latest.json').write_text(json.dumps({'status':'FAILED','next_due_unix':time.time()+10000}))
   with patch.object(p.subprocess,'run') as call:result=p.step(base)
   self.assertEqual(result['status'],'FAILED');call.assert_not_called()
 def test_diagnostic_identity_is_separate_from_product_evidence(self):
  import claude_preflight as p
  self.assertEqual(p.PRODUCT['product_id'],'urace-qualification-preflight');self.assertEqual(p.INTERVAL,18900)

class EvidencePacketTests(unittest.TestCase):
 def test_packet_preserves_exact_health_and_source_hashes_and_unknowns(self):
  import assessment_packet as packet,hashlib
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);health={'pid':42,'controller_processes':1,'last_tasks':{'review':{'status':'FINISHED_WITH_EVIDENCE_LIMITATIONS'}}};raw=json.dumps(health).encode();(b/'supervisor-health.json').write_bytes(raw)
   with patch.object(work,'engine_hash',return_value='e'):result=packet.packet(b)
   self.assertEqual(result['health'],health);self.assertEqual(result['evidence_index']['supervisor-health.json']['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(result['evidence_index']['verification-latest.json']['status'],'MISSING');self.assertFalse(result['assessment_complete'])
 def test_packet_progress_equals_full_progress_no_sampling_or_truncation(self):
  import assessment_packet as packet
  helper=QualificationTests();identity=helper.identity();identity.update(trial_id='t',engine_sha256='e')
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);root=b/'repository-studies/abc';root.mkdir(parents=True);helper.write_pair(root,identity,'navigation',0);(b/'trial-clock.json').write_text('{"trial_id":"t"}');(b/'repository-study-latest.json').write_text(json.dumps({'cohort':'abc','plan':identity}));expected=q.progress(root,identity)
   with patch.object(work,'engine_hash',return_value='e'):result=packet.packet(b)
   for key,value in expected.items():self.assertEqual(result['qualification'][key],value)
 def test_packet_rejects_evidence_symlinks(self):
  import assessment_packet as packet
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);(b/'supervisor-health.json').symlink_to('/outside')
   with self.assertRaises(ValueError):packet.packet(b)

class LosslessPromptTests(unittest.TestCase):
 def test_compact_encoding_preserves_every_field_and_exact_source(self):
  values=[{'source':'def f():\n    return "é \\t"\n','receipt':{'input':0,'unknown':None,'failed':False},'examples':[1,2,3]},work.task_packet({'app.py':'import logic\n','logic.py':'def compute(x): return x\n'},[{'id':'case','request':[1,2],'expected':3}])]
  for value in values:
   self.assertEqual(json.loads(work.prompt_json(value)),value);self.assertLessEqual(len(work.prompt_json(value).encode()),len(json.dumps(value,sort_keys=True).encode()))
 def test_quality_context_selection_still_defaults_full_without_exact_qualified_evidence(self):
  from study_analysis import context_choice
  with tempfile.TemporaryDirectory() as d:self.assertEqual(context_choice(Path(d),'codex','navigation','engine','contract'),'full')

class ExecutorContextQualificationTests(unittest.TestCase):
 def test_effort_mismatch_cannot_activate_compact_context(self):
  import study_analysis as a,time
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);(base/'context-routing.json').write_text(json.dumps({'engine_sha256':'e','expires_unix':time.time()+1000,'recommendations':{'codex:navigation':{'model':'m','native_effort':'low','native_client_version':'fixture','pairs':35,'quality_nonregressing':True,'qualified':True,'contract':'c','time_ratio':.9,'token_ratio':.7}}}))
   with patch('controls.effective',return_value={'executors':{'codex':{'model':'m','native_effort':'medium'}}}),patch('qualification_protocol.native_clients',return_value={'codex':{'verified':True,'version':'fixture'}}):
    self.assertEqual(a.context_choice(base,'codex','navigation','e','c'),'full');self.assertEqual(a.context_choice(base,'codex','navigation','e','c',effort='low'),'compact')

class PhaseResourceTests(unittest.TestCase):
 def test_phase_aggregation_keeps_attempts_when_stage_timing_is_unknown(self):
  import repository_study as study,spec_trial,trial_supervisor,time
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);root=base/'cohort';root.mkdir();(base/'trial-clock.json').write_text(json.dumps({'ends_unix':time.time()+1000}));settings={'enabled':True,'repetitions':1,'efforts':['medium']};identity={'models':{'codex':'m'},'settings':settings,'qualification_protocol':q.protocol(),'scope':'fixture'};controls={'paused':False,'executor_enabled':True,'auto_goals':True}
   def run(project,**kwargs):
    phase=work.declaration(project)['phase'];folder=work.state_root(project,base)/'runs'/('phase-'+str(phase));workspace=folder/'workspace';workspace.mkdir(parents=True);(workspace/'app.py').write_text('app');(workspace/'logic.py').write_text('logic');r={'id':str(phase),'phase':phase,'complete':True,'validated':True,'delivered':True,'queued_unix':time.time()-10,'elapsed_seconds':10,'native_receipts':[{'id':project.parent.name+str(phase),'tokens':10,'provider':'codex','wall_seconds':1}],'attempts':[{'phase':phase}],'timing':{'baseline_seconds':0,'acceptance_seconds':0,'publication_seconds':None},'finished_at':'2026-10-26T00:00:00+00:00','phase_started_unix':1};(folder/'result.json').write_text(json.dumps(r));return r
   with patch.object(trial_supervisor,'external_owner',return_value=None),patch.object(study,'plan',return_value=(root,identity,settings,controls)),patch.object(study,'FAMILIES',('requirements_change',)),patch.object(spec_trial,'eligible',return_value=(['codex'],{})),patch.object(work,'run',side_effect=run),patch.object(study,'status',return_value={}):study.run_one(base)
   r=json.loads((root/'codex-medium-requirements_change-0/standalone/study-result.json').read_text());self.assertEqual(len(r['attempts']),2);self.assertEqual(len(r['phases']),2);self.assertEqual(r['tokens'],20);self.assertIsNone(r['timing']['publication_seconds'])

class AuthoritativeReceiptTests(unittest.TestCase):
 def test_edited_embedded_receipt_cannot_validate_against_native_transport(self):
  helper=QualificationTests();row=helper.row(helper.identity())
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);transport=base/'transport';transport.mkdir();receipt=row['native_receipts'][0];(transport/(receipt['id']+'.json')).write_text(json.dumps(receipt));self.assertTrue(q.reconcile(row,base)['all_cost_known']);row['native_receipts'][0]['tokens']=999;row['tokens']=999;self.assertFalse(q.reconcile(row,base)['authoritative_receipts_match']);self.assertFalse(q.reconcile(row,base)['all_cost_known'])

class PreflightReuseTests(unittest.TestCase):
 def test_recent_exact_profile_success_avoids_redundant_inference_but_new_failure_blocks_reuse(self):
  import claude_preflight as p
  from datetime import datetime,timezone
  success={'id':'valid','provider':'claude','requested_model':'m','effort':'medium','at':datetime.fromtimestamp(100,timezone.utc).isoformat(),'failure':None,'inference_requested':True,'returncode':0,'is_error':False,'subtype':'success'}
  self.assertEqual(p.reusable_receipt([success],'m','medium',101)['id'],'valid');self.assertIsNone(p.reusable_receipt([success],'m','high',101));self.assertIsNone(p.reusable_receipt([success],'m','medium',100+p.INTERVAL+1));failure={**success,'id':'failed','at':datetime.fromtimestamp(101,timezone.utc).isoformat(),'failure':'timeout'};self.assertIsNone(p.reusable_receipt([success,failure],'m','medium',102))

class MeasurementIdentityTests(unittest.TestCase):
 def test_statistical_measurement_changes_are_versioned_separately(self):
  import execution_contract as e
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in ('accounting.py','study_analysis.py','output_quality.py','coverage_assessment.py','qualification_protocol.py'):(root/name).write_text('# frozen')
   before=e.measurement_fingerprint(root);(root/'coverage_assessment.py').write_text('# changed bootstrap');self.assertNotEqual(before,e.measurement_fingerprint(root))

class OrdinaryAdmissionTests(unittest.TestCase):
 def test_shared_guard_eligibility_does_not_bypass_ordinary_provider_backoff(self):
  import claude_preflight as p,resource_governor as g,providers,spec_trial
  controls={'paused':False,'executor_enabled':True,'auto_goals':True,'executors':{'claude':{'enabled':True}}}
  with patch('controls.effective',return_value=controls),patch.object(g,'status',return_value={'eligible':True}),patch.object(spec_trial,'eligible',return_value=(['codex'],{'claude':'reported_provider_capacity_backoff'})),patch.object(g,'reserve') as reserve,patch.object(providers,'claude') as call:
   result=p.probe()
  self.assertEqual(result['status'],'DEFERRED');self.assertEqual(result['inference_calls'],0);reserve.assert_not_called();call.assert_not_called()

class ClientUpgradeTests(unittest.TestCase):
 def test_client_upgrade_invalidates_compact_context_recommendation(self):
  import study_analysis as a,time
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);(base/'context-routing.json').write_text(json.dumps({'engine_sha256':'e','expires_unix':time.time()+1000,'recommendations':{'codex:navigation':{'model':'m','native_effort':'medium','native_client_version':'old','pairs':35,'quality_nonregressing':True,'qualified':True,'contract':'c','time_ratio':.9,'token_ratio':.7}}}))
   with patch('controls.effective',return_value={'executors':{'codex':{'model':'m','native_effort':'medium'}}}),patch('qualification_protocol.native_clients',return_value={'codex':{'verified':True,'version':'new'}}):self.assertEqual(a.context_choice(base,'codex','navigation','e','c'),'full')

class LongitudinalScopeTests(unittest.TestCase):
 def test_operational_windows_separate_profiles_and_do_not_claim_qualified_gain(self):
  from period_feedback import compare
  from datetime import datetime,timezone
  def row(provider,model,tokens):return {'kind':'finished','at':datetime.fromtimestamp(10000,timezone.utc).isoformat(),'provider':provider,'requested_model':model,'effort':'medium','client_version':'fixture','tokens':tokens,'wall_seconds':1,'failure':None}
  result=compare([{**row('codex','m',10),'product_id':'p'},{**row('codex','m',20),'product_id':'other'},row('claude','c',None)],[],11000)
  self.assertFalse(result['qualified_gain_claim']);self.assertEqual(len(result['by_requested_profile']),3);self.assertEqual(result['schema'],'operational-period-feedback-v2');unknown=next(p for p in result['by_requested_profile'].values() if p['requested_identity']['provider']=='claude');self.assertIsNone(unknown['current']['total_tokens']);self.assertEqual(unknown['current']['unknown_usage_attempts'],1)

if __name__=='__main__':unittest.main()

class ActiveTimingCompatibilityTests(unittest.TestCase):
 def test_unclosed_or_uncertain_active_measurement_cannot_qualify(self):
  helper=QualificationTests();identity=helper.identity();r=helper.row(identity);self.assertTrue(q.compatible(r,identity))
  r['active_budget']={'closed':False,'measurement_complete':True};self.assertFalse(q.compatible(r,identity))
  r['active_budget']={'closed':True,'measurement_complete':False};self.assertFalse(q.compatible(r,identity))
  r['active_budget']={'closed':True,'measurement_complete':True};self.assertTrue(q.compatible(r,identity))
