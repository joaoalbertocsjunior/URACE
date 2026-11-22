"""CI pipeline source adapter — observes build status; acts with trigger/cancel.

Supports any CI system with an HTTP API (GitHub Actions, GitLab CI, Jenkins, etc.)
using httpx (already in the p2p optional dep).
"""
from __future__ import annotations

import os
from typing import Any

from ._base import NullSourceAdapter, SourceUnavailableError, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

try:
    import httpx as _httpx
    _AVAILABLE = True
except ImportError:
    _httpx = None  # type: ignore[assignment]
    _AVAILABLE = False


def _require_httpx() -> None:
    if not _AVAILABLE:
        raise SourceUnavailableError('pip install "urace[sources-http]"')


class CIPipelineAdapter(NullSourceAdapter):
    kind = 'ci_pipeline'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--api-url', dest='api_url', default=None,
                               help='CI API base URL')
        subparser.add_argument('--token-env', dest='token_env',
                               default='CI_TOKEN', help='Env var holding the API token')
        subparser.add_argument('--pipeline-id', dest='pipeline_id', default=None,
                               help='Pipeline/workflow identifier')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        api_url = getattr(args, 'api_url', None) or ''
        if not name:
            raise ValueError('source add --kind ci_pipeline requires a name')
        if not api_url:
            raise ValueError('source add --kind ci_pipeline requires --api-url')
        if not api_url.startswith(('http://', 'https://')):
            raise ValueError('--api-url must start with http:// or https://')
        return {
            'kind': self.kind,
            'api_url': api_url.rstrip('/'),
            'token_env': getattr(args, 'token_env', None) or 'CI_TOKEN',
            'pipeline_id': getattr(args, 'pipeline_id', None) or '',
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
                'api_url': kwargs.get('api_url', ''),
                'token_env': kwargs.get('token_env', 'CI_TOKEN'),
                'pipeline_id': kwargs.get('pipeline_id', ''),
                'last_sync_at': None,
                'last_run_status': None,
                'enabled_actions': [],
            },
        }

    def _headers(self, astate: dict) -> dict:
        token = os.environ.get(astate.get('token_env', 'CI_TOKEN'), '')
        return {'Authorization': f'Bearer {token}', 'Accept': 'application/json'} if token else {}

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        _require_httpx()
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        api_url = astate.get('api_url', '')
        pipeline_id = astate.get('pipeline_id', '')
        if not api_url:
            return {'synced': False, 'reason': 'no api_url configured'}
        url = f'{api_url}/status' if not pipeline_id else f'{api_url}/pipelines/{pipeline_id}'
        try:
            resp = _httpx.get(url, headers=self._headers(astate), timeout=10)
            data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
            run_status = data.get('status') or resp.reason_phrase
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        astate['last_sync_at'] = now()
        astate['last_run_status'] = run_status
        _set_source(state, source_id, record)
        return {'synced': True, 'status': run_status}

    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        _require_httpx()
        record = _get_source(state, source_id)
        if not record:
            return {'acted': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        api_url = astate.get('api_url', '')
        pipeline_id = astate.get('pipeline_id', '')
        headers = self._headers(astate)
        try:
            if action == 'trigger':
                url = f'{api_url}/pipelines/{pipeline_id}/trigger' if pipeline_id else f'{api_url}/trigger'
                resp = _httpx.post(url, json=payload, headers=headers, timeout=15)
                return {'acted': True, 'action': 'trigger', 'http_status': resp.status_code}
            elif action == 'cancel':
                url = f'{api_url}/pipelines/{pipeline_id}/cancel' if pipeline_id else f'{api_url}/cancel'
                resp = _httpx.post(url, json=payload, headers=headers, timeout=15)
                return {'acted': True, 'action': 'cancel', 'http_status': resp.status_code}
            else:
                return {'acted': False, 'reason': f'unknown action: {action}'}
        except Exception as exc:
            return {'acted': False, 'reason': str(exc)}


SOURCE_REGISTRY.register(CIPipelineAdapter())
