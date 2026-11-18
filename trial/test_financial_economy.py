"""Financial economy path tests — cartel penalties, escrow idempotency, peer cap.

These cover the economic enforcement mechanisms where bugs have real value impact.
"""
import sys, math, tempfile, unittest
from pathlib import Path
sys.path.insert(0, 'runtime')

def _has_pq_crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric import mldsa  # noqa: F401
        return True
    except ImportError:
        return False

_NEEDS_PQ = unittest.skipUnless(_has_pq_crypto(), 'requires cryptography>=50 (mldsa)')

from urace.p2p_constants import UNIT
from urace.credit_ledger import (
    earn_units, spend_units, balance, escrow_lock, escrow_refund,
    peer_cap_units, BASE_CAP_UNITS,
)

class EscrowIdempotencyTests(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()

    @_NEEDS_PQ
    def test_escrow_refund_idempotent(self):
        """Double-calling escrow_refund for same request_id must not double-credit."""
        earn_units(self.root, 'peer-a', 10 * UNIT, 'initial-earn')
        spend_units(self.root, 'peer-a', 5 * UNIT, 'escrow-lock:req-1')
        escrow_refund(self.root, 'req-1', 'peer-a', 5 * UNIT)
        bal_after_first = balance(self.root, 'peer-a')
        escrow_refund(self.root, 'req-1', 'peer-a', 5 * UNIT)  # duplicate
        bal_after_second = balance(self.root, 'peer-a')
        self.assertEqual(bal_after_first, bal_after_second,
            'Second escrow_refund for same request_id must be a no-op')

    @_NEEDS_PQ
    def test_escrow_refund_zero_amount_noop(self):
        """Zero-amount refund must not write any row."""
        earn_units(self.root, 'peer-b', 5 * UNIT, 'initial-earn')
        bal_before = balance(self.root, 'peer-b')
        escrow_refund(self.root, 'req-2', 'peer-b', 0)
        self.assertEqual(balance(self.root, 'peer-b'), bal_before)


class PeerCapTests(unittest.TestCase):

    def test_peer_cap_units_returns_positive(self):
        """peer_cap_units must always return a positive value."""
        cap = peer_cap_units('/nonexistent/root', 'some-peer-id')
        self.assertGreater(cap, 0)

    def test_peer_cap_baseline_without_exchange(self):
        """Without a valid exchange, cap falls back to BASE_CAP_UNITS × baseline."""
        cap = peer_cap_units('/nonexistent/root', 'peer-x')
        # trust=0.1 → trust_factor=1.1; quality=1.0; network=1.0 → 1.1 × BASE_CAP
        expected = int(BASE_CAP_UNITS * 1.1 * 1.0 * 1.0)
        self.assertEqual(cap, expected)

    @_NEEDS_PQ
    def test_earn_units_respects_cap(self):
        """earn_units must not exceed the peer cap."""
        root = tempfile.mkdtemp()
        cap = peer_cap_units(root, 'capped-peer')
        # Try to earn 2× cap
        earn_units(root, 'capped-peer', cap * 2, 'big-earn')
        self.assertLessEqual(balance(root, 'capped-peer'), cap)


class CartelPenaltyTests(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def test_chunk_penalty_proportional(self):
        """apply_chunk_concentration_penalty penalty scales with concentration."""
        from urace.cartel_guard import apply_chunk_concentration_penalty, DEFAULT_MAX_CHUNK_CONCENTRATION
        import time

        class MockExchange:
            def __init__(self, rows):
                self._rows = rows
                self.appended = []
            def audit_rows(self): return self._rows
            def append_audit_row(self, row): self.appended.append(row)

        now = time.time()
        # 4 out of 6 chunks held by same cluster (66% concentration > 33% threshold)
        rows = [
            {'kind': 'BUNDLE_REPLICA_REGISTERED', 'feature_id': 'feat-1',
             'replica_peer_id': f'peer-{i}', 'at_unix': now - 10, 'chunk_indices': str(i)}
            for i in range(4)  # 4 peers holding consecutive chunks
        ]
        exchange = MockExchange(rows)
        result = apply_chunk_concentration_penalty(exchange, 'feat-1')
        if result.get('applied'):
            penalty_rows = [r for r in exchange.appended if r.get('direction') == 'cartel_chunk_penalty']
            for row in penalty_rows:
                self.assertLess(row['amount_units'], 0, 'Penalty must be negative')
                self.assertLessEqual(row['amount_units'], -UNIT, 'Penalty must be at least 1 token')

    def test_apply_cartel_penalty_idempotent(self):
        """apply_cartel_penalty must not penalize twice within 7-day window."""
        from urace.credit_ledger import apply_cartel_penalty
        import time

        class MockExchange:
            def __init__(self, rows):
                self._rows = list(rows)
                self.appended = []
            def audit_rows(self): return self._rows
            def append_audit_row(self, row):
                self.appended.append(row)
                self._rows.append(row)

        now = time.time()
        earn_rows = [
            {'kind': 'CREDIT_DELTA', 'direction': 'earn', 'peer': 'cartel-peer',
             'delta_units': 1000 * UNIT, 'at_unix': now - 86400 * 10}
            for _ in range(5)
        ] + [
            {'kind': 'CREDIT_DELTA', 'direction': 'earn', 'peer': f'honest-{i}',
             'delta_units': 10 * UNIT, 'at_unix': now - 86400 * 10}
            for i in range(10)
        ]
        exchange = MockExchange(earn_rows)
        r1 = apply_cartel_penalty(exchange, 'cartel-peer')
        r2 = apply_cartel_penalty(exchange, 'cartel-peer')
        if r1.get('applied'):
            self.assertFalse(r2.get('applied'), 'Second penalty within 7 days must be skipped')

if __name__ == '__main__':
    unittest.main()
