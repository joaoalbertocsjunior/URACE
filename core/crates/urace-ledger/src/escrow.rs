//! Escrow store — append-only, monotonic-time release decisions.
//!
//! Ported from `escrow_timeout.py`.
//!
//! # Invariants (from `runtime/urace/CLAUDE.md`):
//! - Escrow release uses **monotonic time only** — never wall-clock `SystemTime::now()`.
//! - Release checks that the caller == `payer_peer_id` who locked the escrow.
//! - The store is append-only (backed by `Journal`); entries are never deleted.

use crate::journal::{Journal, JournalError};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::path::Path;
use thiserror::Error;
use uuid::Uuid;

/// A single escrow lock entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EscrowEntry {
    pub id: String,
    /// Peer who locked the escrow (the payer / buyer).
    pub payer_peer_id: String,
    /// Amount locked, in UCR base units.
    pub amount_ucr: i64,
    /// Monotonic seconds since process start when lock was created.
    pub locked_at: u64,
    /// Monotonic seconds at which the escrow may be released.
    pub release_at: u64,
    /// Whether the escrow has been released.
    pub released: bool,
}

#[derive(Debug, Error)]
pub enum EscrowError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("escrow {0} not found")]
    NotFound(String),
    #[error("escrow {0} already released")]
    AlreadyReleased(String),
    #[error("escrow {0} not yet expired (monotonic_now={1}, release_at={2})")]
    NotExpired(String, u64, u64),
    #[error("caller {caller} is not the payer {payer} for escrow {id}")]
    UnauthorizedRelease {
        id: String,
        caller: String,
        payer: String,
    },
    #[error("amount must be positive, got {0}")]
    NonPositiveAmount(i64),
}

/// Append-only escrow store backed by a `Journal`.
///
/// Entries are written as `ESCROW_LOCK` and `ESCROW_RELEASE` rows.
/// Balance is derived by replaying the journal.
pub struct EscrowStore {
    journal: Journal,
}

impl EscrowStore {
    /// Open (or create) an escrow store at `path`.
    pub fn open(path: impl AsRef<Path>, hmac_key: [u8; 32]) -> Result<Self, EscrowError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(EscrowStore { journal })
    }

    /// Lock `amount_ucr` for `payer_peer_id`, to be released after `duration_secs`
    /// monotonic seconds.
    ///
    /// `monotonic_now` must be provided by the caller (from `Instant::elapsed`
    /// or a passed-in clock) — never use `SystemTime::now()` for release decisions.
    pub fn lock(
        &self,
        payer_peer_id: impl Into<String>,
        amount_ucr: i64,
        duration_secs: u64,
        monotonic_now: u64,
    ) -> Result<EscrowEntry, EscrowError> {
        if amount_ucr <= 0 {
            return Err(EscrowError::NonPositiveAmount(amount_ucr));
        }
        let payer_peer_id = payer_peer_id.into();
        let id = Uuid::new_v4().to_string();
        let release_at = monotonic_now + duration_secs;
        let entry = EscrowEntry {
            id: id.clone(),
            payer_peer_id: payer_peer_id.clone(),
            amount_ucr,
            locked_at: monotonic_now,
            release_at,
            released: false,
        };
        self.journal.append(
            "ESCROW_LOCK",
            json!({
                "id": id,
                "payer_peer_id": payer_peer_id,
                "amount_ucr": amount_ucr,
                "locked_at": monotonic_now,
                "release_at": release_at,
            }),
        )?;
        Ok(entry)
    }

    /// Release escrow `id`. Checks:
    /// 1. Caller == payer_peer_id (the party who locked it).
    /// 2. Monotonic time has passed `release_at`.
    /// 3. Escrow has not already been released.
    ///
    /// `monotonic_now` must be provided by the caller.
    pub fn release(
        &self,
        id: &str,
        caller_peer_id: &str,
        monotonic_now: u64,
    ) -> Result<EscrowEntry, EscrowError> {
        let mut entry = self.find(id)?;
        if entry.released {
            return Err(EscrowError::AlreadyReleased(id.to_owned()));
        }
        if caller_peer_id != entry.payer_peer_id {
            return Err(EscrowError::UnauthorizedRelease {
                id: id.to_owned(),
                caller: caller_peer_id.to_owned(),
                payer: entry.payer_peer_id.clone(),
            });
        }
        if monotonic_now < entry.release_at {
            return Err(EscrowError::NotExpired(
                id.to_owned(),
                monotonic_now,
                entry.release_at,
            ));
        }
        self.journal.append(
            "ESCROW_RELEASE",
            json!({
                "id": id,
                "payer_peer_id": &entry.payer_peer_id,
                "released_at": monotonic_now,
            }),
        )?;
        entry.released = true;
        Ok(entry)
    }

    /// Returns `true` if escrow `id` exists, is not released, and monotonic time
    /// has passed `release_at`.
    pub fn is_expired(&self, id: &str, monotonic_now: u64) -> Result<bool, EscrowError> {
        let entry = self.find(id)?;
        Ok(!entry.released && monotonic_now >= entry.release_at)
    }

    /// Load all escrow entries by replaying the journal.
    pub fn entries(&self) -> Result<Vec<EscrowEntry>, EscrowError> {
        let rows = self.journal.verify_integrity()?;
        let mut locks: std::collections::HashMap<String, EscrowEntry> =
            std::collections::HashMap::new();

        for row in rows {
            match row.kind.as_str() {
                "ESCROW_LOCK" => {
                    let p = &row.payload;
                    let id = p["id"].as_str().unwrap_or_default().to_owned();
                    let entry = EscrowEntry {
                        id: id.clone(),
                        payer_peer_id: p["payer_peer_id"].as_str().unwrap_or_default().to_owned(),
                        amount_ucr: p["amount_ucr"].as_i64().unwrap_or_default(),
                        locked_at: p["locked_at"].as_u64().unwrap_or_default(),
                        release_at: p["release_at"].as_u64().unwrap_or_default(),
                        released: false,
                    };
                    locks.insert(id, entry);
                }
                "ESCROW_RELEASE" => {
                    let id = row.payload["id"].as_str().unwrap_or_default();
                    if let Some(e) = locks.get_mut(id) {
                        e.released = true;
                    }
                }
                _ => {}
            }
        }

        Ok(locks.into_values().collect())
    }

    fn find(&self, id: &str) -> Result<EscrowEntry, EscrowError> {
        self.entries()?
            .into_iter()
            .find(|e| e.id == id)
            .ok_or_else(|| EscrowError::NotFound(id.to_owned()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"urace-escrow-key-32bytes--------";
    const UNIT: i64 = 100_000_000;

    fn open(dir: &tempfile::TempDir) -> EscrowStore {
        EscrowStore::open(dir.path().join("escrow.jsonl"), KEY).unwrap()
    }

    #[test]
    fn lock_creates_entry() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        let entry = store.lock("peer-1", UNIT, 3600, 0).unwrap();
        assert_eq!(entry.payer_peer_id, "peer-1");
        assert_eq!(entry.amount_ucr, UNIT);
        assert!(!entry.released);
        assert_eq!(entry.release_at, 3600);
    }

    #[test]
    fn release_after_expiry() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        let entry = store.lock("peer-1", UNIT, 100, 0).unwrap();
        // monotonic_now = 200 >= release_at = 100
        let released = store.release(&entry.id, "peer-1", 200).unwrap();
        assert!(released.released);
    }

    #[test]
    fn release_before_expiry_errors() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        let entry = store.lock("peer-1", UNIT, 1000, 0).unwrap();
        let err = store.release(&entry.id, "peer-1", 500).unwrap_err();
        assert!(matches!(err, EscrowError::NotExpired(..)));
    }

    #[test]
    fn unauthorized_release_rejected() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        let entry = store.lock("peer-1", UNIT, 0, 0).unwrap();
        let err = store.release(&entry.id, "peer-2", 1).unwrap_err();
        assert!(matches!(err, EscrowError::UnauthorizedRelease { .. }));
    }

    #[test]
    fn double_release_rejected() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        let entry = store.lock("peer-1", UNIT, 0, 0).unwrap();
        store.release(&entry.id, "peer-1", 1).unwrap();
        let err = store.release(&entry.id, "peer-1", 2).unwrap_err();
        assert!(matches!(err, EscrowError::AlreadyReleased(_)));
    }

    #[test]
    fn is_expired_checks_time() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        let entry = store.lock("peer-1", UNIT, 100, 0).unwrap();
        assert!(!store.is_expired(&entry.id, 50).unwrap());
        assert!(store.is_expired(&entry.id, 100).unwrap());
        assert!(store.is_expired(&entry.id, 200).unwrap());
    }

    #[test]
    fn non_positive_amount_rejected() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        assert!(matches!(
            store.lock("peer-1", 0, 100, 0),
            Err(EscrowError::NonPositiveAmount(0))
        ));
        assert!(matches!(
            store.lock("peer-1", -1, 100, 0),
            Err(EscrowError::NonPositiveAmount(-1))
        ));
    }

    #[test]
    fn journal_replay_preserves_released_state() {
        let dir = tempdir().unwrap();
        let store = open(&dir);
        let e1 = store.lock("peer-1", UNIT, 0, 0).unwrap();
        let _e2 = store.lock("peer-2", UNIT * 2, 1000, 0).unwrap();
        store.release(&e1.id, "peer-1", 1).unwrap();

        let entries = store.entries().unwrap();
        let e1_rep = entries.iter().find(|e| e.id == e1.id).unwrap();
        assert!(e1_rep.released);
        // e2 not released
        let e2_rep = entries
            .iter()
            .find(|e| e.payer_peer_id == "peer-2")
            .unwrap();
        assert!(!e2_rep.released);
    }
}
