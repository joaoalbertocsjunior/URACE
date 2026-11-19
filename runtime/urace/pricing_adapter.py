"""Protocol for P2P pricing and reward logic.

Separating pricing from the P2P machinery means you can swap borrow costs,
mint amounts, and escrow budgets without touching any transport, ledger, or
CLI code.  Pass any PricingAdapter implementation to the functions that
currently call credit_ledger directly.

Usage::

    from .pricing_adapter import PricingAdapter
    from .default_pricing import DEFAULT_PRICING

    def request_borrow(exchange, feature, pricing: PricingAdapter = DEFAULT_PRICING):
        cost = pricing.borrow_cost(loc=feature.loc, ...)
        ...

To replace pricing::

    class FlatPricing:
        def borrow_cost(self, **_) -> int:
            return 100_000_000   # always 1 UCR

    pricing = FlatPricing()   # satisfies PricingAdapter at runtime
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PricingAdapter(Protocol):
    """Interface for all pricing/reward computations in the P2P economy.

    Implementations must be stateless or thread-safe; the same instance
    is shared across the lifetime of an exchange session.
    """

    def borrow_cost(
        self,
        loc: int = 0,
        dependency_count: int = 0,
        test_count: int = 0,
        quality_verifications: int = 0,
        total_adoptions: int = 0,
        exchange=None,
        estimated_network_size: int = 1,
    ) -> int:
        """Final borrow cost in base units, including consensus floor and jitter."""
        ...

    def mint_amount(
        self,
        loc: int = 0,
        dependency_count: int = 0,
        test_count: int = 0,
        adopter_trust: float = 0.5,
        adoption_rank: int = 1,
        network_size: int = 1,
        total_network_supply: int = 0,
        estimated_network_size: int = 1,
        **kwargs,
    ) -> int:
        """Tokens to mint for one adoption event, in base units."""
        ...

    def escrow_budget(
        self,
        base_borrow_cost: int,
        exchange=None,
        premium: float = 1.5,
    ) -> int:
        """Final escrow budget in base units (consensus floor + jitter applied)."""
        ...

    def distribution_fee(
        self,
        borrow_cost: int,
        quality_score: float | None = None,
    ) -> int:
        """Fee for the feature's distributor in base units."""
        ...

    def split_shares(self, exchange=None) -> tuple[float, float]:
        """(requester_share, hired_share) — must sum to 1.0."""
        ...
