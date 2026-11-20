"""Phase III-B — CostAdapter and CostLedger tests."""
import unittest
from unittest.mock import patch

from urace.cost_adapter import LiteLLMCostAdapter, NullCostAdapter, make_cost_adapter, CostAdapter
from urace.cost_tracker import CostRecord, CostLedger, get_default_ledger


class CostAdapterProtocolTests(unittest.TestCase):
    def test_null_adapter_satisfies_protocol(self):
        self.assertIsInstance(NullCostAdapter(), CostAdapter)

    def test_null_adapter_returns_none(self):
        a = NullCostAdapter()
        self.assertIsNone(a.cost_for_usage("unknown-model", 100, 50))

    def test_litellm_adapter_satisfies_protocol(self):
        self.assertIsInstance(LiteLLMCostAdapter(), CostAdapter)

    def test_litellm_adapter_returns_float_for_known_model(self):
        a = LiteLLMCostAdapter()
        cost = a.cost_for_usage("claude-3-5-sonnet-20241022", 1000, 200)
        if cost is not None:
            self.assertIsInstance(cost, float)
            self.assertGreater(cost, 0.0)

    def test_litellm_adapter_returns_none_for_unknown_model(self):
        a = LiteLLMCostAdapter()
        cost = a.cost_for_usage("nonexistent-model-xyz-999", 100, 50)
        self.assertIsNone(cost)

    def test_make_cost_adapter_returns_litellm_when_available(self):
        try:
            import litellm  # noqa: F401
        except ImportError:
            self.skipTest("litellm not installed")
        adapter = make_cost_adapter()
        self.assertIsInstance(adapter, LiteLLMCostAdapter)

    def test_make_cost_adapter_returns_null_fallback(self):
        with patch.dict("sys.modules", {"litellm": None}):
            adapter = make_cost_adapter()
        self.assertIsInstance(adapter, NullCostAdapter)


class CostRecordTests(unittest.TestCase):
    def test_total_tokens_sums_all(self):
        r = CostRecord(
            provider="anthropic", model="claude-3-5-sonnet-20241022",
            operation_id="op-1", input_tokens=100, output_tokens=50,
            cache_read_tokens=20, cache_write_tokens=10,
        )
        self.assertEqual(r.total_tokens, 180)

    def test_total_tokens_no_cache(self):
        r = CostRecord(
            provider="openai", model="gpt-4", operation_id="op-2",
            input_tokens=200, output_tokens=80,
        )
        self.assertEqual(r.total_tokens, 280)


class CostLedgerTests(unittest.TestCase):
    def _ledger_with_null_adapter(self):
        return CostLedger()

    def test_record_adds_entry(self):
        ledger = CostLedger()
        ledger.record("anthropic", "claude-3-5-sonnet-20241022", "op-1", 100, 50,
                      adapter=NullCostAdapter())
        self.assertEqual(len(ledger.records()), 1)

    def test_total_usd_none_when_all_null(self):
        ledger = CostLedger()
        ledger.record("local", "llama3", "op-1", 100, 50, adapter=NullCostAdapter())
        self.assertIsNone(ledger.total_usd())

    def test_total_usd_sums_known_costs(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.cost_for_usage.return_value = 0.01
        ledger = CostLedger()
        ledger.record("anthropic", "claude-3-5-sonnet-20241022", "op-1", 100, 50, adapter=adapter)
        ledger.record("anthropic", "claude-3-5-sonnet-20241022", "op-2", 200, 80, adapter=adapter)
        self.assertAlmostEqual(ledger.total_usd(), 0.02)

    def test_summary_total(self):
        ledger = CostLedger()
        ledger.record("anthropic", "claude-3-5-sonnet-20241022", "op-1", 100, 50, adapter=NullCostAdapter())
        s = ledger.summary()
        self.assertEqual(s["total_records"], 1)
        self.assertEqual(s["total_input_tokens"], 100)
        self.assertEqual(s["total_output_tokens"], 50)

    def test_summary_by_provider(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.cost_for_usage.return_value = 0.005
        ledger = CostLedger()
        ledger.record("anthropic", "model-a", "op-1", 100, 50, adapter=adapter)
        ledger.record("openai", "model-b", "op-2", 200, 80, adapter=adapter)
        s = ledger.summary(by="provider")
        self.assertIn("provider", s)
        self.assertIn("anthropic", s["provider"])
        self.assertIn("openai", s["provider"])

    def test_exceeds_budget_false(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.cost_for_usage.return_value = 0.01
        ledger = CostLedger()
        ledger.record("anthropic", "model", "op-1", 100, 50, adapter=adapter)
        self.assertFalse(ledger.exceeds_budget(1.00))

    def test_exceeds_budget_true(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.cost_for_usage.return_value = 0.50
        ledger = CostLedger()
        ledger.record("anthropic", "model", "op-1", 100, 50, adapter=adapter)
        self.assertTrue(ledger.exceeds_budget(0.10))

    def test_cost_snapshot_fields(self):
        from unittest.mock import MagicMock
        adapter = MagicMock()
        adapter.cost_for_usage.return_value = 0.01
        ledger = CostLedger()
        ledger.record("anthropic", "claude-3-5-sonnet-20241022", "op-1", 100, 50, adapter=adapter)
        snap = ledger.cost_snapshot()
        self.assertIn("records", snap)
        self.assertIn("total_usd", snap)
        self.assertIn("total_tokens", snap)
        self.assertIn("providers", snap)
        self.assertEqual(snap["providers"], ["anthropic"])


class M2MEnvelopeCostSnapshotTests(unittest.TestCase):
    def test_api_execute_includes_cost_snapshot(self):
        from urace import api_interface
        from unittest.mock import MagicMock, patch
        import io
        from contextlib import redirect_stdout

        def _runner(args):
            print('{"status":"ok"}')
            return 0

        with patch("urace.cost_tracker.get_default_ledger") as mock_ledger:
            mock_ledger.return_value.cost_snapshot.return_value = {"records": 0, "total_usd": None, "total_tokens": 0, "providers": []}
            result = api_interface.execute(MagicMock(), _runner, argv=["status"])
        self.assertIn("cost_snapshot", result)
