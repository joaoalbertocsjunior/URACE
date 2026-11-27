//! Gossip message boundary types.
//!
//! Adding a new application message type = add a variant here + a tag byte.
//! No change to `urace-p2p` required.

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Maximum payload size for a gossip envelope (64 KiB).
pub const MAX_GOSSIP_PAYLOAD_BYTES: usize = 65_536;

/// Freshness window: gossip older than this is rejected.
pub const GOSSIP_MAX_AGE_SECS: u64 = 300;

// ── kind ──────────────────────────────────────────────────────────────────────

/// Typed gossip message kinds.
///
/// Each variant has a unique `tag_byte()` used for Ed25519 signature domain
/// separation: `canonical_bytes = [tag_byte()] ++ payload`.
///
/// Adding a new application message type here does not require any change in
/// `urace-p2p` — the P2P layer routes by tag byte, not by semantic meaning.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum GossipMessageKind {
    /// Peer joining or updating DHT state.
    PeerAnnounce,
    /// Post-deployment outcome report (product feedback loop).
    OutcomeSignal,
    /// Executor capability / skill claim.
    SkillDeclaration,
    /// Goal propagation across peers (goal-driven work surfacing).
    GoalBroadcast,
    /// Reputation delta from scoring.
    ReputationUpdate,
    /// New work item available.
    WorkListing,
    /// State root hash broadcast (M27).
    StateRoot,
}

impl GossipMessageKind {
    /// Unique tag byte for signature domain separation.
    pub fn tag_byte(&self) -> u8 {
        match self {
            GossipMessageKind::PeerAnnounce     => 0x01,
            GossipMessageKind::OutcomeSignal    => 0x02,
            GossipMessageKind::SkillDeclaration => 0x03,
            GossipMessageKind::GoalBroadcast    => 0x04,
            GossipMessageKind::ReputationUpdate => 0x05,
            GossipMessageKind::WorkListing      => 0x06,
            GossipMessageKind::StateRoot        => 0x07,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            GossipMessageKind::PeerAnnounce     => "PeerAnnounce",
            GossipMessageKind::OutcomeSignal    => "OutcomeSignal",
            GossipMessageKind::SkillDeclaration => "SkillDeclaration",
            GossipMessageKind::GoalBroadcast    => "GoalBroadcast",
            GossipMessageKind::ReputationUpdate => "ReputationUpdate",
            GossipMessageKind::WorkListing      => "WorkListing",
            GossipMessageKind::StateRoot        => "StateRoot",
        }
    }

    pub fn from_str(s: &str) -> Result<Self, GossipRegistryError> {
        match s {
            "PeerAnnounce"     => Ok(GossipMessageKind::PeerAnnounce),
            "OutcomeSignal"    => Ok(GossipMessageKind::OutcomeSignal),
            "SkillDeclaration" => Ok(GossipMessageKind::SkillDeclaration),
            "GoalBroadcast"    => Ok(GossipMessageKind::GoalBroadcast),
            "ReputationUpdate" => Ok(GossipMessageKind::ReputationUpdate),
            "WorkListing"      => Ok(GossipMessageKind::WorkListing),
            "StateRoot"        => Ok(GossipMessageKind::StateRoot),
            other              => Err(GossipRegistryError::UnknownKind(other.to_string())),
        }
    }
}

// ── envelope ──────────────────────────────────────────────────────────────────

/// A typed, signed gossip envelope.
///
/// Constructed by application crates; validated and routed by `urace-p2p`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GossipEnvelope {
    pub kind: GossipMessageKind,
    /// Serialised inner message payload.
    pub payload: Vec<u8>,
    pub signer_peer_id: String,
    /// Ed25519 signature over `(kind.tag_byte() || payload)`, lowercase hex.
    /// Must be exactly 128 hex characters (64 bytes).
    pub signature_hex: String,
    /// Unix timestamp (seconds) at which the message was signed.
    pub signed_at_secs: u64,
}

// ── errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error, PartialEq)]
pub enum GossipRegistryError {
    #[error("unknown gossip kind: {0}")]
    UnknownKind(String),
    #[error("signature invalid")]
    SignatureInvalid,
    #[error("message expired: age {age_secs}s")]
    Expired { age_secs: u64 },
    #[error("payload too large: {size} bytes (max {max})")]
    PayloadTooLarge { size: usize, max: usize },
}

// ── tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kind_roundtrip_all_variants() {
        let names = [
            "PeerAnnounce", "OutcomeSignal", "SkillDeclaration", "GoalBroadcast",
            "ReputationUpdate", "WorkListing", "StateRoot",
        ];
        for name in &names {
            let kind = GossipMessageKind::from_str(name).unwrap();
            assert_eq!(kind.as_str(), *name);
        }
    }

    #[test]
    fn unknown_kind_errors() {
        assert_eq!(
            GossipMessageKind::from_str("Bogus"),
            Err(GossipRegistryError::UnknownKind("Bogus".into()))
        );
    }

    #[test]
    fn tag_bytes_are_unique() {
        use std::collections::HashSet;
        let tags: HashSet<u8> = [
            GossipMessageKind::PeerAnnounce,
            GossipMessageKind::OutcomeSignal,
            GossipMessageKind::SkillDeclaration,
            GossipMessageKind::GoalBroadcast,
            GossipMessageKind::ReputationUpdate,
            GossipMessageKind::WorkListing,
            GossipMessageKind::StateRoot,
        ]
        .iter()
        .map(|k| k.tag_byte())
        .collect();
        assert_eq!(tags.len(), 7);
    }

    #[test]
    fn envelope_is_serializable() {
        let env = GossipEnvelope {
            kind: GossipMessageKind::OutcomeSignal,
            payload: b"test".to_vec(),
            signer_peer_id: "peer-1".into(),
            signature_hex: "ab".repeat(64),
            signed_at_secs: 1_000_000,
        };
        let json = serde_json::to_string(&env).unwrap();
        let back: GossipEnvelope = serde_json::from_str(&json).unwrap();
        assert_eq!(back.kind, GossipMessageKind::OutcomeSignal);
        assert_eq!(back.payload, b"test");
    }

    #[test]
    fn error_display_is_readable() {
        let e = GossipRegistryError::UnknownKind("Foo".into());
        assert!(e.to_string().contains("Foo"));
        let e2 = GossipRegistryError::Expired { age_secs: 400 };
        assert!(e2.to_string().contains("400"));
    }
}
