//! M01 — Identity continuity enforcement.
//!
//! When a peer migrates from an old key to a new key, they must present a
//! `MigrationClaim` signed by the old key. `verify_migration()` checks:
//! 1. The old key signed `canonical_payload(new_key_id, timestamp)`.
//! 2. The claim is not stale (within `MIGRATION_CLAIM_MAX_AGE_SECS`).
//! Without a valid claim, the new key gets no inherited reputation.

use serde::{Deserialize, Serialize};
use thiserror::Error;
use urace_crypto::ed25519_verify;

/// Signed payload: `"migrate:{new_key_id}:{timestamp_secs}"` as UTF-8 bytes.
pub fn canonical_payload(new_key_id: &str, timestamp_secs: u64) -> Vec<u8> {
    format!("migrate:{new_key_id}:{timestamp_secs}")
        .into_bytes()
}

/// A claim that `new_key_id` is the legitimate continuation of `old_key_id`.
/// The `signature_hex` is an Ed25519 signature by the old key over
/// `canonical_payload(new_key_id, timestamp_secs)`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationClaim {
    pub old_key_id: String,
    pub old_public_key_hex: String,
    pub new_key_id: String,
    pub timestamp_secs: u64,
    pub signature_hex: String,
}

#[derive(Debug, Error, PartialEq)]
pub enum ContinuityError {
    #[error("migration claim is stale (age {age_secs}s > max {max_secs}s)")]
    StaleClaim { age_secs: u64, max_secs: u64 },
    #[error("invalid old-key signature on migration claim")]
    BadSignature,
    #[error("hex decode error: {0}")]
    HexDecode(String),
}

/// Maximum age of a migration claim before it is rejected.
pub const MIGRATION_CLAIM_MAX_AGE_SECS: u64 = 300;

fn now_secs() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Verify a `MigrationClaim`.
///
/// Returns `Ok(())` if the claim is fresh and the old-key signature is valid.
/// Returns `Err(ContinuityError)` otherwise — the new key inherits nothing.
pub fn verify_migration(claim: &MigrationClaim) -> Result<(), ContinuityError> {
    let now = now_secs();
    let age = now.saturating_sub(claim.timestamp_secs);
    if age > MIGRATION_CLAIM_MAX_AGE_SECS {
        return Err(ContinuityError::StaleClaim {
            age_secs: age,
            max_secs: MIGRATION_CLAIM_MAX_AGE_SECS,
        });
    }

    let pub_bytes = hex::decode(&claim.old_public_key_hex)
        .map_err(|e| ContinuityError::HexDecode(e.to_string()))?;
    let sig_bytes = hex::decode(&claim.signature_hex)
        .map_err(|e| ContinuityError::HexDecode(e.to_string()))?;

    let payload = canonical_payload(&claim.new_key_id, claim.timestamp_secs);

    if pub_bytes.len() != 32 || sig_bytes.len() != 64 {
        return Err(ContinuityError::BadSignature);
    }

    let mut pk = [0u8; 32];
    let mut sig = [0u8; 64];
    pk.copy_from_slice(&pub_bytes);
    sig.copy_from_slice(&sig_bytes);

    ed25519_verify(&pk, &payload, &sig).map_err(|_| ContinuityError::BadSignature)
}

/// Build a `MigrationClaim` using an existing `Keypair` for the old key.
/// The caller supplies the Ed25519 `Keypair` they are rotating away from.
pub fn build_migration_claim(
    old_keypair: &urace_crypto::Keypair,
    old_key_id: &str,
    new_key_id: &str,
    timestamp_secs: u64,
) -> MigrationClaim {
    let payload = canonical_payload(new_key_id, timestamp_secs);
    let signature = old_keypair.sign(&payload);
    MigrationClaim {
        old_key_id: old_key_id.to_owned(),
        old_public_key_hex: hex::encode(old_keypair.public_key_bytes()),
        new_key_id: new_key_id.to_owned(),
        timestamp_secs,
        signature_hex: hex::encode(signature),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::OsRng;
    use urace_crypto::Keypair;

    fn fresh_claim(old_kp: &Keypair, old_id: &str, new_id: &str) -> MigrationClaim {
        let ts = now_secs();
        build_migration_claim(old_kp, old_id, new_id, ts)
    }

    #[test]
    fn valid_claim_accepted() {
        let old_kp = Keypair::generate(&mut OsRng);
        let claim = fresh_claim(&old_kp, "old-key-1", "new-key-2");
        assert!(verify_migration(&claim).is_ok());
    }

    #[test]
    fn stale_claim_rejected() {
        let old_kp = Keypair::generate(&mut OsRng);
        let ts = now_secs().saturating_sub(MIGRATION_CLAIM_MAX_AGE_SECS + 1);
        let claim = build_migration_claim(&old_kp, "old-key-1", "new-key-2", ts);
        assert!(matches!(
            verify_migration(&claim),
            Err(ContinuityError::StaleClaim { .. })
        ));
    }

    #[test]
    fn wrong_signature_rejected() {
        let old_kp = Keypair::generate(&mut OsRng);
        let mut claim = fresh_claim(&old_kp, "old-key-1", "new-key-2");
        // Corrupt the signature
        claim.signature_hex = "aa".repeat(64);
        assert!(matches!(
            verify_migration(&claim),
            Err(ContinuityError::BadSignature)
        ));
    }

    #[test]
    fn wrong_key_rejected() {
        let old_kp = Keypair::generate(&mut OsRng);
        let other_kp = Keypair::generate(&mut OsRng);
        let ts = now_secs();
        let payload = canonical_payload("new-key-2", ts);
        // Sign with wrong key
        let sig = other_kp.sign(&payload);
        let claim = MigrationClaim {
            old_key_id: "old-key-1".into(),
            old_public_key_hex: hex::encode(old_kp.public_key_bytes()),
            new_key_id: "new-key-2".into(),
            timestamp_secs: ts,
            signature_hex: hex::encode(sig),
        };
        assert!(matches!(
            verify_migration(&claim),
            Err(ContinuityError::BadSignature)
        ));
    }

    #[test]
    fn tampered_new_key_id_rejected() {
        let old_kp = Keypair::generate(&mut OsRng);
        let mut claim = fresh_claim(&old_kp, "old-key-1", "new-key-2");
        // Change the new_key_id after signing — payload mismatch
        claim.new_key_id = "attacker-key-99".into();
        assert!(matches!(
            verify_migration(&claim),
            Err(ContinuityError::BadSignature)
        ));
    }
}
