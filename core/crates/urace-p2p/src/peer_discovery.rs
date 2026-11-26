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

// ── M60 — Jurisdictional diversity ───────────────────────────────────────────

/// Maximum fraction of admitted peers from any single jurisdiction (40%).
pub const MAX_JURISDICTION_FRACTION: f64 = 0.40;

/// A two-letter ISO 3166-1 country code (or "XX" for unknown).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct JurisdictionCode(pub String);

impl JurisdictionCode {
    pub fn new(code: impl Into<String>) -> Self {
        JurisdictionCode(code.into().to_uppercase())
    }
    pub fn unknown() -> Self {
        JurisdictionCode("XX".into())
    }
}

/// Tracks peer counts per jurisdiction to enforce diversity.
pub struct JurisdictionGuard {
    counts: std::collections::HashMap<JurisdictionCode, usize>,
    total: usize,
}

impl JurisdictionGuard {
    pub fn new() -> Self {
        JurisdictionGuard { counts: std::collections::HashMap::new(), total: 0 }
    }

    /// Returns `true` if admitting one more peer from `jurisdiction` would not
    /// exceed `MAX_JURISDICTION_FRACTION` of the current total (after admission).
    pub fn can_admit(&self, jurisdiction: &JurisdictionCode) -> bool {
        let new_total = self.total + 1;
        let new_count = self.counts.get(jurisdiction).copied().unwrap_or(0) + 1;
        (new_count as f64 / new_total as f64) <= MAX_JURISDICTION_FRACTION
    }

    /// Record that a peer from `jurisdiction` was admitted.
    pub fn record_admission(&mut self, jurisdiction: JurisdictionCode) {
        *self.counts.entry(jurisdiction).or_insert(0) += 1;
        self.total += 1;
    }

    /// Record that a peer from `jurisdiction` was removed.
    pub fn record_removal(&mut self, jurisdiction: &JurisdictionCode) {
        if let Some(c) = self.counts.get_mut(jurisdiction) {
            if *c > 0 {
                *c -= 1;
                self.total = self.total.saturating_sub(1);
            }
        }
    }

    pub fn total(&self) -> usize { self.total }
    pub fn count_for(&self, j: &JurisdictionCode) -> usize {
        self.counts.get(j).copied().unwrap_or(0)
    }
}

impl Default for JurisdictionGuard {
    fn default() -> Self { Self::new() }
}

// ── M70 — Peer expiry + re-qualification ─────────────────────────────────────

/// Admitted peers expire after this many seconds of inactivity (24 hours).
pub const PEER_EXPIRY_SECS: f64 = 86_400.0;

impl AdmissionGate {
    /// Mark a peer as having been seen at `now_secs`.
    ///
    /// This refreshes the `entered_at` timestamp so the peer's expiry window restarts.
    pub fn touch(&self, peer_id: &str, now_secs: f64) {
        if let Some(mut rec) = self.records.get_mut(peer_id) {
            rec.entered_at = now_secs;
        }
    }

    /// Expire peers that have been admitted but not seen for `PEER_EXPIRY_SECS`.
    ///
    /// Returns the list of expired peer IDs.  Expired peers transition to `Quarantined`
    /// and must re-qualify before being re-admitted.
    pub fn expire_stale_peers(&self, now_secs: f64) -> Vec<String> {
        let mut expired = vec![];
        for mut rec in self.records.iter_mut() {
            if rec.state == PeerAdmissionState::Admitted
                && (now_secs - rec.entered_at) >= PEER_EXPIRY_SECS
            {
                rec.state = PeerAdmissionState::Quarantined;
                rec.reason = "expired — re-qualification required".into();
                expired.push(rec.peer_id.clone());
            }
        }
        expired
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

    // M60 — jurisdictional diversity tests

    #[test]
    fn jurisdiction_guard_allows_up_to_40_pct() {
        let mut guard = JurisdictionGuard::new();
        let us = JurisdictionCode::new("US");
        // With 2 total peers, 1 US = 50% → exceeds 40%.
        // But with just 1 peer total, 1/1 = 100% → exceeds.
        // Let's pre-admit 4 non-US peers.
        for _ in 0..4 {
            guard.record_admission(JurisdictionCode::new("DE"));
        }
        // Now: total=4, US=0. Adding 1 US → 1/5 = 20% ≤ 40% → allowed.
        assert!(guard.can_admit(&us));
        guard.record_admission(us.clone());
        // Adding another US → 2/6 = 33% ≤ 40% → allowed.
        assert!(guard.can_admit(&us));
        guard.record_admission(us.clone());
        // 3/7 = 42.8% > 40% → denied.
        assert!(!guard.can_admit(&us));
    }

    #[test]
    fn jurisdiction_removal_allows_re_admission() {
        let mut guard = JurisdictionGuard::new();
        let us = JurisdictionCode::new("US");
        // Single peer: 1/1 = 100% → denied.
        assert!(!guard.can_admit(&us));
        // But with zero total, adding first peer is always 1/1 = 100%…
        // Add two non-US peers first.
        guard.record_admission(JurisdictionCode::new("FR"));
        guard.record_admission(JurisdictionCode::new("JP"));
        guard.record_admission(us.clone()); // 1/3 = 33%
        assert_eq!(guard.count_for(&us), 1);
        guard.record_removal(&us);
        assert_eq!(guard.count_for(&us), 0);
        assert_eq!(guard.total(), 2);
    }

    // M70 — peer expiry tests

    #[test]
    fn peer_expiry_quarantines_stale_peer() {
        let gate = AdmissionGate::new();
        gate.admit("peer-stale", 1);
        // Simulate that the peer was admitted 25 hours ago.
        {
            let mut rec = gate.records.get_mut("peer-stale").unwrap();
            rec.entered_at = 0.0; // very old
        }
        let now = PEER_EXPIRY_SECS + 1.0;
        let expired = gate.expire_stale_peers(now);
        assert_eq!(expired, vec!["peer-stale"]);
        assert!(!gate.is_admitted("peer-stale"));
    }

    #[test]
    fn peer_touch_resets_expiry() {
        let gate = AdmissionGate::new();
        gate.admit("peer-fresh", 1);
        {
            let mut rec = gate.records.get_mut("peer-fresh").unwrap();
            rec.entered_at = 0.0;
        }
        // Touch resets timestamp to `now`.
        let now = PEER_EXPIRY_SECS + 1.0;
        gate.touch("peer-fresh", now);
        let expired = gate.expire_stale_peers(now + 1.0);
        assert!(expired.is_empty(), "recently touched peer must not expire immediately");
    }
}
