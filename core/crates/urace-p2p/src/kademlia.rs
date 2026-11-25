//! Kademlia routing table — R-6, BEP 5 DHT compatible.
//!
//! 256-bucket routing table (SHA-256 node IDs), K=20, α=3.
//! Matches `kademlia.py` logic exactly for routing-table compatibility with
//! Python peers during the transition period.
//!
//! Network I/O is NOT in this module — the routing table is local-only.
//! Transport uses the existing peer_exchange RPC path (Python) or the
//! `mainline` crate DHT socket (Rust) during R-7.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::VecDeque;
use std::time::{SystemTime, UNIX_EPOCH};

pub const K_BUCKET_SIZE: usize = 20;
pub const ALPHA: usize = 3;
pub const NODE_ID_BITS: usize = 256;

pub fn peer_id_to_node_id(peer_id: &str) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(peer_id.as_bytes());
    hasher.finalize().into()
}

pub fn xor_distance(a: &[u8; 32], b: &[u8; 32]) -> [u8; 32] {
    let mut out = [0u8; 32];
    for i in 0..32 {
        out[i] = a[i] ^ b[i];
    }
    out
}

pub fn bucket_index(own_id: &[u8; 32], other_id: &[u8; 32]) -> usize {
    let dist = xor_distance(own_id, other_id);
    // leading zero bits in dist = how close; bucket = (bit_length - 1) of dist, or 0.
    for (byte_idx, &byte) in dist.iter().enumerate() {
        if byte != 0 {
            let bit_pos = 7 - byte.leading_zeros() as usize;
            return byte_idx * 8 + bit_pos;
        }
    }
    0
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeInfo {
    pub peer_id: String,
    /// node_id serialised as hex string for JSON compatibility.
    #[serde(
        serialize_with = "serialize_node_id",
        deserialize_with = "deserialize_node_id"
    )]
    pub node_id: [u8; 32],
    pub endpoint: String,
    pub last_seen_secs: f64,
}

fn serialize_node_id<S>(node_id: &[u8; 32], s: S) -> Result<S::Ok, S::Error>
where
    S: serde::Serializer,
{
    s.serialize_str(&hex::encode(node_id))
}

fn deserialize_node_id<'de, D>(d: D) -> Result<[u8; 32], D::Error>
where
    D: serde::Deserializer<'de>,
{
    use serde::de::Error;
    let s = String::deserialize(d)?;
    let bytes = hex::decode(&s).map_err(D::Error::custom)?;
    bytes
        .try_into()
        .map_err(|_| D::Error::custom("expected 32 bytes"))
}

impl NodeInfo {
    pub fn new(peer_id: impl Into<String>, endpoint: impl Into<String>) -> Self {
        let peer_id = peer_id.into();
        let node_id = peer_id_to_node_id(&peer_id);
        let last_seen_secs = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
        NodeInfo {
            peer_id,
            node_id,
            endpoint: endpoint.into(),
            last_seen_secs,
        }
    }

    pub fn touch(&mut self) {
        self.last_seen_secs = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
    }
}

/// A single Kademlia k-bucket (up to K=20 nodes, LRU eviction).
pub struct KBucket {
    nodes: VecDeque<NodeInfo>,
    k: usize,
}

impl KBucket {
    pub fn new(k: usize) -> Self {
        KBucket {
            nodes: VecDeque::with_capacity(k),
            k,
        }
    }

    /// Add or refresh a node. New entries appended at tail (MRU). Full → evict head (LRU).
    pub fn add(&mut self, node: NodeInfo) {
        // If already present, remove and re-append (refresh).
        if let Some(pos) = self.nodes.iter().position(|n| n.peer_id == node.peer_id) {
            self.nodes.remove(pos);
        }
        if self.nodes.len() >= self.k {
            self.nodes.pop_front(); // evict LRU
        }
        self.nodes.push_back(node);
    }

    pub fn remove(&mut self, peer_id: &str) {
        self.nodes.retain(|n| n.peer_id != peer_id);
    }

    pub fn nodes(&self) -> &VecDeque<NodeInfo> {
        &self.nodes
    }

    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    pub fn is_full(&self) -> bool {
        self.nodes.len() >= self.k
    }
}

/// 256-bucket Kademlia routing table.
pub struct KademliaTable {
    own_id: [u8; 32],
    buckets: Vec<KBucket>,
}

impl KademliaTable {
    pub fn new(own_peer_id: &str) -> Self {
        let own_id = peer_id_to_node_id(own_peer_id);
        let buckets = (0..NODE_ID_BITS)
            .map(|_| KBucket::new(K_BUCKET_SIZE))
            .collect();
        KademliaTable { own_id, buckets }
    }

    pub fn add(&mut self, node: NodeInfo) {
        if node.node_id == self.own_id {
            return; // never add self
        }
        let idx = bucket_index(&self.own_id, &node.node_id);
        self.buckets[idx].add(node);
    }

    pub fn remove(&mut self, peer_id: &str) {
        let node_id = peer_id_to_node_id(peer_id);
        let idx = bucket_index(&self.own_id, &node_id);
        self.buckets[idx].remove(peer_id);
    }

    /// Find the `k` closest nodes to `target_id` by XOR distance.
    pub fn closest(&self, target_id: &[u8; 32], k: usize) -> Vec<&NodeInfo> {
        let mut all: Vec<&NodeInfo> = self.buckets.iter().flat_map(|b| b.nodes().iter()).collect();
        all.sort_by_key(|n| xor_distance(&n.node_id, target_id));
        all.into_iter().take(k).collect()
    }

    pub fn total_nodes(&self) -> usize {
        self.buckets.iter().map(|b| b.len()).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_and_find_closest() {
        let mut table = KademliaTable::new("self-peer");
        for i in 0..10u32 {
            table.add(NodeInfo::new(
                format!("peer-{i}"),
                format!("127.0.0.1:1000{i}"),
            ));
        }
        assert_eq!(table.total_nodes(), 10);
        let target = peer_id_to_node_id("peer-5");
        let closest = table.closest(&target, 3);
        assert_eq!(closest.len(), 3);
        // The first result should be peer-5 itself (distance 0).
        assert_eq!(closest[0].peer_id, "peer-5");
    }

    #[test]
    fn bucket_lru_eviction() {
        let mut bucket = KBucket::new(3);
        for i in 0..4u32 {
            bucket.add(NodeInfo::new(format!("p{i}"), "127.0.0.1:0"));
        }
        assert_eq!(bucket.len(), 3);
        // LRU (p0) was evicted.
        assert!(!bucket.nodes().iter().any(|n| n.peer_id == "p0"));
    }

    #[test]
    fn self_not_added() {
        let mut table = KademliaTable::new("self-peer");
        table.add(NodeInfo::new("self-peer", "127.0.0.1:0"));
        assert_eq!(table.total_nodes(), 0);
    }
}
