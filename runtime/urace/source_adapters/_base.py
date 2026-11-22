"""SourceAdapter Protocol v2 and NullSourceAdapter base.

Every source kind MUST inherit NullSourceAdapter (not just implement
SourceAdapter) so structured logging and lifecycle enforcement are injected
uniformly at every action boundary.

Lifecycle stages (§60):
    CONFIGURED → AVAILABLE → AUTHENTICATED → AUTHORIZED → OBSERVED → ACTED

OBSERVED: first successful sync completed.
ACTED: first successful act() completed (opt-in; requires allow_act config gate).

act() safety contract:
  - global gate: config['sources']['allow_act'] must be True (default False)
  - per-source gate: adapter_state['enabled_actions'] must list the action name
  - violations raise SourceActDeniedError (never silently no-op)
"""
from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from ..event_bus import _BUS
from .._common import now, identifier

_log = logging.getLogger('urace.source_adapters')

# ── Exceptions ────────────────────────────────────────────────────────────────

class SourceActDeniedError(PermissionError):
    """Raised when act() is blocked by the global or per-source gate."""

class SourceUnavailableError(RuntimeError):
    """Raised when an optional dep is missing (install hint in message)."""


# ── Protocol (contract) ───────────────────────────────────────────────────────

@runtime_checkable
class SourceAdapter(Protocol):
    """Interface every source adapter must satisfy (v2)."""

    kind: str

    def add_args(self, subparser: Any) -> None: ...
    def validate(self, args: Any) -> dict[str, Any]: ...
    def add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict: ...
    def list(self, state: dict) -> list[dict]: ...
    def status(self, state: dict, source_id: str) -> dict: ...
    def sync(self, config: dict, state: dict, source_id: str) -> dict: ...
    def inspect(self, state: dict, source_id: str) -> dict: ...
    def enable(self, state: dict, source_id: str) -> None: ...
    def disable(self, state: dict, source_id: str) -> None: ...
    def remove(self, state: dict, source_id: str) -> None: ...

    # v2 act path
    def act(self, config: dict, state: dict, source_id: str,
            action: str, payload: dict | None = None) -> dict: ...
    def supported_actions(self, state: dict, source_id: str) -> list[str]: ...


# ── Protocol verifier ─────────────────────────────────────────────────────────

def verify_adapter(adapter: object) -> list[str]:
    """Verify an object satisfies the SourceAdapter Protocol v2.

    Returns a list of issue strings.  Empty list = fully conformant.
    """
    issues: list[str] = []
    required_attrs = (
        'kind', 'add_args', 'validate', 'add', 'list', 'status',
        'sync', 'inspect', 'enable', 'disable', 'remove',
        'act', 'supported_actions',
    )
    for attr in required_attrs:
        if not hasattr(adapter, attr):
            issues.append(f'missing: {attr}')
        elif attr != 'kind' and not callable(getattr(adapter, attr)):
            issues.append(f'not callable: {attr}')
    if hasattr(adapter, 'kind') and not isinstance(adapter.kind, str):
        issues.append('kind must be str')
    return issues


# ── State helpers ─────────────────────────────────────────────────────────────

def _get_source(state: dict, source_id: str) -> dict | None:
    return state.get('sources', {}).get(source_id)


def _set_source(state: dict, source_id: str, record: dict) -> None:
    state.setdefault('sources', {})[source_id] = record


def _advance_lifecycle(record: dict, new_status: str) -> None:
    record['status'] = new_status
    record.setdefault('status_history', []).append({'status': new_status, 'at': now()})


# ── NullSourceAdapter base ────────────────────────────────────────────────────

class NullSourceAdapter:
    """Base class: injects logging, lifecycle, event-bus, and act() safety gate.

    Subclass by overriding _add / _sync / _act / _inspect.
    Never override the public methods — the injection happens there.
    """

    kind: str = 'null'

    # ── argparse ──────────────────────────────────────────────────────────────

    def add_args(self, subparser: Any) -> None:
        pass

    def validate(self, args: Any) -> dict[str, Any]:
        return {}

    # ── observe path (logging-injected) ──────────────────────────────────────

    def add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        self._log_source_event('add', source_id=source_id,
                               **{k: v for k, v in kwargs.items() if not k.endswith('_secret')})
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
        state.get('sources', {}).pop(source_id, None)
        _BUS.publish('source.removed', source_id=source_id, kind=self.kind)

    # ── act path (v2, safety-gated) ───────────────────────────────────────────

    def act(self, config: dict, state: dict, source_id: str,
            action: str, payload: dict | None = None) -> dict:
        """Execute *action* on the source.

        Safety gates (both must pass):
          1. config['sources']['allow_act'] is True
          2. action is in adapter_state['enabled_actions'] for this source
        """
        if not config.get('sources', {}).get('allow_act', False):
            raise SourceActDeniedError(
                f"act() blocked: config['sources']['allow_act'] is False"
            )
        record = _get_source(state, source_id) or {}
        enabled = record.get('adapter_state', {}).get('enabled_actions', [])
        if action not in enabled:
            raise SourceActDeniedError(
                f"act() blocked: action '{action}' not in enabled_actions {enabled}"
            )
        self._log_source_event('act', source_id=source_id, source_action=action)
        try:
            result = self._act(config, state, source_id, action, payload or {})
            # Advance lifecycle on first successful act
            fresh = _get_source(state, source_id) or {}
            if fresh.get('status') == 'OBSERVED':
                _advance_lifecycle(fresh, 'ACTED')
                _set_source(state, source_id, fresh)
            _BUS.publish('source.acted', source_id=source_id, kind=self.kind, source_action=action)
            return result
        except SourceActDeniedError:
            raise
        except Exception as exc:
            self._log_source_event('act_failed', source_id=source_id, source_action=action, error=str(exc))
            _BUS.publish('source.act_failed', source_id=source_id, kind=self.kind,
                         source_action=action, error=str(exc))
            raise

    def supported_actions(self, state: dict, source_id: str) -> list[str]:
        record = _get_source(state, source_id) or {}
        return list(record.get('adapter_state', {}).get('enabled_actions', []))

    # ── internal hooks (override in subclasses) ───────────────────────────────

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {'enabled_actions': []},
            **kwargs,
        }

    def _list(self, state: dict) -> list[dict]:
        sources = state.get('sources', {})
        if isinstance(sources, dict):
            return [v for v in sources.values() if v.get('kind') == self.kind]
        return []

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        return {'synced': False, 'reason': 'stub — override _sync()'}

    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        return {'acted': False, 'reason': 'stub — override _act()'}

    def _inspect(self, state: dict, source_id: str) -> dict:
        return _get_source(state, source_id) or {'id': source_id, 'kind': self.kind, 'status': 'UNKNOWN'}

    # ── logging ───────────────────────────────────────────────────────────────

    def _log_source_event(self, action: str, **ctx: Any) -> None:
        _log.debug('source.%s kind=%s %s', action, self.kind,
                   ' '.join(f'{k}={v}' for k, v in ctx.items()))
        _BUS.publish(f'source.{action}', kind=self.kind, **ctx)
