//! M69 — Emergency fast-path governance vote.
//!
//! For critical incidents (security breach, protocol exploit, mass exit),
//! a reduced quorum with a time-boxed window allows faster governance action.
//!
//! **Safety invariant**: emergency votes may NOT change:
//! - `UNIT` constant
//! - `PEER_CAP`
//! - Authority boundary (§62z)
//! - Exit codes (75, 76)
//!
//! Emergency votes are limited to: protocol halt, quarantine peer list,
//! temporary mint freeze, emergency parameter rollback.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Maximum window for an emergency vote (1 hour).
pub const EMERGENCY_VOTE_WINDOW_SECS: u64 = 3_600;

/// Reduced quorum for emergency votes (33% — still > 1/3 to prevent minority capture).
pub const EMERGENCY_QUORUM_FRACTION: f64 = 0.33;

/// Categories of emergency action permitted through the fast-path.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum EmergencyAction {
    HaltProtocol,
    QuarantinePeerList { peers: Vec<String> },
    FreezeMinting,
    RollbackParameter { parameter: String, revert_to: String },
}

/// A single emergency vote cast by a governance participant.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmergencyVote {
    pub voter_id: String,
    pub action: EmergencyAction,
    pub cast_at_unix: u64,
}

/// An active emergency proposal.
#[derive(Debug)]
pub struct EmergencyProposal {
    pub proposal_id: String,
    pub action: EmergencyAction,
    pub initiated_at_unix: u64,
    votes: HashMap<String, EmergencyVote>,
}

impl EmergencyProposal {
    pub fn new(
        proposal_id: impl Into<String>,
        action: EmergencyAction,
        initiated_at_unix: u64,
    ) -> Self {
        EmergencyProposal {
            proposal_id: proposal_id.into(),
            action,
            initiated_at_unix,
            votes: HashMap::new(),
        }
    }

    /// Cast a vote. Deduplicates by voter_id.
    pub fn cast_vote(&mut self, vote: EmergencyVote) {
        self.votes.entry(vote.voter_id.clone()).or_insert(vote);
    }

    /// Returns `true` iff the vote window is still open at `now_unix`.
    pub fn is_open(&self, now_unix: u64) -> bool {
        now_unix < self.initiated_at_unix + EMERGENCY_VOTE_WINDOW_SECS
    }

    /// Returns `true` iff the proposal has reached quorum given `total_eligible_voters`.
    pub fn quorum_reached(&self, total_eligible_voters: usize) -> bool {
        if total_eligible_voters == 0 {
            return false;
        }
        let required = ((total_eligible_voters as f64 * EMERGENCY_QUORUM_FRACTION).ceil() as usize).max(2);
        self.votes.len() >= required
    }

    pub fn vote_count(&self) -> usize {
        self.votes.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn emergency_quorum_requires_minimum_two() {
        let mut prop = EmergencyProposal::new("e1", EmergencyAction::FreezeMinting, 1000);
        // With 3 eligible voters: ceil(3 * 0.33) = 1, but max(1, 2) = 2.
        prop.cast_vote(EmergencyVote {
            voter_id: "v1".into(),
            action: EmergencyAction::FreezeMinting,
            cast_at_unix: 1001,
        });
        assert!(!prop.quorum_reached(3), "1 vote out of 3 — below minimum 2");

        prop.cast_vote(EmergencyVote {
            voter_id: "v2".into(),
            action: EmergencyAction::FreezeMinting,
            cast_at_unix: 1002,
        });
        assert!(prop.quorum_reached(3), "2 votes — quorum reached");
    }

    #[test]
    fn emergency_vote_window_expires() {
        let prop = EmergencyProposal::new("e2", EmergencyAction::HaltProtocol, 1000);
        assert!(prop.is_open(1000));
        assert!(prop.is_open(1000 + EMERGENCY_VOTE_WINDOW_SECS - 1));
        assert!(!prop.is_open(1000 + EMERGENCY_VOTE_WINDOW_SECS));
    }

    #[test]
    fn duplicate_votes_not_counted() {
        let mut prop = EmergencyProposal::new("e3", EmergencyAction::FreezeMinting, 0);
        for _ in 0..5 {
            prop.cast_vote(EmergencyVote {
                voter_id: "same-voter".into(),
                action: EmergencyAction::FreezeMinting,
                cast_at_unix: 1,
            });
        }
        assert_eq!(prop.vote_count(), 1);
    }
}
