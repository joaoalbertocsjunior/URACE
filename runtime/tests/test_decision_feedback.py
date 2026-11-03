import copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from urace import decision_feedback as d,cli,_common,command_surface

class DecisionFeedbackTests(unittest.TestCase):
 def setUp(self):
  self.config={'resource_product_id':'p','authority':{'delegated':['local implementation changes'],'reserved':['spend money']}}
  self.record={'id':'dec-one','objective_ref':'goal-one','outcome':'AUTONOMOUSLY_AUTHORIZED','provenance_status':'CURRENT'}
  self.state={'objectives':[{'id':'goal-one','title':'Repair receipt accounting','scope':'implementation','status':'planned'}],'decision_records':[self.record],'integrity_gaps':[{'id':'gap-one','description':'Duplicate receipt costs are counted twice','resolved':False}],'operations':[]}
  self.forecast={'benefits':[{'metric':'accuracy','unit':'proportion','baseline':.7,'expected':.9,'direction':'higher','target_gain':.2}],'weights':{'accuracy':1},'evidence_refs':['gap-one'],'bottleneck_id':'gap-one','recommended_action':'Deduplicate receipt IDs','cost':{'tokens':None},'risk':'Receipt conflicts must remain visible','uncertainty':'Engineering estimate; uncalibrated'}
 def configured(self,mode='executor'):return {**self.config,'decision_feedback':{'mode':mode}}
 def response(self,payload):
  return {'status':'ADVISORY_COMPLETE','advice':{'expected_benefit_score':70,'explanation':'May prevent duplicate costs','recommended_action':'Audit duplicate IDs','uncertainty':'No measured effect yet'},'receipt':{'id':'native-one','kind':'finished','inference_requested':True,'failure':None,'provider':'claude','requested_model':'m','effort':'medium','product_id':payload['packet']['product_id'],'decision_id':payload['packet']['decision_id'],'role':'DECISION_EVALUATION_ONLY'},'inference_calls':1}
 def test_default_enabled_auto_never_calls_model(self):
  self.assertEqual(d.settings({}),d.DEFAULTS)
  with patch('subprocess.run',side_effect=AssertionError('no subprocess in auto')):
   result=d.assess(self.config,self.state,self.record)
  self.assertTrue(result['enabled']);self.assertEqual(result['mode'],'auto');self.assertEqual(result['additional_model_calls'],0);self.assertIsNone(result['expected_benefit_score']['value'])
 def test_forecast_links_bottleneck_action_status_and_provisional_score(self):
  d.register_forecast(self.state,self.record,self.forecast);r=d.view(self.config,self.state,self.record)
  self.assertEqual(r['detected_bottlenecks'][0]['id'],'gap-one');self.assertEqual(r['action_recommendation'],'Deduplicate receipt IDs');self.assertEqual(r['status'],'APPROVED');self.assertAlmostEqual(r['expected_benefit_score']['value'],100);self.assertFalse(r['expected_benefit_score']['calibrated']);self.assertIsNone(r['expected_cost']['tokens'])
 def test_score_cannot_approve_reserved_action_or_weaken_acceptance(self):
  self.state['objectives'][0]['title']='spend money';d.register_forecast(self.state,self.record,self.forecast);before=copy.deepcopy(self.state);r=d.view(self.config,self.state,self.record)
  self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['affects_authority_or_acceptance']);self.assertEqual(self.state,before)
 def test_heuristic_defaults_are_not_invented_benefit_predictions(self):
  self.state['objectives'][0].update(expected_value=.5,estimated_cost=.3,risk=.2,source='auto_goals');self.assertIsNone(d.view(self.config,self.state,self.record)['expected_benefit_score']['value'])
 def test_missing_evidence_or_owner_weights_withholds_aggregate_score(self):
  f=copy.deepcopy(self.forecast);f['evidence_refs']=[];self.assertIsNone(d.score(f)['value']);f=copy.deepcopy(self.forecast);f['weights']={};self.assertIsNone(d.score(f)['value'])
 def test_forecast_validation_rejects_nan_boolean_and_invalid_weight(self):
  for value in (float('nan'),True,-1):
   f=copy.deepcopy(self.forecast);f['weights']['accuracy']=value
   with self.assertRaises(ValueError):d.validate_forecast(f)
 def test_refresh_is_cached_and_preserves_decision_records(self):
  d.register_forecast(self.state,self.record,self.forecast);before=copy.deepcopy(self.state['decision_records']);self.assertEqual(d.refresh(self.config,self.state)['changed'],1);self.assertEqual(d.refresh(self.config,self.state)['changed'],0);self.assertEqual(len(self.state['decision_assessment_history']),1);self.assertEqual(self.state['decision_records'],before)
 def test_forecast_revisions_keep_immutable_originals(self):
  first=d.register_forecast(self.state,self.record,self.forecast);f=copy.deepcopy(self.forecast);f['benefits'][0]['expected']=.8;second=d.register_forecast(self.state,self.record,f);self.assertNotEqual(first['id'],second['id']);self.assertEqual(self.state['decision_forecast_history'][0]['forecast']['benefits'][0]['expected'],.9)
 def test_observed_outcomes_do_not_turn_acceptance_into_benefit(self):
  d.register_forecast(self.state,self.record,self.forecast);self.state['operations']=[{'id':'op-one','objective_reference':'goal-one','status':'ACCEPTED','before_metrics':{'accuracy':.7},'after_metrics':{'accuracy':.85},'outcome':{'status':'AWAITING_OUTCOME'}}];self.state['objectives'][0]['status']='completed';r=d.view(self.config,self.state,self.record);self.assertEqual(r['status'],'COMPLETED');self.assertFalse(r['observed_feedback']['benefit_verified']);self.assertAlmostEqual(r['observed_feedback']['metrics'][0]['forecast_error'],-.05)
 def test_late_forecast_is_retrospective(self):
  self.state['operations']=[{'id':'op-one','objective_reference':'goal-one','status':'ACCEPTED'}];self.assertEqual(d.register_forecast(self.state,self.record,self.forecast)['timing'],'RETROSPECTIVE')
 def test_executor_mode_requires_opt_in_and_caches_exact_input(self):
  invoke=__import__('unittest.mock',fromlist=['Mock']).Mock(side_effect=self.response)
  r=d.assess(self.config,self.state,self.record,invoke=invoke);invoke.assert_not_called()
  config=self.configured();first=d.assess(config,self.state,self.record,invoke=invoke);self.assertEqual(first['executor_assessment']['status'],'ADVISORY_COMPLETE');second=d.assess(config,self.state,self.record,invoke=invoke);self.assertTrue(second['cache_hit']);self.assertEqual(invoke.call_count,1);self.assertEqual(second['additional_model_calls'],0)
 def test_executor_score_does_not_override_blocked_authority(self):
  self.state['objectives'][0]['title']='spend money';r=d.assess(self.configured(),self.state,self.record,invoke=self.response);self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['executor_assessment']['advice']['expected_benefit_score'],70)
 def test_changed_material_input_invalidates_cache(self):
  invoke=__import__('unittest.mock',fromlist=['Mock']).Mock(side_effect=self.response);config=self.configured();d.assess(config,self.state,self.record,invoke=invoke);self.state['objectives'][0]['title']='Repair conflicting receipts';d.assess(config,self.state,self.record,invoke=invoke);self.assertEqual(invoke.call_count,2)
 def test_failed_advice_is_not_success_and_is_cached_without_retry(self):
  invoke=__import__('unittest.mock',fromlist=['Mock']).Mock(return_value={'status':'FAILED','advice':{'expected_benefit_score':100},'inference_calls':1});r=d.assess(self.configured(),self.state,self.record,invoke=invoke);self.assertIsNone(r['executor_assessment']['advice']);d.assess(self.configured(),self.state,self.record,invoke=invoke);self.assertEqual(invoke.call_count,1)
 def test_missing_receipt_or_status_in_advice_invalidates_completion(self):
  bad={'status':'ADVISORY_COMPLETE','advice':{'expected_benefit_score':100,'explanation':'x','recommended_action':'x','uncertainty':'x'},'inference_calls':1};self.assertEqual(d.assess(self.configured(),self.state,self.record,invoke=lambda p:bad)['executor_assessment']['status'],'FAILED')
 def test_packet_overflow_defers_without_truncation_or_inference(self):
  self.state['objectives'][0]['title']='x'*20000
  with patch('subprocess.run',side_effect=AssertionError('no inference')):r=d.assess(self.configured(),self.state,self.record)
  self.assertEqual(r['executor_assessment']['status'],'DEFERRED');self.assertEqual(r['executor_assessment']['inference_calls'],0)
 def test_list_summary_has_links_and_required_fields_without_full_evidence(self):
  d.register_forecast(self.state,self.record,self.forecast);full=d.view(self.config,self.state,self.record);brief=d.compact(full);self.assertEqual(brief['bottleneck_ids'],['gap-one']);self.assertIn('detail_command',brief);self.assertLess(len(json.dumps(brief)),len(json.dumps(full)))
 def test_cli_parser_and_api_classify_new_configuration_and_assessment(self):
  parser=cli.build_parser();a=parser.parse_args(['configuration','decision-feedback','--mode','executor']);self.assertEqual(a.mode,'executor');self.assertTrue(command_surface.read_only(['configuration','decision-feedback']));self.assertFalse(command_surface.read_only(['configuration','decision-feedback','--mode','executor']));self.assertFalse(command_surface.read_only(['decision','assess','dec-one']))
 def test_cli_configuration_changes_preserve_authority_and_do_not_infer(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'config.json';config=copy.deepcopy(cli.load_config());p.write_text(json.dumps(config));before=copy.deepcopy(config['authority'])
   with patch.object(cli,'CONFIG_PATH',p),patch.object(_common,'CONFIG_PATH',p),redirect_stdout(io.StringIO()),patch('subprocess.run',side_effect=AssertionError('no inference')):self.assertEqual(cli.main(['configuration','decision-feedback','--mode','executor','--json']),0)
   saved=json.loads(p.read_text());self.assertEqual(saved['authority'],before);self.assertEqual(saved['decision_feedback']['mode'],'executor')

class ExistingPredictionTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_auto_reuses_only_explicit_matching_proposal_evidence_without_inference(self):
  goal=self.state['objectives'][0];goal.update(reason='Duplicate costs distort feedback',success_measure='Unique receipts counted once',metadata={'forecast_evidence_ref':'evidence-one'})
  self.state['evidence']=[{'id':'evidence-one','kind':'executor-proposal','proposal':{**{k:goal[k] for k in ('title','reason','success_measure')},'expected_value':.8,'estimated_cost':.2,'risk':.1}}]
  with patch('subprocess.run',side_effect=AssertionError('no additional call')):r=d.assess(self.config,self.state,self.record)
  self.assertEqual(r['expected_benefit_score']['value'],80);self.assertFalse(r['expected_benefit_score']['calibrated']);self.assertEqual(r['existing_executor_prior']['source_ref'],'evidence-one');goal['title']='Different task';self.assertIsNone(d.view(self.config,self.state,self.record)['expected_benefit_score']['value'])

class FeedbackCachingIntegrityTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_legacy_repeated_authority_ids_do_not_churn_cache_or_history(self):
  self.state['decision_records']=[{**self.record,'outcome':'DENIED'},self.record];self.assertEqual(d.refresh(self.config,self.state)['changed'],1);self.assertEqual(d.refresh(self.config,self.state)['changed'],0);self.assertEqual(len(self.state['decision_assessment_history']),1);self.assertEqual(len(self.state['decision_records']),2)
 def test_conflicting_source_evidence_ids_withhold_existing_prior(self):
  goal=self.state['objectives'][0];goal.update(reason='r',success_measure='s',metadata={'forecast_evidence_ref':'e'});proposal={**{k:goal[k] for k in ('title','reason','success_measure')},'expected_value':.8};self.state['evidence']=[{'id':'e','kind':'executor-proposal','proposal':proposal},{'id':'e','kind':'executor-proposal','proposal':{**proposal,'expected_value':1}}];self.assertIsNone(d.view(self.config,self.state,self.record)['expected_benefit_score']['value'])

class DecisionFeedbackCLITests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_auto_assess_persists_forecast_and_exposes_it_through_inspection_without_inference(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);config=copy.deepcopy(cli.load_config());config.update(self.config,state_path=str(root/'state.json'));config.pop('active_product',None);cp=root/'config.json';cp.write_text(json.dumps(config));state={**self.state,'state_version':0};(root/'state.json').write_text(json.dumps(state));output=io.StringIO()
   with patch.object(cli,'CONFIG_PATH',cp),patch.object(_common,'CONFIG_PATH',cp),redirect_stdout(output),patch('subprocess.Popen',side_effect=AssertionError('auto must not start worker')):self.assertEqual(cli.main(['decision','assess','dec-one','--forecast',json.dumps(self.forecast),'--json']),0)
   result=json.loads(output.getvalue());self.assertEqual(result['status'],'APPROVED');self.assertAlmostEqual(result['expected_benefit_score']['value'],100);saved=json.loads((root/'state.json').read_text());self.assertEqual(len(saved['decision_forecast_history']),1);self.assertEqual(saved['decision_records'],state['decision_records'])
 def test_auto_refresh_cannot_launch_executor_even_when_executor_mode_is_configured(self):
  with patch('subprocess.Popen',side_effect=AssertionError('refresh must not infer')):r=d.refresh({**self.config,'decision_feedback':{'mode':'executor'}},self.state)
  self.assertEqual(r['additional_model_calls'],0)

class AssessmentCancellationTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_timed_out_advisory_worker_is_terminated_and_never_counted_as_success(self):
  import subprocess,signal
  class Process:
   pid=12345
   def __init__(self):self.calls=0
   def poll(self):return None
   def communicate(self,*args,**kwargs):
    self.calls+=1
    if self.calls==1:raise subprocess.TimeoutExpired('worker',160)
    return ('','')
  process=Process()
  with patch('subprocess.Popen',return_value=process),patch('os.killpg') as terminate:r=d.assess({**self.config,'decision_feedback':{'mode':'executor'}},self.state,self.record)
  terminate.assert_called_once_with(12345,signal.SIGTERM);self.assertEqual(r['executor_assessment']['status'],'FAILED');self.assertIsNone(r['additional_model_calls'])

class ExecutorSelectionCacheTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 response=DecisionFeedbackTests.response
 def test_explicit_executor_change_invalidates_advisory_cache(self):
  from unittest.mock import Mock
  invoke=Mock(side_effect=self.response)
  for executor in ('claude','codex'):d.assess({**self.config,'decision_feedback':{'mode':'executor','executor':executor}},self.state,self.record,invoke=invoke)
  self.assertEqual(invoke.call_count,2)
 def test_deferred_metadata_can_be_rechecked_without_reusing_a_stale_unavailability_claim(self):
  from unittest.mock import Mock
  invoke=Mock(side_effect=[{'status':'DEFERRED','inference_calls':0},self.response({'packet':{'product_id':'p','decision_id':'dec-one'}})])
  config={**self.config,'decision_feedback':{'mode':'executor'}};d.assess(config,self.state,self.record,invoke=invoke);r=d.assess(config,self.state,self.record,invoke=invoke);self.assertEqual(r['executor_assessment']['status'],'ADVISORY_COMPLETE')

class UnknownForecastTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_unknown_baseline_or_expected_value_remains_unknown_and_does_not_block_recording(self):
  for key in ('baseline','expected','target_gain'):
   forecast=copy.deepcopy(self.forecast);forecast['benefits'][0][key]=None;d.register_forecast(self.state,self.record,forecast);r=d.view(self.config,self.state,self.record);self.assertIsNone(r['expected_benefit_score']['value']);self.assertIsNone(r['expected_benefits'][0][key])

class DetectedBottleneckLinkTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_deterministic_detection_and_planning_link_the_actual_observation_without_scoring_a_default_prior(self):
  observation={'id':'obs-one','results':{'correctness':{'vs_previous':'regressed','value':.7}}};self.state['progress_observations']=[observation];goal=cli.discover(self.config,self.state,observation);cli.plan_for(self.state,goal);record=self.state['decision_records'][-1];r=d.view(self.config,self.state,record)
  self.assertEqual(record['objective_ref'],goal['id']);self.assertEqual(r['detected_bottlenecks'][0]['id'],'obs-one');self.assertEqual(r['action_recommendation'],goal['title']);self.assertIsNone(r['expected_benefit_score']['value'])

class PollingCostTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_recomputation_timestamp_alone_does_not_churn_feedback_or_trigger_rescoring(self):
  self.state['operations']=[{'id':'op-one','objective_reference':'goal-one','status':'ACCEPTED','outcome':{'status':'AWAITING_OUTCOME','evaluated_at':'2026-10-26T01:00:00+00:00'}}];d.refresh(self.config,self.state);self.state['operations'][0]['outcome']['evaluated_at']='2026-10-26T02:00:00+00:00';self.assertEqual(d.refresh(self.config,self.state)['changed'],0);self.assertEqual(len(self.state['decision_assessment_history']),1)

class ForecastContractBindingTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_requirement_change_withholds_old_score_and_keeps_history(self):
  first=d.register_forecast(self.state,self.record,self.forecast);self.state['objectives'][0]['success_measure']='New owner requirement';r=d.view(self.config,self.state,self.record);self.assertEqual(r['forecast_status'],'STALE_CONTEXT');self.assertIsNone(r['expected_benefit_score']['value']);self.assertEqual(r['status'],'STALE');self.assertEqual(r['authority_status'],'APPROVED');self.assertEqual(self.state['decision_forecast_history'][0]['id'],first['id'])
 def test_owner_reconfirmation_creates_a_new_context_bound_forecast(self):
  first=d.register_forecast(self.state,self.record,self.forecast);self.state['objectives'][0]['success_measure']='New criteria';second=d.register_forecast(self.state,self.record,self.forecast);self.assertNotEqual(first['id'],second['id']);self.assertEqual(d.view(self.config,self.state,self.record)['forecast_status'],'CURRENT');self.assertEqual(len(self.state['decision_forecast_history']),2)
 def test_observed_outcome_does_not_invalidate_the_original_prediction(self):
  d.register_forecast(self.state,self.record,self.forecast);self.state['operations']=[{'id':'op-one','objective_reference':'goal-one','status':'ACCEPTED','after_metrics':{'accuracy':.85}}];self.assertEqual(d.view(self.config,self.state,self.record)['forecast_status'],'CURRENT')

class DecisionObservationRetentionTests(unittest.TestCase):
 setUp=DecisionFeedbackTests.setUp
 def test_new_decision_retains_its_actual_bottleneck_observation_even_when_poll_cache_did_not(self):
  observation={'id':'new-observation','results':{'correctness':{'vs_previous':'regressed','value':.7}}};goal=cli.discover(self.config,self.state,observation);self.assertEqual(self.state['progress_observations'][0],observation);cli.plan_for(self.state,goal);r=d.view(self.config,self.state,self.state['decision_records'][-1]);self.assertEqual(r['detected_bottlenecks'][0]['id'],'new-observation')

if __name__=='__main__':unittest.main()
