import unittest
from urace import cost_model as cm

_CFG_DEFAULT = {}
_CFG_CUSTOM = {'p2p': {'mint_stake_units': 5, 'expected_lifetime_borrows': 10, 'executor_reference_price_per_unit': 10}}


class MintFeatureCostTests(unittest.TestCase):

    def test_returns_expected_keys(self):
        result = cm.mint_feature_cost(_CFG_DEFAULT)
        for key in ('schema', 'operation', 'mint_stake', 'p2p_delivery_cost', 'total_units',
                    'erasure_overhead_fraction', 'n_replicas', 'artifact_size_bytes', 'consensus_cost'):
            self.assertIn(key, result)

    def test_total_equals_stake_plus_p2p(self):
        result = cm.mint_feature_cost(_CFG_DEFAULT, artifact_size_bytes=1_000_000)
        self.assertAlmostEqual(result['total_units'],
                               result['mint_stake'] + result['p2p_delivery_cost'], places=3)

    def test_zero_artifact_size_zero_p2p_cost(self):
        result = cm.mint_feature_cost(_CFG_DEFAULT, artifact_size_bytes=0)
        self.assertEqual(result['p2p_delivery_cost'], 0)

    def test_schema_correct(self):
        self.assertEqual(cm.mint_feature_cost(_CFG_DEFAULT)['schema'], 'urace-cost-model-v1')

    def test_config_override_mint_stake(self):
        result = cm.mint_feature_cost(_CFG_CUSTOM)
        self.assertEqual(result['mint_stake'], 5)


class BorrowFeatureCostTests(unittest.TestCase):

    def test_delivery_fee_when_replica_delivery(self):
        result = cm.borrow_feature_cost(_CFG_DEFAULT, ask_price_units=100, has_replica_delivery=True)
        self.assertEqual(result['delivery_fee'], 10)  # 10% of 100

    def test_delivery_fee_zero_when_no_replica(self):
        result = cm.borrow_feature_cost(_CFG_DEFAULT, ask_price_units=100, has_replica_delivery=False)
        self.assertEqual(result['delivery_fee'], 0)

    def test_composition_referral_pool_20pct_of_net(self):
        result = cm.borrow_feature_cost(_CFG_DEFAULT, ask_price_units=100, has_replica_delivery=False)
        # net = 100 - 0 delivery = 100; referral = 20% of 100 = 20
        self.assertEqual(result['composition_referral_pool'], 20)

    def test_schema_correct(self):
        result = cm.borrow_feature_cost(_CFG_DEFAULT, ask_price_units=50)
        self.assertEqual(result['schema'], 'urace-cost-model-v1')

    def test_zero_artifact_zero_p2p(self):
        result = cm.borrow_feature_cost(_CFG_DEFAULT, ask_price_units=10, artifact_size_bytes=0)
        self.assertEqual(result['p2p_delivery_cost'], 0)


class VsExecutorComparisonTests(unittest.TestCase):

    def test_cheaper_than_executor_true_when_ask_low(self):
        # executor_reference_price=1, ask=0, amortized_mint=3/20=0.15 → saving = 1-(0+0.15) > 0
        result = cm.vs_executor_comparison(_CFG_DEFAULT, ask_price_units=0, executor_calls_saved=1)
        self.assertIsNone(result['cheaper_than_executor'])
        self.assertEqual(result['comparison_status'], 'UNQUALIFIED')

    def test_cheaper_than_executor_false_when_ask_high(self):
        # executor_reference_price=1, ask=10 → saving = 1-(10+0.15) < 0
        result = cm.vs_executor_comparison(_CFG_DEFAULT, ask_price_units=10, executor_calls_saved=1)
        self.assertFalse(result['cheaper_than_executor'])

    def test_multiple_executor_calls_scales(self):
        result = cm.vs_executor_comparison(_CFG_DEFAULT, ask_price_units=0, executor_calls_saved=5)
        self.assertIsNone(result['executor_total'])

    def test_schema_correct(self):
        result = cm.vs_executor_comparison(_CFG_DEFAULT, ask_price_units=0)
        self.assertEqual(result['schema'], 'urace-cost-model-v1')


class TotalOperationCostTests(unittest.TestCase):

    def test_unknown_operation_returns_error_key(self):
        result = cm.total_operation_cost('nonexistent_op', _CFG_DEFAULT)
        self.assertIn('error', result)

    def test_list_for_sale_listing_cost_zero(self):
        result = cm.list_for_sale_cost(_CFG_DEFAULT)
        self.assertEqual(result['listing_cost'], 0)

    def test_challenge_cost_max_bounty(self):
        result = cm.challenge_cost(_CFG_DEFAULT)
        # challenger_stake=2 (default), mint_stake=3 → max_bounty=5
        self.assertEqual(result['max_bounty'], result['challenger_stake'] + 3)

    def test_amortized_mint_cost(self):
        val = cm.amortized_mint_cost_per_borrow(_CFG_DEFAULT)
        # 3 / 20 = 0.15
        self.assertAlmostEqual(val, 0.15, places=5)

    def test_amortized_mint_cost_custom_config(self):
        val = cm.amortized_mint_cost_per_borrow(_CFG_CUSTOM)
        # 5 / 10 = 0.5
        self.assertAlmostEqual(val, 0.5, places=5)

    def test_total_operation_cost_mint_via_unified(self):
        result = cm.total_operation_cost('mint_feature', _CFG_DEFAULT, artifact_size_bytes=0)
        self.assertEqual(result['schema'], 'urace-cost-model-v1')
        self.assertEqual(result['operation'], 'mint_feature')


class CheaperThanExecutorTests(unittest.TestCase):

    def test_cheaper_when_ask_below_executor(self):
        config = {'p2p': {'executor_reference_price_per_unit': 10}}
        result = cm.vs_executor_comparison(config, ask_price_units=5)
        self.assertIsNone(result['cheaper_than_executor'])
        self.assertEqual(result['comparison_status'], 'ESTIMATE_ONLY')

    def test_not_cheaper_when_ask_equals_executor(self):
        config = {'p2p': {'executor_reference_price_per_unit': 10}}
        result = cm.vs_executor_comparison(config, ask_price_units=10)
        self.assertIsNone(result['cheaper_than_executor'])

    def test_saving_scales_with_executor_calls(self):
        config = {'p2p': {'executor_reference_price_per_unit': 10}}
        r1 = cm.vs_executor_comparison(config, 5, executor_calls_saved=1)
        r2 = cm.vs_executor_comparison(config, 5, executor_calls_saved=5)
        self.assertGreater(r2['net_saving'], r1['net_saving'])

    def test_amortized_cost_reduces_saving(self):
        config = {'p2p': {'executor_reference_price_per_unit': 10,
                          'mint_stake_units': 3, 'expected_lifetime_borrows': 1}}
        result = cm.vs_executor_comparison(config, ask_price_units=8)
        # 10 executor - (8 borrow + 3 stake) = -1: not cheaper when stake amortized over 1 borrow
        self.assertFalse(result['cheaper_than_executor'])


if __name__ == '__main__':
    unittest.main()
