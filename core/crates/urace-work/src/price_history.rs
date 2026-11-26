//! M29 — Price history ledger.
//!
//! Tracks historical bid prices for work tasks in an append-only
//! `urace_ledger::Journal`.  Prices are never modified after recording.

use serde::{Deserialize, Serialize};
use std::path::Path;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum PriceHistoryError {
    #[error("journal: {0}")]
    Journal(#[from] JournalError),
    #[error("serialization: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// A single price observation for a task bid.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriceEntry {
    pub task_id: String,
    pub peer_id: String,
    pub amount_ucr: i64,
    /// Unix timestamp in seconds as a string.
    pub recorded_at: String,
}

/// Append-only price history store backed by a signed JSONL journal.
pub struct PriceHistory {
    journal: Journal,
}

impl PriceHistory {
    /// Open (or create) a price history journal at `path`.
    pub fn open(path: impl AsRef<Path>, hmac_key: [u8; 32]) -> Result<Self, PriceHistoryError> {
        Ok(PriceHistory {
            journal: Journal::open(path, hmac_key)?,
        })
    }

    /// Append a price entry for a task.
    pub fn record(&self, entry: PriceEntry) -> Result<(), PriceHistoryError> {
        let payload = serde_json::to_value(&entry)?;
        self.journal.append("PRICE_ENTRY", payload)?;
        Ok(())
    }

    /// Return all price entries for `task_id` in insertion order.
    pub fn entries_for_task(&self, task_id: &str) -> Result<Vec<PriceEntry>, PriceHistoryError> {
        let all = self.all_entries()?;
        Ok(all.into_iter().filter(|e| e.task_id == task_id).collect())
    }

    /// Return every `PRICE_ENTRY` record from the journal.
    pub fn all_entries(&self) -> Result<Vec<PriceEntry>, PriceHistoryError> {
        let entries = self.journal.verify_integrity()?;
        let result = entries
            .into_iter()
            .filter(|e| e.kind == "PRICE_ENTRY")
            .filter_map(|e| serde_json::from_value::<PriceEntry>(e.payload).ok())
            .collect();
        Ok(result)
    }

    /// Average bid price for `task_id`.  Returns `None` when no entries exist.
    pub fn average_price(&self, task_id: &str) -> Result<Option<f64>, PriceHistoryError> {
        let entries = self.entries_for_task(task_id)?;
        if entries.is_empty() {
            return Ok(None);
        }
        let sum: i64 = entries.iter().map(|e| e.amount_ucr).sum();
        Ok(Some(sum as f64 / entries.len() as f64))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"price-history-key-32bytes-pad---";

    fn entry(task_id: &str, peer_id: &str, amount: i64) -> PriceEntry {
        PriceEntry {
            task_id: task_id.to_owned(),
            peer_id: peer_id.to_owned(),
            amount_ucr: amount,
            recorded_at: "1700000000".to_owned(),
        }
    }

    #[test]
    fn record_and_query_by_task() {
        let dir = tempdir().unwrap();
        let ph = PriceHistory::open(dir.path().join("prices.jsonl"), KEY).unwrap();

        ph.record(entry("task-a", "peer-1", 1_000)).unwrap();
        ph.record(entry("task-b", "peer-2", 2_000)).unwrap();
        ph.record(entry("task-a", "peer-3", 1_500)).unwrap();

        let entries_a = ph.entries_for_task("task-a").unwrap();
        assert_eq!(entries_a.len(), 2);
        assert!(entries_a.iter().all(|e| e.task_id == "task-a"));

        let entries_b = ph.entries_for_task("task-b").unwrap();
        assert_eq!(entries_b.len(), 1);
        assert_eq!(entries_b[0].amount_ucr, 2_000);
    }

    #[test]
    fn average_price_calculation() {
        let dir = tempdir().unwrap();
        let ph = PriceHistory::open(dir.path().join("prices.jsonl"), KEY).unwrap();

        ph.record(entry("task-x", "peer-1", 1_000)).unwrap();
        ph.record(entry("task-x", "peer-2", 3_000)).unwrap();
        ph.record(entry("task-x", "peer-3", 2_000)).unwrap();

        let avg = ph.average_price("task-x").unwrap().unwrap();
        assert!(
            (avg - 2_000.0_f64).abs() < f64::EPSILON,
            "expected average 2000, got {avg}"
        );
    }

    #[test]
    fn empty_task_returns_none() {
        let dir = tempdir().unwrap();
        let ph = PriceHistory::open(dir.path().join("prices.jsonl"), KEY).unwrap();

        let avg = ph.average_price("nonexistent").unwrap();
        assert!(avg.is_none());
    }
}
