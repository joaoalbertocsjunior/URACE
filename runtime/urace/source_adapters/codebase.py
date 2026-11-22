"""Codebase source adapter — scans a code tree and populates product_profile."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

_CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.go', '.rb', '.rs', '.c', '.cpp', '.h',
    '.cs', '.swift', '.kt', '.scala', '.sh', '.bash', '.php',
}


class CodebaseAdapter(NullSourceAdapter):
    kind = 'codebase'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--path', default=None, help='Absolute path to codebase root')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        path = getattr(args, 'path', None) or ''
        if not name:
            raise ValueError('source add --kind codebase requires a name')
        if not path:
            raise ValueError('source add --kind codebase requires --path')
        p = Path(path)
        if not p.is_absolute():
            raise ValueError('--path must be an absolute path')
        return {'kind': self.kind, 'path': str(p)}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        path = kwargs.get('path', '')
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'path': path,
                'last_scan_at': None,
                'file_count': None,
                'loc': None,
                'languages': [],
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        path = record.get('adapter_state', {}).get('path', '')
        p = Path(path) if path else None
        if not p or not p.exists():
            return {'synced': False, 'reason': 'path does not exist'}
        file_count = 0
        loc = 0
        lang_counts: dict[str, int] = {}
        for f in p.rglob('*'):
            if not f.is_file():
                continue
            if f.suffix in _CODE_EXTENSIONS:
                file_count += 1
                lang_counts[f.suffix] = lang_counts.get(f.suffix, 0) + 1
                try:
                    loc += sum(1 for _ in f.open('rb'))
                except OSError:
                    pass
        astate = record.get('adapter_state', {})
        astate['last_scan_at'] = now()
        astate['file_count'] = file_count
        astate['loc'] = loc
        astate['languages'] = sorted(lang_counts, key=lambda k: -lang_counts[k])
        _set_source(state, source_id, record)
        # Populate product_profile with codebase observations
        pp = state.setdefault('product_profile', {})
        pp['codebase_loc'] = loc
        pp['codebase_languages'] = astate['languages']
        pp['codebase_source_id'] = source_id
        return {'synced': True, 'file_count': file_count, 'loc': loc, 'languages': astate['languages']}


SOURCE_REGISTRY.register(CodebaseAdapter())
