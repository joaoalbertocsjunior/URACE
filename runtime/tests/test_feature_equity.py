"""Tests for feature_equity.py — equity model, trading, mint splits."""
import unittest, time

class MockExchange:
    def __init__(self):
        self._rows = []
    def audit_rows(self):
        return list(self._rows)
    def append_audit_row(self, row):
        self._rows.append(row)

class EquityGrantTests(unittest.TestCase):
    def setUp(self):
        from urace import feature_equity as fe
        self.fe = fe
        self.ex = MockExchange()

    def test_grant_gives_full_equity(self):
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')
        holdings = self.fe.equity_holdings('feat-1', self.ex)
        self.assertEqual(holdings.get('alice'), 10_000)

    def test_grant_idempotent(self):
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')
        holdings = self.fe.equity_holdings('feat-1', self.ex)
        self.assertEqual(holdings.get('alice'), 10_000)

    def test_original_creator_immutable(self):
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')
        self.assertEqual(self.fe.original_creator('feat-1', self.ex), 'alice')

    def test_no_grant_returns_empty(self):
        self.assertEqual(self.fe.equity_holdings('feat-x', self.ex), {})
        self.assertIsNone(self.fe.original_creator('feat-x', self.ex))


class EquityPartialSaleTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from urace import feature_equity as fe, credit_ledger as cl
        self.fe = fe
        self.cl = cl
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()
        # Give bob enough balance for purchases
        cl.earn_units(self.tmpdir, 'bob', 10 * cl.UNIT, 'test-setup')
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')

    def test_partial_sale_splits_holdings(self):
        self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob', 3_000)
        h = self.fe.equity_holdings('feat-1', self.ex)
        self.assertEqual(h.get('alice'), 7_000)
        self.assertEqual(h.get('bob'), 3_000)

    def test_full_sale_removes_seller(self):
        self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob', 10_000)
        h = self.fe.equity_holdings('feat-1', self.ex)
        self.assertNotIn('alice', h)
        self.assertEqual(h.get('bob'), 10_000)

    def test_original_creator_preserved_after_full_sale(self):
        self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob', 10_000)
        self.assertEqual(self.fe.original_creator('feat-1', self.ex), 'alice')

    def test_min_tranche_enforced(self):
        with self.assertRaises(ValueError):
            self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob', 50)

    def test_insufficient_holdings_rejected(self):
        with self.assertRaises(ValueError):
            self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob', 15_000)

    def test_non_original_anti_monopoly(self):
        # First sale: alice → bob 5000 (50%)
        self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob', 5_000)
        # Second sale: alice → bob another 4000 would put bob at 9000 > 8000 cap
        with self.assertRaises(ValueError):
            self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob', 4_000)

    def test_original_can_sell_above_cap_to_single_buyer(self):
        # Original creator selling full 10_000 to one buyer is allowed (intentional exit)
        self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob', 10_000)
        h = self.fe.equity_holdings('feat-1', self.ex)
        self.assertEqual(h.get('bob'), 10_000)

    def test_price_transfer_uses_trade_rep_source(self):
        from urace import credit_ledger as cl
        initial_earned = cl.earned_balance(self.tmpdir, 'alice')
        self.fe.sell_equity(self.ex, self.tmpdir, 'feat-1', 'alice', 'bob',
                            3_000, price_units=cl.UNIT)
        # alice receives UNIT as REP_SOURCE_TRADE — should NOT increase earned_balance
        new_earned = cl.earned_balance(self.tmpdir, 'alice')
        self.assertEqual(new_earned, initial_earned)


class MintEquitySplitTests(unittest.TestCase):
    def setUp(self):
        from urace import feature_equity as fe
        self.fe = fe
        self.ex = MockExchange()

    def test_no_equity_fallback_to_creator(self):
        # No equity rows → falls back via feature_creator_id which is None here
        # (no exchange integration), so returns empty
        result = self.fe.mint_equity_split('feat-x', 1000, self.ex)
        self.assertEqual(result, {})

    def test_full_equity_goes_to_original(self):
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')
        result = self.fe.mint_equity_split('feat-1', 1000, self.ex)
        self.assertEqual(result.get('alice'), 1000)

    def test_split_after_partial_sale(self):
        import tempfile
        from urace import credit_ledger as cl
        tmpdir = tempfile.mkdtemp()
        cl.earn_units(tmpdir, 'bob', 5 * cl.UNIT, 'test')
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')
        self.fe.sell_equity(self.ex, tmpdir, 'feat-1', 'alice', 'bob', 3_000)
        result = self.fe.mint_equity_split('feat-1', 1000, self.ex)
        self.assertEqual(result.get('alice', 0) + result.get('bob', 0), 1000)
        self.assertGreater(result.get('alice', 0), result.get('bob', 0))

    def test_split_sums_to_total(self):
        import tempfile
        from urace import credit_ledger as cl
        tmpdir = tempfile.mkdtemp()
        cl.earn_units(tmpdir, 'bob', 5 * cl.UNIT, 'test')
        cl.earn_units(tmpdir, 'carol', 5 * cl.UNIT, 'test')
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')
        self.fe.sell_equity(self.ex, tmpdir, 'feat-1', 'alice', 'bob', 2_000)
        self.fe.sell_equity(self.ex, tmpdir, 'feat-1', 'alice', 'carol', 1_000)
        result = self.fe.mint_equity_split('feat-1', 10_000, self.ex)
        self.assertEqual(sum(result.values()), 10_000)

    def test_distribution_fee_split_same_as_mint(self):
        self.fe.grant_equity(self.ex, 'feat-1', 'alice')
        mint = self.fe.mint_equity_split('feat-1', 500, self.ex)
        fee  = self.fe.distribution_fee_equity_split('feat-1', 500, self.ex)
        self.assertEqual(mint, fee)


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm, credit_ledger as cl
        self.wm = wm
        self.cl = cl
        self.ex = MockExchange()

    def test_within_limit_accepted(self):
        for i in range(self.wm.WORK_REQUEST_DAILY_LIMIT):
            self.wm.create_work_request(self.ex, 'req', f'spec-{i}',
                                        budget_units=self.cl.UNIT)

    def test_exceeds_limit_rejected(self):
        for i in range(self.wm.WORK_REQUEST_DAILY_LIMIT):
            self.wm.create_work_request(self.ex, 'req', f'spec-{i}',
                                        budget_units=self.cl.UNIT)
        with self.assertRaises(ValueError):
            self.wm.create_work_request(self.ex, 'req', 'one-too-many',
                                        budget_units=self.cl.UNIT)

    def test_different_requester_not_affected(self):
        for i in range(self.wm.WORK_REQUEST_DAILY_LIMIT):
            self.wm.create_work_request(self.ex, 'req-a', f'spec-{i}',
                                        budget_units=self.cl.UNIT)
        # Different peer unaffected
        self.wm.create_work_request(self.ex, 'req-b', 'spec',
                                    budget_units=self.cl.UNIT)


class PeerReviewQuorumTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm, credit_ledger as cl
        self.wm = wm
        self.cl = cl
        self.ex = MockExchange()
        # Build a request in VERIFICATION state
        rid = wm.create_work_request(self.ex, 'req', 'spec',
                                     budget_units=cl.UNIT)
        self.rid = rid
        wm.submit_bid(self.ex, rid, 'dev-a', combined_rep=0.7)
        import time as _t
        self.ex.append_audit_row({
            'kind': 'WORK_ACCEPTED', 'request_id': rid,
            'requester_id': 'req', 'bidder_id': 'dev-a',
            'budget_units': cl.UNIT, 'at_unix': _t.time(), 'at': 'now',
        })
        wm.submit_delivery(self.ex, rid, 'dev-a', 'hash-abc')

    def test_no_reviews_quorum_none(self):
        result = self.wm.quorum_reached(self.rid, self.ex)
        self.assertIsNone(result)

    def test_below_quorum_still_none(self):
        for i in range(self.wm.VERIFICATION_QUORUM - 1):
            self.wm.submit_peer_review(self.ex, self.rid, f'reviewer-{i}', True)
        self.assertIsNone(self.wm.quorum_reached(self.rid, self.ex))

    def test_quorum_majority_approve(self):
        for i in range(self.wm.VERIFICATION_QUORUM):
            self.wm.submit_peer_review(self.ex, self.rid, f'reviewer-{i}', True)
        self.assertTrue(self.wm.quorum_reached(self.rid, self.ex))

    def test_quorum_majority_reject(self):
        self.wm.submit_peer_review(self.ex, self.rid, 'r0', False)
        self.wm.submit_peer_review(self.ex, self.rid, 'r1', False)
        self.wm.submit_peer_review(self.ex, self.rid, 'r2', True)
        self.assertFalse(self.wm.quorum_reached(self.rid, self.ex))

    def test_dispute_party_excluded(self):
        with self.assertRaises(ValueError):
            self.wm.submit_peer_review(self.ex, self.rid, 'req', True)
        with self.assertRaises(ValueError):
            self.wm.submit_peer_review(self.ex, self.rid, 'dev-a', True)

    def test_duplicate_review_rejected(self):
        self.wm.submit_peer_review(self.ex, self.rid, 'neutral', True)
        with self.assertRaises(ValueError):
            self.wm.submit_peer_review(self.ex, self.rid, 'neutral', False)


class FeatureMarketPriceTests(unittest.TestCase):
    def setUp(self):
        from urace import credit_ledger as cl
        self.cl = cl
        self.ex = MockExchange()

    def test_high_quality_increases_price(self):
        base = self.cl.UNIT
        low  = self.cl.feature_market_price('f', self.ex, base, quality_wilson=0.1)
        high = self.cl.feature_market_price('f', self.ex, base, quality_wilson=0.9)
        self.assertGreater(high, low)

    def test_price_never_below_base(self):
        base = self.cl.UNIT
        price = self.cl.feature_market_price('f', self.ex, base,
                                             quality_wilson=0.0, adoption_count=0)
        self.assertGreaterEqual(price, int(base * 0.96))  # ±4% jitter tolerance

    def test_high_adoption_velocity_raises_price(self):
        base = self.cl.UNIT
        low  = self.cl.feature_market_price('f', self.ex, base,
                                            adoption_count=0, estimated_network_size=100)
        high = self.cl.feature_market_price('f', self.ex, base,
                                            adoption_count=50, estimated_network_size=100)
        self.assertGreater(high, low)
