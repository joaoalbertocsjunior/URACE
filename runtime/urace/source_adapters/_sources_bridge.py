"""Bridge between URACE source adapters and sources-lib SourceAdapter protocol.

URACE adapters use (config, state, source_id) calling convention.
sources-lib adapters use (SourceRecord, app_config) calling convention.

URACEAdapterBridge wraps any NullSourceAdapter and exposes it as a
sources-lib-compatible SourceAdapter, enabling URACE adapters to be
registered in a sources-lib SourceRegistry.

Kinds listed in _SOURCES_LIB_NATIVE_KINDS are served by sources-lib's own
adapters in build_sources_registry() and must not be wrapped via
URACEAdapterBridge — their native implementations take precedence.
"""
from __future__ import annotations

import logging
import os
from typing import Any

_log = logging.getLogger(__name__)

from sources_lib import BaseSourceAdapter, SourceRecord, SourceRegistry
from sources_lib.adapter import SourceActDeniedError

from urace.source_adapters._data_transport_adapter import DataTransportAdapter


class URACEAdapterBridge(BaseSourceAdapter):
    """Wraps a URACE NullSourceAdapter and exposes the sources-lib protocol.

    The SourceRecord.state dict holds the URACE state (source_records etc.).
    The SourceRecord.config dict holds the URACE source config entry.
    app_config is passed through as the URACE top-level config.
    """

    def __init__(self, urace_adapter: Any, urace_state: dict[str, Any] | None = None) -> None:
        self._adapter = urace_adapter
        self._state = urace_state or {}

    @property
    def config_schema(self) -> dict[str, Any]:
        return {}

    @property
    def actions(self) -> list[str]:
        try:
            return self._adapter.supported_actions(self._state, '') or []
        except Exception:
            return []

    def verify(self, record: SourceRecord, config: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self._adapter.status(config, self._state, record.id)
            return {"ok": True, **result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def sync(self, record: SourceRecord, config: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            result = self._adapter.sync(config, self._state, record.id)
            if isinstance(result, dict):
                rows = result.get("rows") or result.get("data") or []
                if not rows and result:
                    rows = [result]
            elif isinstance(result, list):
                rows = result
            else:
                rows = []
            return rows
        except Exception as exc:
            raise

    def act(self, record: SourceRecord, config: dict[str, Any],
            action: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self._adapter.act(config, self._state, record.id, action, payload)
            return result if isinstance(result, dict) else {"result": result}
        except PermissionError as exc:
            raise SourceActDeniedError(str(exc)) from exc


# Kinds with dedicated sources-lib native adapters registered below.
# URACE adapters for these kinds must not be wrapped via URACEAdapterBridge —
# the native implementations own the data-transport path.
_SOURCES_LIB_NATIVE_KINDS: frozenset[str] = frozenset({
    "local_data",
    "a2a_agent",
    "directory",
    "ai_executor",
    "mcp_server",
    "github",
})


def build_sources_registry(
    urace_registry: Any,
    urace_state: dict[str, Any],
    urace_config: dict[str, Any],
) -> SourceRegistry:
    """Build a sources-lib SourceRegistry from URACE's SOURCE_REGISTRY.

    Kinds in _SOURCES_LIB_NATIVE_KINDS are served by sources-lib's own adapters.
    All other URACE adapter kinds are wrapped in URACEAdapterBridge and registered.
    Existing URACE source records (from urace_state) are added as SourceRecords.
    """
    registry = SourceRegistry()
    registry.register_kind("local_data", DataTransportAdapter())

    # Register sources-lib native adapters — A2A is stdlib, AI/MCP/GitHub are conditional
    from sources_lib.adapters.a2a import A2ASourceAdapter
    registry.register_kind("a2a_agent", A2ASourceAdapter())

    from sources_lib.adapters.directory import DirectoryAdapter
    registry.register_kind("directory", DirectoryAdapter())

    try:
        from sources_lib.adapters.ai import AIExecutorAdapter
        registry.register_kind("ai_executor", AIExecutorAdapter())
    except ImportError:
        pass

    try:
        from sources_lib.adapters.mcp import MCPSourceAdapter
        registry.register_kind("mcp_server", MCPSourceAdapter())
    except ImportError:
        pass

    try:
        from sources_lib.adapters.github import GitHubAdapter
        registry.register_kind("github", GitHubAdapter())
    except ImportError:
        pass

    for kind, adapter in urace_registry.all().items():
        if kind in _SOURCES_LIB_NATIVE_KINDS:
            _log.debug("sources-lib native adapter takes precedence for kind %r — skipping URACE bridge", kind)
            continue
        registry.register_kind(kind, URACEAdapterBridge(adapter, urace_state))

    # Load legacy data_source_records (data transport system)
    for record in urace_state.get("data_source_records", []):
        source_id = record.get("id", "")
        kind = record.get("kind", "")
        if source_id and kind and kind in registry.kinds():
            try:
                registry.add(kind, source_id=source_id, config=record)
            except Exception:
                pass

    # Load Protocol v2 source records (state['sources']) into the sources-lib registry.
    # For native kinds, adapter_state is mapped to the sources-lib config_schema format.
    # For URACE bridge kinds, the full record is passed (config_schema is empty).
    for source_id, record in urace_state.get("sources", {}).items():
        if not isinstance(record, dict) or not record.get("enabled", True):
            continue
        kind = record.get("kind", "")
        if not source_id or not kind or kind not in registry.kinds():
            continue
        cfg = _sources_lib_config(kind, record)
        try:
            registry.add(kind, source_id=source_id, config=cfg)
        except Exception:
            pass

    return registry


def _get_native_adapter(kind: str) -> Any:
    """Return a sources-lib native adapter instance for a known native kind, or None."""
    try:
        if kind == "github":
            from sources_lib.adapters.github import GitHubAdapter
            return GitHubAdapter()
        if kind == "mcp_server":
            from sources_lib.adapters.mcp import MCPSourceAdapter
            return MCPSourceAdapter()
        if kind == "a2a_agent":
            from sources_lib.adapters.a2a import A2ASourceAdapter
            return A2ASourceAdapter()
        if kind == "directory":
            from sources_lib.adapters.directory import DirectoryAdapter
            return DirectoryAdapter()
        if kind == "ai_executor":
            from sources_lib.adapters.ai import AIExecutorAdapter
            return AIExecutorAdapter()
    except ImportError:
        pass
    return None


def native_kind_validate(kind: str, args: Any) -> dict[str, Any]:
    """Validate CLI args for a sources-lib native kind.

    Returns kwargs suitable for native_kind_add().  Raises ValueError with a
    user-facing message on invalid input.  Called by _handle_source_add_unified
    instead of NullSourceAdapter.validate() for kinds that have been removed
    from SOURCE_REGISTRY.
    """
    if kind == "github":
        repo = getattr(args, "repo", None) or ""
        if not repo:
            raise ValueError("source add --kind github requires --repo owner/repo")
        if "/" not in repo:
            raise ValueError("--repo must be owner/repo slug")
        return {
            "repo": repo,
            "token_env": getattr(args, "token_env", "URACE_GITHUB_TOKEN") or "URACE_GITHUB_TOKEN",
        }
    if kind == "mcp_server":
        url = getattr(args, "location", None) or getattr(args, "url", None) or ""
        if not url:
            raise ValueError("source add --kind mcp_server requires --location <http-url>")
        if not url.startswith(("http://", "https://")):
            raise ValueError("--location must start with http:// or https://")
        return {"url": url}
    raise ValueError(f"kind {kind!r} is not handled by native_kind_validate")


def native_kind_add(
    kind: str,
    source_id: str,
    state: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Create and store a URACE Protocol v2 source record for a native kind.

    Writes into state['sources'] and returns the record.  Called instead of
    NullSourceAdapter.add() for native kinds removed from SOURCE_REGISTRY.
    """
    import time as _time
    from .._common import now as _now
    astate: dict[str, Any]
    if kind == "github":
        astate = {
            "repo": kwargs.get("repo", ""),
            "token_env": kwargs.get("token_env", "URACE_GITHUB_TOKEN"),
            "last_sync_at": None,
            "default_branch": None,
            "open_issues": None,
            "stars": None,
            "enabled_actions": [],
        }
    elif kind == "mcp_server":
        astate = {
            "url": kwargs.get("url", ""),
            "last_sync_at": None,
            "tool_count": None,
            "tools": [],
            "enabled_actions": [],
        }
    else:
        astate = dict(kwargs)
        astate.setdefault("enabled_actions", [])
    record: dict[str, Any] = {
        "id": source_id,
        "kind": kind,
        "enabled": True,
        "added_at": _now(),
        "status": "CONFIGURED",
        "status_history": [{"status": "CONFIGURED", "at": _now()}],
        "adapter_state": astate,
    }
    state.setdefault("sources", {})[source_id] = record
    return record


def native_kind_sync(
    kind: str,
    urace_record: dict[str, Any],
    urace_config: dict[str, Any],
) -> dict[str, Any]:
    """Sync a native-kind source via its sources-lib adapter.

    Translates from URACE's (config, state, source_id) world to sources-lib's
    (SourceRecord, app_config) world and back.  Returns a URACE-format sync
    result dict with at least {'synced': bool}.
    """
    from sources_lib import SourceRecord
    adapter = _get_native_adapter(kind)
    if adapter is None:
        return {"synced": False, "reason": f"sources-lib adapter for {kind!r} not available"}
    cfg = _sources_lib_config(kind, urace_record)
    source_id = urace_record.get("id", "")
    record = SourceRecord(id=source_id, kind=kind, config=cfg)
    try:
        rows = adapter.sync(record, urace_config)
        return {"synced": True, "rows": rows, "row_count": len(rows)}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def native_kind_act(
    kind: str,
    urace_record: dict[str, Any],
    action: str,
    payload: dict[str, Any],
    urace_config: dict[str, Any],
) -> dict[str, Any]:
    """Act on a native-kind source via its sources-lib adapter.

    Raises PermissionError (maps to SourceActDeniedError) if denied.
    """
    from sources_lib import SourceRecord
    from sources_lib.adapter import SourceActDeniedError as _Denied
    adapter = _get_native_adapter(kind)
    if adapter is None:
        raise RuntimeError(f"sources-lib adapter for {kind!r} not available")
    cfg = _sources_lib_config(kind, urace_record)
    source_id = urace_record.get("id", "")
    record = SourceRecord(id=source_id, kind=kind, config=cfg)
    try:
        return adapter.act(record, urace_config, action, payload)
    except _Denied as exc:
        raise PermissionError(str(exc)) from exc


def native_kind_actions(kind: str) -> list[str]:
    """Return supported action names for a sources-lib native kind."""
    adapter = _get_native_adapter(kind)
    if adapter is None:
        return []
    return list(getattr(adapter, "actions", []))


def _sources_lib_config(kind: str, urace_record: dict[str, Any]) -> dict[str, Any]:
    """Map a URACE Protocol v2 source record to the sources-lib config_schema format.

    For native kinds (github, mcp_server) the adapter_state fields are promoted to
    the flat config dict sources-lib expects.  For all other kinds (URACEAdapterBridge),
    config_schema is empty so the full URACE record is safe to pass through.
    """
    astate = urace_record.get("adapter_state", {})
    if kind == "github":
        cfg: dict[str, Any] = {}
        repo = astate.get("repo", "")
        if repo:
            cfg["repo"] = repo
        token_env = astate.get("token_env", "URACE_GITHUB_TOKEN")
        token = os.environ.get(token_env or "", "") or ""
        if token:
            cfg["token"] = token
        return cfg
    if kind == "mcp_server":
        url = astate.get("url", "")
        return {"url": url} if url else {}
    return urace_record
