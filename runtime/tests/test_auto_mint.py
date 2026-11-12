"""Tests for auto_mint_minimal_features, settlement_state, and handle_purchase_settlement."""
import hashlib
import time
import unittest
from unittest.mock import MagicMock, patch


class MockExchange:
    """Minimal exchange mock following the pattern from test_work_market.py."""
    def __init__(self, peer_id='test-peer-local'):
        self._rows = []
        self._peer_id = peer_id
        self._state = {'peers': {}}

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)

    def load(self):
        return dict(self._state)

    def identity(self):
        return {'peer_id': self._peer_id}


class AutoMintTests(unittest.TestCase):
    def setUp(self):
        from urace import equity_auto_trade as eat
        self.eat = eat
        self.exchange = MockExchange(peer_id='owner-123')

    def test_auto_mint_disabled_returns_empty(self):
        """auto_mint_minimal_features returns [] when not enabled."""
        result = self.eat.auto_mint_minimal_features(
            self.exchange, '/tmp/root', 'owner-123',
            config={'auto_mint': {'enabled': False}}
        )
        self.assertEqual(result, [])

    def test_auto_mint_emits_equity_created(self):
        """auto_mint_minimal_features emits EQUITY_CREATED for a qualifying WORK_RELEASED row."""
        request_id = 'req-abc123'
        self.exchange.append_audit_row({
            'kind': 'WORK_RELEASED',
            'request_id': request_id,
            'requester_id': 'owner-123',
        })
        self.exchange.append_audit_row({
            'kind': 'WORK_REQUEST',
            'request_id': request_id,
            'complexity': 0.3,
            'quality_score': 0.8,
            'budget_units': 500,
        })

        config = {'auto_mint': {'enabled': True, 'max_complexity_threshold': 0.5, 'min_quality_score': 0.6}}
        result = self.eat.auto_mint_minimal_features(self.exchange, '/tmp/root', 'owner-123', config=config)

        self.assertEqual(len(result), 1, f"Expected 1 minted, got: {result}")
        created_rows = [r for r in self.exchange._rows if r.get('kind') == 'EQUITY_CREATED']
        self.assertEqual(len(created_rows), 1)
        self.assertEqual(created_rows[0]['owner_id'], 'owner-123')

    def test_auto_mint_skips_high_complexity(self):
        """auto_mint_minimal_features skips features that exceed max_complexity."""
        request_id = 'req-high-cx'
        self.exchange.append_audit_row({
            'kind': 'WORK_RELEASED',
            'request_id': request_id,
            'requester_id': 'owner-123',
        })
        self.exchange.append_audit_row({
            'kind': 'WORK_REQUEST',
            'request_id': request_id,
            'complexity': 0.9,
            'quality_score': 0.9,
            'budget_units': 100,
        })

        config = {'auto_mint': {'enabled': True, 'max_complexity_threshold': 0.5, 'min_quality_score': 0.6}}
        result = self.eat.auto_mint_minimal_features(self.exchange, '/tmp/root', 'owner-123', config=config)
        self.assertEqual(result, [])

    def test_auto_mint_idempotent(self):
        """Running auto_mint twice does not emit EQUITY_CREATED a second time."""
        request_id = 'req-idem'
        self.exchange.append_audit_row({
            'kind': 'WORK_RELEASED',
            'request_id': request_id,
            'requester_id': 'owner-123',
        })
        self.exchange.append_audit_row({
            'kind': 'WORK_REQUEST',
            'request_id': request_id,
            'complexity': 0.2,
            'quality_score': 0.9,
            'budget_units': 200,
        })
        config = {'auto_mint': {'enabled': True, 'max_complexity_threshold': 0.5, 'min_quality_score': 0.6}}
        self.eat.auto_mint_minimal_features(self.exchange, '/tmp/root', 'owner-123', config=config)
        self.eat.auto_mint_minimal_features(self.exchange, '/tmp/root', 'owner-123', config=config)
        created_rows = [r for r in self.exchange._rows if r.get('kind') == 'EQUITY_CREATED']
        self.assertEqual(len(created_rows), 1)


class SettlementStateTests(unittest.TestCase):
    def setUp(self):
        from urace.purchase_settlement import settlement_state
        self.settlement_state = settlement_state
        self.exchange = MockExchange()

    def test_unknown_listing(self):
        """settlement_state returns UNKNOWN for a listing not in audit rows."""
        result = self.settlement_state(self.exchange, 'nonexistent-listing')
        self.assertEqual(result, 'UNKNOWN')

    def test_pending_state(self):
        """settlement_state returns PENDING when PURCHASE_INITIATED is present."""
        self.exchange.append_audit_row({
            'kind': 'PURCHASE_INITIATED',
            'listing_id': 'lst-001',
            'status': 'PENDING',
        })
        result = self.settlement_state(self.exchange, 'lst-001')
        self.assertEqual(result, 'PENDING')

    def test_confirmed_state(self):
        """settlement_state returns CONFIRMED when PURCHASE_CONFIRMED is present."""
        self.exchange.append_audit_row({'kind': 'PURCHASE_INITIATED', 'listing_id': 'lst-002'})
        self.exchange.append_audit_row({'kind': 'PURCHASE_CONFIRMED', 'listing_id': 'lst-002'})
        result = self.settlement_state(self.exchange, 'lst-002')
        self.assertEqual(result, 'CONFIRMED')

    def test_failed_state(self):
        """settlement_state returns FAILED when PURCHASE_FAILED is present."""
        self.exchange.append_audit_row({'kind': 'PURCHASE_INITIATED', 'listing_id': 'lst-003'})
        self.exchange.append_audit_row({'kind': 'PURCHASE_FAILED', 'listing_id': 'lst-003'})
        result = self.settlement_state(self.exchange, 'lst-003')
        self.assertEqual(result, 'FAILED')


class HandlePurchaseSettlementTests(unittest.TestCase):
    def setUp(self):
        from urace.purchase_settlement import handle_purchase_settlement
        self.handle = handle_purchase_settlement
        self.exchange = MockExchange(peer_id='seller-peer')

    def test_missing_payload_returns_error(self):
        """handle_purchase_settlement returns error for malformed settlement."""
        result = self.handle(self.exchange, 'buyer-peer', {'bad': 'structure'})
        self.assertEqual(result['status'], 'error')

    def test_sender_mismatch_returns_error(self):
        """handle_purchase_settlement returns sender_mismatch when peer IDs differ."""
        settlement = {
            'payload': {
                'schema': 'urace-purchase-settlement-v1',
                'buyer_peer_id': 'actual-buyer',
                'seller_peer_id': 'seller-peer',
                'listing_id': 'lst-x',
                'price_units': 100,
                'at_unix': time.time(),
                'nonce': 'abc123',
            },
            'signature': {},
        }
        result = self.handle(self.exchange, 'different-sender', settlement)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error'], 'sender_mismatch')

    def test_valid_settlement_does_not_raise(self):
        """handle_purchase_settlement with a valid but unverifiable settlement returns a dict."""
        settlement = {
            'payload': {
                'schema': 'urace-purchase-settlement-v1',
                'buyer_peer_id': 'buyer-peer',
                'seller_peer_id': 'seller-peer',
                'listing_id': 'lst-y',
                'price_units': 50,
                'at_unix': time.time(),
                'nonce': 'nonce999',
            },
            'signature': {'schema': 'fake'},
        }
        # trusted_crypto will fail because buyer-peer not in peers — expect error, not exception
        self.exchange._state['peers'] = {}
        result = self.handle(self.exchange, 'buyer-peer', settlement)
        self.assertIn(result['status'], ('ok', 'error'))
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    unittest.main()
