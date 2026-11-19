"""Protocol for executor provider pool management.

executor_routing.py's pure functions (routed_provider_definitions,
classify_unavailability, etc.) are already well-decoupled.  The coupling
problem is that pool_state lives deep inside state["executor_state"]["provider_pool"]
and is read by executor_routing directly via dict passing.

ExecutorPool wraps that dict behind a named interface so callers don't
need to know the nesting path, and so the pool can be replaced with a
test stub that returns fixed provider lists.

Usage::

    from .executor_pool import ExecutorPool, DictExecutorPool

    pool: ExecutorPool = DictExecutorPool(state)
    providers = pool.routed_providers(settings, capability='mutation')
    pool.record_completion(provider_id, capability, elapsed_seconds=12.3)
"""
from __future__ import annotations

import threading
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ExecutorPool(Protocol):
    """Interface for provider selection and outcome recording."""

    def routed_providers(
        self,
        settings: dict[str, Any],
        capability: str,
    ) -> list[dict[str, Any]]:
        """Return providers sorted by routing preference for capability."""
        ...

    def record_completion(
        self,
        provider_id: str,
        capability: str,
        elapsed_seconds: float,
    ) -> None:
        """Persist a successful completion so routing can balance load."""
        ...

    def record_failure(
        self,
        provider_id: str,
        stage: str,
        error: str,
    ) -> None:
        """Persist a failure so routing can apply cooldown."""
        ...

    def pool_state(self) -> dict[str, Any]:
        """Return the raw pool_state dict (read-only snapshot)."""
        ...


class DictExecutorPool:
    """Wraps state['executor_state']['provider_pool'] behind ExecutorPool.

    Pass this wherever ExecutorPool is expected; modifications are reflected
    in the live state dict.
    """

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state
        self._lock = threading.Lock()

    def _pool(self) -> dict[str, Any]:
        return self._state.setdefault('executor_state', {}).setdefault('provider_pool', {})

    def routed_providers(
        self,
        settings: dict[str, Any],
        capability: str,
    ) -> list[dict[str, Any]]:
        from . import executor_routing as _er
        with self._lock:
            return _er.routed_provider_definitions(settings, self._pool(), capability)

    def record_completion(
        self,
        provider_id: str,
        capability: str,
        elapsed_seconds: float,
    ) -> None:
        with self._lock:
            status = self._pool().setdefault(provider_id, {})
            history = status.setdefault('completion_history', [])
            history.append({
                'at': __import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc,
                ).isoformat(),
                'capability': capability,
                'elapsed_seconds': elapsed_seconds,
            })
            # Keep last 100 completions per provider
            if len(history) > 100:
                history[:] = history[-100:]

    def record_failure(
        self,
        provider_id: str,
        stage: str,
        error: str,
    ) -> None:
        from . import cli_state as _cs
        with self._lock:
            _cs.record_executor_failure(self._state, stage, error)

    def pool_state(self) -> dict[str, Any]:
        import copy
        with self._lock:
            return copy.deepcopy(self._pool())
