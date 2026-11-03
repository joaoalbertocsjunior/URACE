import copy,json,unittest
from datetime import datetime,timezone
from urace import cli,inspection,executor,user_controls,_common
class NullableBudgets(unittest.TestCase):
 def test_unlimited_has_no_count_rejection_or_nonfinite_json(self):
  config=copy.deepcopy(cli.load_config());config['executor']['max_executor_calls_per_24h']=None;config['executor']['max_executor_calls_per_30d']=None
  state=cli.initial_state(config);state['executor_state']['executor_calls']=[{'at':datetime.now(timezone.utc).isoformat(),'stage':'execution'} for _ in range(100)]
  self.assertTrue(cli.executor_execution_allowed(config,state));report=inspection.resource_accounting(config,state);self.assertIsNone(report['estimated_executor_capacity']['remaining_calls_24h']);json.dumps(report,allow_nan=False)
  config['executor']['max_executor_calls_per_24h']=2;self.assertFalse(cli.executor_execution_allowed(config,state))
 def test_native_adapter_alias_and_specific_override_precedence(self):
  settings={'native_options':{'codex':{'model':'adapter-model','native_effort':'low'},'primary':{'native_effort':'high'}}};resolved=executor.provider_settings(settings,{'id':'primary','adapter':'codex-cli'});self.assertEqual(resolved['model'],'adapter-model');self.assertEqual(resolved['native_effort'],'high')
 def test_resource_effort_alias_stays_separate_from_native_reasoning(self):
  config={'resources':{'effort':'medium','executor_effort':{'codex':'high'}},'executor':{'providers':[{'id':'primary','adapter':'codex-cli'}],'native_options':{'codex':{'native_effort':'low'}}}}
  self.assertEqual(user_controls.resource_profile(config,'primary')['effort'],'high');self.assertEqual(executor.provider_settings(config['executor'],config['executor']['providers'][0])['native_effort'],'low')

 def test_semantic_technique_gate_accepts_unlimited_without_arithmetic_error(self):
  state={'lifecycle_state':'ACTIVE','executor_state':{'calls_today':100000}}
  for limit,verdict in [(None,'DELEGATE_EXECUTOR'),(0,'DEFER'),(100002,'DELEGATE_EXECUTOR')]:
   result=_common.technique_applicability_gate('T5',state,{'executor':{'max_executor_calls_per_30d':limit}});self.assertEqual(result['verdict'],verdict);json.dumps(result,allow_nan=False)
