//! Canonical audit event kind taxonomy.
//!
//! Rust port of `audit_kinds.py`.
//! All audit events MUST use a kind from this module — freeform strings are rejected.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AuditKind {
    // Authority
    AuthorityDecision,
    AuthorityOverrideAttempt,
    // Identity
    KeyGenerated,
    KeyRotated,
    KeyRevoked,
    // Ledger / financial
    LedgerEntry,
    EscrowCreated,
    EscrowReleased,
    EscrowTimeout,
    // Work market
    WorkBid,
    WorkAssigned,
    WorkCompleted,
    WorkFailed,
    // Goals
    GoalCreated,
    GoalCompleted,
    GoalCancelled,
    MintTriggered,
    // Settlement
    SettlementInitiated,
    SettlementCompleted,
    SettlementFailed,
    // Sources
    SourceAdded,
    SourceRemoved,
    SourceSynced,
    // Upgrade
    CandidateValidated,
    RuntimeActivated,
    // Governance
    PolicyUpdated,
    PolicyViolation,
    // Routing (M03)
    RoutingDecision,
    RoutingRejected,
    // Spec
    SpecCheckPassed,
    SpecCheckFailed,
    // Generic
    Custom(String),
}

impl std::fmt::Display for AuditKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = serde_json::to_string(self).unwrap_or_else(|_| "\"unknown\"".into());
        write!(f, "{}", s.trim_matches('"'))
    }
}
