//! High-level artifact store — wraps ChunkStore with artifact-level metadata.
//!
//! Each stored artifact produces an `ArtifactMeta` and is content-addressed by
//! SHA-256. Retrieval requires a DEK file (`{artifact_id}.dek`) to be present —
//! this is the buyer-only access control model from the Python implementation.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

use crate::chunk_store::{ChunkError, ChunkStore};

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ArtifactError {
    #[error("chunk operation failed: {0}")]
    ChunkError(#[from] ChunkError),
    #[error("DEK file not released for artifact {0}")]
    DekNotReleased(String),
    #[error("artifact not found: {0}")]
    NotFound(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}

// ── ArtifactMeta ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactMeta {
    pub artifact_id: String,
    pub sha256: String,
    pub size_bytes: u64,
    pub k: usize,
    pub p: usize,
    pub chunk_count: usize,
    pub created_at: String,
}

// ── ArtifactStore ─────────────────────────────────────────────────────────────

/// Artifact store — stores and retrieves artifacts via the erasure-coded ChunkStore.
///
/// DEK access control: `retrieve` requires `{artifact_id}.dek` present in the
/// store root (released to buyer only after EQUITY_LISTING_FILLED in economy ledger).
pub struct ArtifactStore {
    root: PathBuf,
    chunk_store: ChunkStore,
}

impl ArtifactStore {
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            chunk_store: ChunkStore::new(root),
        }
    }

    fn meta_path(&self, artifact_id: &str) -> PathBuf {
        self.root.join("artifact-meta").join(format!("{artifact_id}.json"))
    }

    fn dek_path(&self, artifact_id: &str) -> PathBuf {
        self.root.join(format!("{artifact_id}.dek"))
    }

    /// Store `data` as an artifact.
    ///
    /// `artifact_seed` is the caller's private 32-byte material (never stored).
    /// Returns `ArtifactMeta` including the content-addressed `artifact_id`.
    pub fn store(
        &self,
        data: &[u8],
        artifact_seed: &[u8; 32],
        k: usize,
        p: usize,
    ) -> Result<ArtifactMeta, ArtifactError> {
        let sha256 = hex::encode(Sha256::digest(data));
        let artifact_id = sha256.clone();

        let meta_path = self.meta_path(&artifact_id);
        if meta_path.exists() {
            // Idempotent — return existing meta.
            let existing: ArtifactMeta = serde_json::from_str(&std::fs::read_to_string(&meta_path)?)?;
            return Ok(existing);
        }

        let chunks = self.chunk_store.encode(artifact_seed, data, k, p)?;
        let chunk_count = chunks.len();

        std::fs::create_dir_all(meta_path.parent().unwrap())?;
        let meta = ArtifactMeta {
            artifact_id: artifact_id.clone(),
            sha256,
            size_bytes: data.len() as u64,
            k,
            p,
            chunk_count,
            created_at: now_iso(),
        };
        let meta_json = serde_json::to_string_pretty(&meta)?;
        std::fs::write(&meta_path, meta_json.as_bytes())?;

        Ok(meta)
    }

    /// Retrieve an artifact by `artifact_id`.
    ///
    /// Returns `Err(DekNotReleased)` if `{artifact_id}.dek` is not present.
    pub fn retrieve(
        &self,
        artifact_id: &str,
        artifact_seed: &[u8; 32],
    ) -> Result<Vec<u8>, ArtifactError> {
        // DEK gate — buyer-only access control model.
        if !self.dek_path(artifact_id).exists() {
            return Err(ArtifactError::DekNotReleased(artifact_id.to_owned()));
        }

        let meta_path = self.meta_path(artifact_id);
        if !meta_path.exists() {
            return Err(ArtifactError::NotFound(artifact_id.to_owned()));
        }

        self.chunk_store
            .load(artifact_id, artifact_seed)?
            .ok_or_else(|| ArtifactError::NotFound(artifact_id.to_owned()))
    }

    /// Check whether metadata for `artifact_id` exists.
    pub fn exists(&self, artifact_id: &str) -> bool {
        self.meta_path(artifact_id).exists()
    }

    /// Return `ArtifactMeta` without decrypting.
    pub fn meta(&self, artifact_id: &str) -> Result<ArtifactMeta, ArtifactError> {
        let path = self.meta_path(artifact_id);
        if !path.exists() {
            return Err(ArtifactError::NotFound(artifact_id.to_owned()));
        }
        let m: ArtifactMeta = serde_json::from_str(&std::fs::read_to_string(&path)?)?;
        Ok(m)
    }
}

fn now_iso() -> String {
    // RFC 3339 UTC timestamp — no chrono dep; use std time.
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Format as YYYY-MM-DDTHH:MM:SSZ
    let (y, mo, d, h, mi, s) = epoch_to_parts(secs);
    format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

fn epoch_to_parts(mut secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    let s = secs % 60; secs /= 60;
    let mi = secs % 60; secs /= 60;
    let h = secs % 24; secs /= 24;
    // Days since 1970-01-01.
    let mut days = secs;
    let mut y = 1970u64;
    loop {
        let dy = if is_leap(y) { 366 } else { 365 };
        if days < dy { break; }
        days -= dy;
        y += 1;
    }
    let months = [31u64, if is_leap(y) { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let mut mo = 1u64;
    for dm in &months {
        if days < *dm { break; }
        days -= dm;
        mo += 1;
    }
    (y, mo, days + 1, h, mi, s)
}

fn is_leap(y: u64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || y % 400 == 0
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    const SEED: &[u8; 32] = b"artifact-store-seed-32-bytes!!!!";

    #[test]
    fn store_and_meta() {
        let dir = tempfile::tempdir().unwrap();
        let store = ArtifactStore::new(dir.path());
        let data = b"artifact store test data";
        let meta = store.store(data, SEED, 4, 2).unwrap();
        assert_eq!(meta.size_bytes, data.len() as u64);
        assert_eq!(meta.k, 4);
        assert_eq!(meta.p, 2);
        assert_eq!(meta.chunk_count, 6);
        assert!(store.exists(&meta.artifact_id));
    }

    #[test]
    fn retrieve_without_dek_fails() {
        let dir = tempfile::tempdir().unwrap();
        let store = ArtifactStore::new(dir.path());
        let data = b"secret artifact";
        let meta = store.store(data, SEED, 4, 2).unwrap();
        // No .dek file — must fail.
        let result = store.retrieve(&meta.artifact_id, SEED);
        assert!(matches!(result, Err(ArtifactError::DekNotReleased(_))));
    }

    #[test]
    fn retrieve_with_dek_succeeds() {
        let dir = tempfile::tempdir().unwrap();
        let store = ArtifactStore::new(dir.path());
        let data = b"secret artifact data with dek released";
        let meta = store.store(data, SEED, 4, 2).unwrap();
        // Simulate DEK release.
        let dek_path = dir.path().join(format!("{}.dek", meta.artifact_id));
        std::fs::write(&dek_path, b"released").unwrap();
        let recovered = store.retrieve(&meta.artifact_id, SEED).unwrap();
        assert_eq!(recovered, data);
    }

    #[test]
    fn store_idempotent() {
        let dir = tempfile::tempdir().unwrap();
        let store = ArtifactStore::new(dir.path());
        let data = b"idempotent store test";
        let m1 = store.store(data, SEED, 4, 2).unwrap();
        let m2 = store.store(data, SEED, 4, 2).unwrap();
        assert_eq!(m1.artifact_id, m2.artifact_id);
    }
}
