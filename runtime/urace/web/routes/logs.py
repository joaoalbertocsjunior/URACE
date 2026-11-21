"""Phase 6A-6C: log stream, log history, per-component config endpoints."""
from __future__ import annotations

import collections
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse


# Bounded in-memory ring buffer for log history (Phase 6B).
_LOG_HISTORY: collections.deque = collections.deque(maxlen=500)


class _HistoryHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _LOG_HISTORY.append({
                'ts': self.formatTime(record, '%Y-%m-%dT%H:%M:%S'),
                'level': record.levelname,
                'logger': record.name,
                'msg': record.getMessage(),
            })
        except Exception:
            pass


_history_handler = _HistoryHandler()
_history_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(_history_handler)


def build_router(get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get('/history')
    async def log_history(limit: int = 100, _=Depends(verify_token)):
        """Return recent log entries (up to 500 kept in memory)."""
        entries = list(_LOG_HISTORY)
        return {'entries': entries[-min(limit, 500):], 'total': len(entries)}

    @router.get('/stream')
    async def log_stream(_=Depends(verify_token)):
        """SSE log stream — emits recent history then streams new events."""
        import asyncio

        async def _generate():
            snapshot = list(_LOG_HISTORY)
            for entry in snapshot[-50:]:
                yield f'data: {json.dumps(entry)}\n\n'
            seen = len(_LOG_HISTORY)
            for _ in range(300):  # keep alive max 300 × 100ms = 30s
                await asyncio.sleep(0.1)
                current = list(_LOG_HISTORY)
                if len(current) > seen:
                    for entry in current[seen:]:
                        yield f'data: {json.dumps(entry)}\n\n'
                    seen = len(current)

        return StreamingResponse(_generate(), media_type='text/event-stream')

    @router.get('/components')
    async def list_components(_=Depends(verify_token)):
        """List logging components and their current enabled state."""
        from ...logging_config import _COMPONENT_LOGGERS, _ALWAYS_ON
        import logging as _logging
        root_level = _logging.getLogger().level
        result = {}
        for comp, logger_name in _COMPONENT_LOGGERS.items():
            lg = _logging.getLogger(logger_name)
            result[comp] = {
                'enabled': lg.level <= root_level or comp in _ALWAYS_ON,
                'always_on': comp in _ALWAYS_ON,
                'logger': logger_name,
            }
        return result

    @router.post('/components/{component}')
    async def set_component(component: str, body: dict, _=Depends(verify_token)):
        """Phase 6C: enable or disable a logging component at runtime."""
        from ...logging_config import _COMPONENT_LOGGERS, reconfigure_component, _ALWAYS_ON
        if component not in _COMPONENT_LOGGERS:
            raise HTTPException(status_code=404, detail=f'Unknown component: {component!r}')
        enabled = body.get('enabled')
        if not isinstance(enabled, bool):
            raise HTTPException(status_code=422, detail="body must be {\"enabled\": true|false}")
        if component in _ALWAYS_ON and not enabled:
            raise HTTPException(status_code=403, detail=f'{component!r} is always-on and cannot be disabled')
        reconfigure_component(component, enabled)
        return {'component': component, 'enabled': enabled}

    return router
