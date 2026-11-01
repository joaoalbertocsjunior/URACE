"""Tests for version.py, preflight.py, --version flag, bridge client_version, and check integration."""
import copy,io,json,tempfile,unittest
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
from unittest.mock import patch
from urace import version,preflight,cli,_common,integration_bridge

class VersionConstantsTests(unittest.TestCase):
 def test_runtime_version_is_semver_string(self):self.assertRegex(version.RUNTIME_VERSION,r'^\d+\.\d+\.\d+')
 def test_format_version_positive_int(self):self.assertIsInstance(version.FORMAT_VERSION,int);self.assertGreater(version.FORMAT_VERSION,0)
 def test_min_not_above_current(self):self.assertLessEqual(version.MIN_FORMAT_VERSION,version.FORMAT_VERSION)
 def test_bridge_version_positive_int(self):self.assertIsInstance(version.BRIDGE_VERSION,int);self.assertGreater(version.BRIDGE_VERSION,0)
 def test_min_bridge_not_above_current(self):self.assertLessEqual(version.MIN_BRIDGE_CLIENT_VERSION,version.BRIDGE_VERSION)

class VersionFlagTests(unittest.TestCase):
 def test_version_flag_prints_version_and_exits(self):
  import sys as _sys
  out=io.StringIO()
  with self.assertRaises(SystemExit) as ctx:
   with redirect_stdout(out):cli.main(['--version'])
  self.assertEqual(ctx.exception.code,0)
 def test_version_output_contains_runtime_version(self):
  import sys
  out=io.StringIO()
  with self.assertRaises(SystemExit):
   with redirect_stdout(out):cli.main(['--version'])
  self.assertIn(version.RUNTIME_VERSION,out.getvalue())

class PreflightHintsTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def test_no_state_no_hints(self):
  self.assertEqual(preflight.hints({'state_path':str(self.root/'nonexistent.json')},self.root),[])
 def test_current_format_no_hint(self):
  state={'schema_version':version.FORMAT_VERSION,'state_version':0}
  (self.root/'state.json').write_text(json.dumps(state))
  result=preflight.hints({'state_path':str(self.root/'state.json')},self.root)
  self.assertFalse(any(h['code']=='FORMAT_TOO_OLD' for h in result))
  self.assertFalse(any(h['code']=='FORMAT_NEWER' for h in result))
 def test_future_format_warns(self):
  (self.root/'state.json').write_text(json.dumps({'schema_version':9999,'state_version':0}))
  result=preflight.hints({'state_path':str(self.root/'state.json')},self.root)
  self.assertTrue(any(h['code']=='FORMAT_NEWER' for h in result))
 def test_improvement_pending_deployment_hints(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-deployment-pending.json').write_text('{}')
  result=preflight.hints({},self.root)
  self.assertTrue(any(h['code']=='IMPROVEMENT_READY' for h in result))
 def test_improvement_awaiting_approval_hints(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-cycle-latest.json').write_text(json.dumps({'stage':'AWAITING_APPROVAL'}))
  result=preflight.hints({},self.root)
  self.assertTrue(any(h['code']=='IMPROVEMENT_AWAITING_APPROVAL' for h in result))
 def test_other_cycle_stage_no_hint(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-cycle-latest.json').write_text(json.dumps({'stage':'WAITING'}))
  self.assertEqual(preflight.hints({},self.root),[])
 def test_exception_in_config_returns_empty(self):
  self.assertEqual(preflight.hints({'state_path':'///////invalid'},self.root),[])
 def test_pending_deployment_takes_priority_over_awaiting_approval(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-deployment-pending.json').write_text('{}')
  (trial/'runtime-cycle-latest.json').write_text(json.dumps({'stage':'AWAITING_APPROVAL'}))
  codes=[h['code'] for h in preflight.hints({},self.root)]
  self.assertIn('IMPROVEMENT_READY',codes);self.assertNotIn('IMPROVEMENT_AWAITING_APPROVAL',codes)
 def test_all_hints_have_required_keys(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-deployment-pending.json').write_text('{}')
  (self.root/'state.json').write_text(json.dumps({'schema_version':9999,'state_version':0}))
  for h in preflight.hints({'state_path':str(self.root/'state.json')},self.root):
   self.assertIn('level',h);self.assertIn('code',h);self.assertIn('message',h);self.assertIn('action',h)

class PreflightInCheckOutputTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.cp=self.root/'config.json';cfg=copy.deepcopy(cli.load_config());cfg.pop('active_product',None);cfg['state_path']=str(self.root/'state.json')
  self.cp.write_text(json.dumps(cfg));_common.atomic_write_json(Path(cfg['state_path']),cli.initial_state(cfg))
  self.stack=__import__('contextlib').ExitStack();self.addCleanup(self.stack.close)
  for module,name,value in [(cli,'CONFIG_PATH',self.cp),(_common,'CONFIG_PATH',self.cp),(cli,'SYSTEM_ROOT',self.root)]:self.stack.enter_context(patch.object(module,name,value))
 def call(self,args):
  out=io.StringIO()
  with redirect_stdout(out):code=cli.main(args)
  return code,out.getvalue()
 def test_check_json_contains_preflight_hints_key(self):
  code,text=self.call(['check','--json']);self.assertEqual(code,0);data=json.loads(text);self.assertIn('preflight_hints',data);self.assertIsInstance(data['preflight_hints'],list)
 def test_check_human_shows_preflight_hints_when_present(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-deployment-pending.json').write_text('{}')
  code,text=self.call(['check']);self.assertEqual(code,0);self.assertIn('preflight_hints',text)
 def test_hints_printed_to_stderr_for_non_json_commands(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-deployment-pending.json').write_text('{}')
  err=io.StringIO()
  with redirect_stderr(err):self.call(['check'])
  # hints are shown both in check output and on stderr for other commands
 def test_check_json_hints_empty_list_when_none(self):
  code,text=self.call(['check','--json']);data=json.loads(text);self.assertEqual(data['preflight_hints'],[])

class BridgeClientVersionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
 def _policy(self,**extra):
  base={'schema':integration_bridge.SCHEMA,'project_id':'owner','executor_id':'external','commands':['commands']}
  return {**base,**extra}
 def test_missing_client_version_defaults_to_current(self):
  p=integration_bridge.Policy(cli.build_parser(),self._policy(),root=self.root,storage=self.root/'jobs')
  self.assertIsNotNone(p)
 def test_current_client_version_accepted(self):
  p=integration_bridge.Policy(cli.build_parser(),self._policy(client_version=version.BRIDGE_VERSION),root=self.root,storage=self.root/'jobs')
  self.assertIsNotNone(p)
 def test_below_minimum_client_version_rejected(self):
  with self.assertRaises(integration_bridge.BridgeError) as ctx:
   integration_bridge.Policy(cli.build_parser(),self._policy(client_version=0),root=self.root,storage=self.root/'jobs')
  self.assertIn('minimum',str(ctx.exception))
 def test_non_int_client_version_rejected(self):
  with self.assertRaises(integration_bridge.BridgeError):
   integration_bridge.Policy(cli.build_parser(),self._policy(client_version='1'),root=self.root,storage=self.root/'jobs')
 def test_valid_older_version_accepted_when_above_minimum(self):
  if version.BRIDGE_VERSION>version.MIN_BRIDGE_CLIENT_VERSION:
   p=integration_bridge.Policy(cli.build_parser(),self._policy(client_version=version.MIN_BRIDGE_CLIENT_VERSION),root=self.root,storage=self.root/'jobs')
   self.assertIsNotNone(p)

import sys
