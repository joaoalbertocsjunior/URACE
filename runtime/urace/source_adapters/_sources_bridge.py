"""Bridge between URACE source adapters and sources-lib SourceAdapter protocol.

URACE adapters use (config, state, source_id) calling convention.
sources-lib adapters use (SourceRecord, app_config) calling convention.

URACEAdapterBridge wraps any NullSourceAdapter and exposes it as a
sources-lib-compatible SourceAdapter, enabling URACE adapters to be
registered in a sources-lib SourceRegistry.
"""
from __future__ import annotations

from typing import Any

from sources import BaseSourceAdapter, SourceRecord, SourceRegistry
from sources.adapter import SourceActDeniedError

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


def build_sources_registry(
    urace_registry: Any,
    urace_state: dict[str, Any],
    urace_config: dict[str, Any],
) -> SourceRegistry:
    """Build a sources-lib SourceRegistry from URACE's SOURCE_REGISTRY.

    Each URACE adapter kind is wrapped in a URACEAdapterBridge and registered.
    Existing URACE source records (from urace_state) are added as SourceRecords.
    """
    registry = SourceRegistry()
    registry.register_kind("local_data", DataTransportAdapter())

    # Register sources-lib native adapters — A2A is stdlib, AI/MCP are conditional
    from sources.adapters.a2a import A2ASourceAdapter
    registry.register_kind("a2a_agent", A2ASourceAdapter())

    from sources.adapters.directory import DirectoryAdapter
    registry.register_kind("directory", DirectoryAdapter())

    try:
        from sources.adapters.ai import AIExecutorAdapter
        registry.register_kind("ai_executor", AIExecutorAdapter())
    except ImportError:
        pass

    try:
        from sources.adapters.mcp import MCPSourceAdapter
        registry.register_kind("mcp_server", MCPSourceAdapter())
    except ImportError:
        pass
    for kind, adapter in urace_registry.all().items():
        bridge = URACEAdapterBridge(adapter, urace_state)
        try:
            registry.register_kind(kind, bridge)
        except Exception:
            pass

    # Register live source records from URACE state
    for record in urace_state.get("data_source_records", []):
        source_id = record.get("id", "")
        kind = record.get("kind", "")
        if source_id and kind and kind in registry.kinds():
            try:
                registry.add(kind, source_id=source_id, config=record)
            except Exception:
                pass

    return registry
