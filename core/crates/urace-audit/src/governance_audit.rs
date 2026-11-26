//! Governance audit — records policy updates and violation events.
//!
//! Rust port of `governance_audit.py`.

use crate::audit_kinds::AuditKind;
use crate::audit_ledger::{AuditError, AuditEvent, AuditLedger};
use serde_json::json;

/// Convenience wrapper that records governance-specific audit events.
pub struct GovernanceAuditor<'a> {
    ledger: &'a AuditLedger,
    node_id: String,
}

impl<'a> GovernanceAuditor<'a> {
    pub fn new(ledger: &'a AuditLedger, node_id: impl Into<String>) -> Self {
        GovernanceAuditor {
            ledger,
            node_id: node_id.into(),
        }
    }

    pub fn record_policy_update(
        &self,
        policy_id: &str,
        old_generation: u64,
        new_generation: u64,
    ) -> Result<(), AuditError> {
        let evt = AuditEvent::new(
            AuditKind::PolicyUpdated,
            &self.node_id,
            json!({
                "policy_id": policy_id,
                "old_generation": old_generation,
                "new_generation": new_generation,
            }),
        )
        .with_target(policy_id);
        self.ledger.record(evt)
    }

    pub fn record_policy_violation(&self, policy_id: &str, reason: &str) -> Result<(), AuditError> {
        let evt = AuditEvent::new(
            AuditKind::PolicyViolation,
            &self.node_id,
            json!({
                "policy_id": policy_id,
                "reason": reason,
            }),
        )
        .with_target(policy_id);
        self.ledger.record(evt)
    }

    pub fn record_authority_decision(&self, action: &str, outcome: &str) -> Result<(), AuditError> {
        let evt = AuditEvent::new(
            AuditKind::AuthorityDecision,
            &self.node_id,
            json!({ "action": action, "outcome": outcome }),
        );
        self.ledger.record(evt)
    }

    /// M03 — record that a routing decision was taken for `job_id`.
    pub fn record_routing_decision(
        &self,
        job_id: &str,
        selected_provider: &str,
        candidates_considered: usize,
        reason: &str,
    ) -> Result<(), AuditError> {
        let evt = AuditEvent::new(
            AuditKind::RoutingDecision,
            &self.node_id,
            json!({
                "job_id": job_id,
                "selected_provider": selected_provider,
                "candidates_considered": candidates_considered,
                "reason": reason,
            }),
        )
        .with_target(job_id);
        self.ledger.record(evt)
    }

    /// M03 — record that a routing attempt was rejected.
    pub fn record_routing_rejected(
        &self,
        job_id: &str,
        reason: &str,
    ) -> Result<(), AuditError> {
        let evt = AuditEvent::new(
            AuditKind::RoutingRejected,
            &self.node_id,
            json!({ "job_id": job_id, "reason": reason }),
        )
        .with_target(job_id);
        self.ledger.record(evt)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit_kinds::AuditKind;
    use crate::audit_ledger::AuditLedger;

    const KEY: [u8; 32] = *b"governance-audit-key-00000000000";

    #[test]
    fn record_policy_update() {
        let dir = tempfile::tempdir().unwrap();
        let ledger = AuditLedger::open(dir.path().join("gov.jsonl"), KEY).unwrap();
        let auditor = GovernanceAuditor::new(&ledger, "node-a");
        auditor
            .record_policy_update("fleet-policy-1", 0, 1)
            .unwrap();
        let events = ledger.all_events().unwrap();
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].kind, AuditKind::PolicyUpdated);
    }

    #[test]
    fn record_violation() {
        let dir = tempfile::tempdir().unwrap();
        let ledger = AuditLedger::open(dir.path().join("gov.jsonl"), KEY).unwrap();
        let auditor = GovernanceAuditor::new(&ledger, "node-a");
        auditor
            .record_policy_violation("fp-1", "generation stale")
            .unwrap();
        let events = ledger.all_events().unwrap();
        assert_eq!(events[0].kind, AuditKind::PolicyViolation);
    }

    #[test]
    fn record_routing_decision_logged() {
        let dir = tempfile::tempdir().unwrap();
        let ledger = AuditLedger::open(dir.path().join("route.jsonl"), KEY).unwrap();
        let auditor = GovernanceAuditor::new(&ledger, "node-b");
        auditor
            .record_routing_decision("job-1", "provider-anthropic", 3, "highest score")
            .unwrap();
        let events = ledger.all_events().unwrap();
        assert_eq!(events[0].kind, AuditKind::RoutingDecision);
        assert_eq!(events[0].target.as_deref(), Some("job-1"));
    }

    #[test]
    fn record_routing_rejected_logged() {
        let dir = tempfile::tempdir().unwrap();
        let ledger = AuditLedger::open(dir.path().join("route-rej.jsonl"), KEY).unwrap();
        let auditor = GovernanceAuditor::new(&ledger, "node-b");
        auditor
            .record_routing_rejected("job-2", "no available providers")
            .unwrap();
        let events = ledger.all_events().unwrap();
        assert_eq!(events[0].kind, AuditKind::RoutingRejected);
    }
}
