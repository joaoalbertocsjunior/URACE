//! R-6/R-7: BEP 5 Kademlia DHT + P2P peer discovery.
//!
//! Implementation phases:
//! R-6 — Kademlia routing table (256-bucket, XOR metric, K=20), peer discovery,
//!        admission gate, cartel guard, consensus, federation
//! R-7 — PeerExchange protocol, freeform routing
//! M22 — Kademlia subnet diversity
//! M25 — Sybil admission gate
//! M26 — Message replay guard
//! M27 — State root verification
//! M34 — Reputation source diversity
//! M59 — Connection fingerprinting (traffic isolation)
//! M66 — Network health threshold
//! M67 — Network-level rate limiting
//! M09 — Approval graph monitoring
//! M16 — Gossip integrity
//! M71 — Gossip flood throttle (in peer_exchange)

pub mod cartel_guard;
pub mod domain_concentration;
pub mod gossip_registry;
pub mod net_rate_limit;
pub mod replay_guard;
pub mod state_root;
pub mod sybil_gate;
pub mod traffic_isolation;
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
pub use domain_concentration::{
    DomainConcentrationError, DomainConcentrationGuard, DomainConcentrationResult, DomainSlot,
    DOMAIN_CONCENTRATION_THRESHOLD, MAX_DOMAIN_SLOTS_PER_PEER,
};
pub use gossip_registry::{
    validate_envelope_structural, validate_envelope_with_key, GossipEnvelope, GossipMessageKind,
    GossipRegistryError, MAX_GOSSIP_PAYLOAD_BYTES,
};
pub use gossip_integrity::{
    verify_gossip, verify_typed_gossip, GossipVerifyResult, SignedGossip, GOSSIP_MAX_AGE_SECS,
};
pub use consensus::{
    consensus_threshold, select_canonical_fork, ForkCandidate, SealProposal, SealVote,
    VoteCollector,
};
pub use federation::{validate_authority_proof, FederationError, FederationStore, NetworkAnnounce};
pub use kademlia::{KBucket, KademliaTable, NodeInfo};
pub use p2p_capabilities::{CapabilityRegistry, PeerCapabilities};
pub use peer_address_book::{PeerAddressBook, PeerAddrs};
pub use peer_discovery::{
    AdmissionGate, DiscoverySession, JurisdictionCode, JurisdictionGuard, PeerAdmissionRecord,
    PeerAdmissionState, MAX_JURISDICTION_FRACTION, PEER_EXPIRY_SECS,
};
pub use peer_selection::{PeerCandidate, PeerSelector, ScoringParams, SelectionStatus};

// M25 — Sybil admission gate
pub use sybil_gate::{
    SybilAdmissionResult, SybilGate, MAX_NEW_PEERS_PER_SUBNET_PER_HOUR, SYBIL_WINDOW_SECS,
};

// M26 — Message replay guard
pub use replay_guard::{ReplayGuard, ReplayResult, REPLAY_WINDOW_SECS};

// M27 — State root verification
pub use state_root::{
    assert_state_root, compute_state_root, verify_state_root, StateRoot, StateRootError,
};

// M59 — Connection fingerprinting
pub use traffic_isolation::{ConnectionFingerprint, FingerprintStore};

// M67 — Network-level rate limiting
pub use net_rate_limit::{
    MessageClass, NetRateLimiter, NetRateResult, NET_RATE_MESSAGES_PER_SEC, NET_RATE_WINDOW_SECS,
};
