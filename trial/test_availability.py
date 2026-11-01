import unittest
from availability import should_wake
class Recovery(unittest.TestCase):
 def test_recovery_wakes(self):self.assertTrue(should_wake({'codex':{'ordinaryUsageAllowed':False}},{'codex':{'ordinaryUsageAllowed':True}}))
 def test_unknown_does_not_wake(self):self.assertFalse(should_wake({'codex':{'ordinaryUsageAllowed':False}},{'codex':{'ordinaryUsageAllowed':None}}))
 def test_still_available_does_not_wake(self):self.assertFalse(should_wake({'codex':{'ordinaryUsageAllowed':True}},{'codex':{'ordinaryUsageAllowed':True}}))
 def test_first_snapshot_does_not_wake(self):self.assertFalse(should_wake({},{'codex':{'ordinaryUsageAllowed':True}}))
 def test_unknown_gap_retains_recovery(self):self.assertTrue(should_wake({'last_known_codex_usage_allowed':False,'codex':{'ordinaryUsageAllowed':None}},{'codex':{'ordinaryUsageAllowed':True}}))
if __name__=='__main__':unittest.main()
