"""Tests for the URACE→sources-lib bridge layer."""
import unittest
from urace.source_adapters._sources_bridge import URACEAdapterBridge, build_sources_registry
from sources import SourceRecord, SourceRegistry


class _FakeURACEAdapter:
    """Minimal URACE-style adapter for testing."""
    kind = "fake"

    def status(self, config, state, source_id):
        return {"source_id": source_id, "enabled": True}

    def sync(self, config, state, source_id):
        return {"rows": [{"value": 42, "source_id": source_id}]}

    def act(self, config, state, source_id, action, payload):
        if action == "ping":
            return {"pong": True}
        raise PermissionError(f"action not allowed: {action}")

    def supported_actions(self, state, source_id):
        return ["ping"]

    def add(self, config, state, source_id, **kwargs):
        return {}

    def list(self, state):
        return []


class URACEBridgeTests(unittest.TestCase):

    def _make_record(self, source_id="s1"):
        return SourceRecord(id=source_id, kind="fake", config={"source_id": source_id})

    def test_verify_returns_ok(self):
        bridge = URACEAdapterBridge(_FakeURACEAdapter())
        record = self._make_record()
        result = bridge.verify(record, {})
        self.assertTrue(result["ok"])

    def test_sync_returns_rows(self):
        bridge = URACEAdapterBridge(_FakeURACEAdapter())
        record = self._make_record()
        rows = bridge.sync(record, {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value"], 42)

    def test_act_valid(self):
        bridge = URACEAdapterBridge(_FakeURACEAdapter())
        record = self._make_record()
        result = bridge.act(record, {}, "ping", {})
        self.assertEqual(result, {"pong": True})

    def test_act_denied_raises(self):
        from sources.adapter import SourceActDeniedError
        bridge = URACEAdapterBridge(_FakeURACEAdapter())
        record = self._make_record()
        with self.assertRaises(SourceActDeniedError):
            bridge.act(record, {}, "not_allowed", {})

    def test_actions_list(self):
        bridge = URACEAdapterBridge(_FakeURACEAdapter())
        self.assertIn("ping", bridge.actions)


class BuildRegistryTests(unittest.TestCase):

    def test_build_registry_registers_kinds(self):
        class _FakeRegistry:
            def all(self):
                return {"fake": _FakeURACEAdapter()}
        state = {}
        reg = build_sources_registry(_FakeRegistry(), state, {})
        self.assertIn("fake", reg.kinds())

    def test_build_registry_adds_live_records(self):
        class _FakeRegistry:
            def all(self):
                return {"fake": _FakeURACEAdapter()}
        state = {"data_source_records": [
            {"id": "src-1", "kind": "fake"}
        ]}
        reg = build_sources_registry(_FakeRegistry(), state, {})
        records = reg.list()
        self.assertTrue(any(r.id == "src-1" for r in records))
