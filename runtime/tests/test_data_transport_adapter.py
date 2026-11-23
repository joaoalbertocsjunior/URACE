"""Tests for DataTransportAdapter — sources-lib wrapper around data_transport.py."""
import unittest
from unittest.mock import patch

from sources_lib import SourceRecord
from sources_lib.adapter import SourceActDeniedError, SourceError, SourceUnavailableError

from urace.source_adapters._data_transport_adapter import DataTransportAdapter
from urace.source_adapters._sources_bridge import build_sources_registry
from urace.data_transport import TransportError


def _make_record(source_id="src-1", adapter_kind="json", dsn="/tmp/test.json"):
    return SourceRecord(
        id=source_id,
        kind="local_data",
        config={
            "adapter_kind": adapter_kind,
            "connection_metadata": {"dsn": dsn},
            "schema_hint": "",
            "data_limits": {},
        },
    )


class TestVerifyConnected(unittest.TestCase):
    def test_verify_connected(self):
        adapter = DataTransportAdapter()
        record = _make_record()
        verify_result = {"transport": "local", "connectivity_verified": True, "rows_transferred": 0}
        with patch("urace.source_adapters._data_transport_adapter.data_transport.verify",
                   return_value=verify_result):
            result = adapter.verify(record, {})
        self.assertTrue(result["connectivity_verified"])

    def test_verify_transport_error_maps(self):
        """Non-ADAPTER_REQUIRED TransportError should map to SourceError."""
        adapter = DataTransportAdapter()
        record = _make_record()
        with patch("urace.source_adapters._data_transport_adapter.data_transport.verify",
                   side_effect=TransportError("local data source does not exist")):
            with self.assertRaises(SourceError):
                adapter.verify(record, {})

    def test_verify_adapter_required_maps_to_unavailable(self):
        """ADAPTER_REQUIRED TransportError should map to SourceUnavailableError."""
        adapter = DataTransportAdapter()
        record = _make_record()
        with patch("urace.source_adapters._data_transport_adapter.data_transport.verify",
                   side_effect=TransportError("ADAPTER_REQUIRED")):
            with self.assertRaises(SourceUnavailableError):
                adapter.verify(record, {})


class TestSyncReturnsRows(unittest.TestCase):
    def test_sync_returns_rows(self):
        adapter = DataTransportAdapter()
        record = _make_record()
        rows = [{"a": 1}]
        raw = b'[{"a":1}]'
        with patch("urace.source_adapters._data_transport_adapter.data_transport.read",
                   return_value=(rows, raw)):
            result = adapter.sync(record, {})
        self.assertEqual(result, [{"a": 1}])


class TestActPush(unittest.TestCase):
    def test_act_push(self):
        adapter = DataTransportAdapter()
        record = _make_record()
        push_result = {
            "rows_affected": 1,
            "records_written": ["/tmp/test.json"],
            "backup": None,
            "content_sha256": "abc",
        }
        with patch("urace.source_adapters._data_transport_adapter.data_transport.push",
                   return_value=push_result):
            result = adapter.act(record, {}, "push", {"rows": [{"a": 1}]})
        self.assertEqual(result["rows_affected"], 1)

    def test_act_unsupported(self):
        """Unknown action should raise SourceActDeniedError."""
        adapter = DataTransportAdapter()
        record = _make_record()
        with self.assertRaises(SourceActDeniedError):
            adapter.act(record, {}, "delete", {})


class TestSupportedActions(unittest.TestCase):
    def test_supported_actions(self):
        adapter = DataTransportAdapter()
        record = _make_record()
        self.assertEqual(adapter.supported_actions(record, {}), ["push"])


class TestLocalDataRegisteredInRegistry(unittest.TestCase):
    def test_local_data_registered_in_registry(self):
        class _EmptyRegistry:
            def all(self):
                return {}

        registry = build_sources_registry(_EmptyRegistry(), {}, {})
        self.assertIn("local_data", registry.kinds())
