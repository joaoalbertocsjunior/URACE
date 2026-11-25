//! R-6: Consensus — port of `consensus.py`.
//!
//! Invariants:
//! - Supermajority = strict ceil(2N/3) — no single peer may determine outcome.
//! - `is_finalized` requires distinct peer votes on the SAME seal_hash.
//! - Vote deduplication: each peer_id may cast at most one vote per seal_hash.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

/// Returns the strict supermajority threshold for a network of `network_size` peers.
///
/// Definition: max(2, ceil(2 * N / 3)).
/// A single peer can NEVER be a quorum — minimum is always 2.
pub fn consensus_threshold(network_size: usize) -> usize {
    if network_size == 0 {
        return 2;
    }
    // ceil(2*N/3) = (2*N + 2) / 3 in integer arithmetic
    let supermajority = (2 * network_size).div_ceil(3);
    supermajority.max(2)
}

/// A proposal to seal a ledger state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SealProposal {
    pub schema: String,
    pub seal_hash: String,
    pub row_count: usize,
    pub head_sha: String,
    pub proposed_at: f64,
    pub proposer_peer_id: String,
}

impl SealProposal {
    pub fn new(
        seal_hash: impl Into<String>,
        row_count: usize,
        head_sha: impl Into<String>,
        proposer_peer_id: impl Into<String>,
    ) -> Self {
        SealProposal {
            schema: "urace-consensus-v1".into(),
            seal_hash: seal_hash.into(),
            row_count,
            head_sha: head_sha.into(),
            proposed_at: now_secs(),
            proposer_peer_id: proposer_peer_id.into(),
        }
    }
}

/// A signed vote for a seal proposal.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SealVote {
    pub peer_id: String,
    pub seal_hash: String,
    pub voted_at: f64,
    pub signature_hex: String,
}

impl SealVote {
    pub fn new(
        peer_id: impl Into<String>,
        seal_hash: impl Into<String>,
        signature_hex: impl Into<String>,
    ) -> Self {
        SealVote {
            peer_id: peer_id.into(),
            seal_hash: seal_hash.into(),
            voted_at: now_secs(),
            signature_hex: signature_hex.into(),
        }
    }
}

/// Collects votes per seal_hash and determines finalization.
///
/// Each peer may vote at most once per seal_hash (deduplication enforced).
/// Finalization requires strict supermajority of distinct peer votes.
pub struct VoteCollector {
    /// seal_hash → (peer_id → vote)
    votes: DashMap<String, HashMap<String, SealVote>>,
    /// seal_hash → timestamp when it first reached threshold
    finalized_timestamps: DashMap<String, f64>,
}

impl VoteCollector {
    pub fn new() -> Self {
        VoteCollector {
            votes: DashMap::new(),
            finalized_timestamps: DashMap::new(),
        }
    }

    /// Add a vote. Silently drops duplicate votes from the same peer_id.
    pub fn add_vote(&self, vote: SealVote) {
        let mut bucket = self.votes.entry(vote.seal_hash.clone()).or_default();
        // Each peer may cast at most one vote per seal_hash.
        bucket.entry(vote.peer_id.clone()).or_insert(vote);
    }

    /// Returns the number of distinct peers that have voted for `seal_hash`.
    pub fn vote_count(&self, seal_hash: &str) -> usize {
        self.votes.get(seal_hash).map(|b| b.len()).unwrap_or(0)
    }

    /// Returns true iff `seal_hash` has received at least `threshold` distinct peer votes.
    ///
    /// Invariant: threshold must be derived from `consensus_threshold(network_size)`.
    /// A single peer MUST NOT be able to cause finalization (threshold ≥ 2 always).
    pub fn is_finalized(&self, seal_hash: &str, threshold: usize) -> bool {
        // Enforce minimum threshold to prevent single-peer determination.
        let effective_threshold = threshold.max(2);
        let count = self.vote_count(seal_hash);
        let finalized = count >= effective_threshold;
        if finalized {
            // Record timestamp on first finalization.
            self.finalized_timestamps
                .entry(seal_hash.to_string())
                .or_insert_with(now_secs);
        }
        finalized
    }

    /// Returns the timestamp when `seal_hash` was first finalized, if ever.
    pub fn finalized_at(&self, seal_hash: &str) -> Option<f64> {
        self.finalized_timestamps.get(seal_hash).map(|v| *v)
    }

    /// Returns all votes for a given seal_hash.
    pub fn votes_for(&self, seal_hash: &str) -> Vec<SealVote> {
        self.votes
            .get(seal_hash)
            .map(|b| b.values().cloned().collect())
            .unwrap_or_default()
    }

    /// Returns all distinct peer_ids that voted for `seal_hash`.
    pub fn voters_for(&self, seal_hash: &str) -> HashSet<String> {
        self.votes
            .get(seal_hash)
            .map(|b| b.keys().cloned().collect())
            .unwrap_or_default()
    }
}

impl Default for VoteCollector {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_consensus_threshold_values() {
        assert_eq!(consensus_threshold(0), 2);
        assert_eq!(consensus_threshold(1), 2);
        assert_eq!(consensus_threshold(2), 2);
        assert_eq!(consensus_threshold(3), 2);
        assert_eq!(consensus_threshold(4), 3);
        assert_eq!(consensus_threshold(6), 4);
        assert_eq!(consensus_threshold(9), 6);
        assert_eq!(consensus_threshold(100), 67);
    }

    #[test]
    fn test_minimum_threshold_is_two() {
        // No single peer should ever determine outcome.
        for n in 0..=3 {
            assert!(
                consensus_threshold(n) >= 2,
                "threshold for n={} must be >=2",
                n
            );
        }
    }

    #[test]
    fn test_vote_deduplication() {
        let vc = VoteCollector::new();
        vc.add_vote(SealVote::new("peer-a", "hash-1", "sig1"));
        vc.add_vote(SealVote::new("peer-a", "hash-1", "sig2")); // duplicate peer
        assert_eq!(vc.vote_count("hash-1"), 1);
    }

    #[test]
    fn test_not_finalized_below_threshold() {
        let vc = VoteCollector::new();
        vc.add_vote(SealVote::new("peer-a", "hash-2", "sig1"));
        vc.add_vote(SealVote::new("peer-b", "hash-2", "sig2"));
        // threshold for N=6 is 4
        assert!(!vc.is_finalized("hash-2", 4));
    }

    #[test]
    fn test_finalized_at_threshold() {
        let vc = VoteCollector::new();
        for i in 0..4u64 {
            vc.add_vote(SealVote::new(format!("peer-{}", i), "hash-3", "sig"));
        }
        assert!(vc.is_finalized("hash-3", 4));
        assert!(vc.finalized_at("hash-3").is_some());
    }

    #[test]
    fn test_seal_proposal_schema() {
        let p = SealProposal::new("abc", 10, "sha", "proposer");
        assert_eq!(p.schema, "urace-consensus-v1");
    }
}
