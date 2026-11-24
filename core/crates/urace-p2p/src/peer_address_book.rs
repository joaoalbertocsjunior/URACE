//! Peer address book — maps peer_id → Vec<SocketAddr>.
//!
//! Ported from `peer_address_book.py`. Maintains a DashMap of peer_id → endpoints
//! with LRU eviction at MAX_PEERS capacity and MAX_ADDRS per peer.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::sync::Arc;

pub const MAX_PEERS: usize = 500;
pub const MAX_ADDRS_PER_PEER: usize = 5;

/// A single peer address book entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerAddrs {
    pub peer_id: String,
    /// Best-first ordered list of socket addresses.
    pub addrs: Vec<SocketAddr>,
    /// Unix timestamp of last successful contact (0 if never contacted).
    pub last_seen: f64,
}

/// DashMap-backed peer address book.
///
/// Thread-safe, designed for read-heavy DHT workloads.
/// Evicts least-recently-seen peers when at MAX_PEERS capacity.
#[derive(Clone)]
pub struct PeerAddressBook {
    entries: Arc<DashMap<String, PeerAddrs>>,
}

impl Default for PeerAddressBook {
    fn default() -> Self {
        Self::new()
    }
}

impl PeerAddressBook {
    pub fn new() -> Self {
        PeerAddressBook {
            entries: Arc::new(DashMap::new()),
        }
    }

    /// Record a new or updated address for `peer_id`. Moves addr to front.
    pub fn add(&self, peer_id: &str, addr: SocketAddr) {
        self.add_with_timestamp(peer_id, addr, now_unix());
    }

    fn add_with_timestamp(&self, peer_id: &str, addr: SocketAddr, ts: f64) {
        // Evict LRU if at capacity and peer is new.
        if !self.entries.contains_key(peer_id) && self.entries.len() >= MAX_PEERS {
            self.evict_lru();
        }
        self.entries
            .entry(peer_id.to_owned())
            .and_modify(|e| {
                // Move addr to front, deduplicate, cap.
                e.addrs.retain(|a| *a != addr);
                e.addrs.insert(0, addr);
                e.addrs.truncate(MAX_ADDRS_PER_PEER);
                e.last_seen = ts;
            })
            .or_insert_with(|| PeerAddrs {
                peer_id: peer_id.to_owned(),
                addrs: vec![addr],
                last_seen: ts,
            });
    }

    fn evict_lru(&self) {
        // Find peer with oldest last_seen and remove it.
        if let Some(oldest) = self
            .entries
            .iter()
            .min_by(|a, b| a.last_seen.partial_cmp(&b.last_seen).unwrap_or(std::cmp::Ordering::Equal))
            .map(|e| e.peer_id.clone())
        {
            self.entries.remove(&oldest);
        }
    }

    /// Return all known addresses for `peer_id`, best-first.
    pub fn lookup(&self, peer_id: &str) -> Vec<SocketAddr> {
        self.entries
            .get(peer_id)
            .map(|e| e.addrs.clone())
            .unwrap_or_default()
    }

    /// Return the best (first) address for `peer_id`, if any.
    pub fn best_addr(&self, peer_id: &str) -> Option<SocketAddr> {
        self.entries
            .get(peer_id)
            .and_then(|e| e.addrs.first().copied())
    }

    /// Remove all entries for `peer_id`.
    pub fn remove(&self, peer_id: &str) {
        self.entries.remove(peer_id);
    }

    /// Merge entries from a remote address book. Existing addrs take priority.
    pub fn merge(&self, remote: &[(String, Vec<SocketAddr>)]) {
        for (peer_id, addrs) in remote {
            if addrs.is_empty() {
                continue;
            }
            if !self.entries.contains_key(peer_id) && self.entries.len() >= MAX_PEERS {
                // Don't evict local entries for remote peers.
                continue;
            }
            for addr in addrs {
                self.entries
                    .entry(peer_id.clone())
                    .and_modify(|e| {
                        if !e.addrs.contains(addr) && e.addrs.len() < MAX_ADDRS_PER_PEER {
                            e.addrs.push(*addr);
                        }
                    })
                    .or_insert_with(|| PeerAddrs {
                        peer_id: peer_id.clone(),
                        addrs: vec![*addr],
                        last_seen: 0.0,
                    });
            }
        }
    }

    /// Top `n` most recently seen peers with their best address.
    pub fn top_peers(&self, n: usize) -> Vec<(String, SocketAddr)> {
        let mut v: Vec<_> = self
            .entries
            .iter()
            .filter_map(|e| e.addrs.first().map(|a| (e.peer_id.clone(), *a, e.last_seen)))
            .collect();
        v.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));
        v.into_iter().take(n).map(|(id, addr, _)| (id, addr)).collect()
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Serialize the entire book to JSON for gossip.
    pub fn to_json(&self) -> serde_json::Value {
        let map: std::collections::HashMap<String, Vec<String>> = self
            .entries
            .iter()
            .map(|e| {
                (
                    e.peer_id.clone(),
                    e.addrs.iter().map(|a| a.to_string()).collect(),
                )
            })
            .collect();
        serde_json::json!(map)
    }
}

fn now_unix() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::SocketAddr;

    fn addr(port: u16) -> SocketAddr {
        format!("127.0.0.1:{}", port).parse().unwrap()
    }

    #[test]
    fn add_and_lookup() {
        let book = PeerAddressBook::new();
        book.add("peer-a", addr(8000));
        assert_eq!(book.lookup("peer-a"), vec![addr(8000)]);
    }

    #[test]
    fn best_addr_is_first() {
        let book = PeerAddressBook::new();
        book.add("peer-a", addr(8000));
        book.add("peer-a", addr(8001)); // becomes best
        assert_eq!(book.best_addr("peer-a"), Some(addr(8001)));
    }

    #[test]
    fn remove_peer() {
        let book = PeerAddressBook::new();
        book.add("peer-a", addr(8000));
        book.remove("peer-a");
        assert!(book.lookup("peer-a").is_empty());
    }

    #[test]
    fn max_addrs_per_peer() {
        let book = PeerAddressBook::new();
        for port in 8000..8010u16 {
            book.add("peer-a", addr(port));
        }
        assert!(book.lookup("peer-a").len() <= MAX_ADDRS_PER_PEER);
    }

    #[test]
    fn merge_adds_new_peers() {
        let book = PeerAddressBook::new();
        book.add("peer-a", addr(8000));
        book.merge(&[("peer-b".into(), vec![addr(9000)])]);
        assert!(!book.lookup("peer-b").is_empty());
    }

    #[test]
    fn top_peers_ordered_by_recency() {
        let book = PeerAddressBook::new();
        book.add_with_timestamp("peer-old", addr(8000), 1000.0);
        book.add_with_timestamp("peer-new", addr(8001), 9999.0);
        let top = book.top_peers(2);
        assert_eq!(top[0].0, "peer-new");
    }
}
