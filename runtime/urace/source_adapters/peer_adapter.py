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


SOURCE_REGISTRY.register(PeerAdapter())
