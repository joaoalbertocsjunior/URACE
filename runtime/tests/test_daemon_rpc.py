import json
import unittest
from unittest.mock import MagicMock, patch


def _call_handler(msg: dict, config=None):
    """Invoke _handle_rpc_client with a fake connection carrying msg."""
    from urace._daemon import _handle_rpc_client
    data = (json.dumps(msg) + '\n').encode()
    conn = MagicMock()
    conn.recv.side_effect = [data, b'']
    sent = []
    conn.sendall.side_effect = lambda b: sent.append(json.loads(b.decode().strip()))
    stopped = [False]
    _handle_rpc_client(conn, config or {}, stopped)
    return sent[0] if sent else None, stopped


class TestDaemonRPCPing(unittest.TestCase):
    def test_ping(self):
        r, _ = _call_handler({'method': 'ping'})
        self.assertIsNotNone(r)
        self.assertTrue(r.get('pong'))

    def test_ping_schema(self):
        r, _ = _call_handler({'method': 'ping'})
        self.assertEqual(r.get('schema'), 'urace-rpc-v1')


class TestDaemonRPCUnknown(unittest.TestCase):
    def test_unknown_method_returns_error(self):
        r, _ = _call_handler({'method': 'bogus_xyz'})
        self.assertIsNotNone(r)
        self.assertIn('error', r)

    def test_empty_method_returns_error(self):
        r, _ = _call_handler({'method': ''})
        self.assertIn('error', r)


class TestDaemonRPCStop(unittest.TestCase):
    def test_stop_sets_stopped_flag(self):
        _, stopped = _call_handler({'method': 'stop'})
        self.assertTrue(stopped[0])

    def test_stop_response_schema(self):
        r, _ = _call_handler({'method': 'stop'})
        self.assertIsNotNone(r)
        self.assertEqual(r.get('schema'), 'urace-rpc-v1')
        self.assertEqual(r.get('status'), 'stopping')


class TestDaemonRPCStatus(unittest.TestCase):
    def test_status_returns_schema(self):
        with patch('urace._daemon._read_pid', return_value=None), \
             patch('urace._daemon._is_running', return_value=False):
            r, _ = _call_handler({'method': 'status'})
        self.assertIsNotNone(r)
        self.assertEqual(r.get('schema'), 'urace-rpc-v1')
        self.assertIn(r.get('status'), ('running', 'stopped'))


class TestDaemonRPCDispatch(unittest.TestCase):
    def test_dispatch_output_key_present(self):
        import io, contextlib

        def _fake_main(argv):
            print(json.dumps({'status': 'ok', 'argv': argv}))
            return 0

        with patch('urace.cli.main', side_effect=_fake_main):
            r, _ = _call_handler({'method': 'dispatch', 'argv': ['status']})
        self.assertIsNotNone(r)
        self.assertIn('output', r)

    def test_dispatch_error_still_returns_output_key(self):
        def _bad_main(argv):
            raise RuntimeError('simulated failure')

        with patch('urace.cli.main', side_effect=_bad_main):
            r, _ = _call_handler({'method': 'dispatch', 'argv': ['status']})
        self.assertIsNotNone(r)
        # On exception the handler should still return a response with 'error'.
        self.assertIn('error', r)

    def test_dispatch_empty_argv(self):
        def _noop_main(argv):
            return 0

        with patch('urace.cli.main', side_effect=_noop_main):
            r, _ = _call_handler({'method': 'dispatch', 'argv': []})
        self.assertIsNotNone(r)


class TestDaemonRPCEvents(unittest.TestCase):
    def test_events_output_key_present(self):
        def _fake_main(argv):
            print(json.dumps([]))
            return 0

        with patch('urace.cli.main', side_effect=_fake_main):
            r, _ = _call_handler({'method': 'events'})
        self.assertIsNotNone(r)
        self.assertIn('output', r)

    def test_events_default_limit(self):
        """Verify limit=20 is used when omitted."""
        called_with = []

        def _capturing_main(argv):
            called_with.extend(argv)
            print(json.dumps([]))
            return 0

        with patch('urace.cli.main', side_effect=_capturing_main):
            _call_handler({'method': 'events'})
        self.assertIn('20', called_with)

    def test_events_custom_limit(self):
        called_with = []

        def _capturing_main(argv):
            called_with.extend(argv)
            print(json.dumps([]))
            return 0

        with patch('urace.cli.main', side_effect=_capturing_main):
            _call_handler({'method': 'events', 'limit': 5})
        self.assertIn('5', called_with)
