"""Phase III-C — exchange_endpoint P2P settlement tests."""
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from urace.exchange_endpoint import handle_credit_settlement, SCHEMA


def _mock_exchange(root):
    ex = MagicMock()
    ex._root = str(root)
    ex.load.return_value = {"enabled": True, "peers": {}}
    ex.audit = MagicMock()
    return ex


class HandleCreditSettlementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.exchange = _mock_exchange(self.root)

    def _payload(self, **overrides):
        base = {
            "schema": SCHEMA,
            "action": "earn",
            "peer_id": "peer-abc",
            "units": 10,
            "reason": "test",
            "operation_id": "op-1",
        }
        base.update(overrides)
        return base

    def test_wrong_schema_returns_error(self):
        result = handle_credit_settlement(self.exchange, "peer-abc", self._payload(schema="bad"))
        self.assertEqual(result["status"], "error")
        self.assertIn("schema", result["error"])

    def test_invalid_action_returns_error(self):
        result = handle_credit_settlement(self.exchange, "peer-abc", self._payload(action="give"))
        self.assertEqual(result["status"], "error")
        self.assertIn("action", result["error"])

    def test_zero_units_returns_error(self):
        result = handle_credit_settlement(self.exchange, "peer-abc", self._payload(units=0))
        self.assertEqual(result["status"], "error")

    def test_negative_units_returns_error(self):
        result = handle_credit_settlement(self.exchange, "peer-abc", self._payload(units=-5))
        self.assertEqual(result["status"], "error")

    def test_earn_calls_earn_units(self):
        with patch("urace.credit_ledger.earn_units") as mock_earn:
            result = handle_credit_settlement(self.exchange, "peer-abc", self._payload(action="earn"))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["action"], "earn")
        mock_earn.assert_called_once()

    def test_spend_calls_spend_units(self):
        with patch("urace.credit_ledger.spend_units") as mock_spend:
            result = handle_credit_settlement(self.exchange, "peer-abc", self._payload(action="spend"))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["action"], "spend")
        mock_spend.assert_called_once()

    def test_audit_recorded_on_success(self):
        with patch("urace.credit_ledger.earn_units"):
            handle_credit_settlement(self.exchange, "peer-abc", self._payload())
        self.exchange.audit.assert_called_once()
        call_kwargs = self.exchange.audit.call_args[1]
        self.assertEqual(call_kwargs["kind"], "CREDIT_SETTLEMENT_APPLIED")

    def test_credit_ledger_exception_returns_error(self):
        with patch("urace.credit_ledger.earn_units", side_effect=ValueError("ledger error")):
            result = handle_credit_settlement(self.exchange, "peer-abc", self._payload())
        self.assertEqual(result["status"], "error")
        self.assertIn("ledger error", result["error"])


class BuildSettlementRouterTests(unittest.TestCase):
    def test_returns_none_without_fastapi(self):
        from urace.exchange_endpoint import build_settlement_router
        with patch.dict("sys.modules", {"fastapi": None}):
            router = build_settlement_router(lambda: None)
        self.assertIsNone(router)

    def test_returns_router_with_fastapi(self):
        try:
            from fastapi import APIRouter
        except ImportError:
            self.skipTest("fastapi not installed")
        from urace.exchange_endpoint import build_settlement_router
        router = build_settlement_router(lambda: None)
        self.assertIsNotNone(router)
