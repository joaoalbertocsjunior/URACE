"""Log file source adapter — tails a log file for pattern-matched observations."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now


class LogFileAdapter(NullSourceAdapter):
    kind = 'log_file'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--path', default=None, help='Absolute path to log file')
        subparser.add_argument('--pattern', default=None,
                               help='Regex pattern to match (default: match all lines)')
        subparser.add_argument('--tail-lines', dest='tail_lines', type=int, default=200,
                               help='Number of lines to read from end of file')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        path = getattr(args, 'path', None) or ''
        if not name:
            raise ValueError('source add --kind log_file requires a name')
        if not path:
            raise ValueError('source add --kind log_file requires --path')
        p = Path(path)
        if not p.is_absolute():
            raise ValueError('--path must be an absolute path')
        pattern = getattr(args, 'pattern', None) or ''
        if pattern:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f'invalid --pattern regex: {exc}') from exc
        return {
            'kind': self.kind,
            'path': str(p),
            'pattern': pattern,
            'tail_lines': int(getattr(args, 'tail_lines', None) or 200),
        }

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'path': kwargs.get('path', ''),
                'pattern': kwargs.get('pattern', ''),
                'tail_lines': kwargs.get('tail_lines', 200),
                'last_sync_at': None,
                'lines_scanned': None,
                'matches': None,
                'last_offset': 0,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        path = astate.get('path', '')
        pattern = astate.get('pattern', '')
        tail_lines = astate.get('tail_lines', 200)
        p = Path(path) if path else None
        if not p or not p.exists():
            return {'synced': False, 'reason': 'path does not exist'}
        try:
            compiled = re.compile(pattern) if pattern else None
            lines = _tail(p, tail_lines)
            matches = [l for l in lines if compiled is None or compiled.search(l)]
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        astate['last_sync_at'] = now()
        astate['lines_scanned'] = len(lines)
        astate['matches'] = len(matches)
        _set_source(state, source_id, record)
        return {
            'synced': True,
            'lines_scanned': len(lines),
            'matches': len(matches),
            'path': path,
        }


def _tail(path: Path, n: int) -> list[str]:
    with path.open('rb') as f:
        f.seek(0, 2)
        size = f.tell()
        chunk = min(size, n * 200)
        f.seek(max(0, size - chunk))
        lines = f.read().decode('utf-8', errors='replace').splitlines()
    return lines[-n:] if len(lines) > n else lines


SOURCE_REGISTRY.register(LogFileAdapter())
