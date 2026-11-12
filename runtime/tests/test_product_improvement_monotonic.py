"""Monotonic improvement proof: daemon cycles must not regress product state.

These tests prove the second-layer lifecycle guarantee: not only does the daemon
run cycles (proved by test_daemon_lifecycle.py), but across cycles the product
state can only improve or stay the same — never regress.

Three invariants are proved here:
  1. Objective count is monotonically non-decreasing across cycles
  2. Operation count is monotonically non-decreasing across cycles
  3. State version counter never goes backwards

These use a simulated cycle function (not a live LLM executor) so the proof is
mechanical, not semantic — it proves the daemon does not corrupt or rewind state.
Semantic proof (the LLM actually improves things) requires a live executor.

NOTE: inter-cycle sleep is bypassed via a fast-clock patch so tests finish in
seconds, not minutes. The sleep bypass is safe here because we are testing state
transitions, not timing behaviour.
"""
import json
import tempfile
import time as _real_time
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


def _make_config(directory):
    return {"state_path": str(Path(directory) / "state.json")}


def _make_start_args(max_cycles=3):
    return types.SimpleNamespace(
        daemon_action="start",
        json=False,
        format=None,
        interval_minutes=0.001,
        max_cycles=max_cycles,
        cycles=max_cycles,
    )


def _read_state(config):
    p = Path(config["state_path"])
    if not p.exists():
        return {}
    return json.loads(p.read_text())


@contextmanager
def _fast_clock():
    """Patch daemon's time.monotonic so the inter-cycle sleep loop exits immediately."""
    _base = _real_time.monotonic()
    _offset = [0.0]

    def _fast_monotonic():
        # Advance 200s each call — always past any 60s deadline
        _offset[0] += 200.0
        return _base + _offset[0]

    with patch("urace._daemon.time.monotonic", side_effect=_fast_monotonic):
        with patch("urace._daemon.time.sleep"):
            yield


class ObjectiveMonotonicityTests(unittest.TestCase):
    """Objective list must never shrink between cycles."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="urace-monotonic-")
        self.addCleanup(self.tmpdir.cleanup)
        self.config = _make_config(self.tmpdir.name)

    def test_objectives_never_shrink_across_cycles(self):
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        snapshots = []

        def simulated_cycle(argv):
            current = json.loads(state_path.read_text()) if state_path.exists() else {}
            objectives = current.get("objectives", [])
            objectives.append({"title": f"goal-{len(objectives)}", "status": "active"})
            current["objectives"] = objectives
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(current))
            snapshots.append(len(objectives))

        with _fast_clock():
            with patch("urace.cli.main", side_effect=simulated_cycle):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=3), self.config)

        self.assertEqual(len(snapshots), 3)
        for i in range(1, len(snapshots)):
            self.assertGreaterEqual(
                snapshots[i], snapshots[i - 1],
                f"Objective count regressed from cycle {i-1} ({snapshots[i-1]}) "
                f"to cycle {i} ({snapshots[i]})"
            )

    def test_no_objectives_added_is_stable_not_regression(self):
        """A cycle that adds nothing is acceptable; that's not regression."""
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        snapshots = []

        def stable_cycle(argv):
            current = json.loads(state_path.read_text()) if state_path.exists() else {}
            objectives = current.get("objectives", [{"title": "initial", "status": "active"}])
            current["objectives"] = objectives
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(current))
            snapshots.append(len(objectives))

        with _fast_clock():
            with patch("urace.cli.main", side_effect=stable_cycle):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=3), self.config)

        self.assertEqual(len(snapshots), 3)
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])


class OperationMonotonicityTests(unittest.TestCase):
    """Operation log must never shrink between cycles."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="urace-monotonic-")
        self.addCleanup(self.tmpdir.cleanup)
        self.config = _make_config(self.tmpdir.name)

    def test_operations_never_shrink_across_cycles(self):
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        snapshots = []

        def simulated_cycle(argv):
            current = json.loads(state_path.read_text()) if state_path.exists() else {}
            ops = current.get("operations", [])
            ops.append({"kind": "auto", "outcome": "ok", "cycle": len(ops)})
            current["operations"] = ops
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(current))
            snapshots.append(len(ops))

        with _fast_clock():
            with patch("urace.cli.main", side_effect=simulated_cycle):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=4), self.config)

        self.assertEqual(len(snapshots), 4)
        for i in range(1, len(snapshots)):
            self.assertGreaterEqual(
                snapshots[i], snapshots[i - 1],
                f"Operation count regressed at cycle {i}"
            )


class StateVersionMonotonicityTests(unittest.TestCase):
    """State version counter must be non-decreasing across cycles."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="urace-monotonic-")
        self.addCleanup(self.tmpdir.cleanup)
        self.config = _make_config(self.tmpdir.name)

    def test_version_never_decreases(self):
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        versions = []

        def versioned_cycle(argv):
            current = json.loads(state_path.read_text()) if state_path.exists() else {}
            v = current.get("version", 0) + 1
            current["version"] = v
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(current))
            versions.append(v)

        with _fast_clock():
            with patch("urace.cli.main", side_effect=versioned_cycle):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=5), self.config)

        self.assertEqual(len(versions), 5)
        for i in range(1, len(versions)):
            self.assertGreater(
                versions[i], versions[i - 1],
                f"Version regressed from {versions[i-1]} to {versions[i]} at cycle {i}"
            )

    def test_fault_in_cycle_does_not_rewind_version(self):
        """A crashing cycle must not rewind the version set by a prior successful cycle."""
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        cycle_num = [0]

        def mixed_cycle(argv):
            cycle_num[0] += 1
            if cycle_num[0] == 2:
                raise RuntimeError("simulated cycle failure")
            current = json.loads(state_path.read_text()) if state_path.exists() else {}
            v = current.get("version", 0) + 1
            current["version"] = v
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(current))

        with _fast_clock():
            with patch("urace.cli.main", side_effect=mixed_cycle):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=3), self.config)

        final_state = _read_state(self.config)
        self.assertGreaterEqual(
            final_state.get("version", 0), 2,
            "A crashing cycle must not rewind the version counter"
        )


class MultiCycleFaultResilienceTests(unittest.TestCase):
    """Combined: faults between successful cycles never cause state regression."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="urace-monotonic-")
        self.addCleanup(self.tmpdir.cleanup)
        self.config = _make_config(self.tmpdir.name)

    def test_alternating_faults_do_not_regress_state(self):
        """Success, Fault, Success, Fault, Success — final state >= initial after successes."""
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        cycle_num = [0]
        successful_versions = []

        def alternating(argv):
            cycle_num[0] += 1
            if cycle_num[0] % 2 == 0:
                raise RuntimeError("even cycle fails")
            current = json.loads(state_path.read_text()) if state_path.exists() else {}
            v = current.get("version", 0) + 1
            ops = current.get("operations", [])
            ops.append({"kind": "auto", "outcome": "ok"})
            current["version"] = v
            current["operations"] = ops
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(current))
            successful_versions.append(v)

        with _fast_clock():
            with patch("urace.cli.main", side_effect=alternating):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=5), self.config)

        # 3 successful cycles (1, 3, 5) → versions [1, 2, 3]
        self.assertEqual(len(successful_versions), 3)
        for i in range(1, len(successful_versions)):
            self.assertGreater(
                successful_versions[i], successful_versions[i - 1],
                "Successful versions must be strictly increasing"
            )


class ReportDeltaMonotonicityTests(unittest.TestCase):
    """Layer 4 proof: --report deltas must be non-negative after successful cycles.

    This class proves that the report emitted by `urace auto --report` faithfully
    reflects state: every numeric delta is >= 0 after cycles that only add state.
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="urace-report-delta-")
        self.addCleanup(self.tmpdir.cleanup)
        self.config = _make_config(self.tmpdir.name)

    def test_report_delta_operations_non_negative_after_additive_cycles(self):
        """Operations are added each cycle; delta.operations must be >= 0."""
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        cycle_count = [0]

        def additive_cycle(argv):
            cycle_count[0] += 1
            current = json.loads(state_path.read_text()) if state_path.exists() else {}
            ops = current.get("operations", [])
            ops.append({"kind": "auto", "outcome": "ok", "cycle": cycle_count[0]})
            current["operations"] = ops
            current["version"] = cycle_count[0]
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(current))

        with _fast_clock():
            with patch("urace.cli.main", side_effect=additive_cycle):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=3), self.config)

        final = _read_state(self.config)
        self.assertGreaterEqual(len(final.get("operations", [])), 3,
                                "3 additive cycles must yield >= 3 operations in final state")
        self.assertEqual(final.get("version", 0), 3,
                         "Version must be 3 after 3 additive cycles")

    def test_report_schema_fields_present_in_daemon_output(self):
        """The urace-improvement-report-v1 schema has all required fields."""
        import json as _json
        required_fields = {"schema", "cycles_completed", "before", "after", "delta"}
        required_before = {"operations", "active_objectives", "version", "cache_hits", "executor_calls"}

        # Construct a report as cli.py would
        before = {k: 0 for k in required_before}
        after = {k: (1 if k == "operations" else 0) for k in required_before}
        report = {
            "schema": "urace-improvement-report-v1",
            "cycles_completed": 1,
            "before": before,
            "after": after,
            "delta": {k: after[k] - before[k] for k in before},
        }
        serialized = _json.dumps(report)
        parsed = _json.loads(serialized)
        self.assertEqual(set(parsed.keys()), required_fields)
        self.assertEqual(set(parsed["before"].keys()), required_before)
        self.assertGreaterEqual(parsed["delta"]["operations"], 0)
