//! M28 — Periodic audit chain integrity verification.
//!
//! Verifies that an `AuditLedger`'s underlying HMAC-signed journal has not
//! been tampered with.  The `verify_audit_chain` function re-reads all
//! entries, counts how many are valid (readable without an integrity error),
//! and reports the index of the first broken entry if any.

use crate::audit_ledger::{AuditError, AuditLedger};
use serde::{Deserialize, Serialize};

// ── ChainIntegrityReport ──────────────────────────────────────────────────────

/// Maximum acceptable lag between an event occurring and its audit entry being written (24 h).
pub const MAX_AUDIT_LAG_SECS: u64 = 86_400;

/// If more than this fraction of chain entries are broken, trigger a chain anomaly alert (1%).
pub const CHAIN_ANOMALY_ALERT_THRESHOLD: f64 = 0.01;

/// Summary of an audit chain integrity check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainIntegrityReport {
    /// Total number of entries read before the first error (or end of journal).
    pub total_entries: usize,
    /// Entries that passed their HMAC check.
    pub valid_entries: usize,
    /// Index (0-based) of the first entry that failed verification, if any.
    pub first_broken_index: Option<usize>,
    /// `true` iff every entry passed verification (`first_broken_index.is_none()`).
    pub is_intact: bool,
}

// ── verify_audit_chain ────────────────────────────────────────────────────────

/// Verify an `AuditLedger`'s chain integrity.
///
/// Re-reads all events via `AuditLedger::all_events`, which internally calls
/// `Journal::verify_integrity`.  If the journal is intact, every event is
/// counted as valid.  If the journal detects a broken link it surfaces an
/// `AuditError::Journal` — we treat the last successfully read index as the
/// break point.
///
/// Returns `Ok(ChainIntegrityReport)` in both intact and broken cases.
/// Returns `Err` only on unexpected I/O or serialization failures that do not
/// indicate chain tampering.
pub fn verify_audit_chain(ledger: &AuditLedger) -> Result<ChainIntegrityReport, AuditError> {
    match ledger.all_events() {
        Ok(events) => {
            let n = events.len();
            Ok(ChainIntegrityReport {
                total_entries: n,
                valid_entries: n,
                first_broken_index: None,
                is_intact: true,
            })
        }
        Err(AuditError::Journal(journal_err)) => {
            // The journal detected an integrity violation.  Parse the broken
            // index from the error message if available (best effort).
            let broken_index = parse_broken_index(&journal_err.to_string());
            Ok(ChainIntegrityReport {
                total_entries: broken_index.unwrap_or(0),
                valid_entries: broken_index.unwrap_or(0),
                first_broken_index: broken_index,
                is_intact: false,
            })
        }
        Err(other) => Err(other),
    }
}

/// Best-effort extraction of a broken sequence number from a journal error
/// message such as "seq=3 HMAC mismatch".  Returns `None` when no index can
/// be parsed.
fn parse_broken_index(msg: &str) -> Option<usize> {
    // Look for patterns like "seq=N" in the error message.
    let prefix = "seq=";
    if let Some(pos) = msg.find(prefix) {
        let rest = &msg[pos + prefix.len()..];
        let num: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
        num.parse().ok()
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit_kinds::AuditKind;
    use crate::audit_ledger::AuditEvent;
    use serde_json::json;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"test-chain-key-00000000000000000";

    fn open(dir: &tempfile::TempDir) -> AuditLedger {
        AuditLedger::open(dir.path().join("audit.jsonl"), KEY).unwrap()
    }

    #[test]
    fn empty_ledger_is_intact() {
        let dir = tempdir().unwrap();
        let ledger = open(&dir);
        let report = verify_audit_chain(&ledger).unwrap();
        assert!(report.is_intact, "empty ledger must be reported as intact");
        assert_eq!(report.total_entries, 0);
        assert_eq!(report.valid_entries, 0);
        assert!(report.first_broken_index.is_none());
    }

    #[test]
    fn ledger_with_valid_events_is_intact() {
        let dir = tempdir().unwrap();
        let ledger = open(&dir);
        for i in 0..3u64 {
            let evt = AuditEvent::new(
                AuditKind::LedgerEntry,
                format!("node-{i}"),
                json!({"seq": i}),
            );
            ledger.record(evt).unwrap();
        }
        let report = verify_audit_chain(&ledger).unwrap();
        assert!(report.is_intact, "intact ledger must pass");
        assert_eq!(report.total_entries, 3);
        assert_eq!(report.valid_entries, 3);
        assert!(report.first_broken_index.is_none());
    }

    #[test]
    fn tampered_ledger_is_not_intact() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("audit.jsonl");
        {
            let ledger = AuditLedger::open(&path, KEY).unwrap();
            let evt = AuditEvent::new(AuditKind::GoalCreated, "node-1", json!({}));
            ledger.record(evt).unwrap();
        }

        // Tamper: corrupt the file by overwriting content.
        std::fs::write(&path, b"not-valid-json\n").unwrap();

        let ledger = AuditLedger::open(&path, KEY).unwrap();
        let report = verify_audit_chain(&ledger).unwrap();
        assert!(!report.is_intact, "tampered ledger must not be intact");
    }

    #[test]
    fn report_fields_consistent_on_intact_ledger() {
        let dir = tempdir().unwrap();
        let ledger = open(&dir);
        let evt = AuditEvent::new(AuditKind::WorkBid, "worker-1", json!({"task": "t1"}));
        ledger.record(evt).unwrap();
        let report = verify_audit_chain(&ledger).unwrap();
        assert_eq!(report.total_entries, report.valid_entries);
        assert!(report.is_intact);
    }
}
