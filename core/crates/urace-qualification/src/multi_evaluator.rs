//! M46 — Multi-evaluator consensus.
//!
//! When work is sampled (M45 returns PendingSampling), multiple evaluators must vote
//! before a final approve/reject decision is reached.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum EvaluatorError {
    #[error("evaluator '{0}' already voted for work_id '{1}'")]
    AlreadyVoted(String, String),
    #[error("work_id '{0}' not found")]
    NotFound(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum EvaluatorVote {
    Approve { score: f64 },
    Reject { reason: String },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ConsensusResult {
    Approved { mean_score: f64, vote_count: usize },
    Rejected { approve_count: usize, reject_count: usize },
    Pending { votes_received: usize, votes_needed: usize },
}

pub struct MultiEvaluatorRound {
    work_id: String,
    /// Minimum number of evaluators required before a consensus can be reached.
    min_evaluators: usize,
    votes: HashMap<String, EvaluatorVote>, // evaluator_peer_id -> vote
}

impl MultiEvaluatorRound {
    pub fn new(work_id: impl Into<String>, min_evaluators: usize) -> Self {
        MultiEvaluatorRound {
            work_id: work_id.into(),
            min_evaluators,
            votes: HashMap::new(),
        }
    }

    pub fn submit_vote(
        &mut self,
        evaluator_id: &str,
        vote: EvaluatorVote,
    ) -> Result<ConsensusResult, EvaluatorError> {
        if self.votes.contains_key(evaluator_id) {
            return Err(EvaluatorError::AlreadyVoted(
                evaluator_id.to_string(),
                self.work_id.clone(),
            ));
        }
        self.votes.insert(evaluator_id.to_string(), vote);
        Ok(self.current_result())
    }

    pub fn current_result(&self) -> ConsensusResult {
        if self.votes.len() < self.min_evaluators {
            return ConsensusResult::Pending {
                votes_received: self.votes.len(),
                votes_needed: self.min_evaluators,
            };
        }
        let mut approve_scores: Vec<f64> = Vec::new();
        let mut reject_count = 0usize;
        for vote in self.votes.values() {
            match vote {
                EvaluatorVote::Approve { score } => approve_scores.push(*score),
                EvaluatorVote::Reject { .. } => reject_count += 1,
            }
        }
        // Strict majority required: approve count must be strictly greater than reject count.
        if approve_scores.len() > reject_count {
            let mean = approve_scores.iter().sum::<f64>() / approve_scores.len() as f64;
            ConsensusResult::Approved {
                mean_score: mean,
                vote_count: self.votes.len(),
            }
        } else {
            ConsensusResult::Rejected {
                approve_count: approve_scores.len(),
                reject_count,
            }
        }
    }

    pub fn vote_count(&self) -> usize {
        self.votes.len()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pending_until_min_evaluators() {
        let mut round = MultiEvaluatorRound::new("work-1", 3);
        let r1 = round
            .submit_vote("e1", EvaluatorVote::Approve { score: 0.9 })
            .unwrap();
        assert!(matches!(r1, ConsensusResult::Pending { votes_received: 1, votes_needed: 3 }));
        let r2 = round
            .submit_vote("e2", EvaluatorVote::Approve { score: 0.8 })
            .unwrap();
        assert!(matches!(r2, ConsensusResult::Pending { votes_received: 2, votes_needed: 3 }));
    }

    #[test]
    fn majority_approve_consensus() {
        let mut round = MultiEvaluatorRound::new("work-2", 3);
        round
            .submit_vote("e1", EvaluatorVote::Approve { score: 0.9 })
            .unwrap();
        round
            .submit_vote("e2", EvaluatorVote::Approve { score: 0.8 })
            .unwrap();
        let result = round
            .submit_vote("e3", EvaluatorVote::Reject { reason: "poor".into() })
            .unwrap();
        // 2 approvals vs 1 rejection → Approved
        match result {
            ConsensusResult::Approved { mean_score, vote_count } => {
                assert_eq!(vote_count, 3);
                assert!((mean_score - 0.85).abs() < 1e-10);
            }
            other => panic!("expected Approved, got {other:?}"),
        }
    }

    #[test]
    fn majority_reject_consensus() {
        let mut round = MultiEvaluatorRound::new("work-3", 3);
        round
            .submit_vote("e1", EvaluatorVote::Reject { reason: "bad".into() })
            .unwrap();
        round
            .submit_vote("e2", EvaluatorVote::Reject { reason: "bad".into() })
            .unwrap();
        let result = round
            .submit_vote("e3", EvaluatorVote::Approve { score: 0.7 })
            .unwrap();
        // 1 approval vs 2 rejections → Rejected
        assert!(
            matches!(result, ConsensusResult::Rejected { approve_count: 1, reject_count: 2 }),
            "expected Rejected, got {result:?}"
        );
    }

    #[test]
    fn duplicate_vote_rejected() {
        let mut round = MultiEvaluatorRound::new("work-4", 2);
        round
            .submit_vote("e1", EvaluatorVote::Approve { score: 0.9 })
            .unwrap();
        let err = round
            .submit_vote("e1", EvaluatorVote::Approve { score: 0.8 })
            .expect_err("duplicate vote must be rejected");
        matches!(err, EvaluatorError::AlreadyVoted(_, _));
    }

    #[test]
    fn tie_goes_to_reject() {
        // 1 approve, 1 reject with min_evaluators=2 → Rejected (approve not > reject)
        let mut round = MultiEvaluatorRound::new("work-5", 2);
        round
            .submit_vote("e1", EvaluatorVote::Approve { score: 0.9 })
            .unwrap();
        let result = round
            .submit_vote("e2", EvaluatorVote::Reject { reason: "tie".into() })
            .unwrap();
        assert!(
            matches!(result, ConsensusResult::Rejected { approve_count: 1, reject_count: 1 }),
            "tie must go to Rejected, got {result:?}"
        );
    }
}
