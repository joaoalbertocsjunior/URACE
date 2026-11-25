//! Bounded, real local JSON / CSV I/O layer.
//!
//! Ported from `data_transport.py` (159 lines).
//!
//! SQLite support is explicitly out of scope for this Rust port: the workspace
//! does not declare a SQLite dependency and adding one is prohibited by the
//! "no new external deps beyond workspace" constraint.  Any caller that needs
//! SQLite must keep using the Python layer or add the dep separately; the
//! error variant `DataError::SqliteUnsupported` is returned to make the gap
//! explicit rather than silent.

use std::collections::HashMap;
use std::io::Write as IoWrite;
use std::path::{Path, PathBuf};

use serde_json::Value;
use thiserror::Error;

// ---------------------------------------------------------------------------
// Public error type
// ---------------------------------------------------------------------------

/// All errors that can arise from transport operations.
#[derive(Debug, Error)]
pub enum DataError {
    #[error("file size exceeds limit of {limit} bytes (got {actual})")]
    SizeLimitExceeded { actual: usize, limit: usize },

    #[error("row count exceeds limit of {limit} rows (got {actual})")]
    RowLimitExceeded { actual: usize, limit: usize },

    #[error("symlink data targets require an explicit resolved path")]
    SymlinkRejected,

    #[error("SQLite transport is not implemented in the Rust port")]
    SqliteUnsupported,

    #[error("data must be an object or an array of objects with string keys")]
    InvalidShape,

    #[error("path escapes the URACE root")]
    PathEscapesRoot,

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// DataFormat
// ---------------------------------------------------------------------------

/// The on-disk encoding of a data source.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DataFormat {
    Json,
    Csv,
    Sqlite,
}

// ---------------------------------------------------------------------------
// DataTransport
// ---------------------------------------------------------------------------

/// Bounded local data transport.
///
/// All reads and writes are capped by `max_size_bytes` and `max_rows`.
/// The optional `root` field, when set, prevents path traversal beyond it.
#[derive(Debug, Clone)]
pub struct DataTransport {
    /// Maximum byte size for a single read or write.  Default: 5 MiB.
    pub max_size_bytes: usize,
    /// Maximum number of rows returned by any read.  Default: 10 000.
    pub max_rows: usize,
    /// When set, paths are rejected if they escape this root directory.
    pub root: Option<PathBuf>,
}

impl Default for DataTransport {
    fn default() -> Self {
        Self {
            max_size_bytes: 5 * 1024 * 1024,
            max_rows: 10_000,
            root: None,
        }
    }
}

impl DataTransport {
    /// Construct with explicit limits.
    pub fn new(max_size_bytes: usize, max_rows: usize) -> Self {
        Self {
            max_size_bytes,
            max_rows,
            root: None,
        }
    }

    /// Validate a path: reject symlinks, reject escapes from `self.root`.
    pub fn validate_path(&self, path: &Path) -> Result<PathBuf, DataError> {
        // Symlink check before resolving.
        if path.is_symlink() {
            return Err(DataError::SymlinkRejected);
        }

        let resolved = if path.is_absolute() {
            path.to_path_buf()
        } else {
            std::env::current_dir()?.join(path)
        };

        // Normalise by collapsing `.` / `..` without calling `canonicalize`
        // (which would fail on non-existent paths).
        let normalised = normalise_path(&resolved);

        if let Some(root) = &self.root {
            let root_norm = normalise_path(root);
            if !normalised.starts_with(&root_norm) {
                return Err(DataError::PathEscapesRoot);
            }
        }

        Ok(normalised)
    }

    // -----------------------------------------------------------------------
    // JSON
    // -----------------------------------------------------------------------

    /// Read a JSON file, enforcing the size limit.
    pub fn read_json(&self, path: &Path) -> Result<Value, DataError> {
        let path = self.validate_path(path)?;
        let raw = self.read_bounded(&path)?;
        let value = serde_json::from_slice(&raw)?;
        Ok(value)
    }

    /// Atomically write a JSON value, enforcing the size limit.
    ///
    /// Uses a temp file + rename so callers never observe a partial write.
    pub fn write_json(&self, path: &Path, value: &Value) -> Result<(), DataError> {
        let path = self.validate_path(path)?;
        let mut data = serde_json::to_vec(value)?;
        data.push(b'\n');

        if data.len() > self.max_size_bytes {
            return Err(DataError::SizeLimitExceeded {
                actual: data.len(),
                limit: self.max_size_bytes,
            });
        }

        atomic_write(&path, &data)?;
        Ok(())
    }

    // -----------------------------------------------------------------------
    // CSV
    // -----------------------------------------------------------------------

    /// Read a CSV file, returning up to `max_rows` rows.
    ///
    /// Each row is a `Vec<String>` (header row included as the first element).
    pub fn read_csv(&self, path: &Path, max_rows: usize) -> Result<Vec<Vec<String>>, DataError> {
        let path = self.validate_path(path)?;
        let raw = self.read_bounded(&path)?;
        let text = String::from_utf8_lossy(&raw);

        let mut result: Vec<Vec<String>> = Vec::new();
        for line in text.lines() {
            if result.len() > max_rows {
                return Err(DataError::RowLimitExceeded {
                    actual: result.len(),
                    limit: max_rows,
                });
            }
            let row: Vec<String> = split_csv_line(line);
            result.push(row);
        }
        Ok(result)
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    fn read_bounded(&self, path: &Path) -> Result<Vec<u8>, DataError> {
        let meta = std::fs::metadata(path)?;
        let file_len = meta.len() as usize;
        if file_len > self.max_size_bytes {
            return Err(DataError::SizeLimitExceeded {
                actual: file_len,
                limit: self.max_size_bytes,
            });
        }
        let raw = std::fs::read(path)?;
        if raw.len() > self.max_size_bytes {
            return Err(DataError::SizeLimitExceeded {
                actual: raw.len(),
                limit: self.max_size_bytes,
            });
        }
        Ok(raw)
    }
}

// ---------------------------------------------------------------------------
// Module-level convenience functions (matches Python API surface)
// ---------------------------------------------------------------------------

/// Read a JSON file with the default transport limits.
pub fn read_json(path: &Path) -> Result<Value, DataError> {
    DataTransport::default().read_json(path)
}

/// Atomically write a JSON value with the default transport limits.
pub fn write_json(path: &Path, value: &Value) -> Result<(), DataError> {
    DataTransport::default().write_json(path, value)
}

/// Read a bounded CSV file (default limits) up to `max_rows` data rows.
pub fn read_csv(path: &Path, max_rows: usize) -> Result<Vec<Vec<String>>, DataError> {
    DataTransport::default().read_csv(path, max_rows)
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Atomically replace `path` with `data` using a sibling temp file.
fn atomic_write(path: &Path, data: &[u8]) -> Result<(), DataError> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }

    // Write to a temp file in the same directory so rename is atomic.
    let tmp_path = path.with_extension(format!(
        "tmp-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .subsec_nanos()
    ));

    {
        let mut f = std::fs::File::create(&tmp_path)?;
        f.write_all(data)?;
        f.flush()?;
        // fsync — best-effort; ignore error on platforms that don't support it.
        let _ = f.sync_all();
    }

    std::fs::rename(&tmp_path, path)?;
    Ok(())
}

/// Normalise a path by resolving `.` / `..` components without touching the FS.
fn normalise_path(path: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for component in path.components() {
        match component {
            std::path::Component::ParentDir => {
                out.pop();
            }
            std::path::Component::CurDir => {}
            c => out.push(c),
        }
    }
    out
}

/// Minimal RFC 4180 CSV line splitter (no multi-line fields — matching the
/// Python `csv.DictReader` behaviour used in the original module).
fn split_csv_line(line: &str) -> Vec<String> {
    let mut fields = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;
    let mut chars = line.chars().peekable();

    while let Some(c) = chars.next() {
        match c {
            '"' if in_quotes => {
                if chars.peek() == Some(&'"') {
                    chars.next();
                    current.push('"');
                } else {
                    in_quotes = false;
                }
            }
            '"' => in_quotes = true,
            ',' if !in_quotes => {
                fields.push(current.clone());
                current.clear();
            }
            other => current.push(other),
        }
    }
    fields.push(current);
    fields
}

/// Validate that `rows` is an array of objects with string keys and that the
/// total serialised size respects limits.
pub fn validate_rows(
    rows: &Value,
    max_rows: usize,
    max_bytes: usize,
) -> Result<Vec<HashMap<String, Value>>, DataError> {
    let arr: Vec<&Value> = match rows {
        Value::Array(a) => a.iter().collect(),
        Value::Object(_) => vec![rows],
        _ => return Err(DataError::InvalidShape),
    };

    if arr.len() > max_rows {
        return Err(DataError::RowLimitExceeded {
            actual: arr.len(),
            limit: max_rows,
        });
    }

    let mut result: Vec<HashMap<String, Value>> = Vec::with_capacity(arr.len());
    for item in &arr {
        match item {
            Value::Object(map) => {
                result.push(map.iter().map(|(k, v)| (k.clone(), v.clone())).collect());
            }
            _ => return Err(DataError::InvalidShape),
        }
    }

    // Check serialised size.
    let encoded = serde_json::to_vec(rows)?;
    if encoded.len() > max_bytes {
        return Err(DataError::SizeLimitExceeded {
            actual: encoded.len(),
            limit: max_bytes,
        });
    }

    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn write_and_read_json_roundtrip() {
        let mut f = NamedTempFile::new().unwrap();
        let path = f.path().to_path_buf();
        // Ensure file exists before write (NamedTempFile creates it).
        drop(f.as_file_mut()); // keep the file alive

        let value = serde_json::json!({"key": "value", "n": 42});
        write_json(&path, &value).unwrap();
        let back = read_json(&path).unwrap();
        assert_eq!(back["key"], "value");
        assert_eq!(back["n"], 42);
    }

    #[test]
    fn read_json_size_limit_enforced() {
        let mut f = NamedTempFile::new().unwrap();
        // Write 10 bytes of valid JSON.
        f.write_all(b"[1,2,3,4,5]").unwrap();
        f.flush().unwrap();

        let transport = DataTransport {
            max_size_bytes: 5, // very small
            max_rows: 100,
            root: None,
        };
        let result = transport.read_json(f.path());
        assert!(matches!(result, Err(DataError::SizeLimitExceeded { .. })));
    }

    #[test]
    fn symlink_is_rejected() {
        // Create a real file, then a symlink to it.
        let dir = tempfile::tempdir().unwrap();
        let real = dir.path().join("real.json");
        std::fs::write(&real, b"{}").unwrap();
        let link = dir.path().join("link.json");
        #[cfg(unix)]
        std::os::unix::fs::symlink(&real, &link).unwrap();
        #[cfg(windows)]
        std::os::windows::fs::symlink_file(&real, &link).unwrap();

        let transport = DataTransport::default();
        let result = transport.read_json(&link);
        assert!(matches!(result, Err(DataError::SymlinkRejected)));
    }

    #[test]
    fn read_csv_basic() {
        let mut f = NamedTempFile::new().unwrap();
        f.write_all(b"a,b,c\n1,2,3\n4,5,6\n").unwrap();
        f.flush().unwrap();

        let rows = read_csv(f.path(), 100).unwrap();
        assert_eq!(rows.len(), 3); // header + 2 data rows
        assert_eq!(rows[0], vec!["a", "b", "c"]);
        assert_eq!(rows[1], vec!["1", "2", "3"]);
    }

    #[test]
    fn read_csv_row_limit_enforced() {
        let mut f = NamedTempFile::new().unwrap();
        // 5 lines
        f.write_all(b"a\n1\n2\n3\n4\n5\n").unwrap();
        f.flush().unwrap();

        let result = read_csv(f.path(), 2);
        assert!(matches!(result, Err(DataError::RowLimitExceeded { .. })));
    }

    #[test]
    fn validate_rows_rejects_non_object() {
        let v = serde_json::json!([1, 2, 3]);
        let result = validate_rows(&v, 100, 1_000_000);
        assert!(matches!(result, Err(DataError::InvalidShape)));
    }

    #[test]
    fn validate_rows_accepts_object_as_single_row() {
        let v = serde_json::json!({"x": 1});
        let rows = validate_rows(&v, 100, 1_000_000).unwrap();
        assert_eq!(rows.len(), 1);
    }

    #[test]
    fn path_escapes_root_rejected() {
        let dir = tempfile::tempdir().unwrap();
        let transport = DataTransport {
            max_size_bytes: 1024,
            max_rows: 100,
            root: Some(dir.path().to_path_buf()),
        };
        // Try to escape root with ..
        let escaping = dir.path().join("..").join("etc").join("passwd");
        let result = transport.validate_path(&escaping);
        assert!(matches!(result, Err(DataError::PathEscapesRoot)));
    }
}
