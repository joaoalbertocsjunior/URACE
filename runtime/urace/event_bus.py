"""Lightweight synchronous pub/sub event bus. Stdlib only, no external deps.

Handlers are stored as weak references so subscribers do not prevent garbage
collection of their owning objects.  Thread-safe: all mutations are serialized
under a single lock.  Dead references are pruned lazily on each publish call.

Usage::

    from urace.event_bus import _BUS

    def on_goal_added(goal_id: str, **kw) -> None:
        ...

    _BUS.subscribe('goal.added', on_goal_added)
    _BUS.publish('goal.added', goal_id='abc123')
    _BUS.unsubscribe('goal.added', on_goal_added)

Event-type strings use dotted notation: '<domain>.<action>'
(e.g. 'goal.added', 'executor.completed', 'ledger.earned').

Important: keep a strong reference to your handler.  If the handler is a
lambda or a local function with no other referents it will be collected and
the subscription will silently expire.
"""
from __future__ import annotations

import logging
import threading
import weakref
from typing import Any, Callable

_logger = logging.getLogger(__name__)


def _make_ref(handler: Callable[..., Any]) -> weakref.ref:  # type: ignore[type-arg]
    """Return a WeakMethod for bound methods, weakref.ref for plain functions."""
    try:
        return weakref.WeakMethod(handler)  # type: ignore[return-value]
    except TypeError:
        return weakref.ref(handler)


class EventBus:
    """Thread-safe synchronous publish/subscribe bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[weakref.ref]] = {}  # type: ignore[type-arg]
        self._lock = threading.Lock()

    # ── subscription management ───────────────────────────────────────────────

    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        """Register handler for event.  Duplicate registrations are allowed."""
        ref = _make_ref(handler)
        with self._lock:
            self._handlers.setdefault(event, []).append(ref)

    def unsubscribe(self, event: str, handler: Callable[..., Any]) -> None:
        """Remove all registrations of handler for event."""
        with self._lock:
            bucket = self._handlers.get(event, [])
            self._handlers[event] = [
                r for r in bucket
                if r() is not None and r() != handler
            ]

    # ── dispatch ──────────────────────────────────────────────────────────────

    def publish(self, event: str, **payload: Any) -> None:
        """Call all live handlers for event with payload as keyword arguments.

        Exceptions raised by handlers are logged and swallowed so a single
        bad handler cannot block subsequent ones or the caller.
        Dead weak references are pruned after each publish call.
        """
        with self._lock:
            refs = list(self._handlers.get(event, []))
        dead: list[weakref.ref] = []  # type: ignore[type-arg]
        for ref in refs:
            fn = ref()
            if fn is None:
                dead.append(ref)
                continue
            try:
                fn(**payload)
            except Exception:
                _logger.exception("event_bus handler raised for event %r", event)
        if dead:
            with self._lock:
                bucket = self._handlers.get(event, [])
                self._handlers[event] = [r for r in bucket if r not in dead]

    # ── test isolation ────────────────────────────────────────────────────────

    def _clear_all(self) -> None:
        """Remove all subscriptions.  Called by the pytest autouse fixture."""
        with self._lock:
            self._handlers.clear()


_BUS = EventBus()
