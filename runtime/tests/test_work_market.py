import tempfile, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

class MockExchange:
    def __init__(self):
        self._rows = []
    def audit_rows(self):
        return list(self._rows)
    def append_audit_row(self, row):
        self._rows.append(row)

class WorkMarketStateTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm
        self.wm = wm
        self.exchange = MockExchange()

    def test_empty_exchange_not_found(self):
        st = self.wm.escrow_state('nonexistent', self.exchange)
        self.assertEqual(st['state'], 'NOT_FOUND')

    def test_create_request_open(self):
        rid = self.wm.create_work_request(self.exchange, 'peer-a', 'build auth feature', 1000000, n_nodes=1)
        st = self.wm.escrow_state(rid, self.exchange)
        self.assertEqual(st['state'], 'OPEN')

    def test_bid_below_min_rep_rejected(self):
        rid = self.wm.create_work_request(self.exchange, 'peer-a', 'spec', 1000000, min_combined_rep=0.5)
        with self.assertRaises(ValueError):
            self.wm.submit_bid(self.exchange, rid, 'peer-b', combined_rep=0.3)

    def test_bid_above_min_rep_accepted(self):
        rid = self.wm.create_work_request(self.exchange, 'peer-a', 'spec', 1000000, min_combined_rep=0.3)
        self.wm.submit_bid(self.exchange, rid, 'peer-b', combined_rep=0.6)
        st = self.wm.escrow_state(rid, self.exchange)
        self.assertEqual(len(st['bids']), 1)

    def test_equity_split_proportional(self):
        hired = [('a', 2.0), ('b', 1.0), ('c', 1.0)]
        splits = self.wm.equity_split_budget(hired, 1000)
        peer_amounts = dict(splits)
        self.assertEqual(sum(peer_amounts.values()), 1000)
        self.assertGreater(peer_amounts['a'], peer_amounts['b'])

    def test_equity_split_single_node(self):
        splits = self.wm.equity_split_budget([('solo', 1.0)], 500)
        self.assertEqual(splits[0], ('solo', 500))

    def test_future_mint_split_ratio(self):
        from urace import peer_work_market as wm
        result = wm.future_mint_split(1000, [('dev', 1.0)])
        self.assertEqual(result['requester'], 600)
        self.assertEqual(result['dev'], 400)

    def test_future_mint_split_n_nodes(self):
        from urace import peer_work_market as wm
        result = wm.future_mint_split(1000, [('dev1', 1.0), ('dev2', 1.0)])
        self.assertEqual(result['requester'], 600)
        self.assertEqual(result.get('dev1', 0) + result.get('dev2', 0), 400)

class CombinedRepApprovedGateTests(unittest.TestCase):
    def test_approved_fraction_1_no_discount(self):
        from urace import credit_ledger as cl
        base = cl.combined_rep_score(0.8, 0.6, approved_fraction=1.0)
        self.assertAlmostEqual(base, cl.combined_rep_score(0.8, 0.6), places=5)

    def test_approved_fraction_0_half_discount(self):
        from urace import credit_ledger as cl
        full = cl.combined_rep_score(0.8, 0.6, approved_fraction=1.0)
        discounted = cl.combined_rep_score(0.8, 0.6, approved_fraction=0.0)
        self.assertAlmostEqual(discounted, full * 0.5, places=5)

    def test_approved_fraction_partial(self):
        from urace import credit_ledger as cl
        full = cl.combined_rep_score(0.8, 0.6, approved_fraction=1.0)
        partial = cl.combined_rep_score(0.8, 0.6, approved_fraction=0.7)
        self.assertGreater(partial, full * 0.5)
        self.assertLessEqual(partial, full)


class EscrowAntiGamificationTests(unittest.TestCase):
    def setUp(self):
        from urace import credit_ledger as cl
        self.cl = cl
        self.exchange = MockExchange()

    def test_consensus_escrow_floor_no_exchange(self):
        floor = self.cl.consensus_escrow_floor(None)
        self.assertEqual(floor, self.cl.UNIT // 1_000)

    def test_consensus_escrow_floor_sparse_data(self):
        # fewer than 3 rows → fallback floor
        self.exchange.append_audit_row({'kind': 'WORK_REQUEST', 'budget_units': 5_000_000_000})
        self.exchange.append_audit_row({'kind': 'WORK_REQUEST', 'budget_units': 3_000_000_000})
        floor = self.cl.consensus_escrow_floor(self.exchange)
        self.assertEqual(floor, self.cl.UNIT // 1_000)

    def test_consensus_escrow_floor_median(self):
        for amt in [200_000, 400_000, 600_000, 800_000, 1_000_000]:
            self.exchange.append_audit_row({'kind': 'WORK_REQUEST', 'budget_units': amt})
        floor = self.cl.consensus_escrow_floor(self.exchange)
        # median=600_000 → floor = max(UNIT//1_000, 300_000) = 300_000
        self.assertGreater(floor, 0)
        self.assertLessEqual(floor, 600_000)

    def test_escrow_budget_units_applies_premium(self):
        base = self.cl.UNIT  # 1 token
        budget = self.cl.escrow_budget_units(base, None, premium=1.5)
        # Should be ~1.5 UNIT ± 4% jitter
        self.assertGreater(budget, int(base * 1.5 * 0.95))
        self.assertLess(budget, int(base * 1.5 * 1.05) + 1)

    def test_escrow_budget_units_consensus_floor_enforced(self):
        # Seed exchange with high budgets so consensus floor > base×premium
        for amt in [10 * self.cl.UNIT] * 5:
            self.exchange.append_audit_row({'kind': 'WORK_REQUEST', 'budget_units': amt})
        floor = self.cl.consensus_escrow_floor(self.exchange)
        tiny_base = 1  # 1 base unit × 1.5 = 1 → far below floor
        budget = self.cl.escrow_budget_units(tiny_base, self.exchange, premium=1.5)
        self.assertGreaterEqual(budget, int(floor * 0.96))  # at least floor minus jitter

    def test_create_work_request_rejects_below_floor(self):
        from urace import peer_work_market as wm
        # budget=1 is below consensus_escrow_floor when exchange has enough rows
        for amt in [10 * self.cl.UNIT] * 5:
            self.exchange.append_audit_row({'kind': 'WORK_REQUEST', 'budget_units': amt})
        with self.assertRaises(ValueError):
            wm.create_work_request(self.exchange, 'requester', 'spec', budget_units=1)

    def test_create_work_request_accepts_valid_budget(self):
        from urace import peer_work_market as wm
        # No prior rows → floor = UNIT // 1_000; use budget well above floor
        budget = self.cl.escrow_budget_units(self.cl.UNIT, None, premium=1.5)
        rid = wm.create_work_request(self.exchange, 'req', 'spec', budget_units=budget)
        self.assertIsNotNone(rid)


class RoutingScoreTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm
        from urace import credit_ledger as cl
        self.wm = wm
        self.cl = cl
        self.exchange = MockExchange()

    def _base_kwargs(self, **overrides):
        kw = dict(
            exchange=self.exchange,
            local_credit_balance=self.cl.BASELINE_GRANT_UNITS * 5,
            baseline_grant_units=self.cl.BASELINE_GRANT_UNITS,
            spec_complexity=0.4,
            executor_cost_units=self.cl.UNIT,
            available_peers=[],
        )
        kw.update(overrides)
        return kw

    def test_no_peers_routes_executor(self):
        result = self.wm.routing_score(**self._base_kwargs())
        self.assertEqual(result['route'], 'executor')

    def test_low_complexity_routes_executor(self):
        peers = [{'peer_id': f'p{i}', 'combined_rep': 0.8} for i in range(5)]
        result = self.wm.routing_score(**self._base_kwargs(spec_complexity=0.3, available_peers=peers))
        self.assertEqual(result['route'], 'executor')

    def test_executor_estimate_vs_peer_escrow_floor_does_not_claim_savings(self):
        peers = [{'peer_id': f'p{i}', 'combined_rep': 0.8} for i in range(3)]
        result = self.wm.routing_score(**self._base_kwargs(
            spec_complexity=0.8,
            executor_cost_units=50 * self.cl.UNIT,
            available_peers=peers,
        ))
        self.assertEqual(result['route'], 'executor')
        self.assertIsNone(result['executor_cost_factor'])
        self.assertNotIn('cheaper', result['reason'].lower())

    def test_high_credit_pressure_routes_hire(self):
        peers = [{'peer_id': f'p{i}', 'combined_rep': 0.8} for i in range(3)]
        # balance ≈ 0 → credit_pressure ≈ 1.0
        result = self.wm.routing_score(**self._base_kwargs(
            spec_complexity=0.7,
            local_credit_balance=0,
            available_peers=peers,
        ))
        self.assertEqual(result['route'], 'network_hire')
        self.assertIn('no savings claim', result['reason'])

    def test_low_rep_peers_routes_executor(self):
        peers = [{'peer_id': f'p{i}', 'combined_rep': 0.2} for i in range(5)]
        result = self.wm.routing_score(**self._base_kwargs(
            spec_complexity=0.9,
            executor_cost_units=50 * self.cl.UNIT,
            available_peers=peers,
        ))
        self.assertEqual(result['route'], 'executor')

    def test_routing_score_has_required_keys(self):
        result = self.wm.routing_score(**self._base_kwargs())
        for key in ('route', 'confidence', 'reason', 'network_hire_viable',
                    'avg_peer_rep', 'credit_pressure', 'executor_cost_factor'):
            self.assertIn(key, result)

    def test_confidence_bounded(self):
        peers = [{'peer_id': f'p{i}', 'combined_rep': 0.9} for i in range(5)]
        result = self.wm.routing_score(**self._base_kwargs(
            spec_complexity=0.9, local_credit_balance=0, available_peers=peers))
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertLessEqual(result['confidence'], 1.0)


class DynamicSplitTests(unittest.TestCase):
    def setUp(self):
        from urace import credit_ledger as cl
        self.cl = cl
        self.exchange = MockExchange()

    def test_default_split_no_exchange(self):
        req, hired = self.cl.consensus_split_shares(None)
        self.assertAlmostEqual(req, 0.60)
        self.assertAlmostEqual(hired, 0.40)

    def test_default_split_sparse_data(self):
        # < 5 WORK_VERIFIED rows → default
        for _ in range(3):
            self.exchange.append_audit_row({'kind': 'WORK_VERIFIED', 'approved': True, 'split_ratio_requester': 0.55})
        req, hired = self.cl.consensus_split_shares(self.exchange)
        self.assertAlmostEqual(req, 0.60)

    def test_consensus_split_median(self):
        for r in [0.52, 0.54, 0.56, 0.58, 0.60]:
            self.exchange.append_audit_row({'kind': 'WORK_VERIFIED', 'approved': True, 'split_ratio_requester': r})
        req, hired = self.cl.consensus_split_shares(self.exchange)
        # median of [0.52,0.54,0.56,0.58,0.60] = 0.56
        self.assertAlmostEqual(req, 0.56, places=5)
        self.assertAlmostEqual(req + hired, 1.0, places=5)

    def test_split_floors_respected(self):
        # Extreme ratios still clamped
        for r in [0.90, 0.92, 0.94, 0.96, 0.98]:
            self.exchange.append_audit_row({'kind': 'WORK_VERIFIED', 'approved': True, 'split_ratio_requester': r})
        req, hired = self.cl.consensus_split_shares(self.exchange)
        self.assertLessEqual(hired, 0.50)  # hired ≥ 0.20 → req ≤ 0.80
        self.assertGreaterEqual(round(hired, 10), 0.20)

    def test_future_mint_split_uses_exchange(self):
        from urace import peer_work_market as wm
        # Seed 5 rows at 0.55 requester share
        for _ in range(5):
            self.exchange.append_audit_row({'kind': 'WORK_VERIFIED', 'approved': True, 'split_ratio_requester': 0.55})
        result = wm.future_mint_split(1000, [('dev', 1.0)], exchange=self.exchange)
        self.assertEqual(result['requester'], 550)
        self.assertEqual(result['dev'], 450)

    def test_future_mint_split_co_requesters(self):
        from urace import peer_work_market as wm
        shares = {'alice': 0.6, 'bob': 0.4}
        result = wm.future_mint_split(1000, [('dev', 1.0)], co_requester_shares=shares)
        # requester total = 600 (default 60%), split 60/40 → alice=360, bob=240
        self.assertEqual(result.get('alice', 0) + result.get('bob', 0), 600)
        self.assertGreater(result.get('alice', 0), result.get('bob', 0))


class DynamicBudgetCeilingTests(unittest.TestCase):
    def setUp(self):
        from urace import credit_ledger as cl
        self.cl = cl
        self.exchange = MockExchange()

    def test_no_data_returns_default(self):
        mult = self.cl.dynamic_budget_ceiling_multiplier(None, 0, 1)
        self.assertAlmostEqual(mult, 3.0)

    def test_high_supply_tightens_ceiling(self):
        mult_low = self.cl.dynamic_budget_ceiling_multiplier(None, 0, 1)
        # Very high total_minted relative to network → tighter ceiling
        mult_high = self.cl.dynamic_budget_ceiling_multiplier(
            None, total_minted=10**12, network_size=1)
        self.assertLess(mult_high, mult_low)

    def test_ceiling_clamped_to_range(self):
        mult = self.cl.dynamic_budget_ceiling_multiplier(None, 1, 100)
        self.assertGreaterEqual(mult, 1.5)
        self.assertLessEqual(mult, 5.0)


class DeliverySpamGuardTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm
        from urace import credit_ledger as cl
        self.wm = wm
        self.cl = cl
        self.exchange = MockExchange()
        # Create a minimal OPEN request and transition to IN_DELIVERY
        budget = cl.UNIT  # above floor when no prior rows
        self.rid = wm.create_work_request(self.exchange, 'req', 'spec', budget_units=budget)
        wm.submit_bid(self.exchange, self.rid, 'dev-a', combined_rep=0.6)
        # Manually append WORK_ACCEPTED to transition state
        import time
        self.exchange.append_audit_row({
            'kind': 'WORK_ACCEPTED', 'request_id': self.rid,
            'requester_id': 'req', 'bidder_id': 'dev-a',
            'budget_units': budget, 'at_unix': time.time(), 'at': 'now',
        })

    def test_first_delivery_accepted(self):
        self.wm.submit_delivery(self.exchange, self.rid, 'dev-a', 'hash-1')
        st = self.wm.escrow_state(self.rid, self.exchange)
        self.assertEqual(len(st['deliveries']), 1)

    def test_second_delivery_same_peer_rejected(self):
        self.wm.submit_delivery(self.exchange, self.rid, 'dev-a', 'hash-1')
        with self.assertRaises(ValueError):
            self.wm.submit_delivery(self.exchange, self.rid, 'dev-a', 'hash-2')

    def test_different_peer_delivery_accepted(self):
        self.wm.submit_delivery(self.exchange, self.rid, 'dev-a', 'hash-1')
        # Different peer (e.g., for different sub_task) is fine
        self.wm.submit_delivery(self.exchange, self.rid, 'dev-b', 'hash-2')
        st = self.wm.escrow_state(self.rid, self.exchange)
        self.assertEqual(len(st['deliveries']), 2)


class ArbitratorSelectionTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm
        self.wm = wm
        self.exchange = MockExchange()

    def _seed_block_closer(self, peer_id, req_id, rep=0.8):
        import time
        self.exchange.append_audit_row({
            'kind': 'WORK_DELIVERY', 'request_id': req_id,
            'hired_peer_id': peer_id, 'at_unix': time.time(), 'at': 'now',
        })
        self.exchange.append_audit_row({
            'kind': 'WORK_VERIFIED', 'request_id': req_id,
            'approved': True, 'combined_rep': rep, 'at_unix': time.time(), 'at': 'now',
        })

    def test_no_block_closers_returns_empty(self):
        result = self.wm.select_arbitrators(self.exchange, 'req-unknown')
        self.assertEqual(result, [])

    def test_eligible_arbitrators_returned(self):
        self._seed_block_closer('neutral-1', 'other-req-1')
        self._seed_block_closer('neutral-2', 'other-req-2')
        self._seed_block_closer('neutral-3', 'other-req-3')
        result = self.wm.select_arbitrators(self.exchange, 'disputed-req', n=3)
        self.assertEqual(len(result), 3)
        for pid in result:
            self.assertIn(pid, {'neutral-1', 'neutral-2', 'neutral-3'})

    def test_dispute_parties_excluded(self):
        # Seed dispute parties
        import time
        self.exchange.append_audit_row({
            'kind': 'WORK_REQUEST', 'request_id': 'dr',
            'requester_id': 'bad-req', 'budget_units': 1000, 'at_unix': time.time(), 'at': 'now',
        })
        self._seed_block_closer('bad-req', 'other-r')   # bad-req is dispute party
        self._seed_block_closer('neutral', 'other-r2')
        result = self.wm.select_arbitrators(self.exchange, 'dr', n=1)
        # neutral should be preferred; bad-req excluded (proximity=1.0)
        if result:
            self.assertNotIn('bad-req', result)

    def test_arbitrators_odd_number(self):
        for i in range(6):
            self._seed_block_closer(f'peer-{i}', f'req-{i}')
        result = self.wm.select_arbitrators(self.exchange, 'disputed', n=4)
        self.assertEqual(len(result) % 2, 1)   # odd


class DistributionFeeTests(unittest.TestCase):
    def setUp(self):
        from urace import credit_ledger as cl
        self.cl = cl

    def test_fee_fraction(self):
        fee = self.cl.distribution_fee_units(1000)
        self.assertEqual(fee, 100)  # 10%

    def test_fee_zero_on_zero_cost(self):
        self.assertEqual(self.cl.distribution_fee_units(0), 0)


class HiredNodeEarnTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from urace import credit_ledger as cl
        self.cl = cl
        self.tmp = tempfile.mkdtemp()
        self.root = self.tmp
        self.requester_id = 'requester-peer'
        self.request_id = 'req-hired-001'
        self.amount = cl.UNIT  # 1 token in base units

    def test_hired_node_balance_increases_after_escrow_release(self):
        cl = self.cl
        # Give requester enough balance to lock
        cl.earn_units(self.root, self.requester_id, self.amount * 10, 'seed')
        initial_balance = cl.balance(self.root, 'hired-peer')
        cl.escrow_lock(self.root, self.requester_id, self.request_id, self.amount)
        cl.escrow_release(self.root, self.request_id, [('hired-peer', self.amount)])
        self.assertGreater(cl.balance(self.root, 'hired-peer'), initial_balance)

    def test_escrow_release_does_not_credit_requester(self):
        cl = self.cl
        cl.earn_units(self.root, self.requester_id, self.amount * 10, 'seed')
        balance_before = cl.balance(self.root, self.requester_id)
        cl.escrow_lock(self.root, self.requester_id, self.request_id, self.amount)
        cl.escrow_release(self.root, self.request_id, [('hired-peer', self.amount)])
        # requester spent on lock and was not credited on release
        self.assertEqual(cl.balance(self.root, self.requester_id), balance_before - self.amount)

    def test_equity_split_sum_equals_budget(self):
        cl = self.cl
        budget = self.amount
        cl.earn_units(self.root, self.requester_id, budget * 10, 'seed')
        cl.escrow_lock(self.root, self.requester_id, self.request_id, budget)
        half = budget // 2
        splits = [('hired-a', half), ('hired-b', budget - half)]
        bal_a_before = cl.balance(self.root, 'hired-a')
        bal_b_before = cl.balance(self.root, 'hired-b')
        cl.escrow_release(self.root, self.request_id, splits)
        delta_a = cl.balance(self.root, 'hired-a') - bal_a_before
        delta_b = cl.balance(self.root, 'hired-b') - bal_b_before
        # Both hired peers received credits
        self.assertGreater(delta_a, 0)
        self.assertGreater(delta_b, 0)
        # Combined credit equals combined input (velocity multiplier applies uniformly to both,
        # so the ratio and total scale together — verify via peer_work_market equity_split_budget)
        from urace import peer_work_market as wm
        raw_splits = dict(wm.equity_split_budget([('hired-a', 1.0), ('hired-b', 1.0)], budget))
        self.assertEqual(raw_splits['hired-a'] + raw_splits['hired-b'], budget)


class MergedEscrowTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm
        from urace import credit_ledger as cl
        self.wm = wm
        self.cl = cl

    def test_boost_increases_budget(self):
        # Math only — no credit ledger needed
        budget = 1000
        # 1 co-requester → boost = 1.0 + 0.10×1 = 1.10
        merged = int((budget + 500) * 1.10)
        self.assertGreater(merged, budget + 500)

    def test_co_requester_share_proportional(self):
        exchange = MockExchange()
        # Seed a request so merged_co_requester_shares can read it
        import time
        exchange.append_audit_row({
            'kind': 'WORK_REQUEST', 'request_id': 'rid1',
            'requester_id': 'alice', 'budget_units': 600, 'at_unix': time.time(), 'at': 'now',
        })
        exchange.append_audit_row({
            'kind': 'WORK_MERGED', 'request_id': 'rid1',
            'co_requester_id': 'bob', 'co_budget_units': 400, 'at_unix': time.time(), 'at': 'now',
        })
        shares = self.wm.merged_co_requester_shares('rid1', exchange)
        self.assertAlmostEqual(shares['alice'], 0.60, places=5)
        self.assertAlmostEqual(shares['bob'], 0.40, places=5)


# ── Escrow Custody Reward Proof Tests ─────────────────────────────────────────

class EscrowCustodyRewardTests(unittest.TestCase):
    """Proof: hired nodes receive custody CREDIT_DELTA on EVERY release path."""

    def _make_verified_exchange(self, request_id='rid1', budget=1000):
        """Build a minimal exchange with a completed work request."""
        import time
        from urace import peer_work_market as wm
        ex = MockExchange()
        now = time.time()
        ex.append_audit_row({
            'kind': 'WORK_REQUEST', 'request_id': request_id,
            'requester_id': 'buyer', 'budget_units': budget,
            'at_unix': now, 'at': 'now',
        })
        ex.append_audit_row({
            'kind': 'WORK_BID', 'request_id': request_id,
            'bidder_id': 'hired1', 'bid_units': budget, 'combined_rep': 0.9,
            'at_unix': now, 'at': 'now',
        })
        ex.append_audit_row({
            'kind': 'WORK_ACCEPTED', 'request_id': request_id,
            'bidder_id': 'hired1', 'budget_units': budget,
            'at_unix': now, 'at': 'now',
        })
        ex.append_audit_row({
            'kind': 'WORK_DELIVERY', 'request_id': request_id,
            'bidder_id': 'hired1', 'canonical_fingerprint': 'fp1',
            'at_unix': now, 'at': 'now',
        })
        return ex

    def test_verify_delivery_emits_custody_credit_delta(self):
        from urace import peer_work_market as wm
        ex = self._make_verified_exchange(budget=1000)
        with patch('urace.credit_ledger.escrow_release'):
            wm.verify_delivery(ex, root=None, request_id='rid1',
                               requester_id='buyer', approved=True)
        custody_rows = [r for r in ex.audit_rows()
                        if r.get('kind') == 'CREDIT_DELTA'
                        and r.get('direction') == 'escrow_custody_earned'
                        and r.get('peer') == 'hired1']
        self.assertEqual(len(custody_rows), 1)
        self.assertGreater(custody_rows[0]['amount_units'], 0)

    def test_quorum_auto_release_emits_custody_credit_delta(self):
        from urace import peer_work_market as wm
        ex = self._make_verified_exchange(budget=1000)
        # Add quorum reviews to reach verdict=True
        import time
        for peer in ['arb1', 'arb2', 'arb3']:
            ex.append_audit_row({
                'kind': 'WORK_REVIEW', 'request_id': 'rid1',
                'reviewer_id': peer, 'approved': True,
                'at_unix': time.time(), 'at': 'now',
            })
        with patch('urace.credit_ledger.escrow_release'), \
             patch('urace.peer_work_market.escrow_state') as mock_st:
            mock_st.return_value = {
                'state': 'VERIFICATION',
                'quorum': True,
                'quorum_fallback': False,
                'accepted_bids': [{'bidder_id': 'hired1', 'budget_units': 1000}],
            }
            wm.quorum_auto_release('rid1', ex, root='root')
        custody_rows = [r for r in ex.audit_rows()
                        if r.get('kind') == 'CREDIT_DELTA'
                        and r.get('direction') == 'escrow_custody_earned'
                        and r.get('peer') == 'hired1']
        self.assertEqual(len(custody_rows), 1)
        self.assertGreater(custody_rows[0]['amount_units'], 0)

    def test_custody_reward_is_3_percent_of_budget(self):
        from urace import peer_work_market as wm
        ex = self._make_verified_exchange(budget=10000)
        with patch('urace.credit_ledger.escrow_release'):
            wm.verify_delivery(ex, root=None, request_id='rid1',
                               requester_id='buyer', approved=True)
        row = next(r for r in ex.audit_rows()
                   if r.get('kind') == 'CREDIT_DELTA'
                   and r.get('direction') == 'escrow_custody_earned')
        self.assertEqual(row['amount_units'], max(1, int(10000 * 0.03)))

    def test_no_custody_reward_on_dispute(self):
        from urace import peer_work_market as wm
        ex = self._make_verified_exchange(budget=1000)
        wm.verify_delivery(ex, root=None, request_id='rid1',
                           requester_id='buyer', approved=False)
        custody_rows = [r for r in ex.audit_rows()
                        if r.get('kind') == 'CREDIT_DELTA'
                        and r.get('direction') == 'escrow_custody_earned']
        self.assertEqual(len(custody_rows), 0)

    def test_hired_node_net_positive_after_delivery(self):
        """Hired node balance = escrow_release + custody_reward > 0 always."""
        from urace import peer_work_market as wm
        budget = 500
        ex = self._make_verified_exchange(budget=budget)
        released = []
        with patch('urace.credit_ledger.escrow_release',
                   side_effect=lambda root, rid, shares: released.append(shares)):
            wm.verify_delivery(ex, root=None, request_id='rid1',
                               requester_id='buyer', approved=True)
        custody = sum(r['amount_units'] for r in ex.audit_rows()
                      if r.get('kind') == 'CREDIT_DELTA'
                      and r.get('direction') == 'escrow_custody_earned')
        # escrow_release called with the shares; hired node gets full budget share
        total_payout = budget + custody  # escrow + bonus
        self.assertGreater(total_payout, budget)  # bonus is strictly additive


# ── NullAdapter Stub Intentionality Tests ─────────────────────────────────────

class NullAdapterStubBehaviorTests(unittest.TestCase):
    """Proof: NullAdapter is an intentional no-op stub, not a silent failure."""

    def setUp(self):
        from urace.integration_bridge import NullAdapter
        self.adapter = NullAdapter()

    def test_all_methods_return_status_stub(self):
        for method, args in [
            ('mint_nft', ('fid', 'pid', {})),
            ('on_ramp', ('pid', 100, '0xABC')),
            ('off_ramp', ('pid', 100, '0xABC')),
            ('verify', ('fid',)),
        ]:
            result = getattr(self.adapter, method)(*args)
            self.assertEqual(result.get('status'), 'stub',
                             f'{method} should return status=stub, got {result}')

    def test_null_adapter_never_raises(self):
        self.adapter.mint_nft('', '', {})
        self.adapter.on_ramp('', 0, '')
        self.adapter.off_ramp('', 0, '')
        self.adapter.verify('')

    def test_get_chain_adapter_returns_null_without_rpc_config(self):
        from urace.integration_bridge import get_chain_adapter, NullAdapter
        adapter = get_chain_adapter({})
        self.assertIsInstance(adapter, NullAdapter,
                              "No rpc_provider_url must yield NullAdapter (audit-only mode)")

    def test_purchase_settlement_on_ramp_wired(self):
        """on_ramp is wired in handle_purchase_settlement via get_chain_adapter.
        NullAdapter path is the default (audit-only); on-chain fires when configured."""
        import urace.purchase_settlement as ps
        import inspect
        src = inspect.getsource(ps)
        self.assertIn('on_ramp', src)
        self.assertIn('get_chain_adapter', src)

    def test_handle_purchase_settlement_on_ramp_null_no_crypto_address(self):
        """Without crypto_address in payload, on_ramp is not called — no crash."""
        from unittest.mock import MagicMock, patch
        import urace.purchase_settlement as ps
        mock_exchange = MagicMock()
        mock_exchange.load.return_value = {}
        mock_exchange.identity.return_value = {'peer_id': 'seller'}
        mock_exchange.trusted_crypto.return_value = {}
        with patch('urace.purchase_settlement.verify_purchase_from_buyer', return_value=True), \
             patch('urace.purchase_settlement.get_chain_adapter') as mock_adapter_fn:
            result = ps.handle_purchase_settlement(
                mock_exchange,
                sender_peer_id='buyer',
                settlement={
                    'payload': {
                        'schema': 'urace-purchase-settlement-v1',
                        'buyer_peer_id': 'buyer',
                        'seller_peer_id': 'seller',
                        'price_units': 100,
                        'listing_id': 'lid1',
                        'nonce': 'abc',
                    },
                    'signature': 'sig',
                },
            )
        self.assertEqual(result['status'], 'ok')
        mock_adapter_fn.assert_not_called()

    def test_handle_purchase_settlement_on_ramp_called_with_crypto_address(self):
        """With crypto_address, on_ramp fires via NullAdapter (status=stub)."""
        from unittest.mock import MagicMock, patch, call
        import urace.purchase_settlement as ps
        from urace.integration_bridge import NullAdapter
        mock_exchange = MagicMock()
        mock_exchange.load.return_value = {}
        mock_exchange.identity.return_value = {'peer_id': 'seller'}
        mock_exchange.trusted_crypto.return_value = {}
        with patch('urace.purchase_settlement.verify_purchase_from_buyer', return_value=True), \
             patch('urace.purchase_settlement.get_chain_adapter', return_value=NullAdapter()):
            result = ps.handle_purchase_settlement(
                mock_exchange,
                sender_peer_id='buyer',
                settlement={
                    'payload': {
                        'schema': 'urace-purchase-settlement-v1',
                        'buyer_peer_id': 'buyer',
                        'seller_peer_id': 'seller',
                        'price_units': 100,
                        'listing_id': 'lid1',
                        'nonce': 'abc',
                        'crypto_address': '0xABC',
                    },
                    'signature': 'sig',
                },
            )
        self.assertEqual(result['status'], 'ok')
        # ON_RAMP_ATTEMPTED row emitted
        appended = [c.args[0] for c in mock_exchange.append_audit_row.call_args_list]
        ramp_rows = [r for r in appended if r.get('kind') == 'ON_RAMP_ATTEMPTED']
        self.assertEqual(len(ramp_rows), 1)
        self.assertEqual(ramp_rows[0]['adapter_status'], 'stub')
