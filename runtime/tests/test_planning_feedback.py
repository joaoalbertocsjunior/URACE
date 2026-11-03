"""Tests for planning_feedback.py — observability → planning feedback loop."""
import unittest
from urace import planning_feedback as pf


def _make_state(objectives=None, calls=None):
    return {
        "objectives": objectives or [],
        "executor_state": {"executor_calls": calls or []},
    }


class ComputeAdjustmentsTests(unittest.TestCase):
    def test_empty_state(self):
        adj = pf.compute_adjustments(_make_state())
        self.assertEqual(adj, {})

    def test_no_call_history_small_boost(self):
        state = _make_state(objectives=[{"id": "o1", "status": "planned"}])
        adj = pf.compute_adjustments(state)
        self.assertIn("o1", adj)
        self.assertGreater(adj["o1"], 0.0)

    def test_all_accepted_calls_positive(self):
        calls = [{"objective_id": "o1", "outcome": "accepted"} for _ in range(5)]
        state = _make_state(
            objectives=[{"id": "o1", "status": "planned"}],
            calls=calls,
        )
        adj = pf.compute_adjustments(state)
        self.assertGreater(adj["o1"], 0.0)

    def test_all_rejected_calls_negative(self):
        calls = [{"objective_id": "o1", "outcome": "rejected"} for _ in range(5)]
        state = _make_state(
            objectives=[{"id": "o1", "status": "planned"}],
            calls=calls,
        )
        adj = pf.compute_adjustments(state)
        self.assertLess(adj["o1"], 0.0)

    def test_completed_objective_zero(self):
        calls = [{"objective_id": "o1", "outcome": "rejected"} for _ in range(5)]
        state = _make_state(
            objectives=[{"id": "o1", "status": "completed"}],
            calls=calls,
        )
        adj = pf.compute_adjustments(state)
        self.assertEqual(adj["o1"], 0.0)

    def test_stagnation_penalty(self):
        calls = [{"objective_id": "o1", "outcome": "rejected"} for _ in range(10)]
        state = _make_state(
            objectives=[{"id": "o1", "status": "planned"}],
            calls=calls,
        )
        adj = pf.compute_adjustments(state)
        # 10 calls all rejected → stagnation penalty applies
        self.assertLess(adj["o1"], -3.0)

    def test_adjustment_clamped(self):
        calls = [{"objective_id": "o1", "outcome": "accepted"} for _ in range(50)]
        state = _make_state(
            objectives=[{"id": "o1", "status": "planned"}],
            calls=calls,
        )
        adj = pf.compute_adjustments(state)
        self.assertLessEqual(adj["o1"], pf._MAX_ADJUST)
        self.assertGreaterEqual(adj["o1"], -pf._MAX_ADJUST)


class ApplyTests(unittest.TestCase):
    def test_writes_field_into_objectives(self):
        obj = {"id": "o1", "status": "planned"}
        state = _make_state(objectives=[obj])
        pf.apply(state)
        self.assertIn("feedback_priority_adjustment", obj)

    def test_field_is_float(self):
        obj = {"id": "o1", "status": "planned"}
        state = _make_state(objectives=[obj])
        pf.apply(state)
        self.assertIsInstance(obj["feedback_priority_adjustment"], float)

    def test_high_success_yields_positive(self):
        calls = [{"objective_id": "o1", "outcome": "accepted"} for _ in range(8)]
        obj = {"id": "o1", "status": "planned"}
        state = _make_state(objectives=[obj], calls=calls)
        pf.apply(state)
        self.assertGreater(obj["feedback_priority_adjustment"], 0.0)


import sys
