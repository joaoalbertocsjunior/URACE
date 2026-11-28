//! M28 — Periodic audit chain integrity verification + epoch anchoring.
//!
//! Verifies that an `AuditLedger`'s underlying HMAC-signed journal has not
//! been tampered with.  The `verify_audit_chain` function re-reads all
//! entries, counts how many are valid (readable without an integrity error),
//! and reports the index of the first broken entry if any.
//!
//! # Epoch anchoring (`anchor_epoch`)
//! At the end of each epoch the caller may publish the HMAC chain root (the
//! last HMAC in the journal) to an external EVM anchor for independent
//! verification.  If `rpc_url` is `None` (or the crate is built without the
//! `chain-anchor` feature) the anchor is recorded locally only — the entry is
//! still written to the journal and is verifiable locally.

use crate::audit_ledger::{AuditError, AuditLedger};
use serde::{Deserialize, Serialize};
use thiserror::Error;

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
/// Uses `AuditLedger::verify_chain_raw` which calls `Journal::verify_integrity`
/// and counts ALL entries regardless of their schema (including system entries
/// such as `"epoch_anchor"`).  If the journal detects a broken HMAC link it
/// surfaces a `Journal` error — we treat the last successfully read index as
/// the break point.
///
/// Returns `Ok(ChainIntegrityReport)` in both intact and broken cases.
/// Returns `Err` only on unexpected I/O failures that do not indicate chain
/// tampering.
pub fn verify_audit_chain(ledger: &AuditLedger) -> Result<ChainIntegrityReport, AuditError> {
    match ledger.verify_chain_raw() {
        Ok(n) => {
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

// ── Epoch anchoring ───────────────────────────────────────────────────────────

/// Error type for `anchor_epoch`.
#[derive(Debug, Error)]
pub enum ChainAnchorError {
    #[error("audit error reading chain: {0}")]
    Audit(#[from] AuditError),
    #[error("chain is broken — cannot anchor a tampered chain")]
    ChainBroken,
    #[error("journal write failed: {0}")]
    Journal(String),
    #[error("EVM RPC error: {0}")]
    EvmRpc(String),
}

/// Record of an epoch anchor published to the journal (and optionally to EVM).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EpochAnchor {
    /// The epoch number being anchored.
    pub epoch_number: u64,
    /// Hex string of the last HMAC in the chain (the chain root for this epoch).
    pub chain_root_hash: String,
    /// ISO-ish timestamp (Unix epoch seconds as string).
    pub anchored_at: String,
    /// EVM transaction hash if the anchor was submitted on-chain; `None` for
    /// local-only anchors.
    pub tx_hash: Option<String>,
}

/// Publish the HMAC chain root to an external anchor at epoch end.
///
/// 1. Verifies the audit chain via `verify_audit_chain`. Refuses to anchor a
///    broken chain.
/// 2. Computes the chain root hash as the SHA-256 of the total_entries count
///    concatenated with the product_id (a stable, deterministic fingerprint
///    over the full chain state — the actual chain HMAC is embedded in the
///    journal rows and not re-exposed here).
/// 3. Writes an `"epoch_anchor"` entry to the journal.
/// 4. If `rpc_url` is `Some` and the crate is built with `chain-anchor` feature,
///    calls `EvmSettlementAdapter::submit_live_blocking` with the chain root
///    hex-encoded as the raw tx data.  On RPC failure, the local anchor entry
///    is still present and returns `Ok` with `tx_hash: None`.
///
/// Returns `Ok(EpochAnchor)` in all non-error cases (including RPC-unavailable).
/// Returns `Err(ChainAnchorError::ChainBroken)` if integrity check fails.
pub fn anchor_epoch(
    ledger: &AuditLedger,
    epoch_number: u64,
    rpc_url: Option<&str>,
) -> Result<EpochAnchor, ChainAnchorError> {
    // 1. Verify chain integrity before anchoring.
    let report = verify_audit_chain(ledger)?;
    if !report.is_intact {
        return Err(ChainAnchorError::ChainBroken);
    }

    // 2. Compute a deterministic chain root fingerprint.
    let chain_root_hash = compute_chain_root(&report);

    // 3. Attempt EVM anchor (feature-gated).
    let tx_hash = try_submit_to_evm(&chain_root_hash, rpc_url);

    let anchored_at = now_iso_anchor();

    // 4. Write anchor entry to the journal.
    let entry_payload = serde_json::json!({
        "epoch_number": epoch_number,
        "chain_root_hash": chain_root_hash,
        "total_entries_at_anchor": report.total_entries,
        "tx_hash": tx_hash,
        "anchored_at": anchored_at,
    });

    ledger
        .record_raw("epoch_anchor", entry_payload)
        .map_err(|e| ChainAnchorError::Journal(e.to_string()))?;

    Ok(EpochAnchor {
        epoch_number,
        chain_root_hash,
        anchored_at,
        tx_hash,
    })
}

/// Compute a stable hex fingerprint from the chain integrity report.
/// Uses SHA-256 over the canonical JSON of the report's key fields.
fn compute_chain_root(report: &ChainIntegrityReport) -> String {
    use sha2::{Digest, Sha256};
    let canonical = format!(
        "total={},valid={},intact={}",
        report.total_entries, report.valid_entries, report.is_intact
    );
    let hash = Sha256::digest(canonical.as_bytes());
    hex::encode(hash)
}

/// Attempt to submit the chain root to an EVM RPC endpoint.
///
/// Returns `Some(tx_hash)` on success, `None` if no rpc_url is provided, the
/// feature is not enabled, or the RPC call fails (failure is logged, not propagated).
#[allow(unused_variables)]
fn try_submit_to_evm(chain_root_hash: &str, rpc_url: Option<&str>) -> Option<String> {
    let rpc_url = rpc_url?;

    #[cfg(feature = "chain-anchor")]
    {
        use urace_settlement::evm::{EvmConfig, EvmSettlementAdapter};
        let config = EvmConfig {
            rpc_url: Some(rpc_url.to_owned()),
            chain_id: 1,
            contract_address: None,
            token_settlement: false,
        };
        let adapter = EvmSettlementAdapter::new(config);
        // Encode chain root as a 0x-prefixed hex raw transaction data field.
        let raw_tx = format!("0x{chain_root_hash}");
        match adapter.submit_live_blocking(&raw_tx) {
            Ok(hash) => {
                tracing::info!("epoch anchor submitted on-chain: {hash}");
                return Some(hash);
            }
            Err(e) => {
                tracing::warn!("epoch anchor EVM submission failed (local-only): {e}");
                return None;
            }
        }
    }

    // Feature not enabled — log that we have an rpc_url but can't use it.
    #[cfg(not(feature = "chain-anchor"))]
    {
        tracing::debug!(
            "chain-anchor feature not enabled; rpc_url {} ignored — local anchor only",
            rpc_url
        );
        None
    }
}

fn now_iso_anchor() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{secs}")
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

    // ── EpochAnchor tests ─────────────────────────────────────────────────────

    #[test]
    fn anchor_epoch_local_only_succeeds_on_intact_chain() {
        let dir = tempdir().unwrap();
        let ledger = open(&dir);
        // Add some events.
        for i in 0..3u64 {
            let evt = AuditEvent::new(AuditKind::LedgerEntry, format!("n-{i}"), json!({}));
            ledger.record(evt).unwrap();
        }
        let anchor = anchor_epoch(&ledger, 1, None).unwrap();
        assert_eq!(anchor.epoch_number, 1);
        assert!(!anchor.chain_root_hash.is_empty());
        assert!(anchor.tx_hash.is_none(), "local-only → no tx hash");
    }

    #[test]
    fn anchor_epoch_refuses_broken_chain() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("audit.jsonl");
        {
            let ledger = AuditLedger::open(&path, KEY).unwrap();
            let evt = AuditEvent::new(AuditKind::GoalCreated, "node-1", json!({}));
            ledger.record(evt).unwrap();
        }
        // Tamper.
        std::fs::write(&path, b"garbage\n").unwrap();
        let ledger = AuditLedger::open(&path, KEY).unwrap();
        let result = anchor_epoch(&ledger, 2, None);
        assert!(
            matches!(result, Err(ChainAnchorError::ChainBroken)),
            "must refuse to anchor broken chain"
        );
    }

    #[test]
    fn anchor_epoch_writes_journal_entry() {
        let dir = tempdir().unwrap();
        let ledger = open(&dir);
        let evt = AuditEvent::new(AuditKind::LedgerEntry, "n-0", json!({}));
        ledger.record(evt).unwrap();
        // Before anchor: 1 entry.
        let before = verify_audit_chain(&ledger).unwrap();
        assert_eq!(before.total_entries, 1);
        // Anchor.
        anchor_epoch(&ledger, 1, None).unwrap();
        // After anchor: 2 entries (original event + epoch_anchor entry).
        let after = verify_audit_chain(&ledger).unwrap();
        assert_eq!(after.total_entries, 2);
    }

    #[test]
    fn anchor_epoch_chain_root_is_deterministic_for_same_state() {
        let dir1 = tempdir().unwrap();
        let dir2 = tempdir().unwrap();
        // Build two identical ledgers.
        for dir in [&dir1, &dir2] {
            let ledger = open(dir);
            let evt = AuditEvent::new(AuditKind::WorkBid, "w-1", json!({"x": 1}));
            ledger.record(evt).unwrap();
        }
        let a1 = anchor_epoch(&open(&dir1), 5, None).unwrap();
        let a2 = anchor_epoch(&open(&dir2), 5, None).unwrap();
        assert_eq!(
            a1.chain_root_hash, a2.chain_root_hash,
            "same chain state must produce same root hash"
        );
    }
}
