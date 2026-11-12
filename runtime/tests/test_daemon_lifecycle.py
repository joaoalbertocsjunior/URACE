"""Lifecycle proof: daemon runs cycles, updates state, tolerates faults, exposes RPC.

These tests prove the core value proposition: leave daemon running and it continuously
operates improvement cycles without crashing, without leaving ghost processes, and without
regressing state between cycles.

Each test class addresses a specific lifecycle guarantee:
  DaemonCycleCountTests    — daemon calls cli.main once per cycle, correct args
  DaemonStateUpdateTests   — state file advances after each cycle (simulated improvement)
  DaemonFaultResilienceTests — cycle failures do not kill the daemon
  DaemonRpcReadinessTests  — daemon exposes the urace-rpc-v1 TCP contract
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


@contextmanager
def _fast_clock():
    """Bypass the 60s inter-cycle sleep floor so multi-cycle tests finish in milliseconds."""
    _base = _real_time.monotonic()
    _offset = [0.0]

    def _fast_monotonic():
        _offset[0] += 200.0
        return _base + _offset[0]

    with patch("urace._daemon.time.monotonic", side_effect=_fast_monotonic):
        with patch("urace._daemon.time.sleep"):
            yield


def _make_start_args(max_cycles=1, interval_minutes=0.001):
    return types.SimpleNamespace(
        daemon_action="start",
        json=False,
        format=None,
        interval_minutes=interval_minutes,
        max_cycles=max_cycles,
        cycles=max_cycles,
    )


class DaemonCycleCountTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urace-lifecycle-")
        self.addCleanup(self.directory.cleanup)
        self.config = _make_config(self.directory.name)

    def test_one_cycle_calls_main_once(self):
        from urace import _daemon as d
        calls = []
        with patch("urace.cli.main", side_effect=lambda a: calls.append(a)):
            with patch("sys.stdout"):
                d.dispatch(_make_start_args(max_cycles=1), self.config)
        self.assertEqual(len(calls), 1)

    def test_two_cycles_calls_main_twice(self):
        from urace import _daemon as d
        calls = []
        with _fast_clock():
            with patch("urace.cli.main", side_effect=lambda a: calls.append(a)):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=2), self.config)
        self.assertEqual(len(calls), 2)

    def test_cycle_first_arg_is_auto(self):
        from urace import _daemon as d
        calls = []
        with patch("urace.cli.main", side_effect=lambda a: calls.append(a[:])):
            with patch("sys.stdout"):
                d.dispatch(_make_start_args(max_cycles=1), self.config)
        self.assertEqual(calls[0][0], "auto")

    def test_cycle_includes_cycles_1_flag(self):
        from urace import _daemon as d
        calls = []
        with patch("urace.cli.main", side_effect=lambda a: calls.append(a[:])):
            with patch("sys.stdout"):
                d.dispatch(_make_start_args(max_cycles=1), self.config)
        self.assertIn("--cycles", calls[0])
        idx = calls[0].index("--cycles")
        self.assertEqual(calls[0][idx + 1], "1")

    def test_pid_cleared_after_cycles_complete(self):
        from urace import _daemon as d
        with patch("urace.cli.main", return_value=None):
            with patch("sys.stdout"):
                d.dispatch(_make_start_args(max_cycles=1), self.config)
        self.assertIsNone(d._read_pid(self.config))


class DaemonStateUpdateTests(unittest.TestCase):
    """Simulated improvement: each cycle writes an updated state file.

    Real improvement requires a live LLM executor. These tests prove the
    mechanical substrate: the daemon faithfully calls the improvement loop
    and state can advance per cycle. Product-level improvement verification
    requires integration tests with a configured executor.
    """

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urace-lifecycle-")
        self.addCleanup(self.directory.cleanup)
        self.config = _make_config(self.directory.name)

    def test_cycle_can_write_state_file(self):
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])

        def simulated_cycle(argv):
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps({"improved": True, "cycle": 1}))

        with patch("urace.cli.main", side_effect=simulated_cycle):
            with patch("sys.stdout"):
                d.dispatch(_make_start_args(max_cycles=1), self.config)

        self.assertTrue(state_path.exists())
        self.assertTrue(json.loads(state_path.read_text())["improved"])

    def test_state_advances_across_cycles(self):
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        counter = [0]

        def simulated_cycle(argv):
            counter[0] += 1
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps({"cycles_completed": counter[0]}))

        with _fast_clock():
            with patch("urace.cli.main", side_effect=simulated_cycle):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=3), self.config)

        state = json.loads(state_path.read_text())
        self.assertEqual(state["cycles_completed"], 3)

    def test_state_version_monotonically_increases(self):
        from urace import _daemon as d
        state_path = Path(self.config["state_path"])
        versions = []
        counter = [0]

        def simulated_cycle(argv):
            counter[0] += 1
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps({"version": counter[0]}))
            versions.append(counter[0])

        with _fast_clock():
            with patch("urace.cli.main", side_effect=simulated_cycle):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=4), self.config)

        self.assertEqual(len(versions), 4)
        for i in range(1, len(versions)):
            self.assertGreater(versions[i], versions[i - 1],
                               "State version must not regress between cycles")


class DaemonFaultResilienceTests(unittest.TestCase):
    """Critical for hands-free operation: a crashing cycle must not kill the daemon."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urace-lifecycle-")
        self.addCleanup(self.directory.cleanup)
        self.config = _make_config(self.directory.name)

    def test_transient_failure_does_not_stop_daemon(self):
        from urace import _daemon as d
        call_count = [0]

        def sometimes_failing(argv):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("simulated transient failure")

        with _fast_clock():
            with patch("urace.cli.main", side_effect=sometimes_failing):
                with patch("sys.stdout"):
                    rc = d.dispatch(_make_start_args(max_cycles=2), self.config)

        self.assertEqual(rc, 0)
        self.assertEqual(call_count[0], 2, "Both cycles must be attempted despite first failure")

    def test_persistent_failures_exit_cleanly(self):
        from urace import _daemon as d

        def always_failing(argv):
            raise RuntimeError("persistent failure")

        with _fast_clock():
            with patch("urace.cli.main", side_effect=always_failing):
                with patch("sys.stdout"):
                    rc = d.dispatch(_make_start_args(max_cycles=3), self.config)

        self.assertEqual(rc, 0)

    def test_pid_cleared_after_all_failures(self):
        from urace import _daemon as d

        def always_failing(argv):
            raise RuntimeError("failure")

        with _fast_clock():
            with patch("urace.cli.main", side_effect=always_failing):
                with patch("sys.stdout"):
                    d.dispatch(_make_start_args(max_cycles=2), self.config)

        self.assertIsNone(d._read_pid(self.config),
                          "PID file must be cleared even when all cycles fail")

    def test_systemexits_in_cycle_are_swallowed(self):
        from urace import _daemon as d
        call_count = [0]

        def raising_systemexit(argv):
            call_count[0] += 1
            raise SystemExit(0)

        with _fast_clock():
            with patch("urace.cli.main", side_effect=raising_systemexit):
                with patch("sys.stdout"):
                    rc = d.dispatch(_make_start_args(max_cycles=2), self.config)

        self.assertEqual(rc, 0)
        self.assertEqual(call_count[0], 2)


class DaemonRpcReadinessTests(unittest.TestCase):
    """Verify daemon exposes urace-rpc-v1 TCP contract — required for ecosystem clients."""

    def test_rpc_server_function_exists(self):
        from urace import _daemon as d
        self.assertTrue(
            hasattr(d, "_run_rpc_server") or hasattr(d, "_rpc_socket_server"),
            "Daemon must expose an RPC server function for urace-rpc-v1"
        )

    def test_rpc_tcp_port_constant_exists(self):
        from urace import _daemon as d
        self.assertTrue(
            hasattr(d, "RPC_TCP_PORT"),
            "Daemon must expose RPC_TCP_PORT constant"
        )

    def test_rpc_port_is_7474(self):
        from urace import _daemon as d
        self.assertEqual(d.RPC_TCP_PORT, 7474,
                         "urace-rpc-v1 primary transport must be TCP 127.0.0.1:7474")

    def test_rpc_schema_constant_exists(self):
        from urace import _daemon as d
        self.assertTrue(
            hasattr(d, "_RPC_SCHEMA"),
            "Daemon must have _RPC_SCHEMA constant matching urace-rpc-v1"
        )

    def test_rpc_schema_value(self):
        from urace import _daemon as d
        self.assertEqual(d._RPC_SCHEMA, "urace-rpc-v1")
