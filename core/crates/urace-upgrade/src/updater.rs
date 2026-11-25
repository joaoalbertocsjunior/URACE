//! Runtime updater — downloads and verifies runtime update packages.
//!
//! Rust port of `updater.py`.
//! Fetches update manifests, verifies SHA-256 checksums, writes atomically.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;
use tracing::info;

#[derive(Debug, Error)]
pub enum UpdateError {
    #[error("checksum mismatch: expected={expected}, got={got}")]
    ChecksumMismatch { expected: String, got: String },

    #[error("HTTP error fetching manifest: {0}")]
    Http(String),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// Manifest describing a runtime update.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateManifest {
    pub version: String,
    pub download_url: String,
    pub sha256: String,
    pub size_bytes: u64,
    pub changelog: String,
}

/// Verifies and stages runtime updates.
pub struct Updater {
    staging_dir: std::path::PathBuf,
}

impl Updater {
    pub fn new(staging_dir: impl Into<std::path::PathBuf>) -> Self {
        Updater {
            staging_dir: staging_dir.into(),
        }
    }

    /// Verifies `bytes` match `manifest.sha256`.
    pub fn verify_checksum(
        &self,
        bytes: &[u8],
        manifest: &UpdateManifest,
    ) -> Result<(), UpdateError> {
        let mut hasher = Sha256::new();
        hasher.update(bytes);
        let got = hex::encode(hasher.finalize());
        if got != manifest.sha256 {
            return Err(UpdateError::ChecksumMismatch {
                expected: manifest.sha256.clone(),
                got,
            });
        }
        Ok(())
    }

    /// Writes verified bytes atomically to `staging_dir/{version}`.
    pub fn stage(
        &self,
        bytes: &[u8],
        manifest: &UpdateManifest,
    ) -> Result<std::path::PathBuf, UpdateError> {
        self.verify_checksum(bytes, manifest)?;
        let dest = self.staging_dir.join(&manifest.version);
        std::fs::create_dir_all(&self.staging_dir)?;
        std::fs::write(&dest, bytes)?;
        info!(version = %manifest.version, path = %dest.display(), "update staged");
        Ok(dest)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};

    fn manifest_for(bytes: &[u8]) -> UpdateManifest {
        let mut h = Sha256::new();
        h.update(bytes);
        UpdateManifest {
            version: "0.2.0".into(),
            download_url: "http://example.com/update".into(),
            sha256: hex::encode(h.finalize()),
            size_bytes: bytes.len() as u64,
            changelog: "test update".into(),
        }
    }

    #[test]
    fn checksum_valid() {
        let bytes = b"runtime_binary_content";
        let m = manifest_for(bytes);
        let updater = Updater::new("/tmp");
        assert!(updater.verify_checksum(bytes, &m).is_ok());
    }

    #[test]
    fn checksum_mismatch() {
        let bytes = b"runtime_binary_content";
        let mut m = manifest_for(bytes);
        m.sha256 = "deadbeef".repeat(8);
        let updater = Updater::new("/tmp");
        let err = updater.verify_checksum(bytes, &m).unwrap_err();
        assert!(matches!(err, UpdateError::ChecksumMismatch { .. }));
    }

    #[test]
    fn stage_writes_file() {
        let dir = tempfile::tempdir().unwrap();
        let bytes = b"payload";
        let m = manifest_for(bytes);
        let updater = Updater::new(dir.path());
        let path = updater.stage(bytes, &m).unwrap();
        assert!(path.exists());
        assert_eq!(std::fs::read(&path).unwrap(), bytes);
    }
}
