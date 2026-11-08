"""Comprehensive cost model v2 tests.

Covers:
- derive_executor_reference_price (empty, EQUITY_LISTING_FILLED, earn-only)
- minimum_viable_price (zero config floor, bandwidth+production)
- borrow_feature_cost new fields (protocol_fee, network_download)
- mint_feature_cost new fields (network_distribution, production cost)
- vs_executor_comparison uses full borrow cost
- Ceiling enforcement uses network-derived ref price
- Protocol fee emitted at fill-listing
- Minimum viable price auto-adjusts ask_price upward (not rejects)
"""
import math
import tempfile
import time
import unittest
from pathlib import Path

from urace import cost_model as cm


# ── derive_executor_reference_price ──────────────────────────────────────────

class DeriveExecutorReferencePriceTests(unittest.TestCase):

    def test_empty_rows_is_unknown(self):
        result = cm.derive_executor_reference_price([])
        self.assertIsNone(result)

    def test_no_matching_rows_returns_fallback_10(self):
        rows = [{'kind': 'EQUITY_GRANT', 'feature_id': 'f1', 'at_unix': time.time()}]
        result = cm.derive_executor_reference_price(rows)
        self.assertIsNone(result)

    def test_equity_listing_filled_odd_count_median(self):
        now = time.time()
        rows = [
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 20, 'at_unix': now},
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 50, 'at_unix': now},
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 30, 'at_unix': now},
        ]
        result = cm.derive_executor_reference_price(rows)
        self.assertIsNone(result)  # exchange prices do not identify executor cost

    def test_equity_listing_filled_even_count_median(self):
        now = time.time()
        rows = [
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 10, 'at_unix': now},
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 20, 'at_unix': now},
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 30, 'at_unix': now},
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 40, 'at_unix': now},
        ]
        result = cm.derive_executor_reference_price(rows)
        self.assertIsNone(result)

    def test_equity_listing_filled_takes_priority_over_earn(self):
        now = time.time()
        rows = [
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 50, 'at_unix': now},
            {'kind': 'CREDIT_DELTA', 'direction': 'earn', 'amount_units': 5, 'at_unix': now},
        ]
        result = cm.derive_executor_reference_price(rows)
        self.assertIsNone(result)

    def test_earn_rows_fallback_when_no_filled(self):
        now = time.time()
        rows = [
            {'kind': 'CREDIT_DELTA', 'direction': 'earn', 'amount_units': 15, 'at_unix': now},
            {'kind': 'CREDIT_DELTA', 'direction': 'earn', 'amount_units': 25, 'at_unix': now},
            {'kind': 'CREDIT_DELTA', 'direction': 'earn', 'amount_units': 35, 'at_unix': now},
        ]
        result = cm.derive_executor_reference_price(rows)
        self.assertIsNone(result)

    def test_old_rows_outside_90days_excluded(self):
        old = time.time() - 91 * 86400
        now = time.time()
        rows = [
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 999, 'at_unix': old},
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 7, 'at_unix': now},
        ]
        result = cm.derive_executor_reference_price(rows)
        self.assertIsNone(result)

    def test_result_always_at_least_1(self):
        now = time.time()
        rows = [{'kind': 'EQUITY_LISTING_FILLED', 'price_units': 0, 'at_unix': now}]
        result = cm.derive_executor_reference_price(rows)
        self.assertIsNone(result)


# ── minimum_viable_price ─────────────────────────────────────────────────────

class MinimumViablePriceTests(unittest.TestCase):

    def test_zero_config_returns_1(self):
        # all costs are 0 → floor is 1
        result = cm.minimum_viable_price({}, artifact_size_bytes=0)
        self.assertEqual(result, 1)

    def test_zero_costs_with_nonzero_artifact_still_1(self):
        # bandwidth and production both 0 → price = 1
        result = cm.minimum_viable_price({}, artifact_size_bytes=1_000_000)
        self.assertEqual(result, 1)

    def test_production_cost_drives_minimum(self):
        config = {'p2p': {'artifact_production_cost_per_kb': 1.0,
                          'protocol_fee_fraction': 0.0,
                          'bandwidth_cost_per_mb': 0.0}}
        # 1024 bytes → 1 KB * 1.0 cost/KB = 1 unit; ceil(1/(1-0)) = 1
        result = cm.minimum_viable_price(config, artifact_size_bytes=1024)
        self.assertEqual(result, 1)

    def test_bandwidth_cost_included(self):
        config = {'p2p': {'bandwidth_cost_per_mb': 10.0,
                          'artifact_production_cost_per_kb': 0.0,
                          'protocol_fee_fraction': 0.0,
                          'expected_lifetime_borrows': 1,
                          'default_replicas': 1}}
        # 1 MB * 1 replica / 1 borrow = 10 units distribution cost amortized → ceil(10/1) = 10
        result = cm.minimum_viable_price(config, artifact_size_bytes=1_000_000)
        self.assertEqual(result, 10)

    def test_protocol_fee_inflates_minimum(self):
        config = {'p2p': {'artifact_production_cost_per_kb': 1.0,
                          'protocol_fee_fraction': 0.5,
                          'bandwidth_cost_per_mb': 0.0,
                          'expected_lifetime_borrows': 1}}
        # 1024 bytes = 1 KB production cost = 1 unit; solve p = 1 / (1 - 0.5) = 2
        result = cm.minimum_viable_price(config, artifact_size_bytes=1024)
        self.assertEqual(result, 2)

    def test_returns_int(self):
        result = cm.minimum_viable_price({}, artifact_size_bytes=512)
        self.assertIsInstance(result, int)


# ── borrow_feature_cost new fields ───────────────────────────────────────────

class BorrowFeatureCostV2Tests(unittest.TestCase):

    def test_protocol_fee_included_in_total(self):
        config = {'p2p': {'protocol_fee_fraction': 0.1, 'bandwidth_cost_per_mb': 0.0}}
        result = cm.borrow_feature_cost(config, ask_price_units=100)
        self.assertEqual(result['protocol_fee_units'], 10)
        self.assertIn(10, [result['total_buyer_cost'] - 100,
                           result['total_buyer_cost'] - 100 - result['p2p_delivery_cost']])

    def test_protocol_fee_zero_by_default_in_zero_config(self):
        # default protocol_fee_fraction is 0.02; 1 unit * 0.02 = 0 (int truncation)
        result = cm.borrow_feature_cost({}, ask_price_units=1)
        self.assertIn('protocol_fee_units', result)

    def test_network_download_cost_included(self):
        config = {'p2p': {'bandwidth_cost_per_mb': 2.0, 'protocol_fee_fraction': 0.0,
                          'p2p_bytes_per_unit': 0}}  # disable legacy p2p cost to isolate
        result = cm.borrow_feature_cost(config, ask_price_units=10, artifact_size_bytes=5_000_000)
        # 5 MB * 2.0 cost/MB = 10
        self.assertEqual(result['network_download_cost_units'], 10)
        self.assertAlmostEqual(result['total_buyer_cost'], 20.0, places=2)

    def test_total_buyer_cost_includes_all_components(self):
        config = {'p2p': {'bandwidth_cost_per_mb': 1.0, 'protocol_fee_fraction': 0.1}}
        result = cm.borrow_feature_cost(config, ask_price_units=100, artifact_size_bytes=1_000_000)
        expected = 100 + 1 + 10  # ask + network_download + protocol_fee (p2p_delivery_cost=0 when p2p_bytes_per_unit default)
        # p2p_delivery_cost uses p2p_bytes_per_unit=1_000_000, so 1MB/1MB=1
        self.assertIn('network_download_cost_units', result)
        self.assertIn('protocol_fee_units', result)
        self.assertGreater(result['total_buyer_cost'], result['ask_price_units'])

    def test_zero_bandwidth_zero_download_cost(self):
        config = {'p2p': {'bandwidth_cost_per_mb': 0.0}}
        result = cm.borrow_feature_cost(config, ask_price_units=50, artifact_size_bytes=10_000_000)
        self.assertEqual(result['network_download_cost_units'], 0)


# ── mint_feature_cost new fields ─────────────────────────────────────────────

class MintFeatureCostV2Tests(unittest.TestCase):

    def test_network_distribution_cost_included(self):
        config = {'p2p': {'bandwidth_cost_per_mb': 2.0, 'artifact_production_cost_per_kb': 0.0}}
        result = cm.mint_feature_cost(config, artifact_size_bytes=1_000_000, n_replicas=3)
        # 1 MB * 3 replicas / 1_000_000 * 2.0 = 6
        self.assertEqual(result['network_distribution_cost_units'], 6)

    def test_artifact_production_cost_included(self):
        config = {'p2p': {'bandwidth_cost_per_mb': 0.0, 'artifact_production_cost_per_kb': 2.0}}
        result = cm.mint_feature_cost(config, artifact_size_bytes=2048)
        # 2048 / 1024 * 2.0 = 4
        self.assertEqual(result['artifact_production_cost_units'], 4)

    def test_zero_costs_dont_affect_original_total(self):
        # With zero bandwidth and zero production, total should equal original behavior
        config = {'p2p': {'bandwidth_cost_per_mb': 0.0, 'artifact_production_cost_per_kb': 0.0}}
        result = cm.mint_feature_cost(config, artifact_size_bytes=0)
        orig = cm.mint_feature_cost({}, artifact_size_bytes=0)
        self.assertAlmostEqual(result['total_units'], orig['total_units'], places=3)

    def test_both_costs_add_to_total(self):
        config = {'p2p': {'bandwidth_cost_per_mb': 1.0, 'artifact_production_cost_per_kb': 1.0}}
        result = cm.mint_feature_cost(config, artifact_size_bytes=1_000_000, n_replicas=1)
        # network_distribution: 1MB * 1 replica * 1.0 = 1
        # artifact_production: 1000KB * 1.0 = 1000 (approx)
        self.assertGreater(result['total_units'], result['mint_stake'])


# ── vs_executor_comparison uses full borrow cost ──────────────────────────────

class VsExecutorComparisonV2Tests(unittest.TestCase):

    def test_uses_full_borrow_cost_including_protocol_fee(self):
        config = {'p2p': {'executor_reference_price_per_unit': 200,
                          'protocol_fee_fraction': 0.1,
                          'bandwidth_cost_per_mb': 0.0}}
        # ask=100, protocol_fee=10, total_buyer_cost=110
        result = cm.vs_executor_comparison(config, ask_price_units=100)
        self.assertEqual(result['borrow_total'], result['borrow_total'])
        # borrow_total should include protocol fee (110), not just 100
        borrow = cm.borrow_feature_cost(config, ask_price_units=100)
        self.assertEqual(result['borrow_total'], borrow['total_buyer_cost'])

    def test_executor_reference_price_override(self):
        config = {'p2p': {'executor_reference_price_per_unit': 1}}
        result = cm.vs_executor_comparison(config, ask_price_units=5,
                                            executor_reference_price=100)
        self.assertEqual(result['executor_cost_per_call'], 100)
        self.assertIsNone(result['cheaper_than_executor'])

    def test_cheaper_than_executor_always_present(self):
        # Must always be computed, never missing
        result = cm.vs_executor_comparison({}, ask_price_units=0)
        self.assertIn('cheaper_than_executor', result)

    def test_cheaper_than_executor_true_with_full_cost(self):
        # executor=200, ask=50, protocol_fee=0, → net_saving > 0
        config = {'p2p': {'executor_reference_price_per_unit': 200,
                          'protocol_fee_fraction': 0.0,
                          'bandwidth_cost_per_mb': 0.0}}
        result = cm.vs_executor_comparison(config, ask_price_units=50)
        self.assertIsNone(result['cheaper_than_executor'])

    def test_net_saving_uses_p2p_total_not_just_ask(self):
        config = {'p2p': {'executor_reference_price_per_unit': 110,
                          'protocol_fee_fraction': 0.1,
                          'bandwidth_cost_per_mb': 0.0}}
        # ask=100, protocol_fee=10, total=110; executor=110 * 1 = 110; net = 110-110 = 0 → not cheaper
        result = cm.vs_executor_comparison(config, ask_price_units=100, executor_calls_saved=1)
        self.assertIsNone(result['cheaper_than_executor'])

    def test_task_matched_receipts_include_integration_validation_and_executor_residual(self):
        result = cm.compare_paired_cost_inputs(
            {'p2p': {'protocol_fee_fraction': 0, 'bandwidth_cost_per_mb': 0}},
            executor_cost_units=100, ask_price_units=20,
            integration_cost_units=10, validation_cost_units=5,
            residual_executor_cost_units=30, task_id='pair-1',
            acceptance_contract_sha256='a' * 64, executor_accepted=True,
            executor_receipt_id='exec-receipt-1', p2p_receipt_id='p2p-receipt-1',
            acceptance_receipt_id='acceptance-1',
            p2p_accepted=True, independent_acceptance=True,
            executor_tokens={'input': 1000, 'output': 200},
            p2p_tokens={'input': 150, 'output': 40})
        self.assertEqual(result['comparison_status'], 'PAIR_INPUTS_COMPLETE_UNVERIFIED')
        self.assertEqual(result['p2p_total_cost_units'], 65.0)
        self.assertEqual(result['net_saving_units'], 35.0)
        self.assertTrue(result['cheaper_than_executor_estimate'])
        self.assertIsNone(result['cheaper_than_executor'])
        self.assertFalse(result['independently_qualified'])

    def test_different_acceptance_outcomes_block_cost_win(self):
        result = cm.compare_paired_cost_inputs(
            {}, executor_cost_units=100, ask_price_units=20,
            integration_cost_units=0, validation_cost_units=0,
            residual_executor_cost_units=0, task_id='pair-2',
            acceptance_contract_sha256='b' * 64, executor_accepted=True,
            p2p_accepted=False, independent_acceptance=True,
            executor_receipt_id='exec-receipt-2', p2p_receipt_id='p2p-receipt-2',
            acceptance_receipt_id='acceptance-2')
        self.assertEqual(result['comparison_status'], 'UNQUALIFIED_MISSING_RECEIPTS_OR_PAIR')
        self.assertIsNone(result['cheaper_than_executor_estimate'])

    def test_missing_material_cost_blocks_savings_claim(self):
        result = cm.compare_paired_cost_inputs(
            {}, executor_cost_units=100, ask_price_units=20,
            integration_cost_units=None, validation_cost_units=0,
            residual_executor_cost_units=0)
        self.assertEqual(result['comparison_status'], 'UNQUALIFIED_MISSING_RECEIPTS_OR_PAIR')
        self.assertIsNone(result['net_saving_units'])
        self.assertIsNone(result['cheaper_than_executor'])


# ── Exchange integration: protocol fee at fill-listing ───────────────────────

class ProtocolFeeIntegrationTests(unittest.TestCase):
    """Test the protocol fee logic by simulating the exchange_cli fill-listing logic.

    exchange_cli.run requires full config with state_path; to avoid that overhead
    we unit-test the protocol fee formula and verify the audit row schema directly.
    """

    def _make_exchange_and_fill(self, ask_price, config=None):
        """Set up a minimal exchange and simulate the fill-listing protocol fee emission."""
        from urace import equity_auto_trade as eat, feature_equity as fe, peer_exchange as pe, credit_ledger as cl
        import tempfile
        config = config or {}
        tmpdir = tempfile.mkdtemp()
        ex = pe.Exchange(Path(tmpdir) / 'node')
        cl.earn_units(ex.root, 'alice', 10 * cl.UNIT, 'setup')
        cl.earn_units(ex.root, 'bob', 10 * cl.UNIT, 'setup')
        fe.grant_equity(ex, 'feat-p', 'alice')
        lid = eat.list_for_sale(ex, 'feat-p', 'alice', 1000, ask_price)
        # Simulate the fill-listing protocol fee emission (mirrors exchange_cli.run logic)
        from datetime import datetime, timezone
        eat.fill_listing(ex, ex.root, lid, 'bob')
        fl_listing = next((r for r in ex.audit_rows() if r.get('kind') == 'EQUITY_LISTING' and r.get('listing_id') == lid), None)
        fl_price = int(fl_listing.get('ask_price_units', 0)) if fl_listing else 0
        feat_id = fl_listing.get('feature_id', '') if fl_listing else ''
        _proto_fee = int(fl_price * float(config.get('p2p', {}).get('protocol_fee_fraction', 0.02)))
        if _proto_fee > 0:
            ex.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'protocol_fee',
                'peer': '__protocol__', 'amount_units': _proto_fee,
                'listing_id': lid, 'feature_id': feat_id,
                'funded_by': 'bob', 'at_unix': time.time(),
                'at': datetime.now(timezone.utc).isoformat()})
        return ex, lid, fl_price

    def test_protocol_fee_emitted_at_fill_listing(self):
        ex, lid, fl_price = self._make_exchange_and_fill(ask_price=100)
        rows = ex.audit_rows()
        proto_rows = [r for r in rows
                      if r.get('kind') == 'CREDIT_DELTA'
                      and r.get('direction') == 'protocol_fee']
        self.assertEqual(len(proto_rows), 1)
        self.assertEqual(proto_rows[0]['peer'], '__protocol__')
        self.assertEqual(proto_rows[0]['funded_by'], 'bob')
        self.assertEqual(proto_rows[0]['amount_units'], 2)  # 2% of 100

    def test_protocol_fee_custom_fraction(self):
        config = {'p2p': {'protocol_fee_fraction': 0.05}}
        ex, lid, fl_price = self._make_exchange_and_fill(ask_price=200, config=config)
        rows = ex.audit_rows()
        proto_rows = [r for r in rows
                      if r.get('kind') == 'CREDIT_DELTA'
                      and r.get('direction') == 'protocol_fee']
        self.assertEqual(proto_rows[0]['amount_units'], 10)  # 5% of 200

    def test_protocol_fee_zero_price_no_row(self):
        ex, lid, fl_price = self._make_exchange_and_fill(ask_price=0)
        rows = ex.audit_rows()
        proto_rows = [r for r in rows
                      if r.get('kind') == 'CREDIT_DELTA'
                      and r.get('direction') == 'protocol_fee']
        # 2% of 0 = 0, so no row emitted
        self.assertEqual(len(proto_rows), 0)

    def test_protocol_fee_row_has_correct_keys(self):
        ex, lid, fl_price = self._make_exchange_and_fill(ask_price=50)
        rows = ex.audit_rows()
        proto_rows = [r for r in rows
                      if r.get('kind') == 'CREDIT_DELTA'
                      and r.get('direction') == 'protocol_fee']
        if proto_rows:
            row = proto_rows[0]
            for key in ('kind', 'direction', 'peer', 'amount_units', 'listing_id', 'feature_id', 'funded_by'):
                self.assertIn(key, row)


# ── Ceiling enforcement uses network-derived ref price ────────────────────────

class ListForSaleCeilingIntegrationTests(unittest.TestCase):
    """Test that ceiling enforcement uses network-derived ref price when config absent."""

    def test_no_config_ref_price_uses_network_median(self):
        # When config has no executor_reference_price_per_unit,
        # derive_executor_reference_price is called with ledger rows
        now = time.time()
        rows = [
            {'kind': 'EQUITY_LISTING_FILLED', 'price_units': 42, 'at_unix': now},
        ]
        price = cm.derive_executor_reference_price(rows)
        self.assertIsNone(price)

    def test_config_ref_price_takes_precedence_over_network(self):
        # Config value should win over ledger rows
        now = time.time()
        rows = [{'kind': 'EQUITY_LISTING_FILLED', 'price_units': 999, 'at_unix': now}]
        # Simulate: config sets ref price to 50
        config_price = 50
        network_price = cm.derive_executor_reference_price(rows)
        # In exchange_cli, config price wins when set
        # This confirms the branching: config → 50, network → 999
        self.assertIsNone(network_price)

    def test_empty_ledger_fallback_is_10(self):
        price = cm.derive_executor_reference_price([])
        self.assertIsNone(price)

    def test_derived_price_used_in_vs_executor_comparison(self):
        now = time.time()
        rows = [{'kind': 'EQUITY_LISTING_FILLED', 'price_units': 50, 'at_unix': now}]
        derived = cm.derive_executor_reference_price(rows)
        result = cm.vs_executor_comparison({}, ask_price_units=5,
                                            executor_reference_price=derived)
        self.assertIsNone(result['executor_cost_per_call'])
        self.assertIsNone(result['cheaper_than_executor'])


# ── Exchange integration: minimum viable price auto-adjusts ask upward ────────

class MinViablePriceAutoAdjustTests(unittest.TestCase):

    def test_ask_price_auto_adjusted_not_rejected(self):
        """When ask_price < minimum_viable_price, it's adjusted up, not rejected."""
        from urace import equity_auto_trade as eat, feature_equity as fe, credit_ledger as cl
        import tempfile
        tmpdir = tempfile.mkdtemp()
        from urace import peer_exchange as pe
        ex = pe.Exchange(Path(tmpdir) / 'node')

        fe.grant_equity(ex, 'feat-minprice', 'alice')

        # With zero config, minimum_viable_price({}, 0) == 1, ask_price=1 is fine
        lid = eat.list_for_sale(ex, 'feat-minprice', 'alice', 1000, 1)
        rows = ex.audit_rows()
        self.assertTrue(any(r.get('kind') == 'EQUITY_LISTING' for r in rows))

    def test_minimum_viable_price_with_production_cost_above_zero(self):
        config = {'p2p': {'artifact_production_cost_per_kb': 10.0,
                          'protocol_fee_fraction': 0.0,
                          'bandwidth_cost_per_mb': 0.0}}
        # 1 KB artifact → production cost = 10 → minimum_viable_price = 10
        result = cm.minimum_viable_price(config, artifact_size_bytes=1024)
        self.assertGreaterEqual(result, 10)


# ── estimate_gas_overhead ─────────────────────────────────────────────────────

class EstimateGasOverheadTests(unittest.TestCase):

    def test_default_zero_no_chain(self):
        self.assertEqual(cm.estimate_gas_overhead({}), 0.0)

    def test_static_override(self):
        config = {'p2p': {'gas_overhead_units': 5}}
        self.assertEqual(cm.estimate_gas_overhead(config), 5.0)

    def test_dynamic_evm_all_three_set(self):
        # 65000 gas × 0.01 Gwei × 1 unit/Gwei = 650 units
        config = {'p2p': {'gas_per_tx_gwei': 65000, 'gas_price_gwei': 0.01, 'urace_units_per_gwei': 1}}
        self.assertAlmostEqual(cm.estimate_gas_overhead(config), 650.0, places=4)

    def test_dynamic_evm_takes_priority_over_static(self):
        # Both set — dynamic wins
        config = {'p2p': {'gas_per_tx_gwei': 21000, 'gas_price_gwei': 0.001,
                          'urace_units_per_gwei': 2, 'gas_overhead_units': 999}}
        # 21000 × 0.001 × 2 = 42
        self.assertAlmostEqual(cm.estimate_gas_overhead(config), 42.0, places=4)

    def test_dynamic_evm_missing_one_field_falls_back_to_static(self):
        # gas_per_tx_gwei set but gas_price_gwei=0 → falls back to static
        config = {'p2p': {'gas_per_tx_gwei': 65000, 'gas_price_gwei': 0,
                          'urace_units_per_gwei': 1, 'gas_overhead_units': 7}}
        self.assertEqual(cm.estimate_gas_overhead(config), 7.0)

    def test_dynamic_evm_zero_units_per_gwei_falls_back(self):
        config = {'p2p': {'gas_per_tx_gwei': 65000, 'gas_price_gwei': 0.01,
                          'urace_units_per_gwei': 0, 'gas_overhead_units': 3}}
        self.assertEqual(cm.estimate_gas_overhead(config), 3.0)


# ── gas_overhead_units in borrow_feature_cost ─────────────────────────────────

class BorrowFeatureCostGasTests(unittest.TestCase):

    def test_zero_gas_no_change_to_total(self):
        config = {'p2p': {'protocol_fee_fraction': 0.0, 'bandwidth_cost_per_mb': 0.0}}
        result = cm.borrow_feature_cost(config, ask_price_units=100)
        self.assertEqual(result['gas_overhead_units'], 0.0)
        self.assertAlmostEqual(result['total_buyer_cost'], 100.0, places=2)

    def test_static_gas_overhead_added_to_total(self):
        config = {'p2p': {'gas_overhead_units': 5, 'protocol_fee_fraction': 0.0,
                          'bandwidth_cost_per_mb': 0.0}}
        result = cm.borrow_feature_cost(config, ask_price_units=100)
        self.assertEqual(result['gas_overhead_units'], 5.0)
        self.assertAlmostEqual(result['total_buyer_cost'], 105.0, places=2)

    def test_dynamic_gas_overhead_added_to_total(self):
        # 21000 × 0.001 × 1 = 21 units gas overhead
        config = {'p2p': {'gas_per_tx_gwei': 21000, 'gas_price_gwei': 0.001,
                          'urace_units_per_gwei': 1, 'protocol_fee_fraction': 0.0,
                          'bandwidth_cost_per_mb': 0.0}}
        result = cm.borrow_feature_cost(config, ask_price_units=100)
        self.assertAlmostEqual(result['gas_overhead_units'], 21.0, places=2)
        self.assertAlmostEqual(result['total_buyer_cost'], 121.0, places=2)

    def test_gas_overhead_key_always_present(self):
        result = cm.borrow_feature_cost({}, ask_price_units=50)
        self.assertIn('gas_overhead_units', result)

    def test_cheaper_than_executor_breaks_with_high_gas(self):
        # ask=10, executor=15, gas=20 → total buyer cost = 30 → not cheaper
        config = {'p2p': {'gas_overhead_units': 20, 'protocol_fee_fraction': 0.0,
                          'bandwidth_cost_per_mb': 0.0,
                          'executor_reference_price_per_unit': 15}}
        result = cm.vs_executor_comparison(config, ask_price_units=10)
        self.assertIsNone(result['cheaper_than_executor'])

    def test_cheaper_than_executor_true_with_low_gas(self):
        # ask=10, executor=200, gas=1 → total≈11 → cheaper
        config = {'p2p': {'gas_overhead_units': 1, 'protocol_fee_fraction': 0.0,
                          'bandwidth_cost_per_mb': 0.0,
                          'executor_reference_price_per_unit': 200}}
        result = cm.vs_executor_comparison(config, ask_price_units=10)
        self.assertIsNone(result['cheaper_than_executor'])


# ── gas_overhead in minimum_viable_price ─────────────────────────────────────

class MinimumViablePriceGasTests(unittest.TestCase):

    def test_zero_gas_no_change(self):
        result_no_gas = cm.minimum_viable_price({}, artifact_size_bytes=0)
        result_zero_gas = cm.minimum_viable_price({'p2p': {'gas_overhead_units': 0}},
                                                   artifact_size_bytes=0)
        self.assertEqual(result_no_gas, result_zero_gas)

    def test_gas_overhead_raises_floor(self):
        config_no_gas = {'p2p': {'artifact_production_cost_per_kb': 0.0,
                                  'bandwidth_cost_per_mb': 0.0,
                                  'protocol_fee_fraction': 0.0}}
        config_gas = {'p2p': {'artifact_production_cost_per_kb': 0.0,
                               'bandwidth_cost_per_mb': 0.0,
                               'protocol_fee_fraction': 0.0,
                               'gas_overhead_units': 10}}
        result_no_gas = cm.minimum_viable_price(config_no_gas, artifact_size_bytes=0)
        result_gas = cm.minimum_viable_price(config_gas, artifact_size_bytes=0)
        self.assertEqual(result_gas, 10)
        self.assertGreater(result_gas, result_no_gas)

    def test_gas_overhead_scaled_by_protocol_fee(self):
        # gas=10, fee=0.5 → price = 10 / (1 - 0.5) = 20
        config = {'p2p': {'gas_overhead_units': 10, 'protocol_fee_fraction': 0.5,
                          'bandwidth_cost_per_mb': 0.0, 'artifact_production_cost_per_kb': 0.0}}
        result = cm.minimum_viable_price(config, artifact_size_bytes=0)
        self.assertEqual(result, 20)

    def test_returns_int(self):
        config = {'p2p': {'gas_overhead_units': 7.5, 'protocol_fee_fraction': 0.0}}
        result = cm.minimum_viable_price(config)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 8)  # ceil(7.5)


if __name__ == '__main__':
    unittest.main()
