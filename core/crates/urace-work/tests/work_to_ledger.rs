use urace_work::{ReceiptError, ReceiptStore, WorkReceipt};

const HMAC_KEY: [u8; 32] = *b"test-work-ledger-000000000000000";

fn make_receipt(receipt_id: &str, task_id: &str, peer: &str, prev_hash: &str) -> WorkReceipt {
    WorkReceipt {
        receipt_id: receipt_id.into(),
        task_id: task_id.into(),
        executor_peer_id: peer.into(),
        submitter_peer_id: peer.into(),
        amount_ucr: 1000,
        completed_at: "2026-01-01T00:00:00Z".into(),
        delivery_hash: "abc123def456abc123def456abc123def456abc123def456abc123def456abc1".into(),
        previous_receipt_hash: prev_hash.into(),
    }
}

#[test]
fn receipt_persists_and_replays() {
    let dir = tempfile::tempdir().unwrap();
    let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), HMAC_KEY).unwrap();
    let r = make_receipt("r1", "t1", "alice", "");
    store.issue(r).unwrap();
    let receipts = store.receipts_for("alice").unwrap();
    assert_eq!(receipts.len(), 1);
    assert_eq!(receipts[0].receipt_id, "r1");
    assert_eq!(receipts[0].task_id, "t1");
}

#[test]
fn m04_authorship_gate_rejects_mismatch() {
    let dir = tempfile::tempdir().unwrap();
    let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), HMAC_KEY).unwrap();
    let mut r = make_receipt("r2", "t2", "alice", "");
    r.submitter_peer_id = "mallory".into();
    let err = store.issue(r).unwrap_err();
    assert!(matches!(err, ReceiptError::AuthorshipMismatch { .. }));
}

#[test]
fn multiple_receipts_for_different_peers() {
    let dir = tempfile::tempdir().unwrap();
    let store = ReceiptStore::open(dir.path().join("receipts.jsonl"), HMAC_KEY).unwrap();
    store.issue(make_receipt("r1", "t1", "alice", "")).unwrap();
    store.issue(make_receipt("r2", "t2", "bob", "")).unwrap();
    store.issue(make_receipt("r3", "t3", "alice", "")).unwrap();
    assert_eq!(store.receipts_for("alice").unwrap().len(), 2);
    assert_eq!(store.receipts_for("bob").unwrap().len(), 1);
}
