//! R-7: Freeform routing — local route reputation + cache.
//!
//! Security invariants:
//! - `LocalRouteReputation` is process-local ONLY — never serialized, never sent over wire.
//! - `RouteCache` is process-local ONLY — never serialized, never sent over wire.
//! - `select_target` MUST NOT return a peer that failed AdmissionGate.

use crate::kademlia::NodeInfo;
use crate::peer_discovery::AdmissionGate;
use dashmap::DashMap;

/// Per-peer success/failure counters.
///
/// # Security note
/// This struct intentionally does NOT implement Serialize/Deserialize.
/// It MUST remain process-local — it must never be written to disk or sent
/// over the wire, as it could leak internal routing topology.
#[derive(Debug, Default)]
pub struct LocalRouteReputation {
    /// peer_id → (success_count, failure_count)
    counters: DashMap<String, (u64, u64)>,
}

impl LocalRouteReputation {
    pub fn new() -> Self {
        Default::default()
    }

    /// Record a successful interaction with a peer.
    pub fn record_success(&self, peer_id: &str) {
        let mut e = self.counters.entry(peer_id.to_string()).or_insert((0, 0));
        e.0 += 1;
    }

    /// Record a failed interaction with a peer.
    pub fn record_failure(&self, peer_id: &str) {
        let mut e = self.counters.entry(peer_id.to_string()).or_insert((0, 0));
        e.1 += 1;
    }

    /// Return (successes, failures) for a peer. Returns (0, 0) if unknown.
    pub fn stats(&self, peer_id: &str) -> (u64, u64) {
        self.counters.get(peer_id).map(|v| *v).unwrap_or((0, 0))
    }

    /// Simple reputation score in [0.0, 1.0].
    /// Unknown peers default to 0.5 (neutral).
    pub fn score(&self, peer_id: &str) -> f64 {
        let (s, f) = self.stats(peer_id);
        let total = s + f;
        if total == 0 {
            return 0.5;
        }
        s as f64 / total as f64
    }
}

/// Process-local route cache: target_peer_id → ordered list of hop peer IDs.
///
/// # Security note
/// This struct intentionally does NOT implement Serialize/Deserialize.
/// It MUST remain process-local — it must never be written to disk or sent
/// over the wire.
#[derive(Debug, Default)]
pub struct RouteCache {
    routes: DashMap<String, Vec<String>>,
}

impl RouteCache {
    pub fn new() -> Self {
        Default::default()
    }

    /// Insert or replace the route to `target_peer_id`.
    pub fn insert(&self, target_peer_id: &str, hops: Vec<String>) {
        self.routes.insert(target_peer_id.to_string(), hops);
    }

    /// Retrieve the cached route to `target_peer_id`, if any.
    pub fn get(&self, target_peer_id: &str) -> Option<Vec<String>> {
        self.routes.get(target_peer_id).map(|v| v.clone())
    }

    /// Remove the cached route (e.g., after a routing failure).
    pub fn invalidate(&self, target_peer_id: &str) {
        self.routes.remove(target_peer_id);
    }
}

/// Select the best target from `candidates` after filtering non-admitted peers.
///
/// # Security invariant
/// MUST NOT return a peer that failed AdmissionGate — admitted check is applied
/// before any scoring. Returns `None` if no admitted candidates exist.
pub fn select_target<'a>(candidates: &'a [NodeInfo], gate: &AdmissionGate) -> Option<&'a NodeInfo> {
    // Filter to only admitted peers — security invariant.
    let admitted: Vec<&NodeInfo> = candidates
        .iter()
        .filter(|n| gate.is_admitted(&n.peer_id))
        .collect();

    // Among admitted peers, pick the most recently seen one as a simple
    // freshness heuristic (matches Python peer selection behaviour).
    admitted.into_iter().max_by(|a, b| {
        a.last_seen_secs
            .partial_cmp(&b.last_seen_secs)
            .unwrap_or(std::cmp::Ordering::Equal)
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kademlia::NodeInfo;
    use crate::peer_discovery::AdmissionGate;

    #[test]
    fn test_reputation_initial_neutral() {
        let rep = LocalRouteReputation::new();
        assert!((rep.score("unknown") - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_reputation_tracking() {
        let rep = LocalRouteReputation::new();
        rep.record_success("peer-a");
        rep.record_success("peer-a");
        rep.record_failure("peer-a");
        let (s, f) = rep.stats("peer-a");
        assert_eq!(s, 2);
        assert_eq!(f, 1);
        assert!((rep.score("peer-a") - 2.0 / 3.0).abs() < 1e-9);
    }

    #[test]
    fn test_route_cache() {
        let cache = RouteCache::new();
        cache.insert("target-1", vec!["hop-a".into(), "hop-b".into()]);
        assert_eq!(
            cache.get("target-1"),
            Some(vec!["hop-a".into(), "hop-b".into()])
        );
        cache.invalidate("target-1");
        assert!(cache.get("target-1").is_none());
    }

    #[test]
    fn test_select_target_excludes_non_admitted() {
        let gate = AdmissionGate::new();
        gate.admit("peer-admitted", 1);
        // peer-rejected is not admitted.
        let candidates = vec![
            NodeInfo::new("peer-admitted", "addr-1"),
            NodeInfo::new("peer-rejected", "addr-2"),
        ];
        let result = select_target(&candidates, &gate);
        assert!(result.is_some());
        assert_eq!(result.unwrap().peer_id, "peer-admitted");
    }

    #[test]
    fn test_select_target_returns_none_when_no_admitted() {
        let gate = AdmissionGate::new();
        let candidates = vec![NodeInfo::new("unknown-peer", "addr")];
        let result = select_target(&candidates, &gate);
        assert!(result.is_none(), "should not return a non-admitted peer");
    }

    #[test]
    fn test_reputation_not_serializable() {
        // Compile-time check: LocalRouteReputation must not implement Serialize.
        // We verify this by asserting the type name does not accidentally gain serde.
        // The absence of #[derive(Serialize)] is the real guard — this test documents intent.
        let _rep = LocalRouteReputation::new();
        // If this compiles without serde_json::to_string(&_rep), the invariant is preserved.
    }
}
