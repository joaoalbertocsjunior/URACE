"""Tests for cartel_guard.py — multi-node chunk concentration detection."""
import time
import unittest


class MockExchange:
    def __init__(self):
        self._rows = []

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)


def _replica_row(feature_id, peer_id, at_unix=None, chunk_indices=None):
    row = {
        'kind': 'BUNDLE_REPLICA_REGISTERED',
        'feature_id': feature_id,
        'replica_peer_id': peer_id,
        'at_unix': at_unix or time.time(),
    }
    if chunk_indices is not None:
        row['chunk_indices'] = chunk_indices
    return row


class TestCheckChunkConcentration(unittest.TestCase):
    def setUp(self):
        from urace import cartel_guard as cg
        self.cg = cg

    def test_no_rows_returns_not_flagged(self):
        result = self.cg.check_chunk_concentration('feat-1', [], n_total=6)
        self.assertFalse(result['flagged'])

    def test_single_peer_all_chunks_no_co_registered_peer(self):
        # single peer holding all chunks — no cluster with another peer → no cartel
        rows = [_replica_row('f', 'alice')]
        result = self.cg.check_chunk_concentration('f', rows, n_total=6, threshold=0.80)
        # Single-node cluster holding 6/6 = 1.0 — that's above threshold, flagged
        self.assertTrue(result['flagged'])
        self.assertAlmostEqual(result['concentration'], 1.0)

    def test_below_threshold_passes(self):
        now = time.time()
        rows = [
            _replica_row('f', 'alice', at_unix=now, chunk_indices='0,1,2'),
            _replica_row('f', 'bob', at_unix=now + 10, chunk_indices='3,4'),
        ]
        # 5/6 = 0.833 > 0.80 → flagged
        result = self.cg.check_chunk_concentration('f', rows, n_total=6, threshold=0.90)
        # 5/6 ~ 0.833, below 0.90
        self.assertFalse(result['flagged'])

    def test_above_threshold_flagged(self):
        now = time.time()
        rows = [
            _replica_row('f', 'alice', at_unix=now, chunk_indices='0,1,2'),
            _replica_row('f', 'bob', at_unix=now + 10, chunk_indices='3,4,5'),
        ]
        result = self.cg.check_chunk_concentration('f', rows, n_total=6, threshold=0.80)
        self.assertTrue(result['flagged'])
        self.assertAlmostEqual(result['concentration'], 1.0)

    def test_co_registration_window_groups_peers(self):
        now = time.time()
        # alice and bob register within 300s of each other → same cluster
        rows = [
            _replica_row('f', 'alice', at_unix=now, chunk_indices='0,1,2'),
            _replica_row('f', 'bob', at_unix=now + 200, chunk_indices='3,4'),
        ]
        result = self.cg.check_chunk_concentration(
            'f', rows, n_total=6, threshold=0.70,
            registration_window_secs=300,
        )
        # union = {0,1,2,3,4} = 5/6 ~ 0.833 > 0.70
        self.assertTrue(result['flagged'])
        self.assertIn('alice', result['cluster'])
        self.assertIn('bob', result['cluster'])

    def test_outside_window_not_clustered(self):
        now = time.time()
        # alice and charlie register 400s apart (> 300s window) → different clusters
        rows = [
            _replica_row('f', 'alice', at_unix=now, chunk_indices='0,1,2'),
            _replica_row('f', 'charlie', at_unix=now + 400, chunk_indices='3,4,5'),
        ]
        result = self.cg.check_chunk_concentration(
            'f', rows, n_total=6, threshold=0.80,
            registration_window_secs=300,
        )
        # Each cluster has 3/6 = 0.5 → not flagged
        self.assertFalse(result['flagged'])

    def test_different_feature_id_ignored(self):
        now = time.time()
        rows = [
            _replica_row('feat-other', 'alice', at_unix=now, chunk_indices='0,1,2,3,4,5'),
        ]
        result = self.cg.check_chunk_concentration('feat-target', rows, n_total=6)
        self.assertFalse(result['flagged'])

    def test_peer_without_chunk_indices_holds_all(self):
        now = time.time()
        rows = [_replica_row('f', 'alice', at_unix=now)]
        result = self.cg.check_chunk_concentration('f', rows, n_total=6, threshold=0.80)
        # alice holds all 6 → concentration = 1.0 > 0.80
        self.assertTrue(result['flagged'])
        self.assertAlmostEqual(result['concentration'], 1.0)

    def test_flagged_result_includes_feature_id(self):
        now = time.time()
        rows = [
            _replica_row('feat-x', 'a', at_unix=now, chunk_indices='0,1,2'),
            _replica_row('feat-x', 'b', at_unix=now + 10, chunk_indices='3,4,5'),
        ]
        result = self.cg.check_chunk_concentration('feat-x', rows, n_total=6, threshold=0.80)
        self.assertTrue(result['flagged'])
        self.assertEqual(result['feature_id'], 'feat-x')


class TestApplyChunkConcentrationPenalty(unittest.TestCase):
    def setUp(self):
        from urace import cartel_guard as cg
        self.cg = cg
        self.ex = MockExchange()
        self.now = time.time()

    def _add_replicas(self, feature_id, peers_chunks, base_time=None):
        t = base_time or self.now
        for i, (peer, chunks) in enumerate(peers_chunks):
            self.ex.append_audit_row(_replica_row(
                feature_id, peer, at_unix=t + i * 10,
                chunk_indices=','.join(str(c) for c in chunks)
            ))

    def test_penalty_applied_when_flagged(self):
        self._add_replicas('f', [('alice', [0, 1, 2]), ('bob', [3, 4, 5])])
        result = self.cg.apply_chunk_concentration_penalty(self.ex, 'f', n_total=6, threshold=0.80)
        self.assertTrue(result['applied'])
        self.assertIn('alice', result['cluster'])
        self.assertIn('bob', result['cluster'])
        kinds = [r['kind'] for r in self.ex.audit_rows()]
        self.assertIn('CARTEL_CHUNK_CONCENTRATION', kinds)
        credit_penalties = [r for r in self.ex.audit_rows() if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'cartel_chunk_penalty']
        self.assertGreater(len(credit_penalties), 0)

    def test_not_applied_when_not_flagged(self):
        self._add_replicas('f', [('alice', [0, 1, 2])])
        # 3/6 = 0.5 < 0.80 (wait — without bob, cluster is just alice)
        # alice alone = 3/6=0.5 < 0.80 → not flagged
        result = self.cg.apply_chunk_concentration_penalty(self.ex, 'f', n_total=6, threshold=0.80)
        self.assertFalse(result['applied'])

    def test_idempotent_within_24h(self):
        self._add_replicas('f', [('alice', [0, 1, 2]), ('bob', [3, 4, 5])])
        r1 = self.cg.apply_chunk_concentration_penalty(self.ex, 'f', n_total=6, threshold=0.80)
        self.assertTrue(r1['applied'])
        r2 = self.cg.apply_chunk_concentration_penalty(self.ex, 'f', n_total=6, threshold=0.80)
        self.assertFalse(r2['applied'])  # idempotent — not reapplied within 24h


class TestRegisterReplicaGuard(unittest.TestCase):
    def setUp(self):
        from urace import cartel_guard as cg
        self.cg = cg
        self.ex = MockExchange()
        self.now = time.time()

    def test_guard_allows_safe_registration(self):
        # alice holds chunks 0,1,2 (3/6 = 0.5) — adding bob with 3,4 gives 5/6=0.833
        # but threshold is 0.80 → should raise
        self.ex.append_audit_row(_replica_row('f', 'alice', at_unix=self.now, chunk_indices='0,1,2'))
        # bob adds 3,4 → cluster (alice+bob) = 0.833 > 0.80 → raises
        with self.assertRaises(ValueError):
            self.cg.register_replica_guard(
                self.ex, 'f', 'bob', n_total=6, threshold=0.80,
                registration_window_secs=300, chunk_indices='3,4'
            )

    def test_guard_allows_when_below_threshold(self):
        # alice has 0,1,2 (0.5), bob about to add just 3 (1/6)
        # cluster union = 4/6 ~ 0.667 < 0.80 → no raise
        self.ex.append_audit_row(_replica_row('f', 'alice', at_unix=self.now, chunk_indices='0,1,2'))
        # Should not raise
        self.cg.register_replica_guard(
            self.ex, 'f', 'bob', n_total=6, threshold=0.80,
            registration_window_secs=300, chunk_indices='3'
        )

    def test_guard_no_existing_rows_allows(self):
        # No existing replicas, alice registers with only 3 chunks → 0.5 < 0.80 → no raise
        self.cg.register_replica_guard(
            self.ex, 'f', 'alice', n_total=6, threshold=0.80,
            chunk_indices='0,1,2'
        )


if __name__ == '__main__':
    unittest.main()
