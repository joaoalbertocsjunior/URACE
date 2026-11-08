import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import decision_assessor as a

class DecisionAssessorTests(unittest.TestCase):
 def test_advisory_schema_cannot_grant_authority(self):
  advice={'expected_benefit_score':None,'explanation':'Insufficient evidence','recommended_action':'Measure receipt conflicts','uncertainty':'Uncalibrated'};self.assertEqual(a.validate_advice(advice),advice)
  with self.assertRaises(ValueError):a.validate_advice({**advice,'status':'APPROVED'})
 def test_disabled_executor_mode_never_reserves_or_calls(self):
  import resource_governor as g,providers
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);base=root/'trial';base.mkdir();config=root/'runtime/urace';config.mkdir(parents=True);(config/'config.json').write_text('{}')
   with patch.object(a,'BASE',base),patch.object(g,'reserve') as reserve,patch.object(providers,'claude') as claude,patch.object(providers,'codex') as codex:r=a.run({'schema':a.SCHEMA,'packet':{'decision_id':'d','product_id':'p'},'executor':'auto'})
   self.assertEqual(r['status'],'DEFERRED');self.assertEqual(r['inference_calls'],0);reserve.assert_not_called();claude.assert_not_called();codex.assert_not_called()
class OrdinaryGuardTests(unittest.TestCase):
 def test_enabled_executor_mode_still_obeys_ordinary_backoff(self):
  import resource_governor as g,providers,controls,spec_trial,source_integrity
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);base=root/'trial';base.mkdir();config=root/'runtime/urace';config.mkdir(parents=True);(config/'config.json').write_text('{"decision_feedback":{"mode":"executor"}}');(base/'harness-manifest.json').write_text('{"trusted.py":"hash"}')
   ctrl={'paused':False,'executor_enabled':True,'auto_goals':True,'executors':{}}
   with patch.object(a,'BASE',base),patch.object(controls,'effective',return_value=ctrl),patch.object(source_integrity,'matches',return_value=True),patch.object(spec_trial,'eligible',return_value=([],{'claude':'capacity backoff'})),patch.object(g,'reserve') as reserve,patch.object(providers,'claude') as call:r=a.run({'schema':a.SCHEMA,'packet':{'decision_id':'d','product_id':'p'},'executor':'auto'})
   self.assertEqual(r['status'],'DEFERRED');self.assertEqual(r['inference_calls'],0);reserve.assert_not_called();call.assert_not_called()
class DecisionConfigurationBoundaryTests(unittest.TestCase):
 def test_feedback_controls_do_not_unfreeze_authority(self):
  from source_integrity import projected
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'config.json';base={'authority':{'delegated':['assessment']},'decision_feedback':{'enabled':True,'mode':'auto'}};path.write_text(json.dumps(base));before=projected(path);base['decision_feedback']['mode']='executor';path.write_text(json.dumps(base));self.assertEqual(before,projected(path));base['authority']['delegated'].append('spend money');path.write_text(json.dumps(base));self.assertNotEqual(before,projected(path))
if __name__=='__main__':unittest.main()
