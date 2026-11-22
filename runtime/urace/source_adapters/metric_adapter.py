"""Metric and vital source adapters."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class MetricAdapter(NullSourceAdapter):
    kind = 'metric'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--metric-source', dest='metric_source', default=None)
        subparser.add_argument('--metric-path', dest='metric_path', default=None)
        subparser.add_argument('--direction', default='nondecreasing',
                               choices=['nondecreasing', 'nonincreasing'])
        subparser.add_argument('--target', dest='metric_target', type=float, default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        src = getattr(args, 'metric_source', None) or ''
        path = getattr(args, 'metric_path', None) or ''
        if not name:
            raise ValueError('source add --kind metric requires a name')
        if not src:
            raise ValueError('source add --kind metric requires --metric-source')
        if not path:
            raise ValueError('source add --kind metric requires --metric-path')
        return {'kind': self.kind, 'metric_source': src, 'metric_path': path,
                'direction': getattr(args, 'direction', 'nondecreasing')}

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
                'metric_source': kwargs.get('metric_source', ''),
                'metric_path': kwargs.get('metric_path', ''),
                'direction': kwargs.get('direction', 'nondecreasing'),
                'enabled_actions': [],
            },
        }


SOURCE_REGISTRY.register(MetricAdapter())
