import unittest, time, tempfile
from pathlib import Path
from urace import delivery_graph as dg, peer_exchange as pe


def _make_exchange():
    tmp = tempfile.mkdtemp()
    e = pe.Exchange(Path(tmp) / 'node')
    e.configure(enabled=True, network=False)
    e.feature('feat', [])
    return e


def _register(e, feature_id, replica_peer_id, chunk_indices=None):
    row = {'kind': 'BUNDLE_REPLICA_REGISTERED', 'feature_id': feature_id,
           'replica_peer_id': replica_peer_id, 'at_unix': time.time()}
    if chunk_indices is not None:
        row['chunk_indices'] = chunk_indices
    e.append_audit_row(row)


class DeliveryWeightsTests(unittest.TestCase):

    def test_no_replicas_returns_empty(self):
        e = _make_exchange()
        result = dg.delivery_weights('feat-x', e.audit_rows(), 'creator')
        self.assertEqual(result, {})

    def test_single_replica_full_coverage_weight_one(self):
        e = _make_exchange()
        _register(e, 'feat-x', 'replica-A')  # no chunk_indices → full coverage
        result = dg.delivery_weights('feat-x', e.audit_rows(), 'creator', n_total=6)
        self.assertAlmostEqual(result.get('replica-A', 0), 1.0, places=5)

    def test_two_replicas_equal_coverage_equal_weights(self):
        e = _make_exchange()
        _register(e, 'feat-x', 'A', chunk_indices=[0, 1, 2])
        _register(e, 'feat-x', 'B', chunk_indices=[3, 4, 5])
        result = dg.delivery_weights('feat-x', e.audit_rows(), 'creator', n_total=6)
        self.assertAlmostEqual(result.get('A', 0), 0.5, places=3)
        self.assertAlmostEqual(result.get('B', 0), 0.5, places=3)

    def test_unequal_coverage_proportional_weights(self):
        e = _make_exchange()
        _register(e, 'feat-x', 'A', chunk_indices=[0, 1, 2, 3])  # 4/6
        _register(e, 'feat-x', 'B', chunk_indices=[4, 5])         # 2/6
        result = dg.delivery_weights('feat-x', e.audit_rows(), 'creator', n_total=6)
        self.assertGreater(result.get('A', 0), result.get('B', 0))
        self.assertAlmostEqual(result['A'] / result['B'], 2.0, places=2)

    def test_creator_excluded_from_weights(self):
        e = _make_exchange()
        _register(e, 'feat-x', 'creator')   # creator as replica — excluded
        _register(e, 'feat-x', 'replica-B')
        result = dg.delivery_weights('feat-x', e.audit_rows(), 'creator', n_total=6)
        self.assertNotIn('creator', result)
        self.assertIn('replica-B', result)

    def test_weights_sum_to_one(self):
        e = _make_exchange()
        for i, pid in enumerate(['A', 'B', 'C']):
            _register(e, 'feat-x', pid, chunk_indices=[i*2, i*2+1])
        result = dg.delivery_weights('feat-x', e.audit_rows(), 'orig', n_total=6)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=5)


class DeliveryFeeAmountsTests(unittest.TestCase):

    def test_no_replicas_no_fee(self):
        e = _make_exchange()
        result = dg.delivery_fee_amounts('feat-x', e.audit_rows(), 'creator', 100)
        self.assertEqual(result, {})

    def test_single_replica_gets_full_pool(self):
        e = _make_exchange()
        _register(e, 'feat-x', 'replica')
        result = dg.delivery_fee_amounts('feat-x', e.audit_rows(), 'creator', 100, 0.10, 6)
        self.assertEqual(sum(result.values()), 10)  # 10% of 100
        self.assertEqual(result.get('replica'), 10)

    def test_two_replicas_equal_split(self):
        e = _make_exchange()
        _register(e, 'feat-x', 'A', chunk_indices=[0, 1, 2])
        _register(e, 'feat-x', 'B', chunk_indices=[3, 4, 5])
        result = dg.delivery_fee_amounts('feat-x', e.audit_rows(), 'creator', 100, 0.10, 6)
        self.assertEqual(sum(result.values()), 10)
        self.assertEqual(result.get('A'), 5)
        self.assertEqual(result.get('B'), 5)

    def test_proportional_split_unequal_coverage(self):
        e = _make_exchange()
        _register(e, 'feat-x', 'big', chunk_indices=[0, 1, 2, 3])  # 4/6 coverage
        _register(e, 'feat-x', 'small', chunk_indices=[4, 5])       # 2/6 coverage
        result = dg.delivery_fee_amounts('feat-x', e.audit_rows(), 'creator', 100, 0.10, 6)
        total = sum(result.values())
        self.assertEqual(total, 10)
        self.assertGreater(result.get('big', 0), result.get('small', 0))

    def test_zero_price_returns_empty(self):
        e = _make_exchange()
        _register(e, 'feat-x', 'A')
        self.assertEqual(dg.delivery_fee_amounts('feat-x', e.audit_rows(), 'creator', 0), {})

    def test_multiple_replicas_full_coverage(self):
        e = _make_exchange()
        for pid in ['A', 'B', 'C']:
            _register(e, 'feat-x', pid)  # all full coverage
        result = dg.delivery_fee_amounts('feat-x', e.audit_rows(), 'creator', 300, 0.10, 6)
        self.assertEqual(sum(result.values()), 30)
        # Each gets roughly equal share
        for pid in ['A', 'B', 'C']:
            self.assertGreater(result.get(pid, 0), 0)


if __name__ == '__main__':
    unittest.main()
