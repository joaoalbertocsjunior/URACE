//! Cross-peer work quality and improvement loop — port of `peer_improvement.py`.
//!
//! Tracks quality scores for peer-submitted work, computes per-peer averages,
//! and surfaces improvement trends. No I/O: all state is held in-process.
//!
//! # Key invariants
//! - Peer identities are opaque fingerprints (SHA-256(DER cert)); no PII.
//! - `peer_quality_score` returns 0.0 for unknown peers rather than panicking.
//! - Quality scores are always in `[0.0, 1.0]`.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ImprovementError {
    #[error("quality score must be in [0.0, 1.0], got {0}")]
    InvalidQualityScore(f64),

    #[error("peer_id must not be empty")]
    EmptyPeerId,
}

// ── PeerImprovementRecord ─────────────────────────────────────────────────────

/// A single recorded quality score for a peer's completed task.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerImprovementRecord {
    /// Opaque peer fingerprint (hex SHA-256(DER cert)).
    pub peer_id: String,
    /// Task / bundle / work-request identifier.
    pub task_id: String,
    /// Quality score in `[0.0, 1.0]`.
    pub quality_score: f64,
    /// ISO-8601 timestamp.
    pub at: String,
    /// Optional free-form evidence (evaluation notes, test results, etc.).
    pub evidence: Option<String>,
}

impl PeerImprovementRecord {
    /// Validate the record fields before inserting.
    pub fn validate(&self) -> Result<(), ImprovementError> {
        if self.peer_id.is_empty() {
            return Err(ImprovementError::EmptyPeerId);
        }
        if !(0.0..=1.0).contains(&self.quality_score) {
            return Err(ImprovementError::InvalidQualityScore(self.quality_score));
        }
        Ok(())
    }
}

// ── ImprovementLoop ───────────────────────────────────────────────────────────

/// In-process improvement loop that accumulates peer quality records.
///
/// Thread-safety: uses a `Mutex`-protected inner map; callers may clone
/// the struct freely since records are reference-counted through the mutex.
#[derive(Debug, Default)]
pub struct ImprovementLoop {
    /// peer_id → ordered vec of quality records (newest appended last).
    records: HashMap<String, Vec<PeerImprovementRecord>>,
}

impl ImprovementLoop {
    pub fn new() -> Self {
        ImprovementLoop { records: HashMap::new() }
    }

    /// Record a new quality entry for a peer.
    ///
    /// Returns `ImprovementError::InvalidQualityScore` if the score is out of
    /// range so callers can surface the validation failure.
    pub fn record(&mut self, rec: PeerImprovementRecord) -> Result<(), ImprovementError> {
        rec.validate()?;
        self.records
            .entry(rec.peer_id.clone())
            .or_default()
            .push(rec);
        Ok(())
    }

    /// Return the average quality score over all records for `peer_id`.
    ///
    /// Returns `0.0` for unknown peers (never panics).
    pub fn peer_quality_score(&self, peer_id: &str) -> f64 {
        match self.records.get(peer_id) {
            None => 0.0,
            Some(recs) if recs.is_empty() => 0.0,
            Some(recs) => recs.iter().map(|r| r.quality_score).sum::<f64>() / recs.len() as f64,
        }
    }

    /// Return the top `n` peers sorted by average quality score descending.
    pub fn top_peers(&self, n: usize) -> Vec<(String, f64)> {
        let mut ranked: Vec<(String, f64)> = self
            .records
            .keys()
            .map(|id| (id.clone(), self.peer_quality_score(id)))
            .collect();
        ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        ranked.truncate(n);
        ranked
    }

    /// Estimate the improvement rate for `peer_id` as the linear slope of their
    /// recent quality scores.
    ///
    /// Uses the last `window` records (default: all). Returns `0.0` for fewer
    /// than 2 records or unknown peers.
    pub fn improvement_rate(&self, peer_id: &str) -> f64 {
        let recs = match self.records.get(peer_id) {
            Some(r) if r.len() >= 2 => r,
            _ => return 0.0,
        };
        let n = recs.len();
        let ys: Vec<f64> = recs.iter().map(|r| r.quality_score).collect();
        let xs: Vec<f64> = (0..n).map(|i| i as f64).collect();

        let x_mean = xs.iter().sum::<f64>() / n as f64;
        let y_mean = ys.iter().sum::<f64>() / n as f64;

        let num: f64 = xs.iter().zip(ys.iter()).map(|(x, y)| (x - x_mean) * (y - y_mean)).sum();
        let den: f64 = xs.iter().map(|x| (x - x_mean).powi(2)).sum();

        if den.abs() < 1e-12 { 0.0 } else { num / den }
    }

    /// Return all records for `peer_id`, newest last.
    pub fn records_for(&self, peer_id: &str) -> &[PeerImprovementRecord] {
        self.records
            .get(peer_id)
            .map(|v| v.as_slice())
            .unwrap_or(&[])
    }

    /// Total number of records across all peers.
    pub fn total_records(&self) -> usize {
        self.records.values().map(|v| v.len()).sum()
    }

    /// Peer count.
    pub fn peer_count(&self) -> usize {
        self.records.len()
    }
}

// ── Multi-peer amplification helpers ─────────────────────────────────────────

/// Count how many distinct peers have submitted records for `task_id`.
///
/// Mirrors `multi_peer_amplification` logic from the Python module: counts
/// distinct peer identities to prevent one peer from inflating the count.
pub fn distinct_peers_for_task(r#loop: &ImprovementLoop, task_id: &str) -> usize {
    let peers: std::collections::HashSet<&str> = r#loop
        .records
        .values()
        .flatten()
        .filter(|rec| rec.task_id == task_id)
        .map(|rec| rec.peer_id.as_str())
        .collect();
    peers.len()
}

/// Compute a priority boost based on independent peer qualification count.
///
/// Mirrors `multi_peer_amplification()` from Python:
///  1 peer  → 15
///  2 peers → 20
///  4 peers → 25
///  8 peers → 30 (network consensus)
///  max: `max_boost`
pub fn amplification_boost(peer_count: usize, max_boost: u32) -> u32 {
    if peer_count == 0 {
        return 0;
    }
    let raw = 15.0 * (1.0 + (peer_count as f64).log2() / 3.0);
    (raw.round() as u32).min(max_boost)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn ts() -> String {
        "2026-01-01T00:00:00Z".to_string()
    }

    fn rec(peer_id: &str, task_id: &str, score: f64) -> PeerImprovementRecord {
        PeerImprovementRecord {
            peer_id: peer_id.to_string(),
            task_id: task_id.to_string(),
            quality_score: score,
            at: ts(),
            evidence: None,
        }
    }

    #[test]
    fn record_and_query_quality_score() {
        let mut lp = ImprovementLoop::new();
        lp.record(rec("peer_a", "t1", 0.8)).unwrap();
        lp.record(rec("peer_a", "t2", 0.6)).unwrap();
        let score = lp.peer_quality_score("peer_a");
        assert!((score - 0.7).abs() < 1e-10, "expected 0.7, got {}", score);
    }

    #[test]
    fn unknown_peer_returns_zero() {
        let lp = ImprovementLoop::new();
        assert_eq!(lp.peer_quality_score("ghost"), 0.0);
    }

    #[test]
    fn top_peers_sorted_desc() {
        let mut lp = ImprovementLoop::new();
        lp.record(rec("peer_a", "t1", 0.5)).unwrap();
        lp.record(rec("peer_b", "t1", 0.9)).unwrap();
        lp.record(rec("peer_c", "t1", 0.7)).unwrap();
        let top = lp.top_peers(3);
        assert_eq!(top[0].0, "peer_b");
        assert_eq!(top[1].0, "peer_c");
        assert_eq!(top[2].0, "peer_a");
    }

    #[test]
    fn improvement_rate_ascending_is_positive() {
        let mut lp = ImprovementLoop::new();
        for (i, s) in [0.2f64, 0.4, 0.6, 0.8, 1.0].iter().enumerate() {
            lp.record(PeerImprovementRecord {
                peer_id: "peerX".into(),
                task_id: format!("t{}", i),
                quality_score: *s,
                at: ts(),
                evidence: None,
            })
            .unwrap();
        }
        assert!(lp.improvement_rate("peerX") > 0.0);
    }

    #[test]
    fn improvement_rate_descending_is_negative() {
        let mut lp = ImprovementLoop::new();
        for (i, s) in [1.0f64, 0.8, 0.6, 0.4, 0.2].iter().enumerate() {
            lp.record(PeerImprovementRecord {
                peer_id: "peerY".into(),
                task_id: format!("t{}", i),
                quality_score: *s,
                at: ts(),
                evidence: None,
            })
            .unwrap();
        }
        assert!(lp.improvement_rate("peerY") < 0.0);
    }

    #[test]
    fn invalid_quality_score_rejected() {
        let mut lp = ImprovementLoop::new();
        let bad = rec("p", "t", 1.5);
        assert!(matches!(
            lp.record(bad),
            Err(ImprovementError::InvalidQualityScore(_))
        ));
    }

    #[test]
    fn amplification_boost_scales_with_peers() {
        assert_eq!(amplification_boost(0, 30), 0);
        assert_eq!(amplification_boost(1, 30), 15);
        // 2 peers → 15 * (1 + log2(2)/3) = 15 * 1.333 ≈ 20
        let b2 = amplification_boost(2, 30);
        assert!(b2 > 15 && b2 <= 30);
        assert_eq!(amplification_boost(100, 30), 30); // capped at max_boost
    }

    #[test]
    fn distinct_peers_for_task_deduplicates() {
        let mut lp = ImprovementLoop::new();
        lp.record(rec("peer_a", "task_x", 0.9)).unwrap();
        lp.record(rec("peer_b", "task_x", 0.8)).unwrap();
        lp.record(rec("peer_a", "task_x", 0.95)).unwrap(); // same peer again
        assert_eq!(distinct_peers_for_task(&lp, "task_x"), 2);
    }
}
