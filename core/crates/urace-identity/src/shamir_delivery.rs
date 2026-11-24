//! Shamir share delivery tracking.
//!
//! Tracks which shares have been delivered to which peers.
//! In-memory state is backed by an append-only Journal via `urace-ledger`.
//!
//! Invariants:
//! - Delivery records are append-only — no row is deleted or mutated after write.
//! - `mark_delivered` is idempotent: marking an already-delivered share is a no-op.

use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum DeliveryError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("share not found: {0}")]
    NotFound(String),
}

/// A record of one share being delivered to one recipient peer.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ShareDelivery {
    pub share_id: String,
    pub recipient_peer_id: String,
    /// Shamir x-coordinate (1-indexed).
    pub x: u8,
    pub delivered: bool,
    pub delivered_at: Option<String>,
}

fn now_unix_secs() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string())
}

/// Composite key: (share_id, recipient_peer_id).
type DeliveryKey = (String, String);

/// Tracks share delivery state in memory + an append-only Journal.
pub struct DeliveryTracker {
    state: Mutex<HashMap<DeliveryKey, ShareDelivery>>,
    journal: Journal,
}

impl DeliveryTracker {
    /// Open a tracker backed by a journal at `journal_path`.
    ///
    /// `hmac_key` is the HMAC-SHA256 key used by the underlying Journal.
    pub fn open(journal_path: &Path, hmac_key: [u8; 32]) -> Result<Self, DeliveryError> {
        let journal = Journal::open(journal_path, hmac_key)?;

        // Replay journal to rebuild in-memory state.
        let mut state: HashMap<DeliveryKey, ShareDelivery> = HashMap::new();
        for entry in journal.verify_integrity()? {
            match entry.kind.as_str() {
                "SHARE_DELIVERY_RECORDED" => {
                    if let Ok(d) =
                        serde_json::from_value::<ShareDelivery>(entry.payload.clone())
                    {
                        let key = (d.share_id.clone(), d.recipient_peer_id.clone());
                        state.insert(key, d);
                    }
                }
                "SHARE_DELIVERY_MARKED" => {
                    let share_id = entry.payload["share_id"].as_str().unwrap_or("").to_string();
                    let recipient_peer_id =
                        entry.payload["recipient_peer_id"].as_str().unwrap_or("").to_string();
                    let delivered_at =
                        entry.payload["delivered_at"].as_str().map(|s| s.to_string());
                    let key = (share_id, recipient_peer_id);
                    if let Some(rec) = state.get_mut(&key) {
                        rec.delivered = true;
                        rec.delivered_at = delivered_at;
                    }
                }
                _ => {}
            }
        }

        Ok(DeliveryTracker { state: Mutex::new(state), journal })
    }

    /// Record that a share `share_id` with Shamir index `x` is destined for `recipient_peer_id`.
    ///
    /// If this (share_id, recipient_peer_id) pair already exists the call is a no-op.
    pub fn record_delivery(
        &self,
        share_id: &str,
        recipient_peer_id: &str,
        x: u8,
    ) -> Result<(), DeliveryError> {
        let key = (share_id.to_string(), recipient_peer_id.to_string());
        let mut guard = self.state.lock();
        if guard.contains_key(&key) {
            return Ok(());
        }
        let delivery = ShareDelivery {
            share_id: share_id.to_string(),
            recipient_peer_id: recipient_peer_id.to_string(),
            x,
            delivered: false,
            delivered_at: None,
        };
        self.journal
            .append("SHARE_DELIVERY_RECORDED", serde_json::to_value(&delivery).unwrap())?;
        guard.insert(key, delivery);
        Ok(())
    }

    /// Mark a previously recorded share as delivered.  Idempotent.
    pub fn mark_delivered(
        &self,
        share_id: &str,
        recipient_peer_id: &str,
    ) -> Result<(), DeliveryError> {
        let key = (share_id.to_string(), recipient_peer_id.to_string());
        let mut guard = self.state.lock();
        let rec = guard
            .get_mut(&key)
            .ok_or_else(|| DeliveryError::NotFound(share_id.to_string()))?;

        if rec.delivered {
            return Ok(()); // idempotent
        }
        let now = now_unix_secs();
        self.journal.append(
            "SHARE_DELIVERY_MARKED",
            json!({
                "share_id": share_id,
                "recipient_peer_id": recipient_peer_id,
                "delivered_at": now,
            }),
        )?;
        rec.delivered = true;
        rec.delivered_at = Some(now);
        Ok(())
    }

    /// Return all ShareDelivery records for a given `share_id`.
    pub fn delivery_status(&self, share_id: &str) -> Vec<ShareDelivery> {
        self.state
            .lock()
            .iter()
            .filter(|((sid, _), _)| sid == share_id)
            .map(|(_, v)| v.clone())
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const HMAC_KEY: [u8; 32] = *b"urace-shamir-hmac-key-32bytes---";

    #[test]
    fn record_and_status() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("delivery.jsonl");
        let tracker = DeliveryTracker::open(&path, HMAC_KEY).unwrap();

        tracker.record_delivery("share-1", "peer-a", 1).unwrap();
        tracker.record_delivery("share-1", "peer-b", 2).unwrap();

        let status = tracker.delivery_status("share-1");
        assert_eq!(status.len(), 2);
        assert!(status.iter().all(|s| !s.delivered));
    }

    #[test]
    fn mark_delivered() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("delivery.jsonl");
        let tracker = DeliveryTracker::open(&path, HMAC_KEY).unwrap();

        tracker.record_delivery("share-2", "peer-x", 1).unwrap();
        tracker.mark_delivered("share-2", "peer-x").unwrap();

        let status = tracker.delivery_status("share-2");
        assert_eq!(status.len(), 1);
        assert!(status[0].delivered);
        assert!(status[0].delivered_at.is_some());
    }

    #[test]
    fn mark_delivered_idempotent() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("delivery.jsonl");
        let tracker = DeliveryTracker::open(&path, HMAC_KEY).unwrap();

        tracker.record_delivery("share-3", "peer-y", 3).unwrap();
        tracker.mark_delivered("share-3", "peer-y").unwrap();
        // Second call must succeed silently.
        tracker.mark_delivered("share-3", "peer-y").unwrap();

        let status = tracker.delivery_status("share-3");
        assert_eq!(status.len(), 1);
        assert!(status[0].delivered);
    }

    #[test]
    fn record_delivery_idempotent() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("delivery.jsonl");
        let tracker = DeliveryTracker::open(&path, HMAC_KEY).unwrap();

        tracker.record_delivery("share-4", "peer-z", 1).unwrap();
        tracker.record_delivery("share-4", "peer-z", 1).unwrap(); // duplicate — no-op

        let status = tracker.delivery_status("share-4");
        assert_eq!(status.len(), 1);
    }

    #[test]
    fn mark_not_recorded_fails() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("delivery.jsonl");
        let tracker = DeliveryTracker::open(&path, HMAC_KEY).unwrap();

        assert!(matches!(
            tracker.mark_delivered("nonexistent", "peer"),
            Err(DeliveryError::NotFound(_))
        ));
    }

    #[test]
    fn journal_replay_on_reopen() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("delivery.jsonl");

        {
            let tracker = DeliveryTracker::open(&path, HMAC_KEY).unwrap();
            tracker.record_delivery("share-5", "peer-r", 2).unwrap();
            tracker.mark_delivered("share-5", "peer-r").unwrap();
        }

        // Reopen and verify state is restored from journal.
        let tracker2 = DeliveryTracker::open(&path, HMAC_KEY).unwrap();
        let status = tracker2.delivery_status("share-5");
        assert_eq!(status.len(), 1);
        assert!(status[0].delivered);
    }
}
