"""Phase 6E: source registry endpoint — exposes registered source adapters."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException


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
                'instances': [{'id': s.get('id'), 'status': s.get('status'), 'enabled': s.get('enabled')} for s in instances],
            })
        return {'adapters': result, 'total_kinds': len(result)}

    @router.get('/kinds')
    async def list_kinds(_=Depends(verify_token)):
        """Return all registered source kind names."""
        from ...source_adapters import SOURCE_REGISTRY
        return {'kinds': SOURCE_REGISTRY.kinds()}

    @router.get('/{source_id}')
    async def get_source(source_id: str, _=Depends(verify_token)):
        """Return current status for a specific source instance."""
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
            return adapter.inspect(state, source_id)
        return record

    return router
