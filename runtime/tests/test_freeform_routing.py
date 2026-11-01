import contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli,_common,freeform_routing
class FreeformRoutingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.config=copy.deepcopy(cli.load_config());self.config.pop('active_product',None);self.config['state_path']=str(Path(self.tmp.name)/'state.json');self.config['executor']['enabled']=True
  self.state=cli.initial_state(self.config)
 def item(self,kind,params,text,subtype=None,confidence=.99):return {'type':kind,'subtype':subtype,'parameters':params,'raw_text':text,'confidence':confidence,'reasoning':'fixture evidence'}
 def batch(self,text,items,logic='and'):return {'items':items,'raw_text':text,'compound':len(items)>1,'logic':logic}
 def runtext(self,text,batch,extra=()):
  with patch.object(cli,'load_config',return_value=self.config),patch.object(cli,'load_state_for_read',return_value=self.state),patch.object(cli.intelligent_executor,'pool_availability',return_value={'available':True}),patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=batch if isinstance(batch,list) else None,return_value={'message':json.dumps(batch)}),patch.object(cli,'queue_input',return_value={'id':'queued-fixture'}) as queued,contextlib.redirect_stdout(io.StringIO()) as out:
   rc=cli.main(['classify',text,'--json',*extra])
  return rc,json.loads(out.getvalue()),queued
 def test_single_item_null_logic_normalizes_without_losing_intent(self):
  text='hello';batch=self.batch(text,[self.item('response',{'text':'Hello'},text)],None)
  rc,result,queued=self.runtext(text,batch);self.assertEqual(rc,0);self.assertEqual(result['batch']['logic'],'and');queued.assert_not_called()
 def test_backend_exception_is_structured_and_not_retried_as_language_error(self):
  with patch.object(cli,'load_config',return_value=self.config),patch.object(cli,'load_state_for_read',return_value=self.state),patch.object(cli.intelligent_executor,'pool_availability',return_value={'available':True}),patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=RuntimeError('native transport failure')) as run,contextlib.redirect_stdout(io.StringIO()) as out:
   rc=cli.main(['classify','hello','--json'])
  self.assertEqual(rc,2);self.assertEqual(json.loads(out.getvalue())['queued'],[]);self.assertEqual(run.call_count,1)
 def test_task_goes_to_durable_goal_not_direct_execution(self):
  text='Improve checkout latency to under 200ms';item=self.item('goal',{'title':'Improve checkout latency','success_measure':'p95 under 200ms'},text)
  rc,result,queued=self.runtext(text,self.batch(text,[item]),['--confirm']);self.assertEqual(rc,0);self.assertEqual(queued.call_args.args[1],'goal');self.assertEqual(queued.call_args.args[2]['source_text'],text)
 def test_compound_semantic_sections_kept_separate(self):
  text='Improve checkout; preserve usability; never publish externally';items=[self.item('goal',{'title':'Improve checkout','success_measure':'measure checkout latency'},'Improve checkout'),self.item('intent',{'statement':'preserve usability'},'preserve usability','directive'),self.item('constraint',{'statement':'never publish externally'},'never publish externally','prohibition')]
  rc,result,queued=self.runtext(text,self.batch(text,items),['--confirm']);self.assertEqual(rc,0);self.assertEqual([c.args[1] for c in queued.call_args_list],['goal','intent_control','constraint_control'])
 def test_command_semantic_section_uses_installed_multiword_path(self):
  text='Show the executor status';item=self.item('command',{'command':'status executors','args':[]},text)
  rc,result,queued=self.runtext(text,self.batch(text,[item]));self.assertEqual(rc,0);self.assertEqual(result['commands'][0]['exit_code'],0);queued.assert_not_called()
 def test_conversation_does_not_queue_task(self):
  text='Hello, “URACE”! 👋';item=self.item('response',{'text':'Hello!'},text)
  rc,result,queued=self.runtext(text,self.batch(text,[item]));self.assertEqual(rc,0);self.assertEqual(result['text'],text);self.assertEqual(result['responses'],['Hello!']);queued.assert_not_called()
 def test_changed_source_text_is_rejected_without_writes(self):
  text='Improve latency';item=self.item('goal',{'title':'Improve latency','success_measure':'latency'},'unrelated input')
  rc,result,queued=self.runtext(text,self.batch(text,[item]),['--confirm']);self.assertEqual(rc,1);queued.assert_not_called()
 def test_malformed_response_gets_one_corrective_retry(self):
  text='hello';valid=self.batch(text,[self.item('response',{'text':'Hello'},text)])
  rc,result,queued=self.runtext(text,[{'message':'not JSON'},{'message':json.dumps(valid)}]);self.assertEqual(rc,0);self.assertEqual(result['routing_attempts'],2);queued.assert_not_called()
 def test_unknown_command_does_not_recurse_into_classification(self):
  text='Do the thing';item=self.item('command',{'command':'not-installed','args':[]},text)
  rc,result,queued=self.runtext(text,self.batch(text,[item]));self.assertEqual(rc,1);queued.assert_not_called()
 def test_alternatives_not_silently_combined(self):
  text='Improve checkout or improve signup';items=[self.item('goal',{'title':'Checkout','success_measure':'checkout latency'},'Improve checkout'),self.item('goal',{'title':'Signup','success_measure':'signup latency'},'improve signup')]
  rc,result,queued=self.runtext(text,self.batch(text,items,'or'),['--confirm']);self.assertEqual(rc,2);queued.assert_not_called()
  rc,result,queued=self.runtext(text,self.batch(text,items,'or'),['--confirm','--selection','2']);self.assertEqual(rc,0);self.assertEqual(queued.call_args.args[2]['title'],'Signup')
 def test_conditional_and_sequential_not_flattened(self):
  for logic in ('conditional','sequential'):
   text='If the build passes, deploy';item=self.item('goal',{'title':'Deploy after build','success_measure':'build passes before deploy'},text)
   rc,result,queued=self.runtext(text,self.batch(text,[item],logic),['--confirm']);self.assertEqual(rc,2);queued.assert_not_called()
 def test_permissions_and_low_confidence_not_auto_applied(self):
  text='Allow publishing';item=self.item('constraint',{'statement':'Allow publishing'},text,'permission')
  rc,result,queued=self.runtext(text,self.batch(text,[item]),['--confirm']);self.assertEqual(rc,2);queued.assert_not_called()
  item=self.item('goal',{'title':'Publish','success_measure':'published'},text,confidence=.2)
  rc,result,queued=self.runtext(text,self.batch(text,[item]),['--confirm']);self.assertEqual(rc,2);queued.assert_not_called()
 def test_noninteractive_inference_retains_proposed_work_without_blocking_stdin(self):
  text='Improve latency';item=self.item('goal',{'title':'Improve latency','success_measure':'latency'},text)
  with patch('builtins.input',side_effect=AssertionError('interactive prompt')):
   rc,result,queued=self.runtext(text,self.batch(text,[item]));self.assertEqual(rc,2);queued.assert_not_called()
 def test_unavailable_executor_does_not_fabricate_interpretation(self):
  with patch.object(cli,'load_config',return_value=self.config),patch.object(cli,'load_state_for_read',return_value=self.state),patch.object(cli.intelligent_executor,'pool_availability',return_value={'available':False}),patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=AssertionError('unavailable call')),contextlib.redirect_stdout(io.StringIO()) as out:
   rc=cli.main(['classify','hello','--json'])
  self.assertEqual(rc,1);self.assertIn('unavailable',json.loads(out.getvalue())['error'])

class RoutingCoverageAndReuseTests(unittest.TestCase):
 setUp=FreeformRoutingTests.setUp
 item=FreeformRoutingTests.item
 batch=FreeformRoutingTests.batch
 runtext=FreeformRoutingTests.runtext
 def test_punctuation_does_not_require_a_model_retry(self):
  from urace.intent_trace import source_coverage
  self.assertEqual(source_coverage('Keep A; preserve B.',[{'raw_text':'Keep A'},{'raw_text':'preserve B'}])['status'],'SOURCE_COVERED')
  self.assertEqual(source_coverage('Keep A; delete B.',[{'raw_text':'Keep A'}])['status'],'UNASSIGNED_SOURCE')
 def test_confirmation_reuses_validated_classification_without_native_call(self):
  text='Improve latency';batch=self.batch(text,[self.item('goal',{'title':'Latency','success_measure':'latency'},text)])
  rc,first,_=self.runtext(text,batch);self.assertEqual(rc,2)
  with patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=AssertionError('No repeated inference')) as native,patch.object(cli,'load_config',return_value=self.config),patch.object(cli,'load_state_for_read',return_value=self.state),patch.object(cli,'queue_input',return_value={'id':'cached'}),contextlib.redirect_stdout(io.StringIO()) as out:
   rc=cli.main(['classify',text,'--json','--confirm'])
  self.assertEqual(rc,0);self.assertEqual(json.loads(out.getvalue())['routing_source'],'VALIDATED_CACHE');native.assert_not_called()
 def test_generated_listener_and_api_wrapper_cannot_dispatch(self):
  for command in ('api serve --transport stdio','watch events --follow'):
   text='Show status';batch=self.batch(text,[self.item('command',{'command':command,'args':[]},text)])
   rc,result,queued=self.runtext(text,batch,['--confirm']);self.assertEqual(rc,1);queued.assert_not_called()
