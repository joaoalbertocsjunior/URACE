//! `urace-p2p-analysis` — P2P observability modules.
//!
//! Extracted from `urace-p2p` to keep the core routing crate focused.
//! Depends on `urace-p2p` for shared types (Kademlia subnet helpers).

pub mod graph_monitor;
pub mod network_health;
pub mod peer_improvement;
pub mod reputation_diversity;

pub use graph_monitor::ApprovalGraph;
pub use network_health::{
    HealthCondition, NetworkHealthSnapshot, NetworkHealthStatus,
    MAX_CLUSTER_FRACTION, MAX_PEER_DECLINE_7D, MIN_ACTIVE_PEERS,
    MIN_COMPLETION_RATE_7D, MIN_DISTINCT_8_BLOCKS,
};
pub use peer_improvement::{
    amplification_boost, distinct_peers_for_task, ImprovementError,
    ImprovementLoop, PeerImprovementRecord,
};
pub use reputation_diversity::{
    adjusted_reputation, diversity_discount, DISCOUNT_FACTOR, MAX_SUBNET_FRACTION,
};
