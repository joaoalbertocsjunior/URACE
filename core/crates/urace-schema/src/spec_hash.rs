//! M48 — Spec hash pinning.
//!
//! Provides a SHA-256-based `SpecHash` that can be computed from raw bytes or
//! any JSON-serializable spec value, and verified against content or LLM context.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum SpecHashError {
    #[error("spec hash mismatch: expected {expected}, got {actual}")]
    Mismatch { expected: String, actual: String },
    #[error("serialization error: {0}")]
    Serialization(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SpecHash(String); // hex SHA-256

impl SpecHash {
    /// Compute spec hash from spec content bytes.
    pub fn compute(spec_bytes: &[u8]) -> Self {
        let hash = Sha256::digest(spec_bytes);
        SpecHash(hex::encode(hash))
    }

    /// Compute from a JSON-serializable spec value.
    pub fn from_json<T: serde::Serialize>(spec: &T) -> Result<Self, SpecHashError> {
        let bytes = serde_json::to_vec(spec)
            .map_err(|e| SpecHashError::Serialization(e.to_string()))?;
        Ok(Self::compute(&bytes))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Verify that actual content matches this hash.
    pub fn verify(&self, content_bytes: &[u8]) -> Result<(), SpecHashError> {
        let actual = SpecHash::compute(content_bytes);
        if actual != *self {
            return Err(SpecHashError::Mismatch {
                expected: self.0.clone(),
                actual: actual.0,
            });
        }
        Ok(())
    }

    /// Verify LLM context matches expected spec hash.
    pub fn verify_llm_context(&self, context_bytes: &[u8]) -> Result<(), SpecHashError> {
        self.verify(context_bytes)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn compute_is_deterministic() {
        let data = b"governance spec v1.0";
        let h1 = SpecHash::compute(data);
        let h2 = SpecHash::compute(data);
        assert_eq!(h1, h2);
    }

    #[test]
    fn verify_matches() {
        let data = b"spec content";
        let hash = SpecHash::compute(data);
        assert!(hash.verify(data).is_ok());
    }

    #[test]
    fn verify_mismatch_returns_error() {
        let hash = SpecHash::compute(b"original spec");
        let result = hash.verify(b"tampered spec");
        assert!(result.is_err());
        if let Err(SpecHashError::Mismatch { expected, actual }) = result {
            assert_ne!(expected, actual);
        } else {
            panic!("expected Mismatch error");
        }
    }

    #[test]
    fn from_json_works() {
        use serde_json::json;
        let spec = json!({"version": 1, "quorum": 0.66});
        let h1 = SpecHash::from_json(&spec).unwrap();
        let h2 = SpecHash::from_json(&spec).unwrap();
        assert_eq!(h1, h2);
        // Also verify that it matches computing from the serialized bytes
        let bytes = serde_json::to_vec(&spec).unwrap();
        let h3 = SpecHash::compute(&bytes);
        assert_eq!(h1, h3);
    }
}
