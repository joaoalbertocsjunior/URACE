//! Erasure-coded encrypted artifact chunk store.
//!
//! Ports `chunk_store.py` store layer. GF(256) arithmetic is provided by
//! `urace-crypto::gf256::GF`. Encryption is AES-256-GCM via
//! `urace-crypto::aes_gcm`.
//!
//! Security model (unchanged from Python):
//!   - Each chunk is AES-256-GCM ciphertext; useless without the per-chunk key.
//!   - Per-chunk keys are derived from `artifact_seed` (caller's private material).
//!   - Replica holders store ciphertext only.
//!   - DEK (master key) released to buyer only after EQUITY_LISTING_FILLED.
//!   - Any k of (k+p) chunks reconstruct the artifact; up to p nodes can be offline.
//!
//! Reed-Solomon over GF(256)/0x11D — systematic (Vandermonde) exactly as in Python.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;
use urace_crypto::aes_gcm as aes;
use urace_crypto::gf256::GF;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ChunkError {
    #[error("encryption failed")]
    EncryptionFailed,
    #[error("decryption failed")]
    DecodeFailed,
    #[error("insufficient chunks: have {have}, need {need}")]
    InsufficientChunks { have: usize, need: usize },
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("singular matrix — insufficient independent chunks")]
    SingularMatrix,
}

// ── EncryptedChunk ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedChunk {
    /// Index within (k + p) chunks.
    pub index: usize,
    /// AES-256-GCM blob: nonce (12) || ciphertext || tag (16).
    pub ciphertext: Vec<u8>,
    /// SHA-256(artifact_sha256_bytes || b":chunk:" || idx as u32 BE) — routing key.
    pub routing_key: [u8; 32],
}

// ── Chunk manifest (stored on disk) ──────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
struct ChunkManifest {
    schema: String,
    artifact_sha256: String,
    artifact_size_bytes: u64,
    n_data: usize,
    n_parity: usize,
    n_total: usize,
    chunk_hashes: Vec<String>,
    chunk_size_bytes: usize,
}

// ── Per-chunk key derivation ───────────────────────────────────────────────────

/// Derive per-chunk AES-256 key: SHA-256(artifact_seed || "chunk" || chunk_idx as u32 BE).
fn chunk_key(artifact_seed: &[u8; 32], chunk_idx: usize) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(artifact_seed);
    h.update(b"chunk");
    h.update((chunk_idx as u32).to_be_bytes());
    h.finalize().into()
}

/// Routing key: SHA-256(artifact_sha256_hex_bytes || b":chunk:" || idx as u32 BE).
fn routing_key(artifact_sha256_hex: &str, idx: usize) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(artifact_sha256_hex.as_bytes());
    h.update(b":chunk:");
    h.update((idx as u32).to_be_bytes());
    h.finalize().into()
}

// ── Reed-Solomon over GF(256) ─────────────────────────────────────────────────
//
// Exactly mirrors the Python `_rs_encode_block` / `_rs_reconstruct_block`.
// Systematic: first k chunks are the data chunks; last p are Vandermonde parity.
// Payload = 8-byte big-endian length header || data || zero-padding to align.

fn rs_encode(data: &[u8], k: usize, p: usize) -> Vec<Vec<u8>> {
    // Prepend 8-byte length header.
    let mut payload = Vec::with_capacity(8 + data.len());
    payload.extend_from_slice(&(data.len() as u64).to_be_bytes());
    payload.extend_from_slice(data);

    // Pad so that payload.len() is divisible by k.
    let rem = payload.len() % k;
    if rem != 0 {
        payload.extend(std::iter::repeat_n(0u8, k - rem));
    }
    let chunk_size = payload.len() / k;

    // Build k data chunks.
    let chunks: Vec<Vec<u8>> = (0..k)
        .map(|i| payload[i * chunk_size..(i + 1) * chunk_size].to_vec())
        .collect();

    // Build p parity chunks (Vandermonde: parity[p_i][pos] = Σ_j α^((p_i+1)*j) * data[j][pos]).
    let mut parity: Vec<Vec<u8>> = vec![vec![0u8; chunk_size]; p];
    for pos in 0..chunk_size {
        for (pi, parity_row) in parity.iter_mut().enumerate().take(p) {
            let mut s: u8 = 0;
            for (j, chunk_row) in chunks.iter().enumerate().take(k) {
                let coeff = GF.pow(2, (pi + 1) * j);
                s ^= GF.mul(coeff, chunk_row[pos]);
            }
            parity_row[pos] = s;
        }
    }

    let mut result = chunks;
    result.extend(parity);
    result
}

fn rs_decode(
    available: &HashMap<usize, Vec<u8>>,
    k: usize,
    _p: usize,
) -> Result<Vec<u8>, ChunkError> {
    if available.len() < k {
        return Err(ChunkError::InsufficientChunks {
            have: available.len(),
            need: k,
        });
    }

    // Pick the first k available indices.
    let mut indices: Vec<usize> = available.keys().copied().collect();
    indices.sort_unstable();
    let indices = &indices[..k];

    let chunk_size = available[&indices[0]].len();

    // Fast path: all k data chunks are present.
    if indices.iter().copied().eq(0..k) {
        let raw: Vec<u8> = (0..k).flat_map(|i| available[&i].iter().copied()).collect();
        return extract_payload(raw);
    }

    // Gaussian elimination in GF(256).
    // matrix[row] = [a_{row,0}, ..., a_{row,k-1}]  (k × k)
    // rhs[row]    = chunk_data  (chunk_size bytes)
    let mut matrix: Vec<Vec<u8>> = indices
        .iter()
        .map(|&idx| {
            if idx < k {
                // Identity row for data chunk.
                let mut row = vec![0u8; k];
                row[idx] = 1;
                row
            } else {
                // Vandermonde row: a[j] = α^((idx - k + 1)*j)
                let pi = idx - k + 1;
                (0..k).map(|j| GF.pow(2, pi * j)).collect()
            }
        })
        .collect();

    let mut rhs: Vec<Vec<u8>> = indices.iter().map(|idx| available[idx].clone()).collect();

    // RREF in GF(256).
    for col in 0..k {
        // Find pivot.
        let pivot = (col..k)
            .find(|&row| matrix[row][col] != 0)
            .ok_or(ChunkError::SingularMatrix)?;
        if pivot != col {
            matrix.swap(col, pivot);
            rhs.swap(col, pivot);
        }
        // Scale row so matrix[col][col] == 1.
        let inv = GF.inv(matrix[col][col]);
        for v in matrix[col].iter_mut() {
            *v = GF.mul(*v, inv);
        }
        for b in rhs[col].iter_mut() {
            *b = GF.mul(*b, inv);
        }
        // Eliminate column in other rows.
        for row in 0..k {
            if row == col {
                continue;
            }
            let factor = matrix[row][col];
            if factor == 0 {
                continue;
            }
            #[allow(clippy::needless_range_loop)]
            for c in 0..k {
                let m = GF.mul(factor, matrix[col][c]);
                matrix[row][c] ^= m;
            }
            #[allow(clippy::needless_range_loop)]
            for pos in 0..chunk_size {
                let m = GF.mul(factor, rhs[col][pos]);
                rhs[row][pos] ^= m;
            }
        }
    }

    let raw: Vec<u8> = (0..k).flat_map(|i| rhs[i].iter().copied()).collect();
    extract_payload(raw)
}

fn extract_payload(raw: Vec<u8>) -> Result<Vec<u8>, ChunkError> {
    if raw.len() < 8 {
        return Err(ChunkError::DecodeFailed);
    }
    let orig_len = u64::from_be_bytes(raw[..8].try_into().unwrap()) as usize;
    if orig_len > raw.len() - 8 {
        return Err(ChunkError::DecodeFailed);
    }
    Ok(raw[8..8 + orig_len].to_vec())
}

// ── ChunkStore ────────────────────────────────────────────────────────────────

/// Manages encrypted erasure-coded chunks in a directory.
///
/// Storage layout:
///   `<root>/bundle-chunks/<sha256[:2]>/<sha256>/chunk-NNN.bin`
///   `<root>/bundle-chunks/<sha256[:2]>/<sha256>/manifest.json`
pub struct ChunkStore {
    root: PathBuf,
}

impl ChunkStore {
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
        }
    }

    fn chunk_dir(&self, artifact_sha256: &str) -> PathBuf {
        self.root
            .join("bundle-chunks")
            .join(&artifact_sha256[..2])
            .join(artifact_sha256)
    }

    fn manifest_path(&self, artifact_sha256: &str) -> PathBuf {
        self.chunk_dir(artifact_sha256).join("manifest.json")
    }

    /// Encode, encrypt, and store an artifact.
    ///
    /// Returns `Vec<EncryptedChunk>` where each entry carries `index`, `ciphertext`,
    /// and `routing_key`.
    pub fn encode(
        &self,
        artifact_seed: &[u8; 32],
        data: &[u8],
        k: usize,
        p: usize,
    ) -> Result<Vec<EncryptedChunk>, ChunkError> {
        let artifact_sha256 = hex::encode(Sha256::digest(data));
        let raw_chunks = rs_encode(data, k, p);
        let chunk_dir = self.chunk_dir(&artifact_sha256);
        std::fs::create_dir_all(&chunk_dir)?;

        let mut encrypted_chunks = Vec::with_capacity(raw_chunks.len());
        let mut chunk_hashes = Vec::with_capacity(raw_chunks.len());

        let chunk_size = raw_chunks[0].len();

        for (idx, chunk_data) in raw_chunks.iter().enumerate() {
            let key = chunk_key(artifact_seed, idx);
            let blob = aes::encrypt(&key, chunk_data, &mut OsRng);
            let hash = hex::encode(Sha256::digest(&blob));
            chunk_hashes.push(hash);

            let cpath = chunk_dir.join(format!("chunk-{idx:03}.bin"));
            std::fs::write(&cpath, &blob)?;

            encrypted_chunks.push(EncryptedChunk {
                index: idx,
                ciphertext: blob,
                routing_key: routing_key(&artifact_sha256, idx),
            });
        }

        let manifest = ChunkManifest {
            schema: "urace-chunk-manifest-v1".into(),
            artifact_sha256: artifact_sha256.clone(),
            artifact_size_bytes: data.len() as u64,
            n_data: k,
            n_parity: p,
            n_total: k + p,
            chunk_hashes,
            chunk_size_bytes: chunk_size,
        };
        let manifest_json = serde_json::to_vec_pretty(&manifest)?;
        std::fs::write(self.manifest_path(&artifact_sha256), &manifest_json)?;

        Ok(encrypted_chunks)
    }

    /// Decrypt and Reed-Solomon reconstruct from any k of n `chunks`.
    pub fn decode(
        &self,
        artifact_seed: &[u8; 32],
        chunks: &[EncryptedChunk],
        k: usize,
    ) -> Result<Vec<u8>, ChunkError> {
        if chunks.len() < k {
            return Err(ChunkError::InsufficientChunks {
                have: chunks.len(),
                need: k,
            });
        }
        let mut available: HashMap<usize, Vec<u8>> = HashMap::new();
        for chunk in chunks {
            let key = chunk_key(artifact_seed, chunk.index);
            let pt = aes::decrypt(&key, &chunk.ciphertext).map_err(|_| ChunkError::DecodeFailed)?;
            available.insert(chunk.index, pt.to_vec());
        }
        // Determine p from manifest if present (best effort — 0 is safe for decode).
        let p = 0;
        rs_decode(&available, k, p)
    }

    /// Store a received encrypted chunk from a peer (verifies integrity hash).
    pub fn store_chunk(
        &self,
        artifact_sha256: &str,
        chunk_idx: usize,
        encrypted_chunk: &[u8],
        manifest_json: &str,
    ) -> Result<(), ChunkError> {
        let manifest: ChunkManifest = serde_json::from_str(manifest_json)?;
        let expected = &manifest.chunk_hashes[chunk_idx];
        let actual = hex::encode(Sha256::digest(encrypted_chunk));
        if actual != *expected {
            return Err(ChunkError::DecodeFailed);
        }
        let chunk_dir = self.chunk_dir(artifact_sha256);
        std::fs::create_dir_all(&chunk_dir)?;
        let mp = self.manifest_path(artifact_sha256);
        if !mp.exists() {
            std::fs::write(&mp, manifest_json.as_bytes())?;
        }
        let cpath = chunk_dir.join(format!("chunk-{chunk_idx:03}.bin"));
        if !cpath.exists() {
            std::fs::write(cpath, encrypted_chunk)?;
        }
        Ok(())
    }

    /// Load and reconstruct an artifact from locally stored chunks.
    ///
    /// Returns `None` if the manifest is missing or insufficient chunks are present.
    pub fn load(
        &self,
        artifact_sha256: &str,
        artifact_seed: &[u8; 32],
    ) -> Result<Option<Vec<u8>>, ChunkError> {
        let mp = self.manifest_path(artifact_sha256);
        if !mp.exists() {
            return Ok(None);
        }
        let manifest: ChunkManifest = serde_json::from_str(&std::fs::read_to_string(&mp)?)?;
        let chunk_dir = self.chunk_dir(artifact_sha256);
        let mut available: HashMap<usize, Vec<u8>> = HashMap::new();
        for i in 0..manifest.n_total {
            let cpath = chunk_dir.join(format!("chunk-{i:03}.bin"));
            if cpath.exists() {
                if let Ok(blob) = std::fs::read(&cpath) {
                    let key = chunk_key(artifact_seed, i);
                    if let Ok(pt) = aes::decrypt(&key, &blob) {
                        available.insert(i, pt.to_vec());
                    }
                }
            }
        }
        if available.len() < manifest.n_data {
            return Ok(None);
        }
        rs_decode(&available, manifest.n_data, manifest.n_parity).map(Some)
    }

    /// Return list of locally held chunk indices.
    pub fn has_chunks(&self, artifact_sha256: &str) -> Vec<usize> {
        let mp = self.manifest_path(artifact_sha256);
        if !mp.exists() {
            return vec![];
        }
        let Ok(text) = std::fs::read_to_string(&mp) else {
            return vec![];
        };
        let Ok(manifest): Result<ChunkManifest, _> = serde_json::from_str(&text) else {
            return vec![];
        };
        let chunk_dir = self.chunk_dir(artifact_sha256);
        (0..manifest.n_total)
            .filter(|&i| chunk_dir.join(format!("chunk-{i:03}.bin")).exists())
            .collect()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    const TEST_SEED: &[u8; 32] = b"artifact-seed-32bytes-padding!!!";

    #[test]
    fn rs_encode_decode_all_data_chunks() {
        let data = b"hello world from URACE artifact store";
        let k = 4;
        let p = 2;
        let chunks = rs_encode(data, k, p);
        assert_eq!(chunks.len(), k + p);
        // Use only data chunks.
        let avail: HashMap<usize, Vec<u8>> = (0..k).map(|i| (i, chunks[i].clone())).collect();
        let recovered = rs_decode(&avail, k, p).unwrap();
        assert_eq!(recovered, data);
    }

    #[test]
    fn rs_decode_with_parity_substitution() {
        let data = b"test erasure coding with parity recovery";
        let k = 4;
        let p = 2;
        let chunks = rs_encode(data, k, p);
        // Drop first two data chunks, use parity to recover.
        let avail: HashMap<usize, Vec<u8>> = [
            (2, chunks[2].clone()),
            (3, chunks[3].clone()),
            (4, chunks[4].clone()),
            (5, chunks[5].clone()),
        ]
        .into_iter()
        .collect();
        let recovered = rs_decode(&avail, k, p).unwrap();
        assert_eq!(recovered, data);
    }

    #[test]
    fn chunk_key_derivation_deterministic() {
        let k1 = chunk_key(TEST_SEED, 0);
        let k2 = chunk_key(TEST_SEED, 0);
        assert_eq!(k1, k2);
        // Different index → different key.
        let k3 = chunk_key(TEST_SEED, 1);
        assert_ne!(k1, k3);
    }

    #[test]
    fn routing_key_deterministic() {
        let sha = "abcdef0123456789";
        let r1 = routing_key(sha, 0);
        let r2 = routing_key(sha, 0);
        assert_eq!(r1, r2);
        let r3 = routing_key(sha, 1);
        assert_ne!(r1, r3);
    }

    #[test]
    fn chunk_store_encode_decode_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let store = ChunkStore::new(dir.path());
        let data = b"URACE chunk store encrypt and recover test payload data";
        let chunks = store.encode(TEST_SEED, data, 4, 2).unwrap();
        assert_eq!(chunks.len(), 6);
        let recovered = store.decode(TEST_SEED, &chunks, 4).unwrap();
        assert_eq!(recovered, data);
    }

    #[test]
    fn chunk_store_load_from_disk() {
        let dir = tempfile::tempdir().unwrap();
        let store = ChunkStore::new(dir.path());
        let data = b"persist and reload chunks from disk";
        store.encode(TEST_SEED, data, 4, 2).unwrap();
        let sha = hex::encode(Sha256::digest(data));
        let recovered = store.load(&sha, TEST_SEED).unwrap().unwrap();
        assert_eq!(recovered, data);
    }

    #[test]
    fn insufficient_chunks_error() {
        let seed = TEST_SEED;
        let chunks: Vec<EncryptedChunk> = vec![EncryptedChunk {
            index: 0,
            ciphertext: vec![0u8; 28],
            routing_key: [0u8; 32],
        }];
        let dir = tempfile::tempdir().unwrap();
        let store = ChunkStore::new(dir.path());
        let result = store.decode(seed, &chunks, 4);
        assert!(matches!(
            result,
            Err(ChunkError::InsufficientChunks { have: 1, need: 4 })
        ));
    }
}
