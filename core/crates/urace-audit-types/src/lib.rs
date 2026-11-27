//! `urace-audit-types` — boundary crate for audit event types.
//!
//! Provides [`AuditKind`] and [`AuditEvent`] without any ledger engine
//! dependency. Crates that only *emit* audit events should depend on this
//! crate rather than the full `urace-audit` / `urace-ledger` stack.

pub mod event;
pub mod kinds;

pub use event::AuditEvent;
pub use kinds::AuditKind;

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn audit_kind_serialises_to_snake_case() {
        let kind = AuditKind::AuthorityDecision;
        let json = serde_json::to_string(&kind).unwrap();
        assert_eq!(json, "\"authority_decision\"");
    }

    #[test]
    fn audit_kind_work_completed_snake_case() {
        let kind = AuditKind::WorkCompleted;
        let json = serde_json::to_string(&kind).unwrap();
        assert_eq!(json, "\"work_completed\"");
    }

    #[test]
    fn audit_kind_custom_roundtrips() {
        let kind = AuditKind::Custom("my_custom_event".into());
        let json = serde_json::to_string(&kind).unwrap();
        let back: AuditKind = serde_json::from_str(&json).unwrap();
        assert_eq!(kind, back);
    }

    #[test]
    fn audit_event_new_sets_non_empty_event_id() {
        let event = AuditEvent::new(AuditKind::LedgerEntry, "actor-1", json!({"amount": 100}));
        assert!(!event.event_id.is_empty());
        // UUID v4 is 36 characters (8-4-4-4-12 with hyphens)
        assert_eq!(event.event_id.len(), 36);
    }

    #[test]
    fn audit_event_with_target_sets_target_field() {
        let event = AuditEvent::new(AuditKind::WorkAssigned, "dispatcher", json!({}))
            .with_target("worker-node-42");
        assert_eq!(event.target, Some("worker-node-42".to_string()));
    }

    #[test]
    fn audit_event_timestamp_is_non_zero() {
        let event = AuditEvent::new(AuditKind::GoalCreated, "planner", json!({}));
        assert!(event.timestamp_ms > 0, "timestamp_ms should be non-zero");
    }

    #[test]
    fn audit_event_target_is_none_by_default() {
        let event = AuditEvent::new(AuditKind::KeyGenerated, "key-manager", json!({}));
        assert!(event.target.is_none());
    }

    #[test]
    fn audit_event_roundtrips_via_json() {
        let original = AuditEvent::new(AuditKind::SettlementCompleted, "settler", json!({"tx": "abc"}))
            .with_target("peer-99");
        let serialised = serde_json::to_string(&original).unwrap();
        let restored: AuditEvent = serde_json::from_str(&serialised).unwrap();
        assert_eq!(restored.event_id, original.event_id);
        assert_eq!(restored.target, Some("peer-99".to_string()));
        assert_eq!(restored.timestamp_ms, original.timestamp_ms);
    }
}
