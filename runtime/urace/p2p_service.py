"""High-level P2P service facade for exchange_cli.py and cli_cycle.py.

Instead of cli_cycle.py importing peer_exchange, credit_ledger,
peer_work_market, peer_discovery, etc. inline in each function, wire
high-level operations through P2PService or the module-level helpers here.
The facade stays thin — it delegates immediately — but it makes the
dependency boundary explicit and lets CLI handlers be tested without a
live Exchange on disk.

Usage::

    from .p2p_service import P2PService, routing_decision, find_p2p_feature_candidate

    svc = P2PService(exchange)
    result = svc.credit_summary(root)

    # config-based helpers — no prior Exchange construction needed
    route = routing_decision(config, state)
    candidate = find_p2p_feature_candidate(config, state)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .network_adapter import NetworkAdapter


class P2PService:
    """Thin orchestration layer over Exchange and satellite P2P modules.

    Every method delegates to the appropriate module immediately.  No business
    logic lives here — this is a seam, not an implementation.
    """

    def __init__(self, exchange: NetworkAdapter) -> None:
        self._ex = exchange

    # ── Credit / token ────────────────────────────────────────────────────────

    def credit_summary(self, root: str) -> dict[str, Any]:
        from .credit_ledger import summary
        return summary(root)

    def credit_balance(self, root: str, peer_id: str) -> int:
        from .credit_ledger import balance
        return balance(root, peer_id)

    def credit_history(self, root: str, peer_id: str, limit: int = 50) -> list[dict]:
        from .credit_ledger import history
        return history(root, peer_id, limit)

    def token_summary(self) -> dict[str, Any]:
        from . import token_ledger as _tl
        return _tl.summary(self._ex)

    # ── Work market ───────────────────────────────────────────────────────────

    def work_requests(self, *, limit: int = 50) -> list[dict]:
        from . import peer_work_market as _pwm
        return _pwm.list_requests(self._ex, limit=limit)

    def post_work_request(self, requester_id: str, feature_spec: dict, budget_units: int) -> dict:
        from . import peer_work_market as _pwm
        return _pwm.post_request(self._ex, requester_id, feature_spec, budget_units)

    # ── Peer management ───────────────────────────────────────────────────────

    def discover_peers(self, seconds: int = 3) -> dict[str, Any]:
        from . import peer_exchange as _pe
        return _pe.discover(self._ex, seconds)

    def select_peers(self) -> dict[str, Any]:
        from . import peer_selection as _ps
        return _ps.cache(self._ex)

    # ── Exchange summary ──────────────────────────────────────────────────────

    def summary(self, *, detail: bool = False, limit: int = 50,
                offset: int = 0, peer: str | None = None,
                feature: str | None = None) -> dict[str, Any]:
        return self._ex.summary(
            detail=detail, limit=limit, offset=offset,
            peer=peer, feature=feature,
        )


# ── Config-based helpers (no prior Exchange construction required) ─────────────
# These are called from cli_cycle.py so that the cycle orchestrator does not
# import peer_exchange / credit_ledger / peer_work_market directly.


def _ts_age(ts_iso: str) -> float:
    """Seconds since an ISO timestamp. Returns inf on parse failure."""
    try:
        return datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(ts_iso).timestamp()
    except Exception:
        return float("inf")


def routing_decision(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Compute executor vs. network-hire routing score.

    Returns peer_work_market.routing_score() result or a safe executor fallback.
    Never raises — the cycle must always get a routing answer.
    """
    try:
        from . import peer_exchange as _pe
        from . import credit_ledger as _cl
        from . import peer_work_market as _pwm
        from ._common import state_path

        exchange_root = state_path(config).parent / "exchange"
        if not exchange_root.exists():
            return {'route': 'executor', 'confidence': 0.5, 'reason': 'no exchange dir'}
        exchange = _pe.Exchange(exchange_root)
        if not exchange.load().get("enabled"):
            return {'route': 'executor', 'confidence': 0.5, 'reason': 'exchange disabled'}

        _local_id = config.get("peer_id", "local")
        balance = _cl.balance(state_path(config).parent, _local_id)
        baseline = _cl.BASELINE_GRANT_UNITS
        executor_cost = int(config.get("executor", {}).get("cost_per_call_units", _cl.UNIT))

        _planned = [o for o in state.get("objectives", []) if o.get("status") == "planned"]
        complexity = 0.4
        if _planned:
            _loc_est = int(_planned[0].get("estimated_loc", 0))
            complexity = min(1.0, 0.3 + _loc_est / 500.0) if _loc_est else 0.4

        peers = []
        try:
            for row in exchange.audit_rows():
                if row.get('kind') == 'PEER_ANNOUNCE' and row.get('peer_id'):
                    peers.append({
                        'peer_id': row['peer_id'],
                        'combined_rep': float(row.get('combined_rep', 0.0)),
                    })
        except Exception:
            pass

        return _pwm.routing_score(
            exchange=exchange,
            local_credit_balance=balance,
            baseline_grant_units=baseline,
            spec_complexity=complexity,
            executor_cost_units=executor_cost,
            available_peers=peers,
        )
    except Exception:
        return {'route': 'executor', 'confidence': 0.5, 'reason': 'routing_score error'}


def find_p2p_feature_candidate(
    config: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any] | None:
    """Score P2P feature candidates and return the best one, or None.

    Returns a candidate dict with all fields needed for the caller to
    construct an objective record, or None when P2P is disabled / no
    candidate clears the ROI threshold.  Never raises.
    """
    try:
        if not config.get("p2p", {}).get("feature_borrow_enabled", False):
            return None

        from . import peer_exchange as _pe
        from . import credit_ledger as _cl
        from . import product_similarity as _ps
        from ._common import state_path, nullable_limit, now

        exchange_root = state_path(config).parent / "exchange"
        if not exchange_root.exists():
            return None
        exchange = _pe.Exchange(exchange_root)
        if not exchange.load().get("enabled"):
            return None

        candidates = _ps.score_features(config, state, exchange, timeout_seconds=2.0)
        if not candidates:
            return None

        _exec_state = state.get("executor_state", {})
        _calls_24h = [c for c in _exec_state.get("executor_calls", [])
                      if _ts_age(c.get("at", now())) < 86400]
        _limit = nullable_limit(config.get("executor", {}), "max_executor_calls_per_24h", 2)
        call_pressure = min(1.0, len(_calls_24h) / _limit) if _limit else 0.0
        _local_id = config.get("peer_id", "local")
        _bal = _cl.balance(state_path(config).parent, _local_id)
        _baseline = _cl.BASELINE_GRANT_UNITS
        credit_pressure = max(0.0, min(1.0, 1.0 - _bal / max(1, _baseline * 10)))
        budget_pressure = max(call_pressure, credit_pressure)

        BASE_THRESHOLD = float(config.get("p2p", {}).get("p2p_roi_threshold", 0.55))
        adjusted = BASE_THRESHOLD * (1.0 - 0.5 * budget_pressure)

        best = candidates[0]
        if best.get("score", 0.0) < adjusted:
            return None

        if best.get("cold_start") and budget_pressure < 0.8:
            _non_cold = [c for c in candidates if not c.get("cold_start") and c.get("score", 0) >= adjusted]
            if not _non_cold:
                return None
            best = _non_cold[0]

        _intent_floor = max(0.15, 0.30 * (1.0 - budget_pressure))
        if best.get("intent_similarity", 0.0) < _intent_floor:
            return None

        _borrow_cost = _cl.feature_borrow_cost_units()
        if _cl.balance(state_path(config).parent, _local_id) < _borrow_cost:
            return None

        return {
            'feature_id': best['feature_id'],
            'score': best.get('score', 0.0),
            'adjusted_threshold': adjusted,
            'budget_pressure': budget_pressure,
            'call_pressure': call_pressure,
            'credit_pressure': credit_pressure,
            'intent_similarity': best.get('intent_similarity', 0.0),
            'peer_count': best.get('peer_count', 0),
            'confidence': best.get('confidence', 'low'),
            'rationale': best.get('rationale', ''),
            'cold_start': best.get('cold_start', False),
        }
    except Exception:
        return None
