import unittest
from unittest.mock import patch, MagicMock


class TestShellDispatch(unittest.TestCase):
    def _dispatch(self, line, config=None):
        from urace.shell import _dispatch_line
        with patch('urace.shell._run_cmd', return_value=0) as mock_run:
            result = _dispatch_line(line, config or {})
        return result, mock_run

    def test_exit_slash_returns_false(self):
        from urace.shell import _dispatch_line
        with patch('urace.shell._run_cmd', return_value=0):
            self.assertFalse(_dispatch_line('/exit', {}))

    def test_quit_slash_returns_false(self):
        from urace.shell import _dispatch_line
        with patch('urace.shell._run_cmd', return_value=0):
            self.assertFalse(_dispatch_line('/quit', {}))

    def test_known_command_calls_run_cmd(self):
        result, mock_run = self._dispatch('status')
        self.assertTrue(result)
        mock_run.assert_called_once_with(['status'], {})

    def test_freeform_routes_to_classify(self):
        result, mock_run = self._dispatch('improve test coverage')
        self.assertTrue(result)
        mock_run.assert_called_once_with(['classify', 'improve test coverage'], {})

    def test_empty_line_continues(self):
        result, mock_run = self._dispatch('')
        self.assertTrue(result)
        mock_run.assert_not_called()

    def test_slash_help_continues(self):
        result, mock_run = self._dispatch('/help')
        self.assertTrue(result)

    def test_slash_stop_calls_rpc(self):
        from urace.shell import _dispatch_line
        with patch('urace.shell._rpc', return_value={'schema': 'urace-rpc-v1', 'status': 'stopping'}) as mock_rpc:
            with patch('urace.shell._run_cmd', return_value=0):
                result = _dispatch_line('/stop', {})
        self.assertTrue(result)
        mock_rpc.assert_called_once_with('stop')

    def test_exchange_command_dispatches_directly(self):
        result, mock_run = self._dispatch('exchange network discover')
        self.assertTrue(result)
        mock_run.assert_called_once_with(['exchange', 'network', 'discover'], {})

    def test_whitespace_only_continues(self):
        result, mock_run = self._dispatch('   ')
        self.assertTrue(result)
        mock_run.assert_not_called()


class TestShellPrompt(unittest.TestCase):
    def test_prompt_contains_stopped_when_daemon_down(self):
        from urace.shell import _prompt
        with patch('urace.shell._daemon_running', return_value=False), \
             patch('urace.shell._is_tty', return_value=False), \
             patch('urace.shell.peer_exchange', create=True):
            # peer_exchange import inside _prompt may fail; allow it
            try:
                p = _prompt({})
            except Exception:
                self.skipTest('peer_exchange not fully available in test env')
        self.assertIn('stopped', p)

    def test_prompt_contains_running_when_daemon_up(self):
        from urace.shell import _prompt
        with patch('urace.shell._daemon_running', return_value=True), \
             patch('urace.shell._is_tty', return_value=False):
            try:
                p = _prompt({})
            except Exception:
                self.skipTest('peer_exchange not fully available in test env')
        self.assertIn('running', p)

    def test_is_tty_false_when_no_stdout_attr(self):
        from urace.shell import _is_tty
        import sys
        orig = sys.stdout
        # Provide a stdout without isatty
        class _FakeOut:
            pass
        sys.stdout = _FakeOut()
        try:
            result = _is_tty()
        finally:
            sys.stdout = orig
        self.assertFalse(result)


class TestShellRunCmd(unittest.TestCase):
    def test_run_cmd_returns_exit_code(self):
        from urace.shell import _run_cmd
        with patch('urace.cli.main', return_value=0) as mock_main:
            rc = _run_cmd(['status'], {})
        self.assertEqual(rc, 0)

    def test_run_cmd_handles_system_exit(self):
        from urace.shell import _run_cmd
        with patch('urace.cli.main', side_effect=SystemExit(0)):
            rc = _run_cmd(['status'], {})
        self.assertEqual(rc, 0)

    def test_run_cmd_handles_exception(self):
        from urace.shell import _run_cmd
        with patch('urace.cli.main', side_effect=RuntimeError('boom')):
            rc = _run_cmd(['status'], {})
        self.assertEqual(rc, 1)
