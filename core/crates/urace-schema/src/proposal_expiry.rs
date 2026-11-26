//! M63 — Governance proposal expiry: proposals that miss their window are auto-rejected.

use serde::{Deserialize, Serialize};

pub const PROPOSAL_EXPIRY_SECS: u64 = 7 * 24 * 3_600; // 7 days

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProposalExpiryStatus {
    Active,
    Expired,
    Executed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernanceProposal {
    pub proposal_id: String,
    pub title: String,
    pub created_at_unix: u64,
    pub expiry_secs: u64,
    pub status: ProposalExpiryStatus,
}

#[derive(Debug, thiserror::Error)]
pub enum ProposalError {
    #[error("proposal already executed")]
    AlreadyExecuted,
    #[error("proposal already expired")]
    AlreadyExpired,
}

impl GovernanceProposal {
    pub fn new(
        proposal_id: impl Into<String>,
        title: impl Into<String>,
        created_at_unix: u64,
    ) -> Self {
        GovernanceProposal {
            proposal_id: proposal_id.into(),
            title: title.into(),
            created_at_unix,
            expiry_secs: PROPOSAL_EXPIRY_SECS,
            status: ProposalExpiryStatus::Active,
        }
    }

    pub fn is_expired(&self, now_unix: u64) -> bool {
        now_unix > self.created_at_unix + self.expiry_secs
    }

    /// Transitions Active → Expired if past deadline. Returns Err if already executed.
    /// Returns Ok(true) if it was just expired, Ok(false) if still active.
    pub fn expire_if_due(&mut self, now_unix: u64) -> Result<bool, ProposalError> {
        match self.status {
            ProposalExpiryStatus::Executed => Err(ProposalError::AlreadyExecuted),
            ProposalExpiryStatus::Expired => Ok(false),
            ProposalExpiryStatus::Active => {
                if self.is_expired(now_unix) {
                    self.status = ProposalExpiryStatus::Expired;
                    Ok(true)
                } else {
                    Ok(false)
                }
            }
        }
    }

    /// Mark as executed (before expiry).
    pub fn execute(&mut self) -> Result<(), ProposalError> {
        match self.status {
            ProposalExpiryStatus::Executed => Err(ProposalError::AlreadyExecuted),
            ProposalExpiryStatus::Expired => Err(ProposalError::AlreadyExpired),
            ProposalExpiryStatus::Active => {
                self.status = ProposalExpiryStatus::Executed;
                Ok(())
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn not_expired_before_deadline() {
        let proposal = GovernanceProposal::new("p1", "Test", 1000);
        // Just before the deadline
        let before_expiry = 1000 + PROPOSAL_EXPIRY_SECS;
        assert!(!proposal.is_expired(before_expiry));
    }

    #[test]
    fn expired_after_proposal_expiry_secs() {
        let proposal = GovernanceProposal::new("p1", "Test", 1000);
        let after_expiry = 1000 + PROPOSAL_EXPIRY_SECS + 1;
        assert!(proposal.is_expired(after_expiry));
    }

    #[test]
    fn executed_before_expiry_succeeds() {
        let mut proposal = GovernanceProposal::new("p1", "Test", 1000);
        // Execute while still active (way before deadline)
        let result = proposal.execute();
        assert!(result.is_ok());
        assert_eq!(proposal.status, ProposalExpiryStatus::Executed);
    }

    #[test]
    fn expire_after_execute_fails() {
        let mut proposal = GovernanceProposal::new("p1", "Test", 1000);
        proposal.execute().unwrap();
        // Now try to expire an already-executed proposal
        let after_expiry = 1000 + PROPOSAL_EXPIRY_SECS + 1;
        let result = proposal.expire_if_due(after_expiry);
        assert!(matches!(result, Err(ProposalError::AlreadyExecuted)));
    }
}
