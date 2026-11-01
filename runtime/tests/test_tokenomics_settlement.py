"""Tests for audit-derived token settlement and auto_relay.

Balances are computed from the tamper-evident audit log — no separate
mutable state file. Tests verify this property explicitly.
"""
import hashlib, json, tempfile, unittest
from pathlib import Path


def _make_exchange(root, name, network=False):
    from urace import peer_exchange as pe
    e = pe.Exchange(Path(root) / name)
    e.configure(enabled=True, network=network)
    e.feature('feat', [])
    return e


def _make_pair(tmp, network=False):
    from urace import peer_exchange as pe
    root = Path(tmp)
    a = pe.Exchange(root / 'a')
    b = pe.Exchange(root / 'b')
    for e in (a, b):
        e.configure(enabled=True, network=network)
        e.feature('feat', [])
    aid = a.identity()['peer_id']
    bid = b.identity()['peer_id']
    a.peer(b.identity()['certificate'], post_quantum=b.identity()['post_quantum'])
    b.peer(a.identity()['certificate'], post_quantum=a.identity()['post_quantum'])
    a.rule(bid, 'feat', 'send', True)
    b.rule(aid, 'feat', 'receive', True)
    return a, b, aid, bid


class TokenLedgerAuditDerivedTests(unittest.TestCase):
    """Token balances come from the audit log, not a mutable file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _exchange(self, name='node'):
        return _make_exchange(self.tmp.name, name)

    def test_initial_balance_equals_baseline_grant(self):
        from urace import token_ledger as tl
        e = self._exchange()
        # No audit events yet — balance is purely the baseline grant.
        self.assertEqual(tl.balance(e, 'peer1'), 3)

    def test_receive_reserved_event_counts_as_spend(self):
        from urace import token_ledger as tl
        e = self._exchange()
        peer = 'p' * 64
        with e.lock():
            e.event('RECEIVE_RESERVED', peer=peer, bytes=100, bundle='b' * 64)
        self.assertAlmostEqual(tl.balance(e, peer), 2.0)

    def test_applied_event_counts_as_earn(self):
        from urace import token_ledger as tl
        e = self._exchange()
        peer = 'p' * 64
        with e.lock():
            e.event('APPLIED_AFTER_LOCAL_QUALIFICATION', peer=peer, feature='feat',
                    bundle='b' * 64, score_delta=7.5,
                    canonical_fingerprint='c' * 64, outcome_fingerprint='o' * 64,
                    affected_files=[])
        self.assertAlmostEqual(tl.balance(e, peer), 10.5)

    def test_grant_exhausts_then_blocks(self):
        from urace import token_ledger as tl
        e = self._exchange()
        peer = 'p' * 64
        for i in range(3):
            with e.lock():
                e.event('RECEIVE_RESERVED', peer=peer, bytes=100, bundle=f'{i:064d}')
        self.assertAlmostEqual(tl.balance(e, peer), 0.0)
        with self.assertRaises(ValueError):
            tl.check_can_receive(e, peer)

    def test_earn_after_exhaustion_restores_credit(self):
        from urace import token_ledger as tl
        e = self._exchange()
        peer = 'p' * 64
        for i in range(3):
            with e.lock():
                e.event('RECEIVE_RESERVED', peer=peer, bytes=100, bundle=f'{i:064d}')
        with e.lock():
            e.event('APPLIED_AFTER_LOCAL_QUALIFICATION', peer=peer, feature='feat',
                    bundle='b' * 64, score_delta=5.0,
                    canonical_fingerprint='c' * 64, outcome_fingerprint='o' * 64,
                    affected_files=[])
        self.assertAlmostEqual(tl.balance(e, peer), 5.0)
        tl.check_can_receive(e, peer)  # should not raise

    def test_tamper_proof_no_state_file(self):
        """No token_state.json exists — balance is purely audit-derived."""
        from urace import token_ledger as tl
        e = self._exchange()
        # Confirm no token state file was created by balance()
        tl.balance(e, 'x' * 64)
        token_file = e.root / 'tokens' / 'token_state.json'
        self.assertFalse(token_file.exists())

    def test_summary_is_audit_derived_and_tamper_evident_flag_set(self):
        from urace import token_ledger as tl
        e = self._exchange()
        s = tl.summary(e)
        self.assertTrue(s['tamper_evident'])
        self.assertEqual(s['settlement'], 'audit-derived')

    def test_summary_reflects_audit_events(self):
        from urace import token_ledger as tl
        e = self._exchange()
        peer = 'p' * 64
        with e.lock():
            e.event('RECEIVE_RESERVED', peer=peer, bytes=100, bundle='b' * 64)
            e.event('APPLIED_AFTER_LOCAL_QUALIFICATION', peer=peer, feature='feat',
                    bundle='q' * 64, score_delta=4.0,
                    canonical_fingerprint='c' * 64, outcome_fingerprint='o' * 64,
                    affected_files=[])
        s = tl.summary(e)
        self.assertIn(peer, s['peers'])
        info = s['peers'][peer]
        self.assertAlmostEqual(info['earned'], 4.0)
        self.assertAlmostEqual(info['spent'], 1.0)
        self.assertAlmostEqual(info['balance'], 6.0)  # 3 + 4 - 1


class TokenSettlementIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_receive_without_settlement_does_not_check_balance(self):
        from urace import token_ledger as tl
        a, b, aid, bid = _make_pair(self.tmp.name)
        # token_settlement=False (default) — token balance is never checked.
        # Verify a normal receive works and no token_state.json is created.
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        result = b.receive(a.inspect(r['bundle_id'])['bundle'])
        self.assertEqual(result['status'], 'QUARANTINED')
        self.assertFalse((b.root / 'tokens' / 'token_state.json').exists())

    def test_receive_with_settlement_deducts_via_audit(self):
        from urace import token_ledger as tl
        a, b, aid, bid = _make_pair(self.tmp.name)
        b.configure(token_settlement=True)
        before = tl.balance(b, aid)
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        b.receive(a.inspect(r['bundle_id'])['bundle'])
        after = tl.balance(b, aid)
        self.assertAlmostEqual(before - after, 1.0)
        # Verify no token_state.json was created
        self.assertFalse((b.root / 'tokens' / 'token_state.json').exists())

    def test_settlement_blocks_after_baseline_exhausted(self):
        a, b, aid, bid = _make_pair(self.tmp.name)
        b.configure(token_settlement=True)
        for i in range(3):
            art = f'urace runtime improvement {i}'
            r = a.prepare(bid, 'feat', art, True)
            b.receive(a.inspect(r['bundle_id'])['bundle'])
        art4 = 'urace runtime improvement 999'
        r4 = a.prepare(bid, 'feat', art4, True)
        with self.assertRaises(ValueError):
            b.receive(a.inspect(r4['bundle_id'])['bundle'])

    def test_mark_qualified_credits_via_audit_event(self):
        """Without token_settlement, mark_qualified earns tokens regardless of receipt."""
        from urace import peer_improvement as pi, token_ledger as tl
        a, b, aid, bid = _make_pair(self.tmp.name)
        # token_settlement=False (default) — receipt_verified gate is off
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        recv = b.receive(a.inspect(r['bundle_id'])['bundle'])
        before = tl.balance(b, aid)
        pi.mark_qualified(b, recv['bundle_id'], score_delta=7.5,
                          affected_files={'executor.py': 'def run(): pass'},
                          baseline_sha256='a' * 64)
        after = tl.balance(b, aid)
        self.assertAlmostEqual(after - before, 7.5)
        # No token_state.json — earn came from audit event
        self.assertFalse((b.root / 'tokens' / 'token_state.json').exists())

    def test_token_summary_via_exchange(self):
        from urace import token_ledger as tl
        a, b, aid, bid = _make_pair(self.tmp.name)
        b.configure(token_settlement=True)
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        b.receive(a.inspect(r['bundle_id'])['bundle'])
        s = b.token_summary()
        self.assertEqual(s['schema'], 'urace-token-ledger-v1')
        self.assertTrue(s['tamper_evident'])
        self.assertIn(aid, s['peers'])

    def test_unverified_applied_event_does_not_earn_tokens_when_settlement_enabled(self):
        """With token_settlement=True, APPLIED events without receipt_verified=True earn nothing."""
        from urace import token_ledger as tl
        e = _make_exchange(self.tmp.name, 'node')
        e.configure(token_settlement=True)
        peer = 'p' * 64
        # Inject fake APPLIED event — no receipt_verified field (attacker-style)
        with e.lock():
            e.event('APPLIED_AFTER_LOCAL_QUALIFICATION', peer=peer, feature='feat',
                    bundle='b' * 64, score_delta=999.0,
                    canonical_fingerprint='c' * 64, outcome_fingerprint='o' * 64,
                    affected_files=[])
        bal = tl.balance(e, peer)
        # baseline_grant=3, earned=0 (receipt_verified absent), spent=0
        self.assertAlmostEqual(bal, 3.0)

    def test_verified_applied_event_earns_tokens_when_settlement_enabled(self):
        """With token_settlement=True, receipt_verified=True events DO earn tokens."""
        from urace import token_ledger as tl
        e = _make_exchange(self.tmp.name, 'node')
        e.configure(token_settlement=True)
        peer = 'p' * 64
        with e.lock():
            e.event('APPLIED_AFTER_LOCAL_QUALIFICATION', peer=peer, feature='feat',
                    bundle='b' * 64, score_delta=5.0,
                    canonical_fingerprint='c' * 64, outcome_fingerprint='o' * 64,
                    affected_files=[], receipt_verified=True, qualification_id=None)
        bal = tl.balance(e, peer)
        self.assertAlmostEqual(bal, 8.0)  # 3 + 5

    def test_without_settlement_unverified_events_still_earn(self):
        """token_settlement=False — receipt_verified gate is off; unverified events earn normally."""
        from urace import token_ledger as tl
        e = _make_exchange(self.tmp.name, 'node')
        peer = 'p' * 64
        with e.lock():
            e.event('APPLIED_AFTER_LOCAL_QUALIFICATION', peer=peer, feature='feat',
                    bundle='b' * 64, score_delta=5.0,
                    canonical_fingerprint='c' * 64, outcome_fingerprint='o' * 64,
                    affected_files=[])
        bal = tl.balance(e, peer)
        self.assertAlmostEqual(bal, 8.0)


class AutoRelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _three_node_setup(self):
        from urace import peer_exchange as pe
        root = Path(self.tmp.name)
        a = pe.Exchange(root / 'a')
        b = pe.Exchange(root / 'b')
        c = pe.Exchange(root / 'c')
        for e in (a, b, c):
            e.configure(enabled=True)
            e.feature('feat', [])
        aid = a.identity()['peer_id']
        bid = b.identity()['peer_id']
        cid = c.identity()['peer_id']
        for (src, dst, dsid) in [(a, b, bid), (b, a, aid), (b, c, cid), (c, b, bid)]:
            src.peer(dst.identity()['certificate'], post_quantum=dst.identity()['post_quantum'])
            src.rule(dsid, 'feat', 'send', True)
        b.peer(a.identity()['certificate'], post_quantum=a.identity()['post_quantum'])
        b.rule(aid, 'feat', 'receive', True)
        c.peer(b.identity()['certificate'], post_quantum=b.identity()['post_quantum'])
        c.rule(bid, 'feat', 'receive', True)
        return a, b, c, aid, bid, cid

    def test_relay_disabled_by_default(self):
        from urace import peer_improvement as pi
        a, b, c, aid, bid, cid = self._three_node_setup()
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        recv = b.receive(a.inspect(r['bundle_id'])['bundle'])
        with b.lock():
            b.event('APPLIED_AFTER_LOCAL_QUALIFICATION', peer=aid, feature='feat',
                    bundle=recv['bundle_id'], score_delta=5.0,
                    canonical_fingerprint='c' * 64, outcome_fingerprint='o' * 64,
                    affected_files=[])
        result = pi.relay_qualified(b, recv['bundle_id'])
        self.assertEqual(result['status'], 'AUTO_RELAY_DISABLED')

    def test_prepare_relay_requires_qualification_event(self):
        a, b, c, aid, bid, cid = self._three_node_setup()
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        recv = b.receive(a.inspect(r['bundle_id'])['bundle'])
        with self.assertRaises(ValueError):
            b.prepare_relay(cid, recv['bundle_id'])

    def test_prepare_relay_after_qualification_succeeds(self):
        a, b, c, aid, bid, cid = self._three_node_setup()
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        recv = b.receive(a.inspect(r['bundle_id'])['bundle'])
        bundle_id = recv['bundle_id']
        with b.lock():
            b.event('APPLIED_AFTER_LOCAL_QUALIFICATION', peer=aid, feature='feat',
                    bundle=bundle_id, score_delta=5.0,
                    canonical_fingerprint='c' * 64, outcome_fingerprint='o' * 64,
                    affected_files=[])
        result = b.prepare_relay(cid, bundle_id)
        self.assertTrue(result['relay'])
        self.assertEqual(result['source_bundle_id'], bundle_id)

    def test_auto_relay_propagates_to_eligible_peer(self):
        from urace import peer_improvement as pi
        a, b, c, aid, bid, cid = self._three_node_setup()
        b.configure(auto_relay=True)
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        recv = b.receive(a.inspect(r['bundle_id'])['bundle'])
        result = pi.mark_qualified(b, recv['bundle_id'], score_delta=5.0,
                                   affected_files={'executor.py': 'def run(): pass'},
                                   baseline_sha256='a' * 64)
        relay = result.get('relay', {})
        self.assertGreaterEqual(relay.get('relayed', 0), 1)
        rows = b.audit_rows()
        relay_events = [r for r in rows if r.get('kind') == 'RELAY_PREPARED']
        self.assertEqual(len(relay_events), 1)

    def test_relay_skips_original_sender(self):
        from urace import peer_improvement as pi
        a, b, c, aid, bid, cid = self._three_node_setup()
        b.configure(auto_relay=True)
        art = 'urace runtime improvement'
        r = a.prepare(bid, 'feat', art, True)
        recv = b.receive(a.inspect(r['bundle_id'])['bundle'])
        result = pi.mark_qualified(b, recv['bundle_id'], score_delta=5.0,
                                   affected_files={}, baseline_sha256='a' * 64)
        relay = result.get('relay', {})
        relayed_peers = [x['peer'] for x in relay.get('relayed_to', [])]
        self.assertNotIn(aid[:16], relayed_peers)
