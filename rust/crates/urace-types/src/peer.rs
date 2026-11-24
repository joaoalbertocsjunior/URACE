//! Peer/node identity types.

use serde::{Deserialize, Serialize};

/// Routing-table node entry — matches `NodeInfo` in `kademlia.py`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeInfo {
    pub peer_id: String,
    /// SHA-256(peer_id) as 256-bit integer (hex string).
    pub node_id_hex: String,
    pub endpoint: String,
    pub last_seen_secs: f64,
}

impl NodeInfo {
    pub fn node_id(&self) -> u128 {
        // Lower 128 bits of the hex node ID for distance calculations.
        u128::from_str_radix(&self.node_id_hex[32..], 16).unwrap_or(0)
    }
}

/// A discovered peer entry for the admission system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerRecord {
    pub peer_id: String,
    pub endpoint: String,
    pub public_key_hex: Option<String>,
    pub admitted: bool,
    pub first_seen_secs: f64,
    pub last_seen_secs: f64,
}
