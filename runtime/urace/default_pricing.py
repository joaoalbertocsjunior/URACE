"""Default PricingAdapter implementation wrapping credit_ledger functions.

Swap this out for a custom PricingAdapter to change all borrow/mint/escrow
amounts without touching any P2P transport, ledger, or CLI code.

Usage::

    from .default_pricing import DEFAULT_PRICING
    cost = DEFAULT_PRICING.borrow_cost(loc=120, dependency_count=3)

    # Custom pricing (flat rate example):
    class FlatPricing:
        def borrow_cost(self, **_) -> int:
            return 100_000_000   # always 1 UCR
        def mint_amount(self, **_) -> int:
            return 50_000_000    # always 0.5 UCR per adoption
        def escrow_budget(self, base_borrow_cost, **_) -> int:
            return base_borrow_cost * 2
        def distribution_fee(self, borrow_cost, **_) -> int:
            return borrow_cost // 10
        def split_shares(self, **_) -> tuple[float, float]:
            return (0.6, 0.4)

    from .pricing_adapter import PricingAdapter
    assert isinstance(FlatPricing(), PricingAdapter)   # True at runtime
"""
from __future__ import annotations

from . import credit_ledger as _cl


class DefaultPricing:
    """Thin wrapper around credit_ledger pricing functions."""

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
        return _cl.apply_borrow_cost(
            loc=loc,
            dependency_count=dependency_count,
            test_count=test_count,
            quality_verifications=quality_verifications,
            total_adoptions=total_adoptions,
            exchange=exchange,
            estimated_network_size=estimated_network_size,
        )

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
        return _cl.mint_per_adoption(
            loc=loc,
            dependency_count=dependency_count,
            test_count=test_count,
            adopter_trust=adopter_trust,
            adoption_rank=adoption_rank,
            network_size=network_size,
            total_network_supply=total_network_supply,
            estimated_network_size=estimated_network_size,
            **kwargs,
        )

    def escrow_budget(
        self,
        base_borrow_cost: int,
        exchange=None,
        premium: float = 1.5,
    ) -> int:
        return _cl.escrow_budget_units(
            base_borrow_cost, exchange=exchange, premium=premium,
        )

    def distribution_fee(
        self,
        borrow_cost: int,
        quality_score: float | None = None,
    ) -> int:
        return _cl.distribution_fee_units(borrow_cost, quality_score=quality_score)

    def split_shares(self, exchange=None) -> tuple[float, float]:
        return _cl.consensus_split_shares(exchange=exchange)


# Singleton default — import and use directly.
DEFAULT_PRICING: DefaultPricing = DefaultPricing()
