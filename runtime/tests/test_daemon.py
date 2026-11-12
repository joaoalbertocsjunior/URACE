"""Tests for urace._daemon — pid management and dispatch actions."""
import json
import os
import signal
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_config(directory):
    return {"state_path": str(Path(directory) / "state.json")}


def _make_args(action="status", *, as_json=False, interval_minutes=30.0, max_cycles=0):
    args = types.SimpleNamespace(
        daemon_action=action,
        json=as_json,
        format=None,
        interval_minutes=interval_minutes,
        max_cycles=max_cycles,
        cycles=max_cycles,
    )
    return args


class PidFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urace-daemon-test-")
        self.addCleanup(self.directory.cleanup)
        self.config = _make_config(self.directory.name)

    def test_read_pid_returns_none_when_no_file(self):
        from urace import _daemon as d
        self.assertIsNone(d._read_pid(self.config))

    def test_write_and_read_pid_roundtrip(self):
        from urace import _daemon as d
        with patch("os.getpid", return_value=12345):
            d._write_pid(self.config)
        self.assertEqual(d._read_pid(self.config), 12345)

    def test_clear_pid_removes_file(self):
        from urace import _daemon as d
        with patch("os.getpid", return_value=99999):
            d._write_pid(self.config)
        self.assertIsNotNone(d._read_pid(self.config))
        d._clear_pid(self.config)
        self.assertIsNone(d._read_pid(self.config))

    def test_clear_pid_is_idempotent(self):
        from urace import _daemon as d
        d._clear_pid(self.config)
        d._clear_pid(self.config)

    def test_read_pid_returns_none_on_corrupt_file(self):
        from urace import _daemon as d
        pid_path = d._pid_path(self.config)
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text("not-a-number")
        self.assertIsNone(d._read_pid(self.config))


class IsRunningTests(unittest.TestCase):
    def test_returns_true_when_process_exists(self):
        from urace import _daemon as d
        with patch("os.kill", return_value=None):
            self.assertTrue(d._is_running(12345))

    def test_returns_false_when_process_missing(self):
        from urace import _daemon as d
        with patch("os.kill", side_effect=OSError):
            self.assertFalse(d._is_running(99999))


class DispatchStatusTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urace-daemon-test-")
        self.addCleanup(self.directory.cleanup)
        self.config = _make_config(self.directory.name)

    def test_status_stopped_returns_zero(self):
        from urace import _daemon as d
        rc = d.dispatch(_make_args("status"), self.config)
        self.assertEqual(rc, 0)

    def test_status_stopped_human_output(self):
        from urace import _daemon as d
        import io
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            d.dispatch(_make_args("status"), self.config)
            self.assertIn("stopped", mock_out.getvalue().lower())

    def test_status_stopped_json_output(self):
        from urace import _daemon as d
        import io
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            d.dispatch(_make_args("status", as_json=True), self.config)
            data = json.loads(mock_out.getvalue())
        self.assertEqual(data["status"], "stopped")
        self.assertIsNone(data["pid"])

    def test_status_running_json_output(self):
        from urace import _daemon as d
        import io
        with patch("os.getpid", return_value=55555):
            d._write_pid(self.config)
        with patch("os.kill", return_value=None):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                d.dispatch(_make_args("status", as_json=True), self.config)
                data = json.loads(mock_out.getvalue())
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["pid"], 55555)


class DispatchStopTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urace-daemon-test-")
        self.addCleanup(self.directory.cleanup)
        self.config = _make_config(self.directory.name)

    def test_stop_when_not_running_returns_zero(self):
        from urace import _daemon as d
        rc = d.dispatch(_make_args("stop"), self.config)
        self.assertEqual(rc, 0)

    def test_stop_when_not_running_json(self):
        from urace import _daemon as d
        import io
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            d.dispatch(_make_args("stop", as_json=True), self.config)
            data = json.loads(mock_out.getvalue())
        self.assertEqual(data["status"], "not_running")

    def test_stop_running_sends_sigterm(self):
        from urace import _daemon as d
        with patch("os.getpid", return_value=77777):
            d._write_pid(self.config)
        sent = []
        def fake_kill(pid, sig):
            sent.append((pid, sig))
        with patch("os.kill", side_effect=lambda pid, sig: None if sig == 0 else sent.append((pid, sig))):
            with patch("os.kill") as mock_kill:
                mock_kill.return_value = None
                rc = d.dispatch(_make_args("stop"), self.config)
        self.assertEqual(rc, 0)

    def test_stop_oserror_returns_one(self):
        from urace import _daemon as d
        with patch("os.getpid", return_value=88888):
            d._write_pid(self.config)
        def kill_side_effect(pid, sig):
            if sig == 0:
                return None
            raise OSError("permission denied")
        with patch("os.kill", side_effect=kill_side_effect):
            rc = d.dispatch(_make_args("stop"), self.config)
        self.assertEqual(rc, 1)


class DispatchStartTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="urace-daemon-test-")
        self.addCleanup(self.directory.cleanup)
        self.config = _make_config(self.directory.name)

    def test_start_already_running_returns_one(self):
        from urace import _daemon as d
        with patch("os.getpid", return_value=22222):
            d._write_pid(self.config)
        with patch("os.kill", return_value=None):
            rc = d.dispatch(_make_args("start"), self.config)
        self.assertEqual(rc, 1)

    def test_start_already_running_json_message(self):
        from urace import _daemon as d
        import io
        with patch("os.getpid", return_value=22222):
            d._write_pid(self.config)
        with patch("os.kill", return_value=None):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                d.dispatch(_make_args("start", as_json=True), self.config)
                data = json.loads(mock_out.getvalue())
        self.assertEqual(data["status"], "already_running")

    def test_start_max_cycles_one_runs_and_exits(self):
        from urace import _daemon as d
        import io
        cycle_calls = []
        def fake_cli_main(argv):
            cycle_calls.append(argv)
        with patch("urace.cli.main", side_effect=fake_cli_main):
            with patch("os.getpid", return_value=33333):
                with patch("sys.stdout", new_callable=io.StringIO):
                    rc = d.dispatch(_make_args("start", max_cycles=1), self.config)
        self.assertEqual(rc, 0)
        self.assertEqual(len(cycle_calls), 1)

    def test_start_clears_pid_on_exit(self):
        from urace import _daemon as d
        with patch("urace.cli.main", return_value=None):
            with patch("os.getpid", return_value=44444):
                with patch("sys.stdout"):
                    d.dispatch(_make_args("start", max_cycles=1), self.config)
        self.assertIsNone(d._read_pid(self.config))

    def test_start_json_emits_started_event(self):
        from urace import _daemon as d
        import io
        lines = []
        class CapturingIO(io.StringIO):
            def write(self, s):
                lines.append(s)
                return super().write(s)
            def flush(self):
                pass
        with patch("urace.cli.main", return_value=None):
            with patch("os.getpid", return_value=55555):
                with patch("sys.stdout", new_callable=CapturingIO):
                    d.dispatch(_make_args("start", as_json=True, max_cycles=1), self.config)
        full = "".join(lines)
        events = [json.loads(line) for line in full.splitlines() if line.strip()]
        statuses = [e.get("status") or e.get("event") for e in events]
        self.assertIn("started", statuses)

    def test_start_cycle_error_does_not_crash(self):
        from urace import _daemon as d
        def raising_main(argv):
            raise RuntimeError("simulated cycle error")
        with patch("urace.cli.main", side_effect=raising_main):
            with patch("os.getpid", return_value=66666):
                with patch("sys.stdout"):
                    rc = d.dispatch(_make_args("start", max_cycles=1), self.config)
        self.assertEqual(rc, 0)
