//! Ledger entry types — append-only JSONL journal schema.

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// A single signed ledger entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerEntry {
    pub seq: u64,
    pub kind: String,
    pub payload: Value,
    /// HMAC-SHA256 hex over canonical JSON of (seq, kind, payload).
    pub hmac: String,
    pub written_at: String,
}

/// Credit/debit entry in the token ledger.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreditEntry {
    pub entry_id: String,
    pub peer_id: String,
    pub amount_ucr: i64,
    pub reason: String,
    pub reference_id: Option<String>,
    pub at: String,
}

/// Token balance snapshot — derived view, not stored directly.
#[derive(Debug, Clone)]
pub struct BalanceSnapshot {
    pub peer_id: String,
    pub balance_ucr: i64,
    pub as_of_seq: u64,
}
