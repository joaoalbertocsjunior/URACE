"""Vital source adapter."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class VitalAdapter(NullSourceAdapter):
    kind = 'vital'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--numerator', default=None)
        subparser.add_argument('--denominator', default=None)
        subparser.add_argument('--window', default=None)
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        num = getattr(args, 'numerator', None) or ''
        if not name:
            raise ValueError('source add --kind vital requires a name')
        if not num:
            raise ValueError('source add --kind vital requires --numerator')
        return {'kind': self.kind, 'numerator': num,
                'denominator': getattr(args, 'denominator', None),
                'window': getattr(args, 'window', None)}

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
                'numerator': kwargs.get('numerator', ''),
                'denominator': kwargs.get('denominator'),
                'window': kwargs.get('window'),
            },
        }


SOURCE_REGISTRY.register(VitalAdapter())
