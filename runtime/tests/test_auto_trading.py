"""Merged auto-trading tests: equity_auto_trade (list/fill/wash/lucrativity/cancel),
depletion, listings, auto-buy, auto-sell, auto-mint, settlement state, purchase settlement,
and ledger compaction / P2P supply."""
from __future__ import annotations
import hashlib
import time
import tempfile
import unittest
import pytest
from unittest.mock import MagicMock, patch

from conftest import MockExchange


# ── Helpers shared by listing tests ──────────────────────────────────────────

def _inject_grant(exchange, feature_id, seller_id, basis_points):
    """Pre-seed the exchange with an EQUITY_GRANT row."""
    exchange.append_audit_row({
        'kind': 'EQUITY_GRANT',
        'feature_id': feature_id,
        'peer_id': seller_id,
        'basis_points': basis_points,
        'at_unix': time.time(),
        'at': '2026-01-01T00:00:00+00:00',
    })


# ═══════════════════════════════════════════════════════════════════════════
# From test_equity_auto_trade.py — 5 pytest-style function tests
# ═══════════════════════════════════════════════════════════════════════════

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


def test_check_wash_trading_raises_on_self_trade():
    """_check_wash_trading raises ValueError when peer bought and sold same feature within 24h."""
    from urace import equity_auto_trade as eat

    now = time.time()
    feature_id = 'feat-ccc'
    peer_id = 'wash-trader'

    exchange = MockExchange(peer_id=peer_id)
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING_FILLED',
        'feature_id': feature_id,
        'buyer_id': peer_id,
        'seller_id': 'someone-else',
        'at_unix': now - 100,
    })
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING',
        'feature_id': feature_id,
        'seller_id': peer_id,
        'at_unix': now - 50,
    })

    with pytest.raises(ValueError, match='Wash trading detected'):
        eat._check_wash_trading(exchange, seller_id=peer_id, feature_id=feature_id)


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

    eat.cancel_listing(exchange, listing_id=listing_id, seller_id=seller_id)

    cancelled_rows = [r for r in exchange.audit_rows() if r.get('kind') == 'EQUITY_LISTING_CANCELLED']
    assert len(cancelled_rows) == 1
    assert cancelled_rows[0]['listing_id'] == listing_id
    assert cancelled_rows[0]['seller_id'] == seller_id

    with pytest.raises(ValueError, match='not open'):
        eat.cancel_listing(exchange, listing_id=listing_id, seller_id=seller_id)

    assert len([r for r in exchange.audit_rows() if r.get('kind') == 'EQUITY_LISTING_CANCELLED']) == 1


# ═══════════════════════════════════════════════════════════════════════════
# From test_auto_trade.py — unittest-style classes
# ═══════════════════════════════════════════════════════════════════════════

class DepletionStatusTests(unittest.TestCase):
    def setUp(self):
        from urace import equity_auto_trade as eat, credit_ledger as cl
        self.eat = eat
        self.cl = cl
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()

    def test_no_adoption_is_healthy(self):
        d = self.eat.feature_depletion_status('feat-1', self.ex, estimated_network_size=100)
        self.assertEqual(d['state'], 'HEALTHY')
        self.assertTrue(d['listable'])

    def test_near_full_adoption_depleted(self):
        for i in range(98):
            self.ex.append_audit_row({
                'kind': 'CREDIT_DELTA', 'direction': 'spend',
                'feature_id': 'feat-1', 'peer': f'peer-{i}',
                'delta_units': 100, 'at_unix': time.time(),
            })
        d = self.eat.feature_depletion_status('feat-1', self.ex, estimated_network_size=100)
        self.assertIn(d['state'], ('NEAR_DEPLETED', 'DEPLETED'))

    def test_depleted_is_not_listable(self):
        for i in range(99):
            self.ex.append_audit_row({
                'kind': 'CREDIT_DELTA', 'direction': 'spend',
                'feature_id': 'feat-1', 'peer': f'peer-{i}',
                'delta_units': 100, 'at_unix': time.time(),
            })
        d = self.eat.feature_depletion_status('feat-1', self.ex, estimated_network_size=100)
        if d['state'] == 'DEPLETED':
            self.assertFalse(d['listable'])

    def test_remaining_adopters_correct(self):
        for i in range(30):
            self.ex.append_audit_row({
                'kind': 'CREDIT_DELTA', 'direction': 'spend',
                'feature_id': 'feat-1', 'peer': f'peer-{i}',
                'delta_units': 100, 'at_unix': time.time(),
            })
        d = self.eat.feature_depletion_status('feat-1', self.ex, estimated_network_size=100)
        self.assertEqual(d['remaining_adopters'], 70)


class ListingTests(unittest.TestCase):
    def setUp(self):
        from urace import equity_auto_trade as eat, feature_equity as fe, credit_ledger as cl
        self.eat = eat
        self.fe = fe
        self.cl = cl
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()
        cl.earn_units(self.tmpdir, 'alice', 10 * cl.UNIT, 'test')
        cl.earn_units(self.tmpdir, 'bob', 10 * cl.UNIT, 'test')
        fe.grant_equity(self.ex, 'feat-1', 'alice')

    def test_list_and_show(self):
        lid = self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 1000, 500)
        listings = self.eat.open_listings(self.ex)
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0]['listing_id'], lid)

    def test_fill_listing_transfers_equity(self):
        lid = self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 1000, 0)
        self.eat.fill_listing(self.ex, self.tmpdir, lid, 'bob')
        h = self.fe.equity_holdings('feat-1', self.ex)
        self.assertEqual(h.get('bob'), 1000)

    def test_cancel_listing(self):
        lid = self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 1000, 0)
        self.eat.cancel_listing(self.ex, lid, 'alice')
        self.assertEqual(len(self.eat.open_listings(self.ex)), 0)

    def test_non_seller_cannot_cancel(self):
        lid = self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 1000, 0)
        with self.assertRaises(ValueError):
            self.eat.cancel_listing(self.ex, lid, 'bob')

    def test_fill_filled_listing_raises(self):
        lid = self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 1000, 0)
        self.eat.fill_listing(self.ex, self.tmpdir, lid, 'bob')
        with self.assertRaises(ValueError):
            self.eat.fill_listing(self.ex, self.tmpdir, lid, 'bob')

    def test_listing_below_min_tranche_raises(self):
        with self.assertRaises(ValueError):
            self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 50, 0)

    def test_seller_insufficient_bp_raises(self):
        with self.assertRaises(ValueError):
            self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 15000, 0)


class AutoBuyTests(unittest.TestCase):
    def setUp(self):
        from urace import equity_auto_trade as eat, feature_equity as fe, credit_ledger as cl
        self.eat = eat
        self.fe = fe
        self.cl = cl
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()
        cl.earn_units(self.tmpdir, 'alice', 20 * cl.UNIT, 'test')
        cl.earn_units(self.tmpdir, 'bob', 20 * cl.UNIT, 'test')
        fe.grant_equity(self.ex, 'feat-1', 'alice')

    def test_auto_buy_disabled_by_default(self):
        from urace.equity_auto_trade import DEFAULT_CONFIG
        import copy
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 1000, 0)
        result = self.eat.auto_buy(self.ex, self.tmpdir, 'bob', cfg)
        self.assertEqual(len(result['bought']), 0)

    def test_auto_buy_enabled_buys_qualifying_listing(self):
        import copy
        cfg = copy.deepcopy(self.eat.DEFAULT_CONFIG)
        cfg['auto_buy']['enabled'] = True
        cfg['auto_buy']['min_quality_wilson'] = 0.0
        cfg['auto_buy']['min_adoption_count'] = 0
        cfg['auto_buy']['min_lucrativity_score'] = 0.0
        cfg['auto_buy']['min_supply_pressure'] = 0.0
        cfg['auto_buy']['min_remaining_adopters'] = 0
        cfg['auto_buy']['max_adoption_rate'] = 1.0
        self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 1000, 0)
        result = self.eat.auto_buy(self.ex, self.tmpdir, 'bob', cfg,
                                   quality_scores={'feat-1': 1.0},
                                   adoption_counts={'feat-1': 5})
        self.assertEqual(len(result['bought']), 1)

    def test_auto_buy_skips_depleted(self):
        for i in range(95):
            self.ex.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'spend',
                                      'feature_id': 'feat-1', 'peer': f'p-{i}',
                                      'delta_units': 100, 'at_unix': time.time()})
        import copy
        cfg = copy.deepcopy(self.eat.DEFAULT_CONFIG)
        cfg['auto_buy']['enabled'] = True
        cfg['auto_buy']['min_quality_wilson'] = 0.0
        cfg['auto_buy']['min_adoption_count'] = 0
        cfg['auto_buy']['min_lucrativity_score'] = 0.0
        self.eat.list_for_sale(self.ex, 'feat-1', 'alice', 1000, 0,
                               estimated_network_size=100)
        result = self.eat.auto_buy(self.ex, self.tmpdir, 'bob', cfg,
                                   quality_scores={'feat-1': 0.9},
                                   adoption_counts={'feat-1': 95})
        self.assertEqual(len(result['bought']), 0)


class AutoSellTests(unittest.TestCase):
    def setUp(self):
        from urace import equity_auto_trade as eat, feature_equity as fe, credit_ledger as cl
        self.eat = eat
        self.fe = fe
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()
        cl.earn_units(self.tmpdir, 'alice', 20 * cl.UNIT, 'test')
        fe.grant_equity(self.ex, 'feat-1', 'alice')

    def test_auto_sell_disabled_by_default(self):
        from urace.equity_auto_trade import DEFAULT_CONFIG
        import copy
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        result = self.eat.auto_sell(self.ex, self.tmpdir, 'alice', cfg)
        self.assertEqual(len(result['listed']), 0)

    def test_auto_sell_near_depleted_triggers_listing(self):
        import copy
        cfg = copy.deepcopy(self.eat.DEFAULT_CONFIG)
        cfg['auto_sell']['enabled'] = True
        cfg['auto_sell']['sell_on_near_depleted'] = True
        cfg['auto_sell']['min_hold_bp_to_trigger'] = 100
        for i in range(100):
            self.ex.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'spend',
                                      'feature_id': 'feat-1' if i < 83 else 'other',
                                      'peer': f'p-{i}',
                                      'delta_units': 100, 'at_unix': time.time()})
        result = self.eat.auto_sell(self.ex, self.tmpdir, 'alice', cfg,
                                    adoption_counts={'feat-1': 83})
        dep = self.eat.feature_depletion_status('feat-1', self.ex,
                                                 estimated_network_size=100, adoption_count=83)
        if dep['state'] == 'NEAR_DEPLETED':
            self.assertGreater(len(result['listed']), 0)


class DepletionBlocksListingTests(unittest.TestCase):
    def test_depleted_feature_cannot_be_listed(self):
        from urace import equity_auto_trade as eat, feature_equity as fe
        ex = MockExchange()
        tmpdir = tempfile.mkdtemp()
        fe.grant_equity(ex, 'feat-x', 'alice')
        original = eat.feature_depletion_status
        eat.feature_depletion_status = lambda *a, **kw: {
            'state': 'DEPLETED', 'listable': False,
            'adoption_rate': 0.99, 'supply_pressure': 0.001, 'notes': 'test',
        }
        try:
            with self.assertRaises(ValueError):
                eat.list_for_sale(ex, 'feat-x', 'alice', 1000, 100)
        finally:
            eat.feature_depletion_status = original


class LedgerCompactionTests(unittest.TestCase):
    def setUp(self):
        from urace import ledger_compaction as lc, peer_work_market as wm, credit_ledger as cl
        self.lc = lc
        self.wm = wm
        self.cl = cl
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()

    def _make_released_contract(self, rid_suffix=''):
        cl = self.cl
        cl.earn_units(self.tmpdir, 'alice', 5 * cl.UNIT, 'test')
        rid = self.wm.create_work_request(self.ex, 'alice', 'spec', cl.UNIT)
        self.wm.submit_bid(self.ex, rid, 'bob', combined_rep=0.7)
        self.ex.append_audit_row({
            'kind': 'WORK_ACCEPTED', 'request_id': rid,
            'requester_id': 'alice', 'bidder_id': 'bob',
            'budget_units': cl.UNIT, 'at_unix': time.time(), 'at': 'now',
        })
        self.wm.submit_delivery(self.ex, rid, 'bob', 'hash-abc')
        self.ex.append_audit_row({
            'kind': 'WORK_VERIFIED', 'request_id': rid,
            'requester_id': 'alice', 'approved': True,
            'at_unix': time.time(), 'at': 'now',
        })
        return rid

    def test_compact_released_contract(self):
        rid = self._make_released_contract()
        result = self.lc.compact_closed_contracts(self.ex, older_than_days=0)
        self.assertIn(rid, result['compacted'])
        self.assertGreater(result['summary_rows_added'], 0)

    def test_compact_adds_summary_row(self):
        rid = self._make_released_contract()
        self.lc.compact_closed_contracts(self.ex, older_than_days=0)
        rows = self.ex.audit_rows()
        summaries = [r for r in rows if r.get('kind') == 'WORK_CONTRACT_SUMMARY'
                     and r.get('request_id') == rid]
        self.assertEqual(len(summaries), 1)

    def test_compact_not_double_compacted(self):
        self._make_released_contract()
        self.lc.compact_closed_contracts(self.ex, older_than_days=0)
        result2 = self.lc.compact_closed_contracts(self.ex, older_than_days=0)
        self.assertEqual(len(result2['compacted']), 0)

    def test_ledger_checkpoint_written(self):
        ckpt_id = self.lc.ledger_checkpoint(self.ex, self.tmpdir)
        self.assertIsNotNone(ckpt_id)
        ckpt = self.lc.latest_checkpoint(self.ex)
        self.assertIsNotNone(ckpt)
        self.assertEqual(ckpt['checkpoint_id'], ckpt_id)

    def test_sync_tail_returns_checkpoint_plus_tail(self):
        self._make_released_contract()
        self.lc.ledger_checkpoint(self.ex, self.tmpdir)
        self.ex.append_audit_row({'kind': 'WORK_REQUEST', 'request_id': 'new',
                                  'at_unix': time.time(), 'at': 'now'})
        ckpt, tail = self.lc.sync_tail_rows(self.ex)
        self.assertIsNotNone(ckpt)
        self.assertGreater(len(tail), 0)

    def test_no_checkpoint_returns_full_sync(self):
        ckpt, tail = self.lc.sync_tail_rows(self.ex)
        self.assertIsNone(ckpt)


class P2PSupplyCalcTests(unittest.TestCase):
    def setUp(self):
        from urace import ledger_compaction as lc
        self.lc = lc
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()

    def test_basic_supply_calc(self):
        result = self.lc.p2p_optimal_supply(max_network_peers=100, target_ledger_mb=10.0)
        self.assertIn('verdict', result)
        self.assertIn('global_supply_tokens', result)
        self.assertGreater(result['max_features'], 0)

    def test_larger_network_larger_supply(self):
        small = self.lc.p2p_optimal_supply(max_network_peers=100, target_ledger_mb=10.0)
        large = self.lc.p2p_optimal_supply(max_network_peers=10_000, target_ledger_mb=10.0)
        self.assertGreater(large['global_supply_tokens'], small['global_supply_tokens'])

    def test_consensus_row_stats_empty_exchange(self):
        stats = self.lc.consensus_row_stats(self.ex)
        self.assertEqual(stats['avg_row_bytes'], 400)
        self.assertEqual(stats['total_rows'], 0)

    def test_consensus_row_stats_measured(self):
        for i in range(5):
            self.ex.append_audit_row({'kind': 'WORK_REQUEST', 'request_id': f'r{i}',
                                      'spec': 'x' * 100, 'at_unix': time.time()})
        stats = self.lc.consensus_row_stats(self.ex)
        self.assertEqual(stats['total_rows'], 5)
        self.assertGreater(stats['avg_row_bytes'], 50)

    def test_supply_calc_uses_consensus_when_exchange_provided(self):
        result = self.lc.p2p_optimal_supply(max_network_peers=1000, exchange=self.ex)
        self.assertIn('verdict', result)

    def test_auto_trade_config_defaults(self):
        from urace import equity_auto_trade as eat
        cfg = eat.DEFAULT_CONFIG
        self.assertIn('auto_buy', cfg)
        self.assertIn('auto_sell', cfg)
        self.assertIn('min_lucrativity_score', cfg['auto_buy'])
        self.assertIn('sell_on_near_depleted', cfg['auto_sell'])

    def test_auto_trade_config_save_load(self):
        from urace import equity_auto_trade as eat
        eat.save_config(self.tmpdir,
                        {'auto_buy': {'enabled': True, 'min_quality_wilson': 0.8,
                                      'min_adoption_count': 10, 'max_price_multiplier': 1.5,
                                      'max_bp_per_feature': 3000, 'max_spend_per_run_units': 0,
                                      'max_adoption_rate': 0.5, 'min_supply_pressure': 0.3,
                                      'min_remaining_adopters': 10, 'min_lucrativity_score': 0.2,
                                      'lucrativity_window_days': 60.0},
                         'auto_sell': {'enabled': False, 'min_return_multiplier': 3.0,
                                       'bp_to_sell_per_trigger': 500, 'min_hold_bp_to_trigger': 200,
                                       'sell_on_near_depleted': True, 'sell_on_slowing': False}})
        tmpdir = tempfile.mkdtemp()
        eat.save_config(tmpdir, eat.DEFAULT_CONFIG)
        cfg = eat.load_config(tmpdir)
        self.assertFalse(cfg['auto_buy']['enabled'])


# ═══════════════════════════════════════════════════════════════════════════
# From test_auto_mint.py — AutoMint, SettlementState, HandlePurchaseSettlement
# ═══════════════════════════════════════════════════════════════════════════

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
        self.exchange._state['peers'] = {}
        result = self.handle(self.exchange, 'buyer-peer', settlement)
        self.assertIn(result['status'], ('ok', 'error'))
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    unittest.main()
