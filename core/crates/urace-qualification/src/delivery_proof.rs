//! M44 — Delivery proof attestation.
//!
//! A delivery proof must be on record before minting is allowed.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DeliveryProofError {
    #[error("no delivery proof found for work_id '{0}'")]
    NotFound(String),
    #[error("delivery proof already registered for work_id '{0}'")]
    AlreadyRegistered(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeliveryProof {
    pub work_id: String,
    pub executor_peer_id: String,
    /// SHA-256 of the delivered artifact.
    pub delivery_hash: String,
    /// Unix timestamp secs as string.
    pub delivered_at: String,
    /// Ed25519 signature by executor over (work_id || delivery_hash), as hex.
    pub signature_hex: String,
}

pub struct DeliveryProofRegistry {
    proofs: HashMap<String, DeliveryProof>, // work_id -> proof
}

impl DeliveryProofRegistry {
    pub fn new() -> Self {
        DeliveryProofRegistry {
            proofs: HashMap::new(),
        }
    }

    pub fn register(&mut self, proof: DeliveryProof) -> Result<(), DeliveryProofError> {
        if self.proofs.contains_key(&proof.work_id) {
            return Err(DeliveryProofError::AlreadyRegistered(proof.work_id.clone()));
        }
        self.proofs.insert(proof.work_id.clone(), proof);
        Ok(())
    }

    pub fn get(&self, work_id: &str) -> Option<&DeliveryProof> {
        self.proofs.get(work_id)
    }

    /// Verify that a delivery proof exists and matches the expected executor.
    ///
    /// Note: full Ed25519 signature verification is the responsibility of the call site.
    pub fn verify_for_mint(
        &self,
        work_id: &str,
        expected_executor: &str,
    ) -> Result<&DeliveryProof, DeliveryProofError> {
        let proof = self
            .proofs
            .get(work_id)
            .ok_or_else(|| DeliveryProofError::NotFound(work_id.to_string()))?;
        if proof.executor_peer_id != expected_executor {
            return Err(DeliveryProofError::NotFound(format!(
                "proof exists but executor mismatch for work_id '{work_id}'"
            )));
        }
        Ok(proof)
    }
}

impl Default for DeliveryProofRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_proof(work_id: &str, executor: &str) -> DeliveryProof {
        DeliveryProof {
            work_id: work_id.to_string(),
            executor_peer_id: executor.to_string(),
            delivery_hash: "abc123".to_string(),
            delivered_at: "1700000000".to_string(),
            signature_hex: "deadbeef".to_string(),
        }
    }

    #[test]
    fn register_and_retrieve_proof() {
        let mut reg = DeliveryProofRegistry::new();
        let proof = make_proof("work-1", "executor-A");
        reg.register(proof).expect("registration should succeed");
        let retrieved = reg.get("work-1").expect("proof should be retrievable");
        assert_eq!(retrieved.work_id, "work-1");
        assert_eq!(retrieved.executor_peer_id, "executor-A");
    }

    #[test]
    fn duplicate_registration_rejected() {
        let mut reg = DeliveryProofRegistry::new();
        reg.register(make_proof("work-2", "executor-A"))
            .expect("first registration should succeed");
        let err = reg
            .register(make_proof("work-2", "executor-B"))
            .expect_err("duplicate should be rejected");
        matches!(err, DeliveryProofError::AlreadyRegistered(_));
    }

    #[test]
    fn missing_proof_rejected_at_mint() {
        let reg = DeliveryProofRegistry::new();
        let err = reg
            .verify_for_mint("work-99", "executor-A")
            .expect_err("missing proof must block mint");
        matches!(err, DeliveryProofError::NotFound(_));
    }

    #[test]
    fn wrong_executor_rejected() {
        let mut reg = DeliveryProofRegistry::new();
        reg.register(make_proof("work-3", "executor-A"))
            .expect("registration should succeed");
        let err = reg
            .verify_for_mint("work-3", "executor-B")
            .expect_err("wrong executor must be rejected");
        matches!(err, DeliveryProofError::NotFound(_));
    }
}
