//! HMAC-SHA256 node record signing — mirrors `signed_records.py`.
//!
//! The `seq` field is always included in the signed message; omitting it
//! opens a replay-attack vector (see `signed_records.py` invariant).

use hmac::{Hmac, Mac};
use sha2::Sha256;
use thiserror::Error;
use zeroize::Zeroizing;

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Error)]
pub enum SigningError {
    #[error("HMAC key must be 32 bytes, got {0}")]
    InvalidKeyLength(usize),
    #[error("signature verification failed")]
    InvalidSignature,
}

/// Signed node record — matches `SignedRecord` in `signed_records.py`.
#[derive(Debug, Clone)]
pub struct SignedRecord {
    pub peer_id: String,
    pub payload: Vec<u8>,
    pub seq: u64,
    pub signature: [u8; 32],
    pub signed_at_secs: f64,
}

/// Derive a per-peer subkey: HMAC-SHA256(secret, peer_id).
pub fn derive_key(peer_id: &str, secret: &[u8]) -> Zeroizing<[u8; 32]> {
    let mut mac = HmacSha256::new_from_slice(secret)
        .expect("HMAC accepts any key length");
    mac.update(peer_id.as_bytes());
    let result = mac.finalize().into_bytes();
    let mut out = Zeroizing::new([0u8; 32]);
    out.copy_from_slice(&result);
    out
}

fn message_bytes(peer_id: &str, seq: u64, payload: &[u8]) -> Vec<u8> {
    let mut msg = peer_id.as_bytes().to_vec();
    msg.extend_from_slice(&seq.to_be_bytes());
    msg.extend_from_slice(payload);
    msg
}

/// Sign `payload` with HMAC-SHA256.
pub fn sign(peer_id: &str, payload: &[u8], seq: u64, key: &[u8]) -> SignedRecord {
    let msg = message_bytes(peer_id, seq, payload);
    let mut mac = HmacSha256::new_from_slice(key).expect("valid key");
    mac.update(&msg);
    let sig_bytes = mac.finalize().into_bytes();
    let mut signature = [0u8; 32];
    signature.copy_from_slice(&sig_bytes);

    let signed_at_secs = {
        use std::time::{SystemTime, UNIX_EPOCH};
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    };

    SignedRecord { peer_id: peer_id.to_owned(), payload: payload.to_vec(), seq, signature, signed_at_secs }
}

/// Constant-time HMAC-SHA256 verification. Returns `Err(InvalidSignature)` on mismatch.
pub fn verify(record: &SignedRecord, key: &[u8]) -> Result<(), SigningError> {
    let msg = message_bytes(&record.peer_id, record.seq, &record.payload);
    let mut mac = HmacSha256::new_from_slice(key).expect("valid key");
    mac.update(&msg);
    mac.verify_slice(&record.signature)
        .map_err(|_| SigningError::InvalidSignature)
}

#[cfg(test)]
mod tests {
    use super::*;

    const KEY: &[u8; 32] = b"urace-test-key-32bytes-padding!!";

    #[test]
    fn sign_verify_roundtrip() {
        let record = sign("peer-1", b"hello", 1, KEY);
        assert!(verify(&record, KEY).is_ok());
    }

    #[test]
    fn wrong_key_fails() {
        let record = sign("peer-1", b"hello", 1, KEY);
        let bad_key = b"wrong-key-32bytes-padding-------";
        assert!(matches!(verify(&record, bad_key), Err(SigningError::InvalidSignature)));
    }

    #[test]
    fn seq_mismatch_fails() {
        let mut record = sign("peer-1", b"hello", 1, KEY);
        record.seq = 2; // tamper seq without resigning
        assert!(matches!(verify(&record, KEY), Err(SigningError::InvalidSignature)));
    }

    #[test]
    fn payload_tamper_fails() {
        let mut record = sign("peer-1", b"hello", 1, KEY);
        record.payload[0] ^= 0xFF;
        assert!(matches!(verify(&record, KEY), Err(SigningError::InvalidSignature)));
    }

    #[test]
    fn derive_key_deterministic() {
        let k1 = derive_key("peer-1", KEY);
        let k2 = derive_key("peer-1", KEY);
        assert_eq!(k1.as_ref(), k2.as_ref());
        let k3 = derive_key("peer-2", KEY);
        assert_ne!(k1.as_ref(), k3.as_ref());
    }
}
