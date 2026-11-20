"""ExecutionBackend Protocol — port for executor I/O.

The concrete adapter is urace.executor (imported as intelligent_executor in
cli_cycle.py).  Any object satisfying this Protocol can be substituted, which
makes cli_cycle unit-testable without spawning a real AI executor process.

Usage::

    from urace.execution_backend import ExecutionBackend
    # Type-annotate helpers that accept an executor module:
    def my_helper(config, state, backend: ExecutionBackend): ...
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ExecutionBackend(Protocol):
    """Minimal interface for discovery and execution operations."""

    def discover(
        self, root: Path, config: dict[str, Any], state: dict[str, Any]
    ) -> dict[str, Any]: ...

    def execute(
        self,
        root: Path,
        config: dict[str, Any],
        state: dict[str, Any],
        objective: dict[str, Any],
    ) -> dict[str, Any]: ...

    def availability(self, settings: dict[str, Any]) -> dict[str, Any]: ...
