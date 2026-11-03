import unittest
from urace import executor
class UsageTruthContract(unittest.TestCase):
 def test_non_mapping_models_remain_unknown(self):
  for malformed in ('unrecognized',None,3,False,[],['tokens']):
   with self.subTest(value=repr(malformed)):
    usage=executor._claude_usage_metadata({'usage':{'input_tokens':3,'output_tokens':2},'modelUsage':{'model':malformed}});self.assertNotIn('resource_total_tokens',usage);self.assertEqual(usage['input_tokens'],3);self.assertEqual(usage['output_tokens'],2)
 def test_genuine_measured_zero_is_preserved(self):
  fields={key:0 for key in ('inputTokens','cacheCreationInputTokens','cacheReadInputTokens','outputTokens')};self.assertEqual(executor._claude_usage_metadata({'modelUsage':{'model':fields}})['resource_total_tokens'],0)
 def test_complete_usage_is_summed(self):
  fields={'inputTokens':10,'cacheCreationInputTokens':2,'cacheReadInputTokens':4,'outputTokens':3};self.assertEqual(executor._claude_usage_metadata({'modelUsage':{'model':fields}})['resource_total_tokens'],19)
