//! Pure work-market data types: `WorkTask`, `WorkBid`, `WorkReceipt`.
//!
//! This crate has no dependency on `urace-authority` or `urace-ledger`.
//! It is the boundary layer for crates that need these types without pulling
//! in the full work-market stack.

use serde::{Deserialize, Serialize};

// ── WorkBid ──────────────────────────────────────────────────────────────────

/// A bid submitted by an executor peer for a specific task.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WorkBid {
    pub bid_id: String,
    pub executor_peer_id: String,
    pub task_id: String,
    pub bid_price_ucr: i64,
    pub capabilities: Vec<String>,
    pub submitted_at: String,
}

// ── WorkTask ─────────────────────────────────────────────────────────────────

/// A work task posted to the market.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WorkTask {
    pub task_id: String,
    pub required_capabilities: Vec<String>,
    pub budget_ucr: i64,
    pub posted_at: String,
    pub poster_peer_id: String,
}

// ── WorkReceipt ──────────────────────────────────────────────────────────────

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

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn work_bid_serialises_and_deserialises() {
        let bid = WorkBid {
            bid_id: "b1".to_owned(),
            executor_peer_id: "exec-peer".to_owned(),
            task_id: "t1".to_owned(),
            bid_price_ucr: 500,
            capabilities: vec!["rust".to_owned(), "p2p".to_owned()],
            submitted_at: "2026-01-01T00:01:00Z".to_owned(),
        };
        let json = serde_json::to_string(&bid).unwrap();
        let roundtrip: WorkBid = serde_json::from_str(&json).unwrap();
        assert_eq!(roundtrip.bid_id, bid.bid_id);
        assert_eq!(roundtrip.bid_price_ucr, bid.bid_price_ucr);
        assert_eq!(roundtrip.capabilities, bid.capabilities);
    }

    #[test]
    fn work_task_serialises_and_deserialises() {
        let task = WorkTask {
            task_id: "t1".to_owned(),
            required_capabilities: vec!["rust".to_owned()],
            budget_ucr: 1000,
            posted_at: "2026-01-01T00:00:00Z".to_owned(),
            poster_peer_id: "poster-peer".to_owned(),
        };
        let json = serde_json::to_string(&task).unwrap();
        let roundtrip: WorkTask = serde_json::from_str(&json).unwrap();
        assert_eq!(roundtrip.task_id, task.task_id);
        assert_eq!(roundtrip.budget_ucr, task.budget_ucr);
        assert_eq!(roundtrip.required_capabilities, task.required_capabilities);
    }

    #[test]
    fn work_receipt_serialises_and_deserialises() {
        let receipt = WorkReceipt {
            receipt_id: "r1".to_owned(),
            task_id: "t1".to_owned(),
            executor_peer_id: "alice".to_owned(),
            submitter_peer_id: "alice".to_owned(),
            amount_ucr: 1000,
            completed_at: "2026-01-01T00:00:00Z".to_owned(),
            delivery_hash: "abc123".to_owned(),
            previous_receipt_hash: String::new(),
        };
        let json = serde_json::to_string(&receipt).unwrap();
        let roundtrip: WorkReceipt = serde_json::from_str(&json).unwrap();
        assert_eq!(roundtrip.receipt_id, receipt.receipt_id);
        assert_eq!(roundtrip.amount_ucr, receipt.amount_ucr);
        assert_eq!(roundtrip.delivery_hash, receipt.delivery_hash);
    }

    #[test]
    fn work_bid_with_zero_capabilities_is_valid() {
        // WorkBid is a pure data type — no validation, empty capabilities is fine.
        let bid = WorkBid {
            bid_id: "b-empty".to_owned(),
            executor_peer_id: "exec".to_owned(),
            task_id: "t1".to_owned(),
            bid_price_ucr: 100,
            capabilities: vec![],
            submitted_at: "2026-01-01T00:00:00Z".to_owned(),
        };
        assert!(bid.capabilities.is_empty());
        // Can round-trip through JSON without error.
        let json = serde_json::to_string(&bid).unwrap();
        let roundtrip: WorkBid = serde_json::from_str(&json).unwrap();
        assert!(roundtrip.capabilities.is_empty());
    }

    #[test]
    fn two_work_tasks_with_same_task_id_are_structurally_equal() {
        let t1 = WorkTask {
            task_id: "shared-id".to_owned(),
            required_capabilities: vec!["p2p".to_owned()],
            budget_ucr: 500,
            posted_at: "2026-01-01T00:00:00Z".to_owned(),
            poster_peer_id: "poster".to_owned(),
        };
        let t2 = WorkTask {
            task_id: "shared-id".to_owned(),
            required_capabilities: vec!["p2p".to_owned()],
            budget_ucr: 500,
            posted_at: "2026-01-01T00:00:00Z".to_owned(),
            poster_peer_id: "poster".to_owned(),
        };
        assert_eq!(t1, t2);
    }
}
