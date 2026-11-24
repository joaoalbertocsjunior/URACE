//! Peer reputation — scoring, trust weights, federation discount.
//!
//! Ported from `ledger_reputation.py`.
//!
//! # Design
//! Reputation is append-only: every update is a `ReputationEntry` written to a
//! `Journal`. The current score for a peer is the sum of all deltas in the log —
//! no mutable state is kept separately.
//!
//! # Cross-network discount
//! `discount(score, factor)` computes a discounted reputation score for
//! federation cross-network comparisons (lower trust → lower weight).

use crate::journal::{Journal, JournalError};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::path::Path;
use thiserror::Error;

/// A single reputation update.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReputationEntry {
    pub peer_id: String,
    /// Signed delta — positive = reputation gain, negative = penalty.
    pub delta: f64,
    pub reason: String,
    pub at: String,
}

#[derive(Debug, Error)]
pub enum ReputationError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
}

/// Append-only reputation store backed by a `Journal`.
pub struct ReputationStore {
    journal: Journal,
}

impl ReputationStore {
    /// Open (or create) a reputation store at `path`.
    pub fn open(path: impl AsRef<Path>, hmac_key: [u8; 32]) -> Result<Self, ReputationError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(ReputationStore { journal })
    }

    /// Append a reputation delta for `peer_id`.
    pub fn update(
        &self,
        peer_id: impl Into<String>,
        delta: f64,
        reason: impl Into<String>,
    ) -> Result<ReputationEntry, ReputationError> {
        let peer_id = peer_id.into();
        let reason = reason.into();
        let at = now_iso();
        self.journal.append(
            "REPUTATION_DELTA",
            json!({
                "peer_id": peer_id,
                "delta": delta,
                "reason": reason,
                "at": at,
            }),
        )?;
        Ok(ReputationEntry { peer_id, delta, reason, at })
    }

    /// Compute the current reputation score for `peer_id` as the sum of all deltas.
    pub fn score(&self, peer_id: &str) -> Result<f64, ReputationError> {
        let entries = self.journal.verify_integrity()?;
        let total = entries
            .iter()
            .filter(|e| e.kind == "REPUTATION_DELTA")
            .filter_map(|e| {
                let pid = e.payload.get("peer_id")?.as_str()?;
                if pid == peer_id {
                    e.payload.get("delta")?.as_f64()
                } else {
                    None
                }
            })
            .sum();
        Ok(total)
    }

    /// All entries for a peer (in journal order).
    pub fn entries_for(&self, peer_id: &str) -> Result<Vec<ReputationEntry>, ReputationError> {
        let rows = self.journal.verify_integrity()?;
        let out = rows
            .into_iter()
            .filter(|e| e.kind == "REPUTATION_DELTA")
            .filter_map(|e| {
                let pid = e.payload.get("peer_id")?.as_str()?;
                if pid != peer_id {
                    return None;
                }
                Some(ReputationEntry {
                    peer_id: pid.to_owned(),
                    delta: e.payload.get("delta")?.as_f64()?,
                    reason: e.payload.get("reason")?.as_str().unwrap_or("").to_owned(),
                    at: e.payload.get("at")?.as_str().unwrap_or("").to_owned(),
                })
            })
            .collect();
        Ok(out)
    }

    /// All known peer IDs with at least one reputation entry.
    pub fn all_peers(&self) -> Result<Vec<String>, ReputationError> {
        let rows = self.journal.verify_integrity()?;
        let mut peers: std::collections::HashSet<String> = std::collections::HashSet::new();
        for e in &rows {
            if e.kind == "REPUTATION_DELTA" {
                if let Some(pid) = e.payload.get("peer_id").and_then(|v| v.as_str()) {
                    peers.insert(pid.to_owned());
                }
            }
        }
        let mut v: Vec<String> = peers.into_iter().collect();
        v.sort();
        Ok(v)
    }
}

/// Apply a cross-network reputation discount.
///
/// Used for federation cross-network comparisons where the remote network
/// has lower trust than the local network. `factor ∈ [0.0, 1.0]`.
/// Returns `score * factor`, floored at 0.
pub fn discount(score: f64, factor: f64) -> f64 {
    let f = factor.clamp(0.0, 1.0);
    (score * f).max(0.0)
}

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| format!("{:.3}", d.as_secs_f64()))
        .unwrap_or_else(|_| "0".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"urace-rep-key---32bytes---------";

    fn open(dir: &tempfile::TempDir) -> ReputationStore {
        ReputationStore::open(dir.path().join("rep.jsonl"), KEY).unwrap()
    }

    #[test]
    fn score_starts_at_zero() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        assert_eq!(store.score("unknown-peer").unwrap(), 0.0);
    }

    #[test]
    fn update_accumulates() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("peer-1", 1.5, "quality_pass").unwrap();
        store.update("peer-1", 0.5, "delivery_success").unwrap();
        store.update("peer-1", -0.3, "late_delivery").unwrap();
        let score = store.score("peer-1").unwrap();
        assert!((score - 1.7).abs() < 1e-9, "expected 1.7, got {score}");
    }

    #[test]
    fn scores_are_isolated_per_peer() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("peer-1", 10.0, "great").unwrap();
        store.update("peer-2", 2.0, "ok").unwrap();
        assert!((store.score("peer-1").unwrap() - 10.0).abs() < 1e-9);
        assert!((store.score("peer-2").unwrap() - 2.0).abs() < 1e-9);
    }

    #[test]
    fn entries_for_peer_ordered() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("peer-1", 1.0, "first").unwrap();
        store.update("peer-2", 5.0, "unrelated").unwrap();
        store.update("peer-1", 2.0, "second").unwrap();
        let entries = store.entries_for("peer-1").unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].reason, "first");
        assert_eq!(entries[1].reason, "second");
    }

    #[test]
    fn all_peers_returns_sorted() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("zz-peer", 1.0, "r").unwrap();
        store.update("aa-peer", 1.0, "r").unwrap();
        store.update("mm-peer", 1.0, "r").unwrap();
        let peers = store.all_peers().unwrap();
        assert_eq!(peers, vec!["aa-peer", "mm-peer", "zz-peer"]);
    }

    #[test]
    fn negative_score_possible() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("peer-1", -5.0, "penalty").unwrap();
        assert!((store.score("peer-1").unwrap() - (-5.0)).abs() < 1e-9);
    }

    #[test]
    fn discount_applies_factor() {
        assert!((discount(10.0, 0.5) - 5.0).abs() < 1e-9);
        assert!((discount(10.0, 1.0) - 10.0).abs() < 1e-9);
        assert!((discount(10.0, 0.0) - 0.0).abs() < 1e-9);
    }

    #[test]
    fn discount_clamps_factor() {
        // factor > 1 clamped to 1
        assert!((discount(10.0, 2.0) - 10.0).abs() < 1e-9);
        // factor < 0 clamped to 0
        assert!((discount(10.0, -1.0) - 0.0).abs() < 1e-9);
    }

    #[test]
    fn discount_floors_at_zero() {
        // negative score × positive factor → still floored at 0
        assert!((discount(-5.0, 0.5) - 0.0).abs() < 1e-9);
    }
}
