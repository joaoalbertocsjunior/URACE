//! UCR credit/debit ledger — append-only, double-spend protected.
//!
//! Invariants:
//! - Every debit checks balance before deducting (read-modify-write under lock).
//! - Balance is derived by replaying the journal — no mutable balance field.
//! - `UNIT = 10^8 UCR`. Peer cap: 50 UNIT.

use crate::journal::{Journal, JournalError};
use parking_lot::Mutex;
use serde_json::json;
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;
use urace_types::CreditEntry;
use uuid::Uuid;

pub const UNIT: i64 = 100_000_000;
pub const PEER_CAP: i64 = 50 * UNIT;

#[derive(Debug, Error)]
pub enum CreditError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("insufficient balance: have {have}, need {need}")]
    InsufficientBalance { have: i64, need: i64 },
    #[error("peer cap exceeded: cap {cap}, would reach {would_reach}")]
    PeerCapExceeded { cap: i64, would_reach: i64 },
    #[error("amount must be positive, got {0}")]
    NonPositiveAmount(i64),
}

pub struct CreditLedger {
    journal: Journal,
    lock: Mutex<()>,
}

impl CreditLedger {
    pub fn open(path: impl AsRef<Path>, hmac_key: [u8; 32]) -> Result<Self, CreditError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(CreditLedger {
            journal,
            lock: Mutex::new(()),
        })
    }

    /// Replay journal to compute balances for all peers.
    pub fn balances(&self) -> Result<HashMap<String, i64>, CreditError> {
        let entries = self.journal.verify_integrity()?;
        let mut balances: HashMap<String, i64> = HashMap::new();
        for entry in &entries {
            if entry.kind == "CREDIT" || entry.kind == "DEBIT" {
                if let (Some(peer), Some(amount)) = (
                    entry.payload.get("peer_id").and_then(|v| v.as_str()),
                    entry.payload.get("amount_ucr").and_then(|v| v.as_i64()),
                ) {
                    *balances.entry(peer.to_owned()).or_insert(0) += amount;
                }
            }
        }
        Ok(balances)
    }

    pub fn balance(&self, peer_id: &str) -> Result<i64, CreditError> {
        Ok(*self.balances()?.get(peer_id).unwrap_or(&0))
    }

    /// Credit `amount` UCR to `peer_id`. Amount must be positive. Peer cap enforced.
    pub fn credit(
        &self,
        peer_id: &str,
        amount: i64,
        reason: &str,
        reference_id: Option<&str>,
    ) -> Result<CreditEntry, CreditError> {
        if amount <= 0 {
            return Err(CreditError::NonPositiveAmount(amount));
        }
        let _guard = self.lock.lock();
        let current = self.balance(peer_id)?;
        let new_balance = current + amount;
        if new_balance > PEER_CAP {
            return Err(CreditError::PeerCapExceeded {
                cap: PEER_CAP,
                would_reach: new_balance,
            });
        }

        let entry_id = Uuid::new_v4().to_string();
        let now = now_iso();
        let payload = json!({
            "entry_id": entry_id,
            "peer_id": peer_id,
            "amount_ucr": amount,
            "reason": reason,
            "reference_id": reference_id,
            "at": now,
        });
        self.journal.append("CREDIT", payload)?;
        Ok(CreditEntry {
            entry_id,
            peer_id: peer_id.to_owned(),
            amount_ucr: amount,
            reason: reason.to_owned(),
            reference_id: reference_id.map(|s| s.to_owned()),
            at: now,
        })
    }

    /// Debit `amount` UCR from `peer_id`. Checks balance first.
    pub fn debit(
        &self,
        peer_id: &str,
        amount: i64,
        reason: &str,
        reference_id: Option<&str>,
    ) -> Result<CreditEntry, CreditError> {
        if amount <= 0 {
            return Err(CreditError::NonPositiveAmount(amount));
        }
        let _guard = self.lock.lock();
        let current = self.balance(peer_id)?;
        if current < amount {
            return Err(CreditError::InsufficientBalance {
                have: current,
                need: amount,
            });
        }

        let entry_id = Uuid::new_v4().to_string();
        let now = now_iso();
        let payload = json!({
            "entry_id": entry_id,
            "peer_id": peer_id,
            "amount_ucr": -amount,
            "reason": reason,
            "reference_id": reference_id,
            "at": now,
        });
        self.journal.append("DEBIT", payload)?;
        Ok(CreditEntry {
            entry_id,
            peer_id: peer_id.to_owned(),
            amount_ucr: -amount,
            reason: reason.to_owned(),
            reference_id: reference_id.map(|s| s.to_owned()),
            at: now,
        })
    }
}

fn now_iso() -> String {
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
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"urace-credit-key-32bytes--------";

    #[test]
    fn credit_debit_balance() {
        let dir = tempdir().unwrap();
        let ledger = CreditLedger::open(dir.path().join("credit.jsonl"), KEY).unwrap();

        ledger.credit("peer-1", UNIT, "initial", None).unwrap();
        ledger.credit("peer-1", UNIT, "bonus", None).unwrap();
        ledger.debit("peer-1", UNIT, "payment", None).unwrap();

        assert_eq!(ledger.balance("peer-1").unwrap(), UNIT);
    }

    #[test]
    fn double_spend_prevented() {
        let dir = tempdir().unwrap();
        let ledger = CreditLedger::open(dir.path().join("credit.jsonl"), KEY).unwrap();
        ledger.credit("peer-1", UNIT, "initial", None).unwrap();

        let err = ledger
            .debit("peer-1", 2 * UNIT, "overspend", None)
            .unwrap_err();
        assert!(matches!(err, CreditError::InsufficientBalance { .. }));
    }

    #[test]
    fn peer_cap_enforced() {
        let dir = tempdir().unwrap();
        let ledger = CreditLedger::open(dir.path().join("credit.jsonl"), KEY).unwrap();

        let err = ledger
            .credit("peer-1", PEER_CAP + 1, "over cap", None)
            .unwrap_err();
        assert!(matches!(err, CreditError::PeerCapExceeded { .. }));
    }
}
