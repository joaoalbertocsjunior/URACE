//! M68 — Multi-party signing threshold.
//!
//! Critical operations require a threshold-of-N signature scheme.
//! Each signer contributes a signature for a payload hash; only once
//! `threshold` distinct signers have contributed is the operation ready.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum MultisigError {
    #[error("signer '{0}' already contributed a signature")]
    DuplicateSigner(String),
    #[error("threshold not yet reached: {got}/{required}")]
    ThresholdNotMet { got: usize, required: usize },
    #[error("operation '{0}' not found")]
    OperationNotFound(String),
}

/// A pending multi-party signing operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MultisigOperation {
    pub operation_id: String,
    /// Hex SHA-256 of the operation payload.
    pub payload_hash: String,
    pub threshold: usize,
    /// signer_peer_id → signature_hex
    pub signatures: HashMap<String, String>,
    pub created_at: String,
}

impl MultisigOperation {
    pub fn new(
        operation_id: impl Into<String>,
        payload_hash: impl Into<String>,
        threshold: usize,
    ) -> Self {
        MultisigOperation {
            operation_id: operation_id.into(),
            payload_hash: payload_hash.into(),
            threshold,
            signatures: HashMap::new(),
            created_at: now_secs_str(),
        }
    }

    /// Add a signature from `signer_peer_id`.
    ///
    /// Returns `Ok(true)` if the threshold is reached after this addition,
    /// `Ok(false)` if not yet reached.  Returns `Err` if the signer already
    /// contributed.
    pub fn add_signature(
        &mut self,
        signer_peer_id: &str,
        signature_hex: &str,
    ) -> Result<bool, MultisigError> {
        if self.signatures.contains_key(signer_peer_id) {
            return Err(MultisigError::DuplicateSigner(signer_peer_id.to_string()));
        }
        self.signatures
            .insert(signer_peer_id.to_string(), signature_hex.to_string());
        Ok(self.threshold_reached())
    }

    /// Returns `true` iff at least `threshold` distinct signers have contributed.
    pub fn threshold_reached(&self) -> bool {
        self.signatures.len() >= self.threshold
    }

    /// Number of signatures collected so far.
    pub fn signature_count(&self) -> usize {
        self.signatures.len()
    }
}

/// Coordinator that tracks multiple in-flight multisig operations.
pub struct MultisigCoordinator {
    operations: HashMap<String, MultisigOperation>,
}

impl MultisigCoordinator {
    pub fn new() -> Self {
        MultisigCoordinator {
            operations: HashMap::new(),
        }
    }

    /// Register a new operation.
    pub fn initiate(&mut self, op: MultisigOperation) {
        self.operations.insert(op.operation_id.clone(), op);
    }

    /// Add a signature contribution for an existing operation.
    ///
    /// Returns `Ok(true)` once threshold is reached.
    pub fn contribute(
        &mut self,
        operation_id: &str,
        signer_peer_id: &str,
        signature_hex: &str,
    ) -> Result<bool, MultisigError> {
        let op = self
            .operations
            .get_mut(operation_id)
            .ok_or_else(|| MultisigError::OperationNotFound(operation_id.to_string()))?;
        op.add_signature(signer_peer_id, signature_hex)
    }

    /// Returns `true` iff the operation exists and its threshold is reached.
    pub fn is_ready(&self, operation_id: &str) -> bool {
        self.operations
            .get(operation_id)
            .map(|op| op.threshold_reached())
            .unwrap_or(false)
    }

    /// Retrieve an operation by id.
    pub fn get(&self, operation_id: &str) -> Option<&MultisigOperation> {
        self.operations.get(operation_id)
    }
}

impl Default for MultisigCoordinator {
    fn default() -> Self {
        Self::new()
    }
}

fn now_secs_str() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dummy_sig(n: u8) -> String {
        hex::encode([n; 64])
    }

    #[test]
    fn threshold_not_reached_with_one_sig() {
        let mut coord = MultisigCoordinator::new();
        let op = MultisigOperation::new("op1", "deadbeef", 3);
        coord.initiate(op);

        let ready = coord.contribute("op1", "peer-a", &dummy_sig(1)).unwrap();
        assert!(!ready, "one sig should not reach threshold=3");
        assert!(!coord.is_ready("op1"));
        assert_eq!(coord.get("op1").unwrap().signature_count(), 1);
    }

    #[test]
    fn threshold_reached_at_exactly_n() {
        let mut coord = MultisigCoordinator::new();
        let op = MultisigOperation::new("op2", "cafebabe", 3);
        coord.initiate(op);

        coord.contribute("op2", "peer-a", &dummy_sig(1)).unwrap();
        coord.contribute("op2", "peer-b", &dummy_sig(2)).unwrap();
        let ready = coord.contribute("op2", "peer-c", &dummy_sig(3)).unwrap();

        assert!(ready, "third sig should reach threshold=3");
        assert!(coord.is_ready("op2"));
        assert_eq!(coord.get("op2").unwrap().signature_count(), 3);
    }

    #[test]
    fn duplicate_signer_rejected() {
        let mut coord = MultisigCoordinator::new();
        let op = MultisigOperation::new("op3", "aabbccdd", 2);
        coord.initiate(op);

        coord.contribute("op3", "peer-a", &dummy_sig(1)).unwrap();
        let err = coord
            .contribute("op3", "peer-a", &dummy_sig(2))
            .unwrap_err();
        assert!(
            matches!(err, MultisigError::DuplicateSigner(ref id) if id == "peer-a"),
            "expected DuplicateSigner for peer-a, got {:?}",
            err
        );
    }

    #[test]
    fn single_sig_threshold_1_works() {
        let mut coord = MultisigCoordinator::new();
        let op = MultisigOperation::new("op4", "11223344", 1);
        coord.initiate(op);

        let ready = coord.contribute("op4", "peer-a", &dummy_sig(1)).unwrap();
        assert!(ready, "one sig must reach threshold=1");
        assert!(coord.is_ready("op4"));
    }
}
