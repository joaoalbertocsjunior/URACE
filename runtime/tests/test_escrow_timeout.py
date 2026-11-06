"""Tests for escrow_timeout.py — auto-refund on stalled DEK delivery."""

import time
import pytest
from urace.escrow_timeout import (
    DEFAULT_ESCROW_TIMEOUT_HOURS,
    check_escrow_timeouts,
    process_escrow_refunds,
)


class _MockExchange:
    """Minimal in-memory exchange mock with audit_rows / append_audit_row."""

    def __init__(self, rows=None):
        self._rows = list(rows or [])

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)


def _filled_row(listing_id, feature_id, at_unix, buyer="buyer-1", seller="seller-1", price=100):
    return {
        "kind": "EQUITY_LISTING_FILLED",
        "listing_id": listing_id,
        "feature_id": feature_id,
        "buyer_peer_id": buyer,
        "seller_peer_id": seller,
        "at_unix": at_unix,
    }


def _listing_row(listing_id, feature_id, price=100):
    return {
        "kind": "EQUITY_LISTING",
        "listing_id": listing_id,
        "feature_id": feature_id,
        "ask_price_units": price,
        "seller_id": "seller-1",
    }


def _grant_row(listing_id):
    return {
        "kind": "ARTIFACT_KEY_GRANT",
        "listing_id": listing_id,
        "feature_id": "feat-1",
        "at_unix": time.time(),
    }


# ── 1. no overdue returns empty ───────────────────────────────────────────────

def test_no_filled_rows_returns_empty():
    ex = _MockExchange()
    assert check_escrow_timeouts(ex) == []


def test_recent_fill_not_overdue():
    """Fill happened 1 hour ago — below timeout, should not appear."""
    now = time.time()
    ex = _MockExchange([
        _listing_row("lst-1", "feat-1"),
        _filled_row("lst-1", "feat-1", now - 3600),
    ])
    assert check_escrow_timeouts(ex) == []


# ── 2. overdue detected correctly ────────────────────────────────────────────

def test_overdue_fill_detected():
    timeout_secs = DEFAULT_ESCROW_TIMEOUT_HOURS * 3600
    old_fill_time = time.time() - timeout_secs - 10
    ex = _MockExchange([
        _listing_row("lst-2", "feat-2", price=50),
        _filled_row("lst-2", "feat-2", old_fill_time),
    ])
    overdue = check_escrow_timeouts(ex)
    assert len(overdue) == 1
    assert overdue[0]["listing_id"] == "lst-2"
    assert overdue[0]["overdue_hours"] > 0


def test_overdue_includes_correct_fields():
    timeout_secs = DEFAULT_ESCROW_TIMEOUT_HOURS * 3600
    old_time = time.time() - timeout_secs - 100
    ex = _MockExchange([
        _listing_row("lst-3", "feat-3", price=200),
        _filled_row("lst-3", "feat-3", old_time, buyer="buyer-X", seller="seller-Y"),
    ])
    overdue = check_escrow_timeouts(ex)
    assert overdue[0]["buyer_peer_id"] == "buyer-X"
    assert overdue[0]["seller_peer_id"] == "seller-Y"
    assert overdue[0]["price_units"] == 200


# ── 3. not overdue if key grant already emitted ───────────────────────────────

def test_key_grant_present_not_overdue():
    timeout_secs = DEFAULT_ESCROW_TIMEOUT_HOURS * 3600
    old_time = time.time() - timeout_secs - 100
    ex = _MockExchange([
        _listing_row("lst-4", "feat-4"),
        _filled_row("lst-4", "feat-4", old_time),
        _grant_row("lst-4"),
    ])
    assert check_escrow_timeouts(ex) == []


# ── 4. refund emitted once (idempotent) ───────────────────────────────────────

def test_process_refund_emitted():
    timeout_secs = DEFAULT_ESCROW_TIMEOUT_HOURS * 3600
    old_time = time.time() - timeout_secs - 100
    ex = _MockExchange([
        _listing_row("lst-5", "feat-5", price=75),
        _filled_row("lst-5", "feat-5", old_time),
    ])
    processed = process_escrow_refunds(ex)
    assert len(processed) == 1

    rows = ex.audit_rows()
    refund_rows = [r for r in rows if r.get("kind") == "ESCROW_REFUND"]
    assert len(refund_rows) == 1
    assert refund_rows[0]["listing_id"] == "lst-5"
    assert refund_rows[0]["reason"] == "dek_delivery_timeout"


def test_process_refund_idempotent():
    """Calling process_escrow_refunds twice must not double-emit."""
    timeout_secs = DEFAULT_ESCROW_TIMEOUT_HOURS * 3600
    old_time = time.time() - timeout_secs - 100
    ex = _MockExchange([
        _listing_row("lst-6", "feat-6", price=50),
        _filled_row("lst-6", "feat-6", old_time),
    ])
    process_escrow_refunds(ex)
    process_escrow_refunds(ex)

    rows = ex.audit_rows()
    refund_rows = [r for r in rows if r.get("kind") == "ESCROW_REFUND"]
    assert len(refund_rows) == 1


def test_credit_delta_rows_emitted_on_refund():
    """CREDIT_DELTA escrow_refund and escrow_clawback must be emitted."""
    timeout_secs = DEFAULT_ESCROW_TIMEOUT_HOURS * 3600
    old_time = time.time() - timeout_secs - 100
    ex = _MockExchange([
        _listing_row("lst-7", "feat-7", price=120),
        _filled_row("lst-7", "feat-7", old_time, buyer="buyer-A", seller="seller-B"),
    ])
    process_escrow_refunds(ex)

    rows = ex.audit_rows()
    deltas = [r for r in rows if r.get("kind") == "CREDIT_DELTA"]
    directions = {r["direction"] for r in deltas}
    assert "escrow_refund" in directions
    assert "escrow_clawback" in directions

    refund_delta = next(r for r in deltas if r["direction"] == "escrow_refund")
    assert refund_delta["peer"] == "buyer-A"
    assert refund_delta["amount_units"] == 120

    clawback_delta = next(r for r in deltas if r["direction"] == "escrow_clawback")
    assert clawback_delta["peer"] == "seller-B"
    assert clawback_delta["amount_units"] == -120
