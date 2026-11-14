import unittest
from urace.tunnel_server import _parse_cloudflare_url, _parse_localhost_run_url

class TestTunnelParsers(unittest.TestCase):
    def test_cloudflare_url_extracted(self):
        line = '2024-01-01T00:00:00Z INF | https://abc-def-123.trycloudflare.com |'
        self.assertEqual(_parse_cloudflare_url(line), 'https://abc-def-123.trycloudflare.com')

    def test_localhost_run_url_extracted(self):
        line = 'https://abc123.lhr.life tunneled with tls termination'
        self.assertEqual(_parse_localhost_run_url(line), 'https://abc123.lhr.life')

    def test_no_match_returns_none(self):
        self.assertIsNone(_parse_cloudflare_url('some random line'))
        self.assertIsNone(_parse_localhost_run_url('some random line'))
