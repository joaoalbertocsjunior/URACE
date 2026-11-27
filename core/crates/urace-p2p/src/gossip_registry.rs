//! M16 — Typed gossip validation.
//!
//! Message taxonomy and envelope types live in `urace-net-types::gossip`.
//! This module owns only the validation logic (structural + Ed25519) so that
//! adding a new application message kind requires no change here.

pub use urace_net_types::{
    GossipEnvelope, GossipMessageKind, GossipRegistryError, GOSSIP_MAX_AGE_SECS,
    MAX_GOSSIP_PAYLOAD_BYTES,
};

// ── validation ────────────────────────────────────────────────────────────────

/// Structural validation: freshness, payload size, hex format.
///
/// Does NOT verify the Ed25519 signature math. Full cryptographic check is
/// performed by `validate_envelope_with_key` once the public key is resolved.
pub fn validate_envelope_structural(
    env: &GossipEnvelope,
    now_secs: u64,
) -> Result<(), GossipRegistryError> {
    let age_secs = now_secs.saturating_sub(env.signed_at_secs);
    if age_secs >= GOSSIP_MAX_AGE_SECS {
        return Err(GossipRegistryError::Expired { age_secs });
    }
    if env.payload.len() > MAX_GOSSIP_PAYLOAD_BYTES {
        return Err(GossipRegistryError::PayloadTooLarge {
            size: env.payload.len(),
            max: MAX_GOSSIP_PAYLOAD_BYTES,
        });
    }
    if env.signature_hex.len() != 128 {
        return Err(GossipRegistryError::SignatureInvalid);
    }
    if hex::decode(&env.signature_hex).is_err() {
        return Err(GossipRegistryError::SignatureInvalid);
    }
    Ok(())
}

/// Full validation including Ed25519 signature verification.
///
/// `pub_key_bytes` is the 32-byte compressed public key of `env.signer_peer_id`.
pub fn validate_envelope_with_key(
    env: &GossipEnvelope,
    pub_key_bytes: &[u8; 32],
    now_secs: u64,
) -> Result<(), GossipRegistryError> {
    validate_envelope_structural(env, now_secs)?;

    let mut canonical = Vec::with_capacity(1 + env.payload.len());
    canonical.push(env.kind.tag_byte());
    canonical.extend_from_slice(&env.payload);

    let sig_bytes_vec = hex::decode(&env.signature_hex).expect("hex already validated");
    let sig_bytes: &[u8; 64] = sig_bytes_vec
        .as_slice()
        .try_into()
        .map_err(|_| GossipRegistryError::SignatureInvalid)?;

    urace_crypto::ed25519_verify(pub_key_bytes, &canonical, sig_bytes)
        .map_err(|_| GossipRegistryError::SignatureInvalid)
}

// ── tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;
    use urace_crypto::Keypair;

    fn rng() -> StdRng { StdRng::seed_from_u64(42) }

    fn signed_env(kp: &Keypair, kind: GossipMessageKind, payload: &[u8], now: u64) -> GossipEnvelope {
        let mut canonical = vec![kind.tag_byte()];
        canonical.extend_from_slice(payload);
        let sig = kp.sign(&canonical);
        GossipEnvelope {
            kind,
            payload: payload.to_vec(),
            signer_peer_id: "peer-test".into(),
            signature_hex: hex::encode(sig),
            signed_at_secs: now,
        }
    }

    #[test]
    fn structural_valid_accepted() {
        let env = GossipEnvelope {
            kind: GossipMessageKind::PeerAnnounce,
            payload: b"{}".to_vec(),
            signer_peer_id: "p".into(),
            signature_hex: "ab".repeat(64),
            signed_at_secs: 1_000_000,
        };
        assert!(validate_envelope_structural(&env, 1_000_100).is_ok());
    }

    #[test]
    fn structural_expired_rejected() {
        let env = GossipEnvelope {
            kind: GossipMessageKind::OutcomeSignal,
            payload: b"x".to_vec(),
            signer_peer_id: "p".into(),
            signature_hex: "cd".repeat(64),
            signed_at_secs: 1_000_000,
        };
        assert!(matches!(
            validate_envelope_structural(&env, 1_000_400),
            Err(GossipRegistryError::Expired { .. })
        ));
    }

    #[test]
    fn structural_oversized_payload_rejected() {
        let env = GossipEnvelope {
            kind: GossipMessageKind::GoalBroadcast,
            payload: vec![0u8; MAX_GOSSIP_PAYLOAD_BYTES + 1],
            signer_peer_id: "p".into(),
            signature_hex: "ef".repeat(64),
            signed_at_secs: 1_000_000,
        };
        assert!(matches!(
            validate_envelope_structural(&env, 1_000_100),
            Err(GossipRegistryError::PayloadTooLarge { .. })
        ));
    }

    #[test]
    fn full_verify_valid_signature_accepted() {
        let kp = Keypair::generate(&mut rng());
        let now = 1_000_000u64;
        let env = signed_env(&kp, GossipMessageKind::SkillDeclaration, b"skill", now);
        assert!(validate_envelope_with_key(&env, &kp.public_key_bytes(), now + 10).is_ok());
    }

    #[test]
    fn full_verify_tampered_payload_rejected() {
        let kp = Keypair::generate(&mut rng());
        let now = 1_000_000u64;
        let mut env = signed_env(&kp, GossipMessageKind::OutcomeSignal, b"original", now);
        env.payload = b"tampered".to_vec();
        assert_eq!(
            validate_envelope_with_key(&env, &kp.public_key_bytes(), now + 10),
            Err(GossipRegistryError::SignatureInvalid)
        );
    }

    #[test]
    fn full_verify_wrong_key_rejected() {
        let kp1 = Keypair::generate(&mut rng());
        let kp2 = Keypair::generate(&mut StdRng::seed_from_u64(99));
        let now = 1_000_000u64;
        let env = signed_env(&kp1, GossipMessageKind::StateRoot, b"root", now);
        assert_eq!(
            validate_envelope_with_key(&env, &kp2.public_key_bytes(), now + 10),
            Err(GossipRegistryError::SignatureInvalid)
        );
    }
}
