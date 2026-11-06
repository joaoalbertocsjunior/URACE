"""Kademlia-style DHT routing table for artifact chunk discovery.

Local routing table only — no network I/O. Network transport uses existing
peer_exchange RPC system. Maintains 256 k-buckets (one per XOR bit-distance
magnitude), each holding up to K=20 node entries sorted by last-seen time.

Chunk routing key: sha256(artifact_sha256 + ':chunk:' + str(chunk_idx))
Nodes responsible for a chunk = nodes closest to routing key by XOR metric.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

SCHEMA = 'urace-kademlia-v1'
K_BUCKET_SIZE = 20
ALPHA = 3            # concurrency factor
NODE_ID_BITS = 256   # SHA-256 based IDs


def peer_id_to_node_id(peer_id: str) -> int:
    """SHA-256(peer_id.encode()) → 256-bit int."""
    digest = hashlib.sha256(peer_id.encode()).hexdigest()
    return int(digest, 16)


def xor_distance(a: int, b: int) -> int:
    """XOR metric."""
    return a ^ b


def bucket_index(own_id: int, other_id: int) -> int:
    """Which bucket (0..255)? = (own_id XOR other_id).bit_length() - 1. Returns 0 if same."""
    dist = own_id ^ other_id
    if dist == 0:
        return 0
    return dist.bit_length() - 1


@dataclass
class NodeInfo:
    peer_id: str
    node_id: int
    endpoint: str
    last_seen: float = field(default_factory=time.time)


class KBucket:
    """Holds up to k nodes. add() places new at tail (MRU). If full, evicts head (LRU)."""

    def __init__(self, k: int = K_BUCKET_SIZE) -> None:
        self.k = k
        self._nodes: List[NodeInfo] = []

    def add(self, node: NodeInfo) -> bool:
        """Add or refresh node. Returns True if added/refreshed, False if dropped."""
        # Remove existing entry if present (refresh)
        existing_idx = None
        for i, n in enumerate(self._nodes):
            if n.peer_id == node.peer_id:
                existing_idx = i
                break

        if existing_idx is not None:
            self._nodes.pop(existing_idx)
            self._nodes.append(node)
            return True

        if len(self._nodes) < self.k:
            self._nodes.append(node)
            return True

        # Bucket full — evict LRU (head)
        self._nodes.pop(0)
        self._nodes.append(node)
        return True

    def remove(self, peer_id: str) -> None:
        self._nodes = [n for n in self._nodes if n.peer_id != peer_id]

    def __len__(self) -> int:
        return len(self._nodes)

    def nodes(self) -> List[NodeInfo]:
        return list(self._nodes)


class RoutingTable:
    def __init__(self, own_peer_id: str, k: int = K_BUCKET_SIZE) -> None:
        self.own_peer_id = own_peer_id
        self.own_id = peer_id_to_node_id(own_peer_id)
        self.k = k
        self._buckets: List[KBucket] = [KBucket(k) for _ in range(NODE_ID_BITS)]

    def add(self, peer_id: str, endpoint: str = '') -> None:
        """Add peer to routing table. Ignores own peer_id."""
        if peer_id == self.own_peer_id:
            return
        node_id = peer_id_to_node_id(peer_id)
        idx = bucket_index(self.own_id, node_id)
        node = NodeInfo(peer_id=peer_id, node_id=node_id, endpoint=endpoint)
        self._buckets[idx].add(node)

    def remove(self, peer_id: str) -> None:
        if peer_id == self.own_peer_id:
            return
        node_id = peer_id_to_node_id(peer_id)
        idx = bucket_index(self.own_id, node_id)
        self._buckets[idx].remove(peer_id)

    def find_closest(self, target_id: int, count: int = K_BUCKET_SIZE) -> List[NodeInfo]:
        """Sort all known nodes by XOR distance to target_id, return top count."""
        all_nodes: List[NodeInfo] = []
        for bucket in self._buckets:
            all_nodes.extend(bucket.nodes())
        all_nodes.sort(key=lambda n: xor_distance(n.node_id, target_id))
        return all_nodes[:count]

    def find_closest_for_peer(self, target_peer_id: str, count: int = K_BUCKET_SIZE) -> List[NodeInfo]:
        target_id = peer_id_to_node_id(target_peer_id)
        return self.find_closest(target_id, count)

    def chunk_holders(self, artifact_sha256: str, chunk_idx: int, count: int = ALPHA) -> List[NodeInfo]:
        """routing key = sha256(f'{artifact_sha256}:chunk:{chunk_idx}')"""
        key_str = f'{artifact_sha256}:chunk:{chunk_idx}'
        key_hex = hashlib.sha256(key_str.encode()).hexdigest()
        target_id = int(key_hex, 16)
        return self.find_closest(target_id, count)

    def size(self) -> int:
        return sum(len(b) for b in self._buckets)

    def to_dict(self) -> dict:
        nodes = []
        for bucket in self._buckets:
            for n in bucket.nodes():
                nodes.append({
                    'peer_id': n.peer_id,
                    'endpoint': n.endpoint,
                    'last_seen': n.last_seen,
                })
        return {
            'schema': SCHEMA,
            'own_peer_id': self.own_peer_id,
            'nodes': nodes,
        }

    @classmethod
    def from_dict(cls, data: dict, k: int = K_BUCKET_SIZE) -> 'RoutingTable':
        own_peer_id = data['own_peer_id']
        rt = cls(own_peer_id, k)
        for entry in data.get('nodes', []):
            peer_id = entry['peer_id']
            endpoint = entry.get('endpoint', '')
            last_seen = entry.get('last_seen', time.time())
            node_id = peer_id_to_node_id(peer_id)
            idx = bucket_index(rt.own_id, node_id)
            node = NodeInfo(peer_id=peer_id, node_id=node_id, endpoint=endpoint, last_seen=last_seen)
            rt._buckets[idx].add(node)
        return rt

    def save(self, path) -> None:
        """Persist to JSON file."""
        p = Path(path)
        p.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path, own_peer_id: str, k: int = K_BUCKET_SIZE) -> 'RoutingTable':
        """Load from JSON file, or return fresh RoutingTable if file not found."""
        p = Path(path)
        if not p.exists():
            return cls(own_peer_id, k)
        data = json.loads(p.read_text())
        return cls.from_dict(data, k)
