"""SourceAdapter Protocol and NullSourceAdapter base.

Every source kind MUST inherit NullSourceAdapter (not just implement
SourceAdapter) so structured logging and lifecycle enforcement are injected
uniformly at every action boundary.

Lifecycle stages (§60):
    CONFIGURED → AVAILABLE → AUTHENTICATED → AUTHORIZED → OBSERVED

A source that has never synced successfully stays at CONFIGURED.
On first successful sync it transitions to OBSERVED.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from ..event_bus import _BUS
from .._common import now, identifier

_log = logging.getLogger('urace.source_adapters')


@runtime_checkable
class SourceAdapter(Protocol):
    """Interface every source adapter must satisfy."""

    kind: str

    def add_args(self, subparser: Any) -> None:
        """Register kind-specific argparse arguments onto *subparser*."""
        ...

    def validate(self, args: Any) -> dict[str, Any]:
        """Validate parsed args; return source dict or raise ValueError."""
        ...

    def add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        """Register a new source entry. Returns the created source record."""
        ...

    def list(self, state: dict) -> list[dict]:
        """Return all sources of this kind from state."""
        ...

    def status(self, state: dict, source_id: str) -> dict:
        """Return current lifecycle status and adapter_state for source_id."""
        ...

    def sync(self, config: dict, state: dict, source_id: str) -> dict:
        """Run a sync cycle; update adapter_state; advance lifecycle."""
        ...

    def inspect(self, state: dict, source_id: str) -> dict:
        """Return full detail for source_id (state + recent history)."""
        ...

    def enable(self, state: dict, source_id: str) -> None:
        """Mark source as enabled (un-pause sync)."""
        ...

    def disable(self, state: dict, source_id: str) -> None:
        """Mark source as disabled (pause sync without removing)."""
        ...

    def remove(self, state: dict, source_id: str) -> None:
        """Remove source record from state."""
        ...


def verify_adapter(adapter: object) -> list[str]:
    """Phase 7A — verify an object satisfies the SourceAdapter Protocol.

    Returns a list of missing/invalid attribute names.  Empty list = OK.
    """
    issues: list[str] = []
    required_attrs = ('kind', 'add_args', 'validate', 'add', 'list', 'status',
                      'sync', 'inspect', 'enable', 'disable', 'remove')
    for attr in required_attrs:
        if not hasattr(adapter, attr):
            issues.append(f'missing: {attr}')
        elif attr != 'kind' and not callable(getattr(adapter, attr)):
            issues.append(f'not callable: {attr}')
    if hasattr(adapter, 'kind') and not isinstance(adapter.kind, str):
        issues.append('kind must be str')
    return issues


def _get_source(state: dict, source_id: str) -> dict | None:
    sources = state.get('sources', {})
    if isinstance(sources, dict):
        return sources.get(source_id)
    # Legacy list format (connector_sources)
    for s in state.get('connector_sources', []):
        if s.get('id') == source_id:
            return s
    return None


def _set_source(state: dict, source_id: str, record: dict) -> None:
    state.setdefault('sources', {})[source_id] = record


def _advance_lifecycle(record: dict, new_status: str) -> None:
    record['status'] = new_status
    record.setdefault('status_history', []).append({'status': new_status, 'at': now()})


class NullSourceAdapter:
    """Base class providing logging injection and lifecycle utilities.

    Subclasses override _add, _sync, etc.  This class wraps every public
    method with _log_source_event() so logging is injected uniformly.
    """

    kind: str = 'null'

    # ── argparse registration ─────────────────────────────────────────────────

    def add_args(self, subparser: Any) -> None:
        """Default: no extra arguments."""

    def validate(self, args: Any) -> dict[str, Any]:
        """Default: return empty dict (subclasses extend)."""
        return {}

    # ── public API (logging-injected) ─────────────────────────────────────────

    def add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        self._log_source_event('add', source_id=source_id, **{k: v for k, v in kwargs.items() if not k.endswith('_secret')})
        record = self._add(config, state, source_id, **kwargs)
        _set_source(state, source_id, record)
        _BUS.publish('source.added', source_id=source_id, kind=self.kind)
        return record

    def list(self, state: dict) -> list[dict]:
        return self._list(state)

    def status(self, state: dict, source_id: str) -> dict:
        record = _get_source(state, source_id) or {}
        return {'id': source_id, 'kind': self.kind, 'status': record.get('status', 'UNKNOWN')}

    def sync(self, config: dict, state: dict, source_id: str) -> dict:
        self._log_source_event('sync', source_id=source_id)
        try:
            result = self._sync(config, state, source_id)
            record = _get_source(state, source_id) or {}
            if record.get('status') in ('CONFIGURED', 'AVAILABLE', 'AUTHENTICATED', 'AUTHORIZED'):
                _advance_lifecycle(record, 'OBSERVED')
                _set_source(state, source_id, record)
            _BUS.publish('source.synced', source_id=source_id, kind=self.kind)
            return result
        except Exception as exc:
            self._log_source_event('sync_failed', source_id=source_id, error=str(exc))
            _BUS.publish('source.failed', source_id=source_id, kind=self.kind, error=str(exc))
            raise

    def inspect(self, state: dict, source_id: str) -> dict:
        return self._inspect(state, source_id)

    def enable(self, state: dict, source_id: str) -> None:
        record = _get_source(state, source_id)
        if record:
            record['enabled'] = True
            _set_source(state, source_id, record)
        self._log_source_event('enable', source_id=source_id)
        _BUS.publish('source.changed', source_id=source_id, kind=self.kind, enabled=True)

    def disable(self, state: dict, source_id: str) -> None:
        record = _get_source(state, source_id)
        if record:
            record['enabled'] = False
            _set_source(state, source_id, record)
        self._log_source_event('disable', source_id=source_id)
        _BUS.publish('source.changed', source_id=source_id, kind=self.kind, enabled=False)

    def remove(self, state: dict, source_id: str) -> None:
        self._log_source_event('remove', source_id=source_id)
        sources = state.get('sources', {})
        sources.pop(source_id, None)
        _BUS.publish('source.removed', source_id=source_id, kind=self.kind)

    # ── internal (override in subclasses) ─────────────────────────────────────

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {},
            **kwargs,
        }

    def _list(self, state: dict) -> list[dict]:
        sources = state.get('sources', {})
        if isinstance(sources, dict):
            return [v for v in sources.values() if v.get('kind') == self.kind]
        return []

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        return {'synced': False, 'reason': 'no-op sync (base class)'}

    def _inspect(self, state: dict, source_id: str) -> dict:
        return _get_source(state, source_id) or {'id': source_id, 'kind': self.kind, 'status': 'UNKNOWN'}

    # ── logging ───────────────────────────────────────────────────────────────

    def _log_source_event(self, action: str, **ctx: Any) -> None:
        _log.debug('source.%s kind=%s %s', action, self.kind,
                   ' '.join(f'{k}={v}' for k, v in ctx.items()))
        _BUS.publish(f'source.{action}', kind=self.kind, **ctx)
