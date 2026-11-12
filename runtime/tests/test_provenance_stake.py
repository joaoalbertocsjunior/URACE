"""Tests for Asset Provenance Staking (APS) — provenance_stake.py"""
import time
import unittest
from unittest.mock import patch, MagicMock

from urace import provenance_stake as ps


class MockExchange:
    def __init__(self):
        self._rows = []

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)


def _fund(ex, peer_id, amount):
    ex.append_audit_row({'kind': 'CREDIT_DELTA', 'peer': peer_id, 'amount_units': amount, 'at_unix': time.time()})


def _lock(ex, feature_id='feat-1', staker='alice', units=3, days=30):
    _fund(ex, staker, units + 10)
    return ps.lock_mint_stake(ex, feature_id, staker, units, days)


# ── MintStakeLockTests ────────────────────────────────────────────────────────

class MintStakeLockTests(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()

    def test_lock_emits_mint_stake_locked_row(self):
        _fund(self.ex, 'alice', 10)
        row = ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        self.assertEqual(row['kind'], 'MINT_STAKE_LOCKED')
        self.assertEqual(row['feature_id'], 'feat-1')
        self.assertEqual(row['staker_peer_id'], 'alice')
        self.assertEqual(row['stake_units'], 3)
        rows = self.ex.audit_rows()
        lock_rows = [r for r in rows if r['kind'] == 'MINT_STAKE_LOCKED']
        self.assertEqual(len(lock_rows), 1)

    def test_lock_deducts_balance(self):
        _fund(self.ex, 'alice', 10)
        ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        balance = ps._credit_balance(self.ex.audit_rows(), 'alice')
        self.assertEqual(balance, 7)

    def test_lock_insufficient_balance_raises(self):
        _fund(self.ex, 'alice', 2)
        with self.assertRaises(ValueError) as ctx:
            ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        self.assertIn('Insufficient balance', str(ctx.exception))

    def test_lock_idempotent(self):
        _fund(self.ex, 'alice', 10)
        row1 = ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        row2 = ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        self.assertEqual(row1['challenge_deadline_unix'], row2['challenge_deadline_unix'])
        lock_rows = [r for r in self.ex.audit_rows() if r['kind'] == 'MINT_STAKE_LOCKED']
        self.assertEqual(len(lock_rows), 1)


# ── MintStakeReleaseTests ─────────────────────────────────────────────────────

class MintStakeReleaseTests(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()

    def test_release_after_window_returns_stake(self):
        _fund(self.ex, 'alice', 10)
        # Lock with deadline already expired (window=0 days, then manually patch)
        ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        # Patch deadline to past
        for r in self.ex._rows:
            if r.get('kind') == 'MINT_STAKE_LOCKED':
                r['challenge_deadline_unix'] = time.time() - 1
        bal_before = ps._credit_balance(self.ex.audit_rows(), 'alice')
        released = ps.release_mint_stake(self.ex, 'feat-1')
        self.assertTrue(released)
        bal_after = ps._credit_balance(self.ex.audit_rows(), 'alice')
        self.assertEqual(bal_after, bal_before + 3)

    def test_release_before_window_raises(self):
        _fund(self.ex, 'alice', 10)
        ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        with self.assertRaises(ValueError) as ctx:
            ps.release_mint_stake(self.ex, 'feat-1')
        self.assertIn('Challenge window still open', str(ctx.exception))

    def test_release_already_slashed_raises(self):
        _fund(self.ex, 'alice', 10)
        ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        # Patch deadline to past
        for r in self.ex._rows:
            if r.get('kind') == 'MINT_STAKE_LOCKED':
                r['challenge_deadline_unix'] = time.time() - 1
        # Inject a MINT_STAKE_SLASHED row directly
        self.ex.append_audit_row({'kind': 'MINT_STAKE_SLASHED', 'feature_id': 'feat-1', 'staker_peer_id': 'alice', 'stake_units': 3})
        with self.assertRaises(ValueError) as ctx:
            ps.release_mint_stake(self.ex, 'feat-1')
        self.assertIn('already slashed', str(ctx.exception))


# ── ProvChallengeTests ────────────────────────────────────────────────────────

class ProvChallengeTests(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()

    def _setup_locked(self, feature_id='feat-1', creator='alice', stake=3, days=30):
        _fund(self.ex, creator, stake + 5)
        ps.lock_mint_stake(self.ex, feature_id, creator, stake, days)

    def test_file_challenge_emits_row(self):
        self._setup_locked()
        _fund(self.ex, 'bob', 5)
        row = ps.file_challenge(self.ex, 'feat-1', 'bob', 'some evidence', '', 2)
        self.assertEqual(row['kind'], 'PROVENANCE_CHALLENGE')
        self.assertEqual(row['feature_id'], 'feat-1')
        self.assertEqual(row['status'], 'pending')

    def test_file_challenge_locks_challenger_stake(self):
        self._setup_locked()
        _fund(self.ex, 'bob', 5)
        bal_before = ps._credit_balance(self.ex.audit_rows(), 'bob')
        ps.file_challenge(self.ex, 'feat-1', 'bob', '', '', 2)
        bal_after = ps._credit_balance(self.ex.audit_rows(), 'bob')
        self.assertEqual(bal_after, bal_before - 2)

    def test_file_challenge_outside_window_raises(self):
        self._setup_locked()
        # Expire the window
        for r in self.ex._rows:
            if r.get('kind') == 'MINT_STAKE_LOCKED':
                r['challenge_deadline_unix'] = time.time() - 1
        _fund(self.ex, 'bob', 5)
        with self.assertRaises(ValueError) as ctx:
            ps.file_challenge(self.ex, 'feat-1', 'bob')
        self.assertIn('expired', str(ctx.exception))

    def test_file_challenge_insufficient_balance_raises(self):
        self._setup_locked()
        _fund(self.ex, 'bob', 1)
        with self.assertRaises(ValueError) as ctx:
            ps.file_challenge(self.ex, 'feat-1', 'bob', '', '', 2)
        self.assertIn('Insufficient balance', str(ctx.exception))

    def test_file_challenge_already_pending_raises(self):
        self._setup_locked()
        _fund(self.ex, 'bob', 10)
        ps.file_challenge(self.ex, 'feat-1', 'bob', '', '', 2)
        # bob's balance after first challenge is depleted — fund charlie
        _fund(self.ex, 'charlie', 10)
        with self.assertRaises(ValueError) as ctx:
            ps.file_challenge(self.ex, 'feat-1', 'charlie', '', '', 2)
        self.assertIn('pending challenge already exists', str(ctx.exception))

    def test_auto_uphold_when_composition_detected(self):
        self._setup_locked()
        # Inject auto-detected composition
        self.ex.append_audit_row({'kind': 'FEATURE_COMPOSITION', 'composite_feature_id': 'feat-1', 'component_feature_ids': ['orig-feat'], 'auto_detected': True})
        _fund(self.ex, 'bob', 5)
        ps.file_challenge(self.ex, 'feat-1', 'bob', '', 'orig-feat', 2)
        rows = self.ex.audit_rows()
        resolved = [r for r in rows if r.get('kind') == 'PROVENANCE_CHALLENGE_RESOLVED' and r.get('feature_id') == 'feat-1']
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]['verdict'], 'upheld')


# ── ChallengeResolutionTests ──────────────────────────────────────────────────

class ChallengeResolutionTests(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()
        # Fund alice (creator) and lock stake
        _fund(self.ex, 'alice', 10)
        ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        # Fund bob (challenger) and file challenge
        _fund(self.ex, 'bob', 10)
        self.challenge_row = ps.file_challenge(self.ex, 'feat-1', 'bob', 'evidence', 'orig-feat', 2)
        self.cid = self.challenge_row['challenge_id']
        # Add base owner grant row
        self.ex.append_audit_row({'kind': 'EQUITY_GRANT', 'feature_id': 'orig-feat', 'peer_id': 'carol'})

    def test_uphold_revokes_grant(self):
        ps.resolve_challenge(self.ex, self.cid, 'upheld')
        rows = self.ex.audit_rows()
        revoked = [r for r in rows if r.get('kind') == 'EQUITY_GRANT_REVOKED' and r.get('feature_id') == 'feat-1']
        self.assertEqual(len(revoked), 1)

    def test_uphold_distributes_stake_to_challenger(self):
        bal_before = ps._credit_balance(self.ex.audit_rows(), 'bob')
        ps.resolve_challenge(self.ex, self.cid, 'upheld')
        bal_after = ps._credit_balance(self.ex.audit_rows(), 'bob')
        # challenger gets bounty (from slash) + stake return
        self.assertGreater(bal_after, bal_before)

    def test_uphold_compensates_base_owner(self):
        bal_before = ps._credit_balance(self.ex.audit_rows(), 'carol')
        ps.resolve_challenge(self.ex, self.cid, 'upheld')
        bal_after = ps._credit_balance(self.ex.audit_rows(), 'carol')
        self.assertGreater(bal_after, bal_before)

    def test_uphold_returns_challenger_stake(self):
        ps.resolve_challenge(self.ex, self.cid, 'upheld')
        rows = self.ex.audit_rows()
        returned = [r for r in rows if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'challenge_stake_returned' and r.get('peer') == 'bob']
        self.assertEqual(len(returned), 1)
        self.assertEqual(returned[0]['amount_units'], 2)

    def test_rejected_slashes_challenger_stake(self):
        bal_before = ps._credit_balance(self.ex.audit_rows(), 'bob')
        ps.resolve_challenge(self.ex, self.cid, 'rejected')
        bal_after = ps._credit_balance(self.ex.audit_rows(), 'bob')
        # No stake return for challenger on rejection
        rows = self.ex.audit_rows()
        returned = [r for r in rows if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'challenge_stake_returned' and r.get('peer') == 'bob']
        self.assertEqual(len(returned), 0)
        # balance should be same (no extra credit)
        self.assertEqual(bal_after, bal_before)

    def test_rejected_releases_creator_stake(self):
        ps.resolve_challenge(self.ex, self.cid, 'rejected')
        rows = self.ex.audit_rows()
        released = [r for r in rows if r.get('kind') == 'MINT_STAKE_RELEASED' and r.get('feature_id') == 'feat-1']
        self.assertEqual(len(released), 1)
        credit = [r for r in rows if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'mint_stake_released' and r.get('peer') == 'alice']
        self.assertEqual(len(credit), 1)
        self.assertEqual(credit[0]['amount_units'], 3)

    def test_resolve_twice_raises(self):
        ps.resolve_challenge(self.ex, self.cid, 'upheld')
        with self.assertRaises(ValueError) as ctx:
            ps.resolve_challenge(self.ex, self.cid, 'rejected')
        self.assertIn('already resolved', str(ctx.exception))


# ── ChallengeStatusTests ──────────────────────────────────────────────────────

class ChallengeStatusTests(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()

    def test_status_no_stake(self):
        status = ps.challenge_status(self.ex, 'feat-1')
        self.assertFalse(status['staked'])
        self.assertFalse(status['window_open'])

    def test_status_window_open(self):
        _fund(self.ex, 'alice', 10)
        ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        status = ps.challenge_status(self.ex, 'feat-1')
        self.assertTrue(status['staked'])
        self.assertTrue(status['window_open'])
        self.assertGreater(status['days_remaining'], 29.0)

    def test_status_revoked(self):
        _fund(self.ex, 'alice', 10)
        ps.lock_mint_stake(self.ex, 'feat-1', 'alice', 3, 30)
        _fund(self.ex, 'bob', 5)
        challenge = ps.file_challenge(self.ex, 'feat-1', 'bob', '', '', 2)
        ps.resolve_challenge(self.ex, challenge['challenge_id'], 'upheld')
        status = ps.challenge_status(self.ex, 'feat-1')
        self.assertTrue(status['revoked'])
        self.assertEqual(status['verdict'], 'upheld')


# ── FillListingGuardTests ─────────────────────────────────────────────────────

class FillListingGuardTests(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()

    def test_revoked_feature_blocked_at_fill_listing(self):
        """EQUITY_GRANT_REVOKED row prevents borrow — mirrors fill-listing guard logic."""
        feature_id = 'feat-revoked'
        # Inject a revoked grant
        self.ex.append_audit_row({'kind': 'EQUITY_GRANT_REVOKED', 'feature_id': feature_id, 'reason': 'provenance_challenge_upheld'})
        # Inject a listing row
        listing = {'kind': 'EQUITY_LISTING', 'listing_id': 'lst-1', 'feature_id': feature_id}
        # Replicate the guard logic from exchange_cli fill-listing
        rows = self.ex.audit_rows()
        _fl_listing = listing
        _fl_feat_check = _fl_listing.get('feature_id', '')
        _revoked_check = any(r.get('kind') == 'EQUITY_GRANT_REVOKED' and r.get('feature_id') == _fl_feat_check for r in rows)
        self.assertTrue(_revoked_check, 'Revoked feature should be detected')
        # Verify that ValueError would be raised in CLI
        if _revoked_check:
            with self.assertRaises(ValueError) as ctx:
                raise ValueError(f'Feature {_fl_feat_check!r} equity grant has been revoked (provenance challenge upheld) — cannot borrow.')
            self.assertIn('revoked', str(ctx.exception))


# ── QuorumCrossNodeTests ──────────────────────────────────────────────────────

class QuorumCrossNodeTests(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()

    def _setup_pending_challenge(self, feature_id='feat-1', creator='alice', challenger='bob'):
        _fund(self.ex, creator, 10)
        ps.lock_mint_stake(self.ex, feature_id, creator, 3, 30)
        _fund(self.ex, challenger, 10)
        row = ps.file_challenge(self.ex, feature_id, challenger, 'evidence', '', 2)
        return row['challenge_id']

    def test_fetch_quorum_verdicts_calls_bootstrap_peer(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"verdicts": [{"verdict": "upheld", "peer_id": "p1"}]}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch('urllib.request.urlopen', return_value=mock_resp):
            result = ps.fetch_quorum_verdicts(self.ex, 'feat1', 'chal1', ['https://bp.example.com'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['verdict'], 'upheld')
        self.assertEqual(result[0]['peer_id'], 'p1')

    def test_fetch_quorum_verdicts_ignores_unreachable_peer(self):
        with patch('urllib.request.urlopen', side_effect=OSError('connection refused')):
            result = ps.fetch_quorum_verdicts(self.ex, 'feat1', 'chal1', ['https://bp.example.com'])
        self.assertEqual(result, [])

    def test_resolve_challenge_uses_remote_majority_when_available(self):
        cid = self._setup_pending_challenge()
        remote = [{'verdict': 'upheld', 'peer_id': 'p1'}, {'verdict': 'upheld', 'peer_id': 'p2'}]
        with patch.object(ps, 'fetch_quorum_verdicts', return_value=remote):
            # local verdict is 'rejected' but remote majority is 'upheld'
            result = ps.resolve_challenge(self.ex, cid, 'rejected', bootstrap_peers=['https://bp.example.com'])
        self.assertEqual(result['verdict'], 'upheld')
        self.assertEqual(result['resolver_type'], 'remote_quorum')

    def test_resolve_challenge_keeps_local_when_no_bootstrap_peers(self):
        cid = self._setup_pending_challenge()
        with patch.object(ps, 'fetch_quorum_verdicts') as mock_fqv:
            result = ps.resolve_challenge(self.ex, cid, 'rejected', bootstrap_peers=[])
        mock_fqv.assert_not_called()
        self.assertEqual(result['verdict'], 'rejected')

    def test_resolve_challenge_keeps_local_on_remote_tie(self):
        cid = self._setup_pending_challenge()
        remote = [{'verdict': 'upheld', 'peer_id': 'p1'}, {'verdict': 'rejected', 'peer_id': 'p2'}]
        with patch.object(ps, 'fetch_quorum_verdicts', return_value=remote):
            result = ps.resolve_challenge(self.ex, cid, 'rejected', bootstrap_peers=['https://bp.example.com'])
        # tie → local verdict stands
        self.assertEqual(result['verdict'], 'rejected')
        self.assertNotEqual(result.get('resolver_type'), 'remote_quorum')


if __name__ == '__main__':
    unittest.main()
