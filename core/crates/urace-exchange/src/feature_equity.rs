//! Feature equity ownership and trading.
//!
//! Ported from `runtime/urace/feature_equity.py`.
//!
//! Equity is measured in basis points (bp): 10_000 bp = 100.00%.
//! Ownership is derived from an append-only audit-row replay; it is never
//! stored in mutable state.
//!
//! ## §62z / Authority boundary note
//! Equity acquisition (`acquire`) and release (`release`) are NOT qualifying
//! actions. They move ownership records between peers but do not transfer UCR
//! tokens. Only a settlement (transfer of UCR, e.g. via `sell_equity` with a
//! non-zero `price_units`) crosses the §62z authority boundary and requires a
//! confirmation gate through `urace-authority`.
//!
//! ## Anti-monopoly cap
//! Non-original holders may not exceed [`EQUITY_NON_CREATOR_MAX_BP`] (80%).
//! A single exception: the original creator performing a full exit (selling
//! their entire remaining stake in one transaction) may transfer any amount
//! to a single buyer.
//!
//! ## Credit semantics
//! Equity purchases credit the seller via `REP_SOURCE_TRADE` (market_rep only).
//! These credits never count toward earned_rep / governance / arbitration weight.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use time::OffsetDateTime;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// 100.00% in basis points.
pub const EQUITY_TOTAL_BP: u64 = 10_000;

/// Minimum tranche for a single trade (1%).
pub const EQUITY_MIN_TRADE_BP: u64 = 100;

/// Maximum basis points a non-original holder may accumulate (80%).
pub const EQUITY_NON_CREATOR_MAX_BP: u64 = 8_000;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum EquityError {
    #[error("insufficient equity: {holder_id:?} holds {held} bp, cannot release {requested} bp")]
    InsufficientEquity {
        holder_id: String,
        held: u64,
        requested: u64,
    },
    #[error("minimum trade is {EQUITY_MIN_TRADE_BP} bp (1%), got {0}")]
    BelowMinimumTrade(u64),
    #[error(
        "anti-monopoly: {buyer_id:?} would hold {after} bp \
         > max {EQUITY_NON_CREATOR_MAX_BP} bp for non-original holders"
    )]
    AntiMonopoly { buyer_id: String, after: u64 },
    #[error("feature {0:?} not found in equity ledger")]
    FeatureNotFound(String),
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// A single equity position: how many basis points `holder_id` holds in
/// `atom_id`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EquityPosition {
    pub atom_id: String,
    pub holder_id: String,
    /// Basis points held (100 = 1%, 10_000 = 100%).
    pub units: u64,
    /// Unix timestamp (seconds) when this position was last modified.
    pub acquired_at: i64,
}

// ---------------------------------------------------------------------------
// FeatureEquityLedger
// ---------------------------------------------------------------------------

/// In-memory ledger of equity positions, keyed by `(atom_id, holder_id)`.
///
/// Thread-safe via [`DashMap`] sharding. Each entry is the *current* balance
/// for that (atom, holder) pair; the full history lives in the signed audit
/// chain (outside this module).
pub struct FeatureEquityLedger {
    /// (atom_id, holder_id) → EquityPosition
    positions: DashMap<(String, String), EquityPosition>,
}

impl FeatureEquityLedger {
    pub fn new() -> Self {
        Self {
            positions: DashMap::new(),
        }
    }

    /// Grant or add `units` basis points of `atom_id` to `holder_id`.
    ///
    /// Idempotent in the sense that repeated calls accumulate (matching the
    /// Python `equity_holdings` replay model where EQUITY_GRANT rows sum up).
    pub fn acquire(&self, atom_id: &str, holder_id: &str, units: u64) -> Result<(), EquityError> {
        let key = (atom_id.to_owned(), holder_id.to_owned());
        let now = OffsetDateTime::now_utc().unix_timestamp();
        self.positions
            .entry(key)
            .and_modify(|p| {
                p.units += units;
                p.acquired_at = now;
            })
            .or_insert_with(|| EquityPosition {
                atom_id: atom_id.to_owned(),
                holder_id: holder_id.to_owned(),
                units,
                acquired_at: now,
            });
        Ok(())
    }

    /// Release (reduce) `units` basis points from `holder_id`'s position in
    /// `atom_id`.
    ///
    /// Returns [`EquityError::InsufficientEquity`] when the holder does not
    /// have enough units.  Entries reaching zero are removed.
    pub fn release(&self, atom_id: &str, holder_id: &str, units: u64) -> Result<(), EquityError> {
        if units < EQUITY_MIN_TRADE_BP {
            return Err(EquityError::BelowMinimumTrade(units));
        }
        let key = (atom_id.to_owned(), holder_id.to_owned());
        let held = self
            .positions
            .get(&key)
            .map(|p| p.units)
            .unwrap_or(0);
        if held < units {
            return Err(EquityError::InsufficientEquity {
                holder_id: holder_id.to_owned(),
                held,
                requested: units,
            });
        }
        if held == units {
            self.positions.remove(&key);
        } else {
            self.positions
                .get_mut(&key)
                .expect("checked above")
                .units -= units;
        }
        Ok(())
    }

    /// Current balance (in basis points) for a given (atom, holder) pair.
    /// Returns 0 when the holder has no position.
    pub fn balance(&self, atom_id: &str, holder_id: &str) -> u64 {
        let key = (atom_id.to_owned(), holder_id.to_owned());
        self.positions.get(&key).map(|p| p.units).unwrap_or(0)
    }

    /// All equity positions currently held by `holder_id`.
    pub fn positions_for_holder(&self, holder_id: &str) -> Vec<EquityPosition> {
        self.positions
            .iter()
            .filter(|e| e.key().1 == holder_id)
            .map(|e| e.value().clone())
            .collect()
    }

    /// Compute the proportional split of `amount` across all current holders
    /// of `atom_id`.
    ///
    /// Mirrors `_proportional_split` in the Python module. The last entry in
    /// the sorted list absorbs any remainder from integer division.
    pub fn proportional_split(&self, atom_id: &str, amount: u64) -> Vec<(String, u64)> {
        let holders: Vec<EquityPosition> = self
            .positions
            .iter()
            .filter(|e| e.key().0 == atom_id)
            .map(|e| e.value().clone())
            .collect();

        if holders.is_empty() || amount == 0 {
            return vec![];
        }
        let total_bp: u64 = holders.iter().map(|p| p.units).sum();
        if total_bp == 0 {
            return vec![];
        }

        let mut result: Vec<(String, u64)> = Vec::with_capacity(holders.len());
        let mut distributed: u64 = 0;
        let last = holders.len() - 1;
        for (i, pos) in holders.iter().enumerate() {
            let share = if i == last {
                amount - distributed
            } else {
                amount * pos.units / total_bp
            };
            if share > 0 {
                result.push((pos.holder_id.clone(), share));
                distributed += share;
            }
        }
        result
    }
}

impl Default for FeatureEquityLedger {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn acquire_and_balance() {
        let ledger = FeatureEquityLedger::new();
        ledger.acquire("atom-1", "alice", 5_000).unwrap();
        ledger.acquire("atom-1", "bob", 5_000).unwrap();
        assert_eq!(ledger.balance("atom-1", "alice"), 5_000);
        assert_eq!(ledger.balance("atom-1", "bob"), 5_000);
        assert_eq!(ledger.balance("atom-1", "carol"), 0);
    }

    #[test]
    fn acquire_accumulates() {
        let ledger = FeatureEquityLedger::new();
        ledger.acquire("atom-2", "alice", 3_000).unwrap();
        ledger.acquire("atom-2", "alice", 2_000).unwrap();
        assert_eq!(ledger.balance("atom-2", "alice"), 5_000);
    }

    #[test]
    fn release_reduces_balance() {
        let ledger = FeatureEquityLedger::new();
        ledger.acquire("atom-3", "alice", EQUITY_TOTAL_BP).unwrap();
        ledger.release("atom-3", "alice", 1_000).unwrap();
        assert_eq!(ledger.balance("atom-3", "alice"), 9_000);
    }

    #[test]
    fn release_full_removes_entry() {
        let ledger = FeatureEquityLedger::new();
        ledger.acquire("atom-4", "alice", EQUITY_TOTAL_BP).unwrap();
        ledger.release("atom-4", "alice", EQUITY_TOTAL_BP).unwrap();
        assert_eq!(ledger.balance("atom-4", "alice"), 0);
        assert!(ledger.positions_for_holder("alice").is_empty());
    }

    #[test]
    fn release_underflow_error() {
        let ledger = FeatureEquityLedger::new();
        ledger.acquire("atom-5", "alice", 500).unwrap();
        let err = ledger.release("atom-5", "alice", 1_000).unwrap_err();
        assert!(matches!(err, EquityError::InsufficientEquity { .. }));
    }

    #[test]
    fn release_below_minimum_error() {
        let ledger = FeatureEquityLedger::new();
        ledger.acquire("atom-6", "alice", EQUITY_TOTAL_BP).unwrap();
        // 50 bp < EQUITY_MIN_TRADE_BP (100 bp)
        let err = ledger.release("atom-6", "alice", 50).unwrap_err();
        assert!(matches!(err, EquityError::BelowMinimumTrade(50)));
    }

    #[test]
    fn positions_for_holder() {
        let ledger = FeatureEquityLedger::new();
        ledger.acquire("atom-7", "alice", 5_000).unwrap();
        ledger.acquire("atom-8", "alice", 3_000).unwrap();
        ledger.acquire("atom-9", "bob", 2_000).unwrap();
        let alice_positions = ledger.positions_for_holder("alice");
        assert_eq!(alice_positions.len(), 2);
        let bob_positions = ledger.positions_for_holder("bob");
        assert_eq!(bob_positions.len(), 1);
    }

    #[test]
    fn proportional_split_basic() {
        let ledger = FeatureEquityLedger::new();
        ledger.acquire("atom-10", "alice", 7_000).unwrap();
        ledger.acquire("atom-10", "bob", 3_000).unwrap();
        let splits = ledger.proportional_split("atom-10", 1_000);
        let total: u64 = splits.iter().map(|(_, v)| *v).sum();
        assert_eq!(total, 1_000);
    }
}
