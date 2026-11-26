//! M57 — Build attestation: cryptographic binding of a deployable binary to its source.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildAttestation {
    pub binary_hash: String,    // SHA-256 hex of the compiled binary
    pub source_commit: String,  // git commit SHA
    pub builder_id: String,     // CI runner identity
    pub built_at_unix: u64,
    pub signature_hex: String,  // SHA-256(binary_hash || source_commit || builder_id)
}

#[derive(Debug, thiserror::Error)]
pub enum BuildAttestationError {
    #[error("binary hash mismatch")]
    BinaryHashMismatch,
    #[error("attestation signature invalid")]
    SignatureInvalid,
    #[error("attestation expired")]
    Expired,
}

fn compute_attestation_signature(
    binary_hash: &str,
    source_commit: &str,
    builder_id: &str,
) -> String {
    let mut hasher = Sha256::new();
    hasher.update(binary_hash.as_bytes());
    hasher.update(source_commit.as_bytes());
    hasher.update(builder_id.as_bytes());
    hex::encode(hasher.finalize())
}

impl BuildAttestation {
    /// Create a new attestation; computes the signature hash automatically.
    pub fn new(
        binary_hash: &str,
        source_commit: &str,
        builder_id: &str,
        built_at_unix: u64,
    ) -> Self {
        let signature_hex =
            compute_attestation_signature(binary_hash, source_commit, builder_id);
        BuildAttestation {
            binary_hash: binary_hash.to_string(),
            source_commit: source_commit.to_string(),
            builder_id: builder_id.to_string(),
            built_at_unix,
            signature_hex,
        }
    }

    /// Verify signature and that binary_hash matches expected.
    pub fn verify(&self, expected_binary_hash: &str) -> Result<(), BuildAttestationError> {
        // Check binary hash first
        if self.binary_hash != expected_binary_hash {
            return Err(BuildAttestationError::BinaryHashMismatch);
        }

        // Recompute and verify signature
        let expected_sig =
            compute_attestation_signature(&self.binary_hash, &self.source_commit, &self.builder_id);
        if self.signature_hex != expected_sig {
            return Err(BuildAttestationError::SignatureInvalid);
        }

        Ok(())
    }

    /// True if built_at_unix + max_age_secs < now_unix.
    pub fn is_expired(&self, now_unix: u64, max_age_secs: u64) -> bool {
        self.built_at_unix + max_age_secs < now_unix
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_attestation() -> BuildAttestation {
        BuildAttestation::new(
            "abc123def456",
            "deadbeef1234",
            "ci-runner-42",
            1_000_000,
        )
    }

    #[test]
    fn valid_attestation_verifies() {
        let attest = make_attestation();
        let result = attest.verify("abc123def456");
        assert!(result.is_ok());
    }

    #[test]
    fn wrong_binary_hash_fails() {
        let attest = make_attestation();
        let result = attest.verify("wronghash999");
        assert!(matches!(result, Err(BuildAttestationError::BinaryHashMismatch)));
    }

    #[test]
    fn expired_attestation_detected() {
        let attest = make_attestation(); // built_at_unix = 1_000_000
        let max_age_secs = 86_400; // 1 day
        // Now = built_at + max_age + 1 → expired
        assert!(attest.is_expired(1_000_000 + 86_400 + 1, max_age_secs));
        // Now = built_at + max_age → not expired (boundary is exclusive via <)
        assert!(!attest.is_expired(1_000_000 + 86_400, max_age_secs));
    }

    #[test]
    fn signature_tamper_detected() {
        let mut attest = make_attestation();
        // Tamper with the signature
        attest.signature_hex = "0000000000000000000000000000000000000000000000000000000000000000".to_string();
        let result = attest.verify("abc123def456");
        assert!(matches!(result, Err(BuildAttestationError::SignatureInvalid)));
    }
}
