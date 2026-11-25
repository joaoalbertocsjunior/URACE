//! AES-256-GCM chunk encryption — mirrors `chunk_store.py` per-chunk encryption.
//!
//! Each chunk gets a unique 12-byte nonce. The key is derived from the artifact
//! seed material. Nonce is prepended to ciphertext for storage.

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use rand_core::{CryptoRng, RngCore};
use thiserror::Error;
use zeroize::Zeroizing;

pub const KEY_LEN: usize = 32;
pub const NONCE_LEN: usize = 12;
pub const TAG_LEN: usize = 16;

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
