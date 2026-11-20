"""Protocol for P2P exchange objects used by network and peer-selection modules.

Modules that drive peer discovery, selection, and network routing annotate
their exchange parameter as NetworkAdapter instead of the concrete Exchange.
Any object satisfying these methods can be passed instead, enabling unit
testing without a live Exchange directory on disk.

Usage::

    from .network_adapter import NetworkAdapter

    def refresh(exchange: NetworkAdapter, limit: int = 3) -> dict:
        p = exchange.load()
        ...
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .ledger_adapter import LedgerAdapter


@runtime_checkable
class NetworkAdapter(LedgerAdapter, Protocol):
    """LedgerAdapter extended with network-layer operations.

    Implementations must also satisfy LedgerAdapter (audit_rows, append_audit_row,
    event, load).  The concrete Exchange class satisfies both.
    """

    root: Path

    def identity(self) -> dict: ...
    def crypto_identity(self) -> Any: ...
    def lock(self) -> AbstractContextManager[None]: ...
    def permitted(self, policy: dict, peer: str, feature: str, direction: str) -> bool: ...
    def rule(self, peer: str, feature: str, direction: str, allow: bool) -> None: ...
