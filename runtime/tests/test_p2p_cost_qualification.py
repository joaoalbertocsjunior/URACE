"""Tests for p2p_cost_qualification: simulate warning, failure-path coverage,
peer_failure_rate Wilson CI, reputation persistence, select_peers_by_reputation."""
import json
import tempfile
import time
import unittest

from urace import p2p_cost_qualification as pq


class MockExchange:
    def __init__(self):
        self._rows = []

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)

    def event(self, kind, **fields):
        self._rows.append({'kind': kind, **fields})

    def record(self, kind, fields):
        self._rows.append({'kind': kind, **fields})


def _fill_bootstrap(ex, n=30):
    for i in range(n):
        pq.record_qualification_receipt(ex, f'peer-a{i}', f'peer-b{i}', True)


# ── bootstrap_complete ────────────────────────────────────────────────────────

class BootstrapCompleteTests(unittest.TestCase):
    def test_false_below_threshold(self):
        ex = MockExchange()
        _fill_bootstrap(ex, 29)
        self.assertFalse(pq.bootstrap_complete(ex))

    def test_true_at_threshold(self):
        ex = MockExchange()
        _fill_bootstrap(ex, 30)
        self.assertTrue(pq.bootstrap_complete(ex))

    def test_ignores_non_qualification_rows(self):
        ex = MockExchange()
        for i in range(30):
            ex.append_audit_row({'kind': 'OTHER_ROW', 'pair_hash': f'hash{i}'})
        self.assertFalse(pq.bootstrap_complete(ex))

    def test_handles_audit_exception(self):
        class BrokenExchange:
            def audit_rows(self):
                raise RuntimeError("broken")
        self.assertFalse(pq.bootstrap_complete(BrokenExchange()))


# ── run_qualification_round simulate=True ────────────────────────────────────

class SimulateModeTests(unittest.TestCase):
    def test_simulate_logs_warning(self):
        ex = MockExchange()
        with self.assertLogs('urace.p2p_cost_qualification', level='WARNING') as cm:
            pq.run_qualification_round(ex, [('a', 'b')], simulate=True)
        self.assertTrue(any('simulate mode' in msg for msg in cm.output))

    def test_simulate_marks_all_completed(self):
        ex = MockExchange()
        pairs = [(f'a{i}', f'b{i}') for i in range(5)]
        result = pq.run_qualification_round(ex, pairs, simulate=True)
        self.assertEqual(result['completed'], 5)
        self.assertEqual(result['rounds'], 5)


# ── run_qualification_round simulate=False ───────────────────────────────────

class LiveModePeerFailureTests(unittest.TestCase):
    def test_failed_exchange_marks_incomplete(self):
        """When peer_exchange.request raises, pair is recorded completed=False."""
        import unittest.mock as mock
        ex = MockExchange()
        with mock.patch('urace.peer_exchange.request', side_effect=ConnectionError('timeout')):
            result = pq.run_qualification_round(ex, [('p1', 'p2')], simulate=False)
        self.assertEqual(result['completed'], 0)
        self.assertEqual(result['rounds'], 1)
        rows = [r for r in ex.audit_rows() if r.get('kind') == 'QUALIFICATION_RECEIPT']
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]['completed'])

    def test_successful_exchange_marks_complete(self):
        import unittest.mock as mock
        ex = MockExchange()
        with mock.patch('urace.peer_exchange.request', return_value={'status': 'ok'}):
            result = pq.run_qualification_round(ex, [('p1', 'p2')], simulate=False)
        self.assertEqual(result['completed'], 1)
        rows = [r for r in ex.audit_rows() if r.get('kind') == 'QUALIFICATION_RECEIPT']
        self.assertTrue(rows[0]['completed'])


# ── qualification_statistics ─────────────────────────────────────────────────

class QualificationStatisticsTests(unittest.TestCase):
    def test_empty_exchange(self):
        ex = MockExchange()
        stats = pq.qualification_statistics(ex)
        self.assertEqual(stats['total_pairs'], 0)
        self.assertEqual(stats['delivery_rate'], 0.0)
        self.assertFalse(stats['bootstrap_complete'])

    def test_all_completed(self):
        ex = MockExchange()
        _fill_bootstrap(ex, 30)
        stats = pq.qualification_statistics(ex)
        self.assertEqual(stats['total_pairs'], 30)
        self.assertEqual(stats['completed_pairs'], 30)
        self.assertAlmostEqual(stats['delivery_rate'], 1.0)
        self.assertGreater(stats['wilson_lower_bound'], 0.9)
        self.assertTrue(stats['bootstrap_complete'])

    def test_partial_completion(self):
        ex = MockExchange()
        for i in range(10):
            pq.record_qualification_receipt(ex, f'a{i}', f'b{i}', i < 7)
        stats = pq.qualification_statistics(ex)
        self.assertEqual(stats['total_pairs'], 10)
        self.assertEqual(stats['completed_pairs'], 7)
        self.assertAlmostEqual(stats['delivery_rate'], 0.7, places=5)


# ── peer_failure_rate ─────────────────────────────────────────────────────────

class PeerFailureRateTests(unittest.TestCase):
    def test_no_receipts_returns_zero(self):
        ex = MockExchange()
        self.assertEqual(pq.peer_failure_rate(ex, 'nobody'), 0.0)

    def test_zero_failure_rate_for_perfect_peer(self):
        ex = MockExchange()
        for i in range(5):
            ex.append_audit_row({
                'kind': 'QUALIFICATION_RECEIPT',
                'peer_a_id': 'alice',
                'peer_b_id': f'bob{i}',
                'delivery_rate': 1.0,
                'at_unix': time.time(),
            })
        rate = pq.peer_failure_rate(ex, 'alice')
        self.assertEqual(rate, 0.0)

    def test_nonzero_failure_rate_for_bad_peer(self):
        ex = MockExchange()
        for i in range(10):
            ex.append_audit_row({
                'kind': 'QUALIFICATION_RECEIPT',
                'peer_a_id': 'mallory',
                'peer_b_id': f'x{i}',
                'delivery_rate': 0.0,
                'at_unix': time.time(),
            })
        rate = pq.peer_failure_rate(ex, 'mallory')
        self.assertGreater(rate, 0.0)

    def test_result_bounded_zero_to_one(self):
        ex = MockExchange()
        for i in range(5):
            ex.append_audit_row({
                'kind': 'QUALIFICATION_RECEIPT',
                'peer_a_id': 'peer',
                'peer_b_id': f'x{i}',
                'delivery_rate': 0.5,
                'at_unix': time.time(),
            })
        rate = pq.peer_failure_rate(ex, 'peer')
        self.assertGreaterEqual(rate, 0.0)
        self.assertLessEqual(rate, 1.0)


# ── select_peers_by_reputation ───────────────────────────────────────────────

class SelectPeersByReputationTests(unittest.TestCase):
    def test_returns_top_n(self):
        ex = MockExchange()
        candidates = [f'peer{i}' for i in range(20)]
        result = pq.select_peers_by_reputation(ex, candidates, top_n=5)
        self.assertEqual(len(result), 5)

    def test_sorted_ascending_failure(self):
        ex = MockExchange()
        for i in range(5):
            ex.append_audit_row({
                'kind': 'QUALIFICATION_RECEIPT',
                'peer_a_id': 'bad',
                'peer_b_id': f'x{i}',
                'delivery_rate': 0.0,
                'at_unix': time.time(),
            })
        for i in range(5):
            ex.append_audit_row({
                'kind': 'QUALIFICATION_RECEIPT',
                'peer_a_id': 'good',
                'peer_b_id': f'y{i}',
                'delivery_rate': 1.0,
                'at_unix': time.time(),
            })
        result = pq.select_peers_by_reputation(ex, ['bad', 'good'], top_n=2)
        self.assertEqual(result[0], 'good')
        self.assertEqual(result[1], 'bad')


# ── save_reputation / load_reputation ────────────────────────────────────────

class ReputationPersistenceTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        ex = MockExchange()
        pq.record_qualification_receipt(ex, 'a', 'b', True)
        pq.record_qualification_receipt(ex, 'c', 'd', False)

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            path = f.name

        pq.save_reputation(ex, reputation_file=path)

        ex2 = MockExchange()
        pq.load_reputation(ex2, reputation_file=path)

        rows = [r for r in ex2.audit_rows() if r.get('kind') == 'QUALIFICATION_RECEIPT']
        self.assertEqual(len(rows), 2)

    def test_load_missing_file_is_noop(self):
        ex = MockExchange()
        pq.load_reputation(ex, reputation_file='/nonexistent/path/rep.jsonl')
        self.assertEqual(ex.audit_rows(), [])

    def test_load_deduplicates(self):
        ex = MockExchange()
        pq.record_qualification_receipt(ex, 'a', 'b', True)

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            path = f.name

        pq.save_reputation(ex, reputation_file=path)
        pq.load_reputation(ex, reputation_file=path)

        rows = [r for r in ex.audit_rows() if r.get('kind') == 'QUALIFICATION_RECEIPT']
        self.assertEqual(len(rows), 1)


if __name__ == '__main__':
    unittest.main()
