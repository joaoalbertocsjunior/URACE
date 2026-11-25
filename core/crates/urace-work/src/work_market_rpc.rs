//! P2P work market RPC notifications — port of `work_market_rpc.py`.
//!
//! Thin wrappers that build and parse JSON-RPC notification payloads for the
//! P2P work market state machine:
//! - `notify_work_accepted`           requester → hired peer (escrow locked)
//! - `notify_work_delivered`          hired peer → requester (work delivered)
//! - `handle_work_delivery_notification` server-side parse of WORK_DELIVERY
//!
//! These functions are **pure** (no I/O, no ledger writes); callers are
//! responsible for dispatching the returned `serde_json::Value` over the wire
//! and for recording audit events.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use thiserror::Error;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum RpcError {
    #[error("missing required field: {0}")]
    MissingField(String),

    #[error("peer mismatch: notification intended for '{intended}', local id is '{local}'")]
    WrongRecipient { intended: String, local: String },

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

// ── DeliveryAck ───────────────────────────────────────────────────────────────

/// Acknowledgement returned when a work delivery notification is successfully
/// parsed and validated.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DeliveryAck {
    pub status: String,
    pub request_id: String,
}

impl DeliveryAck {
    pub fn ok(request_id: impl Into<String>) -> Self {
        DeliveryAck { status: "ok".to_string(), request_id: request_id.into() }
    }
}

// ── notify_work_accepted ──────────────────────────────────────────────────────

/// Build the JSON-RPC notification payload sent from requester to hired peer
/// when a bid is accepted and escrow is locked.
///
/// Corresponds to `notify_work_accepted()` in the Python module.
/// The escrow snapshot is included so the hired peer can verify the locked
/// amount without an extra round-trip.
pub fn notify_work_accepted(
    peer_id: &str,
    task_id: &str,
    escrow_snapshot: Option<&Value>,
) -> Value {
    json!({
        "jsonrpc": "2.0",
        "method": "exchange.work_accepted",
        "params": {
            "request_id": task_id,
            "hired_peer_id": peer_id,
            "escrow_snapshot": escrow_snapshot.cloned().unwrap_or(json!({})),
        },
        "id": null,
    })
}

// ── notify_work_delivered ─────────────────────────────────────────────────────

/// Build the JSON-RPC notification payload sent from hired peer to requester
/// when work is delivered.
///
/// `result_digest` is a hex-encoded hash of the delivered artifact (e.g.
/// SHA-256 of the patch bundle), so the requester can verify receipt without
/// re-fetching the full payload.
///
/// Corresponds to `submit_delivery_rpc()` in the Python module.
pub fn notify_work_delivered(
    peer_id: &str,
    task_id: &str,
    result_digest: &str,
) -> Value {
    json!({
        "jsonrpc": "2.0",
        "method": "exchange.work_delivery",
        "params": {
            "request_id": task_id,
            "delivery_hash": result_digest,
            "hired_peer_id": peer_id,
        },
        "id": null,
    })
}

// ── handle_work_delivery_notification ────────────────────────────────────────

/// Parse and validate an incoming WORK_DELIVERY notification.
///
/// Validates required fields (`request_id`, `delivery_hash`, `hired_peer_id`).
/// Returns a `DeliveryAck` on success or a typed `RpcError` on failure.
///
/// Corresponds to `handle_work_delivery_notification()` in the Python module.
pub fn handle_work_delivery_notification(payload: &Value) -> Result<DeliveryAck, RpcError> {
    let params = payload.get("params").unwrap_or(payload);

    for field in ["request_id", "delivery_hash", "hired_peer_id"] {
        if params.get(field).and_then(|v| v.as_str()).unwrap_or("").is_empty() {
            return Err(RpcError::MissingField(field.to_string()));
        }
    }

    let request_id = params["request_id"]
        .as_str()
        .unwrap_or("")
        .to_string();

    Ok(DeliveryAck::ok(request_id))
}

/// Parse and validate an incoming WORK_ACCEPTED notification.
///
/// Validates required fields and checks that `hired_peer_id` matches the
/// `local_peer_id` supplied by the caller (so a peer cannot be tricked into
/// accepting a job destined for another node).
///
/// Corresponds to `handle_work_accepted_notification()` in the Python module.
pub fn handle_work_accepted_notification(
    payload: &Value,
    local_peer_id: &str,
) -> Result<DeliveryAck, RpcError> {
    let params = payload.get("params").unwrap_or(payload);

    for field in ["request_id", "hired_peer_id", "escrow_snapshot"] {
        if params.get(field).is_none() {
            return Err(RpcError::MissingField(field.to_string()));
        }
    }

    let hired = params["hired_peer_id"].as_str().unwrap_or("");
    if hired != local_peer_id {
        return Err(RpcError::WrongRecipient {
            intended: hired.to_string(),
            local: local_peer_id.to_string(),
        });
    }

    let request_id = params["request_id"]
        .as_str()
        .unwrap_or("")
        .to_string();

    Ok(DeliveryAck::ok(request_id))
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── notify_work_accepted round-trip ───────────────────────────────────────

    #[test]
    fn notify_work_accepted_builds_valid_payload() {
        let payload = notify_work_accepted("peer_abc", "task-001", None);
        assert_eq!(payload["jsonrpc"], "2.0");
        assert_eq!(payload["method"], "exchange.work_accepted");
        let params = &payload["params"];
        assert_eq!(params["request_id"], "task-001");
        assert_eq!(params["hired_peer_id"], "peer_abc");
    }

    #[test]
    fn notify_work_accepted_with_escrow_snapshot() {
        let snapshot = json!({ "amount_ucr": 100, "locked_at": "2026-01-01T00:00:00Z" });
        let payload = notify_work_accepted("peer_xyz", "task-999", Some(&snapshot));
        assert_eq!(payload["params"]["escrow_snapshot"]["amount_ucr"], 100);
    }

    // ── notify_work_delivered round-trip ──────────────────────────────────────

    #[test]
    fn notify_work_delivered_builds_valid_payload() {
        let digest = "deadbeef".repeat(8); // 64-char hex
        let payload = notify_work_delivered("peer_abc", "task-001", &digest);
        assert_eq!(payload["method"], "exchange.work_delivery");
        assert_eq!(payload["params"]["delivery_hash"], digest.as_str());
        assert_eq!(payload["params"]["request_id"], "task-001");
    }

    // ── handle_work_delivery_notification ────────────────────────────────────

    #[test]
    fn delivery_notification_round_trip() {
        let sent = notify_work_delivered("peer_hired", "task-42", "cafebabe");
        let ack = handle_work_delivery_notification(&sent).unwrap();
        assert_eq!(ack.status, "ok");
        assert_eq!(ack.request_id, "task-42");
    }

    #[test]
    fn delivery_notification_missing_field_returns_error() {
        let bad = json!({ "params": { "request_id": "t1", "delivery_hash": "abc" } });
        // hired_peer_id is missing
        let err = handle_work_delivery_notification(&bad).unwrap_err();
        assert!(matches!(err, RpcError::MissingField(_)));
    }

    // ── handle_work_accepted_notification ────────────────────────────────────

    #[test]
    fn accepted_notification_validates_recipient() {
        let sent = notify_work_accepted("correct_peer", "task-7", None);
        let ack = handle_work_accepted_notification(&sent, "correct_peer").unwrap();
        assert_eq!(ack.request_id, "task-7");
    }

    #[test]
    fn accepted_notification_wrong_recipient_returns_error() {
        let sent = notify_work_accepted("peer_a", "task-8", None);
        let err = handle_work_accepted_notification(&sent, "peer_b").unwrap_err();
        assert!(matches!(err, RpcError::WrongRecipient { .. }));
    }

    #[test]
    fn accepted_notification_missing_escrow_snapshot_returns_error() {
        let bad = json!({ "params": { "request_id": "t1", "hired_peer_id": "p1" } });
        let err = handle_work_accepted_notification(&bad, "p1").unwrap_err();
        assert!(matches!(err, RpcError::MissingField(_)));
    }
}
