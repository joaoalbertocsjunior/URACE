"""File/CSV/JSON/SQLite/API source adapter (data-layer kinds)."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class FileAdapter(NullSourceAdapter):
    """Handles kinds: file, csv, json, sqlite, api.

    Delegates to `urace data add` via main() for full implementation.
    Phase 3A will replace this with the folder/codebase adapters.
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
