import unittest
from unittest.mock import patch
from urace.tunnel_server import _parse_cloudflare_url, _parse_localhost_run_url, TunnelHandle

class TestTunnelParsers(unittest.TestCase):
    def test_cloudflare_url_extracted(self):
        line = '2024-01-01T00:00:00Z INF | https://abc-def-123.trycloudflare.com |'
        self.assertEqual(_parse_cloudflare_url(line), 'https://abc-def-123.trycloudflare.com')

    def test_localhost_run_url_extracted(self):
        line = 'https://abc123.lhr.life tunneled with tls termination'
        self.assertEqual(_parse_localhost_run_url(line), 'https://abc123.lhr.life')

    def test_localhost_run_subdomain_url_extracted(self):
        line = '290d12c1b998a5.app.lhr.life tunneled with tls termination, https://290d12c1b998a5.app.lhr.life'
        self.assertEqual(_parse_localhost_run_url(line), 'https://290d12c1b998a5.app.lhr.life')

    def test_admin_localhost_run_not_matched(self):
        line = 'To set up and manage custom domains go to https://admin.localhost.run/'
        self.assertIsNone(_parse_localhost_run_url(line))

    def test_no_match_returns_none(self):
        self.assertIsNone(_parse_cloudflare_url('some random line'))
        self.assertIsNone(_parse_localhost_run_url('some random line'))

class TestTunnelAutoMode(unittest.TestCase):
    def test_cloudflared_preferred_when_available(self):
        """auto mode picks cloudflared over localhost.run when cloudflared is on PATH."""
        h = TunnelHandle('auto', 9999, timeout=0.1)
        with patch('urace.tunnel_server._direct_inbound_reachable', return_value=None), \
             patch('urace.tunnel_install.find_cloudflared', return_value='/usr/bin/cloudflared'), \
             patch.object(h, '_start_cloudflare') as mock_cf, \
             patch.object(h, '_start_localhost_run') as mock_lhr:
            h.__enter__()
        mock_cf.assert_called_once()
        mock_lhr.assert_not_called()
        self.assertEqual(h.provider, 'cloudflare')

    def test_localhost_run_fallback_when_cloudflared_absent(self):
        """auto mode falls back to localhost.run when cloudflared is not found."""
        h = TunnelHandle('auto', 9999, timeout=0.1)
        with patch('urace.tunnel_server._direct_inbound_reachable', return_value=None), \
             patch('urace.tunnel_install.find_cloudflared', return_value=None), \
             patch('shutil.which', return_value='/usr/bin/ssh'), \
             patch.object(h, '_start_localhost_run') as mock_lhr:
            h.__enter__()
        mock_lhr.assert_called_once()
        self.assertEqual(h.provider, 'localhost.run')

    def test_direct_inbound_skips_tunnel(self):
        """auto mode uses direct URL and starts no tunnel process when inbound is reachable."""
        h = TunnelHandle('auto', 9999, timeout=0.1)
        with patch('urace.tunnel_server._direct_inbound_reachable', return_value='https://1.2.3.4:9999'), \
             patch.object(h, '_start_cloudflare') as mock_cf, \
             patch.object(h, '_start_localhost_run') as mock_lhr:
            h.__enter__()
        mock_cf.assert_not_called()
        mock_lhr.assert_not_called()
        self.assertEqual(h.url, 'https://1.2.3.4:9999')
        self.assertEqual(h.provider, 'direct')
