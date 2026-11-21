"""Executor source adapter."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class ExecutorAdapter(NullSourceAdapter):
    kind = 'executor'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--command', dest='executor_binary', default=None)
        subparser.add_argument('--adapter', default=None)
        subparser.add_argument('--priority', type=int, default=100)
        subparser.add_argument('--capability', action='append', default=[])
        subparser.add_argument('--max-calls-24h', dest='max_calls_24h',
                               type=int, default=None)
        subparser.add_argument('--max-calls-30d', dest='max_calls_30d',
                               type=int, default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        return {
            'kind': self.kind,
            'executor_binary': getattr(args, 'executor_binary', None),
            'adapter': getattr(args, 'adapter', None),
            'priority': getattr(args, 'priority', 100),
            'capability': getattr(args, 'capability', []),
            'max_calls_24h': getattr(args, 'max_calls_24h', None),
            'max_calls_30d': getattr(args, 'max_calls_30d', None),
        }

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
                'executor_binary': kwargs.get('executor_binary'),
                'adapter': kwargs.get('adapter'),
                'priority': kwargs.get('priority', 100),
            },
        }


SOURCE_REGISTRY.register(ExecutorAdapter())
