"""Integration tests: EVT_* publishers wired into save_state, cycle, earn_units, spend_units."""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile, json

from urace.event_bus import _BUS


def _teardown():
    _BUS._clear_all()


class SaveStateEventTest(unittest.TestCase):

    def tearDown(self):
        _teardown()

    def test_state_saved_published_on_save_state(self):
        from urace._common import save_state
        events = []
        handler = lambda **kw: events.append(kw)  # noqa: E731 — strong ref required for weakref bus
        _BUS.subscribe('state.saved', handler)

        with tempfile.TemporaryDirectory() as tmp:
            config = {"state_path": str(Path(tmp) / "state.json")}
            state = {
                "state_version": 0, "updated_at": "",
                "authority_basis": [{"id": "a1", "kind": "intent", "summary": "s", "source": "operator"}],
                "objectives": [], "goal_records": [], "intent_records": [],
                "constraint_records": [], "decision_records": [], "evidence": [],
                "operations": [], "checkpoints": [], "lifecycle_state": "ACTIVE",
            }
            with patch('urace._common._post_save_effects'):
                save_state(config, state)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['state_version'], 1)

    def test_state_saved_includes_incremented_version(self):
        from urace._common import save_state
        versions = []
        handler = lambda **kw: versions.append(kw['state_version'])  # noqa: E731
        _BUS.subscribe('state.saved', handler)

        with tempfile.TemporaryDirectory() as tmp:
            config = {"state_path": str(Path(tmp) / "state.json")}
            state = {
                "state_version": 5, "updated_at": "",
                "authority_basis": [{"id": "a1", "kind": "intent", "summary": "s", "source": "operator"}],
                "objectives": [], "goal_records": [], "intent_records": [],
                "constraint_records": [], "decision_records": [], "evidence": [],
                "operations": [], "checkpoints": [], "lifecycle_state": "ACTIVE",
            }
            with patch('urace._common._post_save_effects'):
                save_state(config, state)

        self.assertEqual(versions, [6])


class LedgerEventTest(unittest.TestCase):

    def tearDown(self):
        _teardown()

    def _make_root(self, tmp):
        root = Path(tmp)
        return root

    def test_ledger_earned_published_on_earn_units(self):
        from urace import credit_ledger as cl
        events = []
        handler = lambda **kw: events.append(kw)  # noqa: E731
        _BUS.subscribe('ledger.earned', handler)

        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            cl.earn_units(root, 'peer-1', cl.UNIT, 'test-earn')

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['peer_id'], 'peer-1')
        self.assertGreater(events[0]['units'], 0)
        self.assertEqual(events[0]['reason'], 'test-earn')

    def test_ledger_spent_published_on_spend_units(self):
        from urace import credit_ledger as cl
        events = []
        handler = lambda **kw: events.append(kw)  # noqa: E731
        _BUS.subscribe('ledger.spent', handler)

        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            # Fund first
            cl.earn_units(root, 'peer-2', cl.UNIT * 5, 'seed')
            cl.spend_units(root, 'peer-2', cl.UNIT, 'test-spend')

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['peer_id'], 'peer-2')
        self.assertEqual(events[0]['units'], cl.UNIT)
        self.assertEqual(events[0]['reason'], 'test-spend')

    def test_earn_units_capped_does_not_publish(self):
        """earn_units returns early when cap reached — no event published."""
        from urace import credit_ledger as cl
        events = []
        handler = lambda **kw: events.append(kw)  # noqa: E731
        _BUS.subscribe('ledger.earned', handler)

        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            # Saturate to cap
            cap = cl.peer_cap_units(root, 'peer-3')
            cl.earn_units(root, 'peer-3', cap, 'fill')
            events.clear()
            # Next earn should be a no-op (adjusted_units becomes 0)
            cl.earn_units(root, 'peer-3', cl.UNIT, 'over-cap')

        self.assertEqual(events, [])


if __name__ == '__main__':
    unittest.main()
