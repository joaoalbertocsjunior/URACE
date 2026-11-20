"""CostLedger — executor-agnostic per-operation cost tracking.

Records USD cost, token counts, latency, and provider metadata for every
executor call. Enables per-provider/model/operation breakdowns, timeline,
and budget gate enforcement.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CostRecord:
    """Uniform cost record across all executor types."""
    provider: str               # "anthropic", "openai", "local", "custom"
    model: str
    operation_id: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    usd_cost: float | None = None   # None if provider unknown to cost adapter
    latency_ms: float = 0.0
    timestamp: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read_tokens + self.cache_write_tokens


class CostLedger:
    """In-process ledger for accumulating CostRecords within a session.

    Thread-safe for concurrent executor calls via a simple list append
    (CPython GIL ensures list.append atomicity).
    """

    def __init__(self) -> None:
        self._records: list[CostRecord] = []

    def record(
        self,
        provider: str,
        model: str,
        operation_id: str,
        input_tokens: int,
        output_tokens: int,
        *,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        latency_ms: float = 0.0,
        adapter=None,
    ) -> CostRecord:
        """Create and store a CostRecord, computing USD cost via adapter."""
        from ._common import now as _now
        from .cost_adapter import make_cost_adapter
        _adapter = adapter or make_cost_adapter()
        usd = _adapter.cost_for_usage(
            model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens
        )
        rec = CostRecord(
            provider=provider,
            model=model,
            operation_id=operation_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            usd_cost=usd,
            latency_ms=latency_ms,
            timestamp=_now(),
        )
        self._records.append(rec)
        return rec

    def records(self) -> list[CostRecord]:
        return list(self._records)

    def total_usd(self) -> float | None:
        """Sum of all known USD costs; None if no cost has been recorded."""
        known = [r.usd_cost for r in self._records if r.usd_cost is not None]
        return sum(known) if known else None

    def summary(
        self,
        *,
        by: str = "total",
    ) -> dict[str, Any]:
        """Return aggregated summary.

        by: "total" | "provider" | "model" | "operation"
        """
        records = self._records
        total = self.total_usd()
        base: dict[str, Any] = {
            "total_records": len(records),
            "total_input_tokens": sum(r.input_tokens for r in records),
            "total_output_tokens": sum(r.output_tokens for r in records),
            "total_tokens": sum(r.total_tokens for r in records),
            "total_usd": total,
        }
        if by == "total":
            return base

        groups: dict[str, list[CostRecord]] = {}
        for r in records:
            key = getattr(r, {"provider": "provider", "model": "model", "operation": "operation_id"}.get(by, "provider"))
            groups.setdefault(key, []).append(r)

        breakdown: dict[str, Any] = {}
        for group_key, recs in groups.items():
            group_usd = [r.usd_cost for r in recs if r.usd_cost is not None]
            breakdown[group_key] = {
                "records": len(recs),
                "input_tokens": sum(r.input_tokens for r in recs),
                "output_tokens": sum(r.output_tokens for r in recs),
                "usd_cost": sum(group_usd) if group_usd else None,
            }
        return {**base, by: breakdown}

    def cost_snapshot(self) -> dict[str, Any]:
        """Compact dict for M2M envelope cost_snapshot field."""
        return {
            "records": len(self._records),
            "total_usd": self.total_usd(),
            "total_tokens": sum(r.total_tokens for r in self._records),
            "providers": list({r.provider for r in self._records}),
        }

    def exceeds_budget(self, budget_usd: float) -> bool:
        """Return True if total known USD cost exceeds budget_usd."""
        total = self.total_usd()
        return total is not None and total > budget_usd


# Module-level default ledger for the current process (singleton per process).
_DEFAULT_LEDGER = CostLedger()


def get_default_ledger() -> CostLedger:
    """Return the process-level default CostLedger."""
    return _DEFAULT_LEDGER
