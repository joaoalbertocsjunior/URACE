//! R-6/R-7: BEP 5 Kademlia DHT + P2P peer discovery.
//!
//! Implementation phases:
//! R-6 — Kademlia routing table (256-bucket, XOR metric, K=20), peer discovery,
//!        admission gate, cartel guard, consensus, federation
//! R-7 — PeerExchange protocol, freeform routing

pub mod cartel_guard;
pub mod consensus;
pub mod federation;
pub mod freeform_routing;
pub mod kademlia;
pub mod p2p_capabilities;
pub mod peer_address_book;
pub mod peer_discovery;
pub mod peer_exchange;
pub mod peer_selection;

pub use cartel_guard::{CartelCheckResult, IpBucketGuard, check_chunk_concentration};
pub use consensus::{SealProposal, SealVote, VoteCollector, consensus_threshold};
pub use federation::{FederationError, FederationStore, NetworkAnnounce, validate_authority_proof};
pub use kademlia::{KBucket, KademliaTable, NodeInfo};
pub use p2p_capabilities::{CapabilityRegistry, PeerCapabilities};
pub use peer_address_book::{PeerAddressBook, PeerAddrs};
pub use peer_discovery::{AdmissionGate, DiscoverySession, PeerAdmissionRecord, PeerAdmissionState};
pub use peer_selection::{PeerCandidate, PeerSelector, ScoringParams, SelectionStatus};
