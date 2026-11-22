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


SOURCE_REGISTRY.register(ProductAdapter())
