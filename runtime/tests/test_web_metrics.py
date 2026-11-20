"""Phase IV-B — live metrics route tests."""
import unittest


class LiveMetricsAccumulatorTests(unittest.TestCase):
    def _fresh(self):
        from urace.web.routes.metrics import _LiveMetrics
        return _LiveMetrics()

    def test_initial_snapshot_has_expected_keys(self):
        m = self._fresh()
        snap = m.snapshot()
        self.assertIn("cycle_started", snap)
        self.assertIn("cycle_completed", snap)
        self.assertIn("ledger_earned_total", snap)
        self.assertIn("ledger_spent_total", snap)

    def test_cycle_started_increments(self):
        m = self._fresh()
        m.on_cycle_started(cycle_id="c-1")
        m.on_cycle_started(cycle_id="c-2")
        self.assertEqual(m.snapshot()["cycle_started"], 2)
        self.assertEqual(m.snapshot()["cycle_last_id"], "c-2")

    def test_cycle_completed_increments_and_records_outcome(self):
        m = self._fresh()
        m.on_cycle_completed(cycle_id="c-1", outcome="ok")
        self.assertEqual(m.snapshot()["cycle_completed"], 1)
        self.assertEqual(m.snapshot()["cycle_last_outcome"], "ok")

    def test_ledger_earned_accumulates(self):
        m = self._fresh()
        m.on_ledger_earned(peer_id="p1", units=10)
        m.on_ledger_earned(peer_id="p2", units=5)
        self.assertEqual(m.snapshot()["ledger_earned_total"], 15)
        self.assertEqual(m.snapshot()["ledger_last_earn_peer"], "p2")

    def test_ledger_spent_accumulates(self):
        m = self._fresh()
        m.on_ledger_spent(peer_id="p1", units=3)
        self.assertEqual(m.snapshot()["ledger_spent_total"], 3)

    def test_none_units_does_not_crash(self):
        m = self._fresh()
        m.on_ledger_earned(peer_id="p1", units=None)
        self.assertEqual(m.snapshot()["ledger_earned_total"], 0)

    def test_snapshot_returns_copy(self):
        m = self._fresh()
        snap1 = m.snapshot()
        m.on_cycle_started(cycle_id="c-1")
        snap2 = m.snapshot()
        self.assertNotEqual(snap1["cycle_started"], snap2["cycle_started"])


class BuildRouterTests(unittest.TestCase):
    def test_returns_router_with_fastapi(self):
        try:
            from fastapi import APIRouter  # noqa: F401
        except ImportError:
            self.skipTest("fastapi not installed")
        from unittest.mock import MagicMock
        from urace.web.routes.metrics import build_router
        router = build_router(verify_token=MagicMock())
        self.assertIsNotNone(router)

    def test_live_metrics_subscribed_on_build(self):
        try:
            from fastapi import APIRouter  # noqa: F401
        except ImportError:
            self.skipTest("fastapi not installed")
        from unittest.mock import MagicMock
        from urace.web.routes import metrics as _m
        build_router = _m.build_router
        build_router(verify_token=MagicMock())
        self.assertTrue(_m._SUBSCRIBED)
