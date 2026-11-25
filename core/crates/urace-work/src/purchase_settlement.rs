//! Purchase settlement: append-only record of P2P feature purchases.
//!
//! Each `PurchaseSettlement` is written once to a signed journal and
//! never modified. `SettlementStore` provides a running total query.

use serde::{Deserialize, Serialize};
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum SettlementError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// An immutable record of a completed P2P feature purchase.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PurchaseSettlement {
    pub settlement_id: String,
    pub buyer_peer_id: String,
    pub seller_peer_id: String,
    pub amount_ucr: i64,
    pub feature_id: String,
    pub settled_at: String,
}

/// Append-only store for purchase settlements backed by a signed JSONL journal.
pub struct SettlementStore {
    journal: Journal,
}

impl SettlementStore {
    pub fn open(
        path: impl AsRef<std::path::Path>,
        hmac_key: [u8; 32],
    ) -> Result<Self, SettlementError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(SettlementStore { journal })
    }

    /// Record a new settlement (append-only).
    pub fn record(&self, settlement: PurchaseSettlement) -> Result<(), SettlementError> {
        let payload = serde_json::to_value(&settlement)?;
        self.journal.append("PURCHASE_SETTLEMENT", payload)?;
        Ok(())
    }

    /// Return the sum of all settled amounts in UCR base units.
    pub fn total_settled_ucr(&self) -> Result<i64, SettlementError> {
        let entries = self.journal.verify_integrity()?;
        let total = entries
            .into_iter()
            .filter(|e| e.kind == "PURCHASE_SETTLEMENT")
            .filter_map(|e| {
                let s: PurchaseSettlement = serde_json::from_value(e.payload).ok()?;
                Some(s.amount_ucr)
            })
            .sum();
        Ok(total)
    }

    /// Return all settlements for a given buyer.
    pub fn settlements_by_buyer(&self, buyer_peer_id: &str) -> Result<Vec<PurchaseSettlement>, SettlementError> {
        let entries = self.journal.verify_integrity()?;
        let settlements = entries
            .into_iter()
            .filter(|e| e.kind == "PURCHASE_SETTLEMENT")
            .filter_map(|e| {
                let s: PurchaseSettlement = serde_json::from_value(e.payload).ok()?;
                if s.buyer_peer_id == buyer_peer_id {
                    Some(s)
                } else {
                    None
                }
            })
            .collect();
        Ok(settlements)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"settlement-store-key-32bytes----";

    fn settlement(id: &str, buyer: &str, seller: &str, amount: i64) -> PurchaseSettlement {
        PurchaseSettlement {
            settlement_id: id.to_owned(),
            buyer_peer_id: buyer.to_owned(),
            seller_peer_id: seller.to_owned(),
            amount_ucr: amount,
            feature_id: "feat-1".to_owned(),
            settled_at: "2026-01-01T00:00:00Z".to_owned(),
        }
    }

    #[test]
    fn record_and_total() {
        let dir = tempdir().unwrap();
        let store = SettlementStore::open(dir.path().join("settlements.jsonl"), KEY).unwrap();

        store.record(settlement("s1", "alice", "bob", 100)).unwrap();
        store.record(settlement("s2", "alice", "carol", 200)).unwrap();
        store.record(settlement("s3", "dave", "bob", 50)).unwrap();

        assert_eq!(store.total_settled_ucr().unwrap(), 350);
    }

    #[test]
    fn filter_by_buyer() {
        let dir = tempdir().unwrap();
        let store = SettlementStore::open(dir.path().join("settlements.jsonl"), KEY).unwrap();

        store.record(settlement("s1", "alice", "bob", 100)).unwrap();
        store.record(settlement("s2", "dave", "carol", 200)).unwrap();

        let alice = store.settlements_by_buyer("alice").unwrap();
        assert_eq!(alice.len(), 1);
        assert_eq!(alice[0].amount_ucr, 100);
    }

    #[test]
    fn empty_store_total_is_zero() {
        let dir = tempdir().unwrap();
        let store = SettlementStore::open(dir.path().join("settlements.jsonl"), KEY).unwrap();
        assert_eq!(store.total_settled_ucr().unwrap(), 0);
    }
}
