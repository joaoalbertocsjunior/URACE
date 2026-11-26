//! M66 — Network health threshold gate.
//!
//! Evaluates five health conditions and returns either `UnrestrictedMode`
//! (all pass) or `RestrictedMode` (one or more failing conditions listed).

use serde::{Deserialize, Serialize};

/// Minimum number of active peers for unrestricted operation.
pub const MIN_ACTIVE_PEERS: usize = 100;
/// Minimum number of distinct /8 IP blocks in the peer set.
pub const MIN_DISTINCT_8_BLOCKS: usize = 5;
/// Minimum 7-day task completion rate (0–1).
pub const MIN_COMPLETION_RATE_7D: f64 = 0.60;
/// Maximum fraction of peers that may belong to the largest cluster.
pub const MAX_CLUSTER_FRACTION: f64 = 0.40;
/// Maximum 7-day peer-count decline rate before restricted mode triggers.
pub const MAX_PEER_DECLINE_7D: f64 = 0.20;

/// A single failing health condition, with the actual and required values.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum HealthCondition {
    PeerCount { actual: usize, required: usize },
    SubnetDiversity { actual: usize, required: usize },
    CompletionRate { actual: f64, required: f64 },
    ClusterConcentration { fraction: f64, max: f64 },
    PeerDecline { decline_rate: f64, max: f64 },
}

/// Overall network health mode.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum NetworkHealthStatus {
    UnrestrictedMode,
    RestrictedMode { failing: Vec<HealthCondition> },
}

/// A snapshot of network health metrics at a point in time.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkHealthSnapshot {
    /// Current active peer count.
    pub active_peers: usize,
    /// Number of distinct /8 IP blocks in the peer set.
    pub distinct_8_blocks: usize,
    /// Rolling 7-day task completion rate (0.0–1.0).
    pub completion_rate_7d: f64,
    /// Fraction of peers in the single largest cluster (0.0–1.0).
    pub max_cluster_fraction: f64,
    /// Net peer count change over 7 days (negative = decline).
    /// E.g. -0.15 means 15% fewer peers than 7 days ago.
    pub peer_count_change_7d: f64,
    /// Unix timestamp (seconds) when this snapshot was taken.
    pub timestamp_secs: u64,
}

impl NetworkHealthSnapshot {
    /// Assess all five health conditions and return the aggregate status.
    pub fn assess(&self) -> NetworkHealthStatus {
        let mut failing = Vec::new();

        if self.active_peers < MIN_ACTIVE_PEERS {
            failing.push(HealthCondition::PeerCount {
                actual: self.active_peers,
                required: MIN_ACTIVE_PEERS,
            });
        }

        if self.distinct_8_blocks < MIN_DISTINCT_8_BLOCKS {
            failing.push(HealthCondition::SubnetDiversity {
                actual: self.distinct_8_blocks,
                required: MIN_DISTINCT_8_BLOCKS,
            });
        }

        if self.completion_rate_7d < MIN_COMPLETION_RATE_7D {
            failing.push(HealthCondition::CompletionRate {
                actual: self.completion_rate_7d,
                required: MIN_COMPLETION_RATE_7D,
            });
        }

        if self.max_cluster_fraction > MAX_CLUSTER_FRACTION {
            failing.push(HealthCondition::ClusterConcentration {
                fraction: self.max_cluster_fraction,
                max: MAX_CLUSTER_FRACTION,
            });
        }

        // peer_count_change_7d is negative for decline; e.g. -0.25 = 25% decline.
        let decline_rate = -self.peer_count_change_7d.min(0.0);
        if decline_rate > MAX_PEER_DECLINE_7D {
            failing.push(HealthCondition::PeerDecline {
                decline_rate,
                max: MAX_PEER_DECLINE_7D,
            });
        }

        if failing.is_empty() {
            NetworkHealthStatus::UnrestrictedMode
        } else {
            NetworkHealthStatus::RestrictedMode { failing }
        }
    }

    /// Convenience: returns `true` iff all conditions pass.
    pub fn is_unrestricted(&self) -> bool {
        self.assess() == NetworkHealthStatus::UnrestrictedMode
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn healthy() -> NetworkHealthSnapshot {
        NetworkHealthSnapshot {
            active_peers: 150,
            distinct_8_blocks: 8,
            completion_rate_7d: 0.75,
            max_cluster_fraction: 0.20,
            peer_count_change_7d: 0.05,
            timestamp_secs: 1_700_000_000,
        }
    }

    #[test]
    fn healthy_snapshot_unrestricted() {
        let snap = healthy();
        assert!(snap.is_unrestricted(), "fully healthy snapshot must be unrestricted");
    }

    #[test]
    fn low_peer_count_restricted() {
        let mut snap = healthy();
        snap.active_peers = 50;
        let status = snap.assess();
        assert!(
            matches!(status, NetworkHealthStatus::RestrictedMode { .. }),
            "low peer count must trigger restricted mode"
        );
        if let NetworkHealthStatus::RestrictedMode { failing } = status {
            assert!(
                failing
                    .iter()
                    .any(|c| matches!(c, HealthCondition::PeerCount { .. })),
                "PeerCount condition must be in failing list"
            );
        }
    }

    #[test]
    fn low_subnet_diversity_restricted() {
        let mut snap = healthy();
        snap.distinct_8_blocks = 2;
        let status = snap.assess();
        assert!(matches!(status, NetworkHealthStatus::RestrictedMode { .. }));
        if let NetworkHealthStatus::RestrictedMode { failing } = status {
            assert!(failing
                .iter()
                .any(|c| matches!(c, HealthCondition::SubnetDiversity { .. })));
        }
    }

    #[test]
    fn high_cluster_concentration_restricted() {
        let mut snap = healthy();
        snap.max_cluster_fraction = 0.60;
        let status = snap.assess();
        assert!(matches!(status, NetworkHealthStatus::RestrictedMode { .. }));
        if let NetworkHealthStatus::RestrictedMode { failing } = status {
            assert!(failing
                .iter()
                .any(|c| matches!(c, HealthCondition::ClusterConcentration { .. })));
        }
    }

    #[test]
    fn peer_decline_restricted() {
        let mut snap = healthy();
        snap.peer_count_change_7d = -0.30; // 30% decline > MAX_PEER_DECLINE_7D (20%)
        let status = snap.assess();
        assert!(matches!(status, NetworkHealthStatus::RestrictedMode { .. }));
        if let NetworkHealthStatus::RestrictedMode { failing } = status {
            assert!(failing
                .iter()
                .any(|c| matches!(c, HealthCondition::PeerDecline { .. })));
        }
    }
}
