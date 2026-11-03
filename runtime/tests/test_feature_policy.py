import copy,unittest
from urace.feature_policy import DEFAULT,validate,effective
class FeaturePolicyTests(unittest.TestCase):
 def test_default_has_no_payment_or_copy_prevention_claim(self):
  result=effective(DEFAULT);self.assertEqual(result['effective_access'],'reviewed-direct');self.assertFalse(result['payment_enabled']);self.assertFalse(result['copy_prevention_guaranteed'])
 def test_explicit_timed_release_never_depends_on_purchase(self):
  terms={**DEFAULT,'license_id':'MIT','open_after_unix':200}
  self.assertEqual(effective(terms,199)['effective_access'],'reviewed-direct');self.assertEqual(effective(terms,200)['usage_price_units'],0)
 def test_core_cannot_be_paywalled_and_open_needs_terms(self):
  with self.assertRaises(ValueError):validate({**DEFAULT,'essential':True})
  with self.assertRaises(ValueError):validate({**DEFAULT,'access':'open'})
  self.assertEqual(effective({**DEFAULT,'essential':True,'access':'open','license_id':'MIT'})['usage_price_units'],0)
 def test_nonfinite_and_unknown_terms_rejected(self):
  with self.assertRaises(ValueError):validate({**DEFAULT,'open_after_unix':float('nan')})
  with self.assertRaises(ValueError):validate({**DEFAULT,'exclusive_control':True})
