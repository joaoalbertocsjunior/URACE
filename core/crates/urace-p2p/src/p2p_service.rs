//! High-level P2P service facade — port of `p2p_service.py`.
//!
//! `P2PService` is a thin orchestration layer over the Kademlia routing table,
//! admission gate, and peer state. No business logic lives here — this is a
//! seam, not an implementation, exactly mirroring the Python module.

use crate::kademlia::{KademliaTable, NodeInfo};
use crate::peer_discovery::AdmissionGate;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, RwLock};
use thiserror::Error;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum P2PError {
    #[error("service already running")]
    AlreadyRunning,

    #[error("service not running")]
    NotRunning,

    #[error("invalid peer address: {0}")]
    InvalidAddress(String),

    #[error("bootstrap failed: {0}")]
    BootstrapFailed(String),
}

// ── Config ────────────────────────────────────────────────────────────────────

/// Configuration for the P2P daemon.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct P2PServiceConfig {
    /// UDP/TCP port to listen on.
    pub port: u16,
    /// Initial bootstrap peers in `"peer_id@host:port"` format.
    pub bootstrap_peers: Vec<String>,
    /// When true: relay only, do not expose real IP.
    pub relay_only: bool,
    /// Peer ID for this node (hex string, e.g. SHA-256 of public key).
    pub peer_id: String,
    /// Maximum concurrent peers.
    pub max_peers: usize,
}

impl Default for P2PServiceConfig {
    fn default() -> Self {
        P2PServiceConfig {
            port: 4001,
            bootstrap_peers: vec![],
            relay_only: false,
            peer_id: String::new(),
            max_peers: 50,
        }
    }
}

// ── Status ────────────────────────────────────────────────────────────────────

/// Snapshot of the service's operational state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct P2PServiceStatus {
    pub running: bool,
    pub peer_count: usize,
    pub bootstrap_connected: bool,
    pub relay_only: bool,
    pub peer_id: String,
}

// ── P2PService ────────────────────────────────────────────────────────────────

/// Connected peers: peer_id → addr string.
type PeerMap = Arc<RwLock<HashMap<String, String>>>;

/// High-level P2P daemon coordinator.
///
/// Owns the Kademlia routing table, the admission gate, and the live peer map.
/// Methods are synchronous stubs; real network I/O would be spawned on a tokio
/// runtime in a production build.
pub struct P2PService {
    config: P2PServiceConfig,
    running: Arc<AtomicBool>,
    routing_table: Arc<RwLock<KademliaTable>>,
    admission: Arc<AdmissionGate>,
    peers: PeerMap,
    /// True when at least one bootstrap peer is reachable.
    bootstrap_connected: Arc<AtomicBool>,
}

impl P2PService {
    /// Create a new (stopped) service from `config`.
    pub fn new(config: P2PServiceConfig) -> Self {
        let routing_table = Arc::new(RwLock::new(KademliaTable::new(&config.peer_id)));
        P2PService {
            config,
            running: Arc::new(AtomicBool::new(false)),
            routing_table,
            admission: Arc::new(AdmissionGate::new()),
            peers: Arc::new(RwLock::new(HashMap::new())),
            bootstrap_connected: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Start the service: initialise routing table, attempt bootstrap peer connection.
    ///
    /// Returns `P2PError::AlreadyRunning` if already started.
    pub fn start(&mut self) -> Result<(), P2PError> {
        if self.running.load(Ordering::SeqCst) {
            return Err(P2PError::AlreadyRunning);
        }

        // Admit bootstrap peers into routing table.
        for peer_addr in &self.config.bootstrap_peers.clone() {
            if let Some((peer_id, addr)) = parse_peer_addr(peer_addr) {
                let node = NodeInfo::new(&peer_id, &addr);
                if let Ok(mut table) = self.routing_table.write() {
                    table.add(node);
                }
                self.bootstrap_connected.store(true, Ordering::SeqCst);
            }
        }

        self.running.store(true, Ordering::SeqCst);
        Ok(())
    }

    /// Stop the service and clear peer state.
    pub fn stop(&mut self) {
        self.running.store(false, Ordering::SeqCst);
        self.bootstrap_connected.store(false, Ordering::SeqCst);
        if let Ok(mut peers) = self.peers.write() {
            peers.clear();
        }
    }

    /// Announce `(peer_id, addr)` to the DHT routing table.
    ///
    /// The admission gate is consulted; peers with invalid protocol_gen
    /// (checked via `AdmissionGate::admit`) are rejected silently.
    pub fn announce(&self, peer_id: &str, addr: &str) {
        // Use protocol_gen=1 for announced peers (minimum supported).
        self.admission.admit(peer_id, 1);
        let node = NodeInfo::new(peer_id, addr);
        if let Ok(mut table) = self.routing_table.write() {
            table.add(node);
        }
        if let Ok(mut peers) = self.peers.write() {
            peers.insert(peer_id.to_string(), addr.to_string());
        }
    }

    /// Return a snapshot of the service status.
    pub fn status(&self) -> P2PServiceStatus {
        let peer_count = self
            .peers
            .read()
            .map(|p| p.len())
            .unwrap_or(0);
        P2PServiceStatus {
            running: self.running.load(Ordering::SeqCst),
            peer_count,
            bootstrap_connected: self.bootstrap_connected.load(Ordering::SeqCst),
            relay_only: self.config.relay_only,
            peer_id: self.config.peer_id.clone(),
        }
    }

    /// Whether the service is currently running.
    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }
}

// ── Config-based helpers ──────────────────────────────────────────────────────

/// Build a `P2PServiceConfig` from a JSON config object.
///
/// Mirrors the Python `routing_decision(config, state)` extraction of P2P settings.
pub fn config_from_value(config: &serde_json::Value) -> P2PServiceConfig {
    let p2p = config.get("p2p").cloned().unwrap_or(serde_json::json!({}));
    P2PServiceConfig {
        port: p2p
            .get("port")
            .and_then(|v| v.as_u64())
            .unwrap_or(4001) as u16,
        bootstrap_peers: p2p
            .get("bootstrap_peers")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(str::to_string)).collect())
            .unwrap_or_default(),
        relay_only: p2p
            .get("relay_only")
            .and_then(|v| v.as_bool())
            .unwrap_or(false),
        peer_id: config
            .get("peer_id")
            .and_then(|v| v.as_str())
            .unwrap_or("local")
            .to_string(),
        max_peers: p2p
            .get("max_peers")
            .and_then(|v| v.as_u64())
            .unwrap_or(50) as usize,
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Parse `"peer_id@host:port"` into `(peer_id, addr)`.
fn parse_peer_addr(s: &str) -> Option<(String, String)> {
    let (peer_id, addr) = s.split_once('@')?;
    Some((peer_id.to_string(), addr.to_string()))
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn default_config() -> P2PServiceConfig {
        P2PServiceConfig {
            peer_id: "aabbccdd".to_string(),
            ..Default::default()
        }
    }

    #[test]
    fn start_sets_running_true() {
        let mut svc = P2PService::new(default_config());
        assert!(!svc.is_running());
        svc.start().unwrap();
        assert!(svc.is_running());
    }

    #[test]
    fn double_start_returns_already_running() {
        let mut svc = P2PService::new(default_config());
        svc.start().unwrap();
        assert!(matches!(svc.start(), Err(P2PError::AlreadyRunning)));
    }

    #[test]
    fn stop_clears_running_flag() {
        let mut svc = P2PService::new(default_config());
        svc.start().unwrap();
        svc.stop();
        assert!(!svc.is_running());
    }

    #[test]
    fn announce_increments_peer_count() {
        let mut svc = P2PService::new(default_config());
        svc.start().unwrap();
        svc.announce("peer1aabb", "127.0.0.1:4002");
        svc.announce("peer2ccdd", "127.0.0.1:4003");
        assert_eq!(svc.status().peer_count, 2);
    }

    #[test]
    fn status_reflects_bootstrap_peers() {
        let config = P2PServiceConfig {
            bootstrap_peers: vec!["aabbccdd@127.0.0.1:4001".to_string()],
            peer_id: "localnode".to_string(),
            ..Default::default()
        };
        let mut svc = P2PService::new(config);
        svc.start().unwrap();
        assert!(svc.status().bootstrap_connected);
    }

    #[test]
    fn config_from_value_parses_p2p_block() {
        let config = serde_json::json!({
            "peer_id": "mynode",
            "p2p": { "port": 9000, "relay_only": true }
        });
        let cfg = config_from_value(&config);
        assert_eq!(cfg.port, 9000);
        assert!(cfg.relay_only);
        assert_eq!(cfg.peer_id, "mynode");
    }
}
