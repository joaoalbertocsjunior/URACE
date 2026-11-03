"""No-inference MCP/API bridge checks, including real bounded child processes."""
import copy,contextlib,io,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli,api_interface,_common,resource_usage
from urace.integration_bridge import Policy,Jobs,BridgeError,load_policy,SCHEMA,operations
from urace.mcp_server import Server,serve

class Fixture(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.parser=cli.build_parser()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir();self.store=self.root/'receipts'
 def policy(self,**kw):return Policy(self.parser,{'project_id':'p','executor_id':'external',**kw},root=self.project,storage=self.store)
 def jobs(self,policy=None,code='import json;print(json.dumps({"status":"ok","output":{"delivered":True}}))',paused=lambda:False):
  j=Jobs(policy or self.policy(),pause_check=paused,command_factory=lambda argv:[sys.executable,'-c',code]);self.addCleanup(j.close);return j

class PolicyTests(Fixture):
 def test_parser_factory_has_no_work_or_configuration_side_effect(self):
  with patch.object(cli,'load_config',side_effect=AssertionError('No config needed')):self.assertIn('api serve',operations(cli.build_parser()))
 def test_catalog_reuses_installed_paths_and_positional_actions(self):
  ops=operations(self.parser)
  for p in ['update download','derive','product work run','product value observe','status quality','add goal']:self.assertIn(p,ops)
 def test_default_policy_readonly_and_compact_catalog(self):
  p=self.policy();self.assertTrue(p.read_only);self.assertLess(len(p.describe()['commands']),15);self.assertTrue(p.describe('goal list')['arguments'])
 def test_unknown_operation_and_recursive_wrappers_rejected(self):
  for name in ['not-real','api call','api batch','api serve','classify']:
   with self.assertRaises(BridgeError):self.policy(commands=[name])
 def test_administration_needs_explicit_operator_policy(self):
  with self.assertRaises(BridgeError):self.policy(commands=['update apply'])
  self.assertIn('update apply',self.policy(operator=True,commands=['update apply']).grants)
 def test_mutation_does_not_inherit_readonly_permission(self):
  with self.assertRaises(BridgeError):self.policy(commands=['add goal']).authorize('add goal',{'title':'x','success_measure':'verified','reason':'declared work'})
 def test_fixed_scope_cannot_be_overridden(self):
  p=self.policy(read_only=False,commands=[{'command':'product work run','fixed_params':{'project':str(self.project)},'allowed_params':['executor']}]);p.authorize('product work run',{'executor':'codex'})
  with self.assertRaises(BridgeError):p.authorize('product work run',{'project':'/other'})
  with self.assertRaises(BridgeError):p.authorize('product work run',{'max_seconds':100})
 def test_invalid_params_or_prose_never_reach_a_runner(self):
  p=self.policy()
  for command,params in [('please help',{}),('goal list',{'typo':'x'}),('goal list',{'limit':-1}),('goal list',[])]:
   # CLI central validation handles semantic negative ranges; the bridge also rejects them.
   with self.assertRaises(BridgeError):p.authorize(command,params)
 def test_persistent_auto_is_rejected_but_finite_work_is_supported(self):
  p=self.policy(read_only=False,commands=['auto'])
  with self.assertRaises(BridgeError):p.authorize('auto',{})
  self.assertFalse(p.authorize('auto',{'cycles':1})[1])
 def test_project_identity_may_be_a_uri(self):self.assertEqual(self.policy(project_id='urace-spec:/a/b').raw['project_id'],'urace-spec:/a/b')
 def test_resource_requires_explicit_grant(self):
  with self.assertRaises(BridgeError):self.policy().read_resource('urace://project/secret')
 def test_resource_confines_paths_and_refuses_symlink_components(self):
  (self.project/'doc.txt').write_text('useful context');p=self.policy(resources=[{'uri':'urace://project/doc','path':'doc.txt'}]);self.assertEqual(p.read_resource('urace://project/doc')['text'],'useful context');(self.project/'alias').symlink_to(self.project,target_is_directory=True);p=self.policy(resources=[{'uri':'urace://project/doc','path':'alias/doc.txt'}])
  with self.assertRaises(OSError):p.read_resource('urace://project/doc')
 def test_hidden_escape_and_reserved_uris_rejected(self):
  for path,uri in [('../secret','urace://p/x'),('/etc/passwd','urace://p/x'),('.envrc','urace://p/x'),('doc','urace://session/capabilities'),('doc','urace://jobs/a')]:
   with self.assertRaises(BridgeError):self.policy(resources=[{'uri':uri,'path':path}])
 def test_resource_byte_limit_is_enforced(self):
  (self.project/'doc').write_text('x'*2000);p=self.policy(limits={'resource_bytes':1024},resources=[{'uri':'urace://p/doc','path':'doc'}])
  with self.assertRaises(BridgeError):p.read_resource('urace://p/doc')
 def test_policy_file_is_owner_side_and_product_bound(self):
  cfg={'resource_product_id':'p','state_path':str(self.root/'state.json')};file=self.root/'policy.json';file.write_text(json.dumps({'project_id':'p','executor_id':'x'}))
  with patch.object(_common,'load_config',return_value=cfg),patch.object(_common,'ROOT',self.project):
   self.assertEqual(load_policy(self.parser,file).raw['project_id'],'p');file.write_text('{"project_id":"other","executor_id":"x"}')
   with self.assertRaises(BridgeError):load_policy(self.parser,file)
   inner=self.project/'policy.json';inner.write_text('{}')
   with self.assertRaises(BridgeError):load_policy(self.parser,inner)

 def test_binary_resource_uses_mcp_blob(self):
  import base64
  (self.project/'image.bin').write_bytes(b'\xff\x00');p=self.policy(resources=[{'uri':'urace://p/image','path':'image.bin'}]);r=p.read_resource('urace://p/image');self.assertEqual(base64.b64decode(r['blob']),b'\xff\x00')

 def test_fixed_false_cannot_be_overridden_through_a_flag_alias(self):
  p=self.policy(read_only=False,operator=True,commands=[{'command':'derive','fixed_params':{'apply-capabilities':False}}])
  with self.assertRaisesRegex(BridgeError,'Fixed parameter'):p.authorize('derive',{'apply_capabilities':True,'constructs':'AP0'})
 def test_duplicate_aliases_are_rejected(self):
  p=self.policy(read_only=False,commands=['derive'])
  with self.assertRaisesRegex(BridgeError,'Duplicate'):p.authorize('derive',{'constructs':'AP0','patterns':'AP4'})

 def test_parent_api_grant_cannot_smuggle_a_recursive_call(self):
  p=self.policy(read_only=False,commands=['api'])
  with self.assertRaises(BridgeError):p.authorize('api',{'action':'call','api_command':'resume'})
 def test_parent_product_grant_cannot_switch_scope_via_parameters(self):
  p=self.policy(read_only=False,commands=['product'])
  with self.assertRaises(BridgeError):p.authorize('product',{'action':'switch','name':'other'})

class JobTests(Fixture):
 def test_real_child_structured_result_and_attribution(self):
  j=self.jobs();row=j.submit('help',{},'request-1');result=j.wait(row['job_id']);self.assertEqual(result['status'],'COMPLETED');self.assertTrue(result['result']['output']['delivered']);self.assertEqual(result['project_id'],'p');self.assertEqual(result['bridge_inference_calls'],0);self.assertIsNone(result['native_tokens'])
 def test_repeat_request_returns_same_job_and_conflicting_payload_is_rejected(self):
  j=self.jobs();a=j.submit('help',{},'r');j.wait(a['job_id']);b=j.submit('help',{},'r');self.assertEqual(a['job_id'],b['job_id'])
  with self.assertRaises(BridgeError):j.submit('commands',{},'r')
 def test_mutation_requires_idempotency_key(self):
  j=self.jobs(self.policy(read_only=False,commands=['add goal']))
  with self.assertRaises(BridgeError):j.submit('add goal',{'title':'x','success_measure':'verified','reason':'declared work'})
 def test_pause_blocks_mutations_but_allows_inspection(self):
  j=self.jobs(self.policy(read_only=False,commands=['help','add goal']),paused=lambda:True)
  with self.assertRaises(BridgeError):j.submit('add goal',{'title':'x','success_measure':'verified','reason':'declared work'},'r')
  self.assertEqual(j.wait(j.submit('help')['job_id'])['status'],'COMPLETED')
 def test_pause_arriving_during_mutation_cancels_process_group(self):
  state=[False];j=self.jobs(self.policy(read_only=False,commands=['add goal']),code='import time;time.sleep(20)',paused=lambda:state[0]);row=j.submit('add goal',{'title':'x','success_measure':'verified','reason':'declared work'},'r');time.sleep(.1);state[0]=True;self.assertEqual(j.wait(row['job_id'])['status'],'CANCELLED')
 def test_async_status_and_explicit_cancellation(self):
  j=self.jobs(code='import time;time.sleep(20)');row=j.submit('help',{},'r');self.assertIn(row['status'],{'PENDING','RUNNING'});j.cancel(row['job_id']);self.assertEqual(j.wait(row['job_id'])['status'],'CANCELLED')
 def test_deadline_is_enforced(self):
  j=self.jobs(self.policy(limits={'wall_seconds':1}),code='import time;time.sleep(20)');self.assertEqual(j.wait(j.submit('help')['job_id'])['status'],'TIMED_OUT')
 def test_output_byte_limit_is_enforced(self):
  j=self.jobs(self.policy(limits={'output_bytes':1024}),code='print("x"*10000)');self.assertEqual(j.wait(j.submit('help')['job_id'])['status'],'OUTPUT_LIMIT')
 def test_invalid_json_and_nonzero_exit_are_failed_jobs(self):
  for code in ['print("not JSON")','raise SystemExit(2)']:
   j=self.jobs(code=code);self.assertEqual(j.wait(j.submit('help')['job_id'])['status'],'FAILED')
 def test_shutdown_cancels_jobs_and_rejects_new_dispatch(self):
  j=self.jobs(code='import time;time.sleep(20)');r=j.submit('help');j.close();self.assertEqual(j.status(r['job_id'])['status'],'CANCELLED')
  with self.assertRaises(BridgeError):j.submit('help')
 def test_interrupted_receipt_is_retained_without_automatic_replay(self):
  j=self.jobs();r=j.submit('help',{},'r');j.wait(r['job_id']);j.update(r['job_id'],status='RUNNING',owner_pid=99999999);self.assertEqual(j.status(r['job_id'])['status'],'INTERRUPTED');self.assertEqual(j.submit('help',{},'r')['status'],'INTERRUPTED')
 def test_wrong_policy_cannot_read_job(self):
  j=self.jobs();r=j.submit('help');j.wait(r['job_id']);j.update(r['job_id'],policy_sha256='other')
  with self.assertRaises(BridgeError):j.status(r['job_id'])
 def test_depth_and_parent_deadline_are_not_renewed(self):
  j=self.jobs()
  with patch.dict(os.environ,{'URACE_BRIDGE_DEPTH':'4'}):
   with self.assertRaises(BridgeError):j.submit('help')
  with patch.dict(os.environ,{'URACE_BRIDGE_DEADLINE':str(time.time()-1)}):
   with self.assertRaises(BridgeError):j.submit('help')
 def test_job_memory_bookkeeping_is_released_after_completion(self):
  j=self.jobs();r=j.submit('help');j.wait(r['job_id']);self.assertFalse(j.events);self.assertFalse(j.futures)

 def test_cancel_reaps_a_child_with_its_own_session(self):
  from urace.integration_bridge import pid_ticks
  pidfile=self.root/'child.pid';code="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'],start_new_session=True);Path("+repr(str(pidfile))+").write_text(str(p.pid));time.sleep(20)";j=self.jobs(code=code);row=j.submit('help')
  for _ in range(200):
   if pidfile.exists():break
   time.sleep(.01)
  self.assertTrue(pidfile.exists());child=int(pidfile.read_text());j.cancel(row['job_id']);self.assertEqual(j.wait(row['job_id'])['status'],'CANCELLED');self.assertIsNone(pid_ticks(child))

 def test_queue_backpressure_does_not_prevent_inspection_or_cancellation(self):
  j=self.jobs(self.policy(limits={'queued_jobs':1}),code='import time;time.sleep(20)');r=j.submit('help',{},'first')
  with self.assertRaisesRegex(BridgeError,'queue busy'):j.submit('help',{},'second')
  self.assertEqual(j.submit('help',{},'first')['job_id'],r['job_id']);j.cancel(r['job_id']);self.assertEqual(j.wait(r['job_id'])['status'],'CANCELLED')

 def test_cancellation_waits_for_a_transient_receipt_guard(self):
  import fcntl,threading
  j=self.jobs(code='import time;time.sleep(20)');r=j.submit('help',{},'r')
  for _ in range(100):
   if j.status(r['job_id'])['status']=='RUNNING':break
   time.sleep(.01)
  descriptor=os.open(j.path(r['job_id']).with_suffix('.lock.guard'),os.O_RDWR);fcntl.flock(descriptor,fcntl.LOCK_EX)
  release=threading.Thread(target=lambda:(time.sleep(.05),os.close(descriptor)));release.start()
  try:j.cancel(r['job_id']);self.assertEqual(j.wait(r['job_id'])['status'],'CANCELLED')
  finally:release.join()
 def test_simultaneous_managers_cannot_duplicate_a_request(self):
  from concurrent.futures import ThreadPoolExecutor
  counter=self.root/'calls';code="from pathlib import Path;import json,time;p=Path("+repr(str(counter))+");p.open('a').write('one\\n');time.sleep(.1);print(json.dumps({'status':'ok'}))";a=self.jobs(code=code);b=self.jobs(code=code)
  with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda j:j.submit('help',{},'same'),[a,b]))
  self.assertEqual(rows[0]['job_id'],rows[1]['job_id']);a.wait(rows[0]['job_id']);b.wait(rows[0]['job_id'])
  for _ in range(100):
   if a.status(rows[0]['job_id'])['status']=='COMPLETED':break
   time.sleep(.01)
  self.assertEqual(a.status(rows[0]['job_id'])['status'],'COMPLETED');self.assertEqual(counter.read_text().count('one'),1)

 def test_worker_api_failure_retains_structured_error_and_exit_status(self):
  j=self.jobs(code="import json;print(json.dumps({'status':'error','error':'expected failure'}));raise SystemExit(2)");r=j.wait(j.submit('help')['job_id']);self.assertEqual(r['status'],'FAILED');self.assertEqual(r['exit_code'],2);self.assertEqual(r['result']['error'],'expected failure')

class ProtocolTests(Fixture):
 def server(self):
  output=io.StringIO();j=self.jobs();server=Server(j.policy,output,jobs=j);self.addCleanup(server.close);return server,output
 def request(self,s,i,method,params=None):s.receive({'jsonrpc':'2.0','id':i,'method':method,'params':params or {}})
 def initialize(self,s):self.request(s,1,'initialize',{'protocolVersion':'2025-06-18'});s.receive({'jsonrpc':'2.0','method':'notifications/initialized'})
 def test_initialize_and_resource_discovery(self):
  s,out=self.server();self.initialize(s);self.request(s,2,'tools/list');self.request(s,3,'resources/list');rows=[json.loads(x) for x in out.getvalue().splitlines()];self.assertEqual(rows[0]['result']['serverInfo']['name'],'urace');self.assertEqual(len(rows[1]['result']['tools']),5);self.assertEqual(rows[2]['result']['resources'][0]['uri'],'urace://session/capabilities')
 def test_uninitialized_and_unknown_methods_are_protocol_errors(self):
  s,out=self.server();self.request(s,1,'tools/list');self.initialize(s);self.request(s,3,'not-a-method');self.assertIn('error',json.loads(out.getvalue().splitlines()[0]));self.assertEqual(json.loads(out.getvalue().splitlines()[-1])['error']['code'],-32601)
 def test_typed_tool_schemas_and_operation_results(self):
  s,out=self.server();self.initialize(s);result=s.execute_tool({'name':'urace_operations','arguments':{'command':'goal list'}},2);self.assertFalse(result['isError']);self.assertEqual(result['structuredContent']['command'],'goal list')
  with self.assertRaises(ValueError):s.execute_tool({'name':'urace_operations','arguments':{'offset':True}},3)
 def test_capability_denial_is_a_tool_error(self):
  s,out=self.server();self.initialize(s);r=s.execute_tool({'name':'urace_call','arguments':{'command':'resume'}},2);self.assertTrue(r['isError']);self.assertIn('not delegated',r['structuredContent']['error'])
 def test_mcp_call_uses_real_job_and_structured_result(self):
  s,out=self.server();self.initialize(s);r=s.execute_tool({'name':'urace_call','arguments':{'command':'help','request_id':'test'}},2);self.assertFalse(r['isError']);self.assertEqual(r['structuredContent']['status'],'COMPLETED')
 def test_cancellation_notification_reaches_running_request(self):
  s,out=self.server();self.initialize(s);s.jobs.command_factory=lambda argv:[sys.executable,'-c','import time;time.sleep(20)'];self.request(s,9,'tools/call',{'name':'urace_call','arguments':{'command':'help'}})
  for _ in range(100):
   if s.active.get(9):break
   time.sleep(.01)
  s.receive({'jsonrpc':'2.0','method':'notifications/cancelled','params':{'requestId':9}});s.pool.shutdown(wait=True);rows=[json.loads(v) for v in out.getvalue().splitlines()];self.assertEqual(rows[-1]['result']['structuredContent']['status'],'CANCELLED')
 def test_bad_json_recovers_and_notifications_emit_no_response(self):
  s=self.policy();output=io.StringIO()
  with patch('urace.mcp_server.load_policy',return_value=s):self.assertEqual(serve(self.parser,input_stream=io.StringIO('bad\n{"jsonrpc":"2.0","method":"notifications/cancelled"}\n'),output_stream=output),0)
  self.assertEqual(len(output.getvalue().splitlines()),1);self.assertEqual(json.loads(output.getvalue())['error']['code'],-32700)

class CorrelationAndApiTests(Fixture):
 def test_bounded_api_capture_does_not_grow_without_limit(self):
  r=api_interface.execute(self.parser,lambda args:print('x'*10000),command='commands',max_output_bytes=1024);self.assertEqual(r['status'],'error');self.assertIn('allowance',r['error'])
 def test_correlation_is_metadata_and_never_authority(self):
  with patch.dict(os.environ,{'URACE_BRIDGE_JOB':'job','URACE_BRIDGE_ROOT_REQUEST':'request','URACE_BRIDGE_PROJECT':'p','URACE_BRIDGE_EXECUTOR':'actor'}):
   d=_common.integration_context();self.assertEqual(d['job_id'],'job');self.assertNotIn('authority',d)
 def test_serve_is_available_through_existing_api_root(self):
  p=self.parser.parse_args(['api','serve','--transport','stdio','--policy','owner.json']);self.assertEqual(p.action,'serve');self.assertEqual(p.policy,'owner.json')

 def test_api_format_and_json_aliases_keep_their_own_types(self):
  a=api_interface.build_argv(self.parser,'help',{'format':'json'});self.assertIn('--format',a);self.assertIn('json',a);b=api_interface.build_argv(self.parser,'help',{'json':True});self.assertIn('--json',b)

 def test_worker_rechecks_deadline_before_dispatch(self):
  from urace.integration_bridge import worker
  with patch.object(_common,'load_config',return_value={'resource_product_id':'p'}),patch.dict(os.environ,{'URACE_BRIDGE_PROJECT':'p','URACE_BRIDGE_DEADLINE':'1'}),patch.object(api_interface,'execute',side_effect=AssertionError('Expired work must not dispatch')):
   with self.assertRaisesRegex(BridgeError,'deadline'):worker(['help'])
 def test_worker_rechecks_pause_before_mutating_dispatch(self):
  from urace.integration_bridge import worker
  with patch.object(_common,'load_config',return_value={'resource_product_id':'p'}),patch.dict(os.environ,{'URACE_BRIDGE_PROJECT':'p','URACE_BRIDGE_DEADLINE':str(time.time()+60)}),patch('urace.integration_bridge.paused',return_value=True),patch.object(api_interface,'execute',side_effect=AssertionError('Paused work must not dispatch')):
   with self.assertRaisesRegex(BridgeError,'paused'):worker(['auto','--cycles','1'])

 def test_contextual_help_covers_positional_command_actions(self):
  for path in [['api','serve'],['update','apply'],['goal','list'],['product','work','status'],['derive']]:
   with contextlib.redirect_stdout(io.StringIO()) as out:
    self.assertEqual(cli.main(['--json','help',*path]),0)
   self.assertEqual(json.loads(out.getvalue())['command'],' '.join(path))

class StdioIntegrationTests(unittest.TestCase):
 def test_real_stdio_server_shared_api_and_pause_boundary(self):
  import select,signal
  p=subprocess.Popen([sys.executable,'-m','urace','api','serve','--transport','stdio'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
  def send(value):p.stdin.write(json.dumps(value)+'\n');p.stdin.flush()
  def read():
   self.assertTrue(select.select([p.stdout],[],[],10)[0],'MCP response timed out');line=p.stdout.readline();self.assertTrue(line,'Server ended');return json.loads(line)
  try:
   send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}});self.assertEqual(read()['result']['serverInfo']['name'],'urace');send({'jsonrpc':'2.0','method':'notifications/initialized'});send({'jsonrpc':'2.0','id':2,'method':'tools/list'});self.assertEqual(len(read()['result']['tools']),5);send({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'urace_call','arguments':{'command':'help','params':{'operation':['api','serve']},'request_id':'stdio-integration'}}});result=read()['result'];self.assertFalse(result['isError'],result);self.assertEqual(result['structuredContent']['status'],'COMPLETED');self.assertEqual(result['structuredContent']['result']['output']['command'],'api serve');send({'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'urace_call','arguments':{'command':'resume','request_id':'forbidden'}}});self.assertTrue(read()['result']['isError']);p.stdin.close();self.assertEqual(p.wait(timeout=10),0)
  finally:
   if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
   for stream in (p.stdin,p.stdout,p.stderr):
    if not stream.closed:stream.close()

 def test_real_stdio_authorized_write_reaches_the_shared_inbox(self):
  import select,signal
  original=_common.CONFIG_PATH.read_bytes();p=None
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cfg=json.loads(original);cfg.pop('active_product',None);cfg['state_path']=str(root/'state/state.json');cfg['resource_product_id']='mcp-write-fixture';cfg['execution_workflow']='core';cfg['executor']['enabled']=False
   _common.atomic_write_json(Path(cfg['state_path']),cli.initial_state(cfg));policy=root/'policy.json';policy.write_text(json.dumps({'project_id':'mcp-write-fixture','executor_id':'fixture','read_only':False,'commands':['add goal']}))
   def send(value):p.stdin.write(json.dumps(value)+'\n');p.stdin.flush()
   def read():
    self.assertTrue(select.select([p.stdout],[],[],10)[0],'MCP response timed out');return json.loads(p.stdout.readline())
   try:
    _common.atomic_write_json(_common.CONFIG_PATH,cfg);environment=os.environ.copy();environment.pop('URACE_ACTIVE_PRODUCT',None)
    p=subprocess.Popen([sys.executable,'-m','urace','api','serve','--policy',str(policy)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment,start_new_session=True)
    send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}});self.assertIn('result',read());send({'jsonrpc':'2.0','method':'notifications/initialized'})
    request={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'urace_call','arguments':{'command':'add goal','params':{'title':'Verify delegated queueing','success_measure':'One attributable input receipt','reason':'Isolated MCP test'},'request_id':'once'}}};send(request);response=read()['result'];self.assertFalse(response['isError'],response);job=response['structuredContent'];self.assertEqual(job['status'],'COMPLETED');self.assertEqual(job['result']['output']['status'],'queued');records=list(_common.input_directory(cfg).glob('*.json'));self.assertEqual(len(records),1);record=json.loads(records[0].read_text());self.assertEqual(record['kind'],'goal')
    request['id']=3;send(request);again=read()['result']['structuredContent'];self.assertEqual(again['job_id'],job['job_id']);self.assertEqual(len(list(_common.input_directory(cfg).glob('*.json'))),1);p.stdin.close();self.assertEqual(p.wait(timeout=10),0)
   finally:
    if p is not None:
     if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
     for stream in (p.stdin,p.stdout,p.stderr):
      if not stream.closed:stream.close()
    _common.atomic_write_text(_common.CONFIG_PATH,original.decode())

class DurableWaitTests(Fixture):
 def test_wait_from_second_session_waits_same_attempt_without_replay(self):
  code='import json,time;time.sleep(.3);print(json.dumps({"output":{"done":True}}))';a=self.jobs(code=code);b=self.jobs();row=a.submit('help',{},'same-attempt');self.assertEqual(b.submit('help',{},'same-attempt')['job_id'],row['job_id']);t=time.monotonic();r=b.wait(row['job_id']);self.assertEqual(r['status'],'COMPLETED');self.assertTrue(r['result']['output']['done']);self.assertGreater(time.monotonic()-t,.1)

class TransportOwnerTests(Fixture):
 def test_launcher_loss_runs_child_transport_cleanup(self):
  import signal
  marker=self.root/'cleanup';ready=self.root/'ready';child_code="import time;from pathlib import Path;from urace.integration_bridge import owner_lifetime\ntry:\n with owner_lifetime():\n  Path("+repr(str(ready))+").write_text('ready');time.sleep(30)\nexcept KeyboardInterrupt:pass\nfinally:Path("+repr(str(marker))+").write_text('closed')"
  parent_code="import subprocess,sys,os,time;env=os.environ.copy();env['URACE_LAUNCHER_CHILD']='1';p=subprocess.Popen([sys.executable,'-c',"+repr(child_code)+"],env=env);print(p.pid,flush=True);p.wait()";parent=subprocess.Popen([sys.executable,'-c',parent_code],stdout=subprocess.PIPE,text=True);child=int(parent.stdout.readline())
  try:
   deadline=time.monotonic()+10
   while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
   self.assertTrue(ready.exists());parent.terminate();parent.wait(timeout=5);deadline=time.monotonic()+10
   while not marker.exists() and time.monotonic()<deadline:time.sleep(.02)
   self.assertEqual(marker.read_text(),'closed')
  finally:
   if parent.poll() is None:parent.kill();parent.wait()
   parent.stdout.close()
   from urace.integration_bridge import pid_ticks
   if pid_ticks(child) is not None:os.kill(child,signal.SIGKILL)
