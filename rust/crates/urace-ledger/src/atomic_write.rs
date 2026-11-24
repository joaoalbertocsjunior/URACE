//! Atomic file write — write to temp file, fsync, rename.
//!
//! All ledger mutations go through this. Partial writes never corrupt the ledger.

use std::io::Write;
use std::path::Path;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AtomicWriteError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("temp file path construction failed for {0}")]
    TempPath(String),
}

/// Atomically write `data` to `path` via a temp file + rename.
pub fn atomic_write(path: &Path, data: &[u8]) -> Result<(), AtomicWriteError> {
    let dir = path.parent().unwrap_or(Path::new("."));
    let tmp_path = dir.join(format!(
        ".{}.tmp",
        path.file_name()
            .and_then(|n| n.to_str())
            .ok_or_else(|| AtomicWriteError::TempPath(path.display().to_string()))?
    ));

    {
        let mut f = std::fs::OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&tmp_path)?;
        f.write_all(data)?;
        f.flush()?;
        f.sync_all()?;
    }

    std::fs::rename(&tmp_path, path)?;
    Ok(())
}

/// Atomically append a JSON line to a `.jsonl` file.
pub fn atomic_append_jsonl(path: &Path, row: &serde_json::Value) -> Result<(), AtomicWriteError> {
    use std::fs::OpenOptions;
    let mut line = serde_json::to_string(row).expect("serializable value");
    line.push('\n');
    // For append-only we use O_APPEND which is atomic at the OS level on POSIX.
    let mut f = OpenOptions::new().create(true).append(true).open(path)?;
    f.write_all(line.as_bytes())?;
    f.flush()?;
    Ok(())
}
