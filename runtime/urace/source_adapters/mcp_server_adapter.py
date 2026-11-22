"""MCP server source adapter — observes an MCP tool server; acts with call_tool.

Requires: pip install "urace[sources-mcp]"  (mcp, MIT)
"""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, SourceUnavailableError, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

try:
    import mcp.client as _mcp_client  # type: ignore[import]
    _AVAILABLE = True
except ImportError:
    _mcp_client = None  # type: ignore[assignment]
    _AVAILABLE = False


def _require_mcp() -> None:
    if not _AVAILABLE:
        raise SourceUnavailableError('pip install "urace[sources-mcp]"')


class MCPServerAdapter(NullSourceAdapter):
    kind = 'mcp_server'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--url', default=None, help='MCP server SSE/HTTP URL')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        url = getattr(args, 'url', None) or ''
        if not name:
            raise ValueError('source add --kind mcp_server requires a name')
        if not url:
            raise ValueError('source add --kind mcp_server requires --url')
        if not url.startswith(('http://', 'https://')):
            raise ValueError('--url must start with http:// or https://')
        return {'kind': self.kind, 'url': url}

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
                'last_sync_at': None,
                'tool_count': None,
                'tools': [],
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        _require_mcp()
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        url = astate.get('url', '')
        if not url:
            return {'synced': False, 'reason': 'no url configured'}
        try:
            # Use httpx directly to list tools via MCP HTTP transport
            import httpx
            resp = httpx.post(f'{url.rstrip("/")}/tools/list', timeout=10,
                              json={'jsonrpc': '2.0', 'method': 'tools/list', 'id': 1})
            resp.raise_for_status()
            tools = resp.json().get('result', {}).get('tools', [])
            tool_names = [t.get('name', '') for t in tools]
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        astate['last_sync_at'] = now()
        astate['tool_count'] = len(tool_names)
        astate['tools'] = tool_names
        _set_source(state, source_id, record)
        return {'synced': True, 'tool_count': len(tool_names), 'tools': tool_names}

    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        if action != 'call_tool':
            return {'acted': False, 'reason': f'unknown action: {action}'}
        record = _get_source(state, source_id)
        if not record:
            return {'acted': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        url = astate.get('url', '')
        tool_name = payload.get('tool', '')
        arguments = payload.get('arguments', {})
        if not url or not tool_name:
            return {'acted': False, 'reason': 'call_tool requires tool in payload'}
        try:
            import httpx
            resp = httpx.post(
                f'{url.rstrip("/")}/tools/call',
                timeout=30,
                json={
                    'jsonrpc': '2.0',
                    'method': 'tools/call',
                    'params': {'name': tool_name, 'arguments': arguments},
                    'id': 1,
                },
            )
            resp.raise_for_status()
            result = resp.json().get('result', {})
        except Exception as exc:
            return {'acted': False, 'reason': str(exc)}
        return {'acted': True, 'tool': tool_name, 'result': result}


SOURCE_REGISTRY.register(MCPServerAdapter())
