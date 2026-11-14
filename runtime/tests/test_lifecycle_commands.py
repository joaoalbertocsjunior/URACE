"""Tests for start/stop/shell/dashboard command parsing and routing."""
import argparse
import threading
import unittest
from unittest.mock import patch, MagicMock


def _reset_parser_cache():
    """Force a fresh dispatch_parser() on next call (parser is per-thread cached)."""
    import urace.cli_parser as _cp
    _cp._DISPATCH_PARSERS = threading.local()


class TestLifecycleCommandParsing(unittest.TestCase):
    """Parser-level tests: verify commands are registered and produce correct args."""

    def setUp(self):
        _reset_parser_cache()

    def _parse(self, argv):
        from urace.cli_parser import dispatch_parser
        p = dispatch_parser()
        args, _ = p.parse_known_args(argv)
        return args

    def test_start_parses(self):
        args = self._parse(['start'])
        self.assertEqual(args.command, 'start')

    def test_stop_parses(self):
        args = self._parse(['stop'])
        self.assertEqual(args.command, 'stop')

    def test_shell_parses(self):
        args = self._parse(['shell'])
        self.assertEqual(args.command, 'shell')

    def test_dashboard_parses(self):
        args = self._parse(['dashboard'])
        self.assertEqual(args.command, 'dashboard')

    def test_start_accepts_interval_minutes(self):
        args = self._parse(['start', '--interval-minutes', '15'])
        self.assertEqual(args.interval_minutes, 15.0)

    def test_stop_accepts_json_flag(self):
        args = self._parse(['stop', '--json'])
        # --json maps format to "json"
        self.assertEqual(getattr(args, 'format', None), 'json')


class TestShellHandler(unittest.TestCase):
    """Integration-lite: verify main() routes shell/dashboard to the correct entry points."""

    def setUp(self):
        _reset_parser_cache()

    def _make_config(self, tmp_path=None):
        import tempfile, os
        d = tmp_path or tempfile.mkdtemp()
        return {
            'state_path': os.path.join(d, 'state.json'),
            'product_name': 'test',
        }

    def test_shell_handler_calls_run_shell(self):
        from urace.cli import main
        cfg = self._make_config()
        with patch('urace.shell.run_shell', return_value=0) as mock_shell, \
             patch('urace._common.load_config', return_value=cfg), \
             patch('urace._common.load_state_for_read', return_value=None), \
             patch('urace.preflight.hints', return_value=[]):
            try:
                rc = main(['shell'])
            except (SystemExit, Exception):
                pass
        mock_shell.assert_called_once()

    def test_dashboard_handler_calls_tui_launch(self):
        from urace.cli import main
        cfg = self._make_config()
        with patch('urace.tui.launch', return_value=0) as mock_tui, \
             patch('urace._common.load_config', return_value=cfg), \
             patch('urace._common.load_state_for_read', return_value=None), \
             patch('urace.preflight.hints', return_value=[]):
            try:
                rc = main(['dashboard'])
            except (SystemExit, Exception):
                pass
        mock_tui.assert_called_once()


class TestStartStopHandlers(unittest.TestCase):
    """Verify start/stop dispatch daemon actions correctly."""

    def setUp(self):
        _reset_parser_cache()

    def test_stop_handler_invokes_daemon_stop(self):
        from urace._daemon import _handle_rpc_client
        import json
        # Test stop via RPC handler (most direct)
        data = (json.dumps({'method': 'stop'}) + '\n').encode()
        conn = MagicMock()
        conn.recv.side_effect = [data, b'']
        sent = []
        conn.sendall.side_effect = lambda b: sent.append(json.loads(b.decode().strip()))
        stopped = [False]
        _handle_rpc_client(conn, {}, stopped)
        self.assertTrue(stopped[0])
        self.assertTrue(len(sent) > 0)
        self.assertEqual(sent[0].get('status'), 'stopping')

    def test_daemon_dispatch_stop_action(self):
        """_daemon.dispatch with stop action sends SIGTERM when pid not running."""
        from urace import _daemon
        args = argparse.Namespace(
            command='daemon', daemon_action='stop',
            json=True, format='json',
        )
        with patch.object(_daemon, '_read_pid', return_value=None):
            rc = _daemon.dispatch(args, {})
        # pid=None → "not_running" response, return 0
        self.assertEqual(rc, 0)

    def test_daemon_dispatch_status_action(self):
        from urace import _daemon
        args = argparse.Namespace(
            command='daemon', daemon_action='status',
            json=True, format='json',
        )
        with patch.object(_daemon, '_read_pid', return_value=None), \
             patch.object(_daemon, '_is_running', return_value=False):
            rc = _daemon.dispatch(args, {})
        self.assertEqual(rc, 0)
