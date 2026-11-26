//! M82 — TPM (Trusted Platform Module) attestation interface.
//!
//! Provides a trait for TPM-based remote attestation.  Real implementations
//! would use the TSS2 or Windows TPM API; this module provides a stub for
//! test and development environments.
//!
//! **Purpose**: prove to a remote verifier that code is running on trusted
//! hardware with a known firmware configuration, binding the peer's identity
//! to the attestation report.

use serde::{Deserialize, Serialize};

#[derive(Debug, thiserror::Error)]
pub enum TpmError {
    #[error("TPM hardware unavailable")]
    HardwareUnavailable,
    #[error("attestation report generation failed: {0}")]
    AttestationFailed(String),
    #[error("attestation report verification failed")]
    VerificationFailed,
    #[error("nonce mismatch — replay attack suspected")]
    NonceMismatch,
}

/// An attestation report containing PCR measurements and a bound nonce.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttestationReport {
    /// Random nonce supplied by the verifier (prevents replay).
    pub nonce: Vec<u8>,
    /// Platform Configuration Register hash — binds firmware state.
    pub pcr_digest: String,
    /// Peer public key bound into this report.
    pub peer_public_key_hex: String,
    /// Signature over (nonce || pcr_digest || peer_public_key_hex) using the AIK.
    pub signature_hex: String,
}

/// Trait for TPM attestation operations.
pub trait TpmBackend: Send + Sync {
    /// Generate an attestation report for the given `nonce` and `peer_public_key`.
    fn attest(
        &self,
        nonce: &[u8],
        peer_public_key_hex: &str,
    ) -> Result<AttestationReport, TpmError>;

    /// Verify that an `AttestationReport` is valid for the supplied `nonce`.
    fn verify(&self, report: &AttestationReport, expected_nonce: &[u8]) -> Result<(), TpmError>;

    /// Whether this is a real hardware TPM.
    fn is_hardware(&self) -> bool;
}

/// Software-only TPM stub — **NOT for production use**.
pub struct SoftwareTpm;

impl TpmBackend for SoftwareTpm {
    fn attest(
        &self,
        nonce: &[u8],
        peer_public_key_hex: &str,
    ) -> Result<AttestationReport, TpmError> {
        use sha2::{Digest, Sha256};
        let mut h = Sha256::new();
        h.update(b"pcr-stub");
        h.update(nonce);
        let pcr_digest = hex::encode(h.finalize());

        let mut sig_h = Sha256::new();
        sig_h.update(nonce);
        sig_h.update(pcr_digest.as_bytes());
        sig_h.update(peer_public_key_hex.as_bytes());
        let signature_hex = hex::encode(sig_h.finalize());

        Ok(AttestationReport {
            nonce: nonce.to_vec(),
            pcr_digest,
            peer_public_key_hex: peer_public_key_hex.to_owned(),
            signature_hex,
        })
    }

    fn verify(&self, report: &AttestationReport, expected_nonce: &[u8]) -> Result<(), TpmError> {
        if report.nonce != expected_nonce {
            return Err(TpmError::NonceMismatch);
        }
        // Re-compute expected signature and compare.
        use sha2::{Digest, Sha256};
        let mut sig_h = Sha256::new();
        sig_h.update(expected_nonce);
        sig_h.update(report.pcr_digest.as_bytes());
        sig_h.update(report.peer_public_key_hex.as_bytes());
        let expected_sig = hex::encode(sig_h.finalize());
        if expected_sig != report.signature_hex {
            return Err(TpmError::VerificationFailed);
        }
        Ok(())
    }

    fn is_hardware(&self) -> bool { false }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn attest_and_verify_roundtrip() {
        let tpm = SoftwareTpm;
        let nonce = b"random-nonce-32-bytes-padded!!!!".as_slice();
        let pubkey_hex = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899";
        let report = tpm.attest(nonce, pubkey_hex).unwrap();
        assert!(tpm.verify(&report, nonce).is_ok());
    }

    #[test]
    fn wrong_nonce_fails_verification() {
        let tpm = SoftwareTpm;
        let nonce = b"nonce-a";
        let report = tpm.attest(nonce, "00aa").unwrap();
        assert!(matches!(tpm.verify(&report, b"nonce-b"), Err(TpmError::NonceMismatch)));
    }

    #[test]
    fn software_tpm_not_hardware() {
        assert!(!SoftwareTpm.is_hardware());
    }
}
