"""Cost source adapter — observe the in-process CostLedger."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, _get_source
from . import SOURCE_REGISTRY
from .._common import now


class CostAdapter(NullSourceAdapter):
    kind = 'cost'

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        if not name:
            raise ValueError('source add --kind cost requires a name')
        return {'kind': self.kind}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'last_total_usd': None,
                'last_record_count': 0,
                'last_synced_at': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        try:
            from ..cost_tracker import get_default_ledger
            ledger = get_default_ledger()
            snapshot = ledger.cost_snapshot()
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        record = _get_source(state, source_id) or {}
        astate = record.get('adapter_state', {})
        astate['last_total_usd'] = snapshot.get('total_usd')
        astate['last_record_count'] = snapshot.get('records', 0)
        astate['last_synced_at'] = now()
        return {
            'synced': True,
            'records': snapshot.get('records', 0),
            'total_usd': snapshot.get('total_usd'),
            'total_tokens': snapshot.get('total_tokens', 0),
            'providers': snapshot.get('providers', []),
        }


SOURCE_REGISTRY.register(CostAdapter())
