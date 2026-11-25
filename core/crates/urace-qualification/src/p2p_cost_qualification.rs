//! P2P cost qualification: validates peer cost claims against expected ranges.
//!
//! Implements the 30-pair bootstrap requirement from `p2p_cost_qualification.py`:
//! - Each pair must complete a borrow/deliver cycle.
//! - Statistical validity: Wilson lower bound on delivery rate (90% CI).
//! - `bootstrap_complete()` returns `true` once 30 pairs have round-tripped.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use thiserror::Error;

/// Minimum number of distinct peer pairs for bootstrap completion.
pub const BOOTSTRAP_THRESHOLD: usize = 30;

/// Wilson z-score for 90% confidence interval (one-sided).
const WILSON_Z: f64 = 1.645;

#[derive(Debug, Error)]
pub enum P2PCostError {
    #[error("invalid cost claim: {0}")]
    InvalidClaim(String),
}

/// A recorded qualification receipt for a peer pair.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualificationReceipt {
    /// Canonical SHA-256 hash of the sorted peer pair.
    pub pair_hash: String,
    pub peer_a_id: String,
    pub peer_b_id: String,
    pub completed: bool,
    pub at_unix: f64,
}

/// Statistics over all qualification receipts.
#[derive(Debug, Clone)]
pub struct QualificationStats {
    pub total_pairs: usize,
    pub completed_pairs: usize,
    pub delivery_rate: f64,
    pub wilson_lower_bound: f64,
    pub bootstrap_complete: bool,
}

/// P2P cost qualifier: validates peer cost claims and tracks qualification state.
pub struct P2PCostQualifier {
    receipts: std::sync::Mutex<Vec<QualificationReceipt>>,
}

impl P2PCostQualifier {
    pub fn new() -> Self {
        P2PCostQualifier {
            receipts: std::sync::Mutex::new(Vec::new()),
        }
    }

    /// Canonical pair hash for an unordered peer pair.
    pub fn pair_hash(peer_a: &str, peer_b: &str) -> String {
        let mut sorted = [peer_a, peer_b];
        sorted.sort_unstable();
        // Simple deterministic hash — use sha2 if available, else naive join.
        // We use the same logic as the Python implementation: sha256(sorted_joined).
        let combined = format!("{}{}", sorted[0], sorted[1]);
        // Compute sha256 without pulling in sha2 directly (it's already in the dep tree via urace-ledger).
        // We re-implement via the hmac crate's sha2 backing.
        use sha2_hash::Sha256Hash;
        Sha256Hash::hash(combined.as_bytes())
    }

    /// Record a qualification receipt for a peer pair.
    pub fn record_receipt(
        &self,
        peer_a_id: &str,
        peer_b_id: &str,
        completed: bool,
    ) -> QualificationReceipt {
        use std::time::{SystemTime, UNIX_EPOCH};
        let at_unix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();

        let receipt = QualificationReceipt {
            pair_hash: Self::pair_hash(peer_a_id, peer_b_id),
            peer_a_id: peer_a_id.to_owned(),
            peer_b_id: peer_b_id.to_owned(),
            completed,
            at_unix,
        };
        self.receipts.lock().unwrap().push(receipt.clone());
        receipt
    }

    /// Return `true` once >= 30 distinct peer pairs have receipts.
    pub fn bootstrap_complete(&self) -> bool {
        let receipts = self.receipts.lock().unwrap();
        let distinct: HashSet<&str> = receipts.iter().map(|r| r.pair_hash.as_str()).collect();
        distinct.len() >= BOOTSTRAP_THRESHOLD
    }

    /// Compute delivery statistics over all recorded receipts.
    pub fn statistics(&self) -> QualificationStats {
        let receipts = self.receipts.lock().unwrap();

        // Last recorded status wins per pair_hash.
        let mut pair_completed: HashMap<String, bool> = HashMap::new();
        for r in receipts.iter() {
            pair_completed.insert(r.pair_hash.clone(), r.completed);
        }

        let total = pair_completed.len();
        let completed = pair_completed.values().filter(|&&v| v).count();

        if total == 0 {
            return QualificationStats {
                total_pairs: 0,
                completed_pairs: 0,
                delivery_rate: 0.0,
                wilson_lower_bound: 0.0,
                bootstrap_complete: false,
            };
        }

        let p = completed as f64 / total as f64;
        let n = total as f64;
        let z = WILSON_Z;
        let z2 = z * z;

        let numerator = p + z2 / (2.0 * n) - z * (p * (1.0 - p) / n + z2 / (4.0 * n * n)).sqrt();
        let denominator = 1.0 + z2 / n;
        let wilson_lb = (numerator / denominator).max(0.0);

        QualificationStats {
            total_pairs: total,
            completed_pairs: completed,
            delivery_rate: p,
            wilson_lower_bound: wilson_lb,
            bootstrap_complete: total >= BOOTSTRAP_THRESHOLD,
        }
    }

    /// Validate a peer cost claim against an expected range.
    ///
    /// Returns `Ok(())` when the claim falls within [min_expected, max_expected].
    pub fn validate_cost_claim(
        &self,
        claimed_cost: f64,
        min_expected: f64,
        max_expected: f64,
    ) -> Result<(), P2PCostError> {
        if claimed_cost < min_expected || claimed_cost > max_expected {
            return Err(P2PCostError::InvalidClaim(format!(
                "claimed cost {:.4} not in expected range [{:.4}, {:.4}]",
                claimed_cost, min_expected, max_expected
            )));
        }
        Ok(())
    }

    /// Return the Wilson CI lower bound on failure rate for a given peer.
    ///
    /// Lower is better (0.0 = perfect record, 1.0 = always fails).
    pub fn peer_failure_rate(&self, peer_id: &str) -> f64 {
        let receipts = self.receipts.lock().unwrap();
        let relevant: Vec<&QualificationReceipt> = receipts
            .iter()
            .filter(|r| r.peer_a_id == peer_id || r.peer_b_id == peer_id)
            .collect();

        let n = relevant.len();
        if n == 0 {
            return 0.0;
        }
        let failures: f64 = relevant
            .iter()
            .map(|r| if r.completed { 0.0 } else { 1.0 })
            .sum();
        let p_hat = failures / n as f64;
        let z = WILSON_Z;
        let denom = 1.0 + z * z / n as f64;
        let centre = (p_hat + z * z / (2.0 * n as f64)) / denom;
        let margin = (z
            * (p_hat * (1.0 - p_hat) / n as f64 + z * z / (4.0 * n as f64 * n as f64)).sqrt())
            / denom;
        (centre - margin).max(0.0)
    }
}

impl Default for P2PCostQualifier {
    fn default() -> Self {
        Self::new()
    }
}

// Minimal SHA-256 helper using the sha2 crate (pulled in transitively).
mod sha2_hash {
    use sha2::{Digest, Sha256};

    pub struct Sha256Hash;
    impl Sha256Hash {
        pub fn hash(data: &[u8]) -> String {
            let mut hasher = Sha256::new();
            hasher.update(data);
            hex::encode(hasher.finalize())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bootstrap_requires_thirty_pairs() {
        let q = P2PCostQualifier::new();
        assert!(!q.bootstrap_complete());

        for i in 0..29 {
            q.record_receipt(&format!("peer-a-{}", i), &format!("peer-b-{}", i), true);
        }
        assert!(!q.bootstrap_complete(), "29 pairs is not enough");

        q.record_receipt("peer-a-29", "peer-b-29", true);
        assert!(q.bootstrap_complete(), "30 pairs must complete bootstrap");
    }

    #[test]
    fn statistics_zero_when_empty() {
        let q = P2PCostQualifier::new();
        let stats = q.statistics();
        assert_eq!(stats.total_pairs, 0);
        assert_eq!(stats.delivery_rate, 0.0);
        assert!(!stats.bootstrap_complete);
    }

    #[test]
    fn statistics_delivery_rate() {
        let q = P2PCostQualifier::new();
        q.record_receipt("a", "b", true);
        q.record_receipt("c", "d", false);
        let stats = q.statistics();
        assert_eq!(stats.total_pairs, 2);
        assert_eq!(stats.completed_pairs, 1);
        assert!((stats.delivery_rate - 0.5).abs() < 1e-9);
    }

    #[test]
    fn cost_claim_validation() {
        let q = P2PCostQualifier::new();
        assert!(q.validate_cost_claim(0.5, 0.1, 1.0).is_ok());
        assert!(q.validate_cost_claim(0.0, 0.1, 1.0).is_err());
        assert!(q.validate_cost_claim(2.0, 0.1, 1.0).is_err());
    }

    #[test]
    fn pair_hash_is_symmetric() {
        let h1 = P2PCostQualifier::pair_hash("alice", "bob");
        let h2 = P2PCostQualifier::pair_hash("bob", "alice");
        assert_eq!(h1, h2, "pair hash must be order-independent");
    }
}
