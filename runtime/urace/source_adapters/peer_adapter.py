"""P2P peer source adapter."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class PeerAdapter(NullSourceAdapter):
    kind = 'peer'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--location', default=None,
                               help='Peer address (https://host:port)')

    def validate(self, args: Any) -> dict[str, Any]:
        target = (getattr(args, 'location', None) or
                  getattr(args, 'name', None) or
                  getattr(args, 'id', None) or '')
        if not target:
            raise ValueError('source add --kind peer requires an address')
        return {'kind': self.kind, 'location': target}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        from .._common import now
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {'location': kwargs.get('location', ''), 'enabled_actions': []},
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        from ._base import _get_source
        record = _get_source(state, source_id) or {}
        location = record.get('adapter_state', {}).get('location', '')
        # Check exchange peer list from state
        peers = state.get('exchange_peers', [])
        known_peer = next((p for p in peers if p.get('location') == location
                           or p.get('peer_id') == source_id), None)
        # Also surface exchange pool health from executor_state
        pool = state.get('executor_state', {}).get('provider_pool', {})
        return {
            'synced': True,
            'location': location,
            'known_in_exchange': known_peer is not None,
            'peer_status': known_peer.get('status') if known_peer else 'unknown',
            'last_seen': known_peer.get('last_seen_at') if known_peer else None,
        }


SOURCE_REGISTRY.register(PeerAdapter())
