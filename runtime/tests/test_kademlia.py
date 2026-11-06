"""Tests for kademlia.py — Kademlia-style DHT routing table."""

import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path

from urace.kademlia import (
    ALPHA,
    K_BUCKET_SIZE,
    KBucket,
    NodeInfo,
    RoutingTable,
    bucket_index,
    peer_id_to_node_id,
    xor_distance,
)


class NodeIdTests(unittest.TestCase):

    def test_peer_id_to_node_id_deterministic(self):
        a = peer_id_to_node_id('peer-abc')
        b = peer_id_to_node_id('peer-abc')
        self.assertEqual(a, b)

    def test_peer_id_to_node_id_different_peers(self):
        a = peer_id_to_node_id('peer-alpha')
        b = peer_id_to_node_id('peer-beta')
        self.assertNotEqual(a, b)

    def test_xor_distance_self_is_zero(self):
        a = peer_id_to_node_id('some-peer')
        self.assertEqual(xor_distance(a, a), 0)

    def test_xor_distance_symmetric(self):
        a = peer_id_to_node_id('peer-x')
        b = peer_id_to_node_id('peer-y')
        self.assertEqual(xor_distance(a, b), xor_distance(b, a))

    def test_bucket_index_self(self):
        x = peer_id_to_node_id('self-peer')
        self.assertEqual(bucket_index(x, x), 0)

    def test_bucket_index_range(self):
        a = peer_id_to_node_id('peer-a')
        b = peer_id_to_node_id('peer-b')
        idx = bucket_index(a, b)
        self.assertIsInstance(idx, int)
        self.assertGreaterEqual(idx, 0)
        self.assertLessEqual(idx, 255)


class KBucketTests(unittest.TestCase):

    def _make_node(self, peer_id: str) -> NodeInfo:
        node_id = peer_id_to_node_id(peer_id)
        return NodeInfo(peer_id=peer_id, node_id=node_id, endpoint='')

    def test_add_new_node(self):
        bucket = KBucket(k=5)
        node = self._make_node('p1')
        bucket.add(node)
        self.assertEqual(len(bucket), 1)
        self.assertEqual(bucket.nodes()[-1].peer_id, 'p1')

    def test_add_duplicate_refreshes(self):
        bucket = KBucket(k=5)
        n1 = self._make_node('p1')
        n2 = self._make_node('p2')
        bucket.add(n1)
        bucket.add(n2)
        # Re-add p1 — should move to tail
        n1_refresh = self._make_node('p1')
        bucket.add(n1_refresh)
        self.assertEqual(len(bucket), 2)
        self.assertEqual(bucket.nodes()[-1].peer_id, 'p1')

    def test_overflow_evicts_lru(self):
        k = 3
        bucket = KBucket(k=k)
        for i in range(k + 1):
            bucket.add(self._make_node(f'peer-{i}'))
        self.assertEqual(len(bucket), k)
        # peer-0 (LRU) should be evicted
        peer_ids = [n.peer_id for n in bucket.nodes()]
        self.assertNotIn('peer-0', peer_ids)
        self.assertIn(f'peer-{k}', peer_ids)

    def test_remove(self):
        bucket = KBucket(k=5)
        bucket.add(self._make_node('p1'))
        bucket.add(self._make_node('p2'))
        bucket.remove('p1')
        self.assertEqual(len(bucket), 1)
        self.assertEqual(bucket.nodes()[0].peer_id, 'p2')

    def test_len(self):
        bucket = KBucket(k=10)
        for i in range(5):
            bucket.add(self._make_node(f'p{i}'))
        self.assertEqual(len(bucket), 5)


class RoutingTableTests(unittest.TestCase):

    OWN_PEER = 'own-peer-id'

    def _rt(self) -> RoutingTable:
        return RoutingTable(self.OWN_PEER)

    def test_add_peer(self):
        rt = self._rt()
        rt.add('peer-1')
        self.assertEqual(rt.size(), 1)

    def test_add_self_ignored(self):
        rt = self._rt()
        rt.add(self.OWN_PEER)
        self.assertEqual(rt.size(), 0)

    def test_add_multiple_peers(self):
        rt = self._rt()
        for i in range(10):
            rt.add(f'peer-{i}')
        self.assertEqual(rt.size(), 10)

    def test_remove_peer(self):
        rt = self._rt()
        rt.add('peer-x')
        rt.remove('peer-x')
        self.assertEqual(rt.size(), 0)

    def test_find_closest_empty(self):
        rt = self._rt()
        result = rt.find_closest(12345678)
        self.assertEqual(result, [])

    def test_find_closest_returns_sorted(self):
        rt = self._rt()
        peers = [f'peer-{i}' for i in range(5)]
        for p in peers:
            rt.add(p)
        target_id = peer_id_to_node_id('arbitrary-target')
        result = rt.find_closest(target_id)
        # Verify sorted by XOR distance
        distances = [xor_distance(n.node_id, target_id) for n in result]
        self.assertEqual(distances, sorted(distances))

    def test_find_closest_count_limit(self):
        rt = self._rt()
        for i in range(10):
            rt.add(f'peer-{i}')
        target_id = peer_id_to_node_id('target')
        result = rt.find_closest(target_id, count=3)
        self.assertLessEqual(len(result), 3)

    def test_chunk_holders_routing(self):
        rt = self._rt()
        for i in range(10):
            rt.add(f'peer-{i}', endpoint=f'127.0.0.1:{5000+i}')
        artifact_sha = 'a' * 64
        result = rt.chunk_holders(artifact_sha, chunk_idx=0, count=ALPHA)
        self.assertLessEqual(len(result), ALPHA)
        # Verify the routing key computation is correct
        key_str = f'{artifact_sha}:chunk:0'
        key_hex = hashlib.sha256(key_str.encode()).hexdigest()
        target_id = int(key_hex, 16)
        expected = rt.find_closest(target_id, ALPHA)
        self.assertEqual([n.peer_id for n in result], [n.peer_id for n in expected])

    def test_serialization_roundtrip(self):
        rt = self._rt()
        for i in range(5):
            rt.add(f'peer-{i}', endpoint=f'127.0.0.1:{6000+i}')
        d = rt.to_dict()
        rt2 = RoutingTable.from_dict(d)
        self.assertEqual(rt2.own_peer_id, rt.own_peer_id)
        self.assertEqual(rt2.size(), rt.size())
        original_ids = {n.peer_id for b in rt._buckets for n in b.nodes()}
        restored_ids = {n.peer_id for b in rt2._buckets for n in b.nodes()}
        self.assertEqual(original_ids, restored_ids)

    def test_save_load(self):
        rt = self._rt()
        for i in range(4):
            rt.add(f'peer-{i}', endpoint=f'127.0.0.1:{7000+i}')
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        rt.save(path)
        rt2 = RoutingTable.load(path, self.OWN_PEER)
        self.assertEqual(rt2.size(), rt.size())
        original_ids = {n.peer_id for b in rt._buckets for n in b.nodes()}
        restored_ids = {n.peer_id for b in rt2._buckets for n in b.nodes()}
        self.assertEqual(original_ids, restored_ids)

    def test_load_missing_file_returns_fresh(self):
        rt = RoutingTable.load('/tmp/nonexistent_kademlia_xyz.json', self.OWN_PEER)
        self.assertEqual(rt.size(), 0)
        self.assertEqual(rt.own_peer_id, self.OWN_PEER)

    def test_size(self):
        rt = self._rt()
        for i in range(7):
            rt.add(f'peer-{i}')
        self.assertEqual(rt.size(), 7)

    def test_find_closest_for_peer(self):
        rt = self._rt()
        for i in range(6):
            rt.add(f'peer-{i}')
        target_peer = 'target-peer-id'
        result = rt.find_closest_for_peer(target_peer, count=3)
        target_id = peer_id_to_node_id(target_peer)
        expected = rt.find_closest(target_id, count=3)
        self.assertEqual([n.peer_id for n in result], [n.peer_id for n in expected])


if __name__ == '__main__':
    unittest.main()
