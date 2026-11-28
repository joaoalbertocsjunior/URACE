//! Append-only audit ledger.
//!
//! Rust port of `audit_ledger.py`.
//! All writes go through `urace-ledger::Journal` (atomic, HMAC-signed).

use serde_json::json;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

pub use urace_audit_types::AuditEvent;

#[derive(Debug, Error)]
pub enum AuditError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// Append-only audit ledger backed by `Journal`.
pub struct AuditLedger {
    journal: Journal,
}

impl AuditLedger {
    pub fn open(path: impl AsRef<std::path::Path>, hmac_key: [u8; 32]) -> Result<Self, AuditError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(AuditLedger { journal })
    }

    pub fn record(&self, event: AuditEvent) -> Result<(), AuditError> {
        let payload = json!({
            "event_id": event.event_id,
            "kind": event.kind,
            "actor": event.actor,
            "target": event.target,
            "details": event.details,
            "timestamp_ms": event.timestamp_ms,
        });
        self.journal.append("audit_event", payload)?;
        Ok(())
    }

    /// Write an arbitrary-kind entry directly to the underlying journal.
    ///
    /// Used for internal system entries (e.g. `"epoch_anchor"`) that do not map
    /// to a typed `AuditEvent`.  The entry is HMAC-signed and append-only like
    /// all other journal entries.
    pub fn record_raw(
        &self,
        kind: &str,
        payload: serde_json::Value,
    ) -> Result<(), AuditError> {
        self.journal.append(kind, payload)?;
        Ok(())
    }

    /// Verify HMAC chain integrity and return the count of all raw journal entries,
    /// regardless of their `kind` field.  Unlike `all_events`, this does not
    /// require each entry to conform to the `AuditEvent` schema, so system
    /// entries (e.g. `"epoch_anchor"`) are counted without error.
    ///
    /// Returns `Err(AuditError::Journal)` if the HMAC chain is broken.
    pub fn verify_chain_raw(&self) -> Result<usize, AuditError> {
        let entries = self.journal.verify_integrity()?;
        Ok(entries.len())
    }

    pub fn all_events(&self) -> Result<Vec<AuditEvent>, AuditError> {
        let entries = self.journal.verify_integrity()?;
        let mut events = Vec::with_capacity(entries.len());
        for entry in entries {
            // Skip non-AuditEvent entries (e.g. epoch_anchor system rows) so
            // the HMAC chain can include system entries without breaking replay.
            if entry.kind == "audit_event" {
                let evt: AuditEvent = serde_json::from_value(entry.payload)?;
                events.push(evt);
            }
        }
        Ok(events)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit_kinds::AuditKind;

    const KEY: [u8; 32] = *b"test-audit-key-00000000000000000";

    #[test]
    fn record_and_replay() {
        let dir = tempfile::tempdir().unwrap();
        let ledger = AuditLedger::open(dir.path().join("audit.jsonl"), KEY).unwrap();
        let evt = AuditEvent::new(AuditKind::GoalCreated, "node-1", json!({"goal_id": "g1"}));
        ledger.record(evt).unwrap();
        let events = ledger.all_events().unwrap();
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].kind, AuditKind::GoalCreated);
    }

    #[test]
    fn multiple_events() {
        let dir = tempfile::tempdir().unwrap();
        let ledger = AuditLedger::open(dir.path().join("audit.jsonl"), KEY).unwrap();
        for i in 0..5 {
            let evt = AuditEvent::new(
                AuditKind::LedgerEntry,
                format!("node-{i}"),
                json!({"amount": i}),
            );
            ledger.record(evt).unwrap();
        }
        assert_eq!(ledger.all_events().unwrap().len(), 5);
    }
}
