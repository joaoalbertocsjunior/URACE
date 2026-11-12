"""Tests for urace.equity_auto_trade covering 5 areas."""
from __future__ import annotations
import time
import pytest
from unittest.mock import patch


class MockExchange:
    def __init__(self, peer_id='test-peer'):
        self._rows = []
        self._peer_id = peer_id
        self._state = {'token_settlement': False, 'token_baseline_grant': 3}

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)

    def load(self):
        return dict(self._state)

    def identity(self):
        return {'peer_id': self._peer_id}

    def crypto_identity(self):
        m = type('CI', (), {'sign': lambda s, d, t: 'mock-sig'})()
        return m


# ── Helper: inject an EQUITY_GRANT row so list_for_sale doesn't fail on
#    "feature_equity.equity_holdings" (seller must hold bp) ──────────────────

def _inject_grant(exchange, feature_id, seller_id, basis_points):
    """Pre-seed the exchange with a CREDIT_DELTA that makes equity_holdings return nonzero."""
    # equity_holdings reads EQUITY_GRANT rows
    exchange.append_audit_row({
        'kind': 'EQUITY_GRANT',
        'feature_id': feature_id,
        'peer_id': seller_id,
        'basis_points': basis_points,
        'at_unix': time.time(),
        'at': '2026-01-01T00:00:00+00:00',
    })


# ── 1. list_for_sale happy path ───────────────────────────────────────────────

def test_list_for_sale_emits_equity_listing():
    """list_for_sale emits EQUITY_LISTING audit row with correct fields."""
    from urace import equity_auto_trade as eat

    exchange = MockExchange(peer_id='seller-peer')
    feature_id = 'feat-aaa'
    seller_id = 'seller-peer'
    bp = 1000
    ask = 10

    _inject_grant(exchange, feature_id, seller_id, bp)

    with (
        patch.object(eat, 'feature_depletion_status', return_value={
            'state': 'HEALTHY', 'adoption_rate': 0.1, 'adoption_count': 1,
            'supply_pressure': 0.9, 'remaining_adopters': 9, 'listable': True,
        }),
        patch('urace.feature_equity.equity_holdings', return_value={seller_id: bp}),
        patch('urace.feature_equity.EQUITY_MIN_TRADE_BP', 1),
    ):
        listing_id = eat.list_for_sale(
            exchange, feature_id, seller_id,
            basis_points=bp, ask_price_units=ask,
        )

    assert listing_id.startswith('elst-')
    rows = exchange.audit_rows()
    listing_rows = [r for r in rows if r.get('kind') == 'EQUITY_LISTING']
    assert len(listing_rows) == 1
    lr = listing_rows[0]
    assert lr['feature_id'] == feature_id
    assert lr['seller_id'] == seller_id
    assert lr['basis_points'] == bp
    assert lr['ask_price_units'] == ask
    assert lr['listing_id'] == listing_id


# ── 2. fill_listing emits EQUITY_LISTING_FILLED ───────────────────────────────

def test_fill_listing_emits_filled_row():
    """fill_listing emits EQUITY_LISTING_FILLED audit row."""
    from urace import equity_auto_trade as eat

    now = time.time()
    listing_id = 'elst-test-123'
    feature_id = 'feat-bbb'
    seller_id = 'seller-peer'
    buyer_id = 'buyer-peer'
    bp = 500
    ask = 20

    exchange = MockExchange(peer_id=buyer_id)
    # Pre-seed the EQUITY_LISTING row so _get_listing and _listing_state work
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING',
        'listing_id': listing_id,
        'feature_id': feature_id,
        'seller_id': seller_id,
        'buyer_id': None,
        'basis_points': bp,
        'ask_price_units': ask,
        'expires_at_unix': now + 3600,
        'at_unix': now,
        'at': '2026-01-01T00:00:00+00:00',
    })

    with (
        patch('urace.feature_equity.sell_equity', return_value=None),
        patch('urace.purchase_settlement.initiate_purchase', return_value={'status': 'confirmed'}),
    ):
        eat.fill_listing(exchange, root='/tmp/fake-root', listing_id=listing_id, buyer_id=buyer_id)

    filled_rows = [r for r in exchange.audit_rows() if r.get('kind') == 'EQUITY_LISTING_FILLED']
    assert len(filled_rows) == 1
    fr = filled_rows[0]
    assert fr['listing_id'] == listing_id
    assert fr['feature_id'] == feature_id
    assert fr['seller_id'] == seller_id
    assert fr['buyer_id'] == buyer_id
    assert fr['basis_points'] == bp
    assert fr['price_units'] == ask


# ── 3. _check_wash_trading raises ValueError on self-trade ───────────────────

def test_check_wash_trading_raises_on_self_trade():
    """_check_wash_trading raises ValueError when peer bought and sold same feature within 24h."""
    from urace import equity_auto_trade as eat

    now = time.time()
    feature_id = 'feat-ccc'
    peer_id = 'wash-trader'

    exchange = MockExchange(peer_id=peer_id)
    # Peer bought the feature
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING_FILLED',
        'feature_id': feature_id,
        'buyer_id': peer_id,
        'seller_id': 'someone-else',
        'at_unix': now - 100,  # 100 seconds ago (within 24h window)
    })
    # Peer sold (listed) the feature
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING',
        'feature_id': feature_id,
        'seller_id': peer_id,
        'at_unix': now - 50,  # 50 seconds ago (within 24h window)
    })

    with pytest.raises(ValueError, match='Wash trading detected'):
        eat._check_wash_trading(exchange, seller_id=peer_id, feature_id=feature_id)


# ── 4. lucrativity_assessment returns dict with expected keys ─────────────────

def test_lucrativity_assessment_returns_expected_keys():
    """lucrativity_assessment returns a dict with feature_id, lucrativity_score, and verdict."""
    from urace import equity_auto_trade as eat

    exchange = MockExchange(peer_id='holder-peer')
    feature_id = 'feat-ddd'

    with (
        patch.object(eat, 'feature_depletion_status', return_value={
            'state': 'HEALTHY',
            'adoption_rate': 0.1,
            'adoption_count': 2,
            'supply_pressure': 0.8,
            'remaining_adopters': 8,
            'listable': True,
            'feature_id': feature_id,
        }),
        patch('urace.credit_ledger.supply_pressure_multiplier', return_value=0.8),
        patch('urace.credit_ledger.apply_borrow_cost', return_value=100),
        patch('urace.credit_ledger.UNIT', 1_000_000),
        patch('urace.ledger_compaction.consensus_mint_per_adoption', return_value=10_000),
    ):
        result = eat.lucrativity_assessment(
            feature_id=feature_id,
            exchange=exchange,
            window_days=30.0,
            bp_held=10_000,
            estimated_network_size=10,
        )

    assert result['feature_id'] == feature_id
    assert 'lucrativity_score' in result
    assert 'verdict' in result
    assert isinstance(result['lucrativity_score'], float)
    assert result['verdict'] in ('HIGH', 'MEDIUM', 'LOW', 'EXHAUSTED')


# ── 5. cancel_listing emits EQUITY_LISTING_CANCELLED; second cancel raises ────

def test_cancel_listing_emits_cancelled_row_and_is_idempotent():
    """cancel_listing emits EQUITY_LISTING_CANCELLED; second call raises ValueError (not open)."""
    from urace import equity_auto_trade as eat

    now = time.time()
    listing_id = 'elst-cancel-test'
    feature_id = 'feat-eee'
    seller_id = 'seller-peer'

    exchange = MockExchange(peer_id=seller_id)
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING',
        'listing_id': listing_id,
        'feature_id': feature_id,
        'seller_id': seller_id,
        'basis_points': 1000,
        'ask_price_units': 5,
        'expires_at_unix': now + 3600,
        'at_unix': now,
        'at': '2026-01-01T00:00:00+00:00',
    })

    # First cancel: should succeed
    eat.cancel_listing(exchange, listing_id=listing_id, seller_id=seller_id)

    cancelled_rows = [r for r in exchange.audit_rows() if r.get('kind') == 'EQUITY_LISTING_CANCELLED']
    assert len(cancelled_rows) == 1
    assert cancelled_rows[0]['listing_id'] == listing_id
    assert cancelled_rows[0]['seller_id'] == seller_id

    # Second cancel: should raise ValueError (listing is no longer OPEN)
    with pytest.raises(ValueError, match='not open'):
        eat.cancel_listing(exchange, listing_id=listing_id, seller_id=seller_id)

    # Still only one CANCELLED row (no duplicate emitted)
    assert len([r for r in exchange.audit_rows() if r.get('kind') == 'EQUITY_LISTING_CANCELLED']) == 1
