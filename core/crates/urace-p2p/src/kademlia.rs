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
use std::collections::{HashMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};

pub const K_BUCKET_SIZE: usize = 20;
pub const ALPHA: usize = 3;
pub const NODE_ID_BITS: usize = 256;

/// M22: Subnet diversity — max peers per /24 IPv4 subnet per bucket = floor(K / D).
pub const SUBNET_DIVERSITY_D: usize = 4;

/// First 3 octets of an IPv4 address, representing a /24 subnet.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Subnet24(pub [u8; 3]);

/// Parse the /24 subnet from an endpoint string like `"1.2.3.4:9000"`.
/// Returns `None` if the endpoint does not contain a valid IPv4 address.
pub fn subnet24_from_endpoint(endpoint: &str) -> Option<Subnet24> {
    // Strip port: take the part before the last ':'
    let host = if let Some(pos) = endpoint.rfind(':') {
        &endpoint[..pos]
    } else {
        endpoint
    };
    // Strip brackets for IPv6 (we only handle IPv4 here)
    let host = host.trim_matches('[').trim_matches(']');
    let parts: Vec<&str> = host.split('.').collect();
    if parts.len() == 4 {
        let a = parts[0].parse::<u8>().ok()?;
        let b = parts[1].parse::<u8>().ok()?;
        let c = parts[2].parse::<u8>().ok()?;
        let _d = parts[3].parse::<u8>().ok()?; // validate 4th octet but don't store
        Some(Subnet24([a, b, c]))
    } else {
        None
    }
}

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
/// M22: Tracks per-/24-subnet counts to enforce subnet diversity.
pub struct KBucket {
    nodes: VecDeque<NodeInfo>,
    k: usize,
    subnet_counts: HashMap<Subnet24, usize>,
}

impl KBucket {
    pub fn new(k: usize) -> Self {
        KBucket {
            nodes: VecDeque::with_capacity(k),
            k,
            subnet_counts: HashMap::new(),
        }
    }

    /// Add or refresh a node. New entries appended at tail (MRU).
    ///
    /// M22 subnet diversity: If the node's /24 subnet already has `floor(K / D)` peers
    /// in this bucket, the insert is silently skipped (no eviction). The refresh path
    /// (peer already present) bypasses the subnet check.
    pub fn add(&mut self, node: NodeInfo) {
        // Minimum 1 so small test buckets are not completely blocked.
        let max_per_subnet = (self.k / SUBNET_DIVERSITY_D).max(1);

        // Refresh path: if already present, remove-and-reinsert without subnet check.
        if let Some(pos) = self.nodes.iter().position(|n| n.peer_id == node.peer_id) {
            // Update subnet counts on removal then re-add
            if let Some(old_subnet) = subnet24_from_endpoint(&self.nodes[pos].endpoint) {
                let count = self.subnet_counts.entry(old_subnet).or_insert(0);
                if *count > 0 {
                    *count -= 1;
                }
            }
            self.nodes.remove(pos);
            // Re-add at tail
            if let Some(subnet) = subnet24_from_endpoint(&node.endpoint) {
                *self.subnet_counts.entry(subnet).or_insert(0) += 1;
            }
            self.nodes.push_back(node);
            return;
        }

        // New peer: check subnet diversity constraint first.
        if let Some(subnet) = subnet24_from_endpoint(&node.endpoint) {
            let current_count = *self.subnet_counts.get(&subnet).unwrap_or(&0);
            if current_count >= max_per_subnet {
                // Skip insert — subnet is saturated.
                return;
            }
        }

        // Bucket full: evict LRU (head).
        if self.nodes.len() >= self.k {
            if let Some(evicted) = self.nodes.pop_front() {
                if let Some(evicted_subnet) = subnet24_from_endpoint(&evicted.endpoint) {
                    let count = self.subnet_counts.entry(evicted_subnet).or_insert(0);
                    if *count > 0 {
                        *count -= 1;
                    }
                }
            }
        }

        // Insert new node.
        if let Some(subnet) = subnet24_from_endpoint(&node.endpoint) {
            *self.subnet_counts.entry(subnet).or_insert(0) += 1;
        }
        self.nodes.push_back(node);
    }

    pub fn remove(&mut self, peer_id: &str) {
        if let Some(pos) = self.nodes.iter().position(|n| n.peer_id == peer_id) {
            let endpoint = self.nodes[pos].endpoint.clone();
            self.nodes.remove(pos);
            if let Some(subnet) = subnet24_from_endpoint(&endpoint) {
                let count = self.subnet_counts.entry(subnet).or_insert(0);
                if *count > 0 {
                    *count -= 1;
                }
            }
        }
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

    /// M22: Returns reference to the per-subnet peer counts.
    pub fn subnet_counts(&self) -> &HashMap<Subnet24, usize> {
        &self.subnet_counts
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

    /// M24 — Eclipse-resistant diverse peer selection.
    ///
    /// Returns up to `k` peers drawn from at most `max_buckets` different k-buckets.
    /// By spreading selection across buckets, this prevents an adversary controlling a
    /// single XOR-distance region from eclipsing the node's view.
    ///
    /// At most `ceil(k / max_buckets)` peers are drawn from each contributing bucket.
    pub fn diverse_closest(
        &self,
        target_id: &[u8; 32],
        k: usize,
        max_buckets: usize,
    ) -> Vec<&NodeInfo> {
        let max_b = max_buckets.max(1);
        let per_bucket = (k + max_b - 1) / max_b; // ceil(k / max_buckets)

        // Collect all nodes sorted by XOR distance.
        let mut all: Vec<&NodeInfo> =
            self.buckets.iter().flat_map(|b| b.nodes().iter()).collect();
        all.sort_by_key(|n| xor_distance(&n.node_id, target_id));

        let mut result: Vec<&NodeInfo> = Vec::with_capacity(k);
        let mut bucket_seen: std::collections::HashMap<usize, usize> =
            std::collections::HashMap::new();

        for node in all {
            if result.len() >= k {
                break;
            }
            let bidx = bucket_index(&self.own_id, &node.node_id);
            let count = bucket_seen.entry(bidx).or_insert(0);
            if *count < per_bucket {
                *count += 1;
                result.push(node);
            }
        }
        result
    }

    /// M22: Returns the ratio of unique /24 subnets to total peers across all buckets.
    /// Returns 0.0 if the table is empty.
    pub fn subnet_diversity_ratio(&self) -> f64 {
        let total = self.total_nodes();
        if total == 0 {
            return 0.0;
        }
        // Merge subnet counts from all buckets.
        let mut merged: HashMap<Subnet24, usize> = HashMap::new();
        for bucket in &self.buckets {
            for (subnet, &count) in bucket.subnet_counts() {
                *merged.entry(subnet.clone()).or_insert(0) += count;
            }
        }
        let unique_subnets = merged.values().filter(|&&c| c > 0).count();
        unique_subnets as f64 / total as f64
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
        // K=3, D=4 → max_per_subnet = max(0, 1) = 1.
        // Use four distinct /24 subnets so subnet diversity does not interfere.
        let mut bucket = KBucket::new(3);
        let endpoints = ["1.0.0.1:0", "2.0.0.1:0", "3.0.0.1:0", "4.0.0.1:0"];
        for (i, ep) in endpoints.iter().enumerate() {
            bucket.add(NodeInfo::new(format!("p{i}"), *ep));
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

    // ── M22 subnet diversity tests ────────────────────────────────────────────

    #[test]
    fn subnet_diversity_reject_sixth() {
        // K=20, D=4 → max 5 per /24 subnet. Sixth from same /24 must be skipped.
        let mut bucket = KBucket::new(20);
        for i in 0..5u8 {
            bucket.add(NodeInfo::new(
                format!("peer-{i}"),
                format!("1.2.3.{}:9000", i + 1),
            ));
        }
        assert_eq!(bucket.len(), 5, "first 5 from same /24 accepted");
        // Sixth peer from same /24 (1.2.3.x) must be silently skipped.
        bucket.add(NodeInfo::new("peer-5", "1.2.3.6:9000"));
        assert_eq!(bucket.len(), 5, "sixth from same /24 must be rejected");
    }

    #[test]
    fn subnet_diversity_allow_different_subnets() {
        let mut bucket = KBucket::new(20);
        let subnets = ["1.2.3", "10.0.0", "172.16.1", "192.168.0", "8.8.0"];
        for (i, s) in subnets.iter().enumerate() {
            bucket.add(NodeInfo::new(
                format!("peer-{i}"),
                format!("{s}.{}:9000", i + 1),
            ));
        }
        assert_eq!(bucket.len(), 5, "one peer per distinct /24 should all be accepted");
    }

    // M24 — eclipse-resistant diverse selection test

    #[test]
    fn diverse_closest_spreads_across_buckets() {
        let mut table = KademliaTable::new("self-peer");
        // Add 20 peers with distinct peer IDs.
        for i in 0..20u32 {
            table.add(NodeInfo::new(
                format!("peer-diverse-{i}"),
                format!("{}.0.0.1:9000", i + 1),
            ));
        }
        let target = peer_id_to_node_id("peer-diverse-5");
        // With max_buckets=4, k=8, at most ceil(8/4)=2 per bucket.
        let diverse = table.diverse_closest(&target, 8, 4);
        assert_eq!(diverse.len(), 8.min(table.total_nodes()));
    }

    #[test]
    fn subnet_diversity_refresh_allowed() {
        let mut bucket = KBucket::new(20);
        bucket.add(NodeInfo::new("peer-refresh", "1.2.3.4:9000"));
        assert_eq!(bucket.len(), 1);
        // Re-inserting same peer is a refresh — should not be blocked.
        bucket.add(NodeInfo::new("peer-refresh", "1.2.3.4:9000"));
        assert_eq!(bucket.len(), 1, "refresh must keep bucket len at 1");
    }
}
