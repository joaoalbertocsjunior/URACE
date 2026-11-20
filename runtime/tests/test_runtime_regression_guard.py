"""Phase III-A — runtime_regression_guard tests."""
import unittest
from unittest.mock import patch

from urace import runtime_regression_guard as rg


def _state_with_regression(scope="api"):
    return {
        "quality_deltas": [
            {"scope": scope, "classification": "REGRESSION", "measured_at": "2026-01-02T00:00:00", "delta": -0.5},
        ],
        "decision_records": [],
    }


def _state_ok(scope="api"):
    return {
        "quality_deltas": [
            {"scope": scope, "classification": "IMPROVEMENT", "measured_at": "2026-01-02T00:00:00", "delta": 0.3},
        ],
        "decision_records": [],
    }


def _state_regression_accepted(scope="api"):
    return {
        "quality_deltas": [
            {"scope": scope, "classification": "REGRESSION", "measured_at": "2026-01-01T00:00:00", "delta": -0.5},
        ],
        "decision_records": [
            {"kind": "CHECKPOINT_ACCEPTANCE", "decided_at": "2026-01-02T00:00:00", "subject": scope},
        ],
    }


class CheckTests(unittest.TestCase):
    def test_ok_when_no_quality_deltas(self):
        self.assertEqual(rg.check({}), "OK")

    def test_ok_when_improvement(self):
        self.assertEqual(rg.check(_state_ok()), "OK")

    def test_regression_when_latest_is_regression(self):
        self.assertEqual(rg.check(_state_with_regression()), "REGRESSION")

    def test_ok_when_regression_accepted(self):
        self.assertEqual(rg.check(_state_regression_accepted()), "OK")

    def test_scope_filter_ignores_other_scopes(self):
        state = _state_with_regression(scope="ui")
        self.assertEqual(rg.check(state, scope="api"), "OK")

    def test_scope_filter_catches_matching_scope(self):
        state = _state_with_regression(scope="api")
        self.assertEqual(rg.check(state, scope="api"), "REGRESSION")

    def test_multiple_deltas_uses_latest(self):
        state = {
            "quality_deltas": [
                {"scope": "api", "classification": "REGRESSION", "measured_at": "2026-01-01T00:00:00", "delta": -0.3},
                {"scope": "api", "classification": "IMPROVEMENT", "measured_at": "2026-01-02T00:00:00", "delta": 0.2},
            ],
            "decision_records": [],
        }
        self.assertEqual(rg.check(state), "OK")


class RecordBlockedTests(unittest.TestCase):
    def test_adds_decision_record(self):
        state = {"decision_records": []}
        record = rg.record_blocked(state, scope="api")
        self.assertEqual(len(state["decision_records"]), 1)
        self.assertEqual(record["kind"], "REGRESSION_BLOCKED")
        self.assertEqual(record["disposition"], "REGRESSION_BLOCKED")

    def test_record_has_required_fields(self):
        state = {}
        record = rg.record_blocked(state)
        self.assertIn("id", record)
        self.assertIn("decided_at", record)
        self.assertIn("rationale", record)


class GuardStatusTests(unittest.TestCase):
    def test_ok_status(self):
        result = rg.guard_status(_state_ok())
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["checked_scopes"], 1)
        self.assertIn("api", result["per_scope"])

    def test_regression_status(self):
        result = rg.guard_status(_state_with_regression())
        self.assertEqual(result["status"], "REGRESSION")

    def test_empty_state(self):
        result = rg.guard_status({})
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["checked_scopes"], 0)


class CycleIntegrationTests(unittest.TestCase):
    def test_cycle_returns_regression_blocked(self):
        from urace import runtime_regression_guard as _rg
        state = _state_with_regression(scope="product")
        self.assertEqual(_rg.check(state, scope="product"), "REGRESSION")
        record = _rg.record_blocked(state, scope="product")
        self.assertIn("REGRESSION_BLOCKED", record["kind"])
