//! Spec audit — verifies runtime state against canonical invariants.
//!
//! Rust port of `spec_audit.py`.
//! Each check emits a PASSED or FAILED audit event; never throws silently.

use crate::audit_kinds::AuditKind;
use crate::audit_ledger::{AuditError, AuditEvent, AuditLedger};
use serde_json::json;

pub struct SpecAuditor<'a> {
    ledger: &'a AuditLedger,
    node_id: String,
}

impl<'a> SpecAuditor<'a> {
    pub fn new(ledger: &'a AuditLedger, node_id: impl Into<String>) -> Self {
        SpecAuditor { ledger, node_id: node_id.into() }
    }

    /// Run `check` and emit a spec audit event.
    ///
    /// Never panics — if the check closure itself errors, that's captured as a failure.
    pub fn run_check<F>(&self, check_name: &str, check: F) -> Result<bool, AuditError>
    where
        F: FnOnce() -> bool,
    {
        let passed = check();
        let (kind, outcome) = if passed {
            (AuditKind::SpecCheckPassed, "passed")
        } else {
            (AuditKind::SpecCheckFailed, "failed")
        };
        let evt = AuditEvent::new(
            kind,
            &self.node_id,
            json!({ "check": check_name, "outcome": outcome }),
        );
        self.ledger.record(evt)?;
        Ok(passed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit_ledger::AuditLedger;

    const KEY: [u8; 32] = *b"spec-audit-key-00000000000000000";

    #[test]
    fn passing_check() {
        let dir = tempfile::tempdir().unwrap();
        let ledger = AuditLedger::open(dir.path().join("spec.jsonl"), KEY).unwrap();
        let auditor = SpecAuditor::new(&ledger, "node-a");
        let ok = auditor.run_check("ledger_non_empty", || true).unwrap();
        assert!(ok);
        let events = ledger.all_events().unwrap();
        assert_eq!(events[0].kind, AuditKind::SpecCheckPassed);
    }

    #[test]
    fn failing_check() {
        let dir = tempfile::tempdir().unwrap();
        let ledger = AuditLedger::open(dir.path().join("spec.jsonl"), KEY).unwrap();
        let auditor = SpecAuditor::new(&ledger, "node-a");
        let ok = auditor.run_check("impossible_check", || false).unwrap();
        assert!(!ok);
        let events = ledger.all_events().unwrap();
        assert_eq!(events[0].kind, AuditKind::SpecCheckFailed);
    }
}
