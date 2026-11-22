"""Source registry endpoints — observe, act, and manage registered source adapters."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel


class ActRequest(BaseModel):
    action: str
    payload: dict = {}


class EnableActionRequest(BaseModel):
    action: str


def build_router(get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get('/')
    async def list_sources(kind: str | None = None, _=Depends(verify_token)):
        """Return all registered source adapters, optionally filtered by kind."""
        from ...source_adapters import SOURCE_REGISTRY
        from ..._common import load_state_for_read
        config = get_config()
        state = load_state_for_read(config) or {}
        sources_state = state.get('sources', {})
        adapters = SOURCE_REGISTRY.all()
        result = []
        for adapter_kind, adapter in adapters.items():
            if kind and adapter_kind != kind:
                continue
            instances = [v for v in sources_state.values() if isinstance(v, dict) and v.get('kind') == adapter_kind]
            result.append({
                'kind': adapter_kind,
                'registered': True,
                'instance_count': len(instances),
                'instances': [
                    {
                        'id': s.get('id'),
                        'status': s.get('status'),
                        'enabled': s.get('enabled'),
                        'enabled_actions': s.get('adapter_state', {}).get('enabled_actions', []),
                    }
                    for s in instances
                ],
            })
        allow_act = get_config().get('sources', {}).get('allow_act', False)
        return {'adapters': result, 'total_kinds': len(result), 'allow_act_global': allow_act}

    @router.get('/kinds')
    async def list_kinds(_=Depends(verify_token)):
        """Return all registered source kind names."""
        from ...source_adapters import SOURCE_REGISTRY
        return {'kinds': SOURCE_REGISTRY.kinds()}

    @router.get('/{source_id}')
    async def get_source(source_id: str, _=Depends(verify_token)):
        """Return current status and detail for a specific source instance."""
        from ..._common import load_state_for_read
        from ...source_adapters import SOURCE_REGISTRY
        config = get_config()
        state = load_state_for_read(config) or {}
        sources_state = state.get('sources', {})
        record = sources_state.get(source_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f'Source {source_id!r} not found')
        kind = record.get('kind', '')
        adapter = SOURCE_REGISTRY.get(kind)
        if adapter:
            detail = adapter.inspect(state, source_id)
            detail['enabled_actions'] = record.get('adapter_state', {}).get('enabled_actions', [])
            return detail
        return record

    @router.get('/{source_id}/actions')
    async def get_source_actions(source_id: str, _=Depends(verify_token)):
        """Return enabled actions for a source instance (Protocol v2 act path)."""
        from ..._common import load_state_for_read
        from ...source_adapters import SOURCE_REGISTRY
        config = get_config()
        state = load_state_for_read(config) or {}
        sources_state = state.get('sources', {})
        record = sources_state.get(source_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f'Source {source_id!r} not found')
        kind = record.get('kind', '')
        adapter = SOURCE_REGISTRY.get(kind)
        actions = adapter.supported_actions(state, source_id) if adapter else []
        allow_act = get_config().get('sources', {}).get('allow_act', False)
        return {
            'source_id': source_id,
            'kind': kind,
            'actions': actions,
            'allow_act_global': allow_act,
        }

    @router.post('/{source_id}/actions/{action_name}/enable')
    async def enable_source_action(source_id: str, action_name: str, _=Depends(verify_token)):
        """Add an action to this source's enabled_actions allowlist."""
        from ..._common import load_state_for_read, save_state
        config = get_config()
        state = load_state_for_read(config) or {}
        sources_state = state.get('sources', {})
        record = sources_state.get(source_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f'Source {source_id!r} not found')
        astate = record.setdefault('adapter_state', {})
        enabled = list(astate.get('enabled_actions', []))
        if action_name not in enabled:
            enabled.append(action_name)
            astate['enabled_actions'] = enabled
            save_state(config, state)
        return {'source_id': source_id, 'action': action_name, 'enabled_actions': enabled}

    @router.delete('/{source_id}/actions/{action_name}/enable')
    async def disable_source_action(source_id: str, action_name: str, _=Depends(verify_token)):
        """Remove an action from this source's enabled_actions allowlist."""
        from ..._common import load_state_for_read, save_state
        config = get_config()
        state = load_state_for_read(config) or {}
        sources_state = state.get('sources', {})
        record = sources_state.get(source_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f'Source {source_id!r} not found')
        astate = record.setdefault('adapter_state', {})
        enabled = [a for a in astate.get('enabled_actions', []) if a != action_name]
        astate['enabled_actions'] = enabled
        save_state(config, state)
        return {'source_id': source_id, 'action': action_name, 'enabled_actions': enabled}

    @router.post('/{source_id}/act')
    async def act_on_source(source_id: str, body: ActRequest, _=Depends(verify_token)):
        """Execute an action on a source (Protocol v2 act path).

        Safety: config['sources']['allow_act'] must be True, and the action must be
        in the source's enabled_actions allowlist.
        """
        from ..._common import load_state_for_read, save_state
        from ...source_adapters import SOURCE_REGISTRY
        from ...source_adapters._base import SourceActDeniedError, SourceUnavailableError
        config = get_config()
        state = load_state_for_read(config) or {}
        sources_state = state.get('sources', {})
        record = sources_state.get(source_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f'Source {source_id!r} not found')
        kind = record.get('kind', '')
        adapter = SOURCE_REGISTRY.get(kind)
        if adapter is None:
            raise HTTPException(status_code=422, detail=f'No registered adapter for kind {kind!r}')
        try:
            result = adapter.act(config, state, source_id, body.action, body.payload)
            save_state(config, state)
        except SourceActDeniedError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except SourceUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return {'source_id': source_id, 'action': body.action, 'result': result}

    return router
