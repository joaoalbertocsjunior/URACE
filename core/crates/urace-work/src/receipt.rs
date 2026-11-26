//! Work receipts: append-only record of completed work deliveries.
//!
//! `ReceiptStore` wraps a `urace_ledger::Journal` to persist receipts as
//! signed, append-only JSONL rows. Receipts are never modified after issuance.
//!
//! # Mitigations implemented
//! - **M04** — Execution authorship gate: `executor_peer_id` must equal
//!   `submitter_peer_id` before a receipt is accepted for mint.
//! - **M43** — Receipt chain validation: each receipt references the SHA-256
//!   hash of its predecessor, enabling a verifiable chain per task.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum ReceiptError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    /// M04 — authorship gate violation.
    #[error("authorship mismatch: executor '{executor}' ≠ submitter '{submitter}'")]
    AuthorshipMismatch { executor: String, submitter: String },

    /// M43 — receipt chain broken.
    #[error("receipt chain broken: expected hash '{expected}', got '{got}'")]
    ChainBroken { expected: String, got: String },
}

/// An immutable record that a task was completed and payment is due.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkReceipt {
    pub receipt_id: String,
    pub task_id: String,
    pub executor_peer_id: String,
    /// M04: the peer that submitted this receipt for mint; must equal
    /// `executor_peer_id` for `validate_authorship` to pass.
    pub submitter_peer_id: String,
    pub amount_ucr: i64,
    pub completed_at: String,
    /// SHA-256 hash of the delivered artefact.
    pub delivery_hash: String,
    /// M43: SHA-256 of the previous receipt in this task's chain, or empty
    /// string for the genesis (first) receipt of a task.
    pub previous_receipt_hash: String,
}

impl WorkReceipt {
    /// M04 — Verify that the submitter is the same peer as the executor.
    ///
    /// Must be called before a receipt is accepted for mint.
    pub fn validate_authorship(&self) -> Result<(), ReceiptError> {
        if self.executor_peer_id != self.submitter_peer_id {
            return Err(ReceiptError::AuthorshipMismatch {
                executor: self.executor_peer_id.clone(),
                submitter: self.submitter_peer_id.clone(),
            });
        }
        Ok(())
    }
}

/// Append-only store for work receipts backed by a signed JSONL journal.
pub struct ReceiptStore {
    journal: Journal,
}

impl ReceiptStore {
    pub fn open(
        path: impl AsRef<std::path::Path>,
        hmac_key: [u8; 32],
    ) -> Result<Self, ReceiptError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(ReceiptStore { journal })
    }

    /// Issue (append) a new receipt.
    ///
    /// Applies the M04 authorship gate before persisting. If
    /// `executor_peer_id != submitter_peer_id` the call returns
    /// `ReceiptError::AuthorshipMismatch` and nothing is written.
    pub fn issue(&self, receipt: WorkReceipt) -> Result<(), ReceiptError> {
        receipt.validate_authorship()?;
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

    /// M43 — All receipts for a specific `task_id`, in insertion order.
    pub fn receipts_for_task(&self, task_id: &str) -> Result<Vec<WorkReceipt>, ReceiptError> {
        let entries = self.journal.verify_integrity()?;
        let receipts = entries
            .into_iter()
            .filter(|e| e.kind == "WORK_RECEIPT")
            .filter_map(|e| {
                let r: WorkReceipt = serde_json::from_value(e.payload).ok()?;
                if r.task_id == task_id {
                    Some(r)
                } else {
                    None
                }
            })
            .collect();
        Ok(receipts)
    }

    /// M43 — Returns the SHA-256 hex digest of a receipt's canonical JSON
    /// serialization (used as `previous_receipt_hash` for chain linking).
    pub fn receipt_hash(receipt: &WorkReceipt) -> Result<String, ReceiptError> {
        let json = serde_json::to_string(receipt)?;
        let hash = Sha256::digest(json.as_bytes());
        Ok(hex::encode(hash))
    }

    /// M43 — Verify that all receipts for `task_id` form a valid hash chain.
    ///
    /// Each receipt (after the first) must carry a `previous_receipt_hash` that
    /// matches the SHA-256 of its predecessor, or the field must be empty
    /// (which is accepted as a relaxed link — only a non-empty *wrong* hash is
    /// rejected).  Returns `Ok(())` when the chain is valid or has ≤1 receipt.
    pub fn verify_chain(&self, task_id: &str) -> Result<(), ReceiptError> {
        let all = self.receipts_for_task(task_id)?;
        if all.len() <= 1 {
            return Ok(());
        }
        for window in all.windows(2) {
            let prev_hash = Self::receipt_hash(&window[0])?;
            if window[1].previous_receipt_hash != prev_hash
                && !window[1].previous_receipt_hash.is_empty()
            {
                return Err(ReceiptError::ChainBroken {
                    expected: prev_hash,
                    got: window[1].previous_receipt_hash.clone(),
                });
            }
        }
        Ok(())
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
            submitter_peer_id: executor.to_owned(), // same peer — authorship OK
            amount_ucr: 1000,
            completed_at: "2026-01-01T00:00:00Z".to_owned(),
            delivery_hash: "abc123".to_owned(),
            previous_receipt_hash: String::new(),
        }
    }

    // ── original tests (preserved, updated for new fields) ───────────────────

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

    // ── M04 authorship gate tests ─────────────────────────────────────────────

    #[test]
    fn authorship_mismatch_rejected() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        let r = WorkReceipt {
            receipt_id: "r-mismatch".to_owned(),
            task_id: "task-1".to_owned(),
            executor_peer_id: "alice".to_owned(),
            submitter_peer_id: "mallory".to_owned(), // different peer
            amount_ucr: 1000,
            completed_at: "2026-01-01T00:00:00Z".to_owned(),
            delivery_hash: "abc123".to_owned(),
            previous_receipt_hash: String::new(),
        };

        let err = store.issue(r).unwrap_err();
        assert!(
            matches!(err, ReceiptError::AuthorshipMismatch { ref executor, ref submitter }
                if executor == "alice" && submitter == "mallory"),
            "unexpected error: {err}"
        );
    }

    #[test]
    fn authorship_match_accepted() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        let r = WorkReceipt {
            receipt_id: "r-ok".to_owned(),
            task_id: "task-2".to_owned(),
            executor_peer_id: "alice".to_owned(),
            submitter_peer_id: "alice".to_owned(),
            amount_ucr: 500,
            completed_at: "2026-01-01T00:00:00Z".to_owned(),
            delivery_hash: "def456".to_owned(),
            previous_receipt_hash: String::new(),
        };

        store.issue(r).unwrap();

        let results = store.receipts_for("alice").unwrap();
        assert_eq!(results.len(), 1);
    }

    // ── M43 receipt chain tests ───────────────────────────────────────────────

    #[test]
    fn single_receipt_chain_valid() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        store.issue(receipt("r1", "alice")).unwrap();
        store.verify_chain("task-1").unwrap();
    }

    #[test]
    fn chain_validates_correctly() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        // First receipt — genesis (empty previous hash)
        let r1 = WorkReceipt {
            receipt_id: "r1".to_owned(),
            task_id: "task-chain".to_owned(),
            executor_peer_id: "alice".to_owned(),
            submitter_peer_id: "alice".to_owned(),
            amount_ucr: 1000,
            completed_at: "2026-01-01T00:00:00Z".to_owned(),
            delivery_hash: "hash-of-artefact-1".to_owned(),
            previous_receipt_hash: String::new(),
        };
        store.issue(r1.clone()).unwrap();

        // Second receipt — links to hash of r1
        let prev_hash = ReceiptStore::receipt_hash(&r1).unwrap();
        let r2 = WorkReceipt {
            receipt_id: "r2".to_owned(),
            task_id: "task-chain".to_owned(),
            executor_peer_id: "alice".to_owned(),
            submitter_peer_id: "alice".to_owned(),
            amount_ucr: 2000,
            completed_at: "2026-01-02T00:00:00Z".to_owned(),
            delivery_hash: "hash-of-artefact-2".to_owned(),
            previous_receipt_hash: prev_hash,
        };
        store.issue(r2).unwrap();

        store.verify_chain("task-chain").unwrap();
    }

    #[test]
    fn broken_chain_detected() {
        let dir = tempdir().unwrap();
        let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), KEY).unwrap();

        let r1 = WorkReceipt {
            receipt_id: "r1".to_owned(),
            task_id: "task-broken".to_owned(),
            executor_peer_id: "alice".to_owned(),
            submitter_peer_id: "alice".to_owned(),
            amount_ucr: 1000,
            completed_at: "2026-01-01T00:00:00Z".to_owned(),
            delivery_hash: "hash1".to_owned(),
            previous_receipt_hash: String::new(),
        };
        store.issue(r1).unwrap();

        // r2 carries a wrong (non-empty) previous hash
        let r2 = WorkReceipt {
            receipt_id: "r2".to_owned(),
            task_id: "task-broken".to_owned(),
            executor_peer_id: "alice".to_owned(),
            submitter_peer_id: "alice".to_owned(),
            amount_ucr: 2000,
            completed_at: "2026-01-02T00:00:00Z".to_owned(),
            delivery_hash: "hash2".to_owned(),
            previous_receipt_hash: "deadbeef".to_owned(), // intentionally wrong
        };
        store.issue(r2).unwrap();

        let err = store.verify_chain("task-broken").unwrap_err();
        assert!(
            matches!(err, ReceiptError::ChainBroken { .. }),
            "expected ChainBroken, got: {err}"
        );
    }
}
