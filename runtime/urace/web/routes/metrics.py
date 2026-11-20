"""Live metrics route — subscribes to event bus events and exposes counts.

Tracks cycle.started, cycle.completed, ledger.earned, ledger.spent events
in a process-level accumulator so the HTMX dashboard can poll /api/metrics/live
for real-time visibility without storing state to disk.
"""
from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse


class _LiveMetrics:
    """Process-level event accumulator.  Thread-safe, no persistence."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {
            "cycle_started": 0,
            "cycle_completed": 0,
            "cycle_last_outcome": None,
            "cycle_last_id": None,
            "ledger_earned_total": 0,
            "ledger_spent_total": 0,
            "ledger_last_earn_peer": None,
            "ledger_last_spend_peer": None,
        }

    # ── handlers (kept as bound methods so the bus holds a WeakMethod ref) ───

    def on_cycle_started(self, cycle_id=None, **_kw):
        with self._lock:
            self._data["cycle_started"] += 1
            self._data["cycle_last_id"] = cycle_id

    def on_cycle_completed(self, cycle_id=None, outcome=None, **_kw):
        with self._lock:
            self._data["cycle_completed"] += 1
            self._data["cycle_last_outcome"] = outcome
            self._data["cycle_last_id"] = cycle_id

    def on_ledger_earned(self, peer_id=None, units=0, **_kw):
        with self._lock:
            self._data["ledger_earned_total"] += units or 0
            self._data["ledger_last_earn_peer"] = peer_id

    def on_ledger_spent(self, peer_id=None, units=0, **_kw):
        with self._lock:
            self._data["ledger_spent_total"] += units or 0
            self._data["ledger_last_spend_peer"] = peer_id

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)


# Process-level singleton; created once per worker process.
_METRICS = _LiveMetrics()
_SUBSCRIBED = False
_SUB_LOCK = threading.Lock()


def _ensure_subscribed() -> None:
    global _SUBSCRIBED
    with _SUB_LOCK:
        if _SUBSCRIBED:
            return
        try:
            from ...event_bus import _BUS
            _BUS.subscribe("cycle.started", _METRICS.on_cycle_started)
            _BUS.subscribe("cycle.completed", _METRICS.on_cycle_completed)
            _BUS.subscribe("ledger.earned", _METRICS.on_ledger_earned)
            _BUS.subscribe("ledger.spent", _METRICS.on_ledger_spent)
            _SUBSCRIBED = True
        except Exception:
            pass


def build_router(verify_token) -> APIRouter:
    _ensure_subscribed()
    router = APIRouter()

    @router.get("/live")
    async def live_metrics(_=Depends(verify_token)):
        return JSONResponse(_METRICS.snapshot())

    return router
