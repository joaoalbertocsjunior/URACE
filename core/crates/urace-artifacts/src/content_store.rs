//! Content-addressed file reference registry (append-only JSONL index).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use thiserror::Error;

const STORE_DIR: &str = "urace/content_refs";
const INDEX_FILE: &str = "index.jsonl";

#[derive(Debug, Error)]
pub enum ContentStoreError {
    #[error("file not found: {0}")]
    FileNotFound(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

/// A registered content reference.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentRef {
    /// First 16 hex chars of sha256 — short stable id.
    pub id: String,
    pub sha256: String,
    pub path: String,
    pub size_bytes: u64,
    pub name: String,
    pub registered_at: String,
}

fn store_root(product_root: &Path) -> PathBuf {
    product_root.join(STORE_DIR)
}

fn index_path(product_root: &Path) -> PathBuf {
    store_root(product_root).join(INDEX_FILE)
}

/// Register a file and return its `ContentRef`.
///
/// If the same SHA-256 is already indexed the existing record is returned
/// without writing a duplicate line (append-only guarantee).
pub fn content_ref(product_root: &Path, file_path: &str) -> Result<ContentRef, ContentStoreError> {
    let src = PathBuf::from(file_path);
    if !src.exists() {
        return Err(ContentStoreError::FileNotFound(file_path.to_owned()));
    }
    let size = src.metadata()?.len();
    let mut h = Sha256::new();
    let mut f = std::fs::File::open(&src)?;
    std::io::copy(&mut f, &mut h)?;
    let digest = hex::encode(h.finalize());

    let entry = ContentRef {
        id: digest[..16].to_owned(),
        sha256: digest.clone(),
        path: src.to_string_lossy().into_owned(),
        size_bytes: size,
        name: src
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default(),
        registered_at: chrono_now_iso(),
    };

    std::fs::create_dir_all(store_root(product_root))?;
    let idx = index_path(product_root);
    let existing = load_index(product_root)?;
    if !existing.iter().any(|r| r.sha256 == digest) {
        use std::io::Write;
        let mut file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&idx)?;
        writeln!(file, "{}", serde_json::to_string(&entry)?)?;
    }

    Ok(entry)
}

/// List all registered content refs.
pub fn content_list(product_root: &Path) -> Result<Vec<ContentRef>, ContentStoreError> {
    load_index(product_root)
}

/// Look up a content ref by id prefix or full sha256 prefix.
pub fn content_show(
    product_root: &Path,
    ref_id: &str,
) -> Result<Option<ContentRef>, ContentStoreError> {
    let entries = load_index(product_root)?;
    Ok(entries
        .into_iter()
        .find(|r| r.id == ref_id || r.sha256.starts_with(ref_id)))
}

fn load_index(product_root: &Path) -> Result<Vec<ContentRef>, ContentStoreError> {
    let idx = index_path(product_root);
    if !idx.exists() {
        return Ok(vec![]);
    }
    let text = std::fs::read_to_string(&idx)?;
    let mut entries = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if !line.is_empty() {
            if let Ok(entry) = serde_json::from_str::<ContentRef>(line) {
                entries.push(entry);
            }
        }
    }
    Ok(entries)
}

/// Portable ISO-8601 timestamp (no chrono dep — use std only).
fn chrono_now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Format: YYYY-MM-DDTHH:MM:SSZ
    let (y, mo, d, h, mi, s) = epoch_to_parts(secs);
    format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

fn epoch_to_parts(mut secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    let s = secs % 60;
    secs /= 60;
    let mi = secs % 60;
    secs /= 60;
    let h = secs % 24;
    secs /= 24;
    // Days since epoch → Gregorian
    let (y, mo, d) = days_to_ymd(secs);
    (y, mo, d, h, mi, s)
}

fn days_to_ymd(mut days: u64) -> (u64, u64, u64) {
    let mut y = 1970u64;
    loop {
        let dy = if is_leap(y) { 366 } else { 365 };
        if days < dy {
            break;
        }
        days -= dy;
        y += 1;
    }
    let months = if is_leap(y) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut mo = 1u64;
    for dm in &months {
        if days < *dm {
            break;
        }
        days -= dm;
        mo += 1;
    }
    (y, mo, days + 1)
}

fn is_leap(y: u64) -> bool {
    (y.is_multiple_of(4) && !y.is_multiple_of(100)) || y.is_multiple_of(400)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    fn write_tmp(dir: &TempDir, name: &str, contents: &[u8]) -> String {
        let p = dir.path().join(name);
        let mut f = std::fs::File::create(&p).unwrap();
        f.write_all(contents).unwrap();
        p.to_string_lossy().into_owned()
    }

    #[test]
    fn register_and_list() {
        let root = TempDir::new().unwrap();
        let file = write_tmp(&root, "a.txt", b"hello");
        let r = content_ref(root.path(), &file).unwrap();
        assert_eq!(r.name, "a.txt");
        assert_eq!(r.size_bytes, 5);
        let list = content_list(root.path()).unwrap();
        assert_eq!(list.len(), 1);
    }

    #[test]
    fn deduplication() {
        let root = TempDir::new().unwrap();
        let file = write_tmp(&root, "b.txt", b"dup");
        content_ref(root.path(), &file).unwrap();
        content_ref(root.path(), &file).unwrap();
        assert_eq!(content_list(root.path()).unwrap().len(), 1);
    }

    #[test]
    fn show_by_id_prefix() {
        let root = TempDir::new().unwrap();
        let file = write_tmp(&root, "c.txt", b"xyz");
        let r = content_ref(root.path(), &file).unwrap();
        let found = content_show(root.path(), &r.id).unwrap();
        assert!(found.is_some());
    }

    #[test]
    fn show_missing_returns_none() {
        let root = TempDir::new().unwrap();
        let found = content_show(root.path(), "deadbeef").unwrap();
        assert!(found.is_none());
    }

    #[test]
    fn file_not_found_error() {
        let root = TempDir::new().unwrap();
        let err = content_ref(root.path(), "/no/such/file.txt").unwrap_err();
        assert!(matches!(err, ContentStoreError::FileNotFound(_)));
    }
}
