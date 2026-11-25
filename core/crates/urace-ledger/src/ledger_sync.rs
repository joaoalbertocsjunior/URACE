//! Sliding-window sync for light/edge peers at million-peer scale.
//!
//! Ported from `ledger_sync.py`. Full peers hold complete history; light peers
//! hold the latest `LEDGER_BLOCK_SEAL` + tail rows since that seal.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

pub const SCHEMA: &str = "urace-ledger-sync-v1";
pub const DEFAULT_TAIL_ROWS: usize = 1000;

// ── Row helpers ───────────────────────────────────────────────────────────────

/// Return the most recent `LEDGER_BLOCK_SEAL` row, or `None`.
pub fn latest_seal(rows: &[Value]) -> Option<&Value> {
    rows.iter()
        .filter(|r| r.get("kind").and_then(Value::as_str) == Some("LEDGER_BLOCK_SEAL"))
        .max_by(|a, b| {
            let ta = a.get("at_unix").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let tb = b.get("at_unix").and_then(|v| v.as_f64()).unwrap_or(0.0);
            ta.partial_cmp(&tb).unwrap_or(std::cmp::Ordering::Equal)
        })
}

/// Return rows after the given seal (located by `sha256`). All rows if `seal` is `None`.
pub fn tail_since_seal<'a>(rows: &'a [Value], seal: Option<&Value>) -> &'a [Value] {
    let seal_sha = match seal.and_then(|s| s.get("sha256")).and_then(Value::as_str) {
        Some(s) => s,
        None => return rows,
    };
    for (i, row) in rows.iter().enumerate() {
        if row.get("sha256").and_then(Value::as_str) == Some(seal_sha) {
            return &rows[i + 1..];
        }
    }
    rows
}

/// Return `[latest_seal_row] + min(tail_rows, len(tail))` rows.
pub fn prune_to_window(rows: &[Value], tail_rows: usize) -> Vec<Value> {
    let seal = latest_seal(rows);
    if seal.is_none() {
        let start = rows.len().saturating_sub(tail_rows);
        return rows[start..].to_vec();
    }
    let tail = tail_since_seal(rows, seal);
    let mut out = vec![seal.unwrap().clone()];
    out.extend_from_slice(&tail[..tail.len().min(tail_rows)]);
    out
}

// ── Chain verification ────────────────────────────────────────────────────────

/// Compute the content-addressed sha256 for a row (excludes `sha256` and `artifact_discovery`).
pub fn row_sha256(row: &Value) -> String {
    if let Some(obj) = row.as_object() {
        let signed: serde_json::Map<String, Value> = obj
            .iter()
            .filter(|(k, _)| k.as_str() != "sha256" && k.as_str() != "artifact_discovery")
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect();
        let canonical = serde_json::to_string(&signed).unwrap_or_default();
        let hash = Sha256::digest(canonical.as_bytes());
        return hex::encode(hash);
    }
    hex::encode(Sha256::digest(b"{}"))
}

/// Verify chain integrity of `tail_rows` starting from `seal`.
///
/// Each row's `previous` must equal the previous row's `sha256`, and each
/// row's `sha256` must match the computed digest. Returns `Err` on violation.
pub fn verify_tail(seal: &Value, tail_rows: &[Value]) -> Result<(), String> {
    let mut prev_sha = seal
        .get("sha256")
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_owned();

    for (i, row) in tail_rows.iter().enumerate() {
        let previous = row.get("previous").and_then(Value::as_str).unwrap_or("");
        if previous != prev_sha {
            return Err(format!(
                "Chain broken at tail row {i}: previous={previous:?} expected={prev_sha:?}"
            ));
        }
        let stored = row.get("sha256").and_then(Value::as_str).unwrap_or("");
        let expected = row_sha256(row);
        if stored != expected {
            return Err(format!(
                "Hash mismatch at tail row {i}: stored={stored:?} computed={expected:?}"
            ));
        }
        prev_sha = stored.to_owned();
    }
    Ok(())
}

// ── Balance computation ───────────────────────────────────────────────────────

/// Compute credit balance for `peer_id` from seal snapshot + tail `CREDIT_DELTA` events.
pub fn balance_from_seal(seal: &Value, tail_rows: &[Value], peer_id: &str) -> i64 {
    let snapshot = seal
        .get("credit_balance_snapshot")
        .and_then(Value::as_object);
    let base: i64 = snapshot
        .and_then(|m| m.get(peer_id))
        .and_then(Value::as_i64)
        .unwrap_or(0);

    let delta: i64 = tail_rows
        .iter()
        .filter(|r| {
            r.get("kind").and_then(Value::as_str) == Some("CREDIT_DELTA")
                && r.get("peer").and_then(Value::as_str) == Some(peer_id)
        })
        .map(|r| {
            r.get("delta_units")
                .or_else(|| r.get("amount_units"))
                .and_then(Value::as_i64)
                .unwrap_or(0)
        })
        .sum();

    base + delta
}

// ── Sync summary ──────────────────────────────────────────────────────────────

/// Summary of local sync state (schema-compatible with `ledger_sync.py`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncSummary {
    pub schema: String,
    pub total_rows: usize,
    pub seal_at_unix: Option<f64>,
    pub seal_sequence: Option<u64>,
    pub tail_rows_since_seal: usize,
    pub is_light_peer_sufficient: bool,
    pub pruned_row_count: usize,
}

/// Compute sync state summary for `rows`.
pub fn sync_summary(rows: &[Value]) -> SyncSummary {
    let seal = latest_seal(rows);
    let tail = tail_since_seal(rows, seal);

    let (seal_at_unix, seal_sequence) = if let Some(s) = seal {
        let at = s.get("at_unix").and_then(Value::as_f64);
        let seq = s
            .get("sequence")
            .or_else(|| s.get("block_height"))
            .and_then(Value::as_u64);
        (at, seq)
    } else {
        (None, None)
    };

    let included = if seal.is_some() { 1 + tail.len() } else { tail.len() };
    let pruned = rows.len().saturating_sub(included);

    SyncSummary {
        schema: SCHEMA.to_owned(),
        total_rows: rows.len(),
        seal_at_unix,
        seal_sequence,
        tail_rows_since_seal: tail.len(),
        is_light_peer_sufficient: seal.is_some(),
        pruned_row_count: pruned,
    }
}

// ── Sync merge ────────────────────────────────────────────────────────────────

/// Result of merging an incoming peer payload.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MergeResult {
    pub merged: Vec<Value>,
    pub added: usize,
    pub skipped: usize,
}

/// Merge an incoming peer tail payload into local rows (content-addressed dedup).
///
/// Returns `Err` if chain integrity verification fails.
pub fn apply_tail_payload(
    local_rows: &[Value],
    payload: &SyncPayload,
) -> Result<MergeResult, String> {
    if let Some(seal) = &payload.seal {
        verify_tail(seal, &payload.tail)?;
    }

    let local_sha_set: std::collections::HashSet<String> = local_rows
        .iter()
        .map(|r| {
            r.get("sha256")
                .and_then(Value::as_str)
                .map(str::to_owned)
                .unwrap_or_else(|| row_sha256(r))
        })
        .collect();

    let mut merged: Vec<Value> = local_rows.to_vec();
    let mut sha_set = local_sha_set;
    let mut added = 0usize;
    let mut skipped = 0usize;

    for row in &payload.tail {
        let sha = row
            .get("sha256")
            .and_then(Value::as_str)
            .map(str::to_owned)
            .unwrap_or_else(|| row_sha256(row));
        if sha_set.contains(&sha) {
            skipped += 1;
        } else {
            sha_set.insert(sha);
            merged.push(row.clone());
            added += 1;
        }
    }

    Ok(MergeResult { merged, added, skipped })
}

// ── Sync packet types ─────────────────────────────────────────────────────────

/// Payload a full peer sends to a light peer (or over RPC).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncPayload {
    pub seal: Option<Value>,
    pub tail: Vec<Value>,
}

/// Build a `SyncPayload` from local rows (full-peer side).
pub fn build_sync_payload(rows: &[Value]) -> SyncPayload {
    let seal = latest_seal(rows);
    if seal.is_none() {
        return SyncPayload { seal: None, tail: vec![] };
    }
    let seal_val = seal.unwrap().clone();
    let tail = tail_since_seal(rows, seal).to_vec();
    SyncPayload { seal: Some(seal_val), tail }
}

/// Attestation record for a completed peer sync event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncAttestation {
    pub schema: String,
    pub peer_id: String,
    pub payload_sha256: String,
    pub merged_count: usize,
    pub added_count: usize,
    pub attested_at: f64,
}

/// Build an attestation for a completed peer sync.
pub fn build_sync_attestation(
    peer_id: &str,
    payload_sha256: &str,
    merged_count: usize,
    added_count: usize,
) -> SyncAttestation {
    SyncAttestation {
        schema: "urace-sync-attestation-v1".to_owned(),
        peer_id: peer_id.to_owned(),
        payload_sha256: payload_sha256.to_owned(),
        merged_count,
        added_count,
        attested_at: unix_now(),
    }
}

// ── Fork resolution ───────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ForkAction {
    KeepLocal,
    AcceptIncoming,
    ForkDetected,
}

/// Result of fork resolution policy check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForkResolution {
    pub action: ForkAction,
    pub fork_detected: bool,
    pub local_head_sha: String,
    pub incoming_head_sha: String,
    pub reason: String,
}

/// Detect and resolve a ledger fork between local rows and incoming payload.
///
/// Policy: prefer longer chain; equal length → lexicographically higher head sha256.
pub fn fork_resolution_policy(local_rows: &[Value], payload: &SyncPayload) -> ForkResolution {
    let local_head_sha = local_rows
        .last()
        .and_then(|r| r.get("sha256"))
        .and_then(Value::as_str)
        .unwrap_or(&"0".repeat(64))
        .to_owned();

    let incoming_tail = &payload.tail;
    let incoming_seal = payload.seal.as_ref();

    let incoming_head_sha = incoming_tail
        .last()
        .and_then(|r| r.get("sha256"))
        .and_then(Value::as_str)
        .or_else(|| incoming_seal.and_then(|s| s.get("sha256")).and_then(Value::as_str))
        .unwrap_or(&"0".repeat(64))
        .to_owned();

    if local_head_sha == incoming_head_sha {
        return ForkResolution {
            action: ForkAction::KeepLocal,
            fork_detected: false,
            local_head_sha,
            incoming_head_sha,
            reason: "identical heads".to_owned(),
        };
    }

    let local_seal = latest_seal(local_rows);
    let local_seq = local_seal
        .and_then(|s| s.get("sequence").or_else(|| s.get("block_height")))
        .and_then(Value::as_u64)
        .unwrap_or(0);
    let incoming_seq = incoming_seal
        .and_then(|s| s.get("sequence").or_else(|| s.get("block_height")))
        .and_then(Value::as_u64)
        .unwrap_or(0);

    let local_total = local_seq + local_rows.len() as u64;
    let incoming_total = incoming_seq + incoming_tail.len() as u64;

    if incoming_total > local_total {
        ForkResolution {
            action: ForkAction::AcceptIncoming,
            fork_detected: true,
            local_head_sha,
            incoming_head_sha,
            reason: format!("incoming chain longer ({incoming_total} > {local_total})"),
        }
    } else if local_total > incoming_total {
        ForkResolution {
            action: ForkAction::KeepLocal,
            fork_detected: true,
            local_head_sha,
            incoming_head_sha,
            reason: format!("local chain longer ({local_total} > {incoming_total})"),
        }
    } else if incoming_head_sha > local_head_sha {
        ForkResolution {
            action: ForkAction::AcceptIncoming,
            fork_detected: true,
            local_head_sha,
            incoming_head_sha,
            reason: "equal length, incoming sha256 wins tiebreak".to_owned(),
        }
    } else {
        ForkResolution {
            action: ForkAction::KeepLocal,
            fork_detected: true,
            local_head_sha,
            incoming_head_sha,
            reason: "equal length, local sha256 wins tiebreak".to_owned(),
        }
    }
}

// ── Checkpoint ────────────────────────────────────────────────────────────────

/// Checkpoint record comparing local and peer chain heads.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckpointRecord {
    pub schema: String,
    pub peer_id: String,
    pub local_sequence: u64,
    pub local_head_sha: String,
    pub local_row_count: usize,
    pub checked_at: f64,
    pub peer_sequence: Option<u64>,
    pub peer_head_sha: Option<String>,
    pub peer_row_count: Option<usize>,
    pub matches: Option<bool>,
    pub status: Option<String>,
}

/// Exchange chain head checkpoint with a peer (pure logic, no network I/O).
pub fn exchange_checkpoint(
    local_rows: &[Value],
    peer_id: &str,
    peer_rows: Option<&[Value]>,
) -> CheckpointRecord {
    let local_seal = latest_seal(local_rows);
    let local_seq = local_seal
        .and_then(|s| s.get("sequence").or_else(|| s.get("block_height")))
        .and_then(Value::as_u64)
        .unwrap_or(0);
    let local_head = local_rows
        .last()
        .and_then(|r| r.get("sha256"))
        .and_then(Value::as_str)
        .unwrap_or(&"0".repeat(64))
        .to_owned();

    let mut rec = CheckpointRecord {
        schema: SCHEMA.to_owned(),
        peer_id: peer_id.to_owned(),
        local_sequence: local_seq,
        local_head_sha: local_head.clone(),
        local_row_count: local_rows.len(),
        checked_at: unix_now(),
        peer_sequence: None,
        peer_head_sha: None,
        peer_row_count: None,
        matches: None,
        status: None,
    };

    if let Some(peers) = peer_rows {
        let peer_seal = latest_seal(peers);
        let peer_seq = peer_seal
            .and_then(|s| s.get("sequence").or_else(|| s.get("block_height")))
            .and_then(Value::as_u64)
            .unwrap_or(0);
        let peer_head = peers
            .last()
            .and_then(|r| r.get("sha256"))
            .and_then(Value::as_str)
            .unwrap_or(&"0".repeat(64))
            .to_owned();
        let matches = local_head == peer_head;
        rec.peer_sequence = Some(peer_seq);
        rec.peer_head_sha = Some(peer_head);
        rec.peer_row_count = Some(peers.len());
        rec.matches = Some(matches);
        rec.status = Some(if matches { "MATCH" } else { "CHECKPOINT_CONFLICT" }.to_owned());
    }

    rec
}

// ── Internal ──────────────────────────────────────────────────────────────────

fn unix_now() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_seal(seq: u64, sha: &str) -> Value {
        json!({
            "kind": "LEDGER_BLOCK_SEAL",
            "at_unix": 1_000_000.0 + seq as f64,
            "sequence": seq,
            "sha256": sha,
            "credit_balance_snapshot": {}
        })
    }

    fn make_row(sha: &str, prev: &str) -> Value {
        json!({ "sha256": sha, "previous": prev, "kind": "DATA" })
    }

    #[test]
    fn latest_seal_returns_most_recent() {
        let rows = vec![
            make_seal(1, "aaa"),
            json!({"kind": "DATA", "sha256": "ddd"}),
            make_seal(5, "eee"),
        ];
        let seal = latest_seal(&rows).unwrap();
        assert_eq!(seal.get("sequence").and_then(Value::as_u64), Some(5));
    }

    #[test]
    fn tail_since_seal_slices_correctly() {
        let seal = make_seal(1, "s1");
        let r1 = make_row("r1", "s1");
        let r2 = make_row("r2", "r1");
        let rows = vec![seal.clone(), r1.clone(), r2.clone()];
        let tail = tail_since_seal(&rows, Some(&seal));
        assert_eq!(tail.len(), 2);
    }

    #[test]
    fn prune_to_window_respects_limit() {
        let seal = make_seal(1, "s0");
        let mut rows = vec![seal];
        for i in 0..1500usize {
            rows.push(json!({"sha256": format!("r{i}"), "kind": "DATA"}));
        }
        let pruned = prune_to_window(&rows, DEFAULT_TAIL_ROWS);
        assert_eq!(pruned.len(), DEFAULT_TAIL_ROWS + 1); // seal + 1000 tail
    }

    #[test]
    fn balance_from_seal_sums_deltas() {
        let seal = json!({
            "kind": "LEDGER_BLOCK_SEAL",
            "sha256": "s",
            "credit_balance_snapshot": {"peer1": 1000}
        });
        let tail = vec![
            json!({"kind": "CREDIT_DELTA", "peer": "peer1", "delta_units": 50}),
            json!({"kind": "CREDIT_DELTA", "peer": "peer1", "delta_units": -20}),
            json!({"kind": "CREDIT_DELTA", "peer": "peer2", "delta_units": 999}),
        ];
        assert_eq!(balance_from_seal(&seal, &tail, "peer1"), 1030);
        assert_eq!(balance_from_seal(&seal, &tail, "peer2"), 999);
        assert_eq!(balance_from_seal(&seal, &tail, "peer3"), 0);
    }

    #[test]
    fn fork_resolution_longer_chain_wins() {
        let local: Vec<Value> = (0..5).map(|i| json!({"sha256": format!("l{i}")})).collect();
        let seal = make_seal(0, "iseal");
        let tail: Vec<Value> = (0..10)
            .map(|i| json!({"sha256": format!("r{i}")}))
            .collect();
        let payload = SyncPayload { seal: Some(seal), tail };
        let res = fork_resolution_policy(&local, &payload);
        assert_eq!(res.action, ForkAction::AcceptIncoming);
        assert!(res.fork_detected);
    }
}
