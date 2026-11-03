import unittest,tempfile,json
from pathlib import Path
from urace import authority,validation,cli,_common,command_surface
class UserBenefitCoreTests(unittest.TestCase):
 def test_local_code_requires_explicit_implementation_delegation(self):
  goal={'scope':'implementation','title':'Implement requested local workflow'}
  self.assertEqual(authority.resolve(goal,{'authority':{'delegated':[]}}, {})['outcome'],authority.REQUIRES_AUTHORITATIVE_DECISION)
  self.assertEqual(authority.resolve(goal,{'authority':{'delegated':['local implementation changes']}}, {})['outcome'],authority.AUTONOMOUSLY_AUTHORIZED)
 def test_implementation_files_are_validated_under_their_own_scope(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'logic.py').write_text('def compute(x): return x');cfg={'executor':{'allowed_files_by_scope':{'implementation':['logic.py']}}};result=validation.validate_operation(root,{'scope':'implementation','changed_files':['logic.py'],'authority_basis':'owner'}, {'quality':0},{'quality':1},cfg,{})
   self.assertEqual(result['verdict'],validation.VALIDATED)
 def test_recovery_uses_declared_product_root(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'logic.py').write_text('next');cfg={'state_path':str(root/'state/state.json')};_common.atomic_write_json(Path(cfg['state_path']),{'state_version':0,'checkpoints':[]});_common.atomic_write_json(_common.transaction_path(cfg),{'id':'tx','recovery_protocol':'atomic-v2','before':{'logic.py':'base'},'after':{'logic.py':'next'}});self.assertEqual(cli.reconcile_transaction(cfg,root=root),'ROLLED_BACK');self.assertEqual((root/'logic.py').read_text(),'base')
 def test_work_status_and_benefit_status_are_read_only(self):
  self.assertTrue(command_surface.read_only(['product','work','status']));self.assertTrue(command_surface.read_only(['trial','study','benefit','status']));self.assertFalse(command_surface.read_only(['product','work','run']))

 def test_recovery_includes_new_modules_without_expanding_executor_authority(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'urace/runtime/urace/new_component.py';p.parent.mkdir(parents=True);p.write_text('x=1');config={'executor':{'allowed_files_by_scope':{'runtime':[]}}}
   with patch.object(cli,'ROOT',root):self.assertIn('urace/runtime/urace/new_component.py',cli.runtime_files(config))
   self.assertTrue(validation.candidate_file_errors(root,'runtime',['urace/runtime/urace/new_component.py'],config))
