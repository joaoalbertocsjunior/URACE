//! Multi-dimensional peer reputation categories.
//!
//! Ported from `reputation_categories.py`. Five categories, each in [0,1]:
//! quality, delivery, service, validation, longevity. Consensus weight profiles
//! combine them for different governance decisions.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

/// The five earned reputation categories.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ReputationCategory {
    Quality,
    Delivery,
    Service,
    Validation,
    Longevity,
}

impl ReputationCategory {
    pub const ALL: [ReputationCategory; 5] = [
        ReputationCategory::Quality,
        ReputationCategory::Delivery,
        ReputationCategory::Service,
        ReputationCategory::Validation,
        ReputationCategory::Longevity,
    ];
}

/// Per-category scores for a peer, all in [0.0, 1.0].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerReputation {
    pub peer_id: String,
    pub quality: f64,
    pub delivery: f64,
    pub service: f64,
    pub validation: f64,
    pub longevity: f64,
}

impl PeerReputation {
    pub fn new(peer_id: impl Into<String>) -> Self {
        PeerReputation {
            peer_id: peer_id.into(),
            quality: 0.05, // cold-start floor
            delivery: 0.05,
            service: 0.0,
            validation: 0.10, // new peers get floor, not zero
            longevity: 0.0,
        }
    }

    /// Return the score for a given category.
    pub fn score(&self, cat: ReputationCategory) -> f64 {
        match cat {
            ReputationCategory::Quality => self.quality,
            ReputationCategory::Delivery => self.delivery,
            ReputationCategory::Service => self.service,
            ReputationCategory::Validation => self.validation,
            ReputationCategory::Longevity => self.longevity,
        }
    }

    pub fn set_score(&mut self, cat: ReputationCategory, value: f64) {
        let v = value.clamp(0.0, 1.0);
        match cat {
            ReputationCategory::Quality => self.quality = v,
            ReputationCategory::Delivery => self.delivery = v,
            ReputationCategory::Service => self.service = v,
            ReputationCategory::Validation => self.validation = v,
            ReputationCategory::Longevity => self.longevity = v,
        }
    }
}

/// Named consensus weight profile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsensusProfile {
    pub name: String,
    pub quality: f64,
    pub delivery: f64,
    pub service: f64,
    pub validation: f64,
    pub longevity: f64,
}

impl ConsensusProfile {
    /// Pre-defined profiles from `reputation_categories.py`.
    pub fn work_quality_gate() -> Self {
        ConsensusProfile {
            name: "work_quality_gate".into(),
            quality: 0.50,
            delivery: 0.25,
            service: 0.05,
            validation: 0.15,
            longevity: 0.05,
        }
    }

    pub fn network_governance() -> Self {
        ConsensusProfile {
            name: "network_governance".into(),
            quality: 0.15,
            delivery: 0.10,
            service: 0.40,
            validation: 0.05,
            longevity: 0.30,
        }
    }

    pub fn challenge_weight() -> Self {
        ConsensusProfile {
            name: "challenge_weight".into(),
            quality: 0.25,
            delivery: 0.05,
            service: 0.05,
            validation: 0.50,
            longevity: 0.15,
        }
    }

    pub fn cartel_resistant() -> Self {
        ConsensusProfile {
            name: "cartel_resistant".into(),
            quality: 0.20,
            delivery: 0.05,
            service: 0.25,
            validation: 0.15,
            longevity: 0.35,
        }
    }

    pub fn arbitration() -> Self {
        ConsensusProfile {
            name: "arbitration".into(),
            quality: 0.25,
            delivery: 0.15,
            service: 0.15,
            validation: 0.25,
            longevity: 0.20,
        }
    }

    /// Compute consensus weight for a peer under this profile.
    pub fn weight(&self, rep: &PeerReputation) -> f64 {
        self.quality * rep.quality
            + self.delivery * rep.delivery
            + self.service * rep.service
            + self.validation * rep.validation
            + self.longevity * rep.longevity
    }

    pub fn weight_for_category(&self, cat: ReputationCategory) -> f64 {
        match cat {
            ReputationCategory::Quality => self.quality,
            ReputationCategory::Delivery => self.delivery,
            ReputationCategory::Service => self.service,
            ReputationCategory::Validation => self.validation,
            ReputationCategory::Longevity => self.longevity,
        }
    }
}

/// Convenience struct exposing all five profiles.
pub struct ReputationCategories;

impl ReputationCategories {
    pub fn profile(name: &str) -> Option<ConsensusProfile> {
        match name {
            "work_quality_gate" => Some(ConsensusProfile::work_quality_gate()),
            "network_governance" => Some(ConsensusProfile::network_governance()),
            "challenge_weight" => Some(ConsensusProfile::challenge_weight()),
            "cartel_resistant" => Some(ConsensusProfile::cartel_resistant()),
            "arbitration" => Some(ConsensusProfile::arbitration()),
            _ => None,
        }
    }

    /// Sybil admission gate: check minimum thresholds per category.
    pub fn sybil_gate(rep: &PeerReputation) -> (bool, Vec<ReputationCategory>) {
        const THRESHOLDS: [(ReputationCategory, f64); 5] = [
            (ReputationCategory::Quality, 0.10),
            (ReputationCategory::Delivery, 0.10),
            (ReputationCategory::Service, 0.05),
            (ReputationCategory::Validation, 0.05),
            (ReputationCategory::Longevity, 0.05),
        ];
        let failing: Vec<_> = THRESHOLDS
            .iter()
            .filter(|(cat, thresh)| rep.score(*cat) < *thresh)
            .map(|(cat, _)| *cat)
            .collect();
        (failing.is_empty(), failing)
    }
}

/// DashMap-backed store of peer reputation records.
#[derive(Clone)]
pub struct ReputationStore {
    peers: Arc<DashMap<String, PeerReputation>>,
}

impl Default for ReputationStore {
    fn default() -> Self {
        Self::new()
    }
}

impl ReputationStore {
    pub fn new() -> Self {
        ReputationStore {
            peers: Arc::new(DashMap::new()),
        }
    }

    /// Return reputation for a peer (creates cold-start record if absent).
    pub fn get(&self, peer_id: &str) -> PeerReputation {
        self.peers
            .get(peer_id)
            .map(|e| e.clone())
            .unwrap_or_else(|| PeerReputation::new(peer_id))
    }

    /// Update a single category score for a peer.
    pub fn update_category(&self, peer_id: &str, cat: ReputationCategory, score: f64) {
        let mut entry = self
            .peers
            .entry(peer_id.to_owned())
            .or_insert_with(|| PeerReputation::new(peer_id));
        entry.set_score(cat, score);
    }

    /// Replace a peer's full reputation record.
    pub fn upsert(&self, rep: PeerReputation) {
        self.peers.insert(rep.peer_id.clone(), rep);
    }

    /// Consensus weight for a peer under a named profile.
    pub fn consensus_weight(&self, peer_id: &str, profile_name: &str) -> f64 {
        let profile = ReputationCategories::profile(profile_name)
            .unwrap_or_else(ConsensusProfile::work_quality_gate);
        let rep = self.get(peer_id);
        profile.weight(&rep)
    }

    /// All peers, sorted by consensus weight (default: work_quality_gate) descending.
    pub fn ranked(&self, profile_name: &str) -> Vec<(String, f64)> {
        let profile = ReputationCategories::profile(profile_name)
            .unwrap_or_else(ConsensusProfile::work_quality_gate);
        let mut v: Vec<(String, f64)> = self
            .peers
            .iter()
            .map(|e| (e.peer_id.clone(), profile.weight(&e)))
            .collect();
        v.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        v
    }

    pub fn len(&self) -> usize {
        self.peers.len()
    }

    pub fn is_empty(&self) -> bool {
        self.peers.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cold_start_floors() {
        let rep = PeerReputation::new("peer-x");
        assert_eq!(rep.quality, 0.05);
        assert_eq!(rep.validation, 0.10);
        assert_eq!(rep.service, 0.0);
    }

    #[test]
    fn sybil_gate_new_peer() {
        let rep = PeerReputation::new("peer-x");
        let (passes, failing) = ReputationCategories::sybil_gate(&rep);
        // quality=0.05 < 0.10, delivery=0.05 < 0.10 → fails
        assert!(!passes);
        assert!(failing.contains(&ReputationCategory::Quality));
        assert!(failing.contains(&ReputationCategory::Delivery));
    }

    #[test]
    fn update_and_query() {
        let store = ReputationStore::new();
        store.update_category("peer-a", ReputationCategory::Quality, 0.8);
        store.update_category("peer-a", ReputationCategory::Delivery, 0.7);
        let rep = store.get("peer-a");
        assert_eq!(rep.quality, 0.8);
        let w = store.consensus_weight("peer-a", "work_quality_gate");
        assert!(w > 0.0);
    }

    #[test]
    fn ranked_order() {
        let store = ReputationStore::new();
        let mut rep_a = PeerReputation::new("peer-a");
        rep_a.quality = 0.9;
        rep_a.delivery = 0.9;
        store.upsert(rep_a);
        let mut rep_b = PeerReputation::new("peer-b");
        rep_b.quality = 0.1;
        store.upsert(rep_b);
        let ranked = store.ranked("work_quality_gate");
        assert_eq!(ranked[0].0, "peer-a");
    }

    #[test]
    fn consensus_profiles_sum_to_one() {
        let profiles = [
            ConsensusProfile::work_quality_gate(),
            ConsensusProfile::network_governance(),
            ConsensusProfile::challenge_weight(),
            ConsensusProfile::cartel_resistant(),
            ConsensusProfile::arbitration(),
        ];
        for p in &profiles {
            let sum = p.quality + p.delivery + p.service + p.validation + p.longevity;
            assert!((sum - 1.0).abs() < 1e-6, "{}: sum={}", p.name, sum);
        }
    }
}
