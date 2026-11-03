import copy,io,json,tempfile,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urace import milestone_feedback as m,primitives,cli,_common

class MilestoneFeedbackTests(unittest.TestCase):
 def setUp(self):
  self.milestone={'id':'mst-1234567890','name':'Receipt reliability','description':'Complete declared gates','status':'ACTIVE','capability_gates':['cap-receipts'],'quality_gates':[{'scope':'implementation','min_streak':3}]}
  self.config={'capability_envelope':{'milestones':[self.milestone]}}
  self.state={'capability_states':[{'capability_id':'cap-receipts','status':'PARTIAL'}],'quality_state':{'implementation':{'current_streak':0}}}
 def test_existing_status_contract_stays_valid_and_projection_does_not_mutate_it(self):
  before=copy.deepcopy((self.config,self.state));primitives.validate('ProductMilestone',self.milestone);r=m.assess(self.config,self.state,self.milestone);self.assertEqual(r['canonical_status'],'ACTIVE');self.assertEqual(r['phase'],'IMPLEMENTATION');self.assertEqual((self.config,self.state),before);self.assertFalse(r['mutates_achievement_contract'])
 def test_quality_validation_is_a_separate_phase_and_gate_remains_required(self):
  self.state['capability_states'][0]['status']='CAPABLE';r=m.assess(self.config,self.state,self.milestone);self.assertEqual(r['phase'],'VALIDATION');self.assertTrue(any(b['kind']=='quality_gate' for b in r['bottlenecks']));self.assertNotEqual(r['operational_status'],'ACHIEVED')
 def test_ready_gates_do_not_automatically_relabel_the_canonical_milestone(self):
  self.state['capability_states'][0]['status']='CAPABLE';self.state['quality_state']['implementation']['current_streak']=3;r=m.assess(self.config,self.state,self.milestone);self.assertEqual(r['operational_status'],'READY_FOR_GATE_EVALUATION');self.assertEqual(self.milestone['status'],'ACTIVE')
 def test_achieved_does_not_claim_observed_user_benefit_and_regression_is_visible(self):
  self.milestone['status']='ACHIEVED';self.state['capability_states'][0]['status']='CAPABLE';self.state['quality_state']['implementation']['current_streak']=3;r=m.assess(self.config,self.state,self.milestone);self.assertEqual(r['phase'],'COMPLETE');self.assertEqual(r['phases'][-1]['status'],'UNMEASURED');self.state['capability_states'][0]['status']='PARTIAL';r=m.assess(self.config,self.state,self.milestone);self.assertEqual(r['operational_status'],'NEEDS_REASSESSMENT');self.assertEqual(self.milestone['status'],'ACHIEVED')
 def test_pending_superseded_and_explicit_blockers_are_distinct(self):
  self.milestone['status']='PENDING';self.assertEqual(m.assess(self.config,self.state,self.milestone)['phase'],'PLANNING');self.milestone['status']='SUPERSEDED';self.assertEqual(m.assess(self.config,self.state,self.milestone)['operational_status'],'SUPERSEDED');self.milestone['status']='ACTIVE';self.state['blockers']=[{'id':'b','milestone_id':self.milestone['id'],'reason':'Missing owner decision'}];self.assertEqual(m.assess(self.config,self.state,self.milestone)['operational_status'],'BLOCKED')
 def test_unknown_constraints_are_not_zero_or_passed(self):
  self.milestone['complexity_ceiling']=10;r=m.assess(self.config,self.state,self.milestone);self.assertFalse(r['constraints'][0]['measurement_known']);self.assertFalse(r['constraints'][0]['satisfied'])
 def test_projection_never_calls_executor(self):
  with patch('subprocess.Popen',side_effect=AssertionError('no milestone inference')):r=m.assess(self.config,self.state,self.milestone)
  self.assertEqual(r['additional_model_calls'],0)
 def test_existing_cli_exposes_phases_and_statuses(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);config=copy.deepcopy(cli.load_config());config.pop('active_product',None);config.update(self.config,state_path=str(root/'state.json'));cp=root/'config.json';cp.write_text(json.dumps(config));state=cli.initial_state(config);state.update(self.state);(root/'state.json').write_text(json.dumps(state));output=io.StringIO()
   with patch.object(cli,'CONFIG_PATH',cp),patch.object(_common,'CONFIG_PATH',cp),redirect_stdout(output):self.assertEqual(cli.main(['milestone','--json']),0)
   payload=json.loads(output.getvalue());self.assertEqual(payload['phase_feedback']['phase'],'IMPLEMENTATION');self.assertEqual(payload['milestones'][0]['canonical_status'],'ACTIVE');self.assertIn('active_milestone',payload)
class ZeroStreakContractTests(unittest.TestCase):
 setUp=MilestoneFeedbackTests.setUp
 def test_zero_streak_requirement_does_not_invent_an_additional_gate(self):
  self.milestone['quality_gates'][0]['min_streak']=0;self.state['capability_states'][0]['status']='CAPABLE';self.state['quality_state']={};r=m.assess(self.config,self.state,self.milestone);self.assertEqual(r['operational_status'],'READY_FOR_GATE_EVALUATION');self.assertFalse(r['quality_gates'][0]['measurement_known'])
if __name__=='__main__':unittest.main()

class AutomaticSuggestionTests(unittest.TestCase):
 def test_stable_deduplicated_drafts_and_no_mutation_or_inference(self):
  from urace import milestone_suggestions as ms
  cfg={'capability_envelope':{'capabilities':[{'id':'a'},{'id':'a'},{'id':'b'}]}};state={'capability_states':[{'capability_id':'a','status':'PARTIAL'},{'capability_id':'b','status':'CAPABLE'}]};before=copy.deepcopy((cfg,state))
  with patch('subprocess.Popen',side_effect=AssertionError('no inference')):a=ms.suggestions(cfg,state);b=ms.suggestions(cfg,state)
  self.assertEqual(a,b);self.assertEqual(len(a['suggestions']),1);self.assertEqual((cfg,state),before);self.assertEqual(a['additional_model_calls'],0);self.assertFalse(a['suggestions'][0]['automatically_activated'])
 def test_configured_gates_and_objectives_are_not_duplicated(self):
  from urace import milestone_suggestions as ms
  cfg={'capability_envelope':{'capabilities':[{'id':'a'}],'milestones':[{'id':'m','status':'ACHIEVED','capability_gates':['a'],'objective_ref':'g'}]}};state={'objectives':[{'id':'g','title':'Goal','success_measure':'Independent acceptance'}]}
  self.assertEqual(ms.suggestions(cfg,state)['suggestions'],[])
 def test_unknown_is_not_absent_and_objective_criteria_are_literal(self):
  from urace import milestone_suggestions as ms
  cfg={'capability_envelope':{'capabilities':[{'id':'a'}]}};state={'objectives':[{'id':'g','title':'Goal','success_measure':'Exact declared criterion'},{'id':'bad','title':'Missing criterion'}]}
  drafts=ms.suggestions(cfg,state)['suggestions'];self.assertEqual(len(drafts),2);cap=next(d for d in drafts if d['source_refs']==['capability:a']);self.assertEqual(cap['bottleneck']['status'],'UNKNOWN');goal=next(d for d in drafts if d['source_refs']==['objective:g']);self.assertEqual(goal['declared_success'],'Exact declared criterion');self.assertEqual(goal['proposed_capability_gates'],[])
 def test_disable_hides_drafts_without_modifying_configured_milestones(self):
  from urace import milestone_suggestions as ms
  cfg={'auto_milestones':{'enabled':False},'capability_envelope':{'capabilities':[{'id':'a'}],'milestones':[{'id':'m','status':'ACTIVE'}]}};before=copy.deepcopy(cfg);self.assertEqual(ms.suggestions(cfg,{})['suggestions'],[]);self.assertEqual(cfg,before)
 def test_configuration_cli_defaults_toggle_and_inspection_are_persistent(self):
  with tempfile.TemporaryDirectory() as directory:
   cp=Path(directory)/'config.json';cfg=copy.deepcopy(cli.load_config());cfg.pop('auto_milestones',None);cp.write_text(json.dumps(cfg))
   with patch.object(cli,'CONFIG_PATH',cp),patch.object(_common,'CONFIG_PATH',cp):
    for args,expected in [([],True),(['--enabled','false'],False),([],False),(['--enabled','true'],True)]:
     output=io.StringIO()
     with redirect_stdout(output):self.assertEqual(cli.main(['configuration','auto-milestones',*args,'--json']),0)
     self.assertEqual(json.loads(output.getvalue())['enabled'],expected)
 def test_inspection_policy_and_operator_projection_reject_invalid_values(self):
  from urace import command_surface,milestone_suggestions as ms
  self.assertTrue(command_surface.read_only(['configuration','auto-milestones','--json']))
  self.assertFalse(command_surface.read_only(['configuration','auto-milestones','--enabled=false']))
  with self.assertRaises(ValueError):ms.settings({'auto_milestones':{'enabled':'false'}})

class NativeObjectiveStatusTests(unittest.TestCase):
 def test_completed_native_statuses_do_not_produce_new_milestone_drafts(self):
  from urace import milestone_suggestions as ms
  for status in ('completed','COMPLETED','achieved','cancelled','Superseded'):
   r=ms.suggestions({}, {'objectives':[{'id':'owner','title':'Finished work','success_measure':'Recorded completion','status':status}]});self.assertEqual(r['suggestions'],[],status)
 def test_unknown_status_is_not_inferred_complete(self):
  from urace import milestone_suggestions as ms
  r=ms.suggestions({}, {'objectives':[{'id':'owner','title':'Unverified work','success_measure':'Independent completion','status':None}]});self.assertEqual(len(r['suggestions']),1)
