"""Tests for http_adapter — mocked at the HttpAdapter boundary."""
import json
import unittest
from unittest.mock import MagicMock, patch


class HttpAdapterProtocolTests(unittest.TestCase):
    def test_stdlib_adapter_satisfies_protocol(self):
        from urace.http_adapter import StdlibHttpAdapter, HttpAdapter
        a = StdlibHttpAdapter()
        self.assertIsInstance(a, HttpAdapter)

    def test_make_http_adapter_returns_stdlib_when_httpx_missing(self):
        from urace.http_adapter import make_http_adapter, StdlibHttpAdapter
        with patch.dict("sys.modules", {"httpx": None}):
            a = make_http_adapter()
        self.assertIsInstance(a, StdlibHttpAdapter)

    def test_make_http_adapter_returns_httpx_when_available(self):
        from urace.http_adapter import make_http_adapter, HttpxAdapter
        import httpx  # noqa: F401 — only run if httpx installed
        a = make_http_adapter()
        self.assertIsInstance(a, HttpxAdapter)


class BootstrapRequestAdapterTests(unittest.TestCase):
    def _mock_adapter(self, response: dict):
        adapter = MagicMock()
        adapter.post_json.return_value = response
        return adapter

    def test_bootstrap_request_returns_result_field(self):
        from urace.peer_exchange import _bootstrap_request
        adapter = self._mock_adapter({"jsonrpc": "2.0", "id": "bootstrap", "result": {"peers": []}})
        with patch("urace.http_adapter.make_http_adapter", return_value=adapter), \
             patch("urace.peer_exchange.validate_endpoint", return_value=None):
            result = _bootstrap_request("https://peer.example.com", "bootstrap.peers", {})
        self.assertEqual(result, {"peers": []})
        adapter.post_json.assert_called_once()
        call_url = adapter.post_json.call_args[0][0]
        self.assertIn("/bootstrap-rpc", call_url)

    def test_bootstrap_request_raises_on_rpc_error(self):
        from urace.peer_exchange import _bootstrap_request
        adapter = self._mock_adapter({"error": {"code": -32600, "message": "bad request"}})
        with patch("urace.http_adapter.make_http_adapter", return_value=adapter), \
             patch("urace.peer_exchange.validate_endpoint", return_value=None):
            with self.assertRaises(ValueError, msg="Bootstrap RPC error"):
                _bootstrap_request("https://peer.example.com", "bootstrap.peers", {})

    def test_bootstrap_request_raises_on_http_error(self):
        from urace.peer_exchange import _bootstrap_request
        adapter = MagicMock()
        adapter.post_json.side_effect = ValueError("HTTP 503")
        with patch("urace.http_adapter.make_http_adapter", return_value=adapter), \
             patch("urace.peer_exchange.validate_endpoint", return_value=None):
            with self.assertRaises(ValueError):
                _bootstrap_request("https://peer.example.com", "bootstrap.peers", {})
