//! `urace-net-types` — shared P2P message boundary types.
//!
//! This crate defines the gossip envelope contract that both the P2P routing
//! layer (`urace-p2p`) and application crates (`urace-qualification`,
//! `urace-goals`, `urace-work`, …) depend on. Neither layer depends on the
//! other — they meet here.
//!
//! # What belongs here
//! - Message type taxonomy (`GossipMessageKind`)
//! - Signed envelope carrier (`GossipEnvelope`)
//! - Shared error variants (`GossipRegistryError`)
//! - Shared constants (TTL, max payload size)
//!
//! # What does NOT belong here
//! - Signature verification logic → `urace-p2p::gossip_registry`
//! - Routing / DHT logic → `urace-p2p`
//! - Application payload semantics → respective application crates

pub mod gossip;

pub use gossip::{
    GossipEnvelope, GossipMessageKind, GossipRegistryError, GOSSIP_MAX_AGE_SECS,
    MAX_GOSSIP_PAYLOAD_BYTES,
};
