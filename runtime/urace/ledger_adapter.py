"""Minimal Protocol interface for P2P audit ledger access.

Modules that need read/write access to the audit chain should annotate
their `exchange` parameter as LedgerAdapter instead of the concrete Exchange
class.  Any object satisfying these four methods can be passed instead,
enabling independent unit testing without a live Exchange directory.

Usage::

    from .ledger_adapter import LedgerAdapter

    def balance(exchange: LedgerAdapter, peer_id: str) -> float:
        rows = exchange.audit_rows()   # works on Exchange or any mock
        ...
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LedgerAdapter(Protocol):
    """Minimal interface required by credit_ledger, token_ledger, peer_work_market."""

    def audit_rows(self) -> list[dict]:
        """Return all verified audit rows in chain order."""
        ...

    def append_audit_row(self, row: dict) -> None:
        """Append a pre-formed audit row dict (kind field required)."""
        ...

    def event(self, kind: str, **details) -> dict:
        """Append a new audit event and return the signed row."""
        ...

    def load(self) -> dict:
        """Return the current policy/config dict (read-only snapshot)."""
        ...
