"""
Executor circuit breaker — reads/writes pool_state failure counters.

Design:
- Tracks consecutive failures per provider in pool_state (already persisted by executor.py)
- When failures >= trip_threshold → extend cooldown to circuit_breaker_cooldown_seconds
- reset() clears failures + cooldown for a provider (operator action)
- status() returns per-provider health without modifying state

Zero-degradation guarantee: only called from explicit CLI commands, never from the
hot execution path. Does not modify routed_provider_definitions() or run_routed_codex().
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

DEFAULT_TRIP_THRESHOLD = 5       # consecutive failures before trip
DEFAULT_COOLDOWN_SECONDS = 1800  # 30-minute open-circuit cooldown


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def status(executor_settings: dict, pool_state: dict) -> dict:
    """Return per-provider circuit breaker status (read-only)."""
    from . import executor as _ex
    providers = _ex.provider_definitions(executor_settings)
    threshold = int(executor_settings.get("circuit_breaker_trip_threshold", DEFAULT_TRIP_THRESHOLD))
    cooldown_secs = float(executor_settings.get("circuit_breaker_cooldown_seconds", DEFAULT_COOLDOWN_SECONDS))
    now = datetime.now(timezone.utc)
    reports = []
    for p in providers:
        pid = p["id"]
        st = pool_state.get(pid, {})
        failures = int(st.get("failures", 0))
        retry_at = st.get("retry_at")
        cooldown_until = st.get("cooldown_until")
        tripped = failures >= threshold
        in_cooldown = bool(
            (retry_at and now < datetime.fromisoformat(retry_at)) or
            (cooldown_until and now < datetime.fromisoformat(cooldown_until))
        )
        reports.append({
            "provider_id": pid,
            "failures": failures,
            "threshold": threshold,
            "tripped": tripped,
            "in_cooldown": in_cooldown,
            "retry_at": retry_at,
            "cooldown_until": cooldown_until,
            "last_probe_at": st.get("last_probe_at"),
            "calls_24h": st.get("calls_24h", 0),
            "calls_30d": st.get("calls_30d", 0),
            "recommendation": "reset" if tripped and not in_cooldown else ("wait" if in_cooldown else "ok"),
        })
    tripped_count = sum(1 for r in reports if r["tripped"])
    return {
        "status": "ok",
        "trip_threshold": threshold,
        "circuit_breaker_cooldown_seconds": cooldown_secs,
        "providers": reports,
        "tripped_count": tripped_count,
        "healthy_count": len(reports) - tripped_count,
    }


def reset(provider_id: str, executor_settings: dict, pool_state: dict) -> dict:
    """Clear circuit breaker state for a provider. Returns updated pool_state."""
    from . import executor as _ex
    known = {p["id"] for p in _ex.provider_definitions(executor_settings)}
    if provider_id not in known:
        raise ValueError(f"Unknown provider: {provider_id!r}. Known: {sorted(known)}")
    st = pool_state.setdefault(provider_id, {})
    cleared = {k: st.pop(k, None) for k in ("failures", "retry_at", "cooldown_until")}
    st["circuit_breaker_reset_at"] = _now_iso()
    return {
        "status": "ok",
        "provider_id": provider_id,
        "cleared": {k: v for k, v in cleared.items() if v is not None},
        "reset_at": st["circuit_breaker_reset_at"],
    }


def auto_trip(provider_id: str, executor_settings: dict, pool_state: dict) -> dict | None:
    """
    Check if provider should be tripped. Call after recording a failure.
    Returns trip metadata if tripped, None otherwise.
    Side-effects: writes extended cooldown_until to pool_state[provider_id].
    """
    threshold = int(executor_settings.get("circuit_breaker_trip_threshold", DEFAULT_TRIP_THRESHOLD))
    cooldown_secs = float(executor_settings.get("circuit_breaker_cooldown_seconds", DEFAULT_COOLDOWN_SECONDS))
    st = pool_state.setdefault(provider_id, {})
    failures = int(st.get("failures", 0))
    if failures < threshold:
        return None
    extended = datetime.fromtimestamp(time.time() + cooldown_secs, timezone.utc).isoformat()
    st["cooldown_until"] = extended
    st["circuit_breaker_tripped_at"] = _now_iso()
    return {
        "provider_id": provider_id,
        "tripped": True,
        "failures": failures,
        "threshold": threshold,
        "cooldown_until": extended,
    }
