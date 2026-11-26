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
    /// M02 — optional key_id binding; when set, this update is tied to a
    /// specific signing key (prevents score transfer across key rotations).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub key_id: Option<String>,
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
        self.update_with_key(peer_id, delta, reason, None)
    }

    /// M02 — Append a key-bound reputation delta for `peer_id`.
    ///
    /// When `key_id` is `Some`, the entry is bound to that signing key.
    /// Callers should supply the peer's current active key so that reputation
    /// cannot be transferred across key rotations.
    pub fn update_with_key(
        &self,
        peer_id: impl Into<String>,
        delta: f64,
        reason: impl Into<String>,
        key_id: Option<String>,
    ) -> Result<ReputationEntry, ReputationError> {
        let peer_id = peer_id.into();
        let reason = reason.into();
        let at = now_iso();
        let mut payload = json!({
            "peer_id": peer_id,
            "delta": delta,
            "reason": reason,
            "at": at,
        });
        if let Some(ref k) = key_id {
            payload["key_id"] = serde_json::Value::String(k.clone());
        }
        self.journal.append("REPUTATION_DELTA", payload)?;
        Ok(ReputationEntry { peer_id, delta, reason, at, key_id })
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
                    key_id: e.payload.get("key_id").and_then(|v| v.as_str()).map(|s| s.to_owned()),
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

// ---------------------------------------------------------------------------
// M13 — Reputation decay
// ---------------------------------------------------------------------------

/// Default fraction of the current score removed per daemon cycle (1 %).
pub const DEFAULT_DECAY_RATE: f64 = 0.01;

impl ReputationStore {
    /// Append a negative delta equal to `decay_rate × current_score` for
    /// `peer_id`.
    ///
    /// Returns the appended `ReputationEntry`, or `None` if the peer's score
    /// is already ≤ 0 or the computed decay is negligibly small (< 1e-9).
    pub fn apply_decay(
        &self,
        peer_id: &str,
        decay_rate: f64,
    ) -> Result<Option<ReputationEntry>, ReputationError> {
        let current = self.score(peer_id)?;
        if current <= 0.0 {
            return Ok(None);
        }
        let decay_amount = current * decay_rate.abs();
        if decay_amount < 1e-9 {
            return Ok(None);
        }
        let entry = self.update(peer_id, -decay_amount, "decay")?;
        Ok(Some(entry))
    }

    /// Apply decay to every peer with a positive score.
    ///
    /// Returns the number of peers whose score was reduced.
    pub fn apply_decay_all(&self, decay_rate: f64) -> Result<usize, ReputationError> {
        let peers = self.all_peers()?;
        let mut count = 0usize;
        for peer_id in &peers {
            if self.apply_decay(peer_id, decay_rate)?.is_some() {
                count += 1;
            }
        }
        Ok(count)
    }
}

// ── M21 — Usage-based reputation credit ──────────────────────────────────────

/// Compute the reputation delta earned for completing `tasks_completed` tasks
/// with an average score of `avg_score` ∈ [0.0, 1.0].
///
/// Returns `tasks_completed × clamp(avg_score, 0, 1) × 0.1`.
/// A perfect task earns 0.1 reputation units.
pub fn usage_reputation_delta(tasks_completed: u64, avg_score: f64) -> f64 {
    tasks_completed as f64 * avg_score.clamp(0.0, 1.0) * 0.1
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

// ---------------------------------------------------------------------------
// M01 — Peer reputation genesis
// ---------------------------------------------------------------------------

/// Neutral starting reputation for a new peer (prevents both cold-start bias
/// and sybil bootstrapping with inflated scores).
pub const GENESIS_REPUTATION_SCORE: f64 = 0.5;

/// Record created when a peer first joins — anchors the reputation chain.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerGenesisRecord {
    pub peer_id: String,
    pub genesis_score: f64,
    pub at_unix: u64,
}

impl PeerGenesisRecord {
    pub fn new(peer_id: impl Into<String>, at_unix: u64) -> Self {
        PeerGenesisRecord {
            peer_id: peer_id.into(),
            genesis_score: GENESIS_REPUTATION_SCORE,
            at_unix,
        }
    }
}

/// Create the initial `ReputationEntry` for a new peer at `GENESIS_REPUTATION_SCORE`.
///
/// The entry has an empty `reason` string and no `key_id`, mirroring what
/// `ReputationStore::update` would produce for a fresh peer.
pub fn bootstrap_reputation(peer_id: &str, at_unix: u64) -> ReputationEntry {
    ReputationEntry {
        peer_id: peer_id.to_owned(),
        delta: GENESIS_REPUTATION_SCORE,
        reason: "genesis".to_owned(),
        at: at_unix.to_string(),
        key_id: None,
    }
}

// ---------------------------------------------------------------------------
// M35 — Reputation laundering guard
// ---------------------------------------------------------------------------

/// A reputation credit transferred between peers.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReputationTransfer {
    pub from_peer: String,
    pub to_peer: String,
    pub delta: f64,
    pub at_unix: u64,
}

/// Detection window for reputation laundering cycles (24 hours).
pub const LAUNDERING_CYCLE_WINDOW_SECS: u64 = 86_400;

/// Detect laundering: peer X → peer Y → peer X within `window_secs`.
///
/// A "laundering cycle" is when both X→Y and Y→X transfers occur within the
/// window. Returns a deduplicated list of suspected launderer peer IDs
/// (both endpoints of each detected cycle).
pub fn detect_reputation_laundering(
    transfers: &[ReputationTransfer],
    window_secs: u64,
) -> Vec<String> {
    use std::collections::{HashMap, HashSet};

    // For each (from, to) pair, collect timestamps within the window.
    // We use the latest timestamp in the slice as "now" to decide what's
    // within the window, matching the wash-trade detection approach.
    let now = transfers.iter().map(|t| t.at_unix).max().unwrap_or(0);
    let cutoff = now.saturating_sub(window_secs);

    // Build a set of (from, to) pairs that have at least one transfer in-window.
    let mut pairs: HashMap<(String, String), bool> = HashMap::new();
    for t in transfers {
        if t.at_unix >= cutoff {
            pairs.insert((t.from_peer.clone(), t.to_peer.clone()), true);
        }
    }

    let mut suspects: HashSet<String> = HashSet::new();
    for (from, to) in pairs.keys() {
        // Check if the reverse direction also exists in-window.
        if pairs.contains_key(&(to.clone(), from.clone())) {
            suspects.insert(from.clone());
            suspects.insert(to.clone());
        }
    }

    let mut v: Vec<String> = suspects.into_iter().collect();
    v.sort();
    v
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

    // M13 — decay tests

    #[test]
    fn decay_reduces_positive_score() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("peer-d", 10.0, "initial").unwrap();
        let entry = store
            .apply_decay("peer-d", DEFAULT_DECAY_RATE)
            .unwrap()
            .expect("should produce a decay entry");
        // decay delta should be –0.1 (1 % of 10.0)
        assert!((entry.delta - (-0.1)).abs() < 1e-9, "delta = {}", entry.delta);
        let score = store.score("peer-d").unwrap();
        // 10.0 – 0.1 = 9.9
        assert!((score - 9.9).abs() < 1e-9, "score = {score}");
    }

    #[test]
    fn decay_no_effect_on_zero() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        // peer with no entries → score 0
        let result = store.apply_decay("peer-e", DEFAULT_DECAY_RATE).unwrap();
        assert!(result.is_none(), "no decay entry expected for zero score");

        // explicitly set to zero via cancelling entries
        store.update("peer-f", 5.0, "up").unwrap();
        store.update("peer-f", -5.0, "down").unwrap();
        let result = store.apply_decay("peer-f", DEFAULT_DECAY_RATE).unwrap();
        assert!(result.is_none());
    }

    #[test]
    fn decay_all_applies_to_all_peers() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("alpha", 10.0, "r").unwrap();
        store.update("beta", 20.0, "r").unwrap();
        store.update("gamma", -5.0, "r").unwrap(); // negative — should not decay

        let count = store.apply_decay_all(DEFAULT_DECAY_RATE).unwrap();
        assert_eq!(count, 2, "only alpha and beta have positive scores");

        let s_alpha = store.score("alpha").unwrap();
        let s_beta = store.score("beta").unwrap();
        assert!((s_alpha - 9.9).abs() < 1e-9, "alpha = {s_alpha}");
        assert!((s_beta - 19.8).abs() < 1e-9, "beta = {s_beta}");
    }

    // M02 — key-id binding tests

    #[test]
    fn key_id_bound_entry_stored_and_retrieved() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store
            .update_with_key("peer-k", 5.0, "keyed", Some("key-abc123".to_owned()))
            .unwrap();
        let entries = store.entries_for("peer-k").unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].key_id, Some("key-abc123".to_owned()));
    }

    #[test]
    fn unkeyed_entry_has_no_key_id() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("peer-nk", 1.0, "plain").unwrap();
        let entries = store.entries_for("peer-nk").unwrap();
        assert_eq!(entries[0].key_id, None);
    }

    // M21 — usage-based reputation delta test

    #[test]
    fn usage_reputation_delta_full_score() {
        let delta = usage_reputation_delta(10, 1.0);
        assert!((delta - 1.0).abs() < 1e-9, "10 tasks @ 1.0 = 1.0, got {delta}");
    }

    #[test]
    fn usage_reputation_delta_partial_score() {
        let delta = usage_reputation_delta(5, 0.8);
        assert!((delta - 0.4).abs() < 1e-9, "5 tasks @ 0.8 = 0.4, got {delta}");
    }

    #[test]
    fn decay_rate_clamp_uses_abs() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        store.update("peer-g", 10.0, "initial").unwrap();
        // passing a negative rate: abs() is applied, so result is same as +0.1
        let entry = store
            .apply_decay("peer-g", -0.1)
            .unwrap()
            .expect("should decay");
        assert!((entry.delta - (-1.0)).abs() < 1e-9, "delta = {}", entry.delta);
    }

    // M01 — Peer reputation genesis tests

    #[test]
    fn genesis_score_is_neutral() {
        let entry = bootstrap_reputation("new-peer", 1_000);
        assert!(
            (entry.delta - GENESIS_REPUTATION_SCORE).abs() < 1e-9,
            "genesis delta should be GENESIS_REPUTATION_SCORE, got {}",
            entry.delta
        );
    }

    #[test]
    fn genesis_entry_has_no_history() {
        let entry = bootstrap_reputation("fresh-peer", 2_000);
        assert_eq!(entry.peer_id, "fresh-peer");
        assert_eq!(entry.reason, "genesis");
        assert!(entry.key_id.is_none(), "genesis entry must have no key_id");
    }

    #[test]
    fn two_distinct_peers_get_independent_genesis_entries() {
        let e1 = bootstrap_reputation("peer-alpha", 1_000);
        let e2 = bootstrap_reputation("peer-beta", 2_000);
        assert_ne!(e1.peer_id, e2.peer_id);
        // Both start at the same neutral score
        assert!((e1.delta - GENESIS_REPUTATION_SCORE).abs() < 1e-9);
        assert!((e2.delta - GENESIS_REPUTATION_SCORE).abs() < 1e-9);
        // But their timestamps differ
        assert_ne!(e1.at, e2.at);
    }

    #[test]
    fn peer_genesis_record_uses_genesis_score() {
        let rec = PeerGenesisRecord::new("p1", 42_000);
        assert_eq!(rec.peer_id, "p1");
        assert!((rec.genesis_score - GENESIS_REPUTATION_SCORE).abs() < 1e-9);
        assert_eq!(rec.at_unix, 42_000);
    }

    // M35 — Reputation laundering guard tests

    #[test]
    fn laundering_cycle_within_window_flagged() {
        let transfers = vec![
            ReputationTransfer { from_peer: "X".into(), to_peer: "Y".into(), delta: 1.0, at_unix: 1000 },
            ReputationTransfer { from_peer: "Y".into(), to_peer: "X".into(), delta: 0.9, at_unix: 2000 },
        ];
        let suspects = detect_reputation_laundering(&transfers, LAUNDERING_CYCLE_WINDOW_SECS);
        assert!(suspects.contains(&"X".to_string()), "X should be flagged");
        assert!(suspects.contains(&"Y".to_string()), "Y should be flagged");
    }

    #[test]
    fn one_way_transfer_is_clean() {
        let transfers = vec![
            ReputationTransfer { from_peer: "X".into(), to_peer: "Y".into(), delta: 1.0, at_unix: 1000 },
        ];
        let suspects = detect_reputation_laundering(&transfers, LAUNDERING_CYCLE_WINDOW_SECS);
        assert!(suspects.is_empty(), "one-way transfer must not be flagged");
    }

    #[test]
    fn transfers_outside_window_not_flagged() {
        // X→Y at t=0, Y→X at t=100000 (> 86400s window from the latest event at t=100000)
        // But the cutoff is now - window = 100000 - 86400 = 13600
        // X→Y is at t=0, which is < 13600, so outside the window
        let transfers = vec![
            ReputationTransfer { from_peer: "X".into(), to_peer: "Y".into(), delta: 1.0, at_unix: 0 },
            ReputationTransfer { from_peer: "Y".into(), to_peer: "X".into(), delta: 0.9, at_unix: 100_000 },
        ];
        let suspects = detect_reputation_laundering(&transfers, LAUNDERING_CYCLE_WINDOW_SECS);
        // Only Y→X is in the window; X→Y is not, so no cycle detected.
        assert!(suspects.is_empty(), "stale first leg must not form a cycle");
    }
}
