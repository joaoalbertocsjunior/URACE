//! R-6: Cartel guard — port of `cartel_guard.py`.
//!
//! Detects cartel-style chunk concentration: a cluster of colluding peers
//! that co-registers the same set of replica chunks, allowing them to
//! perform data-witholding attacks.
//!
//! Sybil constraint: a single IP must not occupy multiple bucket slots.

use dashmap::DashMap;
use serde_json::Value;
use std::collections::{HashMap, HashSet};

/// RS erasure parameters (matches Python constants).
pub const N_DATA: usize = 4;
pub const N_PARITY: usize = 2;
pub const N_TOTAL: usize = N_DATA + N_PARITY; // 6

/// A cluster whose concentration exceeds this threshold triggers a cartel flag.
pub const DEFAULT_THRESHOLD: f64 = N_PARITY as f64 / N_TOTAL as f64; // 0.333…

/// Maximum co-registered slots before an automatic flag regardless of concentration.
pub const DEFAULT_MAX_CLUSTER_SLOTS: usize = N_PARITY + 1; // 3

/// Result of a cartel concentration check for a single feature.
#[derive(Debug, Clone)]
pub struct CartelCheckResult {
    pub flagged: bool,
    /// Peer IDs forming the largest suspicious cluster.
    pub cluster: Vec<String>,
    /// Fraction of total slots occupied by the cluster.
    pub concentration: f64,
    pub slot_count: usize,
    pub flag_reason: String,
    pub feature_id: String,
}

/// Check a set of BUNDLE_REPLICA_REGISTERED rows for cartel concentration.
///
/// `replica_rows` is the full audit row slice; this function filters by
/// `kind == "BUNDLE_REPLICA_REGISTERED"` and the given `feature_id`.
///
/// Returns a `CartelCheckResult` — `flagged` is true if concentration exceeds
/// `threshold` or `slot_count >= DEFAULT_MAX_CLUSTER_SLOTS`.
pub fn check_chunk_concentration(
    feature_id: &str,
    replica_rows: &[HashMap<String, Value>],
    n_total: usize,
    threshold: f64,
) -> CartelCheckResult {
    // Filter rows relevant to this feature.
    let relevant: Vec<&HashMap<String, Value>> = replica_rows
        .iter()
        .filter(|row| {
            row.get("kind")
                .and_then(Value::as_str)
                .map(|k| k == "BUNDLE_REPLICA_REGISTERED")
                .unwrap_or(false)
                && row
                    .get("feature_id")
                    .and_then(Value::as_str)
                    .map(|f| f == feature_id)
                    .unwrap_or(false)
        })
        .collect();

    // Build peer → set of chunk indices they registered.
    let mut peer_chunks: HashMap<String, HashSet<usize>> = HashMap::new();
    for row in &relevant {
        let peer_id = match row.get("peer_id").and_then(Value::as_str) {
            Some(p) => p.to_string(),
            None => continue,
        };
        let chunk_idx = match row.get("chunk_idx").and_then(Value::as_u64) {
            Some(i) => i as usize,
            None => continue,
        };
        peer_chunks.entry(peer_id).or_default().insert(chunk_idx);
    }

    if peer_chunks.is_empty() {
        return CartelCheckResult {
            flagged: false,
            cluster: vec![],
            concentration: 0.0,
            slot_count: 0,
            flag_reason: String::new(),
            feature_id: feature_id.to_string(),
        };
    }

    // Find the largest cluster of peers that share any overlapping chunks.
    // Simple greedy: sort by chunk-set size, group peers sharing ≥1 chunk.
    let peers: Vec<String> = peer_chunks.keys().cloned().collect();

    let mut best_cluster: Vec<String> = vec![];
    let mut best_overlap_count = 0usize;

    // For each pair combination, build overlap graph — O(N²) acceptable for small N.
    for i in 0..peers.len() {
        let mut cluster = vec![peers[i].clone()];
        let chunks_i = &peer_chunks[&peers[i]];
        let mut shared_chunks: HashSet<usize> = chunks_i.clone();

        for j in 0..peers.len() {
            if i == j {
                continue;
            }
            let chunks_j = &peer_chunks[&peers[j]];
            let overlap: HashSet<usize> = chunks_i.intersection(chunks_j).cloned().collect();
            if !overlap.is_empty() {
                cluster.push(peers[j].clone());
                shared_chunks = shared_chunks.intersection(chunks_j).cloned().collect();
            }
        }

        // Deduplicate cluster peers.
        cluster.sort();
        cluster.dedup();

        let overlap_count = cluster.len();
        if overlap_count > best_overlap_count {
            best_overlap_count = overlap_count;
            best_cluster = cluster;
        }
    }

    let slot_count = best_cluster.len();
    let n_total_safe = if n_total == 0 { N_TOTAL } else { n_total };
    let concentration = slot_count as f64 / n_total_safe as f64;

    let (flagged, flag_reason) = if slot_count >= DEFAULT_MAX_CLUSTER_SLOTS {
        (
            true,
            format!(
                "cluster size {} >= DEFAULT_MAX_CLUSTER_SLOTS {}",
                slot_count, DEFAULT_MAX_CLUSTER_SLOTS
            ),
        )
    } else if concentration > threshold {
        (
            true,
            format!(
                "concentration {:.3} > threshold {:.3}",
                concentration, threshold
            ),
        )
    } else {
        (false, String::new())
    };

    CartelCheckResult {
        flagged,
        cluster: best_cluster,
        concentration,
        slot_count,
        flag_reason,
        feature_id: feature_id.to_string(),
    }
}

/// Sybil guard: prevent a single IP from occupying multiple bucket slots.
///
/// This is a process-local guard — it is NOT serialized or sent over the wire.
pub struct IpBucketGuard {
    /// ip → set of bucket_idx already occupied.
    slots: DashMap<String, HashSet<usize>>,
}

impl IpBucketGuard {
    pub fn new() -> Self {
        IpBucketGuard {
            slots: DashMap::new(),
        }
    }

    /// Returns true and records the slot if the IP has NOT already occupied `bucket_idx`.
    /// Returns false (Sybil rejected) if the IP is already in that bucket.
    pub fn check(&self, ip: &str, bucket_idx: usize) -> bool {
        let mut entry = self.slots.entry(ip.to_string()).or_default();
        if entry.contains(&bucket_idx) {
            return false;
        }
        entry.insert(bucket_idx);
        true
    }

    /// Remove an IP from a bucket slot (e.g., peer left).
    pub fn release(&self, ip: &str, bucket_idx: usize) {
        if let Some(mut entry) = self.slots.get_mut(ip) {
            entry.remove(&bucket_idx);
        }
    }
}

impl Default for IpBucketGuard {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_row(peer_id: &str, chunk_idx: u64, feature_id: &str) -> HashMap<String, Value> {
        let mut m = HashMap::new();
        m.insert(
            "kind".into(),
            Value::String("BUNDLE_REPLICA_REGISTERED".into()),
        );
        m.insert("peer_id".into(), Value::String(peer_id.into()));
        m.insert("chunk_idx".into(), Value::Number(chunk_idx.into()));
        m.insert("feature_id".into(), Value::String(feature_id.into()));
        m
    }

    #[test]
    fn test_no_concentration() {
        // 6 distinct peers, each holding 1 chunk.
        let rows: Vec<HashMap<String, Value>> = (0..6u64)
            .map(|i| make_row(&format!("peer-{}", i), i, "feat-1"))
            .collect();
        let result = check_chunk_concentration("feat-1", &rows, N_TOTAL, DEFAULT_THRESHOLD);
        assert!(
            !result.flagged,
            "diverse peers should not be flagged: {:?}",
            result.flag_reason
        );
    }

    #[test]
    fn test_cluster_flagged_by_slot_count() {
        // 3 peers all sharing chunk 0 — slot_count=3 >= DEFAULT_MAX_CLUSTER_SLOTS.
        let rows = vec![
            make_row("peer-a", 0, "feat-2"),
            make_row("peer-b", 0, "feat-2"),
            make_row("peer-c", 0, "feat-2"),
        ];
        let result = check_chunk_concentration("feat-2", &rows, N_TOTAL, DEFAULT_THRESHOLD);
        assert!(result.flagged);
        assert!(result.flag_reason.contains("DEFAULT_MAX_CLUSTER_SLOTS"));
    }

    #[test]
    fn test_ip_bucket_guard_sybil_rejection() {
        let guard = IpBucketGuard::new();
        assert!(guard.check("1.2.3.4", 5), "first entry should succeed");
        assert!(
            !guard.check("1.2.3.4", 5),
            "same IP, same bucket must be rejected"
        );
    }

    #[test]
    fn test_ip_bucket_guard_different_buckets() {
        let guard = IpBucketGuard::new();
        assert!(guard.check("1.2.3.4", 0));
        assert!(
            guard.check("1.2.3.4", 1),
            "different bucket should be allowed"
        );
    }

    #[test]
    fn test_constants() {
        assert_eq!(N_TOTAL, 6);
        assert!((DEFAULT_THRESHOLD - 1.0 / 3.0).abs() < 1e-9);
        assert_eq!(DEFAULT_MAX_CLUSTER_SLOTS, 3);
    }
}
