"""Tests for urace start routing and compact banner output."""
import contextlib, copy, io, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urace import cli, bootstrap, _common
from helpers import patch_config_path


class StartRoutingTests(unittest.TestCase):
    """urace start must NOT be intercepted by SD alias table."""

    def test_start_not_aliased_to_resume(self):
        """'start' in _KNOWN_TOP_COMMANDS must take priority over _SD_TRUE_EXACT alias."""
        from urace.cli import _preprocess_args
        result = _preprocess_args(['start'])
        self.assertEqual(result, ['start'], "start must route to itself, not resume")

    def test_stop_still_routes_via_sd(self):
        """'stop' is both a known command and SD alias — known command takes priority."""
        from urace.cli import _preprocess_args
        result = _preprocess_args(['stop'])
        # stop is a known top command → passes through as-is
        self.assertEqual(result, ['stop'])

    def test_resume_still_works(self):
        """'resume' as explicit command still routes to itself."""
        from urace.cli import _preprocess_args
        result = _preprocess_args(['resume'])
        self.assertEqual(result, ['resume'])


class AutoCompleteQuietTests(unittest.TestCase):
    """auto_complete with _quiet=True must not print JSON."""

    def _make_config(self, root):
        config = copy.deepcopy(cli.load_config())
        config.pop('active_product', None)
        config['state_path'] = str(Path(root) / 'state.json')
        config_path = Path(root) / 'config.json'
        config_path.write_text(json.dumps(config))
        return config, config_path

    def _mock_exchange(self):
        mock_exc = MagicMock()
        mock_exc.return_value.identity.return_value = {'peer_id': 'test-peer'}
        mock_exc.return_value.load.return_value = {}
        return mock_exc

    def _mock_nat(self):
        mock_nc = MagicMock()
        mock_nc.check_node_capability.return_value = {
            'nat_type': 'cone', 'public_ip': '1.2.3.4',
            'upnp_available': False, 'can_relay': False,
            'recommended_roles': ['consumer'],
            'recommended_network_mode': 'hybrid',
        }
        return mock_nc

    def test_quiet_suppresses_json_output(self):
        with tempfile.TemporaryDirectory() as root:
            config, config_path = self._make_config(root)
            buf = io.StringIO()
            with patch_config_path(config_path), \
                 patch('urace.peer_exchange.Exchange', self._mock_exchange()), \
                 patch('urace.nat_check.check_node_capability',
                       self._mock_nat().check_node_capability), \
                 patch.object(cli, 'write_stable_snapshot'), \
                 patch.object(cli, 'write_runtime_snapshot'), \
                 patch('shutil.which', return_value=None), \
                 contextlib.redirect_stdout(buf):
                result = bootstrap.auto_complete(cli, config, _quiet=True)
            output = buf.getvalue()
            self.assertNotIn('"status"', output, "quiet=True must suppress JSON blob")
            self.assertIsInstance(result, dict)
            self.assertIn('status', result)

    def test_non_quiet_prints_json(self):
        with tempfile.TemporaryDirectory() as root:
            config, config_path = self._make_config(root)
            buf = io.StringIO()
            with patch_config_path(config_path), \
                 patch('urace.peer_exchange.Exchange', self._mock_exchange()), \
                 patch('urace.nat_check.check_node_capability',
                       self._mock_nat().check_node_capability), \
                 patch.object(cli, 'write_stable_snapshot'), \
                 patch.object(cli, 'write_runtime_snapshot'), \
                 patch('shutil.which', return_value=None), \
                 contextlib.redirect_stdout(buf):
                result = bootstrap.auto_complete(cli, config, _quiet=False)
            output = buf.getvalue()
            self.assertIn('"status"', output, "quiet=False must print JSON blob")


class StartBannerTests(unittest.TestCase):
    """urace start prints compact banner, not verbose auto_complete JSON."""

    def test_start_prints_compact_banner_not_verbose_json(self):
        with tempfile.TemporaryDirectory() as root:
            config = copy.deepcopy(cli.load_config())
            config.pop('active_product', None)
            config['state_path'] = str(Path(root) / 'state.json')
            config_path = Path(root) / 'config.json'
            config_path.write_text(json.dumps(config))

            buf = io.StringIO()
            fake_init_result = {
                'status': 'ready',
                'executor_providers': 0,
                'steps': [
                    {'step': 'nat_detection', 'status': 'ok', 'nat_type': 'cone',
                     'public_ip': '1.2.3.4', 'upnp_available': False,
                     'recommended_roles': ['consumer', 'creator'],
                     'recommended_network_mode': 'hybrid'},
                    {'step': 'doctor', 'status': 'WARN'},
                ],
                'network_guide': {'scenario': 'localhost_run', 'label': 'localhost.run'},
            }
            with patch_config_path(config_path), \
                 patch('urace.bootstrap.auto_complete', return_value=fake_init_result), \
                 patch('urace._daemon.dispatch', return_value=0), \
                 patch.object(cli, 'write_stable_snapshot'), \
                 patch.object(cli, 'write_runtime_snapshot'), \
                 contextlib.redirect_stdout(buf):
                cli.main(['start'])
            output = buf.getvalue()
            # Banner must contain key fields
            self.assertIn('starting', output)
            self.assertIn('nat:', output)
            self.assertIn('roles:', output)
            self.assertIn('tunnel:', output)
            # Must NOT contain the full JSON auto_complete blob
            self.assertNotIn('"executor_providers"', output)
            self.assertNotIn('"auto_detected_providers"', output)
