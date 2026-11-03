import copy,unittest
from unittest.mock import patch
from urace import implementation_sequence as seq,inspection,cli

class SequenceTests(unittest.TestCase):
 def test_dependencies_precede_high_priority_dependents(self):
  tasks=[{'id':'deliver','priority':100,'dependencies':['check']},{'id':'check','priority':20,'uncertainty_reduction':True}];p=seq.plan(tasks);self.assertEqual([r['id'] for r in p['tasks']],['check','deliver']);self.assertFalse(p['absolute_optimum_proven']);self.assertEqual(p['native_model_calls'],0)
 def test_missing_dependency_and_cycles_are_blocked_no_native_work(self):
  p=seq.plan([{'id':'a','dependencies':['b']},{'id':'b','dependencies':['a']},{'id':'c','dependencies':['missing']}]);self.assertEqual(p['dispatch_order'],[]);self.assertTrue(all(r['status']=='BLOCKED' for r in p['tasks']))
 def test_completed_dependencies_and_independent_phases(self):
  p=seq.plan([{'id':'done','status':'completed'},{'id':'a','dependencies':['done']},{'id':'b'}],eligible={'a':True,'b':True});self.assertEqual(set(p['dependency_phases'][0]),{'a','b'});self.assertEqual(set(p['dispatch_order']),{'a','b'})
 def test_known_local_tasks_never_need_executor_tokens(self):
  p=seq.plan([{'id':'rank','controller_action':'rank_peers','priority':50},{'id':'build','priority':50}]);self.assertEqual(p['tasks'][0]['route'],'LOCAL_CONTROLLER');self.assertEqual(p['tasks'][0]['id'],'rank')
 def test_owner_priority_wins_before_resource_tie_break(self):
  p=seq.plan([{'id':'native','priority':90},{'id':'local','priority':10,'controller_action':'status'}]);self.assertEqual(p['tasks'][0]['id'],'native')
 def test_local_execution_has_no_product_gain_claim_or_native_call(self):
  goal={'id':'status','status':'planned','scope':'implementation','controller_action':'status'};state={'objectives':[goal]}
  with patch.object(cli.intelligent_executor,'execute',side_effect=AssertionError('No native maintenance')):
   result=cli.execute_with_executor({},state,goal,{})
  self.assertEqual(result['native_calls'],0);self.assertFalse(result['product_improvement_claim']);self.assertEqual(goal['status'],'completed')
 def test_unknown_local_handler_blocks_instead_of_native_fallback(self):
  goal={'id':'x','status':'planned','scope':'implementation','execution_kind':'local_orchestration','controller_action':'unknown'}
  with self.assertRaises(RuntimeError):cli.execute_with_executor({}, {'objectives':[goal]},goal,{})
 def test_planning_recomputes_when_requirements_change(self):
  tasks=[{'id':'a'}];first=seq.plan(tasks);tasks.append({'id':'b','dependencies':['a']});second=seq.plan(tasks);self.assertNotEqual(first['source_sha256'],second['source_sha256'])
 def test_forecast_includes_same_sequence_without_new_root_commands(self):
  state={'objectives':[{'id':'one','title':'One','status':'planned','scope':'implementation'}]};report=inspection.goal_portfolio(state);self.assertEqual(report['implementation_sequence']['tasks'][0]['id'],'one')
 def test_native_discovery_is_not_used_to_resolve_local_only_maintenance(self):
  state={'objectives':[{'id':'local','status':'blocked','execution_kind':'local_orchestration'}]}
  with patch.object(cli.intelligent_executor,'discover',side_effect=AssertionError('No native discovery for local maintenance')):
   self.assertIsNone(cli.discover_with_executor({},state))
  self.assertEqual(state['executor_state']['discovery_budget_status'],'LOCAL_CONTROLLER_ONLY')
