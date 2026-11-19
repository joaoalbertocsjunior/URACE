"""Tests for asset_registry.py — asset registration, earn, transfer, portfolio."""
import unittest

from conftest import MockExchange
from urace import asset_registry as ar


class TestAssetRegister(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()

    def test_register_new_asset(self):
        result = ar.register_asset(self.ex, 'feat-1', 'alice')
        self.assertEqual(result['status'], 'registered')
        self.assertEqual(result['feature_id'], 'feat-1')
        self.assertEqual(result['owner_peer_id'], 'alice')
        rows = self.ex.audit_rows()
        reg_rows = [r for r in rows if r.get('kind') == 'ASSET_REGISTERED']
        self.assertEqual(len(reg_rows), 1)
        self.assertEqual(reg_rows[0]['feature_id'], 'feat-1')

    def test_register_idempotent(self):
        ar.register_asset(self.ex, 'feat-1', 'alice')
        result2 = ar.register_asset(self.ex, 'feat-1', 'alice')
        self.assertEqual(result2['status'], 'already_registered')
        # Only one row in exchange
        rows = [r for r in self.ex.audit_rows() if r.get('kind') == 'ASSET_REGISTERED']
        self.assertEqual(len(rows), 1)

    def test_register_duplicate_fingerprint_blocked(self):
        fp = 'abc123fingerprint'
        ar.register_asset(self.ex, 'feat-orig', 'alice', canonical_fingerprint=fp)
        result = ar.register_asset(self.ex, 'feat-dupe', 'bob', canonical_fingerprint=fp)
        self.assertEqual(result['status'], 'duplicate')
        self.assertEqual(result['existing_feature_id'], 'feat-orig')
        self.assertIn('canonical_fingerprint', result)


class TestAssetUsageEarn(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()
        ar.register_asset(self.ex, 'feat-1', 'alice')

    def test_record_usage_earn_emits_rows(self):
        result = ar.record_usage_earn(self.ex, 'feat-1', 'bob', earn_units=10)
        self.assertEqual(result['status'], 'earned')
        self.assertEqual(result['earn_units'], 10)
        self.assertIn('borrow_tax_units', result)
        kinds = [r['kind'] for r in self.ex.audit_rows()]
        self.assertIn('ASSET_EARN', kinds)
        self.assertIn('CREDIT_DELTA', kinds)

    def test_self_borrow_blocked(self):
        result = ar.record_usage_earn(self.ex, 'feat-1', 'alice', earn_units=5)
        self.assertEqual(result['status'], 'self_borrow_blocked')
        earn_rows = [r for r in self.ex.audit_rows() if r.get('kind') == 'ASSET_EARN']
        self.assertEqual(len(earn_rows), 0)

    def test_earn_rate_24h(self):
        ar.record_usage_earn(self.ex, 'feat-1', 'bob', earn_units=100)
        ar.record_usage_earn(self.ex, 'feat-1', 'carol', earn_units=200)
        rows = self.ex.audit_rows()
        rate = ar.earn_rate(rows, 'feat-1', window_seconds=86400.0)
        # 300 earn_units over 86400 seconds
        self.assertAlmostEqual(rate, 300 / 86400.0, places=10)

    def test_cumulative_earn(self):
        ar.record_usage_earn(self.ex, 'feat-1', 'bob', earn_units=5)
        ar.record_usage_earn(self.ex, 'feat-1', 'carol', earn_units=7)
        rows = self.ex.audit_rows()
        summary = ar.asset_summary(rows, 'feat-1')
        self.assertEqual(summary['cumulative_earn_units'], 12)


class TestAssetTransfer(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()
        ar.register_asset(self.ex, 'feat-1', 'alice')

    def test_initiate_transfer(self):
        result = ar.initiate_transfer(self.ex, 'feat-1', 'alice', 'bob', expires_in_seconds=3600)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['from_peer_id'], 'alice')
        self.assertEqual(result['to_peer_id'], 'bob')
        rows = self.ex.audit_rows()
        pending = [r for r in rows if r.get('kind') == 'ASSET_TRANSFER_PENDING']
        self.assertEqual(len(pending), 1)

    def test_accept_transfer(self):
        ar.initiate_transfer(self.ex, 'feat-1', 'alice', 'bob', expires_in_seconds=3600)
        result = ar.accept_transfer(self.ex, 'feat-1', 'bob')
        self.assertEqual(result['status'], 'transferred')
        self.assertEqual(result['to_peer_id'], 'bob')
        rows = self.ex.audit_rows()
        transferred = [r for r in rows if r.get('kind') == 'ASSET_TRANSFERRED']
        self.assertEqual(len(transferred), 1)

    def test_cancel_transfer(self):
        ar.initiate_transfer(self.ex, 'feat-1', 'alice', 'bob', expires_in_seconds=3600)
        result = ar.cancel_transfer(self.ex, 'feat-1', 'alice')
        self.assertEqual(result['status'], 'cancelled')
        rows = self.ex.audit_rows()
        cancelled = [r for r in rows if r.get('kind') == 'ASSET_TRANSFER_CANCELLED']
        self.assertEqual(len(cancelled), 1)

    def test_transfer_blocked_during_challenge(self):
        # Inject a pending challenge row
        self.ex.append_audit_row({
            'kind': 'PROVENANCE_CHALLENGE',
            'feature_id': 'feat-1',
            'status': 'pending',
        })
        with self.assertRaises(ValueError) as ctx:
            ar.initiate_transfer(self.ex, 'feat-1', 'alice', 'bob')
        self.assertIn('challenge', str(ctx.exception).lower())


class TestAssetPortfolio(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()

    def test_peer_asset_portfolio_empty(self):
        rows = self.ex.audit_rows()
        portfolio = ar.peer_asset_portfolio(rows, 'alice')
        self.assertEqual(portfolio, [])

    def test_peer_asset_portfolio_with_assets(self):
        ar.register_asset(self.ex, 'feat-1', 'alice')
        ar.register_asset(self.ex, 'feat-2', 'alice')
        ar.register_asset(self.ex, 'feat-3', 'bob')
        rows = self.ex.audit_rows()
        portfolio = ar.peer_asset_portfolio(rows, 'alice')
        feature_ids = {item['feature_id'] for item in portfolio}
        self.assertIn('feat-1', feature_ids)
        self.assertIn('feat-2', feature_ids)
        self.assertNotIn('feat-3', feature_ids)
        self.assertEqual(len(portfolio), 2)


class TestAssetOpportunitiesDispatch(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()
        ar.register_asset(self.ex, 'feat-high', 'alice')
        ar.register_asset(self.ex, 'feat-low', 'bob')
        # Give feat-high more earn activity
        for _ in range(5):
            ar.record_usage_earn(self.ex, 'feat-high', 'carol', earn_units=100)
        ar.record_usage_earn(self.ex, 'feat-low', 'carol', earn_units=1)

    def test_opportunities_filter_min_earn_rate(self):
        rows = self.ex.audit_rows()
        # feat-high has 500 earn units; feat-low has 1 — rate over 86400s
        rate_high = ar.earn_rate(rows, 'feat-high')
        rate_low = ar.earn_rate(rows, 'feat-low')
        self.assertGreater(rate_high, rate_low)

    def test_asset_summary(self):
        rows = self.ex.audit_rows()
        summary = ar.asset_summary(rows, 'feat-high')
        self.assertIsNotNone(summary)
        self.assertEqual(summary['feature_id'], 'feat-high')
        self.assertEqual(summary['owner_peer_id'], 'alice')
        self.assertEqual(summary['total_uses'], 5)
        self.assertEqual(summary['cumulative_earn_units'], 500)
        # unregistered returns None
        self.assertIsNone(ar.asset_summary(rows, 'feat-nonexistent'))
