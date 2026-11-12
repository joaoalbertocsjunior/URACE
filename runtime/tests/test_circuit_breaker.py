import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from urace import circuit_breaker as cb


def _future(seconds=3600):
 return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _past(seconds=3600):
 return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


SETTINGS = {
 "providers": [
  {"id": "p1", "adapter": "codex-cli", "priority": 100},
  {"id": "p2", "adapter": "codex-cli", "priority": 80},
 ],
 "circuit_breaker_trip_threshold": 3,
 "circuit_breaker_cooldown_seconds": 600,
}


class CircuitBreakerAutoTripTests(unittest.TestCase):
 def test_no_trip_below_threshold(self):
  pool = {"p1": {"failures": 2}}
  result = cb.auto_trip("p1", SETTINGS, pool)
  self.assertIsNone(result)
  self.assertNotIn("cooldown_until", pool["p1"])

 def test_trips_at_threshold(self):
  pool = {"p1": {"failures": 3}}
  result = cb.auto_trip("p1", SETTINGS, pool)
  self.assertIsNotNone(result)
  self.assertTrue(result["tripped"])
  self.assertEqual(result["provider_id"], "p1")
  self.assertEqual(result["threshold"], 3)
  self.assertIn("cooldown_until", pool["p1"])
  self.assertIn("circuit_breaker_tripped_at", pool["p1"])

 def test_trips_above_threshold(self):
  pool = {"p1": {"failures": 10}}
  result = cb.auto_trip("p1", SETTINGS, pool)
  self.assertIsNotNone(result)
  self.assertEqual(result["failures"], 10)

 def test_cooldown_until_is_in_future(self):
  pool = {"p1": {"failures": 5}}
  cb.auto_trip("p1", SETTINGS, pool)
  cooldown = datetime.fromisoformat(pool["p1"]["cooldown_until"])
  self.assertGreater(cooldown, datetime.now(timezone.utc))

 def test_cooldown_duration_matches_settings(self):
  pool = {"p1": {"failures": 5}}
  before = datetime.now(timezone.utc)
  cb.auto_trip("p1", SETTINGS, pool)
  cooldown = datetime.fromisoformat(pool["p1"]["cooldown_until"])
  delta = (cooldown - before).total_seconds()
  self.assertAlmostEqual(delta, 600, delta=5)

 def test_default_threshold_used_when_not_in_settings(self):
  pool = {"p1": {"failures": cb.DEFAULT_TRIP_THRESHOLD - 1}}
  self.assertIsNone(cb.auto_trip("p1", {}, pool))
  pool["p1"]["failures"] = cb.DEFAULT_TRIP_THRESHOLD
  result = cb.auto_trip("p1", {}, pool)
  self.assertIsNotNone(result)

 def test_creates_provider_key_if_missing(self):
  pool = {}
  result = cb.auto_trip("p1", SETTINGS, pool)
  self.assertIsNone(result)  # failures defaults to 0, below threshold=3


def _providers_patch(providers=None):
 if providers is None:
  providers = [{"id": "p1"}, {"id": "p2"}]
 from unittest.mock import MagicMock
 mock_ex = MagicMock()
 mock_ex.provider_definitions.return_value = providers
 return patch.dict("sys.modules", {"urace.executor": mock_ex, "urace.circuit_breaker._ex": mock_ex}), mock_ex


class CircuitBreakerResetTests(unittest.TestCase):
 def setUp(self):
  import sys
  import types
  # Pre-import executor module mock so the lazy import inside cb functions finds it
  if "urace.executor" not in sys.modules:
   mod = types.ModuleType("urace.executor")
   sys.modules["urace.executor"] = mod
  from urace import executor as _ex_mod
  self._orig_provider_defs = getattr(_ex_mod, "provider_definitions", None)
  _ex_mod.provider_definitions = lambda s: [{"id": "p1"}, {"id": "p2"}]
  self._ex_mod = _ex_mod

 def tearDown(self):
  if self._orig_provider_defs is not None:
   self._ex_mod.provider_definitions = self._orig_provider_defs
  else:
   try: delattr(self._ex_mod, "provider_definitions")
   except AttributeError: pass

 def test_reset_clears_failures_retry_cooldown(self):
  pool = {"p1": {"failures": 5, "retry_at": _future(), "cooldown_until": _future()}}
  result = cb.reset("p1", SETTINGS, pool)
  self.assertEqual(result["status"], "ok")
  self.assertEqual(result["provider_id"], "p1")
  self.assertNotIn("failures", pool["p1"])
  self.assertNotIn("retry_at", pool["p1"])
  self.assertNotIn("cooldown_until", pool["p1"])
  self.assertIn("circuit_breaker_reset_at", pool["p1"])

 def test_reset_records_cleared_keys(self):
  pool = {"p1": {"failures": 3, "retry_at": _future()}}
  result = cb.reset("p1", SETTINGS, pool)
  self.assertIn("failures", result["cleared"])
  self.assertIn("retry_at", result["cleared"])

 def test_reset_unknown_provider_raises(self):
  pool = {}
  with self.assertRaises(ValueError):
   cb.reset("unknown-x", SETTINGS, pool)

 def test_reset_creates_provider_entry_if_absent(self):
  pool = {}
  result = cb.reset("p1", SETTINGS, pool)
  self.assertEqual(result["status"], "ok")
  self.assertIn("p1", pool)


class CircuitBreakerStatusTests(unittest.TestCase):
 def setUp(self):
  from urace import executor as _ex_mod
  self._orig = getattr(_ex_mod, "provider_definitions", None)
  _ex_mod.provider_definitions = lambda s: [{"id": "p1"}, {"id": "p2"}]
  self._ex_mod = _ex_mod

 def tearDown(self):
  if self._orig is not None:
   self._ex_mod.provider_definitions = self._orig
  else:
   try: delattr(self._ex_mod, "provider_definitions")
   except AttributeError: pass

 def test_status_returns_all_providers(self):
  pool = {}
  result = cb.status(SETTINGS, pool)
  self.assertEqual(result["status"], "ok")
  ids = [r["provider_id"] for r in result["providers"]]
  self.assertIn("p1", ids)
  self.assertIn("p2", ids)

 def test_tripped_flag_set_when_failures_at_threshold(self):
  pool = {"p1": {"failures": 3}}
  result = cb.status(SETTINGS, pool)
  p1 = next(r for r in result["providers"] if r["provider_id"] == "p1")
  self.assertTrue(p1["tripped"])
  self.assertEqual(result["tripped_count"], 1)
  self.assertEqual(result["healthy_count"], 1)

 def test_in_cooldown_when_retry_at_in_future(self):
  pool = {"p1": {"failures": 3, "retry_at": _future()}}
  result = cb.status(SETTINGS, pool)
  p1 = next(r for r in result["providers"] if r["provider_id"] == "p1")
  self.assertTrue(p1["in_cooldown"])
  self.assertEqual(p1["recommendation"], "wait")

 def test_not_in_cooldown_when_retry_at_past(self):
  pool = {"p1": {"failures": 3, "retry_at": _past()}}
  result = cb.status(SETTINGS, pool)
  p1 = next(r for r in result["providers"] if r["provider_id"] == "p1")
  self.assertFalse(p1["in_cooldown"])
  self.assertEqual(p1["recommendation"], "reset")

 def test_ok_recommendation_when_healthy(self):
  pool = {"p1": {"failures": 1}}
  result = cb.status(SETTINGS, pool)
  p1 = next(r for r in result["providers"] if r["provider_id"] == "p1")
  self.assertEqual(p1["recommendation"], "ok")

 def test_calls_counters_returned(self):
  pool = {"p1": {"calls_24h": 7, "calls_30d": 42}}
  result = cb.status(SETTINGS, pool)
  p1 = next(r for r in result["providers"] if r["provider_id"] == "p1")
  self.assertEqual(p1["calls_24h"], 7)
  self.assertEqual(p1["calls_30d"], 42)


if __name__ == "__main__":
 unittest.main()
