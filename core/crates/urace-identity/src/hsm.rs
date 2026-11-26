//! M80 — HSM (Hardware Security Module) key storage interface.
//!
//! Provides a trait-based abstraction over HSM operations so that:
//! - Signing keys may be stored in hardware and never exported.
//! - Software implementations are available for testing (marked unsafe to use in production).
//!
//! In production, callers must wire a real HSM backend (PKCS#11 or similar).
//! The `SoftwareHsm` here is a test/development stand-in only.

use serde::{Deserialize, Serialize};

/// An HSM-resident key reference (opaque handle — the private key never leaves the HSM).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct HsmKeyHandle(pub String);

/// Error type for HSM operations.
#[derive(Debug, thiserror::Error)]
pub enum HsmError {
    #[error("key not found: {0}")]
    KeyNotFound(String),
    #[error("HSM operation failed: {0}")]
    OperationFailed(String),
    #[error("hardware unavailable — using software fallback is not permitted in production")]
    HardwareUnavailable,
}

/// Trait representing HSM key operations.
///
/// Production implementations should wrap a PKCS#11 token or cloud KMS.
pub trait HsmBackend: Send + Sync {
    /// Generate a new key and return an opaque handle. The private key is never exported.
    fn generate_key(&self, key_id: &str) -> Result<HsmKeyHandle, HsmError>;

    /// Sign `message` bytes using the key identified by `handle`.
    /// Returns the raw signature bytes.
    fn sign(&self, handle: &HsmKeyHandle, message: &[u8]) -> Result<Vec<u8>, HsmError>;

    /// Return the public key (DER or raw bytes) for `handle`.
    fn public_key(&self, handle: &HsmKeyHandle) -> Result<Vec<u8>, HsmError>;

    /// Destroy a key handle permanently.
    fn destroy_key(&self, handle: &HsmKeyHandle) -> Result<(), HsmError>;

    /// Whether this backend is backed by real hardware.
    fn is_hardware(&self) -> bool;
}

/// Software-only HSM — **DO NOT use in production**.
///
/// Stores keys in memory using ed25519-dalek.  This implementation exists solely
/// for unit testing.  `is_hardware()` returns `false` so production guards can
/// reject it.
pub struct SoftwareHsm {
    keys: std::sync::RwLock<std::collections::HashMap<String, [u8; 32]>>,
}

impl SoftwareHsm {
    pub fn new() -> Self {
        SoftwareHsm { keys: std::sync::RwLock::new(std::collections::HashMap::new()) }
    }
}

impl Default for SoftwareHsm {
    fn default() -> Self { Self::new() }
}

impl HsmBackend for SoftwareHsm {
    fn generate_key(&self, key_id: &str) -> Result<HsmKeyHandle, HsmError> {
        use rand::RngCore;
        let mut seed = [0u8; 32];
        rand::thread_rng().fill_bytes(&mut seed);
        self.keys.write().unwrap().insert(key_id.to_owned(), seed);
        Ok(HsmKeyHandle(key_id.to_owned()))
    }

    fn sign(&self, handle: &HsmKeyHandle, message: &[u8]) -> Result<Vec<u8>, HsmError> {
        use sha2::{Digest, Sha256};
        let keys = self.keys.read().unwrap();
        let seed = keys.get(&handle.0).ok_or_else(|| HsmError::KeyNotFound(handle.0.clone()))?;
        // Minimal stub: SHA-256(seed || message) as a fake signature.
        let mut h = Sha256::new();
        h.update(seed);
        h.update(message);
        Ok(h.finalize().to_vec())
    }

    fn public_key(&self, handle: &HsmKeyHandle) -> Result<Vec<u8>, HsmError> {
        let keys = self.keys.read().unwrap();
        let seed = keys.get(&handle.0).ok_or_else(|| HsmError::KeyNotFound(handle.0.clone()))?;
        // Stub: return the seed as a fake "public key" (not real ed25519, but functional for tests).
        Ok(seed.to_vec())
    }

    fn destroy_key(&self, handle: &HsmKeyHandle) -> Result<(), HsmError> {
        self.keys.write().unwrap().remove(&handle.0);
        Ok(())
    }

    fn is_hardware(&self) -> bool { false }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn software_hsm_generate_and_sign() {
        let hsm = SoftwareHsm::new();
        let handle = hsm.generate_key("key-1").unwrap();
        let sig = hsm.sign(&handle, b"test message").unwrap();
        assert_eq!(sig.len(), 32, "stub signature is SHA-256 output = 32 bytes");
    }

    #[test]
    fn software_hsm_not_hardware() {
        let hsm = SoftwareHsm::new();
        let handle = hsm.generate_key("key-hw").unwrap();
        assert!(!hsm.is_hardware());
        let _ = handle;
    }

    #[test]
    fn destroyed_key_returns_error() {
        let hsm = SoftwareHsm::new();
        let handle = hsm.generate_key("key-del").unwrap();
        hsm.destroy_key(&handle).unwrap();
        assert!(matches!(hsm.sign(&handle, b"msg"), Err(HsmError::KeyNotFound(_))));
    }
}
