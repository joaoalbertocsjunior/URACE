import contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli,_common
class ReadyBootstrap(unittest.TestCase):
 def test_ready_does_not_invent_aggregate_call_caps(self):
  with tempfile.TemporaryDirectory() as root:
   config=copy.deepcopy(cli.load_config());config.pop('active_product',None);config['state_path']=str(Path(root)/'state.json')
   for key in ('max_executor_calls_per_24h','max_executor_calls_per_30d'):config['executor'].pop(key,None)
   config_path=Path(root)/'config.json';config_path.write_text(json.dumps(config))
   with patch.object(cli,'CONFIG_PATH',config_path),patch.object(_common,'CONFIG_PATH',config_path),patch.object(cli,'write_stable_snapshot'),patch.object(cli,'write_runtime_snapshot'),patch('shutil.which',side_effect=lambda name:'/fixture/'+name if name in ('codex','claude') else None),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(cli.main(['init','--ready']),0)
   accepted=json.loads(config_path.read_text())
   self.assertIsNone(accepted['executor']['max_executor_calls_per_24h']);self.assertIsNone(accepted['executor']['max_executor_calls_per_30d'])
 def test_ready_runs_real_onboarding_and_preserves_authority(self):
  with tempfile.TemporaryDirectory() as root:
   config=copy.deepcopy(cli.load_config());config.pop('active_product',None);config['state_path']=str(Path(root)/'state.json');config['executor']['enabled']=False;config_path=Path(root)/'config.json';config_path.write_text(json.dumps(config));before=copy.deepcopy(config['authority'])
   with patch.object(cli,'CONFIG_PATH',config_path),patch.object(_common,'CONFIG_PATH',config_path),patch.object(cli,'write_stable_snapshot'),patch.object(cli,'write_runtime_snapshot'),patch('shutil.which',side_effect=lambda name:'/fixture/'+name if name in ('codex','claude') else None),contextlib.redirect_stdout(io.StringIO()):
    self.assertEqual(cli.main(['init','--ready']),0)
   accepted=json.loads(config_path.read_text());state=json.loads(Path(config['state_path']).read_text());self.assertEqual(accepted['authority'],before);self.assertTrue(accepted['executor']['enabled']);self.assertTrue(state['onboard_records']);self.assertEqual(state['onboard_records'][-1]['confirmed_by'],'operator');self.assertIsNone(cli._run_onboard_gate(accepted,state));self.assertEqual(accepted['auto_goals'],config['auto_goals'])
 def test_init_ready_does_not_invent_executor_credentials(self):
  with tempfile.TemporaryDirectory() as root:
   config=copy.deepcopy(cli.load_config());config.pop('active_product',None);config['state_path']=str(Path(root)/'state.json');config['executor']['enabled']=False;config_path=Path(root)/'config.json';config_path.write_text(json.dumps(config))
   with patch.object(cli,'CONFIG_PATH',config_path),patch.object(_common,'CONFIG_PATH',config_path),patch.object(cli,'write_stable_snapshot'),patch.object(cli,'write_runtime_snapshot'),patch('shutil.which',return_value=None),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(cli.main(['init','--ready']),2)
   self.assertFalse(json.loads(config_path.read_text())['executor']['enabled']);self.assertEqual(json.loads(Path(config['state_path']).read_text())['onboard_records'],[])
