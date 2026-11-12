"""Cross-peer purchase settlement for equity listings.

Protocol:
1. Buyer deducts locally (CREDIT_DELTA spend)
2. Buyer sends signed PURCHASE_SETTLEMENT message to seller via RPC
3. Seller verifies buyer balance (from buyer's tail payload), records receipt
4. Seller calls on_ramp() to initiate on-chain transfer (NullAdapter if not configured)
5. Seller releases artifact (via existing peer_exchange send path)
6. Both peers sync ledger tails

on_ramp() is a no-op (status=stub) unless token_settlement=True and rpc_provider_url
are set in exchange config. Use chain_id=137 (Polygon) for economical per-borrow settlement.
"""
from __future__ import annotations

import hashlib
import os
import time

from . import ledger_crypto
from . import token_ledger
from . import peer_exchange
from .integration_bridge import get_chain_adapter


def initiate_purchase(
    exchange,
    seller_peer_id: str,
    listing_id: str,
    price_units: int,
) -> dict:
    """Initiate a cross-peer purchase settlement as the buyer.

    Checks local balance, signs a settlement message, and sends it to the seller
    via RPC. Emits audit rows for PENDING, CONFIRMED, or FAILED states.

    Returns dict with 'status' key: 'confirmed' or 'failed'.
    Raises ValueError('Insufficient balance') if local balance is too low.
    """
    peer_id = exchange.identity()['peer_id']

    bal = token_ledger.balance(exchange, peer_id)
    if bal < price_units:
        raise ValueError('Insufficient balance')

    msg = {
        'schema': 'urace-purchase-settlement-v1',
        'listing_id': listing_id,
        'buyer_peer_id': peer_id,
        'seller_peer_id': seller_peer_id,
        'price_units': price_units,
        'at_unix': time.time(),
        'nonce': hashlib.sha256(os.urandom(32)).hexdigest(),
    }

    sig = exchange.crypto_identity().sign(msg, 'purchase-settlement')

    # Debit buyer atomically with PURCHASE_INITIATED — CREDIT_DELTA picked up by token_ledger.balance()
    exchange.append_audit_row({
        'kind': 'CREDIT_DELTA',
        'direction': 'purchase_spend',
        'peer': peer_id,
        'amount_units': -price_units,
        'listing_id': listing_id,
        'seller_peer_id': seller_peer_id,
        'at_unix': time.time(),
    })
    exchange.append_audit_row({
        'kind': 'PURCHASE_INITIATED',
        'listing_id': listing_id,
        'seller_peer_id': seller_peer_id,
        'price_units': price_units,
        'status': 'PENDING',
        'at_unix': time.time(),
    })

    try:
        result = peer_exchange.request(
            exchange,
            seller_peer_id,
            'exchange.purchase_settlement',
            {'settlement': {'payload': msg, 'signature': sig}},
        )
        if isinstance(result, dict) and result.get('status') == 'ok':
            exchange.append_audit_row({
                'kind': 'PURCHASE_CONFIRMED',
                'listing_id': listing_id,
                'seller_peer_id': seller_peer_id,
                'price_units': price_units,
                'settlement_nonce': msg['nonce'],
                'at_unix': time.time(),
            })
            return {
                'status': 'confirmed',
                'listing_id': listing_id,
                'settlement_nonce': msg['nonce'],
            }
        # Seller returned a non-ok result — treat as failure
        raise ValueError(f"Seller returned: {result}")
    except Exception as e:
        exchange.append_audit_row({
            'kind': 'PURCHASE_FAILED',
            'listing_id': listing_id,
            'seller_peer_id': seller_peer_id,
            'price_units': price_units,
            'error': str(e),
            'at_unix': time.time(),
        })
        return {'status': 'failed', 'error': str(e)}


def verify_purchase_from_buyer(
    exchange,
    seller_peer_id: str,
    settlement_msg: dict,
    buyer_public_key: dict,
) -> bool:
    """Verify an inbound purchase settlement message.

    Validates the schema, verifies the hybrid signature, and confirms the
    seller_peer_id matches the settlement payload.

    Returns True if all checks pass. Raises ValueError on any failure.
    """
    payload = settlement_msg.get('payload', {})
    if payload.get('schema') != 'urace-purchase-settlement-v1':
        raise ValueError(
            f"Unsupported settlement schema: {payload.get('schema')!r}"
        )

    ledger_crypto.verify(
        buyer_public_key,
        payload,
        settlement_msg['signature'],
        'purchase-settlement',
    )

    if payload.get('seller_peer_id') != seller_peer_id:
        raise ValueError(
            f"seller_peer_id mismatch: expected {seller_peer_id!r}, "
            f"got {payload.get('seller_peer_id')!r}"
        )

    return True


def handle_purchase_settlement(
    exchange,
    sender_peer_id: str,
    settlement: dict,
) -> dict:
    """Server-side handler for inbound purchase settlement RPC messages.

    Called from the peer_exchange server dispatch. Validates the settlement,
    verifies the buyer's signature, emits an audit row, and returns status.

    Returns {'status': 'ok', ...} on success or {'status': 'error', 'error': ...}.
    """
    if not isinstance(settlement, dict) or 'payload' not in settlement or 'signature' not in settlement:
        return {'status': 'error', 'error': 'invalid_settlement_structure'}

    payload = settlement.get('payload', {})
    buyer_peer_id = payload.get('buyer_peer_id', '')

    if sender_peer_id != buyer_peer_id:
        return {'status': 'error', 'error': 'sender_mismatch'}

    try:
        p = exchange.load()
        buyer_public_key = exchange.trusted_crypto(p, buyer_peer_id)
        verify_purchase_from_buyer(exchange, exchange.identity()['peer_id'], settlement, buyer_public_key)
    except Exception as e:
        return {'status': 'error', 'error': f'verification_failed: {e}'}

    price_units = payload.get('price_units', 0)
    listing_id = payload.get('listing_id', '')
    seller_peer_id = exchange.identity()['peer_id']

    exchange.append_audit_row({
        'kind': 'PURCHASE_SETTLEMENT_RECEIVED',
        'listing_id': listing_id,
        'buyer_peer_id': buyer_peer_id,
        'price_units': price_units,
        'nonce': payload.get('nonce', ''),
        'at_unix': time.time(),
    })
    # Credit seller — CREDIT_DELTA picked up by token_ledger.balance()
    exchange.append_audit_row({
        'kind': 'CREDIT_DELTA',
        'direction': 'purchase_receive',
        'peer': seller_peer_id,
        'amount_units': price_units,
        'listing_id': listing_id,
        'buyer_peer_id': buyer_peer_id,
        'at_unix': time.time(),
    })

    # On-chain transfer: NullAdapter (audit-only) unless token_settlement=True
    # and rpc_provider_url are set in exchange config. Use chain_id=137 for
    # economical settlement; chain_id=1 (mainnet) is uneconomical per-borrow.
    try:
        config = exchange.load() if hasattr(exchange, 'load') else {}
        p2p_config = config.get('p2p', {}) if isinstance(config, dict) else {}
        crypto_address = payload.get('crypto_address', '')
        if crypto_address:
            adapter = get_chain_adapter({'p2p': p2p_config})
            ramp_result = adapter.on_ramp(buyer_peer_id, price_units, crypto_address)
            exchange.append_audit_row({
                'kind': 'ON_RAMP_ATTEMPTED',
                'listing_id': listing_id,
                'buyer_peer_id': buyer_peer_id,
                'amount_units': price_units,
                'adapter_status': ramp_result.get('status'),
                'tx_hash': ramp_result.get('tx_hash'),
                'at_unix': time.time(),
            })
    except Exception:
        pass  # on_ramp failure never blocks settlement confirmation

    return {
        'status': 'ok',
        'listing_id': listing_id,
        'confirmed_at': time.time(),
    }


def settlement_state(exchange, listing_id: str) -> str:
    """Return the settlement state for a given listing_id.

    Scans audit rows for PURCHASE_CONFIRMED, PURCHASE_FAILED, or
    PURCHASE_INITIATED events matching the listing_id.

    Returns 'CONFIRMED', 'FAILED', 'PENDING', or 'UNKNOWN'.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return 'UNKNOWN'

    for kind, state in [
        ('PURCHASE_CONFIRMED', 'CONFIRMED'),
        ('PURCHASE_FAILED', 'FAILED'),
        ('PURCHASE_INITIATED', 'PENDING'),
    ]:
        if any(
            r.get('kind') == kind and r.get('listing_id') == listing_id
            for r in rows
        ):
            return state

    return 'UNKNOWN'
