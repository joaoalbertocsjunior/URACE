"""Tests for credit_ledger.py — locked grant APIs and weighted_rep_score."""
import tempfile
import time
import unittest
from pathlib import Path

from urace import credit_ledger as cl


def _root(tmp_dir, name='peer'):
    root = Path(tmp_dir) / name
    root.mkdir(parents=True, exist_ok=True)
    return str(root)


def _append_credit(root, peer_id, direction, amount_units, rep_source='work'):
    """Directly append a CREDIT_DELTA row to the ledger."""
    cl._ledger(root).append('CREDIT_DELTA', {
        'peer': peer_id,
        'delta_units': amount_units,
        'direction': direction,
        'rep_source': rep_source,
        'at_unix': time.time(),
    })


class LockedGrantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='urace-grant-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = _root(self.tmp.name)

    def test_locked_grant_balance_full_at_creation(self):
        # Fresh peer: no unlock events → locked balance == BASELINE_GRANT_UNITS
        locked = cl.locked_grant_balance(self.root, 'alice')
        self.assertEqual(locked, cl.BASELINE_GRANT_UNITS)

    def test_unlock_grant_returns_nonzero_unlocked(self):
        # unlock_grant should report unlocked amount > 0 on first call
        result = cl.unlock_grant(self.root, 'alice', delivery_earn_units=cl.UNIT)
        self.assertGreater(result['unlocked'], 0)
        self.assertEqual(result['unlocked'], cl.UNIT)

    def test_unlock_grant_capped_at_baseline_grant_units(self):
        # First unlock: still_locked=BASELINE_GRANT_UNITS, unlocks 1 UNIT,
        # returns remaining = BASELINE_GRANT_UNITS - UNIT = 2*UNIT.
        r1 = cl.unlock_grant(self.root, 'alice', delivery_earn_units=cl.UNIT)
        self.assertEqual(r1['unlocked'], cl.UNIT)
        self.assertEqual(r1['remaining_locked'], cl.BASELINE_GRANT_UNITS - cl.UNIT)
        # Returned dict's remaining_locked is always based on current still_locked
        self.assertGreaterEqual(r1['remaining_locked'], 0)

    def test_unlock_grant_idempotent_beyond_cap(self):
        # When locked_grant_balance returns 0, unlock_grant is a no-op.
        # Simulate by directly injecting enough baseline_grant_unlock rows so
        # _row_units sums to >= BASELINE_GRANT_UNITS.
        # _row_units uses delta_units; inject rows with delta_units=UNIT to reduce balance.
        for _ in range(cl.BASELINE_GRANT):
            cl._ledger(self.root).append('CREDIT_DELTA', {
                'peer': 'alice',
                'delta_units': cl.UNIT,
                'direction': 'baseline_grant_unlock',
                'rep_source': 'work',
                'at_unix': 1.0,
            })
        # Now locked_grant_balance should be 0 (3*UNIT unlocked)
        remaining = cl.locked_grant_balance(self.root, 'alice')
        self.assertEqual(remaining, 0)
        result = cl.unlock_grant(self.root, 'alice', delivery_earn_units=cl.UNIT)
        self.assertEqual(result['unlocked'], 0)
        self.assertEqual(result['remaining_locked'], 0)


class WeightedRepScoreEventCountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='urace-rep-test-')
        self.addCleanup(self.tmp.cleanup)

    def test_score_counts_events_not_amounts(self):
        """Two earn events at 1 unit vs two earn events at 1M units → same score."""
        root_small = _root(self.tmp.name, 'small')
        root_large = _root(self.tmp.name, 'large')

        # peer_small: 2 earn events at 1 unit each
        _append_credit(root_small, 'peer', 'earn', 1)
        _append_credit(root_small, 'peer', 'earn', 1)

        # peer_large: 2 earn events at 1_000_000 units each
        _append_credit(root_large, 'peer', 'earn', 1_000_000)
        _append_credit(root_large, 'peer', 'earn', 1_000_000)

        score_small = cl.weighted_rep_score(root_small, 'peer')
        score_large = cl.weighted_rep_score(root_large, 'peer')

        # Both have 2 earn events → same score (event count, not amounts)
        self.assertAlmostEqual(score_small, score_large, places=10)

    def test_trade_source_events_excluded(self):
        """Rows with rep_source='trade' should contribute 0 to score."""
        root = _root(self.tmp.name, 'trade')

        _append_credit(root, 'peer', 'earn', 100, rep_source='work')
        _append_credit(root, 'peer', 'asset_royalty', 1_000_000, rep_source='trade')
        _append_credit(root, 'peer', 'purchase_receive', 500, rep_source='trade')

        score = cl.weighted_rep_score(root, 'peer')
        # Only the 'earn' work row contributes (weight=1.0)
        # asset_royalty + purchase_receive are trade → weight=0.0
        expected = cl.CONSENSUS_WEIGHTS.get('earn', 1.0)
        self.assertAlmostEqual(score, expected, places=10)

    def test_longevity_multiplier_applied(self):
        root = _root(self.tmp.name, 'longevity')
        _append_credit(root, 'peer', 'earn', 10)
        _append_credit(root, 'peer', 'earn', 10)

        base_score = cl.weighted_rep_score(root, 'peer', longevity_multiplier=1.0)
        scaled_score = cl.weighted_rep_score(root, 'peer', longevity_multiplier=2.0)
        self.assertAlmostEqual(scaled_score, base_score * 2.0, places=10)

    def test_unknown_direction_scores_zero(self):
        root = _root(self.tmp.name, 'unknown')
        _append_credit(root, 'peer', 'completely_unknown_direction', 999)

        score = cl.weighted_rep_score(root, 'peer')
        # CONSENSUS_WEIGHTS.get('completely_unknown_direction', 0.0) == 0.0
        self.assertEqual(score, 0.0)

    def test_zero_longevity_multiplier_gives_zero(self):
        root = _root(self.tmp.name, 'zerolongevity')
        _append_credit(root, 'peer', 'earn', 10)

        score = cl.weighted_rep_score(root, 'peer', longevity_multiplier=0.0)
        self.assertEqual(score, 0.0)
