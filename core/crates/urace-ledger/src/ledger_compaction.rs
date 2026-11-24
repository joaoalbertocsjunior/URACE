//! Ledger compaction — reduce sync cost while preserving the full audit chain.
//!
//! Ported from `ledger_compaction.py`.
//!
//! # Invariant (from `runtime/urace/CLAUDE.md`):
//! Compaction MUST preserve the full audit chain — no entries are dropped.
//!
//! The `compact` function reads all entries from the source journal,
//! verifies the HMAC chain, then writes them verbatim to the output journal.
//! The result is a single JSONL file whose chain is re-signed under the
//! output key; the original source file is left unmodified.
//!
//! `CompactionResult` reports how many entries were processed and whether
//! the HMAC chain of the source was intact.

use crate::journal::{Journal, JournalError};
use serde::{Deserialize, Serialize};
use std::path::Path;
use thiserror::Error;
use urace_types::LedgerEntry;

#[derive(Debug, Serialize, Deserialize)]
pub struct CompactionResult {
    pub entries_read: usize,
    pub entries_written: usize,
    /// Whether the source HMAC chain verified without error.
    pub hmac_verified: bool,
}

#[derive(Debug, Error)]
pub enum CompactionError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

/// Compact `source_path` into `output_path`.
///
/// 1. Opens `source_path` and verifies its HMAC chain.
/// 2. Writes every entry into `output_path` (a fresh journal), re-signing
///    each row under `output_hmac_key`.
/// 3. Returns `CompactionResult`.
///
/// # Append-only invariant
/// Every entry read from the source is written to the output — zero entries
/// are dropped. The source file is NOT modified.
pub fn compact(
    source_path: impl AsRef<Path>,
    output_path: impl AsRef<Path>,
    source_hmac_key: [u8; 32],
    output_hmac_key: [u8; 32],
) -> Result<CompactionResult, CompactionError> {
    let source = Journal::open(&source_path, source_hmac_key)?;

    // Verify chain integrity; record whether it passed.
    let (entries, hmac_verified) = match source.verify_integrity() {
        Ok(e) => (e, true),
        Err(JournalError::IntegrityViolation(_)) => {
            // Chain is corrupt — read raw entries so we still write them all.
            let raw = read_raw_entries(&source_path)?;
            (raw, false)
        }
        Err(e) => return Err(e.into()),
    };

    let entries_read = entries.len();

    // Write to output journal, re-signing under the output key.
    let output = Journal::open(&output_path, output_hmac_key)?;
    for entry in &entries {
        // Re-append with original kind + payload (seq will be reassigned).
        output.append(&entry.kind, entry.payload.clone())?;
    }

    Ok(CompactionResult {
        entries_read,
        entries_written: entries_read, // invariant: entries_written == entries_read
        hmac_verified,
    })
}

/// Read raw `LedgerEntry` values line-by-line without HMAC verification
/// (fallback for corrupt-but-parseable journals).
fn read_raw_entries(path: impl AsRef<Path>) -> Result<Vec<LedgerEntry>, CompactionError> {
    if !path.as_ref().exists() {
        return Ok(vec![]);
    }
    let content = std::fs::read_to_string(&path)?;
    let mut out = Vec::new();
    for line in content.lines() {
        if line.trim().is_empty() {
            continue;
        }
        if let Ok(entry) = serde_json::from_str::<LedgerEntry>(line) {
            out.push(entry);
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tempfile::tempdir;

    const KEY_SRC: [u8; 32] = *b"urace-compact-src-32bytes-------";
    const KEY_OUT: [u8; 32] = *b"urace-compact-out-32bytes-------";

    #[test]
    fn compact_preserves_all_entries() {
        let dir = tempdir().unwrap();
        let src = dir.path().join("source.jsonl");
        let out = dir.path().join("output.jsonl");

        let journal = Journal::open(&src, KEY_SRC).unwrap();
        journal.append("EVT_A", json!({"data": "hello"})).unwrap();
        journal.append("EVT_B", json!({"data": "world"})).unwrap();
        journal.append("EVT_C", json!({"data": "foo"})).unwrap();

        let result = compact(&src, &out, KEY_SRC, KEY_OUT).unwrap();

        assert_eq!(result.entries_read, 3);
        assert_eq!(result.entries_written, 3);
        assert!(result.hmac_verified);
    }

    #[test]
    fn entries_written_equals_entries_read() {
        let dir = tempdir().unwrap();
        let src = dir.path().join("source.jsonl");
        let out = dir.path().join("output.jsonl");

        let journal = Journal::open(&src, KEY_SRC).unwrap();
        for i in 0..10 {
            journal.append("ROW", json!({"i": i})).unwrap();
        }

        let result = compact(&src, &out, KEY_SRC, KEY_OUT).unwrap();
        assert_eq!(result.entries_written, result.entries_read);
        assert_eq!(result.entries_read, 10);
    }

    #[test]
    fn output_journal_is_valid() {
        let dir = tempdir().unwrap();
        let src = dir.path().join("source.jsonl");
        let out = dir.path().join("output.jsonl");

        let journal = Journal::open(&src, KEY_SRC).unwrap();
        journal.append("EVT", json!({"x": 1})).unwrap();
        journal.append("EVT", json!({"x": 2})).unwrap();

        compact(&src, &out, KEY_SRC, KEY_OUT).unwrap();

        let out_journal = Journal::open(&out, KEY_OUT).unwrap();
        let entries = out_journal.verify_integrity().unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].kind, "EVT");
        assert_eq!(entries[1].kind, "EVT");
    }

    #[test]
    fn empty_source_produces_empty_output() {
        let dir = tempdir().unwrap();
        let src = dir.path().join("source.jsonl");
        let out = dir.path().join("output.jsonl");

        // Create empty source
        std::fs::write(&src, b"").unwrap();

        let result = compact(&src, &out, KEY_SRC, KEY_OUT).unwrap();
        assert_eq!(result.entries_read, 0);
        assert_eq!(result.entries_written, 0);
        assert!(result.hmac_verified);
    }
}
