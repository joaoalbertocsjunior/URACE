//! M59 — Connection fingerprinting: detect when multiple claimed peer IDs share
//! the same underlying connection fingerprint (possible Sybil behind NAT or proxy).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct ConnectionFingerprint {
    /// SHA-256 hex of the IP portion of the peer address (port stripped).
    pub addr_hash: String,
    pub first_seen_unix: u64,
}

impl ConnectionFingerprint {
    /// Create from a peer address string "1.2.3.4:5678" — hashes the IP portion only.
    pub fn from_addr(addr: &str, first_seen_unix: u64) -> Self {
        let ip = extract_ip(addr);
        let mut h = Sha256::new();
        h.update(ip.as_bytes());
        let digest = h.finalize();
        ConnectionFingerprint {
            addr_hash: hex::encode(digest),
            first_seen_unix,
        }
    }
}

/// Strip the port from an address string, returning only the IP/hostname.
fn extract_ip(addr: &str) -> String {
    // Handle "[::1]:port" IPv6 bracket notation.
    let addr = addr.trim_start_matches('[');
    if let Some(colon) = addr.rfind(':') {
        let after = &addr[colon + 1..];
        if after.chars().all(|c| c.is_ascii_digit()) {
            return addr[..colon].trim_end_matches(']').to_string();
        }
    }
    addr.trim_end_matches(']').to_string()
}

/// Registry mapping connection fingerprints to the peer IDs observed on them.
pub struct FingerprintStore {
    /// addr_hash -> Vec<peer_id>
    registry: HashMap<String, Vec<String>>,
}

impl FingerprintStore {
    pub fn new() -> Self {
        FingerprintStore {
            registry: HashMap::new(),
        }
    }

    /// Register a peer_id under its fingerprint.
    pub fn register(&mut self, peer_id: &str, fp: &ConnectionFingerprint) {
        let peers = self.registry.entry(fp.addr_hash.clone()).or_default();
        if !peers.contains(&peer_id.to_string()) {
            peers.push(peer_id.to_string());
        }
    }

    /// Return the list of peer IDs sharing the same fingerprint as `fp`.
    pub fn peers_sharing_fingerprint(&self, fp: &ConnectionFingerprint) -> Vec<String> {
        self.registry
            .get(&fp.addr_hash)
            .cloned()
            .unwrap_or_default()
    }

    /// Return true if more than one distinct peer ID uses this fingerprint.
    pub fn is_shared(&self, fp: &ConnectionFingerprint) -> bool {
        self.registry
            .get(&fp.addr_hash)
            .map(|v| v.len() > 1)
            .unwrap_or(false)
    }
}

impl Default for FingerprintStore {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fp(addr: &str) -> ConnectionFingerprint {
        ConnectionFingerprint::from_addr(addr, 1_000)
    }

    #[test]
    fn test_single_peer_per_fingerprint_not_shared() {
        let mut store = FingerprintStore::new();
        let f = fp("1.2.3.4:9000");
        store.register("peer-A", &f);
        assert!(!store.is_shared(&f));
    }

    #[test]
    fn test_two_peer_ids_same_ip_is_shared() {
        let mut store = FingerprintStore::new();
        let f = fp("1.2.3.4:9000");
        store.register("peer-A", &f);
        store.register("peer-B", &f);
        assert!(store.is_shared(&f));
    }

    #[test]
    fn test_different_ips_not_shared() {
        let mut store = FingerprintStore::new();
        let f1 = fp("10.0.0.1:443");
        let f2 = fp("10.0.0.2:443");
        store.register("peer-X", &f1);
        store.register("peer-Y", &f2);
        assert!(!store.is_shared(&f1));
        assert!(!store.is_shared(&f2));
    }

    #[test]
    fn test_peers_sharing_returns_both_ids() {
        let mut store = FingerprintStore::new();
        let f = fp("5.5.5.5:1234");
        store.register("peer-1", &f);
        store.register("peer-2", &f);
        let mut sharing = store.peers_sharing_fingerprint(&f);
        sharing.sort();
        assert_eq!(sharing, vec!["peer-1", "peer-2"]);
    }

    #[test]
    fn test_duplicate_registration_idempotent() {
        let mut store = FingerprintStore::new();
        let f = fp("7.7.7.7:80");
        store.register("peer-Z", &f);
        store.register("peer-Z", &f); // duplicate — should not inflate count
        assert!(!store.is_shared(&f));
        assert_eq!(store.peers_sharing_fingerprint(&f).len(), 1);
    }

    #[test]
    fn test_fingerprint_same_ip_different_ports_equal() {
        // Port is stripped; two fingerprints from same IP but different ports must be equal.
        let f1 = fp("9.9.9.9:1000");
        let f2 = fp("9.9.9.9:2000");
        assert_eq!(f1.addr_hash, f2.addr_hash);
    }
}
