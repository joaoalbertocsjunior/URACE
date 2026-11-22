"""Product source adapter."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class ProductAdapter(NullSourceAdapter):
    kind = 'product'

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        if not name:
            raise ValueError('source add --kind product requires a product id')
        return {'kind': self.kind, 'product_id': name}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        from .._common import now
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {'product_id': kwargs.get('product_id', source_id), 'enabled_actions': []},
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        from ._base import _get_source
        record = _get_source(state, source_id) or {}
        product_id = record.get('adapter_state', {}).get('product_id', source_id)
        # Surfaces the lifecycle and objective health of the product
        lifecycle = state.get('lifecycle_state', 'UNKNOWN')
        objectives = state.get('objectives', [])
        active = sum(1 for o in objectives if o.get('status') == 'active')
        planned = sum(1 for o in objectives if o.get('status') == 'planned')
        completed = sum(1 for o in objectives if o.get('status') == 'completed')
        progress = state.get('executor_state', {}).get('progress_vector')
        return {
            'synced': True,
            'product_id': product_id,
            'lifecycle_state': lifecycle,
            'objectives_active': active,
            'objectives_planned': planned,
            'objectives_completed': completed,
            'progress_vector': progress,
        }


SOURCE_REGISTRY.register(ProductAdapter())
