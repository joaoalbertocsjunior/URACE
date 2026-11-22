"""SOURCE_REGISTRY — maps kind string to SourceAdapter instance.

Usage::

    from urace.source_adapters import SOURCE_REGISTRY

    adapter = SOURCE_REGISTRY.get('github')
    record = adapter.add(config, state, source_id, repo='owner/repo')

Adapters self-register at import time via SOURCE_REGISTRY.register().
The registry is populated by importing this package.
"""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, SourceAdapter


class _Registry:
    """Singleton that maps kind → SourceAdapter instance."""

    def __init__(self) -> None:
        self._adapters: dict[str, NullSourceAdapter] = {}

    def register(self, adapter: NullSourceAdapter) -> None:
        self._adapters[adapter.kind] = adapter

    def get(self, kind: str) -> NullSourceAdapter | None:
        return self._adapters.get(kind)

    def kinds(self) -> list[str]:
        return sorted(self._adapters.keys())

    def all(self) -> dict[str, NullSourceAdapter]:
        return dict(self._adapters)


SOURCE_REGISTRY = _Registry()

# ── Import adapters to trigger self-registration ──────────────────────────────
# Each module calls SOURCE_REGISTRY.register(MyAdapter()) at module level.

from . import (  # noqa: E402, F401
    file_adapter,
    github_adapter,
    connector_adapter,
    executor_adapter,
    peer_adapter,
    product_adapter,
    metric_adapter,
    vital_adapter,
    # Phase 3A — local
    folder,
    shell_adapter,
    environment_adapter,
    # Phase 3B — observation
    codebase,
    testsuite_adapter,
    # Phase 3C — remote/push
    webhook,
    database,
    # Phase 3D — network
    p2p_catalog_adapter,
    # Protocol v2 — new kinds (optional deps, all Apache 2.0 compatible)
    git_adapter,
    s3_adapter,
    ci_pipeline_adapter,
    event_stream_adapter,
    inbox_adapter,
    mcp_server_adapter,
    log_file_adapter,
    package_registry_adapter,
    # Runtime-internal observation sources
    audit_adapter,
    cost_adapter,
)

__all__ = ['SOURCE_REGISTRY', 'SourceAdapter', 'NullSourceAdapter']
