//! Node identity for URACE mesh — peer_id, node_id, stable persistence.
//!
//! Invariants (from CLAUDE.md / runtime/urace/CLAUDE.md):
//! - Node IDs must be cryptographically random — never sequential, never user-supplied
//!   without verification.
//! - `persist_node_identity` is idempotent: creates on first call, returns existing on
//!   subsequent calls.
//! - Writes are atomic (no partial writes).

use rand_core::{CryptoRng, RngCore};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;
use thiserror::Error;
use tracing::info;

/// Errors emitted by mesh identity operations.
#[derive(Debug, Error)]
pub enum IdentityError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON serialization error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("atomic write error: {0}")]
    AtomicWrite(String),
    #[error("identity file missing")]
    Missing,
}

impl From<urace_ledger::atomic_write::AtomicWriteError> for IdentityError {
    fn from(e: urace_ledger::atomic_write::AtomicWriteError) -> Self {
        IdentityError::AtomicWrite(e.to_string())
    }
}

/// Stable node identity for one URACE peer.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NodeIdentity {
    /// UUID v4 — cryptographically random, never sequential.
    pub peer_id: String,
    /// Ed25519 public key (hex-encoded).
    pub public_key_hex: String,
    /// SHA-256 of `peer_id` bytes, hex-encoded.
    pub node_id_hex: String,
    /// ISO-8601 / Unix seconds creation timestamp.
    pub created_at: String,
}

fn now_unix_secs() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string())
}

/// Generate a new NodeIdentity.
///
/// `peer_id` is a UUID v4 built from cryptographically random bytes sourced from `rng`.
/// Never sequential, never user-supplied without verification — hard invariant.
pub fn generate_node_identity<R: RngCore + CryptoRng>(rng: &mut R) -> NodeIdentity {
    // Generate UUID v4 from CSPRNG.
    let mut b = [0u8; 16];
    rng.fill_bytes(&mut b);
    // Set version 4 and variant bits.
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    let peer_id = format!(
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
    );

    // Generate ephemeral Ed25519 keypair for the public_key_hex field.
    let keypair = urace_crypto::Keypair::generate(rng);
    let public_key_hex = hex::encode(keypair.public_key_bytes());

    // node_id_hex = SHA-256(peer_id as UTF-8 bytes).
    let node_id_hex = hex::encode(Sha256::digest(peer_id.as_bytes()));

    NodeIdentity {
        peer_id,
        public_key_hex,
        node_id_hex,
        created_at: now_unix_secs(),
    }
}

/// Idempotently persist a NodeIdentity under `state_dir/node_identity.json`.
///
/// Creates a new identity on first call; returns the existing one on subsequent calls.
/// Writes are atomic (temp-file + rename via `urace_ledger::atomic_write`).
pub fn persist_node_identity<R: RngCore + CryptoRng>(
    state_dir: &Path,
    rng: &mut R,
) -> Result<NodeIdentity, IdentityError> {
    let path = state_dir.join("node_identity.json");

    // If the file already exists, return the stored identity (idempotent).
    if path.exists() {
        return load_node_identity(state_dir);
    }

    std::fs::create_dir_all(state_dir)?;

    let identity = generate_node_identity(rng);
    let json_bytes = serde_json::to_vec_pretty(&identity)?;
    urace_ledger::atomic_write(&path, &json_bytes)?;

    info!(peer_id = %identity.peer_id, "node identity created and persisted");
    Ok(identity)
}

/// Load an existing NodeIdentity from `state_dir/node_identity.json`.
pub fn load_node_identity(state_dir: &Path) -> Result<NodeIdentity, IdentityError> {
    let path = state_dir.join("node_identity.json");
    if !path.exists() {
        return Err(IdentityError::Missing);
    }
    let data = std::fs::read(&path)?;
    let identity: NodeIdentity = serde_json::from_slice(&data)?;
    Ok(identity)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;
    use tempfile::tempdir;

    fn rng() -> StdRng {
        StdRng::seed_from_u64(0)
    }

    #[test]
    fn generate_is_random() {
        let mut r1 = StdRng::seed_from_u64(1);
        let mut r2 = StdRng::seed_from_u64(2);
        let id1 = generate_node_identity(&mut r1);
        let id2 = generate_node_identity(&mut r2);
        assert_ne!(id1.peer_id, id2.peer_id, "peer_ids must differ");
        assert_ne!(id1.node_id_hex, id2.node_id_hex, "node_ids must differ");
    }

    #[test]
    fn node_id_is_sha256_of_peer_id() {
        let mut r = rng();
        let id = generate_node_identity(&mut r);
        let expected = hex::encode(Sha256::digest(id.peer_id.as_bytes()));
        assert_eq!(id.node_id_hex, expected);
    }

    #[test]
    fn persist_idempotent() {
        let dir = tempdir().unwrap();
        let id1 = persist_node_identity(dir.path(), &mut rng()).unwrap();
        let id2 = persist_node_identity(dir.path(), &mut rng()).unwrap();
        assert_eq!(id1, id2, "second call must return same identity");
    }

    #[test]
    fn load_missing_fails() {
        let dir = tempdir().unwrap();
        assert!(matches!(load_node_identity(dir.path()), Err(IdentityError::Missing)));
    }

    #[test]
    fn persist_then_load_roundtrip() {
        let dir = tempdir().unwrap();
        let id = persist_node_identity(dir.path(), &mut rng()).unwrap();
        let loaded = load_node_identity(dir.path()).unwrap();
        assert_eq!(id, loaded);
    }

    #[test]
    fn peer_id_is_uuid_v4_format() {
        let mut r = rng();
        let id = generate_node_identity(&mut r);
        // UUID v4: xxxxxxxx-xxxx-4xxx-[89ab]xxx-xxxxxxxxxxxx
        let parts: Vec<&str> = id.peer_id.split('-').collect();
        assert_eq!(parts.len(), 5);
        assert_eq!(parts[0].len(), 8);
        assert_eq!(parts[1].len(), 4);
        assert_eq!(parts[2].len(), 4);
        assert_eq!(parts[3].len(), 4);
        assert_eq!(parts[4].len(), 12);
        // version nibble = '4'
        assert_eq!(&parts[2][0..1], "4");
        // variant: first hex char of parts[3] must be 8, 9, a, or b
        let variant_char = parts[3].chars().next().unwrap();
        assert!(
            matches!(variant_char, '8' | '9' | 'a' | 'b'),
            "UUID v4 variant nibble must be 8/9/a/b, got {variant_char}"
        );
    }
}
