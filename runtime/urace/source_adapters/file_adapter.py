"""File/CSV/JSON/SQLite/API source adapter (data-layer kinds)."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, _get_source
from . import SOURCE_REGISTRY


class FileAdapter(NullSourceAdapter):
    """Handles kinds: file, csv, json, sqlite, api.

    _sync() delegates to data_transport for local JSON/CSV/SQLite I/O.
    Remote/API sources return connectivity-verified status only.
    """

    kind = 'file'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--type', dest='adapter_kind', default='file',
                               help='Adapter sub-type: file|csv|json|sqlite|api')
        subparser.add_argument('--connect', dest='dsn', default='',
                               help='Connection string or file path')
        subparser.add_argument('--direction', default='read',
                               choices=['read', 'write', 'readwrite'])
        subparser.add_argument('--auto', default='true', choices=['true', 'false'])
        subparser.add_argument('--schema', dest='schema_hint', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        return {
            'kind': self.kind,
            'adapter_kind': getattr(args, 'adapter_kind', 'file'),
            'dsn': getattr(args, 'dsn', ''),
            'direction': getattr(args, 'direction', 'read'),
        }

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        from .._common import now
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'dsn': kwargs.get('dsn', ''),
                'adapter_kind': kwargs.get('adapter_kind', 'file'),
                'direction': kwargs.get('direction', 'read'),
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        from .. import data_transport
        record = _get_source(state, source_id) or {}
        astate = record.get('adapter_state', {})
        # Build a lightweight record dict that data_transport understands
        dt_record = {
            'adapter_kind': astate.get('adapter_kind', self.kind),
            'connection_metadata': {'dsn': astate.get('dsn', '')},
            'schema_hint': astate.get('schema_hint'),
        }
        try:
            info = data_transport.verify(dt_record)
            # For read-direction sources, also count rows (bounded by data_limits)
            row_count = None
            if astate.get('direction', 'read') in ('read', 'readwrite'):
                try:
                    rows, _ = data_transport.read(dt_record, config)
                    row_count = len(rows)
                except Exception:
                    pass
            return {'synced': True, 'dsn': astate.get('dsn', ''),
                    'row_count': row_count, **info}
        except data_transport.TransportError as exc:
            msg = str(exc)
            if msg == 'ADAPTER_REQUIRED':
                return {'synced': False, 'reason': 'remote/API source — not locally verifiable'}
            return {'synced': False, 'reason': msg}
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}


class CsvAdapter(FileAdapter):
    kind = 'csv'


class JsonAdapter(FileAdapter):
    kind = 'json'


class SqliteAdapter(FileAdapter):
    kind = 'sqlite'


class ApiAdapter(FileAdapter):
    kind = 'api'


SOURCE_REGISTRY.register(FileAdapter())
SOURCE_REGISTRY.register(CsvAdapter())
SOURCE_REGISTRY.register(JsonAdapter())
SOURCE_REGISTRY.register(SqliteAdapter())
SOURCE_REGISTRY.register(ApiAdapter())
