use urace_audit::{AuditEvent, AuditKind, AuditLedger, ChainIntegrityReport, verify_audit_chain};
use serde_json::json;

const HMAC_KEY: [u8; 32] = *b"test-audit-integ-000000000000000";

#[test]
fn records_three_events_and_replays_them() {
    let dir = tempfile::tempdir().unwrap();
    let ledger = AuditLedger::open(dir.path().join("audit.jsonl"), HMAC_KEY).unwrap();

    ledger.record(AuditEvent::new(AuditKind::GoalCreated, "planner", json!({"goal_id": "g1"}))).unwrap();
    ledger.record(AuditEvent::new(AuditKind::WorkCompleted, "executor", json!({"task_id": "t1"}))).unwrap();
    ledger.record(AuditEvent::new(AuditKind::MintTriggered, "ledger", json!({"amount": 1000}))).unwrap();

    let events = ledger.all_events().unwrap();
    assert_eq!(events.len(), 3);
    assert_eq!(events[0].kind, AuditKind::GoalCreated);
    assert_eq!(events[1].kind, AuditKind::WorkCompleted);
    assert_eq!(events[2].kind, AuditKind::MintTriggered);

    let ids: Vec<_> = events.iter().map(|e| &e.event_id).collect();
    assert_ne!(ids[0], ids[1]);
    assert_ne!(ids[1], ids[2]);
}

#[test]
fn chain_integrity_intact_on_clean_ledger() {
    let dir = tempfile::tempdir().unwrap();
    let ledger = AuditLedger::open(dir.path().join("audit.jsonl"), HMAC_KEY).unwrap();
    ledger.record(AuditEvent::new(AuditKind::LedgerEntry, "node", json!({}))).unwrap();

    let report = verify_audit_chain(&ledger).unwrap();
    assert!(report.is_intact);
    assert_eq!(report.first_broken_index, None);
}

#[test]
fn event_ids_are_unique_uuid_format() {
    let dir = tempfile::tempdir().unwrap();
    let ledger = AuditLedger::open(dir.path().join("audit.jsonl"), HMAC_KEY).unwrap();
    for i in 0..5 {
        ledger.record(AuditEvent::new(
            AuditKind::LedgerEntry,
            format!("actor-{i}"),
            json!({}),
        )).unwrap();
    }
    let events = ledger.all_events().unwrap();
    let unique_ids: std::collections::HashSet<_> = events.iter().map(|e| &e.event_id).collect();
    assert_eq!(unique_ids.len(), 5);
    assert!(events[0].event_id.len() == 36);
}
