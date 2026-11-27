//! `AuditEvent` — the envelope for every audit entry emitted by the runtime.
//!
//! This struct is intentionally ledger-free: any crate that only *emits*
//! audit events adds `urace-audit-types` as a dependency instead of pulling
//! in the full `urace-audit` / `urace-ledger` stack.

use crate::kinds::AuditKind;
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEvent {
    pub event_id: String,
    pub kind: AuditKind,
    pub actor: String,
    pub target: Option<String>,
    pub details: Value,
    pub timestamp_ms: u64,
}

impl AuditEvent {
    pub fn new(kind: AuditKind, actor: impl Into<String>, details: Value) -> Self {
        AuditEvent {
            event_id: uuid::Uuid::new_v4().to_string(),
            kind,
            actor: actor.into(),
            target: None,
            details,
            timestamp_ms: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as u64)
                .unwrap_or(0),
        }
    }

    pub fn with_target(mut self, target: impl Into<String>) -> Self {
        self.target = Some(target.into());
        self
    }
}
