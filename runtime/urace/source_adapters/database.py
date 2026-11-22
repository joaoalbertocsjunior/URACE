"""Database source adapter — executes read-only queries via SQLAlchemy.

Requires: pip install "urace[sources-db]"  (sqlalchemy, MIT)
Supports any SQLAlchemy-compatible DSN: postgresql://, mysql://, sqlite:///, etc.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from ._base import NullSourceAdapter, SourceUnavailableError, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

try:
    import sqlalchemy as _sa
    _AVAILABLE = True
except ImportError:
    _sa = None  # type: ignore[assignment]
    _AVAILABLE = False


def _require_sqlalchemy() -> None:
    if not _AVAILABLE:
        raise SourceUnavailableError('pip install "urace[sources-db]"')


class DatabaseAdapter(NullSourceAdapter):
    kind = 'database'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--dsn', default=None,
                               help='SQLAlchemy DSN (e.g. postgresql://user:pass@host/db)')
        subparser.add_argument('--query', default=None, help='Read-only SELECT query to observe')
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
        q_upper = query.strip().upper()
        if any(q_upper.startswith(kw) for kw in
               ('INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE')):
            raise ValueError('--query must be a read-only SELECT statement')
        try:
            parsed = urlparse(dsn)
            safe_dsn = parsed._replace(password=None).geturl() if parsed.password else dsn
        except Exception:
            safe_dsn = '<redacted>'
        return {'kind': self.kind, 'dsn': dsn, 'dsn_safe': safe_dsn, 'query': query}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'dsn': kwargs.get('dsn', ''),
                'dsn_safe': kwargs.get('dsn_safe', ''),
                'query': kwargs.get('query', ''),
                'last_run_at': None,
                'row_count': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        _require_sqlalchemy()
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        dsn = astate.get('dsn', '')
        query = astate.get('query', '')
        if not dsn or not query:
            return {'synced': False, 'reason': 'no dsn or query configured'}
        try:
            engine = _sa.create_engine(dsn, pool_pre_ping=True)
            with engine.connect() as conn:
                result = conn.execute(_sa.text(query))
                rows = result.fetchall()
                row_count = len(rows)
            engine.dispose()
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        astate['last_run_at'] = now()
        astate['row_count'] = row_count
        _set_source(state, source_id, record)
        return {'synced': True, 'dsn_safe': astate.get('dsn_safe', ''),
                'row_count': row_count}


SOURCE_REGISTRY.register(DatabaseAdapter())
