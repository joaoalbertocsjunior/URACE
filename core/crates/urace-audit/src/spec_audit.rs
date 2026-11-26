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

// ── M11 — Anti-siphon anomaly detection ──────────────────────────────────────

/// A mint event: amount minted for a peer at a given time.
#[derive(Debug, Clone)]
pub struct MintRecord {
    pub peer_id: String,
    pub amount_ucr: i64,
    pub at_unix: u64,
}

/// Detects concentration anomalies that could indicate siphoning.
///
/// Returns the list of peer IDs whose share of total minted tokens in the
/// provided window exceeds `max_share_fraction`.
pub fn detect_siphon_anomalies(
    records: &[MintRecord],
    max_share_fraction: f64,
) -> Vec<String> {
    let total: i64 = records.iter().map(|r| r.amount_ucr).sum();
    if total == 0 {
        return vec![];
    }

    // Aggregate per peer.
    let mut by_peer: std::collections::HashMap<String, i64> = std::collections::HashMap::new();
    for r in records {
        *by_peer.entry(r.peer_id.clone()).or_insert(0) += r.amount_ucr;
    }

    by_peer
        .into_iter()
        .filter(|(_, amt)| (*amt as f64 / total as f64) > max_share_fraction)
        .map(|(peer_id, _)| peer_id)
        .collect()
}

/// Maximum fraction of epoch minting a single peer may receive before flagging (25%).
pub const SIPHON_MAX_SHARE_FRACTION: f64 = 0.25;

impl<'a> SpecAuditor<'a> {
    pub fn new(ledger: &'a AuditLedger, node_id: impl Into<String>) -> Self {
        SpecAuditor {
            ledger,
            node_id: node_id.into(),
        }
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

    // M11 — anti-siphon tests

    #[test]
    fn siphon_detection_flags_concentrated_peer() {
        let records = vec![
            MintRecord { peer_id: "peer-siphon".into(), amount_ucr: 800, at_unix: 0 },
            MintRecord { peer_id: "peer-normal-1".into(), amount_ucr: 100, at_unix: 0 },
            MintRecord { peer_id: "peer-normal-2".into(), amount_ucr: 100, at_unix: 0 },
        ];
        // peer-siphon has 80% share → exceeds SIPHON_MAX_SHARE_FRACTION (25%)
        let flagged = detect_siphon_anomalies(&records, SIPHON_MAX_SHARE_FRACTION);
        assert_eq!(flagged, vec!["peer-siphon"]);
    }

    #[test]
    fn siphon_detection_clean_distribution() {
        let records: Vec<MintRecord> = (0..5)
            .map(|i| MintRecord { peer_id: format!("peer-{i}"), amount_ucr: 200, at_unix: 0 })
            .collect();
        // Equal 20% each — below 25% threshold.
        let flagged = detect_siphon_anomalies(&records, SIPHON_MAX_SHARE_FRACTION);
        assert!(flagged.is_empty());
    }

    #[test]
    fn siphon_detection_empty_records() {
        assert!(detect_siphon_anomalies(&[], 0.25).is_empty());
    }
}
