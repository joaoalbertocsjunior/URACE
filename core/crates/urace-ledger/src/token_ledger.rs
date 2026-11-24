//! Token ledger — balance tracking with Journal backing.
//!
//! Ported from `token_ledger.py`. Balances are derived by replaying the journal.
//! No separate mutable balance file — the journal IS the ledger.
//!
//! Invariants:
//! - No negative balances (checked before every debit).
//! - UNIT = 100_000_000 (8 decimal places).
//! - Mint on qualified acceptance only (score_delta > 0).
//! - Peer cap: 50 UNIT.

use crate::journal::{Journal, JournalError};
use parking_lot::Mutex;
use serde_json::json;
use std::collections::HashMap;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;

pub const UNIT: i64 = 100_000_000;
pub const PEER_CAP: i64 = 50 * UNIT;
pub const DEFAULT_BASELINE_GRANT: i64 = 3; // 3 UCR on first quality pass

#[derive(Debug, Error)]
pub enum TokenLedgerError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("insufficient balance: peer {peer} has {have}, needs {need}")]
    InsufficientBalance {
        peer: String,
        have: i64,
        need: i64,
    },
    #[error("peer cap exceeded: cap {cap}, would reach {would_reach}")]
    PeerCapExceeded { cap: i64, would_reach: i64 },
    #[error("non-positive amount: {0}")]
    NonPositiveAmount(i64),
    #[error("score_delta must be positive for mint; got {0}")]
    NonPositiveScoreDelta(f64),
}

pub struct TokenLedger {
    journal: Journal,
    lock: Mutex<()>,
}

impl TokenLedger {
    pub fn open(path: impl AsRef<Path>, hmac_key: [u8; 32]) -> Result<Self, TokenLedgerError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(TokenLedger { journal, lock: Mutex::new(()) })
    }

    fn now_unix() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    /// Replay the journal and compute balances for all peers.
    /// Balances can be negative internally only during replay; enforced at write time.
    fn balances_inner(&self) -> Result<HashMap<String, i64>, TokenLedgerError> {
        let entries = self.journal.verify_integrity()?;
        let mut balances: HashMap<String, i64> = HashMap::new();
        let mut baseline_unlocked: std::collections::HashSet<String> = std::collections::HashSet::new();

        for entry in &entries {
            match entry.kind.as_str() {
                "TOKEN_MINT" => {
                    if let (Some(peer), Some(amount)) = (
                        entry.payload.get("peer_id").and_then(|v| v.as_str()),
                        entry.payload.get("amount_units").and_then(|v| v.as_i64()),
                    ) {
                        // Baseline grant unlock: first mint unlocks grant
                        if !baseline_unlocked.contains(peer) {
                            baseline_unlocked.insert(peer.to_owned());
                            *balances.entry(peer.to_owned()).or_insert(0) += DEFAULT_BASELINE_GRANT;
                        }
                        *balances.entry(peer.to_owned()).or_insert(0) += amount;
                    }
                }
                "TOKEN_TRANSFER" => {
                    if let (Some(from), Some(to), Some(amount)) = (
                        entry.payload.get("from_peer_id").and_then(|v| v.as_str()),
                        entry.payload.get("to_peer_id").and_then(|v| v.as_str()),
                        entry.payload.get("amount_units").and_then(|v| v.as_i64()),
                    ) {
                        *balances.entry(from.to_owned()).or_insert(0) -= amount;
                        *balances.entry(to.to_owned()).or_insert(0) += amount;
                    }
                }
                "TOKEN_BURN" => {
                    if let (Some(peer), Some(amount)) = (
                        entry.payload.get("peer_id").and_then(|v| v.as_str()),
                        entry.payload.get("amount_units").and_then(|v| v.as_i64()),
                    ) {
                        *balances.entry(peer.to_owned()).or_insert(0) -= amount;
                    }
                }
                _ => {}
            }
        }
        Ok(balances)
    }

    /// Return the token balance for `peer_id` in base units.
    pub fn balance(&self, peer_id: &str) -> Result<i64, TokenLedgerError> {
        let balances = self.balances_inner()?;
        Ok(*balances.get(peer_id).unwrap_or(&0))
    }

    /// Return balances for all peers.
    pub fn balances(&self) -> Result<HashMap<String, i64>, TokenLedgerError> {
        self.balances_inner()
    }

    /// Mint tokens to `peer_id` on qualified acceptance (score_delta must be > 0).
    pub fn mint(
        &self,
        peer_id: &str,
        score_delta: f64,
        reason: &str,
    ) -> Result<i64, TokenLedgerError> {
        if score_delta <= 0.0 {
            return Err(TokenLedgerError::NonPositiveScoreDelta(score_delta));
        }
        // amount = score_delta scaled to base units, capped at PEER_CAP
        let amount = ((score_delta * UNIT as f64) as i64).max(1);
        let _guard = self.lock.lock();
        let current = self.balance(peer_id)?;
        if current + amount > PEER_CAP {
            return Err(TokenLedgerError::PeerCapExceeded {
                cap: PEER_CAP,
                would_reach: current + amount,
            });
        }
        self.journal.append(
            "TOKEN_MINT",
            json!({
                "peer_id": peer_id,
                "amount_units": amount,
                "score_delta": score_delta,
                "reason": reason,
                "at_unix": Self::now_unix(),
            }),
        )?;
        Ok(amount)
    }

    /// Transfer `amount_units` from `from_peer_id` to `to_peer_id`.
    /// Never allows negative balance on `from_peer_id`.
    pub fn transfer(
        &self,
        from_peer_id: &str,
        to_peer_id: &str,
        amount_units: i64,
        reason: &str,
    ) -> Result<(), TokenLedgerError> {
        if amount_units <= 0 {
            return Err(TokenLedgerError::NonPositiveAmount(amount_units));
        }
        let _guard = self.lock.lock();
        let from_balance = self.balance(from_peer_id)?;
        if from_balance < amount_units {
            return Err(TokenLedgerError::InsufficientBalance {
                peer: from_peer_id.to_owned(),
                have: from_balance,
                need: amount_units,
            });
        }
        let to_balance = self.balance(to_peer_id)?;
        if to_balance + amount_units > PEER_CAP {
            return Err(TokenLedgerError::PeerCapExceeded {
                cap: PEER_CAP,
                would_reach: to_balance + amount_units,
            });
        }
        self.journal.append(
            "TOKEN_TRANSFER",
            json!({
                "from_peer_id": from_peer_id,
                "to_peer_id": to_peer_id,
                "amount_units": amount_units,
                "reason": reason,
                "at_unix": Self::now_unix(),
            }),
        )?;
        Ok(())
    }

    /// Burn (destroy) `amount_units` from `peer_id`. Never goes below 0.
    pub fn burn(
        &self,
        peer_id: &str,
        amount_units: i64,
        reason: &str,
    ) -> Result<(), TokenLedgerError> {
        if amount_units <= 0 {
            return Err(TokenLedgerError::NonPositiveAmount(amount_units));
        }
        let _guard = self.lock.lock();
        let balance = self.balance(peer_id)?;
        if balance < amount_units {
            return Err(TokenLedgerError::InsufficientBalance {
                peer: peer_id.to_owned(),
                have: balance,
                need: amount_units,
            });
        }
        self.journal.append(
            "TOKEN_BURN",
            json!({
                "peer_id": peer_id,
                "amount_units": amount_units,
                "reason": reason,
                "at_unix": Self::now_unix(),
            }),
        )?;
        Ok(())
    }

    /// Summary of all peers and their balances.
    pub fn summary(&self) -> Result<serde_json::Value, TokenLedgerError> {
        let balances = self.balances()?;
        Ok(json!({
            "schema": "urace-token-ledger-v1",
            "unit": UNIT,
            "peer_cap": PEER_CAP,
            "baseline_grant": DEFAULT_BASELINE_GRANT,
            "peers": balances,
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    const KEY: [u8; 32] = *b"token-ledger-key-32bytes-pad----";

    // Returns both the dir (to keep it alive) and the ledger.
    fn make_ledger() -> (TempDir, TokenLedger) {
        let dir = TempDir::new().unwrap();
        let ledger = TokenLedger::open(dir.path().join("tokens.jsonl"), KEY).unwrap();
        (dir, ledger)
    }

    #[test]
    fn mint_increases_balance() {
        let (_dir, l) = make_ledger();
        l.mint("peer-a", 1.0, "qualification").unwrap();
        // balance = DEFAULT_BASELINE_GRANT + 1 UNIT
        let bal = l.balance("peer-a").unwrap();
        assert!(bal > 0);
        assert!(bal >= UNIT);
    }

    #[test]
    fn mint_requires_positive_delta() {
        let (_dir, l) = make_ledger();
        assert!(l.mint("peer-a", 0.0, "test").is_err());
        assert!(l.mint("peer-a", -1.0, "test").is_err());
    }

    #[test]
    fn transfer_basic() {
        let (_dir, l) = make_ledger();
        l.mint("peer-a", 5.0, "earn").unwrap();
        let initial = l.balance("peer-a").unwrap();
        l.transfer("peer-a", "peer-b", UNIT, "payment").unwrap();
        assert_eq!(l.balance("peer-a").unwrap(), initial - UNIT);
        // peer-b gets UNIT (no baseline since no mint)
        assert_eq!(l.balance("peer-b").unwrap(), UNIT);
    }

    #[test]
    fn transfer_negative_balance_error() {
        let (_dir, l) = make_ledger();
        // peer-a has no tokens
        let err = l.transfer("peer-a", "peer-b", UNIT, "test").unwrap_err();
        assert!(matches!(err, TokenLedgerError::InsufficientBalance { .. }));
    }

    #[test]
    fn burn_reduces_balance() {
        let (_dir, l) = make_ledger();
        l.mint("peer-a", 2.0, "earn").unwrap();
        let before = l.balance("peer-a").unwrap();
        l.burn("peer-a", UNIT, "decay").unwrap();
        assert_eq!(l.balance("peer-a").unwrap(), before - UNIT);
    }

    #[test]
    fn burn_below_zero_blocked() {
        let (_dir, l) = make_ledger();
        assert!(l.burn("peer-a", UNIT, "test").is_err());
    }

    #[test]
    fn peer_cap_enforcement() {
        let (_dir, l) = make_ledger();
        // Mint just below cap — 49 UNIT
        l.mint("peer-a", 49.0, "earn").unwrap();
        // Try to mint 2 more UNIT — would exceed 50 UNIT cap
        let err = l.mint("peer-a", 2.0, "earn").unwrap_err();
        assert!(matches!(err, TokenLedgerError::PeerCapExceeded { .. }));
    }
}
