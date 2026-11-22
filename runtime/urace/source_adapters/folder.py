"""Folder source adapter — watches a local directory for changes."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source, _advance_lifecycle
from . import SOURCE_REGISTRY
from .._common import now


class FolderAdapter(NullSourceAdapter):
    kind = 'folder'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--path', default=None, help='Absolute path to watch')
        subparser.add_argument('--pattern', default='**/*', help='Glob pattern (default: **/*)')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        path = getattr(args, 'path', None) or ''
        if not name:
            raise ValueError('source add --kind folder requires a name')
        if not path:
            raise ValueError('source add --kind folder requires --path')
        p = Path(path)
        if not p.is_absolute():
            raise ValueError('--path must be an absolute path')
        return {
            'kind': self.kind,
            'path': str(p),
            'pattern': getattr(args, 'pattern', None) or '**/*',
        }

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        path = kwargs.get('path', '')
        exists = Path(path).exists() if path else False
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'AVAILABLE' if exists else 'CONFIGURED',
            'status_history': [{'status': 'AVAILABLE' if exists else 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'path': path,
                'pattern': kwargs.get('pattern', '**/*'),
                'last_scan_at': None,
                'file_count': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        path = record.get('adapter_state', {}).get('path', '')
        pattern = record.get('adapter_state', {}).get('pattern', '**/*')
        p = Path(path) if path else None
        if not p or not p.exists():
            return {'synced': False, 'reason': 'path does not exist'}
        files = list(p.glob(pattern))
        record['adapter_state']['last_scan_at'] = now()
        record['adapter_state']['file_count'] = len(files)
        _set_source(state, source_id, record)
        return {'synced': True, 'file_count': len(files), 'path': path}


    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        if action != 'scan':
            return {'acted': False, 'reason': f'unknown action: {action}'}
        return self._sync(config, state, source_id) | {'acted': True}


SOURCE_REGISTRY.register(FolderAdapter())
