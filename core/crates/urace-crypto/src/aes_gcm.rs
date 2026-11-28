//! AES-256-GCM chunk encryption — mirrors `chunk_store.py` per-chunk encryption.
//!
//! Each chunk gets a unique 12-byte nonce. The key is derived from the artifact
//! seed material. Nonce is prepended to ciphertext for storage.
//!
//! For single-use keys (one key per chunk/artifact), `encrypt()` with a random
//! nonce is safe. For long-lived keys that encrypt many payloads use `EncryptingKey`,
//! which eliminates the birthday-bound collision risk by combining a 4-byte random
//! key-prefix with a monotonic 8-byte counter.

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use rand_core::{CryptoRng, RngCore};
use std::sync::atomic::{AtomicU64, Ordering};
use thiserror::Error;
use zeroize::Zeroizing;

pub const KEY_LEN: usize = 32;
pub const NONCE_LEN: usize = 12;
pub const TAG_LEN: usize = 16;

/// Maximum number of encryptions safe under a single key before mandatory rekey.
/// At 2^32 encryptions the counter portion wraps — rekey well before this.
pub const MAX_ENCRYPTIONS_PER_KEY: u64 = u32::MAX as u64;

/// A long-lived AES-256-GCM key paired with a monotonic nonce counter.
///
/// Nonce layout (12 bytes):
///   [0..4]  — 4-byte random prefix, fixed at construction (per-key unique)
///   [4..12] — 8-byte big-endian counter, incremented atomically per encryption
///
/// This eliminates the birthday-bound collision risk of purely random nonces
/// when a single key encrypts many payloads across process restarts.
/// The caller must persist `counter()` to stable storage and pass it to
/// `EncryptingKey::restore()` on restart to ensure cross-session uniqueness.
pub struct EncryptingKey {
    key: [u8; KEY_LEN],
    prefix: [u8; 4],
    counter: AtomicU64,
}

impl EncryptingKey {
    /// Create a new `EncryptingKey` with a fresh random prefix and counter at 0.
    pub fn new<R: RngCore + CryptoRng>(key: [u8; KEY_LEN], rng: &mut R) -> Self {
        let mut prefix = [0u8; 4];
        rng.fill_bytes(&mut prefix);
        EncryptingKey {
            key,
            prefix,
            counter: AtomicU64::new(0),
        }
    }

    /// Restore from a persisted counter value (call on process restart).
    pub fn restore(key: [u8; KEY_LEN], prefix: [u8; 4], counter: u64) -> Self {
        EncryptingKey {
            key,
            prefix,
            counter: AtomicU64::new(counter),
        }
    }

    /// Current counter value — persist this to stable storage for restart safety.
    pub fn counter(&self) -> u64 {
        self.counter.load(Ordering::SeqCst)
    }

    /// The 4-byte prefix — persist alongside the counter.
    pub fn prefix(&self) -> [u8; 4] {
        self.prefix
    }

    /// Encrypt `plaintext`. Returns `nonce || ciphertext || tag`.
    /// Panics if the counter has reached `MAX_ENCRYPTIONS_PER_KEY` — rekey first.
    pub fn encrypt(&self, plaintext: &[u8]) -> Vec<u8> {
        let n = self.counter.fetch_add(1, Ordering::SeqCst);
        assert!(
            n < MAX_ENCRYPTIONS_PER_KEY,
            "EncryptingKey exhausted: rekey before {} encryptions",
            MAX_ENCRYPTIONS_PER_KEY
        );
        let mut nonce_bytes = [0u8; NONCE_LEN];
        nonce_bytes[0..4].copy_from_slice(&self.prefix);
        nonce_bytes[4..12].copy_from_slice(&n.to_be_bytes());

        let cipher = Aes256Gcm::new(&self.key.into());
        let nonce = Nonce::from_slice(&nonce_bytes);
        let ct = cipher
            .encrypt(nonce, plaintext)
            .expect("AES-GCM encryption never fails");
        let mut out = Vec::with_capacity(NONCE_LEN + ct.len());
        out.extend_from_slice(&nonce_bytes);
        out.extend_from_slice(&ct);
        out
    }

    /// Decrypt a blob produced by `EncryptingKey::encrypt`.
    pub fn decrypt_blob(&self, blob: &[u8]) -> Result<Zeroizing<Vec<u8>>, AesGcmError> {
        decrypt(&self.key, blob)
    }
}

#[derive(Debug, Error)]
pub enum AesGcmError {
    #[error("key must be {KEY_LEN} bytes, got {0}")]
    InvalidKeyLength(usize),
    #[error("ciphertext too short to contain nonce+tag")]
    CiphertextTooShort,
    #[error("decryption failed (authentication tag mismatch)")]
    DecryptionFailed,
}

/// Encrypt `plaintext` with `key`. Returns `nonce || ciphertext || tag`.
pub fn encrypt<R: RngCore + CryptoRng>(
    key: &[u8; KEY_LEN],
    plaintext: &[u8],
    rng: &mut R,
) -> Vec<u8> {
    let cipher = Aes256Gcm::new(key.into());
    let mut nonce_bytes = [0u8; NONCE_LEN];
    rng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ct = cipher
        .encrypt(nonce, plaintext)
        .expect("AES-GCM encryption never fails");
    let mut out = Vec::with_capacity(NONCE_LEN + ct.len());
    out.extend_from_slice(&nonce_bytes);
    out.extend_from_slice(&ct);
    out
}

/// Decrypt `nonce || ciphertext || tag` with `key`. Returns plaintext on success.
pub fn decrypt(key: &[u8; KEY_LEN], blob: &[u8]) -> Result<Zeroizing<Vec<u8>>, AesGcmError> {
    if blob.len() < NONCE_LEN + TAG_LEN {
        return Err(AesGcmError::CiphertextTooShort);
    }
    let cipher = Aes256Gcm::new(key.into());
    let nonce = Nonce::from_slice(&blob[..NONCE_LEN]);
    let ct = &blob[NONCE_LEN..];
    cipher
        .decrypt(nonce, ct)
        .map(Zeroizing::new)
        .map_err(|_| AesGcmError::DecryptionFailed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    const KEY: &[u8; KEY_LEN] = b"urace-aes-key-32bytes-padding!!!";

    #[test]
    fn encrypt_decrypt_roundtrip() {
        let mut rng = StdRng::seed_from_u64(42);
        let pt = b"artifact chunk data";
        let blob = encrypt(KEY, pt, &mut rng);
        let recovered = decrypt(KEY, &blob).unwrap();
        assert_eq!(recovered.as_slice(), pt);
    }

    #[test]
    fn encrypting_key_roundtrip() {
        let mut rng = StdRng::seed_from_u64(99);
        let ek = EncryptingKey::new(*KEY, &mut rng);
        let blob = ek.encrypt(b"hello world");
        let pt = ek.decrypt_blob(&blob).unwrap();
        assert_eq!(pt.as_slice(), b"hello world");
    }

    #[test]
    fn encrypting_key_unique_nonces() {
        let mut rng = StdRng::seed_from_u64(7);
        let ek = EncryptingKey::new(*KEY, &mut rng);
        let b1 = ek.encrypt(b"msg1");
        let b2 = ek.encrypt(b"msg1");
        // Same plaintext, different nonces → different ciphertexts
        assert_ne!(&b1[..NONCE_LEN], &b2[..NONCE_LEN]);
        assert_ne!(b1, b2);
        assert_eq!(ek.counter(), 2);
    }

    #[test]
    fn encrypting_key_restore_continues_counter() {
        let mut rng = StdRng::seed_from_u64(3);
        let ek = EncryptingKey::new(*KEY, &mut rng);
        let _ = ek.encrypt(b"a");
        let _ = ek.encrypt(b"b");
        let saved_counter = ek.counter();
        let saved_prefix = ek.prefix();

        // Simulate restart
        let ek2 = EncryptingKey::restore(*KEY, saved_prefix, saved_counter);
        let blob = ek2.encrypt(b"c");
        let pt = ek2.decrypt_blob(&blob).unwrap();
        assert_eq!(pt.as_slice(), b"c");
        // Counter advanced from saved_counter, not 0
        assert_eq!(ek2.counter(), saved_counter + 1);
    }

    #[test]
    fn wrong_key_fails() {
        let mut rng = StdRng::seed_from_u64(42);
        let blob = encrypt(KEY, b"data", &mut rng);
        let bad_key = b"bad-key-32-bytes-of-padding-here";
        assert!(matches!(
            decrypt(bad_key, &blob),
            Err(AesGcmError::DecryptionFailed)
        ));
    }

    #[test]
    fn tampered_ciphertext_fails() {
        let mut rng = StdRng::seed_from_u64(42);
        let mut blob = encrypt(KEY, b"data", &mut rng);
        blob[NONCE_LEN] ^= 0xFF; // flip byte in ciphertext
        assert!(matches!(
            decrypt(KEY, &blob),
            Err(AesGcmError::DecryptionFailed)
        ));
    }
}
