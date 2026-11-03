import unittest
from datetime import datetime,timezone
from urace import executor
class ActualQuotaWording(unittest.TestCase):
 def test_real_claude_limit_uses_configured_fallback(self):
  start=datetime.now(timezone.utc);error=executor.classify_unavailability("You've hit your limit · resets 4am (America/Sao_Paulo)",{'capacity_fallback_seconds':18900});self.assertIsNotNone(error);self.assertEqual(error.category,'PROVIDER_CAPACITY');seconds=(datetime.fromisoformat(error.retry_at)-start).total_seconds();self.assertGreaterEqual(seconds,18900);self.assertLess(seconds,18905)
 def test_output_limit_is_not_account_quota(self):
  self.assertIsNone(executor.classify_unavailability('response exceeded the8192 output token maximum'))
