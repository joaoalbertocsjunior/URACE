//! Domain concentration guard.
//!
//! Detects when a cluster of peers monopolises routing in a specific
//! skill/work domain.  A "cluster" is defined as the largest group of peers
//! whose registration timestamps fall within a 3 600-second window (1 hour).
//!
//! Integration point: call `register` when a peer claims a domain slot, then
//! `check_domain` before routing work to that domain.

use std::collections::HashMap;
use thiserror::Error;

/// Flag when a cluster holds more than this fraction of a domain's total slots.
pub const DOMAIN_CONCENTRATION_THRESHOLD: f64 = 0.60;

/// A single peer may not register more than this many slots in one domain.
pub const MAX_DOMAIN_SLOTS_PER_PEER: usize = 3;

/// Window used to identify correlated registration timestamps (1 hour).
const CORRELATION_WINDOW_SECS: u64 = 3_600;

// ── types ─────────────────────────────────────────────────────────────────────

/// A peer's claim to a particular skill/work domain.
#[derive(Debug, Clone)]
pub struct DomainSlot {
    pub peer_id: String,
    pub domain: String,
    pub registered_at: u64,
}

/// Result of a domain concentration check.
#[derive(Debug, Clone)]
pub struct DomainConcentrationResult {
    pub flagged: bool,
    pub domain: String,
    /// Peer IDs forming the dominant (possibly suspicious) cluster.
    pub dominant_cluster: Vec<String>,
    /// Fraction of domain slots held by the dominant cluster.
    pub concentration: f64,
    pub total_slots: usize,
    pub flag_reason: String,
}

#[derive(Debug, Error, PartialEq)]
pub enum DomainConcentrationError {
    #[error(
        "peer {peer_id} already holds {limit} slots in domain '{domain}' (MAX_DOMAIN_SLOTS_PER_PEER)"
    )]
    SlotLimitExceeded {
        peer_id: String,
        domain: String,
        limit: usize,
    },
    #[error("domain '{0}' has no registered slots")]
    DomainEmpty(String),
}

// ── guard ─────────────────────────────────────────────────────────────────────

/// Process-local domain concentration guard.
pub struct DomainConcentrationGuard {
    /// domain → list of slots (one entry per registration).
    slots: HashMap<String, Vec<DomainSlot>>,
}

impl DomainConcentrationGuard {
    pub fn new() -> Self {
        DomainConcentrationGuard {
            slots: HashMap::new(),
        }
    }

    /// Register a peer's interest in a domain.
    ///
    /// Returns `Err(SlotLimitExceeded)` if the peer already holds
    /// `MAX_DOMAIN_SLOTS_PER_PEER` slots in that domain.
    pub fn register(
        &mut self,
        peer_id: &str,
        domain: &str,
        now_secs: u64,
    ) -> Result<(), DomainConcentrationError> {
        let entries = self.slots.entry(domain.to_string()).or_default();
        let peer_count = entries.iter().filter(|s| s.peer_id == peer_id).count();
        if peer_count >= MAX_DOMAIN_SLOTS_PER_PEER {
            return Err(DomainConcentrationError::SlotLimitExceeded {
                peer_id: peer_id.to_string(),
                domain: domain.to_string(),
                limit: MAX_DOMAIN_SLOTS_PER_PEER,
            });
        }
        entries.push(DomainSlot {
            peer_id: peer_id.to_string(),
            domain: domain.to_string(),
            registered_at: now_secs,
        });
        Ok(())
    }

    /// Check whether any cluster dominates the given domain.
    ///
    /// "Cluster" = largest set of distinct peers whose registration timestamps
    /// all fall within `CORRELATION_WINDOW_SECS` of each other.
    pub fn check_domain(&self, domain: &str) -> DomainConcentrationResult {
        let entries = match self.slots.get(domain) {
            Some(e) if !e.is_empty() => e,
            _ => {
                return DomainConcentrationResult {
                    flagged: false,
                    domain: domain.to_string(),
                    dominant_cluster: vec![],
                    concentration: 0.0,
                    total_slots: 0,
                    flag_reason: String::new(),
                }
            }
        };

        // Deduplicate: for each peer keep only the earliest registration in
        // this domain so each peer counts once per cluster search.
        let mut earliest: HashMap<&str, u64> = HashMap::new();
        for slot in entries {
            let e = earliest.entry(slot.peer_id.as_str()).or_insert(slot.registered_at);
            if slot.registered_at < *e {
                *e = slot.registered_at;
            }
        }

        let total_slots = entries.len();
        let peers: Vec<(&str, u64)> = earliest.iter().map(|(&id, &ts)| (id, ts)).collect();

        // Find the largest group of distinct peers whose timestamps all lie
        // within CORRELATION_WINDOW_SECS of the group's minimum timestamp.
        let mut best_cluster: Vec<String> = vec![];

        for i in 0..peers.len() {
            let anchor_ts = peers[i].1;
            let group: Vec<String> = peers
                .iter()
                .filter(|&&(_, ts)| {
                    ts >= anchor_ts && ts <= anchor_ts + CORRELATION_WINDOW_SECS
                        || ts < anchor_ts && anchor_ts <= ts + CORRELATION_WINDOW_SECS
                })
                .map(|&(id, _)| id.to_string())
                .collect();

            if group.len() > best_cluster.len() {
                best_cluster = group;
            }
        }

        best_cluster.sort();
        best_cluster.dedup();

        let concentration = best_cluster.len() as f64 / total_slots as f64;

        let (flagged, flag_reason) = if concentration > DOMAIN_CONCENTRATION_THRESHOLD {
            (
                true,
                format!(
                    "cluster of {} peers holds {:.1}% of domain '{}' ({} total slots)",
                    best_cluster.len(),
                    concentration * 100.0,
                    domain,
                    total_slots,
                ),
            )
        } else {
            (false, String::new())
        };

        DomainConcentrationResult {
            flagged,
            domain: domain.to_string(),
            dominant_cluster: best_cluster,
            concentration,
            total_slots,
            flag_reason,
        }
    }

    /// Remove slots whose registration timestamp is older than `ttl_secs`.
    pub fn evict_expired(&mut self, now_secs: u64, ttl_secs: u64) {
        for entries in self.slots.values_mut() {
            entries.retain(|s| {
                now_secs.saturating_sub(s.registered_at) < ttl_secs
            });
        }
        self.slots.retain(|_, v| !v.is_empty());
    }
}

impl Default for DomainConcentrationGuard {
    fn default() -> Self {
        Self::new()
    }
}

// ── tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── happy path: diverse domain ───────────────────────────────────────────

    #[test]
    fn diverse_domain_not_flagged() {
        let mut guard = DomainConcentrationGuard::new();
        let base = 1_000_000u64;
        // 10 peers all registering hours apart — no correlation cluster > 60 %.
        for i in 0..10u64 {
            guard
                .register(&format!("peer-{}", i), "nlp", base + i * 7_200)
                .unwrap();
        }
        let result = guard.check_domain("nlp");
        assert!(!result.flagged, "diverse peers should not be flagged: {:?}", result.flag_reason);
    }

    // ── correlated cluster exceeds threshold ─────────────────────────────────

    #[test]
    fn correlated_cluster_flagged() {
        let mut guard = DomainConcentrationGuard::new();
        let base = 2_000_000u64;
        // 7 peers register within 10 minutes of each other (highly correlated).
        for i in 0..7u64 {
            guard
                .register(&format!("cartel-{}", i), "code-review", base + i * 60)
                .unwrap();
        }
        // 2 more peers register 2 hours later (outside window).
        guard.register("honest-1", "code-review", base + 7_300).unwrap();
        guard.register("honest-2", "code-review", base + 7_400).unwrap();
        // 7/9 ≈ 77.8 % > 60 %
        let result = guard.check_domain("code-review");
        assert!(result.flagged, "cartel cluster must be flagged");
        assert!(result.concentration > DOMAIN_CONCENTRATION_THRESHOLD);
        assert_eq!(result.dominant_cluster.len(), 7);
    }

    // ── per-peer slot limit ───────────────────────────────────────────────────

    #[test]
    fn slot_limit_per_peer_enforced() {
        let mut guard = DomainConcentrationGuard::new();
        let base = 3_000_000u64;
        guard.register("peer-x", "math", base).unwrap();
        guard.register("peer-x", "math", base + 1).unwrap();
        guard.register("peer-x", "math", base + 2).unwrap();
        // 4th slot must fail.
        let err = guard.register("peer-x", "math", base + 3).unwrap_err();
        assert!(matches!(err, DomainConcentrationError::SlotLimitExceeded { .. }));
    }

    // ── empty domain ─────────────────────────────────────────────────────────

    #[test]
    fn check_empty_domain_returns_unflagged() {
        let guard = DomainConcentrationGuard::new();
        let result = guard.check_domain("unknown-domain");
        assert!(!result.flagged);
        assert_eq!(result.total_slots, 0);
        assert!(result.dominant_cluster.is_empty());
    }

    // ── eviction ─────────────────────────────────────────────────────────────

    #[test]
    fn evict_expired_removes_old_slots() {
        let mut guard = DomainConcentrationGuard::new();
        let base = 5_000_000u64;
        guard.register("old-peer", "audio", base).unwrap();
        guard.register("new-peer", "audio", base + 90_000).unwrap();
        // Evict anything older than 86 400 s (1 day) relative to base + 100 000.
        guard.evict_expired(base + 100_000, 86_400);
        // old-peer registered at base, age = 100 000 > 86 400 — evicted.
        // new-peer registered at base + 90 000, age = 10 000 < 86 400 — kept.
        let result = guard.check_domain("audio");
        assert_eq!(result.total_slots, 1);
        assert_eq!(result.dominant_cluster, vec!["new-peer".to_string()]);
    }

    // ── concentration math ────────────────────────────────────────────────────

    #[test]
    fn concentration_exactly_at_threshold_not_flagged() {
        // threshold = 0.60; 3 out of 5 = 0.60 — strictly > 0.60 is required.
        let mut guard = DomainConcentrationGuard::new();
        let base = 6_000_000u64;
        // 3 correlated peers
        for i in 0..3u64 {
            guard.register(&format!("cluster-{}", i), "vision", base + i * 10).unwrap();
        }
        // 2 uncorrelated peers (> 1 h later each)
        guard.register("solo-1", "vision", base + 10_000).unwrap();
        guard.register("solo-2", "vision", base + 20_000).unwrap();
        // cluster=3, total=5, concentration=0.60 — NOT strictly > 0.60
        let result = guard.check_domain("vision");
        assert!(!result.flagged, "exactly at threshold must not be flagged");
    }

    #[test]
    fn constants_are_correct() {
        assert!((DOMAIN_CONCENTRATION_THRESHOLD - 0.60).abs() < 1e-9);
        assert_eq!(MAX_DOMAIN_SLOTS_PER_PEER, 3);
    }
}
