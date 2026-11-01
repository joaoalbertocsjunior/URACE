"""Core integration scenarios; native study evidence is recorded separately."""
import copy,hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import _common,cli,resource_usage,auto_goals,authority,validation,data_transport,command_surface,trial_cli,api_interface

class ValueWorkflowIntegration(unittest.TestCase):
 def test_declared_goal_authority_validation_and_reload(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);config={'state_path':str(root/'state.json'),'authority':{'delegated':['objectives','local implementation changes']},'project':{'id':'p','intent':'Provide validated product guidance','requirements':[{'id':'guide','title':'Guide','success_measure':'Independent check passes'}]},'executor':{'allowed_files_by_scope':{'documentation':['guide.md']}}};state={'state_version':0}
   goal=auto_goals.select(config,state);decision=authority.resolve(goal,config,state);self.assertEqual(decision['outcome'],authority.AUTONOMOUSLY_AUTHORIZED)
   (root/'guide.md').write_text('Validated guidance');op={'scope':'documentation','changed_files':['guide.md'],'authority_basis':decision['basis']};check=validation.validate_operation(root,op,{'quality':0},{'quality':1},config,state);self.assertEqual(check['verdict'],validation.VALIDATED)
   goal['status']='completed';_common.save_state(config,state);saved=_common.load_state(config);self.assertEqual(saved['objectives'][0]['status'],'completed')
 def test_resource_projection_avoids_cold_state_decode_and_corruption_falls_back(self):
  import sys
  trial=Path(__file__).resolve().parents[2]/'trial';sys.path.insert(0,str(trial));import core_resources
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);cfg={'state_path':str(root/'state.json')};state={'state_version':0,'intent':'private','executor_state':{'executor_calls':[{'id':'real','usage':{'total_tokens':7}}]}}
   _common.save_state(cfg,state)
   with patch.object(core_resources,'_resource_projection',side_effect=AssertionError('cold decode')):self.assertEqual(core_resources.resource_state(root/'state.json')['executor_state']['executor_calls'][0]['id'],'real')
   p=root/'resource-projection.json';value=json.loads(p.read_text());value['executor_calls'][0]['id']='corrupt';p.write_text(json.dumps(value));self.assertEqual(core_resources.resource_state(root/'state.json')['executor_state']['executor_calls'][0]['id'],'real')
 def test_projection_is_stale_after_atomic_state_replacement(self):
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'trial'));import core_resources
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);cfg={'state_path':str(root/'state.json')};s={'state_version':0,'executor_state':{'executor_calls':[]}};_common.save_state(cfg,s)
   s['executor_state']['executor_calls']=[{'id':'new'}];_common.atomic_write_json(root/'state.json',s);self.assertEqual(core_resources.resource_state(root/'state.json')['executor_state']['executor_calls'][0]['id'],'new')
 def recover(self,accepted,external=False,escape=False):
  with tempfile.TemporaryDirectory() as directory:
   parent=Path(directory);root=parent/'product';root.mkdir();config={'state_path':str(root/'state/state.json')};s={'state_version':0,'checkpoints':[{'transaction':'t'}] if accepted else []};_common.atomic_write_json(Path(config['state_path']),s)
   (root/'guide.md').write_text('owner' if external else 'candidate');relative='../outside' if escape else 'guide.md';outside=parent/'outside';outside.write_text('keep')
   _common.atomic_write_json(_common.transaction_path(config),{'id':'t','phase':'APPLYING','applied':[relative],'recovery_protocol':'atomic-v2','before':{relative:'base'},'after':{relative:'candidate'}})
   with patch.object(cli,'ROOT',root):
    if external or escape:
     with self.assertRaises(RuntimeError):cli.reconcile_transaction(config)
     self.assertEqual((root/'guide.md').read_text(),'owner' if external else 'candidate');self.assertEqual(outside.read_text(),'keep');self.assertTrue(_common.transaction_path(config).exists())
    else:self.assertEqual(cli.reconcile_transaction(config),'ROLLED_FORWARD' if accepted else 'ROLLED_BACK');self.assertEqual((root/'guide.md').read_text(),'candidate' if accepted else 'base')
 def test_interrupted_transaction_rolls_back(self):self.recover(False)
 def test_accepted_transaction_rolls_forward(self):self.recover(True)
 def test_recovery_preserves_owner_edits(self):self.recover(False,external=True)
 def test_recovery_cannot_escape_product_root(self):self.recover(False,escape=True)
 def test_study_cli_and_api_share_discoverable_options(self):
  import argparse
  p=argparse.ArgumentParser();p.add_subparsers(dest='command').add_parser('trial',parents=[trial_cli.build_parser()],add_help=False)
  argv=api_interface.build_argv(p,'trial study configure',{'enabled':'true','repetitions':3,'efforts':['low','medium','high'],'json':True});self.assertEqual(p.parse_args(argv).efforts,['low','medium','high']);self.assertTrue(command_surface.read_only(['trial','study','status']));self.assertFalse(command_surface.read_only(['trial','study','run']))
