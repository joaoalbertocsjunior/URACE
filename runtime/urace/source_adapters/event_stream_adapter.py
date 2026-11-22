"""Event stream source adapter — consumes Kafka/Redis streams as observation feeds.

Optional deps:
  Kafka: pip install "urace[sources-kafka]"   (kafka-python, Apache 2.0)
  Redis: pip install "urace[sources-redis]"   (redis, MIT)
"""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, SourceUnavailableError, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

try:
    from kafka import KafkaConsumer as _KafkaConsumer  # type: ignore[import]
    _KAFKA_AVAILABLE = True
except ImportError:
    _KafkaConsumer = None  # type: ignore[assignment,misc]
    _KAFKA_AVAILABLE = False

try:
    import redis as _redis_mod
    _REDIS_AVAILABLE = True
except ImportError:
    _redis_mod = None  # type: ignore[assignment]
    _REDIS_AVAILABLE = False

_SUPPORTED_BACKENDS = ('kafka', 'redis')


class EventStreamAdapter(NullSourceAdapter):
    kind = 'event_stream'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--backend', default='kafka', choices=list(_SUPPORTED_BACKENDS),
                               help='Streaming backend: kafka or redis')
        subparser.add_argument('--brokers', default=None,
                               help='Comma-separated broker addresses (Kafka)')
        subparser.add_argument('--topic', default=None, help='Topic or stream name')
        subparser.add_argument('--group-id', dest='group_id', default=None,
                               help='Consumer group ID (Kafka)')
        subparser.add_argument('--max-poll', dest='max_poll', type=int, default=100,
                               help='Max messages per sync poll')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        topic = getattr(args, 'topic', None) or ''
        if not name:
            raise ValueError('source add --kind event_stream requires a name')
        if not topic:
            raise ValueError('source add --kind event_stream requires --topic')
        backend = getattr(args, 'backend', None) or 'kafka'
        if backend not in _SUPPORTED_BACKENDS:
            raise ValueError(f'--backend must be one of {_SUPPORTED_BACKENDS}')
        return {
            'kind': self.kind,
            'backend': backend,
            'brokers': getattr(args, 'brokers', None) or '',
            'topic': topic,
            'group_id': getattr(args, 'group_id', None) or f'urace-{name}',
            'max_poll': int(getattr(args, 'max_poll', None) or 100),
        }

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'backend': kwargs.get('backend', 'kafka'),
                'brokers': kwargs.get('brokers', ''),
                'topic': kwargs.get('topic', ''),
                'group_id': kwargs.get('group_id', ''),
                'max_poll': kwargs.get('max_poll', 100),
                'last_sync_at': None,
                'messages_polled': 0,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        backend = astate.get('backend', 'kafka')
        topic = astate.get('topic', '')
        max_poll = astate.get('max_poll', 100)
        if not topic:
            return {'synced': False, 'reason': 'no topic configured'}

        if backend == 'kafka':
            if not _KAFKA_AVAILABLE:
                raise SourceUnavailableError('pip install "urace[sources-kafka]"')
            brokers = [b.strip() for b in astate.get('brokers', 'localhost:9092').split(',') if b.strip()]
            group_id = astate.get('group_id', 'urace')
            try:
                consumer = _KafkaConsumer(
                    topic,
                    bootstrap_servers=brokers,
                    group_id=group_id,
                    consumer_timeout_ms=2000,
                    auto_offset_reset='latest',
                )
                count = sum(1 for _ in consumer)
                consumer.close()
            except Exception as exc:
                return {'synced': False, 'reason': str(exc)}

        elif backend == 'redis':
            if not _REDIS_AVAILABLE:
                raise SourceUnavailableError('pip install "urace[sources-redis]"')
            redis_url = astate.get('brokers', 'redis://localhost:6379')
            try:
                client = _redis_mod.from_url(redis_url)
                messages = client.xread({topic: '$'}, count=max_poll, block=2000) or []
                count = sum(len(msgs) for _, msgs in messages)
                client.close()
            except Exception as exc:
                return {'synced': False, 'reason': str(exc)}
        else:
            return {'synced': False, 'reason': f'unsupported backend: {backend}'}

        astate['last_sync_at'] = now()
        astate['messages_polled'] = astate.get('messages_polled', 0) + count
        _set_source(state, source_id, record)
        return {'synced': True, 'backend': backend, 'topic': topic, 'messages_polled': count}


SOURCE_REGISTRY.register(EventStreamAdapter())
