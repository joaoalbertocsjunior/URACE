//! R-6/R-7: BEP 5 Kademlia DHT + P2P peer discovery.
//!
//! Implementation phases:
//! R-6 — Kademlia routing table (256-bucket, XOR metric, K=20), peer discovery,
//!        admission gate, cartel guard, consensus, federation
//! R-7 — PeerExchange protocol, freeform routing
//! M22 — Kademlia subnet diversity
//! M66 — Network health threshold
//! M09 — Approval graph monitoring
//! M16 — Gossip integrity
//! M34 — Reputation source diversity
//! M71 — Gossip flood throttle (in peer_exchange)

pub mod cartel_guard;
pub mod consensus;
pub mod federation;
pub mod freeform_routing;
pub mod gossip_integrity;
pub mod graph_monitor;
pub mod kademlia;
pub mod network_health;
pub mod p2p_capabilities;
pub mod peer_address_book;
pub mod peer_discovery;
pub mod peer_exchange;
pub mod peer_improvement;
pub mod peer_selection;
pub mod reputation_diversity;

pub use cartel_guard::{check_chunk_concentration, CartelCheckResult, IpBucketGuard};
pub use consensus::{consensus_threshold, SealProposal, SealVote, VoteCollector};
pub use federation::{validate_authority_proof, FederationError, FederationStore, NetworkAnnounce};
pub use kademlia::{KBucket, KademliaTable, NodeInfo};
pub use p2p_capabilities::{CapabilityRegistry, PeerCapabilities};
pub use peer_address_book::{PeerAddressBook, PeerAddrs};
pub use peer_discovery::{
    AdmissionGate, DiscoverySession, PeerAdmissionRecord, PeerAdmissionState,
};
pub use peer_selection::{PeerCandidate, PeerSelector, ScoringParams, SelectionStatus};
