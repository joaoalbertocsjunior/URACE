"""escrow_timeout.py — Escrow auto-refund for stalled DEK deliveries.

If a creator fills an EQUITY_LISTING but never emits ARTIFACT_KEY_GRANT
within DEFAULT_ESCROW_TIMEOUT_HOURS, the buyer's credits are refunded
automatically.

The logic is intentionally idempotent: a listing that already has an
ESCROW_REFUND row is skipped.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # exchange type is duck-typed

DEFAULT_ESCROW_TIMEOUT_HOURS: int = 48


def check_escrow_timeouts(exchange) -> list[dict]:
    """Return overdue EQUITY_LISTING_FILLED rows without an ARTIFACT_KEY_GRANT.

    Each entry: {listing_id, feature_id, buyer_peer_id, seller_peer_id,
                 fill_time, overdue_hours, price_units}
    """
    rows = exchange.audit_rows()
    timeout_secs = DEFAULT_ESCROW_TIMEOUT_HOURS * 3600
    now = time.time()

    filled = {r["listing_id"]: r for r in rows
              if r.get("kind") == "EQUITY_LISTING_FILLED"}
    granted = {r["listing_id"] for r in rows
               if r.get("kind") == "ARTIFACT_KEY_GRANT"}
    refunded = {r["listing_id"] for r in rows
                if r.get("kind") == "ESCROW_REFUND"}

    overdue: list[dict] = []
    for listing_id, fill_row in filled.items():
        if listing_id in granted:
            continue
        if listing_id in refunded:
            continue
        fill_time = float(fill_row.get("at_unix", 0))
        elapsed = now - fill_time
        if elapsed < timeout_secs:
            continue

        # Retrieve price from the matching EQUITY_LISTING row
        listing_row = next(
            (r for r in rows
             if r.get("kind") == "EQUITY_LISTING"
             and r.get("listing_id") == listing_id),
            None,
        )
        price_units = int((listing_row or {}).get("ask_price_units", 0))
        buyer_peer_id = fill_row.get("buyer_peer_id", fill_row.get("peer_id", ""))
        seller_peer_id = fill_row.get("seller_peer_id", fill_row.get("seller_id", ""))

        overdue.append({
            "listing_id": listing_id,
            "feature_id": fill_row.get("feature_id", ""),
            "buyer_peer_id": buyer_peer_id,
            "seller_peer_id": seller_peer_id,
            "fill_time": fill_time,
            "overdue_hours": round(elapsed / 3600, 2),
            "price_units": price_units,
        })

    return overdue


def process_escrow_refunds(exchange) -> list[dict]:
    """Emit ESCROW_REFUND + CREDIT_DELTA rows for each overdue listing.

    Idempotent: listings that already have an ESCROW_REFUND are skipped.
    Returns list of processed refund dicts.
    """
    overdue = check_escrow_timeouts(exchange)
    processed: list[dict] = []
    now = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()

    for item in overdue:
        listing_id = item["listing_id"]
        feature_id = item["feature_id"]
        buyer_peer_id = item["buyer_peer_id"]
        seller_peer_id = item["seller_peer_id"]
        price_units = item["price_units"]

        exchange.append_audit_row({
            "kind": "ESCROW_REFUND",
            "listing_id": listing_id,
            "feature_id": feature_id,
            "buyer_peer_id": buyer_peer_id,
            "refund_units": price_units,
            "reason": "dek_delivery_timeout",
            "at_unix": now,
            "at": now_iso,
        })
        # Credit buyer back
        exchange.append_audit_row({
            "kind": "CREDIT_DELTA",
            "direction": "escrow_refund",
            "peer": buyer_peer_id,
            "amount_units": price_units,
            "listing_id": listing_id,
            "feature_id": feature_id,
            "at_unix": now,
            "at": now_iso,
        })
        # Clawback from seller
        if seller_peer_id:
            exchange.append_audit_row({
                "kind": "CREDIT_DELTA",
                "direction": "escrow_clawback",
                "peer": seller_peer_id,
                "amount_units": -price_units,
                "listing_id": listing_id,
                "feature_id": feature_id,
                "at_unix": now,
                "at": now_iso,
            })

        refund_record = {**item, "refund_emitted": True}
        processed.append(refund_record)

    return processed
