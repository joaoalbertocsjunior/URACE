"""Connector source adapter."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class ConnectorAdapter(NullSourceAdapter):
    kind = 'connector'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--location', default=None,
                               help='Connector location/URL')
        subparser.add_argument('--visibility', default='private',
                               choices=['private', 'public'])
        subparser.add_argument('--credential-env', dest='credential_env', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        loc = getattr(args, 'location', None) or ''
        if not loc:
            raise ValueError('source add --kind connector requires --location')
        return {'kind': self.kind, 'location': loc,
                'visibility': getattr(args, 'visibility', 'private'),
                'credential_env': getattr(args, 'credential_env', None)}

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
                'location': kwargs.get('location', ''),
                'visibility': kwargs.get('visibility', 'private'),
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        from ._base import _get_source
        record = _get_source(state, source_id) or {}
        location = record.get('adapter_state', {}).get('location', '')
        if not location:
            return {'synced': False, 'reason': 'no location configured'}
        if not location.startswith(('http://', 'https://')):
            return {'synced': True, 'location': location, 'reachable': None,
                    'note': 'non-HTTP connector — reachability not checked'}
        try:
            import httpx
        except ImportError:
            from ._base import SourceUnavailableError
            raise SourceUnavailableError('pip install "urace[sources-http]"')
        try:
            resp = httpx.head(location, timeout=5, follow_redirects=True)
            return {'synced': True, 'location': location,
                    'reachable': True, 'http_status': resp.status_code}
        except Exception as exc:
            return {'synced': True, 'location': location, 'reachable': False, 'reason': str(exc)}


SOURCE_REGISTRY.register(ConnectorAdapter())
