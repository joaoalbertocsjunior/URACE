//! P2P peer capability flags.
//!
//! Ported from `p2p_capabilities.py`. Each peer advertises which capabilities
//! it supports; capabilities are bitflags for compact wire representation.

use serde::{Deserialize, Serialize};

/// Capability flags for a URACE peer.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct PeerCapabilities {
    /// Can store features and serve them to peers.
    pub storage: bool,
    /// Can execute work tasks (LLM executor, sandbox, etc.).
    pub executor: bool,
    /// Can relay traffic for NAT-traversal-challenged peers.
    pub relay: bool,
    /// Runs a bootstrap/seed node for peer discovery.
    pub bootstrap: bool,
    /// Participates in consensus voting.
    pub consensus: bool,
    /// Provides ledger seal rewards (full node).
    pub sealer: bool,
    /// Accepts EVM settlement transactions.
    pub evm_settlement: bool,
    /// Runs a Kademlia DHT node.
    pub dht: bool,
}

impl PeerCapabilities {
    pub fn all_disabled() -> Self {
        PeerCapabilities::default()
    }

    pub fn full_node() -> Self {
        PeerCapabilities {
            storage: true,
            executor: false,
            relay: false,
            bootstrap: false,
            consensus: true,
            sealer: true,
            evm_settlement: false,
            dht: true,
        }
    }

    pub fn executor_node() -> Self {
        PeerCapabilities {
            storage: false,
            executor: true,
            relay: false,
            bootstrap: false,
            consensus: false,
            sealer: false,
            evm_settlement: false,
            dht: false,
        }
    }

    pub fn relay_node() -> Self {
        PeerCapabilities {
            storage: false,
            executor: false,
            relay: true,
            bootstrap: true,
            consensus: false,
            sealer: false,
            evm_settlement: false,
            dht: true,
        }
    }

    /// Convert to u16 bitmask for wire protocol.
    pub fn to_bits(&self) -> u16 {
        let mut bits: u16 = 0;
        if self.storage { bits |= 1 << 0; }
        if self.executor { bits |= 1 << 1; }
        if self.relay { bits |= 1 << 2; }
        if self.bootstrap { bits |= 1 << 3; }
        if self.consensus { bits |= 1 << 4; }
        if self.sealer { bits |= 1 << 5; }
        if self.evm_settlement { bits |= 1 << 6; }
        if self.dht { bits |= 1 << 7; }
        bits
    }

    /// Reconstruct from u16 bitmask.
    pub fn from_bits(bits: u16) -> Self {
        PeerCapabilities {
            storage: bits & (1 << 0) != 0,
            executor: bits & (1 << 1) != 0,
            relay: bits & (1 << 2) != 0,
            bootstrap: bits & (1 << 3) != 0,
            consensus: bits & (1 << 4) != 0,
            sealer: bits & (1 << 5) != 0,
            evm_settlement: bits & (1 << 6) != 0,
            dht: bits & (1 << 7) != 0,
        }
    }

    /// True if any capability is enabled.
    pub fn any_enabled(&self) -> bool {
        self.to_bits() != 0
    }

    /// True if the peer can participate in governance (consensus or sealer).
    pub fn governance_eligible(&self) -> bool {
        self.consensus || self.sealer
    }
}

/// Registry mapping peer_id → PeerCapabilities.
#[derive(Clone)]
pub struct CapabilityRegistry {
    entries: std::sync::Arc<dashmap::DashMap<String, PeerCapabilities>>,
}

impl Default for CapabilityRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl CapabilityRegistry {
    pub fn new() -> Self {
        CapabilityRegistry {
            entries: std::sync::Arc::new(dashmap::DashMap::new()),
        }
    }

    pub fn set(&self, peer_id: &str, caps: PeerCapabilities) {
        self.entries.insert(peer_id.to_owned(), caps);
    }

    pub fn get(&self, peer_id: &str) -> Option<PeerCapabilities> {
        self.entries.get(peer_id).map(|e| *e)
    }

    pub fn remove(&self, peer_id: &str) {
        self.entries.remove(peer_id);
    }

    /// All peers with a specific capability enabled.
    pub fn peers_with(&self, f: impl Fn(&PeerCapabilities) -> bool) -> Vec<String> {
        self.entries
            .iter()
            .filter(|e| f(e.value()))
            .map(|e| e.key().clone())
            .collect()
    }

    /// All executor-capable peers.
    pub fn executors(&self) -> Vec<String> {
        self.peers_with(|c| c.executor)
    }

    /// All relay peers.
    pub fn relays(&self) -> Vec<String> {
        self.peers_with(|c| c.relay)
    }

    /// All governance-eligible peers.
    pub fn governance_peers(&self) -> Vec<String> {
        self.peers_with(|c| c.governance_eligible())
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bits_roundtrip() {
        let caps = PeerCapabilities {
            storage: true,
            executor: true,
            relay: false,
            bootstrap: false,
            consensus: true,
            sealer: false,
            evm_settlement: false,
            dht: true,
        };
        let bits = caps.to_bits();
        let restored = PeerCapabilities::from_bits(bits);
        assert_eq!(caps, restored);
    }

    #[test]
    fn full_node_governance_eligible() {
        assert!(PeerCapabilities::full_node().governance_eligible());
    }

    #[test]
    fn executor_node_not_governance() {
        assert!(!PeerCapabilities::executor_node().governance_eligible());
    }

    #[test]
    fn registry_filter() {
        let reg = CapabilityRegistry::new();
        reg.set("peer-a", PeerCapabilities::executor_node());
        reg.set("peer-b", PeerCapabilities::relay_node());
        reg.set("peer-c", PeerCapabilities::full_node());
        assert_eq!(reg.executors().len(), 1);
        assert!(reg.executors().contains(&"peer-a".to_string()));
        assert_eq!(reg.relays().len(), 1);
        assert_eq!(reg.governance_peers().len(), 1);
        assert!(reg.governance_peers().contains(&"peer-c".to_string()));
    }

    #[test]
    fn all_disabled_any_enabled_false() {
        assert!(!PeerCapabilities::all_disabled().any_enabled());
    }

    #[test]
    fn serde_roundtrip() {
        let caps = PeerCapabilities::full_node();
        let json = serde_json::to_string(&caps).unwrap();
        let restored: PeerCapabilities = serde_json::from_str(&json).unwrap();
        assert_eq!(caps, restored);
    }
}
