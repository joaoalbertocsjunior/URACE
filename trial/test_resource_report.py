import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import resource_report
class ResourceAttribution(unittest.TestCase):
 def test_completed_unknown_and_inflight_are_distinct_and_reserved(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);ops=root/'ops';ops.mkdir();trial=root/'productive-native-30d-v1';trial.mkdir();rows=[]
   for i in range(3):rows.append({'id':str(i),'kind':'reserved','provider':'codex','token_reservation':50000})
   rows.extend([{'id':'0','kind':'finished','provider':'codex','tokens':25,'wall_seconds':1},{'id':'1','kind':'finished','provider':'codex','tokens':None,'wall_seconds':2}]);rows.extend([{'id':'c','kind':'reserved','provider':'claude'},{'id':'c','kind':'finished','provider':'claude','tokens':None}]);(trial/'ledger.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
   with patch.object(resource_report,'ROOT',ops),contextlib.redirect_stdout(io.StringIO()):resource_report.main()
   d=json.loads((ops/'resources-latest.json').read_text());c=d['providers']['codex'];self.assertEqual(c['known_tokens'],25);self.assertEqual(c['inflight_calls'],1);self.assertEqual(c['completed_missing_usage'],1);self.assertEqual(c['reserved_tokens_for_unmeasured_usage'],100000);self.assertIsNone(c['actual_subscription_credit_charge']);self.assertIsNone(d['providers']['claude']['api_equivalent_usd'])
