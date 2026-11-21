"""Webhook source adapter — registers an inbound HTTP endpoint as an observation source."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now


class WebhookAdapter(NullSourceAdapter):
    kind = 'webhook'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--url', default=None, help='Callback URL this webhook will POST to')
        subparser.add_argument('--secret', default=None, help='HMAC signing secret (not stored in state)')
        subparser.add_argument('--events', default=None, help='Comma-separated event types to subscribe')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        if not name:
            raise ValueError('source add --kind webhook requires a name')
        url = getattr(args, 'url', None) or ''
        if not url:
            raise ValueError('source add --kind webhook requires --url')
        if not url.startswith(('http://', 'https://')):
            raise ValueError('--url must start with http:// or https://')
        events_raw = getattr(args, 'events', None) or ''
        events = [e.strip() for e in events_raw.split(',') if e.strip()] if events_raw else []
        # secret is not forwarded — the caller stores it out-of-band
        return {'kind': self.kind, 'url': url, 'events': events}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'url': kwargs.get('url', ''),
                'events': kwargs.get('events', []),
                'last_received_at': None,
                'delivery_count': 0,
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        # Webhooks are push-driven; sync only checks registration health.
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        return {'synced': True, 'mode': 'push', 'delivery_count': record.get('adapter_state', {}).get('delivery_count', 0)}


SOURCE_REGISTRY.register(WebhookAdapter())
