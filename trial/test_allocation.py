import copy,unittest
from datetime import datetime,timezone
from allocation import decide
class Allocation(unittest.TestCase):
 def setUp(self):self.now=1000000;self.snapshot={'at':datetime.fromtimestamp(self.now,timezone.utc).isoformat(),'codex':{'ordinaryUsageAllowed':True,'rateLimits':{'primary':{'usedPercent':30},'secondary':{'usedPercent':40}}}}
 def test_available_headroom(self):self.assertTrue(decide(self.snapshot,self.now)['eligible'])
 def test_primary_reserve(self):self.snapshot['codex']['rateLimits']['primary']['usedPercent']=97;self.assertFalse(decide(self.snapshot,self.now)['eligible'])
 def test_weekly_reserve(self):self.snapshot['codex']['rateLimits']['secondary']['usedPercent']=97;self.assertFalse(decide(self.snapshot,self.now)['eligible'])
 def test_unavailable(self):self.snapshot['codex']['ordinaryUsageAllowed']=False;self.assertFalse(decide(self.snapshot,self.now)['eligible'])
 def test_stale(self):self.assertFalse(decide(self.snapshot,self.now+7*3600)['eligible'])
 def test_unknown(self):del self.snapshot['codex']['rateLimits']['primary'];self.assertFalse(decide(self.snapshot,self.now)['eligible'])
 def test_missing(self):self.assertFalse(decide({},self.now)['eligible'])
if __name__=='__main__':unittest.main()

class FreshCohort(unittest.TestCase):
 def test_build_before_first_native_reservation(self):
  import contextlib,io,json,tempfile
  from pathlib import Path
  from unittest.mock import patch
  import allocation
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);ops=root/'operations';ops.mkdir();trial=root/'trial';trial.mkdir();(trial/'receipts').mkdir()
   (ops/'comparison-current.json').write_text(json.dumps({'root':str(trial)}));(ops/'availability-latest.json').write_text('{}');(ops/'resource-policy.json').write_text('{}')
   with patch.object(allocation,'ROOT',ops),contextlib.redirect_stdout(io.StringIO()):allocation.build()
   result=json.loads((ops/'allocation-latest.json').read_text());self.assertEqual(result['observed_productive_results']['codex']['attempts'],0);self.assertIsNone(result['single_case_comparison']);self.assertIsNone(result['observed_productive_results']['claude']['tokens_per_accepted_result'])
