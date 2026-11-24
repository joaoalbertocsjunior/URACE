//! R-6/R-7: BEP 5 Kademlia DHT + P2P peer discovery.
//!
//! Implementation phases:
//! R-6 — Kademlia routing table (256-bucket, XOR metric, K=20), peer discovery,
//!        admission gate, cartel guard, consensus, federation
//! R-7 — PeerExchange protocol, freeform routing

pub mod kademlia;
pub mod peer_discovery;
pub mod cartel_guard;
pub mod consensus;
pub mod federation;
pub mod peer_exchange;
pub mod freeform_routing;

pub use kademlia::{KBucket, KademliaTable, NodeInfo};
pub use peer_discovery::{AdmissionGate, DiscoverySession, PeerAdmissionRecord, PeerAdmissionState};
pub use cartel_guard::{CartelCheckResult, IpBucketGuard, check_chunk_concentration};
pub use consensus::{SealProposal, SealVote, VoteCollector, consensus_threshold};
pub use federation::{FederationError, FederationStore, NetworkAnnounce, validate_authority_proof};
