//! Phase 2: PeerTaskRouter — broadcast bid requests to K closest peers,
//! collect bids within RPC_TIMEOUT_SECS, return the cheapest qualified bid.
//!
//! Falls back to a self-bid at `local_cost_usd` when no peers respond.
//!
//! # Message flow
//! 1. Router sends `KademliaMessage::TaskBidRequest` to K closest peers.
//! 2. Each peer that accepts replies with `KademliaMessage::TaskBidResponse`.
//! 3. After `RPC_TIMEOUT_SECS`, the cheapest accepted bid wins.
//! 4. If no bids arrive, the router returns a self-bid.

use crate::kademlia::{peer_id_to_node_id, KademliaTable, K_BUCKET_SIZE};
use crate::transport::{new_txid, KademliaMessage, RPC_TIMEOUT_SECS, UdpTransport};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;

// ── Wire types ────────────────────────────────────────────────────────────────

/// Sent by the router to candidate peers to solicit a cost bid.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskBidRequest {
    pub task_id: String,
    pub task_type: String,
    pub estimated_tokens: u64,
    pub required_capability: String,
    pub transaction_id: String,
}

/// Returned by a peer that is willing and able to execute the task.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskBid {
    pub peer_id: String,
    pub task_id: String,
    pub bid_usd: f64,
    /// "subprocess" or "cloud-llm"
    pub capability_attestation: String,
    pub transaction_id: String,
}

// ── PeerTaskRouter ────────────────────────────────────────────────────────────

pub struct PeerTaskRouter {
    transport: Arc<UdpTransport>,
    routing_table: Arc<RwLock<KademliaTable>>,
    local_peer_id: String,
}

impl PeerTaskRouter {
    pub fn new(
        transport: Arc<UdpTransport>,
        routing_table: Arc<RwLock<KademliaTable>>,
        peer_id: &str,
    ) -> Self {
        PeerTaskRouter {
            transport,
            routing_table,
            local_peer_id: peer_id.to_owned(),
        }
    }

    /// Broadcast a task bid request to the K closest peers, collect bids within
    /// `RPC_TIMEOUT_SECS`, and return the cheapest qualified bid.
    ///
    /// Falls back to a self-bid at `local_cost_usd` if no peers respond.
    pub async fn route_task(
        &self,
        task_id: &str,
        task_type: &str,
        estimated_tokens: u64,
        local_cost_usd: f64,
    ) -> TaskBid {
        let txid = new_txid();

        let bid_request = TaskBidRequest {
            task_id: task_id.to_owned(),
            task_type: task_type.to_owned(),
            estimated_tokens,
            required_capability: "subprocess".to_owned(),
            transaction_id: txid.clone(),
        };

        let request_value = match serde_json::to_value(&bid_request) {
            Ok(v) => v,
            Err(e) => {
                tracing::warn!("route_task: failed to serialise bid request: {e}");
                return self.self_bid(task_id, local_cost_usd, &txid);
            }
        };

        // Find K closest peers by XOR distance to task_id.
        let target_node_id = peer_id_to_node_id(task_id);
        let candidates: Vec<(String, String)> = {
            let table = self.routing_table.read().await;
            table
                .closest(&target_node_id, K_BUCKET_SIZE)
                .into_iter()
                .map(|n| (n.peer_id.clone(), n.endpoint.clone()))
                .collect()
        };

        if candidates.is_empty() {
            tracing::debug!("route_task: no peers in routing table — self-bid");
            return self.self_bid(task_id, local_cost_usd, &txid);
        }

        // Send TaskBidRequest to each candidate.
        let bid_msg = KademliaMessage::TaskBidRequest {
            node_id: self.local_peer_id.clone(),
            task_id: task_id.to_owned(),
            value: request_value,
            transaction_id: txid.clone(),
        };

        for (_peer_id, endpoint) in &candidates {
            if let Err(e) = self.transport.send(endpoint, &bid_msg).await {
                tracing::debug!("route_task: send to {endpoint} failed: {e}");
            }
        }

        // Open receive loop and collect TaskBidResponse messages within timeout.
        let (mut rx, _handle) = self.transport.spawn_receive_loop();
        let deadline = Duration::from_secs(RPC_TIMEOUT_SECS);
        let mut bids: Vec<TaskBid> = Vec::new();
        let expected_responses = candidates.len();

        let collect = async {
            while bids.len() < expected_responses {
                match rx.recv().await {
                    Some(inbound) => {
                        if let KademliaMessage::TaskBidResponse {
                            transaction_id,
                            value: Some(bid_value),
                            ..
                        } = inbound.message
                        {
                            if transaction_id == txid {
                                match serde_json::from_value::<TaskBid>(bid_value) {
                                    Ok(bid) if bid.task_id == task_id => bids.push(bid),
                                    Ok(_) => {}
                                    Err(e) => tracing::debug!("route_task: bad bid payload: {e}"),
                                }
                            }
                        }
                    }
                    None => break,
                }
            }
        };

        let _ = tokio::time::timeout(deadline, collect).await;

        // Pick the cheapest bid; fall back to self if none arrived.
        bids.into_iter()
            .min_by(|a, b| a.bid_usd.partial_cmp(&b.bid_usd).unwrap_or(std::cmp::Ordering::Equal))
            .unwrap_or_else(|| self.self_bid(task_id, local_cost_usd, &txid))
    }

    fn self_bid(&self, task_id: &str, cost_usd: f64, txid: &str) -> TaskBid {
        TaskBid {
            peer_id: self.local_peer_id.clone(),
            task_id: task_id.to_owned(),
            bid_usd: cost_usd,
            capability_attestation: "subprocess".to_owned(),
            transaction_id: txid.to_owned(),
        }
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kademlia::NodeInfo;

    #[tokio::test]
    async fn self_bid_when_no_peers() {
        let transport = Arc::new(UdpTransport::bind("127.0.0.1:0").await.unwrap());
        let table = Arc::new(RwLock::new(KademliaTable::new("router-node")));
        let router = PeerTaskRouter::new(transport, table, "router-node");

        let bid = router
            .route_task("task-001", "lint", 100, 0.05)
            .await;

        assert_eq!(bid.peer_id, "router-node");
        assert_eq!(bid.task_id, "task-001");
        assert!((bid.bid_usd - 0.05).abs() < 1e-10);
    }

    #[tokio::test]
    async fn bid_serialization_roundtrip() {
        let bid = TaskBid {
            peer_id: "peer-x".into(),
            task_id: "task-42".into(),
            bid_usd: 0.123,
            capability_attestation: "cloud-llm".into(),
            transaction_id: "tx-abc".into(),
        };
        let serialized = serde_json::to_value(&bid).unwrap();
        let deserialized: TaskBid = serde_json::from_value(serialized).unwrap();
        assert_eq!(deserialized.peer_id, bid.peer_id);
        assert!((deserialized.bid_usd - bid.bid_usd).abs() < 1e-15);
    }

    #[tokio::test]
    async fn route_task_with_unreachable_peers_falls_back_to_self() {
        let transport = Arc::new(UdpTransport::bind("127.0.0.1:0").await.unwrap());
        let table = Arc::new(RwLock::new(KademliaTable::new("router-node")));
        {
            let mut t = table.write().await;
            // Add a peer pointing at a port that won't respond.
            t.add(NodeInfo::new("unreachable-peer", "127.0.0.1:19999"));
        }
        let router = PeerTaskRouter::new(Arc::clone(&transport), table, "router-node");

        let bid = router
            .route_task("task-no-response", "build", 200, 0.10)
            .await;

        // Should fall back to self-bid since no peer responded within timeout.
        assert_eq!(bid.peer_id, "router-node");
        assert!((bid.bid_usd - 0.10).abs() < 1e-10);
    }
}
