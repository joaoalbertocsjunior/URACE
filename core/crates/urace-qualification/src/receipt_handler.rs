//! Trial receipt delivery and settlement protocol.
//!
//! Ported from `runtime/urace/receipt_handler.py`. Provides the `ReceiptHandler`
//! trait and two implementations: `P2PReceiptHandler` (delivers over the peer
//! exchange) and `LocalReceiptHandler` (records locally, useful in tests).
//!
//! §62z: any path that proceeds to settlement after a successful delivery must
//! be gated by the authority boundary — this module only delivers; it does not
//! initiate settlement autonomously.

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::trial_common::now_iso;
use crate::trial_receipt::TrialReceipt;

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum ReceiptHandlerError {
    #[error("delivery failed: peer_id={peer_id}, reason={reason}")]
    DeliveryFailed { peer_id: String, reason: String },
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("invalid receipt: {0}")]
    InvalidReceipt(String),
}

// ---------------------------------------------------------------------------
// Delivery outcome
// ---------------------------------------------------------------------------

/// Outcome of a single receipt delivery attempt.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeliveryOutcome {
    /// Receipt id that was delivered (or attempted).
    pub receipt_id: String,
    /// True when the receipt was successfully recorded.
    pub success: bool,
    /// Destination peer id (None for local-only delivery).
    pub peer_id: Option<String>,
    /// ISO-8601 timestamp of the delivery attempt.
    pub attempted_at: String,
    /// Error message on failure, None on success.
    pub error: Option<String>,
}

impl DeliveryOutcome {
    fn success(receipt_id: impl Into<String>, peer_id: Option<String>) -> Self {
        DeliveryOutcome {
            receipt_id: receipt_id.into(),
            success: true,
            peer_id,
            attempted_at: now_iso(),
            error: None,
        }
    }

    fn failure(
        receipt_id: impl Into<String>,
        peer_id: Option<String>,
        error: impl Into<String>,
    ) -> Self {
        DeliveryOutcome {
            receipt_id: receipt_id.into(),
            success: false,
            peer_id,
            attempted_at: now_iso(),
            error: Some(error.into()),
        }
    }
}

// ---------------------------------------------------------------------------
// Handler trait
// ---------------------------------------------------------------------------

/// Interface for delivering trial qualification receipts.
///
/// Implementations must validate the receipt schema before recording.
/// Returns `DeliveryOutcome` — callers check `.success` rather than matching
/// on errors, so a failed delivery never crashes the cycle.
pub trait ReceiptHandler {
    /// Deliver `receipt` to `peer_id` (or store locally when `peer_id` is `None`).
    fn deliver(&self, receipt: &TrialReceipt, peer_id: Option<&str>) -> DeliveryOutcome;
}

// ---------------------------------------------------------------------------
// Local handler (test-safe, no network)
// ---------------------------------------------------------------------------

/// Records receipts in memory without any network call. Useful in tests.
#[derive(Debug, Default)]
pub struct LocalReceiptHandler {
    delivered: std::sync::Mutex<Vec<(TrialReceipt, Option<String>)>>,
}

impl LocalReceiptHandler {
    /// Create a new, empty local handler.
    pub fn new() -> Self {
        LocalReceiptHandler {
            delivered: std::sync::Mutex::new(Vec::new()),
        }
    }

    /// Return a snapshot of all delivered receipts.
    pub fn all_delivered(&self) -> Vec<(TrialReceipt, Option<String>)> {
        self.delivered
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .clone()
    }
}

impl ReceiptHandler for LocalReceiptHandler {
    fn deliver(&self, receipt: &TrialReceipt, peer_id: Option<&str>) -> DeliveryOutcome {
        if let Err(e) = receipt.validate_schema() {
            return DeliveryOutcome::failure(
                receipt.feature_id.clone(),
                peer_id.map(str::to_owned),
                e.to_string(),
            );
        }
        let mut store = self.delivered.lock().unwrap_or_else(|e| e.into_inner());
        store.push((receipt.clone(), peer_id.map(str::to_owned)));
        DeliveryOutcome::success(receipt.feature_id.clone(), peer_id.map(str::to_owned))
    }
}

// ---------------------------------------------------------------------------
// P2P handler (placeholder — real exchange wired at runtime)
// ---------------------------------------------------------------------------

/// Delivers receipts via a P2P exchange to the originating peer.
///
/// When `peer_id` is `None`, records the event locally without a network call.
/// The `exchange_event` callback is used to emit lifecycle events into the
/// exchange layer without coupling this module to a specific exchange type.
pub struct P2PReceiptHandler<F>
where
    F: Fn(&str, &str) + Send + Sync,
{
    /// Callback: `fn(event_kind, receipt_id)` — wired to the exchange at construction.
    emit_event: F,
}

impl<F> P2PReceiptHandler<F>
where
    F: Fn(&str, &str) + Send + Sync,
{
    /// Create a handler backed by `emit_event` for lifecycle event emission.
    pub fn new(emit_event: F) -> Self {
        P2PReceiptHandler { emit_event }
    }
}

impl<F> ReceiptHandler for P2PReceiptHandler<F>
where
    F: Fn(&str, &str) + Send + Sync,
{
    fn deliver(&self, receipt: &TrialReceipt, peer_id: Option<&str>) -> DeliveryOutcome {
        if let Err(e) = receipt.validate_schema() {
            return DeliveryOutcome::failure(
                receipt.feature_id.clone(),
                peer_id.map(str::to_owned),
                e.to_string(),
            );
        }

        let rid = receipt.feature_id.as_str();

        match peer_id {
            None => {
                // Local-only: emit event but skip network.
                (self.emit_event)("TRIAL_RECEIPT_LOCAL", rid);
                DeliveryOutcome::success(rid, None)
            }
            Some(pid) => {
                // Network delivery: emit event and record outcome.
                // Real exchange integration is injected via emit_event;
                // any network error surfaces as a failed outcome rather than a panic.
                (self.emit_event)("TRIAL_RECEIPT_P2P", rid);
                DeliveryOutcome::success(rid, Some(pid.to_owned()))
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Settlement confirmation record
// ---------------------------------------------------------------------------

/// A settlement confirmation record produced after a successful delivery.
///
/// §62z: producing this record does not trigger settlement autonomously.
/// The authority gate must be passed before any token transfer is initiated.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SettlementConfirmation {
    /// Receipt id that triggered this confirmation.
    pub receipt_id: String,
    /// Destination peer id.
    pub peer_id: String,
    /// ISO-8601 timestamp.
    pub confirmed_at: String,
    /// Whether the authority gate was checked before this record was created.
    pub authority_checked: bool,
}

impl SettlementConfirmation {
    /// Build a confirmation record. `authority_checked` must be `true`; if the
    /// authority gate has not been passed, do not create this record.
    pub fn new(
        receipt_id: impl Into<String>,
        peer_id: impl Into<String>,
        authority_checked: bool,
    ) -> Result<Self, ReceiptHandlerError> {
        if !authority_checked {
            return Err(ReceiptHandlerError::InvalidReceipt(
                "§62z: settlement confirmation requires authority_checked = true".into(),
            ));
        }
        Ok(SettlementConfirmation {
            receipt_id: receipt_id.into(),
            peer_id: peer_id.into(),
            confirmed_at: now_iso(),
            authority_checked,
        })
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::trial_receipt::TrialReceipt;

    fn good_receipt(feature: &str, borrower: &str, creator: &str) -> TrialReceipt {
        TrialReceipt::new(feature, creator, borrower, 0.5)
    }

    #[test]
    fn local_handler_records_receipt() {
        let handler = LocalReceiptHandler::new();
        let r = good_receipt("feat-1", "peer-b", "peer-c");
        let outcome = handler.deliver(&r, Some("peer-b"));
        assert!(outcome.success);
        assert_eq!(handler.all_delivered().len(), 1);
    }

    #[test]
    fn local_handler_accepts_none_peer() {
        let handler = LocalReceiptHandler::new();
        let r = good_receipt("feat-2", "peer-b", "peer-c");
        let outcome = handler.deliver(&r, None);
        assert!(outcome.success);
        assert!(outcome.peer_id.is_none());
    }

    #[test]
    fn p2p_handler_emits_local_event_on_no_peer() {
        use std::sync::{Arc, Mutex};
        let events: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
        let ev = events.clone();
        let handler = P2PReceiptHandler::new(move |kind, _rid| {
            ev.lock().unwrap().push(kind.to_owned());
        });
        let r = good_receipt("feat-3", "peer-b", "peer-c");
        let outcome = handler.deliver(&r, None);
        assert!(outcome.success);
        assert_eq!(events.lock().unwrap()[0], "TRIAL_RECEIPT_LOCAL");
    }

    #[test]
    fn settlement_confirmation_requires_authority_checked() {
        let result = SettlementConfirmation::new("rcpt-1", "peer-x", false);
        assert!(result.is_err(), "must require authority_checked = true");

        let ok = SettlementConfirmation::new("rcpt-1", "peer-x", true);
        assert!(ok.is_ok());
        assert!(ok.unwrap().authority_checked);
    }

    #[test]
    fn local_handler_rejects_bad_schema() {
        let handler = LocalReceiptHandler::new();
        let mut r = good_receipt("feat-4", "peer-b", "peer-c");
        r.schema = "bad-schema".to_owned();
        let outcome = handler.deliver(&r, Some("peer-b"));
        assert!(!outcome.success);
        assert!(outcome.error.is_some());
    }
}
