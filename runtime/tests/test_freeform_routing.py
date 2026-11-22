import contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli,freeform_routing
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
 def test_explicit_p2p_asset_fetch_skips_executor_and_only_quarantines(self):
  text='Use the existing response parser';candidate={'asset_id':'asset-1','seller_peer_id':'peer-1','feature_id':'parser','license_id':'MIT'}
  exchange=type('ExchangeFixture',(),{'load':lambda self:{'enabled':True,'network':True}})()
  with patch.object(cli,'load_config',return_value=self.config),patch.object(cli,'load_state_for_read',return_value=self.state),patch('urace.peer_exchange.Exchange',return_value=exchange),patch('urace.remote_assets.discover',return_value={'open_assets':[candidate]}),patch('urace.remote_assets.fetch_open_asset',return_value={'status':'QUARANTINED','applied':False}) as fetch,patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=AssertionError('P2P selection must bypass classifier')),contextlib.redirect_stdout(io.StringIO()) as out:
   rc=cli.main(['classify',text,'--json','--p2p-asset','asset-1'])
  result=json.loads(out.getvalue());self.assertEqual(rc,0);self.assertEqual(result['status'],'p2p_asset_quarantined');self.assertFalse(result['applied']);fetch.assert_called_once()
 def test_freeform_ranks_assets_after_classification_using_goal_fields(self):
  text='Please urgently update deployment settings for login'
  item=self.item('goal',{'title':'Improve checkout latency','success_measure':'p95 response time below 200ms'},text)
  features=[{'feature_id':'deployment-settings','description':'urgent login deployment settings'},
            {'feature_id':'checkout-latency','description':'checkout p95 response time latency optimizer'}]
  exchange=type('ExchangeFixture',(),{'load':lambda self:{'enabled':False,'network':False}})()
  with patch('urace.peer_exchange.Exchange',return_value=exchange),patch.object(freeform_routing,'_p2p_free_features',return_value=features),patch.object(freeform_routing,'_p2p_paid_features',return_value=[]):
   rc,result,queued=self.runtext(text,self.batch(text,[item]))
  self.assertEqual(rc,2)  # classified goal is retained pending user confirmation
  self.assertEqual(result['p2p_suggestions'][0]['feature_id'],'checkout-latency')
  self.assertIn('intent-fields-v1', result['p2p_suggestions'][0]['match_method'])
  self.assertEqual(result['value_route']['matching_stage'],'post-classification goal/intent fields')
  queued.assert_not_called()
 def test_non_actionable_input_skips_asset_discovery(self):
  text='Hello there';item=self.item('response',{'text':'Hello!'},text)
  with patch.object(freeform_routing,'_p2p_free_features',side_effect=AssertionError('no catalog read')),patch('urace.remote_assets.discover',side_effect=AssertionError('no peer lookup')):
   rc,result,queued=self.runtext(text,self.batch(text,[item]))
  self.assertEqual(rc,0);self.assertEqual(result['remote_p2p_discovery']['status'],'NOT_APPLICABLE_NO_ACTIONABLE_INTENT')
  self.assertEqual(result['p2p_suggestions'],[]);queued.assert_not_called()

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

class CancelDetectionTests(unittest.TestCase):
 def test_cancel_re_matches_all_cancel_words(self):
  from urace.freeform_routing import _CANCEL_RE
  for word in ('cancel','Cancel','CANCEL','ignore','never mind','nevermind','forget','forget it','forget that','abort','scratch that','no thanks','undo','cancel.','  cancel  '):
   self.assertIsNotNone(_CANCEL_RE.match(word),f'Expected _CANCEL_RE to match {word!r}')

 def test_cancel_re_does_not_match_normal_input(self):
  from urace.freeform_routing import _CANCEL_RE
  for word in ('cancellation task','ignore me later','do not abort','forgotten goal','undone work','cancel the sprint','abort the mission','I want to cancel'):
   self.assertIsNone(_CANCEL_RE.match(word),f'Expected _CANCEL_RE NOT to match {word!r}')

 def _run_cancel(self,text,state_override=None,extra=()):
  import copy,io,tempfile
  from unittest.mock import patch
  config=copy.deepcopy(cli.load_config());config.pop('active_product',None)
  with tempfile.TemporaryDirectory() as tmp:
   config['state_path']=str(Path(tmp)/'state.json')
   state=cli.initial_state(config)
   if state_override:state.update(state_override)
   with patch.object(cli,'load_config',return_value=config),patch.object(cli,'load_state_for_read',return_value=state),patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=AssertionError('LLM must not be called for cancel')),contextlib.redirect_stdout(io.StringIO()) as out:
    rc=cli.main(['classify',text,'--json',*extra])
  return rc,json.loads(out.getvalue())

 def test_cancel_with_nothing_queued_returns_zero_and_nothing_to_cancel(self):
  rc,result=self._run_cancel('cancel')
  self.assertEqual(rc,0);self.assertEqual(result.get('status'),'nothing_to_cancel')

 def test_never_mind_with_nothing_queued_returns_zero(self):
  rc,result=self._run_cancel('never mind')
  self.assertEqual(rc,0);self.assertEqual(result.get('status'),'nothing_to_cancel')

 def test_abort_with_nothing_queued_returns_zero(self):
  rc,result=self._run_cancel('abort')
  self.assertEqual(rc,0);self.assertEqual(result.get('status'),'nothing_to_cancel')

 def test_cancel_with_recent_queued_in_state_cancels_it(self):
  import time
  recent=[{'kind':'goal','id':'inp-test-123','label':'Improve latency','at':time.time()}]
  rc,result=self._run_cancel('cancel',state_override={'recently_queued':recent})
  self.assertEqual(rc,0);self.assertIn(result.get('status'),('cancelled','nothing_to_cancel'))

 def test_cancel_does_not_call_llm(self):
  rc,result=self._run_cancel('cancel')
  self.assertEqual(rc,0)

 def test_cancel_plain_text_output(self):
  import io,copy,tempfile
  from unittest.mock import patch
  config=copy.deepcopy(cli.load_config());config.pop('active_product',None)
  with tempfile.TemporaryDirectory() as tmp:
   config['state_path']=str(Path(tmp)/'state.json')
   state=cli.initial_state(config)
   with patch.object(cli,'load_config',return_value=config),patch.object(cli,'load_state_for_read',return_value=state),patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=AssertionError('no LLM for cancel')),contextlib.redirect_stdout(io.StringIO()) as out:
    rc=cli.main(['classify','cancel'])
  self.assertEqual(rc,0);self.assertIn('cancel',out.getvalue().lower())


class ClarificationLoopTests(unittest.TestCase):
 setUp=FreeformRoutingTests.setUp
 item=FreeformRoutingTests.item
 batch=FreeformRoutingTests.batch
 runtext=FreeformRoutingTests.runtext
 def test_json_mode_surfaces_clarifying_question_without_prompting(self):
  # JSON mode: clarifying_question returned in result, no interactive prompt
  text='Improve something';item=self.item('goal',{'title':'Improve something','success_measure':'better'},text,confidence=0.4)
  b={**self.batch(text,[item]),'clarifying_question':'What specifically should be improved?'}
  rc,result,queued=self.runtext(text,b)
  self.assertEqual(rc,2);self.assertEqual(result['status'],'interpretation_required')
  self.assertEqual(result['clarifying_question'],'What specifically should be improved?')
  self.assertEqual(len(result['deferred']),1);queued.assert_not_called()
 def test_interactive_clarification_resolves_ambiguous_goal(self):
  import copy,io,tempfile
  text='Improve something';cq='What specifically?'
  enriched=text+' ['+cq+': performance]'
  low=self.item('goal',{'title':'Improve something','success_measure':'better'},text,confidence=0.4)
  resolved={'type':'goal','subtype':None,'parameters':{'title':'Improve performance','success_measure':'lower p95 latency','priority':70,'expected_value':0.7,'estimated_cost':0.5,'risk':0.3,'urgency':0.5,'dependencies':[],'target':'product'},'raw_text':text,'confidence':0.95,'reasoning':'clarified'}
  first_b={'items':[low],'raw_text':text,'compound':False,'logic':'and','clarifying_question':cq}
  second_b={'items':[resolved],'raw_text':enriched,'compound':False,'logic':'and'}
  config=copy.deepcopy(cli.load_config());config.pop('active_product',None);config['executor']['enabled']=True
  with tempfile.TemporaryDirectory() as tmp:
   config['state_path']=str(Path(tmp)/'state.json')
   state=cli.initial_state(config)
   with patch.object(cli,'load_config',return_value=config),patch.object(cli,'load_state_for_read',return_value=state),patch.object(cli.intelligent_executor,'pool_availability',return_value={'available':True}),patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=[{'message':json.dumps(first_b)},{'message':json.dumps(second_b)}]),patch('builtins.input',return_value='performance'),patch.object(cli,'queue_input',return_value={'id':'q1'}) as queued,patch.object(freeform_routing,'_p2p_free_features',return_value=[]),patch.object(freeform_routing,'_p2p_paid_features',return_value=[]),patch('urace.remote_assets.discover',return_value={'open_assets':[],'paid_listings':[],'peer_failures':[]}),contextlib.redirect_stdout(io.StringIO()):
    rc=cli.main(['classify',text,'--confirm'])
  self.assertEqual(rc,0)
  kinds=[c.args[1] for c in queued.call_args_list]
  self.assertIn('goal',kinds);self.assertIn('context_input',kinds)
 def test_clarification_cancel_mid_loop_queues_nothing(self):
  import copy,io,tempfile
  text='Improve something';cq='What specifically?'
  low=self.item('goal',{'title':'Improve something','success_measure':'better'},text,confidence=0.4)
  b={'items':[low],'raw_text':text,'compound':False,'logic':'and','clarifying_question':cq}
  config=copy.deepcopy(cli.load_config());config.pop('active_product',None);config['executor']['enabled']=True
  with tempfile.TemporaryDirectory() as tmp:
   config['state_path']=str(Path(tmp)/'state.json')
   state=cli.initial_state(config)
   with patch.object(cli,'load_config',return_value=config),patch.object(cli,'load_state_for_read',return_value=state),patch.object(cli.intelligent_executor,'pool_availability',return_value={'available':True}),patch.object(cli.intelligent_executor,'run_routed_codex',return_value={'message':json.dumps(b)}),patch('builtins.input',return_value='cancel'),patch.object(cli,'queue_input',return_value={'id':'q1'}) as queued,patch.object(freeform_routing,'_p2p_free_features',return_value=[]),patch.object(freeform_routing,'_p2p_paid_features',return_value=[]),contextlib.redirect_stdout(io.StringIO()):
    cli.main(['classify',text,'--confirm'])
  # cancel in clarification loop breaks out; low-confidence item defers, nothing queued
  queued.assert_not_called()


class TokenBudgetTests(unittest.TestCase):
 def _run_over_budget(self,limit,tokens):
  import copy,io,tempfile
  from datetime import datetime,timezone
  config=copy.deepcopy(cli.load_config());config.pop('active_product',None)
  config.setdefault('executor',{}).update({'freeform_max_tokens_per_24h':limit,'enabled':True})
  with tempfile.TemporaryDirectory() as tmp:
   config['state_path']=str(Path(tmp)/'state.json')
   state=cli.initial_state(config)
   state.setdefault('executor_state',{})['executor_calls']=[{'kind':'freeform-routing','tokens':tokens,'at':datetime.now(timezone.utc).isoformat()}]
   Path(config['state_path']).write_text(json.dumps(state))  # state file must exist for load_state_for_read to be called
   with patch.object(cli,'load_config',return_value=config),patch.object(cli,'load_state_for_read',return_value=state),patch.object(cli.intelligent_executor,'pool_availability',return_value={'available':True}),patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=AssertionError('budget must block call')),contextlib.redirect_stdout(io.StringIO()) as out:
    rc=cli.main(['classify','improve latency','--json'])
  return rc,json.loads(out.getvalue())
 def test_exceeded_24h_budget_blocks_inference_with_helpful_error(self):
  rc,result=self._run_over_budget(limit=100,tokens=200)
  self.assertEqual(rc,1);self.assertIn('token budget exceeded',result['error'])
 def test_within_24h_budget_allows_inference(self):
  import copy,io,tempfile
  from datetime import datetime,timezone
  config=copy.deepcopy(cli.load_config());config.pop('active_product',None)
  config.setdefault('executor',{}).update({'freeform_max_tokens_per_24h':10000,'enabled':True})
  text='Improve latency';b={'items':[{'type':'goal','subtype':None,'parameters':{'title':'Improve latency','success_measure':'latency','priority':70,'expected_value':0.7,'estimated_cost':0.5,'risk':0.3,'urgency':0.5,'dependencies':[],'target':'product'},'raw_text':text,'confidence':0.99,'reasoning':'ok'}],'raw_text':text,'compound':False,'logic':'and'}
  with tempfile.TemporaryDirectory() as tmp:
   config['state_path']=str(Path(tmp)/'state.json')
   state=cli.initial_state(config)
   state.setdefault('executor_state',{})['executor_calls']=[{'kind':'freeform-routing','tokens':50,'at':datetime.now(timezone.utc).isoformat()}]
   Path(config['state_path']).write_text(json.dumps(state))
   with patch.object(cli,'load_config',return_value=config),patch.object(cli,'load_state_for_read',return_value=state),patch.object(cli.intelligent_executor,'pool_availability',return_value={'available':True}),patch.object(cli.intelligent_executor,'run_routed_codex',return_value={'message':json.dumps(b)}),patch.object(cli,'queue_input',return_value={'id':'q1'}),contextlib.redirect_stdout(io.StringIO()):
    rc=cli.main(['classify',text,'--json','--confirm'])
  self.assertEqual(rc,0)


class LedgerContextTests(unittest.TestCase):
 setUp=FreeformRoutingTests.setUp
 item=FreeformRoutingTests.item
 batch=FreeformRoutingTests.batch
 runtext=FreeformRoutingTests.runtext
 def test_ledger_context_never_disables_p2p_discovery_and_suggestions(self):
  text='Improve latency';item=self.item('goal',{'title':'Improve latency','success_measure':'low p95'},text)
  with patch.object(freeform_routing,'_p2p_free_features',side_effect=AssertionError('no catalog lookup with never')),patch('urace.remote_assets.discover',side_effect=AssertionError('no peer lookup with never')):
   rc,result,queued=self.runtext(text,self.batch(text,[item]),extra=['--ledger-context','never','--confirm'])
  self.assertEqual(result['remote_p2p_discovery']['status'],'DISABLED_BY_REQUEST')
  self.assertEqual(result['p2p_suggestions'],[])
  self.assertIn('p2p_candidates_disabled',result['value_route'])
 def test_ledger_context_auto_searches_when_exchange_network_enabled(self):
  text='Improve latency';item=self.item('goal',{'title':'Improve latency','success_measure':'lower latency'},text)
  exchange=type('ExchangeFixture',(),{'load':lambda self:{'enabled':True,'network':True}})()
  with patch('urace.peer_exchange.Exchange',return_value=exchange),patch.object(freeform_routing,'_p2p_free_features',return_value=[]),patch.object(freeform_routing,'_p2p_paid_features',return_value=[]),patch('urace.remote_assets.discover',return_value={'open_assets':[],'paid_listings':[],'peer_failures':[]}) as disc:
   rc,result,queued=self.runtext(text,self.batch(text,[item]))
  self.assertEqual(result['remote_p2p_discovery']['status'],'SEARCHED_PINNED_PEERS')
  disc.assert_called_once()
 def test_ledger_context_auto_skips_when_exchange_network_disabled(self):
  text='Improve latency';item=self.item('goal',{'title':'Improve latency','success_measure':'lower latency'},text)
  exchange=type('ExchangeFixture',(),{'load':lambda self:{'enabled':True,'network':False}})()
  with patch('urace.peer_exchange.Exchange',return_value=exchange),patch.object(freeform_routing,'_p2p_free_features',return_value=[]),patch.object(freeform_routing,'_p2p_paid_features',return_value=[]):
   rc,result,queued=self.runtext(text,self.batch(text,[item]))
  self.assertEqual(result['remote_p2p_discovery']['status'],'NETWORK_DISABLED')


class LowConfidenceDeferralTests(unittest.TestCase):
 setUp=FreeformRoutingTests.setUp
 item=FreeformRoutingTests.item
 batch=FreeformRoutingTests.batch
 runtext=FreeformRoutingTests.runtext
 def test_low_confidence_goal_deferred_with_question_in_json_result(self):
  text='Improve something';item=self.item('goal',{'title':'Improve something','success_measure':'better'},text,confidence=0.5)
  b={**self.batch(text,[item]),'clarifying_question':'What aspect should be improved?'}
  rc,result,queued=self.runtext(text,b)
  self.assertEqual(rc,2);self.assertEqual(result['status'],'interpretation_required')
  self.assertEqual(len(result['deferred']),1);self.assertEqual(result['clarifying_question'],'What aspect should be improved?')
  queued.assert_not_called()
 def test_low_confidence_intent_deferred_in_json_mode(self):
  text='Preserve something';item=self.item('intent',{'statement':'Preserve something'},text,'directive',confidence=0.5)
  rc,result,queued=self.runtext(text,self.batch(text,[item]))
  self.assertEqual(rc,2);self.assertEqual(len(result['deferred']),1);queued.assert_not_called()
 def test_low_confidence_prohibition_deferred_in_json_mode(self):
  text='Never do that';item=self.item('constraint',{'statement':'Never do that'},text,'prohibition',confidence=0.4)
  rc,result,queued=self.runtext(text,self.batch(text,[item]))
  self.assertEqual(rc,2);self.assertEqual(len(result['deferred']),1);queued.assert_not_called()
 def test_high_confidence_goal_queues_with_confirm(self):
  text='Improve latency';item=self.item('goal',{'title':'Improve latency','success_measure':'p95 under 200ms'},text,confidence=0.95)
  rc,result,queued=self.runtext(text,self.batch(text,[item]),['--confirm'])
  self.assertEqual(rc,0);self.assertEqual(result['status'],'classified');queued.assert_called_once()
