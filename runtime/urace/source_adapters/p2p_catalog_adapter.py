"""P2P catalog source adapter — syncs atom listings from a peer's feature catalog."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

_HEX64 = __import__('re').compile(r'^[a-f0-9]{64}$')


class P2PCatalogAdapter(NullSourceAdapter):
    kind = 'p2p_catalog'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--peer-id', default=None, dest='peer_id', help='64-char hex peer ID')
        subparser.add_argument('--endpoint', default=None, help='Peer catalog endpoint URL')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        if not name:
            raise ValueError('source add --kind p2p_catalog requires a name')
        peer_id = getattr(args, 'peer_id', None) or ''
        if not peer_id:
            raise ValueError('source add --kind p2p_catalog requires --peer-id')
        if not _HEX64.fullmatch(peer_id):
            raise ValueError('--peer-id must be a 64-char hex string')
        endpoint = getattr(args, 'endpoint', None) or ''
        if endpoint and not endpoint.startswith(('http://', 'https://')):
            raise ValueError('--endpoint must start with http:// or https://')
        return {'kind': self.kind, 'peer_id': peer_id, 'endpoint': endpoint}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'peer_id': kwargs.get('peer_id', ''),
                'endpoint': kwargs.get('endpoint', ''),
                'last_sync_at': None,
                'atom_count': None,
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        # Network sync deferred to exchange layer; records last-attempt timestamp.
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        astate['last_sync_at'] = now()
        _set_source(state, source_id, record)
        return {'synced': False, 'reason': 'network sync delegated to exchange layer'}


SOURCE_REGISTRY.register(P2PCatalogAdapter())
