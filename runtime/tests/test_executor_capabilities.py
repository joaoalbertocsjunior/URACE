import copy,hashlib,json,unittest
from urace import executor_capabilities as ec,cli,api_interface,command_surface

class CapabilityTests(unittest.TestCase):
 def task(self,n=3):return {'family':'receipts','intent':'Receipt integrity','requirements':[{'id':'r'+str(i),'title':'Requirement '+str(i),'success_measure':'Public check '+str(i)} for i in range(n)]}
 def test_defaults_auto_and_no_model_or_host_setup(self):
  packet=ec.prepare({},'codex',self.task());self.assertTrue(ec.settings({})['enabled']);self.assertEqual(packet['model_calls'],0);self.assertFalse(packet['native_plugin_injection_verified']);self.assertEqual(packet['skills'][0]['id'],'urace-receipt-review');self.assertNotIn('instructions',ec.read(packet,'@skills')['skills'][0])
 def test_executor_and_task_relevance_skip_unsuitable_skills(self):
  packet=ec.prepare({},'claude',{'family':'navigation','requirements':[]});self.assertEqual(packet['skills'],[]);self.assertTrue(all(x['reason']=='NO_CONCRETE_TASK_MATCH' for x in packet['skipped_skills']))
 def test_disabled_skills_do_not_disable_context_guard(self):
  p=ec.prepare({'executor_skills':{'enabled':False}},'codex',self.task());self.assertEqual(p['skills'],[]);self.assertEqual(len(p['requirements']),3)
 def test_bounded_catalog_pins_and_no_setup_scripts(self):
  s={**copy.deepcopy(ec.BUILTINS[0]),'id':'owner-review','sha256':hashlib.sha256(ec.BUILTINS[0]['instructions'].encode()).hexdigest()};self.assertTrue(ec.settings({'executor_skills':{'catalog':[s]}}));s['instructions']+='changed'
  with self.assertRaises(ValueError):ec.settings({'executor_skills':{'catalog':[s]}})
  s['setup_script']='curl unsafe'
  with self.assertRaises(ValueError):ec.settings({'executor_skills':{'catalog':[s]}})
 def test_middle_and_last_requirements_remain_losslessly_retrievable(self):
  task=self.task(137);p=ec.prepare({},'codex',task);ids=[];start=1
  while start:
   page=ec.read(p,'@requirements',start);ids.extend(row['id'] for row in page['entries']);start=page['next_start']
  self.assertEqual(ids,[r['id'] for r in task['requirements']]);self.assertEqual(ec.read(p,'@requirement/r68')['passage'],task['requirements'][68]);self.assertEqual(ec.read(p,'@requirement/r136')['passage'],task['requirements'][-1]);self.assertFalse(ec.read(p,'@requirements')['comprehension_proven'])
 def test_missing_critical_passage_blocks_but_read_is_not_comprehension(self):
  task=self.task();task['requirements'][1]['requires_explicit_context_read']=True;p=ec.prepare({},'codex',task);self.assertEqual(ec.feedback(p,[])['status'],'MISSING_REQUIRED_CONTEXT');feedback=ec.feedback(p,[{'tool':'read_file','path':'@requirement/r1'}]);self.assertEqual(feedback['status'],'PROTOCOL_SATISFIED');self.assertFalse(feedback['understanding_proven'])
 def test_clarification_returns_source_then_can_require_owner(self):
  p=ec.prepare({},'codex',self.task());result=ec.clarify(p,'r1',json.dumps({'question':'Which boundary applies?'}));self.assertEqual(result['status'],'SOURCE_PASSAGE_RETURNED');question=ec.clarify(p,'r1',json.dumps({'question':'Meaning still ambiguous','needs_owner':True}));self.assertEqual(ec.feedback(p,[{'tool':'write_file','clarification':question}])['status'],'AWAITING_OWNER_CLARIFICATION');p['clarifications']['r1']='Owner-defined boundary';self.assertEqual(ec.clarify(p,'r1',json.dumps({'question':'Confirm boundary','needs_owner':True}))['status'],'ANSWERED_FROM_OWNER_CONTEXT')
 def test_unknown_requirements_and_duplicate_ids_fail_closed(self):
  p=ec.prepare({},'codex',self.task())
  with self.assertRaises(ValueError):ec.read(p,'@requirement/unknown')
  task=self.task();task['requirements'][1]['id']='r0'
  with self.assertRaises(ValueError):ec.prepare({},'codex',task)
 def test_skill_and_context_conditions_are_versioned(self):
  a=ec.prepare({},'codex',self.task())['contract_sha256'];b=ec.prepare({'executor_skills':{'enabled':False}},'codex',self.task())['contract_sha256'];self.assertNotEqual(a,b)
 def test_shared_cli_api_controls_and_clarification_discovery(self):
  parser=cli.build_parser();paths=command_surface.operation_parsers(parser)
  for name in ('configuration executor-skills','configuration context-guard','product work clarify'):self.assertIn(name,paths)
  args=api_interface.build_argv(parser,command='product work clarify',params={'project':'/tmp/fixture','requirement_id':'r1','answer':'Owner answer'});self.assertIn('--answer',args);self.assertFalse(command_surface.read_only(args));self.assertTrue(command_surface.read_only(['configuration','executor-skills']))
