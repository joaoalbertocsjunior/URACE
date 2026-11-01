from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack,redirect_stdout
import copy,io,json,tempfile,unittest
from urace import cli,_common,product_creation as pc,api_interface,integration_bridge

class ProductCreationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.system=self.root/'urace';self.system.mkdir();self.cfg=copy.deepcopy(cli.load_config());self.cfg['state_path']=str(self.root/'owner-state.json');self.cfg.pop('active_product',None);self.cfg['product_registry']=[];self.path=self.root/'config.json';self.path.write_text(json.dumps(self.cfg));self.stack=ExitStack();self.addCleanup(self.stack.close)
  for module,name,value in ((cli,'CONFIG_PATH',self.path),(_common,'CONFIG_PATH',self.path),(cli,'ROOT',self.root),(_common,'ROOT',self.root),(cli,'SYSTEM_ROOT',self.system),(_common,'SYSTEM_ROOT',self.system)):self.stack.enter_context(patch.object(module,name,value))
 def call(self,args):
  output=io.StringIO()
  with redirect_stdout(output):code=cli.main(args)
  return code,json.loads(output.getvalue())
 def test_no_preexisting_product_or_native_call_required(self):
  with patch.object(cli.intelligent_executor,'run_routed_codex',side_effect=AssertionError('Local bootstrap')):code,result=self.call(['create a new app that tracks my household tasks','--json'])
  self.assertEqual(code,0);self.assertEqual(result['status'],'BOOTSTRAPPED_OR_QUEUED');product=result['sections'][0]['result'];self.assertFalse(product['working_implementation_verified']);self.assertTrue(Path(product['root']).is_dir());entry=json.loads(self.path.read_text())['product_registry'][0];self.assertEqual(Path(product['root'],'INTENT.md').read_text(),'create a new app that tracks my household tasks');self.assertTrue(Path(entry['state_path']).is_file());self.assertTrue(entry['improvement_enabled'])
 def test_structured_create_is_discoverable_and_registered_with_no_existing_artifact(self):
  code,result=self.call(['product','create','A new documentation product for gardeners','--name','Garden','--json']);self.assertEqual(code,0);self.assertEqual(result['name'],'Garden');self.assertEqual(result['native_calls'],0)
 def test_repeat_request_is_idempotent(self):
  args=['create a new app for household tasks','--json'];self.call(args);self.call(args);self.assertEqual(len(json.loads(self.path.read_text())['product_registry']),1)
 def test_ambiguous_or_conditional_creation_does_not_write(self):
  before=self.path.read_bytes();code,result=self.call(['create a new app if my existing product cannot do this','--json']);self.assertEqual(code,2);self.assertEqual(result['actions_taken'],[]);self.assertEqual(self.path.read_bytes(),before);self.assertFalse((self.system/'products').exists())
 def test_questions_and_existing_changes_are_not_new_products(self):
  for text in ('How should I create a new product?','Add a feature to my current app','Do not create a new app'):
   self.assertFalse(pc.explicit_creation(text))
 def test_mixed_existing_first_and_creation_first_targets_are_distinct(self):
  registry=[{'name':'Ledger','status':'ACTIVE'}]
  for text in ('Create a new app for plants. Also add exports to Ledger','Add exports to Ledger and create a new app for plants'):
   result=pc.interpret(text,registry,'Ledger');self.assertEqual(result['status'],'INTERPRETED');self.assertEqual({i['kind'] for i in result['intents']},{'new_product','existing_product_change'});self.assertEqual(next(i['target'] for i in result['intents'] if i['kind']=='existing_product_change'),'Ledger');self.assertEqual(result['raw_text'],text)
 def test_original_intent_tamper_is_rejected_and_legacy_threshold_not_weakened(self):
  result=pc.create(cli,'A short original intent','One');entry=json.loads(self.path.read_text())['product_registry'][0];self.assertEqual(cli.validate_product(entry['configuration']),[]);Path(result['root'],'INTENT.md').write_text('changed')
  self.assertTrue(any('intent' in e.lower() for e in cli.validate_product(entry['configuration'])))
 def test_isolated_product_configuration_does_not_overwrite_owner_fields(self):
  pc.create(cli,'A short product intent','One');base=json.loads(self.path.read_text());base['active_product']='One';self.path.write_text(json.dumps(base));effective=_common.load_config();self.assertEqual(effective['product'],'One');effective['resources']['effort']='low';_common.save_config(effective);saved=json.loads(self.path.read_text());self.assertEqual(saved['product'],self.cfg['product']);self.assertEqual(saved['intent'],self.cfg['intent']);self.assertEqual(saved['product_registry'][0]['configuration']['resources']['effort'],'low')
 def test_scopes_cannot_escape_into_runtime_or_other_product(self):
  pc.create(cli,'Product intent','One');entry=json.loads(self.path.read_text())['product_registry'][0];entry['configuration']['executor']['allowed_files_by_scope']['implementation']=['URACE.md']
  with self.assertRaises(ValueError):pc.validate_entry(entry,self.root)
 def test_delegated_creation_requires_operator_policy(self):
  raw={'schema':integration_bridge.SCHEMA,'project_id':'p','executor_id':'e','commands':['product create'],'read_only':False}
  with self.assertRaises(integration_bridge.BridgeError):integration_bridge.Policy(cli.build_parser(),raw,root=self.root,storage=self.root/'jobs')
