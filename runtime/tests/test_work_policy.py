"""Tests for urace.work_policy — contract-bound execution choices."""
import math
import time
import unittest


def _base_policy(*, model="claude-sonnet-4-6", provider="anthropic", engine="abc123",
                  family="navigation", contract="navigation-v1", effort="medium",
                  samples=40, time_ratio=0.75, token_ratio=0.75, expires_offset=3600):
    return {
        "expires_unix": time.time() + expires_offset,
        "models": {provider: model},
        "engine_sha256": engine,
        "contracts": {family: contract},
        "recommendations": [{
            "provider": provider,
            "family": family,
            "native_effort": effort,
            "samples": samples,
            "quality_nonregressing": True,
            "usage_complete": True,
            "timing_complete": True,
            "time_ratio": time_ratio,
            "token_ratio": token_ratio,
        }],
    }


class ChooseDefaultsTests(unittest.TestCase):
    def test_fallback_on_none_policy(self):
        from urace.work_policy import choose
        result = choose(None, provider="anthropic", family="nav", model="claude-sonnet-4-6",
                        contract="nav-v1", engine="x", default_effort="medium", now=time.time())
        self.assertFalse(result["adaptive"])

    def test_fallback_on_disabled(self):
        from urace.work_policy import choose
        p = _base_policy()
        result = choose(p, provider="anthropic", family="navigation", model="claude-sonnet-4-6",
                        contract="navigation-v1", engine="abc123", default_effort="medium",
                        now=time.time(), enabled=False)
        self.assertFalse(result["adaptive"])

    def test_fallback_on_quarantined(self):
        from urace.work_policy import choose
        p = _base_policy()
        result = choose(p, provider="anthropic", family="navigation", model="claude-sonnet-4-6",
                        contract="navigation-v1", engine="abc123", default_effort="medium",
                        now=time.time(), quarantined=True)
        self.assertFalse(result["adaptive"])

    def test_fallback_on_expired_policy(self):
        from urace.work_policy import choose
        p = _base_policy(expires_offset=-10)
        result = choose(p, provider="anthropic", family="navigation", model="claude-sonnet-4-6",
                        contract="navigation-v1", engine="abc123", default_effort="medium",
                        now=time.time())
        self.assertFalse(result["adaptive"])

    def test_fallback_on_model_mismatch(self):
        from urace.work_policy import choose
        p = _base_policy()
        result = choose(p, provider="anthropic", family="navigation", model="gpt-4",
                        contract="navigation-v1", engine="abc123", default_effort="medium",
                        now=time.time())
        self.assertFalse(result["adaptive"])

    def test_fallback_on_engine_mismatch(self):
        from urace.work_policy import choose
        p = _base_policy()
        result = choose(p, provider="anthropic", family="navigation", model="claude-sonnet-4-6",
                        contract="navigation-v1", engine="wrong_engine", default_effort="medium",
                        now=time.time())
        self.assertFalse(result["adaptive"])

    def test_adaptive_on_valid_policy(self):
        from urace.work_policy import choose
        p = _base_policy()
        result = choose(p, provider="anthropic", family="navigation", model="claude-sonnet-4-6",
                        contract="navigation-v1", engine="abc123", default_effort="medium",
                        now=time.time())
        self.assertTrue(result["adaptive"])
        self.assertEqual(result["native_effort"], "medium")

    def test_fallback_on_insufficient_samples(self):
        from urace.work_policy import choose
        p = _base_policy(samples=10)
        result = choose(p, provider="anthropic", family="navigation", model="claude-sonnet-4-6",
                        contract="navigation-v1", engine="abc123", default_effort="medium",
                        now=time.time())
        self.assertFalse(result["adaptive"])

    def test_fallback_on_bad_ratio(self):
        from urace.work_policy import choose
        p = _base_policy(time_ratio=1.1)  # max > 1.05 → skip
        result = choose(p, provider="anthropic", family="navigation", model="claude-sonnet-4-6",
                        contract="navigation-v1", engine="abc123", default_effort="medium",
                        now=time.time())
        self.assertFalse(result["adaptive"])

    def test_invalid_default_effort_coerced_to_medium(self):
        from urace.work_policy import choose
        result = choose(None, provider="a", family="b", model="m", contract="c",
                        engine="e", default_effort="turbo", now=time.time())
        self.assertEqual(result["native_effort"], "medium")


class ExecutionModeTests(unittest.TestCase):
    def test_lightweight_for_single_simple_requirement(self):
        from urace.work_policy import execution_mode
        reqs = [{"name": "simple"}]
        self.assertEqual(execution_mode("auto", requirements=reqs), "lightweight")

    def test_managed_for_continuity(self):
        from urace.work_policy import execution_mode
        reqs = [{"name": "simple"}]
        self.assertEqual(execution_mode("auto", requirements=reqs, continuity=True), "managed")

    def test_managed_for_multiple_requirements(self):
        from urace.work_policy import execution_mode
        reqs = [{"name": "a"}, {"name": "b"}]
        self.assertEqual(execution_mode("auto", requirements=reqs), "managed")

    def test_managed_for_requirement_with_dependencies(self):
        from urace.work_policy import execution_mode
        reqs = [{"name": "x", "dependencies": ["y"]}]
        self.assertEqual(execution_mode("auto", requirements=reqs), "managed")

    def test_explicit_mode_passthrough(self):
        from urace.work_policy import execution_mode
        for mode in ("lightweight", "managed", "standalone"):
            self.assertEqual(execution_mode(mode, requirements=[]), mode)

    def test_invalid_mode_raises(self):
        from urace.work_policy import execution_mode
        with self.assertRaises(ValueError):
            execution_mode("turbo", requirements=[])


class OutcomesTests(unittest.TestCase):
    def _row(self, *, complete=True, delivered=True, tokens=100, receipt_id="r1"):
        return {
            "complete": complete,
            "delivered": delivered,
            "native_receipts": [{"id": receipt_id, "tokens": tokens}],
        }

    def test_basic_throughput(self):
        from urace.work_policy import outcomes
        rows = [self._row(receipt_id=f"r{i}") for i in range(3)]
        result = outcomes(rows, 3600.0)
        self.assertEqual(result["completed"], 3)
        self.assertEqual(result["validated"], 3)
        self.assertAlmostEqual(result["validated_per_elapsed_hour"], 3.0)

    def test_zero_elapsed_raises(self):
        from urace.work_policy import outcomes
        with self.assertRaises(ValueError):
            outcomes([], 0.0)

    def test_negative_elapsed_raises(self):
        from urace.work_policy import outcomes
        with self.assertRaises(ValueError):
            outcomes([], -1.0)

    def test_tokens_per_delivery_calculated(self):
        from urace.work_policy import outcomes
        rows = [self._row(tokens=200, receipt_id="r1"), self._row(tokens=200, receipt_id="r2")]
        result = outcomes(rows, 1.0)
        self.assertEqual(result["tokens_per_validated_delivery"], 200)

    def test_failed_rows_in_denominator(self):
        from urace.work_policy import outcomes
        rows = [
            self._row(complete=True, delivered=True, receipt_id="r1"),
            {"complete": False, "delivered": False, "native_receipts": []},
        ]
        result = outcomes(rows, 3600.0)
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["failed_or_pending"], 1)

    def test_known_tokens_false_when_no_receipts(self):
        from urace.work_policy import outcomes
        rows = [{"complete": True, "delivered": True, "native_receipts": []}]
        result = outcomes(rows, 1.0)
        self.assertFalse(result["usage_complete"])
