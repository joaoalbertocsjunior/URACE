import json,unittest
from pathlib import Path
from unittest.mock import patch
from urace import executor
class NativeUsageErrorTests(unittest.TestCase):
    def envelope(self):
        return {'is_error':True,'subtype':'success','result':'output token limit','total_cost_usd':.02,'usage':{'input_tokens':2,'output_tokens':3},'modelUsage':{'main':{'inputTokens':2,'cacheCreationInputTokens':10,'cacheReadInputTokens':20,'outputTokens':3},'aux':{'inputTokens':7,'cacheCreationInputTokens':0,'cacheReadInputTokens':0,'outputTokens':1}}}
    def test_zero_exit_error_is_not_accepted(self):
        with patch.object(executor.shutil,'which',return_value='/native'),patch.object(executor,'_run_with_heartbeats',return_value=(0,json.dumps(self.envelope()),'')):
            with self.assertRaises(RuntimeError) as caught:executor._run_claude(Path('/tmp'),{},'task',None,'read-only')
        self.assertEqual(caught.exception.__urace_executor_metadata__['resource_total_tokens'],43)
    def test_nonzero_error_retains_cost(self):
        with patch.object(executor.shutil,'which',return_value='/native'),patch.object(executor,'_run_with_heartbeats',return_value=(1,json.dumps(self.envelope()),'')):
            with self.assertRaises(RuntimeError) as caught:executor._run_claude(Path('/tmp'),{},'task',None,'read-only')
        self.assertEqual(caught.exception.__urace_executor_metadata__['reported_cost_usd'],.02)
