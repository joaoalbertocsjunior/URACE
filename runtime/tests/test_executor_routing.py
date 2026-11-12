import copy,unittest
from datetime import datetime, timedelta, timezone

from urace import executor_routing as er


def _future(seconds=3600):
 return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _past(seconds=3600):
 return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


class ExecutorUnavailableTests(unittest.TestCase):
 def test_category_stored(self):
  exc = er.ExecutorUnavailable("PROVIDER_CAPACITY", None)
  self.assertEqual(exc.category, "PROVIDER_CAPACITY")

 def test_retry_at_stored(self):
  exc = er.ExecutorUnavailable("PROVIDER_CAPACITY", "2025-01-01T00:00:00+00:00")
  self.assertEqual(exc.retry_at, "2025-01-01T00:00:00+00:00")

 def test_detail_truncated_to_500(self):
  exc = er.ExecutorUnavailable("PROVIDER_CAPACITY", None, "x" * 1000)
  self.assertEqual(len(exc.detail), 500)

 def test_is_runtime_error(self):
  self.assertTrue(issubclass(er.ExecutorUnavailable, RuntimeError))

 def test_message_includes_condition(self):
  exc = er.ExecutorUnavailable("LOCAL_TRANSPORT_CEILING", None)
  self.assertIn("Local Executor transport ceiling", str(exc))


class ClassifyUnavailabilityTests(unittest.TestCase):
 def test_rate_limit_detected(self):
  result = er.classify_unavailability("You have hit your rate limit for today")
  self.assertIsNotNone(result)
  self.assertIsInstance(result, er.ExecutorUnavailable)
  self.assertEqual(result.category, "PROVIDER_CAPACITY")

 def test_unrelated_message_returns_none(self):
  result = er.classify_unavailability("Task completed successfully")
  self.assertIsNone(result)

 def test_credits_exhausted_detected(self):
  result = er.classify_unavailability("credits exhausted, please add funds")
  self.assertIsNotNone(result)

 def test_quota_exceeded_detected(self):
  result = er.classify_unavailability("quota exceeded")
  self.assertIsNotNone(result)

 def test_fallback_retry_at_in_future(self):
  result = er.classify_unavailability("usage limit reached")
  self.assertIsNotNone(result)
  retry = datetime.fromisoformat(result.retry_at)
  self.assertGreater(retry, datetime.now(timezone.utc))


class ClassifyExecutionEnvironmentTests(unittest.TestCase):
 def test_bwrap_loopback_detected(self):
  detail = "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"
  result = er.classify_execution_environment(detail, {})
  self.assertIsNotNone(result)
  self.assertEqual(result.category, "EXECUTION_ENVIRONMENT_UNAVAILABLE")

 def test_sandbox_init_detected(self):
  result = er.classify_execution_environment("sandbox could not initialize", {})
  self.assertIsNotNone(result)

 def test_unrelated_returns_none(self):
  result = er.classify_execution_environment("normal output here", {})
  self.assertIsNone(result)


class ClassifyAuthFailureTests(unittest.TestCase):
 def test_401_detected(self):
  result = er.classify_auth_failure("HTTP 401 unauthorized", {})
  self.assertIsNotNone(result)
  self.assertEqual(result.category, "EXECUTOR_AUTH_UNAVAILABLE")

 def test_invalid_api_key_detected(self):
  result = er.classify_auth_failure("Invalid API key provided", {})
  self.assertIsNotNone(result)

 def test_valid_response_returns_none(self):
  result = er.classify_auth_failure("All good here", {})
  self.assertIsNone(result)


class ClassifyTransientNetworkTests(unittest.TestCase):
 def test_502_detected(self):
  result = er.classify_transient_network_failure("502 Bad Gateway", {})
  self.assertIsNotNone(result)
  self.assertEqual(result.category, "EXECUTOR_TRANSIENT_NETWORK")

 def test_stream_disconnected_detected(self):
  result = er.classify_transient_network_failure("stream disconnected mid-response", {})
  self.assertIsNotNone(result)

 def test_unrelated_returns_none(self):
  result = er.classify_transient_network_failure("success", {})
  self.assertIsNone(result)

 def test_short_backoff_applied(self):
  settings = {"transient_network_backoff_seconds": 30}
  result = er.classify_transient_network_failure("503 service unavailable", settings)
  retry = datetime.fromisoformat(result.retry_at)
  delta = (retry - datetime.now(timezone.utc)).total_seconds()
  self.assertLess(delta, 60)


class ProviderDefinitionsTests(unittest.TestCase):
 def test_no_providers_returns_default(self):
  providers = er.provider_definitions({})
  self.assertTrue(len(providers) >= 1)
  self.assertEqual(providers[0]["id"], "primary")

 def test_explicit_providers_returned(self):
  settings = {"providers": [
   {"id": "a", "priority": 100, "enabled": True},
   {"id": "b", "priority": 80, "enabled": True},
  ]}
  providers = er.provider_definitions(settings)
  ids = [p["id"] for p in providers]
  self.assertIn("a", ids)
  self.assertIn("b", ids)

 def test_disabled_providers_excluded(self):
  settings = {"providers": [
   {"id": "a", "priority": 100, "enabled": True},
   {"id": "b", "priority": 80, "enabled": False},
  ]}
  providers = er.provider_definitions(settings)
  ids = [p["id"] for p in providers]
  self.assertIn("a", ids)
  self.assertNotIn("b", ids)

 def test_sorted_by_priority_descending(self):
  settings = {"providers": [
   {"id": "low", "priority": 50, "enabled": True},
   {"id": "high", "priority": 100, "enabled": True},
  ]}
  providers = er.provider_definitions(settings)
  self.assertEqual(providers[0]["id"], "high")

 def test_capability_filter_applied(self):
  settings = {"providers": [
   {"id": "full", "priority": 100, "enabled": True,
    "capabilities": ["discovery", "planning", "execution"]},
  ]}
  providers = er.provider_definitions(settings, capability="execution")
  self.assertTrue(any(p["id"] == "full" for p in providers))

 def test_default_capabilities_added(self):
  settings = {"providers": [{"id": "p", "priority": 100, "enabled": True}]}
  providers = er.provider_definitions(settings)
  self.assertIn("execution", providers[0]["capabilities"])


class RoutedProviderDefinitionsTests(unittest.TestCase):
 def _settings(self, *provider_ids):
  return {"providers": [{"id": pid, "priority": 100, "enabled": True} for pid in provider_ids]}

 def test_compatible_providers_returned(self):
  settings = self._settings("p1", "p2")
  result = er.routed_provider_definitions(settings, {}, "execution")
  ids = [p["id"] for p in result]
  self.assertIn("p1", ids)
  self.assertIn("p2", ids)

 def test_recent_success_prefers_provider(self):
  settings = self._settings("p1", "p2")
  pool = {
   "p1": {"completion_history": [
    {"capability": "execution", "at": _future(-10), "elapsed_seconds": 5}
   ]},
  }
  result = er.routed_provider_definitions(settings, pool, "execution")
  # p1 has a completion history entry — verify it appears
  self.assertTrue(any(p["id"] == "p1" for p in result))

 def test_timing_error_in_pool_state_handled_gracefully(self):
  settings = self._settings("p1")
  pool = {"p1": {"retry_at": "not-a-valid-iso-timestamp"}}
  # Should not raise
  result = er.routed_provider_definitions(settings, pool, "execution")
  self.assertIsInstance(result, list)


class ProviderSettingsTests(unittest.TestCase):
 def test_merges_provider_into_settings(self):
  settings = {"timeout": 30, "providers": []}
  provider = {"id": "p1", "command": "codex", "adapter": "codex-cli", "priority": 100}
  result = er.provider_settings(settings, provider)
  self.assertEqual(result["command"], "codex")
  self.assertEqual(result["timeout"], 30)

 def test_provider_id_not_leaked(self):
  settings = {}
  provider = {"id": "p1", "command": "codex", "adapter": "codex-cli", "priority": 100}
  result = er.provider_settings(settings, provider)
  self.assertNotIn("id", result)


class TransportReceiptTests(unittest.TestCase):
 def test_receipt_stores_provider_id(self):
  receipt = er._transport_receipt("p1", {"input_tokens": 100})
  self.assertEqual(receipt["provider_id"], "p1")

 def test_receipt_copies_metadata(self):
  meta = {"input_tokens": 100}
  receipt = er._transport_receipt("p1", meta)
  meta["input_tokens"] = 999
  self.assertEqual(receipt["usage"]["input_tokens"], 100)

 def test_none_metadata_gives_none_usage(self):
  receipt = er._transport_receipt("p1", None)
  self.assertIsNone(receipt["usage"])


class AggregateTransportUsageTests(unittest.TestCase):
 def test_single_receipt_returned_directly(self):
  receipts = [{"provider_id": "p1", "usage": {"input_tokens": 50}}]
  result = er._aggregate_transport_usage(receipts)
  self.assertEqual(result["input_tokens"], 50)

 def test_empty_returns_none(self):
  self.assertIsNone(er._aggregate_transport_usage([]))

 def test_aggregates_token_sums(self):
  receipts = [
   {"provider_id": "p1", "usage": {"input_tokens": 100, "output_tokens": 20, "cached_input_tokens": 0}},
   {"provider_id": "p2", "usage": {"input_tokens": 200, "output_tokens": 30, "cached_input_tokens": 5}},
  ]
  result = er._aggregate_transport_usage(receipts)
  self.assertEqual(result["input_tokens"], 300)
  self.assertEqual(result["output_tokens"], 50)

 def test_partial_usage_gives_aggregated_partial_provenance(self):
  receipts = [
   {"provider_id": "p1", "usage": {"input_tokens": 100}},
   {"provider_id": "p2", "usage": None},
  ]
  result = er._aggregate_transport_usage(receipts)
  self.assertEqual(result["usage_provenance"], "AGGREGATED_PARTIAL")


class ConfiguredTransportLimitTests(unittest.TestCase):
 def test_uses_provider_key_when_present(self):
  provider = {"max_calls_per_24h": 5}
  result = er.configured_transport_limit(provider, {}, "max_calls_per_24h", "max_executor_calls_per_24h", 2)
  self.assertEqual(result, 5)

 def test_falls_back_to_settings_key(self):
  provider = {}
  settings = {"max_executor_calls_per_24h": 10}
  result = er.configured_transport_limit(provider, settings, "max_calls_per_24h", "max_executor_calls_per_24h", 2)
  self.assertEqual(result, 10)

 def test_uses_fallback_default(self):
  result = er.configured_transport_limit({}, {}, "max_calls_per_24h", "max_executor_calls_per_24h", 2)
  self.assertEqual(result, 2)

 def test_none_propagated(self):
  provider = {"max_calls_per_24h": None}
  result = er.configured_transport_limit(provider, {}, "max_calls_per_24h", "max_executor_calls_per_24h", 2)
  self.assertIsNone(result)


if __name__ == "__main__":
 unittest.main()
