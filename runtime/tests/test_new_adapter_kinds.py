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


# ── Phase 3: Protocol v2 state['sources'] loading ────────────────────────────

def test_github_source_loaded_from_state():
    state = {"sources": {"gh-1": {"kind": "github", "enabled": True,
                                   "adapter_state": {"repo": "owner/repo"}}}}
    registry = build_sources_registry(_empty_registry(), state, {})
    try:
        from sources_lib.adapters.github import GitHubAdapter  # noqa: F401
        assert any(r.id == "gh-1" for r in registry.list())
    except ImportError:
        pass


def test_mcp_source_loaded_from_state():
    state = {"sources": {"mcp-1": {"kind": "mcp_server", "enabled": True,
                                    "adapter_state": {"url": "http://localhost:8080"}}}}
    registry = build_sources_registry(_empty_registry(), state, {})
    try:
        from sources_lib.adapters.mcp import MCPSourceAdapter  # noqa: F401
        assert any(r.id == "mcp-1" for r in registry.list())
    except ImportError:
        pass


def test_disabled_source_not_loaded():
    state = {"sources": {"gh-disabled": {"kind": "github", "enabled": False,
                                          "adapter_state": {"repo": "owner/repo"}}}}
    registry = build_sources_registry(_empty_registry(), state, {})
    assert not any(r.id == "gh-disabled" for r in registry.list())


def test_sources_lib_config_github():
    from urace.source_adapters._sources_bridge import _sources_lib_config
    record = {"adapter_state": {"repo": "owner/repo", "token_env": "NO_SUCH_ENV_VAR_XYZ"}}
    cfg = _sources_lib_config("github", record)
    assert cfg["repo"] == "owner/repo"
    assert "token" not in cfg  # env var absent → no token key


def test_sources_lib_config_mcp():
    from urace.source_adapters._sources_bridge import _sources_lib_config
    record = {"adapter_state": {"url": "http://mcp.local"}}
    cfg = _sources_lib_config("mcp_server", record)
    assert cfg == {"url": "http://mcp.local"}


def test_sources_lib_config_passthrough():
    from urace.source_adapters._sources_bridge import _sources_lib_config
    record = {"kind": "metric", "adapter_state": {"foo": "bar"}}
    cfg = _sources_lib_config("metric", record)
    assert cfg is record
