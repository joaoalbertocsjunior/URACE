"""Protocol for trial receipt delivery and settlement.

trial_receipt.py's deliver_receipt() calls peer_exchange.request() and
triggers implicit token-ledger state via audit rows.  Callers that want
to record a receipt don't need to know whether it goes to a P2P peer, a
local file, or a test stub.

Usage::

    from .receipt_handler import ReceiptHandler, P2PReceiptHandler

    handler: ReceiptHandler = P2PReceiptHandler(exchange)
    ok, receipt_id = handler.deliver(receipt_dict, peer_id)

To test receipt recording without network::

    class MemoryReceiptHandler:
        def __init__(self):
            self.delivered = []
        def deliver(self, receipt, peer_id=None):
            self.delivered.append(receipt)
            return True, receipt.get('id', 'test-id')

    handler = MemoryReceiptHandler()
    assert isinstance(handler, ReceiptHandler)
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ReceiptHandler(Protocol):
    """Interface for delivering trial qualification receipts."""

    def deliver(
        self,
        receipt: dict[str, Any],
        peer_id: str | None = None,
    ) -> tuple[bool, str]:
        """Deliver receipt to peer (or store locally if peer_id is None).

        Returns (success, receipt_id).
        """
        ...


class P2PReceiptHandler:
    """Delivers receipts via P2P exchange to the originating peer."""

    def __init__(self, exchange) -> None:
        self._ex = exchange

    def deliver(
        self,
        receipt: dict[str, Any],
        peer_id: str | None = None,
    ) -> tuple[bool, str]:
        from . import trial_receipt as _tr
        from . import peer_exchange as _pe
        receipt_id = receipt.get('id', '')
        if peer_id is None:
            # Local-only: just record the event
            self._ex.event('TRIAL_RECEIPT_LOCAL', receipt_id=receipt_id)
            return True, receipt_id
        try:
            _pe.request(self._ex, peer_id, 'exchange.trial_receipt', {'receipt': receipt})
            return True, receipt_id
        except Exception:
            return False, receipt_id


class LocalReceiptHandler:
    """Records receipts locally without any network call.  Useful in tests."""

    def __init__(self) -> None:
        self.delivered: list[dict] = []

    def deliver(
        self,
        receipt: dict[str, Any],
        peer_id: str | None = None,
    ) -> tuple[bool, str]:
        self.delivered.append({'receipt': receipt, 'peer_id': peer_id})
        return True, receipt.get('id', 'local')
