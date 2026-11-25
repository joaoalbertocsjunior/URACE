//! Session Data Encryption Key (DEK) generation and derivation.
//!
//! Invariants:
//! - DEK must never appear in logs, exceptions, or return values other than
//!   designated sign/export calls.
//! - `Zeroizing` ensures the DEK bytes are wiped from memory when dropped.
//! - HKDF-SHA256 is used for key derivation (RustCrypto `hkdf` crate, Apache 2/MIT).

use hkdf::Hkdf;
use rand_core::{CryptoRng, RngCore};
use sha2::Sha256;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;
use zeroize::Zeroizing;

/// HKDF info string for session DEK derivation — must match across all URACE implementations.
const HKDF_INFO: &[u8] = b"urace-session-dek-v1";

#[derive(Debug, Error)]
pub enum DekError {
    #[error("HKDF expand failed")]
    HkdfExpand,
}

/// A session-scoped Data Encryption Key.
///
/// The inner `dek` bytes are wrapped in `Zeroizing` so they are wiped on drop.
/// `Debug` output deliberately omits the key material — do NOT add it.
pub struct SessionDek {
    pub key_id: String,
    /// 32-byte random DEK. `Zeroizing` wipes on drop.
    pub dek: Zeroizing<[u8; 32]>,
    pub created_at_secs: f64,
}

impl std::fmt::Debug for SessionDek {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SessionDek")
            .field("key_id", &self.key_id)
            .field("dek", &"[REDACTED]")
            .field("created_at_secs", &self.created_at_secs)
            .finish()
    }
}

fn now_secs_f64() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

fn random_key_id<R: RngCore + CryptoRng>(rng: &mut R) -> String {
    let mut b = [0u8; 16];
    rng.fill_bytes(&mut b);
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    format!(
        "{:08x}-{:04x}-{:04x}-{:04x}-{:012x}",
        u32::from_be_bytes([b[0], b[1], b[2], b[3]]),
        u16::from_be_bytes([b[4], b[5]]),
        u16::from_be_bytes([b[6], b[7]]),
        u16::from_be_bytes([b[8], b[9]]),
        {
            let hi = u16::from_be_bytes([b[10], b[11]]) as u64;
            let lo = u32::from_be_bytes([b[12], b[13], b[14], b[15]]) as u64;
            (hi << 32) | lo
        }
    )
}

impl SessionDek {
    /// Generate a fresh 32-byte random DEK from `rng`.
    pub fn generate<R: RngCore + CryptoRng>(rng: &mut R) -> Self {
        let mut dek = Zeroizing::new([0u8; 32]);
        rng.fill_bytes(dek.as_mut());
        SessionDek {
            key_id: random_key_id(rng),
            dek,
            created_at_secs: now_secs_f64(),
        }
    }

    /// Derive a DEK from `master_key` and `session_id` via HKDF-SHA256.
    ///
    /// `salt` = `session_id` bytes
    /// `info` = `b"urace-session-dek-v1"`
    pub fn derive(master_key: &[u8; 32], session_id: &str) -> Result<Self, DekError> {
        let hk = Hkdf::<Sha256>::new(Some(session_id.as_bytes()), master_key);
        let mut dek = Zeroizing::new([0u8; 32]);
        hk.expand(HKDF_INFO, dek.as_mut())
            .map_err(|_| DekError::HkdfExpand)?;

        // key_id = hex of first 8 bytes of the DEK (non-secret identifier).
        let key_id = hex::encode(&dek[..8]);

        Ok(SessionDek {
            key_id,
            dek,
            created_at_secs: now_secs_f64(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    fn rng() -> StdRng {
        StdRng::seed_from_u64(7)
    }

    #[test]
    fn generate_produces_nonzero_dek() {
        let dek = SessionDek::generate(&mut rng());
        assert_ne!(*dek.dek, [0u8; 32], "DEK must not be all-zero");
    }

    #[test]
    fn generate_two_deks_differ() {
        let d1 = SessionDek::generate(&mut StdRng::seed_from_u64(1));
        let d2 = SessionDek::generate(&mut StdRng::seed_from_u64(2));
        assert_ne!(*d1.dek, *d2.dek);
    }

    #[test]
    fn derive_deterministic() {
        let master = b"urace-master-key-32bytes-pad----";
        let d1 = SessionDek::derive(master, "session-abc").unwrap();
        let d2 = SessionDek::derive(master, "session-abc").unwrap();
        assert_eq!(*d1.dek, *d2.dek, "same inputs must yield same DEK");
    }

    #[test]
    fn derive_different_sessions_differ() {
        let master = b"urace-master-key-32bytes-pad----";
        let d1 = SessionDek::derive(master, "session-1").unwrap();
        let d2 = SessionDek::derive(master, "session-2").unwrap();
        assert_ne!(*d1.dek, *d2.dek);
    }

    #[test]
    fn derive_different_masters_differ() {
        let m1 = b"master-key-1-32bytes-padding----";
        let m2 = b"master-key-2-32bytes-padding----";
        let d1 = SessionDek::derive(m1, "session-x").unwrap();
        let d2 = SessionDek::derive(m2, "session-x").unwrap();
        assert_ne!(*d1.dek, *d2.dek);
    }

    #[test]
    fn debug_does_not_leak_dek() {
        let dek = SessionDek::generate(&mut rng());
        let dbg = format!("{dek:?}");
        assert!(
            dbg.contains("REDACTED"),
            "Debug must not expose key material"
        );
        // Confirm the actual key bytes are not in the output.
        let key_hex = hex::encode(*dek.dek);
        assert!(
            !dbg.contains(&key_hex),
            "hex of DEK must not appear in Debug output"
        );
    }
}
