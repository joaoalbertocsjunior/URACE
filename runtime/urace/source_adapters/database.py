"""Database source adapter — queries a database and surfaces row counts as observations."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now


class DatabaseAdapter(NullSourceAdapter):
    kind = 'database'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--dsn', default=None, help='Database DSN (credentials in secrets/)')
        subparser.add_argument('--query', default=None, help='Observation query (read-only)')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        if not name:
            raise ValueError('source add --kind database requires a name')
        dsn = getattr(args, 'dsn', None) or ''
        if not dsn:
            raise ValueError('source add --kind database requires --dsn')
        query = getattr(args, 'query', None) or ''
        if not query:
            raise ValueError('source add --kind database requires --query')
        # Reject obviously write-modifying keywords
        q_upper = query.strip().upper()
        if any(q_upper.startswith(kw) for kw in ('INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE')):
            raise ValueError('--query must be a read-only SELECT statement')
        # Redact credentials from stored DSN
        try:
            parsed = urlparse(dsn)
            safe_dsn = parsed._replace(password=None).geturl() if parsed.password else dsn
        except Exception:
            safe_dsn = '<redacted>'
        return {'kind': self.kind, 'dsn_safe': safe_dsn, 'query': query}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'dsn_safe': kwargs.get('dsn_safe', ''),
                'query': kwargs.get('query', ''),
                'last_run_at': None,
                'row_count': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        # Actual DB execution requires driver availability — returns CONFIGURED until wired.
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        astate['last_run_at'] = now()
        _set_source(state, source_id, record)
        return {'synced': False, 'reason': 'database driver not installed; wire a driver in executor config'}


SOURCE_REGISTRY.register(DatabaseAdapter())
