//! R-6: Peer discovery and admission gate — port of `peer_discovery.py`.
//!
//! Security invariants:
//! - `relay_only=true` MUST NOT expose real IP (enforced via relay flag in DiscoverySession).
//! - Peers with protocol_gen < MIN_SUPPORTED are quarantined and rejected.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use sha1::{Digest, Sha1};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

/// Minimum supported protocol generation. Peers advertising lower are rejected.
pub const MIN_SUPPORTED_PROTOCOL_GEN: u32 = 1;

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PeerAdmissionState {
    Quarantined,
    Admitted,
    Rejected,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerAdmissionRecord {
    pub peer_id: String,
    pub state: PeerAdmissionState,
    /// Protocol generation advertised by the peer, None until verified.
    pub protocol_gen: Option<u32>,
    pub entered_at: f64,
    pub reason: String,
}

impl PeerAdmissionRecord {
    fn new(
        peer_id: impl Into<String>,
        state: PeerAdmissionState,
        reason: impl Into<String>,
    ) -> Self {
        PeerAdmissionRecord {
            peer_id: peer_id.into(),
            state,
            protocol_gen: None,
            entered_at: now_secs(),
            reason: reason.into(),
        }
    }
}

/// Thread-safe admission gate for incoming peers.
///
/// A peer is quarantined on first contact; it transitions to `Admitted` only
/// after a protocol_gen >= MIN_SUPPORTED_PROTOCOL_GEN is verified.
pub struct AdmissionGate {
    records: DashMap<String, PeerAdmissionRecord>,
}

impl AdmissionGate {
    pub fn new() -> Self {
        AdmissionGate {
            records: DashMap::new(),
        }
    }

    /// Attempt to admit a peer with the given protocol generation.
    ///
    /// Returns the resulting admission state.
    pub fn admit(&self, peer_id: &str, protocol_gen: u32) -> PeerAdmissionState {
        if protocol_gen < MIN_SUPPORTED_PROTOCOL_GEN {
            let mut rec = PeerAdmissionRecord::new(
                peer_id,
                PeerAdmissionState::Rejected,
                format!(
                    "protocol_gen {} < MIN_SUPPORTED {}",
                    protocol_gen, MIN_SUPPORTED_PROTOCOL_GEN
                ),
            );
            rec.protocol_gen = Some(protocol_gen);
            self.records.insert(peer_id.to_string(), rec);
            return PeerAdmissionState::Rejected;
        }

        let mut rec = self.records.entry(peer_id.to_string()).or_insert_with(|| {
            PeerAdmissionRecord::new(peer_id, PeerAdmissionState::Quarantined, "initial")
        });
        rec.state = PeerAdmissionState::Admitted;
        rec.protocol_gen = Some(protocol_gen);
        rec.reason = "protocol_gen verified".into();
        PeerAdmissionState::Admitted
    }

    /// Returns true iff the peer is currently in `Admitted` state.
    pub fn is_admitted(&self, peer_id: &str) -> bool {
        self.records
            .get(peer_id)
            .map(|r| r.state == PeerAdmissionState::Admitted)
            .unwrap_or(false)
    }

    /// Quarantine a peer (e.g., after misbehaviour).
    pub fn quarantine(&self, peer_id: &str, reason: &str) {
        let mut rec = self.records.entry(peer_id.to_string()).or_insert_with(|| {
            PeerAdmissionRecord::new(peer_id, PeerAdmissionState::Quarantined, reason)
        });
        rec.state = PeerAdmissionState::Quarantined;
        rec.reason = reason.to_string();
    }

    /// Retrieve the full record for a peer, if known.
    pub fn get(&self, peer_id: &str) -> Option<PeerAdmissionRecord> {
        self.records.get(peer_id).map(|r| r.clone())
    }
}

impl Default for AdmissionGate {
    fn default() -> Self {
        Self::new()
    }
}

fn sha1_bytes(data: &[u8]) -> [u8; 20] {
    let mut hasher = Sha1::new();
    hasher.update(data);
    hasher.finalize().into()
}

/// A BEP 5 compatible DHT discovery session.
///
/// Security note: when `relay_only = true` the session MUST NOT expose the
/// node's real IP address. The DHT node_id is still derived from peer_id so
/// that routing is consistent, but all outbound announces must go through a
/// relay peer.
pub struct DiscoverySession {
    /// SHA-1 of peer_id — used as BEP 5 DHT node ID.
    pub dht_node_id: [u8; 20],
    /// SHA-1("urace-exchange-v1") — infohash for peer lookup.
    pub topic_infohash: [u8; 20],
    pub admission: Arc<AdmissionGate>,
    /// When true, real IP MUST NOT be announced; use relay peer only.
    pub relay_only: bool,
}

impl DiscoverySession {
    pub fn new(peer_id: &str, relay_only: bool) -> Self {
        let dht_node_id = sha1_bytes(peer_id.as_bytes());
        let topic_infohash = sha1_bytes(b"urace-exchange-v1");
        DiscoverySession {
            dht_node_id,
            topic_infohash,
            admission: Arc::new(AdmissionGate::new()),
            relay_only,
        }
    }

    /// Whether real-IP DHT announces are permitted for this session.
    ///
    /// Returns false (and must remain false) when relay_only is set.
    pub fn may_announce_real_ip(&self) -> bool {
        !self.relay_only
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_admit_valid_peer() {
        let gate = AdmissionGate::new();
        assert!(!gate.is_admitted("peer-a"));
        let state = gate.admit("peer-a", 1);
        assert_eq!(state, PeerAdmissionState::Admitted);
        assert!(gate.is_admitted("peer-a"));
    }

    #[test]
    fn test_reject_old_protocol() {
        let gate = AdmissionGate::new();
        let state = gate.admit("peer-b", 0);
        assert_eq!(state, PeerAdmissionState::Rejected);
        assert!(!gate.is_admitted("peer-b"));
    }

    #[test]
    fn test_relay_only_no_real_ip() {
        let session = DiscoverySession::new("peer-c", true);
        assert!(
            !session.may_announce_real_ip(),
            "relay_only session must never expose real IP"
        );
    }

    #[test]
    fn test_non_relay_may_announce() {
        let session = DiscoverySession::new("peer-d", false);
        assert!(session.may_announce_real_ip());
    }

    #[test]
    fn test_dht_node_id_is_sha1_of_peer_id() {
        let session = DiscoverySession::new("peer-x", false);
        let expected = sha1_bytes(b"peer-x");
        assert_eq!(session.dht_node_id, expected);
    }

    #[test]
    fn test_topic_infohash() {
        let session = DiscoverySession::new("any", false);
        let expected = sha1_bytes(b"urace-exchange-v1");
        assert_eq!(session.topic_infohash, expected);
    }

    #[test]
    fn test_quarantine() {
        let gate = AdmissionGate::new();
        gate.admit("peer-e", 1);
        assert!(gate.is_admitted("peer-e"));
        gate.quarantine("peer-e", "misbehaviour");
        assert!(!gate.is_admitted("peer-e"));
    }
}
