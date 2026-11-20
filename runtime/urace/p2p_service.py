"""High-level P2P service facade for exchange_cli.py.

Instead of exchange_cli.py importing peer_exchange, credit_ledger,
peer_work_market, peer_discovery, etc. inline in each function, wire
high-level operations through P2PService.  The facade stays thin — it
delegates immediately — but it makes the dependency boundary explicit and
lets CLI handlers be tested by passing a mock P2PService.

Usage::

    from .p2p_service import P2PService

    svc = P2PService(exchange)
    result = svc.credit_summary(root)
    result = svc.work_requests(limit=20)
"""
from __future__ import annotations

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
