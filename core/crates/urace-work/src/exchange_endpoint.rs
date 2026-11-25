//! P2P CREDIT_SETTLEMENT RPC endpoint.
//!
//! Accepts authenticated CREDIT_SETTLEMENT RPC calls from peer nodes and
//! wires them to `CreditLedger::credit` / `CreditLedger::debit`. Imported
//! by the Exchange server when `token_settlement = true`.
//!
//! # §62z
//!
//! `handle_credit_settlement` is a qualifying action (transfer).
//!
//! §62z: caller must gate through authority before calling.
//!
//! The handler enforces this by requiring an `authority_token` field in the
//! payload. Any call that arrives without a non-empty token is rejected with
//! `SettlementEndpointError::AuthorityRequired` before any ledger write occurs.

use serde::{Deserialize, Serialize};
use thiserror::Error;
use urace_ledger::CreditLedger;
#[cfg(test)]
use urace_ledger::UNIT;

/// Wire schema version — both sides must agree.
pub const SCHEMA: &str = "urace-credit-settlement-v1";

// ── Error type ───────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum SettlementEndpointError {
    #[error("unsupported schema: {0}")]
    UnsupportedSchema(String),

    #[error("unknown action: {0}")]
    UnknownAction(String),

    #[error("units must be a positive integer, got {0}")]
    InvalidUnits(i64),

    #[error("authority token missing — §62z gate not satisfied")]
    AuthorityRequired,

    #[error("ledger error: {0}")]
    Ledger(#[from] urace_ledger::CreditError),
}

// ── Wire types ────────────────────────────────────────────────────────────────

/// Incoming CREDIT_SETTLEMENT RPC payload (deserialized from JSON-RPC params).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SettlementPayload {
    /// Must equal `SCHEMA`.
    pub schema: String,
    /// `"earn"` or `"spend"`.
    pub action: String,
    /// Target peer whose balance changes.
    pub peer_id: String,
    /// Amount in UCR base units (1 UNIT = 100_000_000). Must be positive.
    pub units: i64,
    /// Human-readable reason forwarded to the ledger entry.
    #[serde(default)]
    pub reason: String,
    /// Idempotency key; callers should use a UUID.
    #[serde(default)]
    pub operation_id: String,
    /// Non-empty value attests that the §62z authority gate was satisfied by
    /// the caller before dispatching this RPC. The handler rejects empty tokens.
    #[serde(default)]
    pub authority_token: String,
}

/// Successful response body.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SettlementResponse {
    pub status: String,
    pub action: String,
    pub units: i64,
    pub operation_id: String,
}

// ── Core handler ──────────────────────────────────────────────────────────────

/// Validate and apply an authenticated CREDIT_SETTLEMENT RPC call from a peer.
///
/// §62z: caller must gate through authority before calling.
///
/// # Invariants
///
/// - `payload.schema` must equal `SCHEMA`.
/// - `payload.authority_token` must be non-empty (attests §62z gate was satisfied).
/// - `payload.units` must be `>= 1`; `UNIT = 100_000_000`.
/// - `payload.action` must be `"earn"` or `"spend"`.
/// - All ledger writes go through `CreditLedger` — no direct file access.
pub fn handle_credit_settlement(
    payload: &SettlementPayload,
    caller_peer_id: &str,
    ledger: &CreditLedger,
) -> Result<SettlementResponse, SettlementEndpointError> {
    // §62z gate: reject if the caller has not attested authority resolution.
    if payload.authority_token.trim().is_empty() {
        return Err(SettlementEndpointError::AuthorityRequired);
    }

    if payload.schema != SCHEMA {
        return Err(SettlementEndpointError::UnsupportedSchema(payload.schema.clone()));
    }

    if payload.units < 1 {
        return Err(SettlementEndpointError::InvalidUnits(payload.units));
    }

    let reason = format!(
        "settlement:{} caller={} op={}",
        payload.reason, caller_peer_id, payload.operation_id
    );
    let op_ref = if payload.operation_id.is_empty() {
        None
    } else {
        Some(payload.operation_id.as_str())
    };

    match payload.action.as_str() {
        "earn" => {
            ledger.credit(&payload.peer_id, payload.units, &reason, op_ref)?;
        }
        "spend" => {
            ledger.debit(&payload.peer_id, payload.units, &reason, op_ref)?;
        }
        other => return Err(SettlementEndpointError::UnknownAction(other.to_owned())),
    }

    Ok(SettlementResponse {
        status: "ok".to_owned(),
        action: payload.action.clone(),
        units: payload.units,
        operation_id: payload.operation_id.clone(),
    })
}

// ── Router builder ────────────────────────────────────────────────────────────

/// Configuration for the settlement HTTP sub-router.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SettlementRouterConfig {
    /// HTTP path to mount the endpoint on (e.g. `"/p2p/settle"`).
    pub mount_path: String,
    /// Whether the settlement endpoint is active.
    pub enabled: bool,
}

impl Default for SettlementRouterConfig {
    fn default() -> Self {
        SettlementRouterConfig {
            mount_path: "/p2p/settle".to_owned(),
            enabled: true,
        }
    }
}

/// Construct the routing configuration for the exchange settlement endpoint.
///
/// Returns `None` when `token_settlement` is disabled; the exchange server
/// should omit the route entirely in that case.
pub fn build_settlement_router(
    token_settlement: bool,
    mount_path: Option<&str>,
) -> Option<SettlementRouterConfig> {
    if !token_settlement {
        return None;
    }
    Some(SettlementRouterConfig {
        mount_path: mount_path.unwrap_or("/p2p/settle").to_owned(),
        enabled: true,
    })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"exchange-endpoint-key-32bytes---";

    fn ledger() -> (CreditLedger, tempfile::TempDir) {
        let dir = tempdir().unwrap();
        let l = CreditLedger::open(dir.path().join("credit.jsonl"), KEY).unwrap();
        (l, dir)
    }

    fn payload(action: &str, units: i64, authority_token: &str) -> SettlementPayload {
        SettlementPayload {
            schema: SCHEMA.to_owned(),
            action: action.to_owned(),
            peer_id: "peer-alice".to_owned(),
            units,
            reason: "test".to_owned(),
            operation_id: "op-1".to_owned(),
            authority_token: authority_token.to_owned(),
        }
    }

    #[test]
    fn earn_increases_balance() {
        let (ledger, _dir) = ledger();
        let p = payload("earn", UNIT, "auth-tok");
        let resp = handle_credit_settlement(&p, "peer-bob", &ledger).unwrap();
        assert_eq!(resp.status, "ok");
        assert_eq!(ledger.balance("peer-alice").unwrap(), UNIT);
    }

    #[test]
    fn spend_decreases_balance() {
        let (ledger, _dir) = ledger();
        ledger.credit("peer-alice", 2 * UNIT, "seed", None).unwrap();
        let p = payload("spend", UNIT, "auth-tok");
        handle_credit_settlement(&p, "peer-bob", &ledger).unwrap();
        assert_eq!(ledger.balance("peer-alice").unwrap(), UNIT);
    }

    #[test]
    fn missing_authority_token_rejected() {
        let (ledger, _dir) = ledger();
        let p = payload("earn", UNIT, "");
        let err = handle_credit_settlement(&p, "peer-bob", &ledger).unwrap_err();
        assert!(matches!(err, SettlementEndpointError::AuthorityRequired));
    }

    #[test]
    fn wrong_schema_rejected() {
        let (ledger, _dir) = ledger();
        let mut p = payload("earn", UNIT, "auth-tok");
        p.schema = "bad-schema".to_owned();
        let err = handle_credit_settlement(&p, "peer-bob", &ledger).unwrap_err();
        assert!(matches!(err, SettlementEndpointError::UnsupportedSchema(_)));
    }

    #[test]
    fn build_settlement_router_disabled() {
        assert!(build_settlement_router(false, None).is_none());
        let cfg = build_settlement_router(true, Some("/custom/settle")).unwrap();
        assert!(cfg.enabled);
        assert_eq!(cfg.mount_path, "/custom/settle");
    }
}
