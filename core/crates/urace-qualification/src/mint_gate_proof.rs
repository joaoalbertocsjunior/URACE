//! M32 — Mint gate bypass detection: every mint event must carry a verifiable proof
//! that score_delta > 0.

use serde::{Deserialize, Serialize};

pub const MINT_GATE_MIN_SCORE_DELTA: f64 = 0.0; // strictly greater than this

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MintGateProof {
    pub operation_id: String,
    pub score_delta: f64,
    pub peer_id: String,
    /// SHA-256(operation_id || score_delta_bytes || peer_id), hex-encoded.
    pub proof_hash: String,
}

#[derive(Debug, thiserror::Error)]
pub enum MintGateError {
    #[error("score delta {0} does not exceed mint threshold")]
    InsufficientDelta(f64),
    #[error("proof hash mismatch")]
    HashMismatch,
}

impl MintGateProof {
    /// Generate a proof. Fails if score_delta <= MINT_GATE_MIN_SCORE_DELTA.
    pub fn generate(
        operation_id: &str,
        score_delta: f64,
        peer_id: &str,
    ) -> Result<Self, MintGateError> {
        if score_delta <= MINT_GATE_MIN_SCORE_DELTA {
            return Err(MintGateError::InsufficientDelta(score_delta));
        }
        let proof_hash = compute_proof_hash(operation_id, score_delta, peer_id);
        Ok(MintGateProof {
            operation_id: operation_id.to_string(),
            score_delta,
            peer_id: peer_id.to_string(),
            proof_hash,
        })
    }

    /// Verify the proof hash and that score_delta > 0.
    pub fn verify(&self) -> Result<(), MintGateError> {
        if self.score_delta <= MINT_GATE_MIN_SCORE_DELTA {
            return Err(MintGateError::InsufficientDelta(self.score_delta));
        }
        let expected = compute_proof_hash(&self.operation_id, self.score_delta, &self.peer_id);
        if expected != self.proof_hash {
            return Err(MintGateError::HashMismatch);
        }
        Ok(())
    }
}

fn compute_proof_hash(operation_id: &str, score_delta: f64, peer_id: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(operation_id.as_bytes());
    h.update(&score_delta.to_le_bytes());
    h.update(peer_id.as_bytes());
    hex::encode(h.finalize())
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn positive_delta_generates_valid_proof() {
        let proof = MintGateProof::generate("op-001", 1.5, "peer-abc").unwrap();
        assert!(proof.verify().is_ok());
        assert_eq!(proof.operation_id, "op-001");
        assert!((proof.score_delta - 1.5).abs() < 1e-12);
    }

    #[test]
    fn zero_delta_rejected_at_generate() {
        let err = MintGateProof::generate("op-002", 0.0, "peer-abc").unwrap_err();
        assert!(matches!(err, MintGateError::InsufficientDelta(d) if d == 0.0));
    }

    #[test]
    fn negative_delta_rejected_at_generate() {
        let err = MintGateProof::generate("op-003", -0.5, "peer-abc").unwrap_err();
        assert!(matches!(err, MintGateError::InsufficientDelta(_)));
    }

    #[test]
    fn hash_tamper_fails_verify() {
        let mut proof = MintGateProof::generate("op-004", 2.0, "peer-xyz").unwrap();
        proof.proof_hash = "deadbeef".repeat(8); // corrupt the hash
        assert!(matches!(proof.verify(), Err(MintGateError::HashMismatch)));
    }

    #[test]
    fn zero_delta_rejected_at_verify() {
        // Craft a proof where score_delta was manually set to 0 after generation.
        let mut proof = MintGateProof::generate("op-005", 0.1, "peer-xyz").unwrap();
        proof.score_delta = 0.0;
        assert!(matches!(
            proof.verify(),
            Err(MintGateError::InsufficientDelta(_))
        ));
    }

    #[test]
    fn deterministic_hash_for_same_inputs() {
        let p1 = MintGateProof::generate("op-006", 3.0, "peer-def").unwrap();
        let p2 = MintGateProof::generate("op-006", 3.0, "peer-def").unwrap();
        assert_eq!(p1.proof_hash, p2.proof_hash);
    }
}
