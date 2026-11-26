//! M40 — Commit-reveal bidding.
//!
//! Bidders first commit a hash of `(amount_ucr || bidder_id || work_id || nonce)`.
//! They must reveal the plaintext within `reveal_window_secs` or forfeit
//! `NO_REVEAL_PENALTY_UCR` base units.  This prevents last-second sniping and
//! Sybil-amplified front-running.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use thiserror::Error;

/// Penalty applied to peers who committed but failed to reveal by deadline.
/// 100 000 base units = 0.001 UNIT.
pub const NO_REVEAL_PENALTY_UCR: i64 = 100_000;

// ── M30 — Bid validity window ─────────────────────────────────────────────────

/// Default bid validity window in seconds (1 hour).
pub const BID_VALIDITY_WINDOW_SECS: u64 = 3_600;

/// Returns `true` iff the bid is still within its validity window at `now_secs`.
pub fn is_bid_valid(commitment: &BidCommitment, now_secs: u64) -> bool {
    now_secs <= commitment.committed_at_secs + commitment.reveal_window_secs
}

#[derive(Debug, Error)]
pub enum CommitRevealError {
    #[error("commitment not found for work_id '{0}' peer '{1}'")]
    NotFound(String, String),
    #[error("reveal hash mismatch")]
    HashMismatch,
    #[error("reveal window expired")]
    WindowExpired,
    #[error("already revealed")]
    AlreadyRevealed,
}

/// A sealed bid commitment stored on-chain before the reveal phase.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BidCommitment {
    pub work_id: String,
    pub bidder_peer_id: String,
    /// Hex-encoded SHA-256 of `(amount_ucr_le || bidder_id || work_id || nonce_hex)`.
    pub commitment_hash: String,
    /// Unix timestamp (seconds) when the commitment was recorded.
    pub committed_at_secs: u64,
    /// How long (seconds) the bidder has to reveal.  Default: 3600 (one cycle).
    pub reveal_window_secs: u64,
}

/// The plaintext bid revealed after the commitment phase.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BidReveal {
    pub work_id: String,
    pub bidder_peer_id: String,
    pub amount_ucr: i64,
    /// 32-byte random nonce as hex (64 hex chars).
    pub nonce_hex: String,
}

impl BidCommitment {
    /// Compute the commitment hash from plaintext bid parameters.
    ///
    /// Hash input: `SHA-256(amount_le_bytes || bidder_id || work_id || nonce_hex)`
    pub fn compute_hash(
        amount_ucr: i64,
        bidder_id: &str,
        work_id: &str,
        nonce_hex: &str,
    ) -> String {
        let mut h = Sha256::new();
        h.update(amount_ucr.to_le_bytes());
        h.update(bidder_id.as_bytes());
        h.update(work_id.as_bytes());
        h.update(nonce_hex.as_bytes());
        hex::encode(h.finalize())
    }
}

/// In-memory commit-reveal store.
///
/// For production use, commitments should also be persisted to a journal;
/// this implementation is intentionally stateless across restarts (the reveal
/// window enforcement requires the committed_at timestamp).
pub struct CommitRevealStore {
    /// work_id → (bidder_id → commitment)
    commitments: HashMap<String, HashMap<String, BidCommitment>>,
    /// work_id → (bidder_id → reveal)
    revealed: HashMap<String, HashMap<String, BidReveal>>,
}

impl CommitRevealStore {
    pub fn new() -> Self {
        CommitRevealStore {
            commitments: HashMap::new(),
            revealed: HashMap::new(),
        }
    }

    /// Store a bid commitment.  If the same `(work_id, bidder_id)` pair has
    /// already committed, the new commitment silently replaces it (allowing
    /// correction before the reveal phase opens).
    ///
    /// M30: If `commitment.reveal_window_secs == 0`, it is set to
    /// `BID_VALIDITY_WINDOW_SECS` before storing.
    pub fn commit(&mut self, mut commitment: BidCommitment) {
        if commitment.reveal_window_secs == 0 {
            commitment.reveal_window_secs = BID_VALIDITY_WINDOW_SECS;
        }
        self.commitments
            .entry(commitment.work_id.clone())
            .or_default()
            .insert(commitment.bidder_peer_id.clone(), commitment);
    }

    /// Reveal a bid and validate the commitment hash.
    ///
    /// Returns the revealed `amount_ucr` on success.
    ///
    /// # Errors
    /// - `NotFound`       — no matching commitment exists
    /// - `AlreadyRevealed`— this peer already revealed for this work_id
    /// - `WindowExpired`  — `now_secs > committed_at + reveal_window`
    /// - `HashMismatch`   — the plaintext does not match the committed hash
    pub fn reveal(
        &mut self,
        reveal: BidReveal,
        now_secs: u64,
    ) -> Result<i64, CommitRevealError> {
        // 1. Find commitment.
        let commitment = self
            .commitments
            .get(&reveal.work_id)
            .and_then(|m| m.get(&reveal.bidder_peer_id))
            .ok_or_else(|| {
                CommitRevealError::NotFound(
                    reveal.work_id.clone(),
                    reveal.bidder_peer_id.clone(),
                )
            })?
            .clone();

        // 2. Check not already revealed.
        if self
            .revealed
            .get(&reveal.work_id)
            .and_then(|m| m.get(&reveal.bidder_peer_id))
            .is_some()
        {
            return Err(CommitRevealError::AlreadyRevealed);
        }

        // 3. Check reveal window not expired.
        if now_secs > commitment.committed_at_secs + commitment.reveal_window_secs {
            return Err(CommitRevealError::WindowExpired);
        }

        // 4. Verify hash.
        let expected_hash = BidCommitment::compute_hash(
            reveal.amount_ucr,
            &reveal.bidder_peer_id,
            &reveal.work_id,
            &reveal.nonce_hex,
        );
        if expected_hash != commitment.commitment_hash {
            return Err(CommitRevealError::HashMismatch);
        }

        // 5. Store reveal and return amount.
        let amount = reveal.amount_ucr;
        self.revealed
            .entry(reveal.work_id.clone())
            .or_default()
            .insert(reveal.bidder_peer_id.clone(), reveal);

        Ok(amount)
    }

    /// Returns `true` if the commitment exists and the reveal window has
    /// already elapsed for `now_secs`, regardless of whether a reveal occurred.
    pub fn is_expired(&self, work_id: &str, peer_id: &str, now_secs: u64) -> bool {
        self.commitments
            .get(work_id)
            .and_then(|m| m.get(peer_id))
            .map(|c| now_secs > c.committed_at_secs + c.reveal_window_secs)
            .unwrap_or(false)
    }

    /// Collect the no-reveal penalty from all peers who committed but did not
    /// reveal for `work_id` and whose window has expired by `now_secs`.
    ///
    /// Returns a list of `(peer_id, penalty_ucr)` pairs.
    pub fn collect_expired_penalties(
        &self,
        work_id: &str,
        now_secs: u64,
    ) -> Vec<(String, i64)> {
        let Some(commitments) = self.commitments.get(work_id) else {
            return vec![];
        };
        commitments
            .iter()
            .filter(|(peer_id, commitment)| {
                // Window must have expired …
                now_secs > commitment.committed_at_secs + commitment.reveal_window_secs
                    // … and the peer must not have revealed.
                    && self
                        .revealed
                        .get(work_id)
                        .and_then(|m| m.get(*peer_id))
                        .is_none()
            })
            .map(|(peer_id, _)| (peer_id.clone(), NO_REVEAL_PENALTY_UCR))
            .collect()
    }

    /// Return the reveal for `(work_id, peer_id)` if it exists.
    pub fn get_reveal(&self, work_id: &str, peer_id: &str) -> Option<&BidReveal> {
        self.revealed
            .get(work_id)
            .and_then(|m| m.get(peer_id))
    }
}

impl Default for CommitRevealStore {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const WORK_ID: &str = "work-42";
    const PEER_ID: &str = "peer-alice";
    const AMOUNT: i64 = 500_000;
    const NONCE: &str = "aabbccdd00112233aabbccdd00112233aabbccdd00112233aabbccdd00112233";
    const COMMIT_TIME: u64 = 1_000_000;
    const WINDOW: u64 = 3600;

    fn make_commitment() -> BidCommitment {
        BidCommitment {
            work_id: WORK_ID.to_owned(),
            bidder_peer_id: PEER_ID.to_owned(),
            commitment_hash: BidCommitment::compute_hash(AMOUNT, PEER_ID, WORK_ID, NONCE),
            committed_at_secs: COMMIT_TIME,
            reveal_window_secs: WINDOW,
        }
    }

    fn make_reveal() -> BidReveal {
        BidReveal {
            work_id: WORK_ID.to_owned(),
            bidder_peer_id: PEER_ID.to_owned(),
            amount_ucr: AMOUNT,
            nonce_hex: NONCE.to_owned(),
        }
    }

    #[test]
    fn valid_commit_reveal() {
        let mut store = CommitRevealStore::new();
        store.commit(make_commitment());

        let now = COMMIT_TIME + 60; // well within window
        let amount = store.reveal(make_reveal(), now).unwrap();
        assert_eq!(amount, AMOUNT);
        assert!(store.get_reveal(WORK_ID, PEER_ID).is_some());
    }

    #[test]
    fn wrong_nonce_rejected() {
        let mut store = CommitRevealStore::new();
        store.commit(make_commitment());

        let mut bad_reveal = make_reveal();
        bad_reveal.nonce_hex = "deadbeef".to_owned();

        let err = store.reveal(bad_reveal, COMMIT_TIME + 60).unwrap_err();
        assert!(
            matches!(err, CommitRevealError::HashMismatch),
            "expected HashMismatch, got: {err}"
        );
    }

    #[test]
    fn expired_reveal_rejected() {
        let mut store = CommitRevealStore::new();
        store.commit(make_commitment());

        // Attempt reveal after window has closed.
        let now = COMMIT_TIME + WINDOW + 1;
        let err = store.reveal(make_reveal(), now).unwrap_err();
        assert!(
            matches!(err, CommitRevealError::WindowExpired),
            "expected WindowExpired, got: {err}"
        );
    }

    #[test]
    fn double_reveal_rejected() {
        let mut store = CommitRevealStore::new();
        store.commit(make_commitment());

        let now = COMMIT_TIME + 60;
        store.reveal(make_reveal(), now).unwrap();

        let err = store.reveal(make_reveal(), now).unwrap_err();
        assert!(
            matches!(err, CommitRevealError::AlreadyRevealed),
            "expected AlreadyRevealed, got: {err}"
        );
    }

    #[test]
    fn penalty_collected_for_no_reveal() {
        let mut store = CommitRevealStore::new();
        store.commit(make_commitment());

        // A second peer also commits but won't reveal.
        let peer2 = "peer-bob";
        store.commit(BidCommitment {
            work_id: WORK_ID.to_owned(),
            bidder_peer_id: peer2.to_owned(),
            commitment_hash: BidCommitment::compute_hash(300_000, peer2, WORK_ID, NONCE),
            committed_at_secs: COMMIT_TIME,
            reveal_window_secs: WINDOW,
        });

        // Alice reveals in time; Bob does not.
        let now_inside = COMMIT_TIME + 60;
        store.reveal(make_reveal(), now_inside).unwrap();

        // Advance past window.
        let now_expired = COMMIT_TIME + WINDOW + 1;

        let penalties = store.collect_expired_penalties(WORK_ID, now_expired);
        assert_eq!(penalties.len(), 1, "only Bob should be penalised");
        assert_eq!(penalties[0].0, peer2);
        assert_eq!(penalties[0].1, NO_REVEAL_PENALTY_UCR);
    }

    // M30 bid validity tests

    #[test]
    fn bid_valid_within_window() {
        let c = make_commitment();
        assert!(is_bid_valid(&c, COMMIT_TIME + WINDOW - 1));
        assert!(is_bid_valid(&c, COMMIT_TIME)); // start of window
    }

    #[test]
    fn bid_expired_outside_window() {
        let c = make_commitment();
        assert!(!is_bid_valid(&c, COMMIT_TIME + WINDOW + 1));
    }

    #[test]
    fn commit_with_zero_window_uses_default() {
        let mut store = CommitRevealStore::new();
        // A zero reveal_window_secs should be replaced with BID_VALIDITY_WINDOW_SECS.
        // We verify indirectly: is_expired at committed_at + BID_VALIDITY_WINDOW_SECS + 1
        // must return true, but at committed_at + BID_VALIDITY_WINDOW_SECS - 1 must return false.
        let hash = BidCommitment::compute_hash(100, "p", "w", "nonce00");
        let c = BidCommitment {
            work_id: "w".to_owned(),
            bidder_peer_id: "p".to_owned(),
            commitment_hash: hash,
            committed_at_secs: 1000,
            reveal_window_secs: 0, // should become BID_VALIDITY_WINDOW_SECS
        };
        store.commit(c);
        assert!(!store.is_expired("w", "p", 1000 + BID_VALIDITY_WINDOW_SECS - 1));
        assert!(store.is_expired("w", "p", 1000 + BID_VALIDITY_WINDOW_SECS + 1));
    }

    #[test]
    fn not_found_returns_error() {
        let mut store = CommitRevealStore::new();
        let err = store
            .reveal(make_reveal(), COMMIT_TIME + 60)
            .unwrap_err();
        assert!(
            matches!(err, CommitRevealError::NotFound(..)),
            "expected NotFound, got: {err}"
        );
    }
}
