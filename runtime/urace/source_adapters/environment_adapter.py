"""Environment source adapter — reads environment variables as observations."""
from __future__ import annotations

import os
from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

_SENSITIVE_PATTERNS = ('secret', 'password', 'token', 'key', 'auth', 'credential')


class EnvironmentAdapter(NullSourceAdapter):
    kind = 'environment'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--prefix', default=None, help='Only include vars with this prefix')
        subparser.add_argument('--vars', default=None, help='Comma-separated list of var names')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        if not name:
            raise ValueError('source add --kind environment requires a name')
        prefix = getattr(args, 'prefix', None) or ''
        vars_arg = getattr(args, 'vars', None) or ''
        var_list = [v.strip() for v in vars_arg.split(',') if v.strip()] if vars_arg else []
        if not prefix and not var_list:
            raise ValueError('source add --kind environment requires --prefix or --vars')
        return {'kind': self.kind, 'prefix': prefix, 'vars': var_list}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'prefix': kwargs.get('prefix', ''),
                'vars': kwargs.get('vars', []),
                'last_scan_at': None,
                'var_count': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        prefix = astate.get('prefix', '')
        var_names = astate.get('vars', [])
        if prefix:
            found = {k: v for k, v in os.environ.items() if k.startswith(prefix)}
        else:
            found = {k: os.environ[k] for k in var_names if k in os.environ}
        # Redact sensitive-looking values before storing counts
        redacted_keys = [
            k for k in found
            if any(p in k.lower() for p in _SENSITIVE_PATTERNS)
        ]
        astate['last_scan_at'] = now()
        astate['var_count'] = len(found)
        astate['redacted_count'] = len(redacted_keys)
        _set_source(state, source_id, record)
        return {
            'synced': True,
            'var_count': len(found),
            'redacted_count': len(redacted_keys),
        }


SOURCE_REGISTRY.register(EnvironmentAdapter())
