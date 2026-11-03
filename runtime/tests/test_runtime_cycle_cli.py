"""Shared CLI/API grammar, product scope, transaction and stream-policy tests."""
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
import copy,io,json,tempfile,unittest
from urace import cli,_common,api_interface,command_surface,integration_bridge,runtime_product

class RuntimeCLIAlignmentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.base=self.root/'trial';self.base.mkdir();self.cp=self.root/'config.json';self.cfg=copy.deepcopy(cli.load_config());self.cfg.pop('active_product',None);self.cfg['state_path']=str(self.root/'state.json');self.cfg['runtime_workflow']={'enabled':True};self.cfg['product_registry']=[{'name':'Owner normal product','status':'ACTIVE'}];self.cp.write_text(json.dumps(self.cfg));_common.atomic_write_json(Path(self.cfg['state_path']),cli.initial_state(self.cfg));self.runtime='urace-runtime:'+str(self.root);(self.base/'products.json').write_text(json.dumps({'products':[{'id':self.runtime,'kind':'runtime','name':'Runtime','improvement_enabled':True},{'id':'spec-owner','name':'Specification','improvement_enabled':False},{'id':'urace-work:internal','name':'Internal engineering artifact'}]}));(self.base/'contract.json').write_text(json.dumps({'product_id':'spec-owner'}))
  self.stack=__import__('contextlib').ExitStack();self.addCleanup(self.stack.close)
  self.stack.enter_context(patch.object(__import__('sys'),'path',[str(Path(__file__).resolve().parents[2]/'trial'),*__import__('sys').path]))
  for module,name,value in [(cli,'CONFIG_PATH',self.cp),(_common,'CONFIG_PATH',self.cp),(cli,'SYSTEM_ROOT',self.root)]:self.stack.enter_context(patch.object(module,name,value))
 def call(self,args):
  output=io.StringIO()
  with redirect_stdout(output):code=cli.main(args)
  return code,output.getvalue()
 def test_canonical_watch_views_and_old_flags_match(self):
  for action in ('dashboard','guard','report'):
   code,a=self.call(['watch',action,'--json']);other,b=self.call(['watch','--'+action,'--json']);self.assertEqual(code,0);self.assertEqual(other,0)
   one=json.loads(a);two=json.loads(b);one.pop('checked_at',None);two.pop('checked_at',None);self.assertEqual(one,two)
 def test_unknown_score_not_displayed_as_zero(self):
  code,text=self.call(['watch','dashboard']);self.assertEqual(code,0);self.assertIn('unavailable',text);self.assertNotIn('Progress bar',text)
 def test_runtime_status_alias_uses_the_same_schema(self):
  code,text=self.call(['status','improvements','--json']);self.assertEqual(code,0);self.assertEqual(json.loads(text)['schema'],'runtime-dashboard-v2')
 def test_normal_product_list_remains_normal_registry(self):
  code,text=self.call(['product','list','--json']);self.assertEqual(code,0);self.assertEqual(json.loads(text)[0]['name'],'Owner normal product')
 def test_improvement_products_do_not_flood_with_internal_artifacts(self):
  code,text=self.call(['product','improvements','list','--json']);self.assertEqual(code,0);rows=json.loads(text)['products'];self.assertEqual(len(rows),2);self.assertNotIn('urace-work:internal',[p['id'] for p in rows])
 def test_product_toggle_and_legacy_alias_use_the_same_record(self):
  for args,wanted in [(['product','improvements','disable',self.runtime],False),(['product','enable',self.runtime],True)]:
   code,text=self.call([*args,'--json']);self.assertEqual(code,0);self.assertIs(json.loads(text)['improvement_enabled'],wanted)
 def test_runtime_controls_persist_and_inspection_is_read_only(self):
  raw=self.cp.read_bytes();code,text=self.call(['configuration','runtime-improvement','--json']);self.assertEqual(code,0);self.assertEqual(self.cp.read_bytes(),raw)
  code,text=self.call(['configuration','runtime-improvement','--auto-deploy','false','--interval-seconds','120','--json']);self.assertEqual(code,0);self.assertFalse(json.loads(text)['auto_deploy']);self.assertEqual(json.loads(self.cp.read_text())['runtime_workflow']['interval_seconds'],120)
 def test_typed_api_and_cli_share_dashboard(self):
  result=api_interface.execute(cli.build_parser(),cli.main,command='watch dashboard',params={});self.assertEqual(result['status'],'ok');self.assertEqual(result['output']['schema'],'runtime-dashboard-v2')
 def test_persistent_watch_requires_explicit_stream(self):
  result=api_interface.execute(cli.build_parser(),cli.main,command='watch events',params={'follow':True});self.assertEqual(result['status'],'error');self.assertIn('persistent',result['error'])
 def test_read_only_delegation_cannot_enable_improvement(self):
  parser=cli.build_parser();raw={'schema':integration_bridge.SCHEMA,'project_id':'owner','executor_id':'external','read_only':True,'commands':['watch dashboard','watch guard','product improvements list']};policy=integration_bridge.Policy(parser,raw,root=self.root,storage=self.root/'jobs');self.assertTrue(policy.authorize('watch dashboard',{})[1]);self.assertTrue(policy.authorize('product improvements list',{})[1])
  with self.assertRaises(integration_bridge.BridgeError):integration_bridge.Policy(parser,{**raw,'read_only':False,'commands':['product improvements enable']},root=self.root,storage=self.root/'jobs')
 def test_delegated_follow_is_not_a_second_controller(self):
  raw={'schema':integration_bridge.SCHEMA,'project_id':'owner','executor_id':'external','commands':['watch events']};policy=integration_bridge.Policy(cli.build_parser(),raw,root=self.root,storage=self.root/'jobs')
  with self.assertRaises(integration_bridge.BridgeError):policy.authorize('watch events',{'follow':True})
 def test_canonical_operations_discoverable_without_new_root(self):
  parser=cli.build_parser();catalog=command_surface.operation_parsers(parser)
  for name in ('watch events','watch dashboard','watch guard','watch report','product improvements list','product improvements enable','configuration runtime-improvement','status improvements'):self.assertIn(name,catalog)
  self.assertNotIn('runtime',command_surface.child_parsers(parser))
 def test_guard_and_dashboard_inspection_do_not_write_guard_files(self):
  self.call(['watch','guard','--json']);self.call(['watch','dashboard','--json']);self.assertFalse((self.base/'runtime-regression-status.json').exists());self.assertFalse((self.base/'runtime-cycle-latest.json').exists())
 def test_transaction_defers_mutation_but_allows_observation_and_emergency_disable(self):
  (self.base/'runtime-deployment-transaction.json').write_text(json.dumps({'status':'PREPARED'}))
  self.assertIsNotNone(runtime_product.mutation_blocker(self.root,['goal','add','new']))
  for args in (['watch','dashboard'],['pause'],['product','improvements','disable',self.runtime],['configuration','runtime-improvement','--auto-deploy','false']):self.assertIsNone(runtime_product.mutation_blocker(self.root,args))
  self.assertIsNotNone(runtime_product.mutation_blocker(self.root,['configuration','runtime-improvement','--auto-deploy','true']))

class RecoveryInventoryTests(unittest.TestCase):
 def test_all_core_acceptance_tests_are_recoverable_without_new_execution_authority(self):
  config=cli.load_config();directory=cli.ROOT/'urace/runtime/tests';expected={str(path.relative_to(cli.ROOT)) for path in directory.glob('*.py') if path.is_file() and not path.is_symlink()}
  self.assertTrue(expected);self.assertTrue(expected<=set(cli.runtime_files(config)))
