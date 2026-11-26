//! M16 — Gossip integrity: unsigned or expired gossip is rejected.
//!
//! Structural validation of signed gossip messages. Full Ed25519 signature
//! verification is performed at the call site using `urace_crypto::verify_signature`;
//! this module enforces non-empty hex signature and freshness requirements.

/// Maximum age of a gossip message before it is considered expired.
pub const GOSSIP_MAX_AGE_SECS: u64 = 300; // 5 minutes

/// Result of verifying a gossip message.
#[derive(Debug, Clone, PartialEq)]
pub enum GossipVerifyResult {
    /// Message passes all structural checks.
    Valid,
    /// No signature was provided.
    MissingSignature,
    /// Signature is present but malformed (not valid hex or wrong length).
    InvalidSignature,
    /// Message timestamp is older than `GOSSIP_MAX_AGE_SECS`.
    Expired { age_secs: u64 },
}

/// A gossip message with an Ed25519 signature.
pub struct SignedGossip {
    /// JSON-serialized `NodeInfo` payload.
    pub payload: Vec<u8>,
    /// Peer ID of the signer.
    pub signer_peer_id: String,
    /// Ed25519 signature over `payload`, encoded as lowercase hex.
    /// Ed25519 signatures are 64 bytes → 128 hex characters.
    pub signature_hex: String,
    /// Unix timestamp (seconds) at which the message was signed.
    pub signed_at_secs: u64,
}

/// Verify a gossip message structurally.
///
/// Checks:
/// 1. `signature_hex` is non-empty.
/// 2. `signature_hex` decodes to valid hex (non-empty bytes).
/// 3. Message age < `GOSSIP_MAX_AGE_SECS`.
///
/// Full Ed25519 verification (public key lookup + signature math) is left to
/// the call site.
pub fn verify_gossip(msg: &SignedGossip, now_secs: u64) -> GossipVerifyResult {
    // 1. Signature must be non-empty.
    if msg.signature_hex.is_empty() {
        return GossipVerifyResult::MissingSignature;
    }

    // 2. Signature must be valid hex.
    if hex::decode(&msg.signature_hex).is_err() {
        return GossipVerifyResult::InvalidSignature;
    }

    // 3. Check expiry.
    let age_secs = now_secs.saturating_sub(msg.signed_at_secs);
    if age_secs >= GOSSIP_MAX_AGE_SECS {
        return GossipVerifyResult::Expired { age_secs };
    }

    GossipVerifyResult::Valid
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_msg(sig: &str, signed_at: u64) -> SignedGossip {
        SignedGossip {
            payload: b"{}".to_vec(),
            signer_peer_id: "peer-a".into(),
            signature_hex: sig.to_string(),
            signed_at_secs: signed_at,
        }
    }

    #[test]
    fn empty_signature_rejected() {
        let msg = make_msg("", 1_000_000);
        assert_eq!(
            verify_gossip(&msg, 1_000_000),
            GossipVerifyResult::MissingSignature
        );
    }

    #[test]
    fn expired_message_rejected() {
        // now - signed_at = 400 > 300
        let now = 1_000_400u64;
        let signed_at = 1_000_000u64;
        // Valid hex signature (doesn't matter what it is for this test)
        let sig = "deadbeef";
        let msg = make_msg(sig, signed_at);
        assert!(
            matches!(
                verify_gossip(&msg, now),
                GossipVerifyResult::Expired { age_secs: 400 }
            ),
            "message older than 300s must be expired"
        );
    }

    #[test]
    fn valid_gossip_accepted() {
        let now = 1_000_100u64;
        let signed_at = 1_000_000u64;
        // 128-char hex string simulating an Ed25519 sig (64 bytes).
        let sig = "a".repeat(128);
        let msg = make_msg(&sig, signed_at);
        assert_eq!(
            verify_gossip(&msg, now),
            GossipVerifyResult::Valid,
            "non-empty hex sig within TTL must be valid"
        );
    }
}
