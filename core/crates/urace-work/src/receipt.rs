//! Work receipts: append-only record of completed work deliveries.
//!
//! `ReceiptStore` wraps a `urace_ledger::Journal` to persist receipts as
//! signed, append-only JSONL rows. Receipts are never modified after issuance.

use serde::{Deserialize, Serialize};
use serde_json::json;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum ReceiptError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// An immutable record that a task was completed and payment is due.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkReceipt {
    pub receipt_id: String,
    pub task_id: String,
    pub executor_peer_id: String,
    pub amount_ucr: i64,
    pub completed_at: String,
    /// SHA-256 hash of the delivered artefact.
    pub delivery_hash: String,
}

/// Append-only store for work receipts backed by a signed JSONL journal.
pub struct ReceiptStore {
    journal: Journal,
}

impl ReceiptStore {
    pub fn open(path: impl AsRef<std::path::Path>, hmac_key: [u8; 32]) -> Result<Self, ReceiptError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(ReceiptStore { journal })
    }

    /// Issue (append) a new receipt.
    pub fn issue(&self, receipt: WorkReceipt) -> Result<(), ReceiptError> {
        let payload = serde_json::to_value(&receipt)?;
        self.journal.append("WORK_RECEIPT", payload)?;
        Ok(())
    }

    /// Return all receipts for `peer_id` as the executor.
    pub fn receipts_for(&self, peer_id: &str) -> Result<Vec<WorkReceipt>, ReceiptError> {
        let entries = self.journal.verify_integrity()?;
        let receipts = entries
            .into_iter()
            .filter(|e| e.kind == "WORK_RECEIPT")
            .filter_map(|e| {
                let r: WorkReceipt = serde_json::from_value(e.payload).ok()?;
                if r.executor_peer_id == peer_id {
                    Some(r)
                } else {
                    None
                }
            })
            .collect();
        Ok(receipts)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"receipt-store-key-32bytes-pad---";

    fn receipt(id: &str, executor: &str) -> WorkReceipt {
        WorkReceipt {
            receipt_id: id.to_owned(),
            task_id: "task-1".to_owned(),
            executor_peer_id: executor.to_owned(),
            amount_ucr: 1000,
            completed_at: "2026-01-01T00:00:00Z".to_owned(),
            delivery_hash: "abc123".to_owned(),
        }
    }

    #[test]
    fn issue_and_query() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        store.issue(receipt("r1", "alice")).unwrap();
        store.issue(receipt("r2", "bob")).unwrap();
        store.issue(receipt("r3", "alice")).unwrap();

        let alice = store.receipts_for("alice").unwrap();
        assert_eq!(alice.len(), 2);
        assert!(alice.iter().all(|r| r.executor_peer_id == "alice"));

        let bob = store.receipts_for("bob").unwrap();
        assert_eq!(bob.len(), 1);
    }

    #[test]
    fn empty_store_returns_empty_vec() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();
        assert!(store.receipts_for("anyone").unwrap().is_empty());
    }
}
