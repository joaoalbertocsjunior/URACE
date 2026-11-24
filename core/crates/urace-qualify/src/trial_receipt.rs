//! Trial receipts: cross-peer signed receipts for token settlement.
//!
//! A `TrialReceipt` is created by the borrower after a successful local
//! qualification and delivered to the creator peer. The `ReceiptStore` is
//! append-only — entries are never deleted or mutated after write.
//!
//! Security: relay-prevention is enforced — `sender_peer_id` must match
//! `borrower_peer_id`; relayed receipts are rejected.

use serde::{Deserialize, Serialize};
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum ReceiptError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("schema mismatch: expected urace-qualify-receipt-v1, got {0}")]
    SchemaMismatch(String),
    #[error("relay rejected: sender_peer_id does not match borrower_peer_id")]
    RelayRejected,
    #[error("invalid receipt: {0}")]
    Invalid(String),
}

/// A signed trial receipt created by the borrower.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrialReceipt {
    pub schema: String,
    pub feature_id: String,
    pub creator_peer_id: String,
    pub borrower_peer_id: String,
    pub outcome_delta: f64,
    pub at_unix: f64,
}

impl TrialReceipt {
    pub const SCHEMA: &'static str = "urace-qualify-receipt-v1";

    /// Create a new receipt. `at_unix` is set to the current Unix timestamp.
    pub fn new(
        feature_id: impl Into<String>,
        creator_peer_id: impl Into<String>,
        borrower_peer_id: impl Into<String>,
        outcome_delta: f64,
    ) -> Self {
        use std::time::{SystemTime, UNIX_EPOCH};
        let at_unix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        TrialReceipt {
            schema: Self::SCHEMA.to_owned(),
            feature_id: feature_id.into(),
            creator_peer_id: creator_peer_id.into(),
            borrower_peer_id: borrower_peer_id.into(),
            outcome_delta,
            at_unix,
        }
    }

    /// Validate that the schema is correct.
    pub fn validate_schema(&self) -> Result<(), ReceiptError> {
        if self.schema != Self::SCHEMA {
            return Err(ReceiptError::SchemaMismatch(self.schema.clone()));
        }
        Ok(())
    }
}

/// Append-only store for trial receipts backed by a HMAC-signed JSONL journal.
pub struct ReceiptStore {
    journal: Journal,
}

impl ReceiptStore {
    /// Open (or create) a receipt store at `path` with HMAC key `hmac_key`.
    pub fn open(
        path: impl AsRef<std::path::Path>,
        hmac_key: [u8; 32],
    ) -> Result<Self, ReceiptError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(ReceiptStore { journal })
    }

    /// Record a receipt (append-only). Validates schema before writing.
    pub fn record(&self, receipt: &TrialReceipt) -> Result<(), ReceiptError> {
        receipt.validate_schema()?;
        let payload = serde_json::to_value(receipt)?;
        self.journal.append("TRIAL_RECEIPT", payload)?;
        Ok(())
    }

    /// Handle incoming receipt delivery with relay-prevention.
    ///
    /// Returns `Err(ReceiptError::RelayRejected)` if `sender_peer_id != borrower_peer_id`.
    pub fn handle_delivery(
        &self,
        sender_peer_id: &str,
        receipt: &TrialReceipt,
    ) -> Result<(), ReceiptError> {
        receipt.validate_schema()?;
        // Relay-prevention: sender must be the borrower.
        if sender_peer_id != receipt.borrower_peer_id {
            return Err(ReceiptError::RelayRejected);
        }
        self.record(receipt)
    }

    /// Return all receipts for `feature_id`.
    pub fn receipts_for_feature(&self, feature_id: &str) -> Result<Vec<TrialReceipt>, ReceiptError> {
        let entries = self.journal.verify_integrity()?;
        let receipts = entries
            .into_iter()
            .filter(|e| e.kind == "TRIAL_RECEIPT")
            .filter_map(|e| serde_json::from_value::<TrialReceipt>(e.payload).ok())
            .filter(|r| r.feature_id == feature_id)
            .collect();
        Ok(receipts)
    }

    /// Return all receipts in the store.
    pub fn all_receipts(&self) -> Result<Vec<TrialReceipt>, ReceiptError> {
        let entries = self.journal.verify_integrity()?;
        let receipts = entries
            .into_iter()
            .filter(|e| e.kind == "TRIAL_RECEIPT")
            .filter_map(|e| serde_json::from_value::<TrialReceipt>(e.payload).ok())
            .collect();
        Ok(receipts)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"receipt-store-key-32bytes-pad---";

    fn sample_receipt(feature: &str, borrower: &str, creator: &str) -> TrialReceipt {
        TrialReceipt::new(feature, creator, borrower, 0.5)
    }

    #[test]
    fn receipt_roundtrip() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        let r = sample_receipt("feat-1", "peer-borrower", "peer-creator");
        store.record(&r).unwrap();

        let all = store.all_receipts().unwrap();
        assert_eq!(all.len(), 1);
        assert_eq!(all[0].feature_id, "feat-1");
        assert_eq!(all[0].borrower_peer_id, "peer-borrower");
        assert_eq!(all[0].creator_peer_id, "peer-creator");
        assert_eq!(all[0].schema, TrialReceipt::SCHEMA);
    }

    #[test]
    fn relay_rejected() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        let r = sample_receipt("feat-1", "real-borrower", "creator");
        // sender_peer_id differs from borrower_peer_id — must be rejected.
        let result = store.handle_delivery("relay-node", &r);
        assert!(matches!(result, Err(ReceiptError::RelayRejected)));
    }

    #[test]
    fn direct_delivery_accepted() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        let r = sample_receipt("feat-1", "borrower-a", "creator-b");
        // sender == borrower — must succeed.
        store.handle_delivery("borrower-a", &r).unwrap();

        let all = store.all_receipts().unwrap();
        assert_eq!(all.len(), 1);
    }

    #[test]
    fn filter_by_feature() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        store.record(&sample_receipt("feat-1", "b1", "c1")).unwrap();
        store.record(&sample_receipt("feat-2", "b2", "c2")).unwrap();
        store.record(&sample_receipt("feat-1", "b3", "c3")).unwrap();

        let feat1 = store.receipts_for_feature("feat-1").unwrap();
        assert_eq!(feat1.len(), 2);
        assert!(feat1.iter().all(|r| r.feature_id == "feat-1"));
    }

    #[test]
    fn schema_validation_rejects_wrong_schema() {
        let mut r = TrialReceipt::new("f", "c", "b", 1.0);
        r.schema = "wrong-schema-v99".to_owned();
        assert!(matches!(r.validate_schema(), Err(ReceiptError::SchemaMismatch(_))));
    }
}
