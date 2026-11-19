from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


class _SetBody(BaseModel):
    key: str
    value: str


def _get_fields_and_values(config: dict) -> tuple[list[dict], dict]:
    from ... import config_schema
    fields = config_schema.fields()
    values = {}
    for f in fields:
        try:
            values[f["path"]] = config_schema.get_value(config, f["path"])
        except (KeyError, TypeError):
            values[f["path"]] = f.get("default")
    return fields, values


def build_router(templates: Jinja2Templates, get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get("/fields")
    async def config_fields(_=Depends(verify_token)):
        from ... import config_schema
        return config_schema.fields()

    @router.get("/values")
    async def config_values(_=Depends(verify_token)):
        from ..._common import load_config
        config = load_config()
        fields, values = _get_fields_and_values(config)
        return values

    @router.post("/set")
    async def config_set(body: _SetBody, _=Depends(verify_token)):
        from ... import config_schema
        from ..._common import load_config, save_config
        config = load_config()
        try:
            config_schema.set_value(config, body.key, body.value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        save_config(config)
        return {"status": "ok", "key": body.key}

    return router
