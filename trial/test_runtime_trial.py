"""Legacy numeric claims are explicitly rejected; full transactions covered in test_runtime_cycle."""
import json,tempfile,unittest
from pathlib import Path
import runtime_trial as rt
class LegacyDeploymentBoundaryTests(unittest.TestCase):
 def test_numeric_score_never_creates_a_deployment(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d)/'trial';b.mkdir();p=b.parent/'runtime/urace';p.mkdir(parents=True);(p/'helper.py').write_text('# owner source');(b/'executable-benchmark-latest.json').write_text(json.dumps({'scorecard':{'overall_quality_score':60}}));result=rt.run(b,{}, {'rationale':'unmeasured proposal'},100);self.assertEqual(result['status'],'REJECTED');self.assertEqual(rt.deployment_log(b),[]);self.assertEqual((p/'helper.py').read_text(),'# owner source')
 def test_automatic_deletion_and_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d)/'trial';b.mkdir();p=b.parent/'runtime/urace';p.mkdir(parents=True);(p/'helper.py').write_text('# owner source')
   with self.assertRaises(rt.RuntimeDeploymentError):rt.validate_diff(b,{'files_removed':['../owner.txt']})
   with self.assertRaises(rt.RuntimeDeploymentError):rt._apply_diff(b.parent/'runtime','--- a/../owner.txt\n+++ b/../owner.txt\n@@ -1 +1 @@\n-old\n+new\n')
