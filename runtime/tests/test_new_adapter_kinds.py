"""Tests for new sources-lib adapter kinds registered in build_sources_registry."""
import pytest

from urace.source_adapters._sources_bridge import build_sources_registry
from sources_lib.adapters.a2a import A2ASourceAdapter
from sources_lib.adapter import SourceRecord, SourceUnavailableError


def _empty_registry():
    """Return a minimal URACE registry stub with no adapters."""

    class _Stub:
        def all(self):
            return {}

    return _Stub()


def test_a2a_agent_kind_registered():
    registry = build_sources_registry(_empty_registry(), {}, {})
    assert "a2a_agent" in registry.kinds()


def test_local_data_kind_registered():
    registry = build_sources_registry(_empty_registry(), {}, {})
    assert "local_data" in registry.kinds()


def test_ai_executor_kind_conditional():
    registry = build_sources_registry(_empty_registry(), {}, {})
    try:
        from sources_lib.adapters.ai import AIExecutorAdapter  # noqa: F401
        assert "ai_executor" in registry.kinds()
    except ImportError:
        assert "ai_executor" not in registry.kinds()


def test_mcp_server_kind_conditional():
    registry = build_sources_registry(_empty_registry(), {}, {})
    try:
        from sources_lib.adapters.mcp import MCPSourceAdapter  # noqa: F401
        assert "mcp_server" in registry.kinds()
    except ImportError:
        assert "mcp_server" not in registry.kinds()


def test_a2a_adapter_verify_no_url():
    adapter = A2ASourceAdapter()
    record = SourceRecord(id="x", kind="a2a_agent", config={}, state={}, added_at=0.0)
    with pytest.raises(SourceUnavailableError):
        adapter.verify(record, {})


def test_a2a_adapter_supported_actions():
    adapter = A2ASourceAdapter()
    assert adapter.supported_actions(None, {}) == ["send_message"]


def test_directory_kind_registered():
    registry = build_sources_registry(_empty_registry(), {}, {})
    assert 'directory' in registry.kinds()
