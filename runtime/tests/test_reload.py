"""Tests for urace reload command and daemon SIGHUP handler."""
import contextlib, copy, io, json, os, signal, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urace import cli, _daemon
from helpers import patch_config_path


class ReloadCommandTests(unittest.TestCase):

    def test_reload_no_daemon(self):
        """reload with no running daemon prints informative message, returns 0."""
        with tempfile.TemporaryDirectory() as root:
            config = copy.deepcopy(cli.load_config())
            config['state_path'] = str(Path(root) / 'state.json')
            config_path = Path(root) / 'config.json'
            config_path.write_text(json.dumps(config))
            buf = io.StringIO()
            with patch_config_path(config_path), \
                 patch('urace._daemon._read_pid', return_value=None), \
                 contextlib.redirect_stdout(buf):
                code = cli.main(['reload'])
            self.assertEqual(code, 0)
            output = buf.getvalue()
            self.assertTrue(
                'no daemon' in output.lower() or 'no_daemon' in output.lower(),
                f"Expected 'no daemon' in output, got: {output!r}"
            )

    def test_reload_sends_sighup(self):
        """reload sends SIGHUP to daemon pid."""
        with tempfile.TemporaryDirectory() as root:
            config = copy.deepcopy(cli.load_config())
            config['state_path'] = str(Path(root) / 'state.json')
            config_path = Path(root) / 'config.json'
            config_path.write_text(json.dumps(config))
            sent = []
            with patch_config_path(config_path), \
                 patch('urace._daemon._read_pid', return_value=12345), \
                 patch('urace._daemon._is_running', return_value=True), \
                 patch('os.kill', side_effect=lambda pid, sig: sent.append((pid, sig))), \
                 contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(['reload'])
            self.assertEqual(code, 0)
            self.assertEqual(len(sent), 1)
            self.assertEqual(sent[0][0], 12345)
            self.assertEqual(sent[0][1], signal.SIGHUP)

    def test_reload_json_output(self):
        """reload --format json returns parseable JSON."""
        with tempfile.TemporaryDirectory() as root:
            config = copy.deepcopy(cli.load_config())
            config['state_path'] = str(Path(root) / 'state.json')
            config_path = Path(root) / 'config.json'
            config_path.write_text(json.dumps(config))
            buf = io.StringIO()
            with patch_config_path(config_path), \
                 patch('urace._daemon._read_pid', return_value=None), \
                 contextlib.redirect_stdout(buf):
                cli.main(['reload', '--format', 'json'])
            result = json.loads(buf.getvalue())
            self.assertIn('status', result)


class ConfigSchemaTests(unittest.TestCase):

    def test_network_section_in_default_config(self):
        """Default config.json contains network section with expected keys."""
        config = cli.load_config()
        network = config.get('network', {})
        self.assertIn('enabled', network)
        self.assertIn('mode', network)
        self.assertIn('tunnel', network)

    def test_sources_section_in_default_config(self):
        """Default config.json contains sources list."""
        config = cli.load_config()
        self.assertIn('sources', config)
        self.assertIsInstance(config['sources'], list)

    def test_api_section_in_default_config(self):
        """Default config.json contains api section."""
        config = cli.load_config()
        api = config.get('api', {})
        self.assertIn('mcp', api)
        self.assertIn('a2a', api)

    def test_rules_section_in_default_config(self):
        """Default config.json contains rules list."""
        config = cli.load_config()
        self.assertIn('rules', config)
        self.assertIsInstance(config['rules'], list)
