//! R-6/R-7: BEP 5 Kademlia DHT + P2P peer discovery.
//!
//! Implementation phases:
//! R-6 — Kademlia routing table (256-bucket, XOR metric, K=20)
//! R-7 — Peer discovery, admission gate, cartel guard, consensus

pub mod kademlia;

pub use kademlia::{KBucket, KademliaTable, NodeInfo};
