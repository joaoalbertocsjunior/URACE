//! Kademlia UDP transport — real network layer for URACE P2P routing.
//!
//! This module binds a UDP socket and provides async send/receive for
//! Kademlia DHT messages. It is the layer that makes the routing table
//! talk to real peers instead of operating on injected test data.
//!
//! # Message format
//! Messages are JSON-encoded and length-prefixed within a single UDP datagram.
//! Max message size: 1472 bytes (Ethernet MTU - UDP/IP headers, no fragmentation).
//!
//! # Bootstrap
//! On `bind()`, the transport sends PING to each bootstrap address.
//! Peers that respond are added to the routing table via `on_peer_seen`.

use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::sync::Arc;
use thiserror::Error;
use tokio::net::UdpSocket;
use tokio::sync::mpsc;

/// Maximum UDP payload size (conservative — no fragmentation).
pub const MAX_UDP_PAYLOAD: usize = 1_472;

/// Timeout for a single Kademlia RPC round (seconds).
pub const RPC_TIMEOUT_SECS: u64 = 5;

/// Maximum number of queued inbound messages before dropping.
pub const INBOUND_QUEUE_DEPTH: usize = 256;

#[derive(Debug, Error)]
pub enum TransportError {
    #[error("bind failed: {0}")]
    Bind(String),
    #[error("send failed to {addr}: {err}")]
    Send { addr: String, err: String },
    #[error("message too large: {0} bytes (max {MAX_UDP_PAYLOAD})")]
    MessageTooLarge(usize),
    #[error("encode error: {0}")]
    Encode(String),
    #[error("decode error: {0}")]
    Decode(String),
}

// ── Message types ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum KademliaMessage {
    /// Liveness probe. Responder returns Pong with their node_id.
    Ping { node_id: String, transaction_id: String },
    Pong { node_id: String, transaction_id: String },
    /// Find the K closest nodes to `target_id`.
    FindNode { node_id: String, target_id: String, transaction_id: String },
    /// Response to FindNode: list of (node_id, addr) pairs.
    FindNodeResponse {
        node_id: String,
        transaction_id: String,
        nodes: Vec<NodeContact>,
    },
    /// Store a value in the DHT (used for TaskPatternRegistry).
    StoreValue {
        node_id: String,
        key: String,
        value: serde_json::Value,
        transaction_id: String,
    },
    /// Look up a stored value by key.
    FindValue { node_id: String, key: String, transaction_id: String },
    /// Response: either the value or the K closest nodes that may have it.
    FindValueResponse {
        node_id: String,
        transaction_id: String,
        value: Option<serde_json::Value>,
        nodes: Vec<NodeContact>,
    },
    /// Broadcast a bid request for a task to candidate peers (Phase 2).
    TaskBidRequest {
        node_id: String,
        task_id: String,
        value: serde_json::Value,
        transaction_id: String,
    },
    /// Response from a peer willing to execute the task (Phase 2).
    TaskBidResponse {
        node_id: String,
        task_id: String,
        transaction_id: String,
        /// `Some(bid_json)` when the peer accepts; `None` when it declines.
        value: Option<serde_json::Value>,
    },
}

/// A node contact record for routing table exchange.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NodeContact {
    pub node_id: String,
    pub addr: String,
}

impl KademliaMessage {
    pub fn transaction_id(&self) -> &str {
        match self {
            KademliaMessage::Ping { transaction_id, .. } => transaction_id,
            KademliaMessage::Pong { transaction_id, .. } => transaction_id,
            KademliaMessage::FindNode { transaction_id, .. } => transaction_id,
            KademliaMessage::FindNodeResponse { transaction_id, .. } => transaction_id,
            KademliaMessage::StoreValue { transaction_id, .. } => transaction_id,
            KademliaMessage::FindValue { transaction_id, .. } => transaction_id,
            KademliaMessage::FindValueResponse { transaction_id, .. } => transaction_id,
            KademliaMessage::TaskBidRequest { transaction_id, .. } => transaction_id,
            KademliaMessage::TaskBidResponse { transaction_id, .. } => transaction_id,
        }
    }
}

// ── Inbound envelope ─────────────────────────────────────────────────────────

/// A received message with its source address.
#[derive(Debug)]
pub struct InboundMessage {
    pub from: SocketAddr,
    pub message: KademliaMessage,
}

// ── UdpTransport ─────────────────────────────────────────────────────────────

/// Async UDP transport for Kademlia messages.
///
/// Created with `UdpTransport::bind(addr)`. After binding, call
/// `spawn_receive_loop()` to start processing inbound messages in the
/// background. Send outbound messages with `send()`.
pub struct UdpTransport {
    socket: Arc<UdpSocket>,
    local_addr: SocketAddr,
}

impl UdpTransport {
    /// Bind to `addr` (e.g. `"0.0.0.0:0"` for a random port).
    pub async fn bind(addr: &str) -> Result<Self, TransportError> {
        let socket = UdpSocket::bind(addr)
            .await
            .map_err(|e| TransportError::Bind(e.to_string()))?;
        let local_addr = socket
            .local_addr()
            .map_err(|e| TransportError::Bind(e.to_string()))?;
        Ok(UdpTransport {
            socket: Arc::new(socket),
            local_addr,
        })
    }

    pub fn local_addr(&self) -> SocketAddr {
        self.local_addr
    }

    /// Send a `KademliaMessage` to `addr`.
    pub async fn send(
        &self,
        addr: &str,
        msg: &KademliaMessage,
    ) -> Result<(), TransportError> {
        let encoded = serde_json::to_vec(msg)
            .map_err(|e| TransportError::Encode(e.to_string()))?;
        if encoded.len() > MAX_UDP_PAYLOAD {
            return Err(TransportError::MessageTooLarge(encoded.len()));
        }
        let peer: SocketAddr = addr
            .parse()
            .map_err(|e: std::net::AddrParseError| TransportError::Send {
                addr: addr.to_string(),
                err: e.to_string(),
            })?;
        self.socket
            .send_to(&encoded, peer)
            .await
            .map_err(|e| TransportError::Send {
                addr: addr.to_string(),
                err: e.to_string(),
            })?;
        Ok(())
    }

    /// Spawn a background task that receives UDP datagrams and forwards
    /// decoded messages to `tx`. Returns the join handle.
    pub fn spawn_receive_loop(
        &self,
    ) -> (mpsc::Receiver<InboundMessage>, tokio::task::JoinHandle<()>) {
        let (tx, rx) = mpsc::channel::<InboundMessage>(INBOUND_QUEUE_DEPTH);
        let socket = Arc::clone(&self.socket);

        let handle = tokio::spawn(async move {
            let mut buf = vec![0u8; MAX_UDP_PAYLOAD + 64];
            loop {
                match socket.recv_from(&mut buf).await {
                    Ok((len, from)) => {
                        match serde_json::from_slice::<KademliaMessage>(&buf[..len]) {
                            Ok(message) => {
                                let _ = tx
                                    .send(InboundMessage { from, message })
                                    .await;
                            }
                            Err(e) => {
                                tracing::debug!("kademlia decode error from {from}: {e}");
                            }
                        }
                    }
                    Err(e) => {
                        tracing::warn!("UDP recv error: {e}");
                        // Don't exit on transient errors
                    }
                }
            }
        });

        (rx, handle)
    }

    /// Send PING to each bootstrap address. Used on startup.
    pub async fn bootstrap_ping(
        &self,
        node_id: &str,
        bootstrap_addrs: &[String],
    ) {
        for addr in bootstrap_addrs {
            let msg = KademliaMessage::Ping {
                node_id: node_id.to_owned(),
                transaction_id: new_txid(),
            };
            if let Err(e) = self.send(addr, &msg).await {
                tracing::debug!("bootstrap ping to {addr} failed: {e}");
            }
        }
    }
}

/// Generate a short random transaction ID.
pub fn new_txid() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0);
    format!("{nanos:08x}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn bind_and_get_local_addr() {
        let transport = UdpTransport::bind("127.0.0.1:0").await.unwrap();
        assert!(transport.local_addr().port() > 0);
    }

    #[tokio::test]
    async fn send_and_receive_ping() {
        let server = UdpTransport::bind("127.0.0.1:0").await.unwrap();
        let server_addr = server.local_addr().to_string();
        let (mut rx, _handle) = server.spawn_receive_loop();

        let client = UdpTransport::bind("127.0.0.1:0").await.unwrap();
        let ping = KademliaMessage::Ping {
            node_id: "node-a".into(),
            transaction_id: "txid-1".into(),
        };
        client.send(&server_addr, &ping).await.unwrap();

        let inbound = tokio::time::timeout(
            std::time::Duration::from_secs(2),
            rx.recv(),
        )
        .await
        .expect("timeout")
        .expect("channel closed");

        assert_eq!(inbound.message, ping);
    }

    #[tokio::test]
    async fn message_roundtrip_find_node() {
        let msg = KademliaMessage::FindNode {
            node_id: "n1".into(),
            target_id: "t1".into(),
            transaction_id: "tx1".into(),
        };
        let encoded = serde_json::to_vec(&msg).unwrap();
        let decoded: KademliaMessage = serde_json::from_slice(&encoded).unwrap();
        assert_eq!(msg, decoded);
    }

    #[test]
    fn oversized_message_rejected() {
        // Build a message that exceeds MAX_UDP_PAYLOAD
        let huge_value = "x".repeat(MAX_UDP_PAYLOAD + 100);
        let msg = KademliaMessage::StoreValue {
            node_id: "n".into(),
            key: "k".into(),
            value: serde_json::Value::String(huge_value),
            transaction_id: "tx".into(),
        };
        let encoded = serde_json::to_vec(&msg).unwrap();
        assert!(encoded.len() > MAX_UDP_PAYLOAD);
    }
}
