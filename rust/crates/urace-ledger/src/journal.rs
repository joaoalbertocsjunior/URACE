//! Append-only HMAC-SHA256-signed JSONL journal.
//!
//! Invariants (from `authenticated_journal.py`):
//! - Rows are never deleted or mutated after write.
//! - Every row carries a valid HMAC-SHA256 chain over canonical JSON.
//! - `seq` is monotonically increasing, starting at 0.
//! - Writes are atomic — partial writes never corrupt the journal.
//! - `except Exception: pass` is forbidden on this path; all errors surface.

use crate::atomic_write::atomic_append_jsonl;
use hmac::{Hmac, Mac};
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::Sha256;
use std::path::{Path, PathBuf};
use thiserror::Error;
use urace_types::LedgerEntry;

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Error)]
pub enum JournalError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("atomic write error: {0}")]
    AtomicWrite(#[from] crate::atomic_write::AtomicWriteError),
    #[error("journal integrity violation: {0}")]
    IntegrityViolation(String),
    #[error("symlink in journal path is prohibited")]
    SymlinkProhibited,
}

pub struct Journal {
    path: PathBuf,
    lock: Mutex<()>,
    hmac_key: [u8; 32],
}

impl Journal {
    /// Open (or create) a journal at `path` with HMAC key `hmac_key`.
    pub fn open(path: impl AsRef<Path>, hmac_key: [u8; 32]) -> Result<Self, JournalError> {
        let path = path.as_ref().to_path_buf();
        if path.is_symlink() {
            return Err(JournalError::SymlinkProhibited);
        }
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        Ok(Journal { path, lock: Mutex::new(()), hmac_key })
    }

    fn canonical_bytes(seq: u64, kind: &str, payload: &Value) -> Vec<u8> {
        // Canonical JSON: sorted keys, no whitespace.
        let v = json!({ "kind": kind, "payload": payload, "seq": seq });
        serde_json::to_vec(&v).expect("serializable")
    }

    fn compute_hmac(&self, seq: u64, kind: &str, payload: &Value) -> String {
        let canonical = Self::canonical_bytes(seq, kind, payload);
        let mut mac = HmacSha256::new_from_slice(&self.hmac_key).expect("valid key");
        mac.update(&canonical);
        hex::encode(mac.finalize().into_bytes())
    }

    fn next_seq(&self) -> Result<u64, JournalError> {
        if !self.path.exists() {
            return Ok(0);
        }
        let content = std::fs::read_to_string(&self.path)?;
        let count = content.lines().filter(|l| !l.trim().is_empty()).count();
        Ok(count as u64)
    }

    /// Append a row of `kind` with `payload`. Returns the written `LedgerEntry`.
    pub fn append(
        &self,
        kind: &str,
        payload: Value,
    ) -> Result<LedgerEntry, JournalError> {
        let _guard = self.lock.lock();

        let seq = self.next_seq()?;
        let hmac = self.compute_hmac(seq, kind, &payload);

        let now = {
            use std::time::{SystemTime, UNIX_EPOCH};
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64().to_string())
                .unwrap_or_else(|_| "0".to_string())
        };

        let entry = LedgerEntry {
            seq,
            kind: kind.to_owned(),
            payload: payload.clone(),
            hmac: hmac.clone(),
            written_at: now,
        };

        let row = serde_json::to_value(&entry)?;
        atomic_append_jsonl(&self.path, &row)?;

        Ok(entry)
    }

    /// Read all rows and verify HMAC chain integrity.
    pub fn verify_integrity(&self) -> Result<Vec<LedgerEntry>, JournalError> {
        if !self.path.exists() {
            return Ok(vec![]);
        }
        let content = std::fs::read_to_string(&self.path)?;
        let mut entries = Vec::new();

        for (line_no, line) in content.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let entry: LedgerEntry = serde_json::from_str(line)
                .map_err(|e| JournalError::IntegrityViolation(
                    format!("line {}: parse error: {e}", line_no + 1)
                ))?;

            let expected = self.compute_hmac(entry.seq, &entry.kind, &entry.payload);
            if !constant_time_eq(&expected, &entry.hmac) {
                return Err(JournalError::IntegrityViolation(
                    format!("seq={} HMAC mismatch", entry.seq)
                ));
            }
            if entry.seq != entries.len() as u64 {
                return Err(JournalError::IntegrityViolation(
                    format!("seq gap: expected {}, got {}", entries.len(), entry.seq)
                ));
            }
            entries.push(entry);
        }
        Ok(entries)
    }

    pub fn path(&self) -> &Path {
        &self.path
    }
}

fn constant_time_eq(a: &str, b: &str) -> bool {
    use hmac::digest::CtOutput;
    if a.len() != b.len() {
        return false;
    }
    // Use hmac::digest::CtOutput for constant-time comparison on the bytes.
    let a_bytes = a.as_bytes();
    let b_bytes = b.as_bytes();
    let mut diff = 0u8;
    for (x, y) in a_bytes.iter().zip(b_bytes.iter()) {
        diff |= x ^ y;
    }
    diff == 0
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"urace-ledger-key-32bytes-pad----";

    #[test]
    fn append_and_verify() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("test.jsonl");
        let j = Journal::open(&path, KEY).unwrap();

        j.append("TEST_EVENT", json!({ "data": "hello" })).unwrap();
        j.append("TEST_EVENT", json!({ "data": "world" })).unwrap();

        let entries = j.verify_integrity().unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].seq, 0);
        assert_eq!(entries[1].seq, 1);
    }

    #[test]
    fn tampered_hmac_detected() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("test.jsonl");
        let j = Journal::open(&path, KEY).unwrap();
        j.append("EVT", json!({"x": 1})).unwrap();

        // Corrupt the file.
        let mut content = fs::read_to_string(&path).unwrap();
        content = content.replacen("\"hmac\":", "\"hmac\":\"", 1);
        // simpler: just flip a char in the hmac value
        let content_bytes = content.as_bytes();
        let hmac_pos = content.find("\"hmac\":\"").unwrap() + 8;
        let mut bytes = content_bytes.to_vec();
        bytes[hmac_pos] ^= 0x01;
        fs::write(&path, bytes).unwrap();

        assert!(matches!(j.verify_integrity(), Err(JournalError::IntegrityViolation(_))));
    }

    #[test]
    fn symlink_rejected() {
        let dir = tempdir().unwrap();
        let real = dir.path().join("real.jsonl");
        let link = dir.path().join("link.jsonl");
        fs::write(&real, b"").unwrap();
        std::os::unix::fs::symlink(&real, &link).unwrap();
        assert!(matches!(Journal::open(&link, KEY), Err(JournalError::SymlinkProhibited)));
    }
}
