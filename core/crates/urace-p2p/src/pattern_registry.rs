//! Phase 5: TaskPatternRegistry — collaborative learning via DHT.
//!
//! Each node maintains local task-pattern statistics and publishes them to the
//! 3 closest peers via `KademliaMessage::StoreValue`. Lookups use
//! `KademliaMessage::FindValue` with a `"pattern:<task_type>"` key.
//!
//! # Warm-start
//! On node start, `warm_start` fetches patterns for all known task types
//! from the network, populating the local cache before the first task runs.

use crate::kademlia::{peer_id_to_node_id, KademliaTable};
use crate::transport::{new_txid, KademliaMessage, RPC_TIMEOUT_SECS, UdpTransport};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;

/// Number of closest peers to replicate pattern records to.
const PATTERN_REPLICATION_FACTOR: usize = 3;

/// A single pattern record for one task type.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskPatternRecord {
    pub task_type: String,
    pub network_approval_rate: f64,
    pub sample_count: u64,
    pub p50_latency_ms: u64,
    pub median_cost_usd: f64,
    pub last_updated: String,
    pub node_id: String,
}

impl TaskPatternRecord {
    fn new_local(task_type: &str, node_id: &str) -> Self {
        TaskPatternRecord {
            task_type: task_type.to_owned(),
            network_approval_rate: 0.0,
            sample_count: 0,
            p50_latency_ms: 0,
            median_cost_usd: 0.0,
            last_updated: now_iso(),
            node_id: node_id.to_owned(),
        }
    }

    /// Update a local record with a new observation using an incremental mean.
    fn observe(&mut self, approved: bool, latency_ms: u64, cost_usd: f64) {
        let n = self.sample_count as f64;
        let n1 = n + 1.0;
        // Incremental mean for approval rate and cost.
        let approval_val = if approved { 1.0 } else { 0.0 };
        self.network_approval_rate = (self.network_approval_rate * n + approval_val) / n1;
        self.median_cost_usd = (self.median_cost_usd * n + cost_usd) / n1;
        // Approximate p50: running median update via simple average (good enough for sparse data).
        self.p50_latency_ms = ((self.p50_latency_ms as f64 * n + latency_ms as f64) / n1) as u64;
        self.sample_count += 1;
        self.last_updated = now_iso();
    }
}

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    // Minimal ISO-like string to avoid pulling in `time` crate formatting here.
    format!("{secs}")
}

// ── PatternRegistry ───────────────────────────────────────────────────────────

pub struct PatternRegistry {
    transport: Arc<UdpTransport>,
    routing_table: Arc<RwLock<KademliaTable>>,
    local_patterns: Arc<RwLock<HashMap<String, TaskPatternRecord>>>,
    local_node_id: String,
}

impl PatternRegistry {
    pub fn new(
        transport: Arc<UdpTransport>,
        routing_table: Arc<RwLock<KademliaTable>>,
        node_id: &str,
    ) -> Self {
        PatternRegistry {
            transport,
            routing_table,
            local_patterns: Arc::new(RwLock::new(HashMap::new())),
            local_node_id: node_id.to_owned(),
        }
    }

    /// Record a local observation and publish the updated record to 3 closest peers.
    pub async fn record_and_publish(
        &self,
        task_type: &str,
        approved: bool,
        latency_ms: u64,
        cost_usd: f64,
    ) {
        // Update local record.
        let record = {
            let mut patterns = self.local_patterns.write().await;
            let entry = patterns
                .entry(task_type.to_owned())
                .or_insert_with(|| TaskPatternRecord::new_local(task_type, &self.local_node_id));
            entry.observe(approved, latency_ms, cost_usd);
            entry.clone()
        };

        self.publish_record(&record).await;
    }

    async fn publish_record(&self, record: &TaskPatternRecord) {
        let key = format!("pattern:{}", record.task_type);
        let value = match serde_json::to_value(record) {
            Ok(v) => v,
            Err(e) => {
                tracing::warn!("pattern_registry: failed to serialise record: {e}");
                return;
            }
        };

        let txid = new_txid();
        let msg = KademliaMessage::StoreValue {
            node_id: self.local_node_id.clone(),
            key: key.clone(),
            value,
            transaction_id: txid,
        };

        let target = peer_id_to_node_id(&key);
        let peers: Vec<String> = {
            let table = self.routing_table.read().await;
            table
                .closest(&target, PATTERN_REPLICATION_FACTOR)
                .into_iter()
                .map(|n| n.endpoint.clone())
                .collect()
        };

        for endpoint in &peers {
            if let Err(e) = self.transport.send(endpoint, &msg).await {
                tracing::debug!("pattern_registry: publish to {endpoint} failed: {e}");
            }
        }
    }

    /// Look up the network-wide pattern for a task type.
    /// Returns the local record if the network lookup times out or fails.
    pub async fn lookup(&self, task_type: &str) -> Option<TaskPatternRecord> {
        let key = format!("pattern:{task_type}");
        let txid = new_txid();

        let msg = KademliaMessage::FindValue {
            node_id: self.local_node_id.clone(),
            key: key.clone(),
            transaction_id: txid.clone(),
        };

        let target = peer_id_to_node_id(&key);
        let peers: Vec<String> = {
            let table = self.routing_table.read().await;
            table
                .closest(&target, PATTERN_REPLICATION_FACTOR)
                .into_iter()
                .map(|n| n.endpoint.clone())
                .collect()
        };

        if peers.is_empty() {
            return self.local_patterns.read().await.get(task_type).cloned();
        }

        for endpoint in &peers {
            if let Err(e) = self.transport.send(endpoint, &msg).await {
                tracing::debug!("pattern_registry: lookup send to {endpoint} failed: {e}");
            }
        }

        // Wait for the first FindValueResponse that carries the pattern.
        let (mut rx, _handle) = self.transport.spawn_receive_loop();
        let deadline = Duration::from_secs(RPC_TIMEOUT_SECS);

        let network_result: Option<TaskPatternRecord> = {
            let wait = async {
                loop {
                    match rx.recv().await {
                        Some(inbound) => {
                            if let KademliaMessage::FindValueResponse {
                                transaction_id,
                                value: Some(v),
                                ..
                            } = inbound.message
                            {
                                if transaction_id == txid {
                                    if let Ok(record) =
                                        serde_json::from_value::<TaskPatternRecord>(v)
                                    {
                                        return Some(record);
                                    }
                                }
                            }
                        }
                        None => return None,
                    }
                }
            };
            tokio::time::timeout(deadline, wait).await.unwrap_or(None)
        };

        // Merge network result into local cache if found.
        if let Some(ref rec) = network_result {
            let mut patterns = self.local_patterns.write().await;
            patterns
                .entry(task_type.to_owned())
                .and_modify(|local| {
                    // Keep whichever has more samples.
                    if rec.sample_count > local.sample_count {
                        *local = rec.clone();
                    }
                })
                .or_insert_with(|| rec.clone());
        }

        if network_result.is_some() {
            return network_result;
        }
        self.local_patterns.read().await.get(task_type).cloned()
    }

    /// Warm-start: fetch patterns for all known task types from the network at startup.
    pub async fn warm_start(&self, known_task_types: &[String]) {
        for task_type in known_task_types {
            // Drive lookup but discard result — it populates the local cache as a side-effect.
            let _ = self.lookup(task_type).await;
        }
        tracing::debug!(
            "pattern_registry: warm_start complete for {} task types",
            known_task_types.len()
        );
    }

    /// Read access to the local patterns cache (for testing / introspection).
    pub async fn local_patterns_snapshot(&self) -> HashMap<String, TaskPatternRecord> {
        self.local_patterns.read().await.clone()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kademlia::KademliaTable;

    async fn make_registry(node_id: &str) -> PatternRegistry {
        let transport = UdpTransport::bind("127.0.0.1:0").await.unwrap();
        let table = Arc::new(RwLock::new(KademliaTable::new(node_id)));
        PatternRegistry::new(Arc::new(transport), table, node_id)
    }

    #[tokio::test]
    async fn record_and_lookup_local() {
        let registry = make_registry("node-pat-1").await;

        registry.record_and_publish("lint", true, 120, 0.01).await;
        registry.record_and_publish("lint", false, 200, 0.02).await;
        registry.record_and_publish("lint", true, 80, 0.015).await;

        let snap = registry.local_patterns_snapshot().await;
        let rec = snap.get("lint").expect("pattern should be present");
        assert_eq!(rec.sample_count, 3);
        // 2/3 approvals
        assert!((rec.network_approval_rate - 2.0 / 3.0).abs() < 1e-6);
    }

    #[tokio::test]
    async fn lookup_returns_none_for_unknown_type_no_peers() {
        let registry = make_registry("node-pat-2").await;
        // No peers and no local data → None.
        let result = registry.lookup("unknown-task-type").await;
        assert!(result.is_none());
    }

    #[tokio::test]
    async fn warm_start_with_no_peers_does_not_panic() {
        let registry = make_registry("node-pat-3").await;
        let types = vec!["lint".to_string(), "build".to_string()];
        // Should complete without panicking; no peers to query.
        registry.warm_start(&types).await;
    }

    #[tokio::test]
    async fn pattern_record_serialization() {
        let mut rec = TaskPatternRecord::new_local("build", "node-x");
        rec.observe(true, 300, 0.05);
        let v = serde_json::to_value(&rec).unwrap();
        let dec: TaskPatternRecord = serde_json::from_value(v).unwrap();
        assert_eq!(dec.task_type, "build");
        assert_eq!(dec.sample_count, 1);
        assert!((dec.network_approval_rate - 1.0).abs() < 1e-10);
    }
}
