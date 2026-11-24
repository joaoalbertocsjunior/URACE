//! Key rotation and lifecycle management.
//!
//! Invariants (from CLAUDE.md / runtime/urace/CLAUDE.md):
//! - Key rotation MUST invalidate old signatures; `is_valid_key` returns false for Rotated/Revoked.
//! - Key storage MUST NOT be plaintext — AES-256-GCM via `urace-crypto::aes_gcm` for persistent export.
//! - `except Exception: pass` / silent swallowing is forbidden on this path.

use parking_lot::RwLock;
use rand_core::{CryptoRng, RngCore};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use tracing::{info, warn};
use urace_crypto::{aes_decrypt, aes_encrypt, Keypair};
use zeroize::Zeroizing;

/// Errors emitted by KeyStore operations.
#[derive(Debug, Error)]
pub enum KeyError {
    #[error("key not found: {0}")]
    NotFound(String),
    #[error("key already revoked: {0}")]
    AlreadyRevoked(String),
    #[error("key is not active (already rotated or revoked): {0}")]
    NotActive(String),
    #[error("AES-GCM decryption failed — wrong encryption key or corrupt blob")]
    DecryptionFailed,
    #[error("serialization error: {0}")]
    Serialization(String),
    #[error("invalid key seed length in blob")]
    InvalidSeedLength,
}

/// Lifecycle state of a managed key.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "state")]
pub enum KeyState {
    Active,
    Rotated { rotated_at: String },
    Revoked { revoked_at: String },
}

/// A record describing one managed Ed25519 keypair.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyRecord {
    pub key_id: String,
    pub public_key_hex: String,
    pub state: KeyState,
    pub created_at: String,
}

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{secs}")
}

fn new_uuid() -> String {
    use rand::Rng;
    // Generate a UUID v4-shaped string using random bytes.
    let mut rng = rand::thread_rng();
    let b: [u8; 16] = rng.gen();
    format!(
        "{:08x}-{:04x}-{:04x}-{:04x}-{:012x}",
        u32::from_be_bytes([b[0], b[1], b[2], b[3]]),
        u16::from_be_bytes([b[4], b[5]]),
        (u16::from_be_bytes([b[6], b[7]]) & 0x0fff) | 0x4000,
        (u16::from_be_bytes([b[8], b[9]]) & 0x3fff) | 0x8000,
        {
            let hi = u16::from_be_bytes([b[10], b[11]]) as u64;
            let lo = u32::from_be_bytes([b[12], b[13], b[14], b[15]]) as u64;
            (hi << 32) | lo
        }
    )
}

/// In-memory key store.  Keypairs are stored in memory; persistent export is always encrypted.
pub struct KeyStore {
    // Maps key_id → (KeyRecord, Keypair)
    store: RwLock<HashMap<String, (KeyRecord, Keypair)>>,
}

impl Default for KeyStore {
    fn default() -> Self {
        Self::new()
    }
}

impl KeyStore {
    pub fn new() -> Self {
        KeyStore { store: RwLock::new(HashMap::new()) }
    }

    /// Generate a fresh Ed25519 keypair, record it as Active, return the KeyRecord.
    pub fn generate<R: RngCore + CryptoRng>(&self, rng: &mut R) -> KeyRecord {
        let keypair = Keypair::generate(rng);
        let key_id = new_uuid();
        let public_key_hex = hex::encode(keypair.public_key_bytes());
        let record = KeyRecord {
            key_id: key_id.clone(),
            public_key_hex,
            state: KeyState::Active,
            created_at: now_iso(),
        };
        self.store.write().insert(key_id.clone(), (record.clone(), keypair));
        info!(key_id = %key_id, "key generated");
        record
    }

    /// Rotate a key: mark old key Rotated, generate a new Active key.
    /// Returns the new KeyRecord.
    /// Old signatures become invalid — `is_valid_key(old_key_id)` will return false.
    pub fn rotate<R: RngCore + CryptoRng>(
        &self,
        key_id: &str,
        rng: &mut R,
    ) -> Result<KeyRecord, KeyError> {
        let new_record = {
            let mut guard = self.store.write();
            let (record, _keypair) = guard
                .get_mut(key_id)
                .ok_or_else(|| KeyError::NotFound(key_id.to_string()))?;

            match &record.state {
                KeyState::Active => {}
                KeyState::Revoked { .. } => {
                    return Err(KeyError::AlreadyRevoked(key_id.to_string()));
                }
                KeyState::Rotated { .. } => {
                    return Err(KeyError::NotActive(key_id.to_string()));
                }
            }

            record.state = KeyState::Rotated { rotated_at: now_iso() };
            info!(old_key_id = %key_id, "key rotated — old signatures invalidated");

            // Generate new keypair inside the write lock so there's no race.
            let new_keypair = Keypair::generate(rng);
            let new_key_id = new_uuid();
            let new_public_key_hex = hex::encode(new_keypair.public_key_bytes());
            let new_rec = KeyRecord {
                key_id: new_key_id.clone(),
                public_key_hex: new_public_key_hex,
                state: KeyState::Active,
                created_at: now_iso(),
            };
            guard.insert(new_key_id, (new_rec.clone(), new_keypair));
            new_rec
        };
        Ok(new_record)
    }

    /// Revoke a key — it can no longer be used for signing or export.
    pub fn revoke(&self, key_id: &str) -> Result<(), KeyError> {
        let mut guard = self.store.write();
        let (record, _keypair) = guard
            .get_mut(key_id)
            .ok_or_else(|| KeyError::NotFound(key_id.to_string()))?;

        match &record.state {
            KeyState::Revoked { .. } => {
                return Err(KeyError::AlreadyRevoked(key_id.to_string()));
            }
            _ => {}
        }
        record.state = KeyState::Revoked { revoked_at: now_iso() };
        warn!(key_id = %key_id, "key revoked");
        Ok(())
    }

    /// Returns true only for Active keys — Rotated and Revoked keys always return false.
    pub fn is_valid_key(&self, key_id: &str) -> bool {
        let guard = self.store.read();
        guard
            .get(key_id)
            .map(|(rec, _)| matches!(rec.state, KeyState::Active))
            .unwrap_or(false)
    }

    /// Export the Ed25519 seed of `key_id`, AES-256-GCM encrypted with `encryption_key`.
    /// Format: `nonce(12) || ciphertext(32) || tag(16)` — produced by `urace_crypto::aes_encrypt`.
    pub fn export_encrypted<R: RngCore + CryptoRng>(
        &self,
        key_id: &str,
        encryption_key: &[u8; 32],
        rng: &mut R,
    ) -> Result<Vec<u8>, KeyError> {
        let guard = self.store.read();
        let (record, keypair) = guard
            .get(key_id)
            .ok_or_else(|| KeyError::NotFound(key_id.to_string()))?;

        match &record.state {
            KeyState::Revoked { .. } => {
                return Err(KeyError::AlreadyRevoked(key_id.to_string()));
            }
            _ => {}
        }

        let seed: Zeroizing<[u8; 32]> = keypair.to_seed();
        let blob = aes_encrypt(encryption_key, seed.as_ref(), rng);
        Ok(blob)
    }

    /// Import an encrypted key blob produced by `export_encrypted`.
    /// Decrypts, reconstructs the keypair, registers it as Active.
    pub fn import_encrypted<R: RngCore + CryptoRng>(
        &self,
        blob: &[u8],
        encryption_key: &[u8; 32],
        rng: &mut R,
    ) -> Result<KeyRecord, KeyError> {
        let plaintext = aes_decrypt(encryption_key, blob)
            .map_err(|_| KeyError::DecryptionFailed)?;

        if plaintext.len() != 32 {
            return Err(KeyError::InvalidSeedLength);
        }

        let mut seed = Zeroizing::new([0u8; 32]);
        seed.copy_from_slice(&plaintext);
        let _ = rng; // rng not needed for deterministic import, kept for API symmetry

        let keypair = Keypair::from_seed(&seed);
        let key_id = new_uuid();
        let public_key_hex = hex::encode(keypair.public_key_bytes());
        let record = KeyRecord {
            key_id: key_id.clone(),
            public_key_hex,
            state: KeyState::Active,
            created_at: now_iso(),
        };
        self.store.write().insert(key_id.clone(), (record.clone(), keypair));
        info!(key_id = %key_id, "key imported from encrypted blob");
        Ok(record)
    }

    /// Retrieve a copy of a KeyRecord (without the private key).
    pub fn get(&self, key_id: &str) -> Option<KeyRecord> {
        self.store.read().get(key_id).map(|(r, _)| r.clone())
    }

    /// Sign `msg` with the key identified by `key_id`.  Requires Active state.
    pub fn sign(&self, key_id: &str, msg: &[u8]) -> Result<[u8; 64], KeyError> {
        let guard = self.store.read();
        let (record, keypair) = guard
            .get(key_id)
            .ok_or_else(|| KeyError::NotFound(key_id.to_string()))?;
        if !matches!(record.state, KeyState::Active) {
            return Err(KeyError::NotActive(key_id.to_string()));
        }
        Ok(keypair.sign(msg))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    fn rng() -> StdRng {
        StdRng::seed_from_u64(42)
    }

    #[test]
    fn generate_and_valid() {
        let store = KeyStore::new();
        let rec = store.generate(&mut rng());
        assert!(store.is_valid_key(&rec.key_id));
        assert!(matches!(rec.state, KeyState::Active));
    }

    #[test]
    fn rotate_invalidates_old_key() {
        let store = KeyStore::new();
        let old = store.generate(&mut rng());
        let new = store.rotate(&old.key_id, &mut rng()).unwrap();

        // Old key must be invalid after rotation.
        assert!(!store.is_valid_key(&old.key_id));
        // New key must be valid.
        assert!(store.is_valid_key(&new.key_id));

        let old_rec = store.get(&old.key_id).unwrap();
        assert!(matches!(old_rec.state, KeyState::Rotated { .. }));
    }

    #[test]
    fn rotate_twice_on_same_key_fails() {
        let store = KeyStore::new();
        let old = store.generate(&mut rng());
        store.rotate(&old.key_id, &mut rng()).unwrap();
        let err = store.rotate(&old.key_id, &mut rng()).unwrap_err();
        assert!(matches!(err, KeyError::NotActive(_)));
    }

    #[test]
    fn revoke_invalidates_key() {
        let store = KeyStore::new();
        let rec = store.generate(&mut rng());
        store.revoke(&rec.key_id).unwrap();
        assert!(!store.is_valid_key(&rec.key_id));
    }

    #[test]
    fn revoke_already_revoked_fails() {
        let store = KeyStore::new();
        let rec = store.generate(&mut rng());
        store.revoke(&rec.key_id).unwrap();
        assert!(matches!(store.revoke(&rec.key_id), Err(KeyError::AlreadyRevoked(_))));
    }

    #[test]
    fn export_import_roundtrip() {
        let store = KeyStore::new();
        let enc_key = b"urace-test-enc-key-32bytes-pad!!";
        let old = store.generate(&mut rng());

        let blob = store.export_encrypted(&old.key_id, enc_key, &mut rng()).unwrap();
        let new_rec = store.import_encrypted(&blob, enc_key, &mut rng()).unwrap();

        // Both should produce the same public key.
        assert_eq!(old.public_key_hex, new_rec.public_key_hex);
    }

    #[test]
    fn export_wrong_key_fails() {
        let store = KeyStore::new();
        let rec = store.generate(&mut rng());
        let enc_key = b"urace-test-enc-key-32bytes-pad!!";
        let blob = store.export_encrypted(&rec.key_id, enc_key, &mut rng()).unwrap();

        let bad_key = b"bad-enc-key-32bytes-padding-here";
        assert!(matches!(
            store.import_encrypted(&blob, bad_key, &mut rng()),
            Err(KeyError::DecryptionFailed)
        ));
    }

    #[test]
    fn sign_rotated_key_fails() {
        let store = KeyStore::new();
        let old = store.generate(&mut rng());
        store.rotate(&old.key_id, &mut rng()).unwrap();
        assert!(matches!(store.sign(&old.key_id, b"msg"), Err(KeyError::NotActive(_))));
    }

    #[test]
    fn not_found_error() {
        let store = KeyStore::new();
        assert!(matches!(store.rotate("nonexistent", &mut rng()), Err(KeyError::NotFound(_))));
        assert!(matches!(store.revoke("nonexistent"), Err(KeyError::NotFound(_))));
    }
}
