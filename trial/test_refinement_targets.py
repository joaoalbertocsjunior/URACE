import unittest
from refinement_targets import report
class TargetsTests(unittest.TestCase):
 def test_no_self_awarded_advantage_or_native_work(self):
  value=report();self.assertEqual(value['native_inference_calls'],0);self.assertFalse(value['self_awarded_scores']);self.assertEqual(len(value['targets']),7)
  self.assertTrue(all(t['status']=='EVIDENCE_REQUIRED' and t['evidence_required'] and t['claim_limit'] for t in value['targets']))
  self.assertEqual(value['priority_order'],['stable_qualified_release','sufficient_compatible_matched_evidence','independent_retained_user_benefit'])
