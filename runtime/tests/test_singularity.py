"""Tests for singularity-grade features: federation, decomposition, LLM-peer, audit chain."""
import unittest
import time


class MockExchange:
    def __init__(self):
        self._rows = []
    def audit_rows(self):
        return list(self._rows)
    def append_audit_row(self, row):
        self._rows.append(row)


class FederationTests(unittest.TestCase):
    def setUp(self):
        from urace import federation as fed
        self.fed = fed
        self.ex = MockExchange()

    def test_announce_creates_row(self):
        self.fed.announce_network(self.ex, 'net-a', 'http://a.example', 'Test net A')
        nets = self.fed.federated_networks(self.ex)
        self.assertEqual(len(nets), 1)
        self.assertEqual(nets[0]['network_id'], 'net-a')

    def test_announce_increments_sequence(self):
        self.fed.announce_network(self.ex, 'net-a', 'http://a.example')
        self.fed.announce_network(self.ex, 'net-a', 'http://a2.example')
        nets = self.fed.federated_networks(self.ex)
        self.assertEqual(len(nets), 1)
        self.assertEqual(nets[0]['sequence_id'], 2)
        self.assertEqual(nets[0]['endpoint'], 'http://a2.example')

    def test_multiple_networks_separate(self):
        self.fed.announce_network(self.ex, 'net-a', 'http://a.example')
        self.fed.announce_network(self.ex, 'net-b', 'http://b.example')
        nets = self.fed.federated_networks(self.ex)
        self.assertEqual(len(nets), 2)

    def test_query_and_adoption(self):
        qid = self.fed.query_feature(self.ex, 'feat-x', 'alice')
        self.assertIsNotNone(qid)
        self.fed.record_federation_adoption(self.ex, qid, 'net-remote', 'feat-x', 'bob', 0.8)
        results = self.fed.federation_adoption_results(self.ex, qid)
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]['discounted_rep'], 0.8 * 0.7)

    def test_adoption_count_sybil_resistant(self):
        qid = self.fed.query_feature(self.ex, 'feat-x', 'alice')
        # Same (network, peer) pair — should count only once
        self.fed.record_federation_adoption(self.ex, qid, 'net-r', 'feat-x', 'bob', 0.8)
        self.fed.record_federation_adoption(self.ex, qid, 'net-r', 'feat-x', 'bob', 0.9)
        self.fed.record_federation_adoption(self.ex, qid, 'net-r', 'feat-x', 'carol', 0.7)
        count = self.fed.federated_adoption_count(self.ex, 'feat-x')
        self.assertEqual(count, 2)  # bob + carol, not 3

    def test_rep_discount_applied(self):
        qid = self.fed.query_feature(self.ex, 'feat-x', 'alice')
        self.fed.record_federation_adoption(self.ex, qid, 'net-r', 'feat-x', 'bob', 1.0)
        results = self.fed.federation_adoption_results(self.ex, qid)
        self.assertLess(results[0]['discounted_rep'], 1.0)
        self.assertGreaterEqual(results[0]['discounted_rep'], self.fed.FEDERATION_MIN_REP)


class AutoDecomposeTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from urace import peer_work_market as wm, credit_ledger as cl
        self.wm = wm
        self.cl = cl
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()
        cl.earn_units(self.tmpdir, 'alice', 100 * cl.UNIT, 'test-setup')

    def test_low_complexity_no_split(self):
        rids = self.wm.auto_decompose_request(
            self.ex, 'alice', 'simple task', self.cl.UNIT, complexity=0.4)
        self.assertEqual(len(rids), 1)

    def test_high_complexity_splits(self):
        rids = self.wm.auto_decompose_request(
            self.ex, 'alice', 'complex task', 4 * self.cl.UNIT, complexity=0.8)
        self.assertGreater(len(rids), 1)

    def test_all_sub_requests_in_exchange(self):
        rids = self.wm.auto_decompose_request(
            self.ex, 'alice', 'big task', 4 * self.cl.UNIT, complexity=0.9)
        rows = self.ex.audit_rows()
        created_ids = {r['request_id'] for r in rows if r.get('kind') == 'WORK_REQUEST'}
        for rid in rids:
            self.assertIn(rid, created_ids)


class ExecutorPeerTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm
        self.wm = wm
        self.ex = MockExchange()

    def test_register_executor_peer(self):
        self.wm.register_executor_peer(self.ex, 'claude-3', 'claude-3-sonnet', ['code', 'analysis'])
        rows = [r for r in self.ex.audit_rows() if r.get('kind') == self.wm.EXECUTOR_PEER_KIND]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['executor_id'], 'claude-3')

    def test_register_idempotent(self):
        self.wm.register_executor_peer(self.ex, 'claude-3', 'claude-3-sonnet')
        self.wm.register_executor_peer(self.ex, 'claude-3', 'claude-3-sonnet')
        rows = [r for r in self.ex.audit_rows() if r.get('kind') == self.wm.EXECUTOR_PEER_KIND]
        self.assertEqual(len(rows), 1)

    def test_executor_rep_defaults_to_initial(self):
        self.wm.register_executor_peer(self.ex, 'claude-3', 'model', initial_rep=0.5)
        rep = self.wm.executor_peer_combined_rep('claude-3', self.ex)
        self.assertAlmostEqual(rep, 0.5)

    def test_unregistered_executor_returns_zero(self):
        rep = self.wm.executor_peer_combined_rep('ghost', self.ex)
        self.assertEqual(rep, 0.0)


class AuditChainTests(unittest.TestCase):
    def setUp(self):
        from urace import peer_work_market as wm, credit_ledger as cl
        self.wm = wm
        self.ex = MockExchange()

    def test_empty_exchange_returns_hash(self):
        h = self.wm.audit_chain_root(self.ex)
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)  # sha256 hex

    def test_hash_changes_on_new_row(self):
        h1 = self.wm.audit_chain_root(self.ex)
        self.ex.append_audit_row({'kind': 'WORK_REQUEST', 'request_id': 'r1', 'at_unix': 1.0})
        h2 = self.wm.audit_chain_root(self.ex)
        self.assertNotEqual(h1, h2)

    def test_hash_deterministic(self):
        self.ex.append_audit_row({'kind': 'WORK_REQUEST', 'request_id': 'r1', 'at_unix': 1.0})
        h1 = self.wm.audit_chain_root(self.ex)
        h2 = self.wm.audit_chain_root(self.ex)
        self.assertEqual(h1, h2)


class QuorumStallFallbackTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from urace import peer_work_market as wm, credit_ledger as cl
        self.wm = wm
        self.cl = cl
        self.ex = MockExchange()
        self.tmpdir = tempfile.mkdtemp()
        cl.earn_units(self.tmpdir, 'alice', 10 * cl.UNIT, 'test')
        rid = wm.create_work_request(self.ex, 'alice', 'spec', cl.UNIT)
        self.rid = rid
        wm.submit_bid(self.ex, rid, 'bob', combined_rep=0.7)
        self.ex.append_audit_row({
            'kind': 'WORK_ACCEPTED', 'request_id': rid,
            'requester_id': 'alice', 'bidder_id': 'bob',
            'budget_units': cl.UNIT, 'at_unix': time.time(), 'at': 'now',
        })
        wm.submit_delivery(self.ex, rid, 'bob', 'hash-abc')

    def test_quorum_fallback_set_when_insufficient_peers(self):
        # Small network: only alice+bob in exchange, neither is neutral
        st = self.wm.escrow_state(self.rid, self.ex)
        self.assertEqual(st['state'], 'VERIFICATION')
        self.assertTrue(st['quorum_fallback'])

    def test_quorum_auto_release_noop_without_quorum(self):
        released = self.wm.quorum_auto_release(self.rid, self.ex, self.tmpdir)
        self.assertFalse(released)

    def test_escrow_state_or_raise_on_missing(self):
        with self.assertRaises(self.wm.EscrowNotFoundError):
            self.wm.escrow_state_or_raise('nonexistent', self.ex)

    def test_escrow_state_or_raise_on_existing(self):
        st = self.wm.escrow_state_or_raise(self.rid, self.ex)
        self.assertEqual(st['state'], 'VERIFICATION')
