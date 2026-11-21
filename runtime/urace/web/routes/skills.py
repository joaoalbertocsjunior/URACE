"""Phase 6D: skill query endpoint — exposes executor skill vocabulary and probe."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException


def build_router(get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get('/')
    async def list_skills(provider: str = 'claude', _=Depends(verify_token)):
        """Return skills available for *provider* (probe contract)."""
        from ...executor_capabilities import probe, SKILL_VOCABULARY
        config = get_config()
        try:
            result = probe(config, provider)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        result['skill_vocabulary'] = SKILL_VOCABULARY
        return result

    @router.get('/vocabulary')
    async def skill_vocabulary(_=Depends(verify_token)):
        """Return the canonical SKILL_VOCABULARY mapping."""
        from ...executor_capabilities import SKILL_VOCABULARY
        return {'vocabulary': SKILL_VOCABULARY}

    @router.get('/{skill_id}')
    async def get_skill(skill_id: str, provider: str = 'claude', _=Depends(verify_token)):
        """Return full detail for a single skill by ID."""
        from ...executor_capabilities import BUILTINS, settings
        config = get_config()
        cfg = settings(config)
        all_skills = [*BUILTINS, *cfg.get('catalog', [])]
        skill = next((s for s in all_skills if s['id'] == skill_id), None)
        if skill is None:
            raise HTTPException(status_code=404, detail=f'Skill {skill_id!r} not found')
        if provider not in skill['providers']:
            raise HTTPException(status_code=404, detail=f'Skill {skill_id!r} not available for provider {provider!r}')
        return skill

    return router
