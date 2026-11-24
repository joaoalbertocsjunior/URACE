//! Authority resolution outcome types — §62z invariant.
//!
//! Outcomes mirror `authority.py`. UNRESOLVED must always be treated as DENIED.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum AuthorityOutcome {
    AutonomouslyAuthorized,
    Denied,
    RequiresAuthoritativeDecision,
    /// Unresolved must be treated as Denied — never proceed on Unresolved.
    Unresolved,
}

impl AuthorityOutcome {
    pub fn is_allowed(&self) -> bool {
        matches!(self, AuthorityOutcome::AutonomouslyAuthorized)
    }

    /// Returns true if execution may proceed (only AUTONOMOUSLY_AUTHORIZED).
    pub fn may_proceed(&self) -> bool {
        self.is_allowed()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorityResolution {
    pub outcome: AuthorityOutcome,
    pub basis: String,
    pub gate: String,
    pub resolved_at: String,
}
