"""CostAdapter port — executor-agnostic USD cost calculation.

Follows the same port pattern as LedgerAdapter and NetworkAdapter.
Adding a new executor type = implementing this Protocol, nothing else.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CostAdapter(Protocol):
    """Port for computing USD cost from token usage."""

    def cost_for_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> float | None:
        """Return USD cost or None if the model is not priced."""
        ...


class LiteLLMCostAdapter:
    """CostAdapter backed by litellm's auto-updated price tables.

    litellm is used ONLY as a pricing calculator — no API calls are made
    through it. URACE keeps its direct Anthropic SDK calls unchanged.
    """

    def cost_for_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> float | None:
        try:
            from litellm import cost_per_token
            input_cost, output_cost = cost_per_token(
                model=model,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
            )
            # litellm doesn't expose per-token cache pricing directly;
            # cache_read is typically ~10% of input price, cache_write ~125%
            cache_read_cost = cache_read_tokens * (input_cost / max(1, input_tokens)) * 0.1 if cache_read_tokens and input_tokens else 0.0
            cache_write_cost = cache_write_tokens * (input_cost / max(1, input_tokens)) * 1.25 if cache_write_tokens and input_tokens else 0.0
            return input_cost + output_cost + cache_read_cost + cache_write_cost
        except Exception:
            return None


class NullCostAdapter:
    """CostAdapter for local/unknown models where cost cannot be computed."""

    def cost_for_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> float | None:
        return None


def make_cost_adapter() -> LiteLLMCostAdapter | NullCostAdapter:
    """Return LiteLLMCostAdapter if litellm is available, else NullCostAdapter."""
    try:
        import litellm  # noqa: F401
        return LiteLLMCostAdapter()
    except ImportError:
        return NullCostAdapter()
