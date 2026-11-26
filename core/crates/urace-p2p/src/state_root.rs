//! M27 — State root verification: cryptographic commitment to ledger state.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StateRoot {
    pub height: u64,
    /// Hex-encoded SHA-256 of the concatenated sorted entry hashes.
    pub root_hash: String,
    pub timestamp_unix: u64,
    pub entry_count: usize,
}

/// Hash a single entry string to a 32-byte digest.
fn hash_entry(entry: &str) -> Vec<u8> {
    let mut h = Sha256::new();
    h.update(entry.as_bytes());
    h.finalize().to_vec()
}

/// Compute a state root from a list of entry strings (each is an HMAC-signed row serialised to string).
/// Sorts entries before hashing for determinism.
pub fn compute_state_root(entries: &[&str], height: u64, timestamp_unix: u64) -> StateRoot {
    let mut sorted: Vec<&str> = entries.to_vec();
    sorted.sort_unstable();

    let mut outer = Sha256::new();
    for entry in &sorted {
        outer.update(hash_entry(entry));
    }
    let root_bytes = outer.finalize();
    let root_hash = hex::encode(root_bytes);

    StateRoot {
        height,
        root_hash,
        timestamp_unix,
        entry_count: entries.len(),
    }
}

/// Verify that recomputing the root from entries matches `root.root_hash`.
pub fn verify_state_root(root: &StateRoot, entries: &[&str]) -> bool {
    let recomputed = compute_state_root(entries, root.height, root.timestamp_unix);
    recomputed.root_hash == root.root_hash
}

#[derive(Debug, thiserror::Error)]
pub enum StateRootError {
    #[error("state root hash mismatch: expected {expected}, got {actual}")]
    HashMismatch { expected: String, actual: String },
    #[error("entry count mismatch: expected {expected}, got {actual}")]
    CountMismatch { expected: usize, actual: usize },
}

/// Verify entry count then hash; returns the first error encountered.
pub fn assert_state_root(root: &StateRoot, entries: &[&str]) -> Result<(), StateRootError> {
    if entries.len() != root.entry_count {
        return Err(StateRootError::CountMismatch {
            expected: root.entry_count,
            actual: entries.len(),
        });
    }

    let recomputed = compute_state_root(entries, root.height, root.timestamp_unix);
    if recomputed.root_hash != root.root_hash {
        return Err(StateRootError::HashMismatch {
            expected: root.root_hash.clone(),
            actual: recomputed.root_hash,
        });
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_entries_produce_consistent_root() {
        let r1 = compute_state_root(&[], 0, 1_000);
        let r2 = compute_state_root(&[], 0, 1_000);
        assert_eq!(r1.root_hash, r2.root_hash, "empty root should be deterministic");
        assert_eq!(r1.entry_count, 0);
    }

    #[test]
    fn test_root_verified_after_roundtrip() {
        let entries = ["row-a", "row-b", "row-c"];
        let root = compute_state_root(&entries, 1, 2_000);
        assert!(verify_state_root(&root, &entries));
        assert!(assert_state_root(&root, &entries).is_ok());
    }

    #[test]
    fn test_adding_entry_changes_root_hash() {
        let entries_v1 = ["row-a", "row-b"];
        let entries_v2 = ["row-a", "row-b", "row-c"];
        let root_v1 = compute_state_root(&entries_v1, 1, 1_000);
        let root_v2 = compute_state_root(&entries_v2, 2, 1_001);
        assert_ne!(root_v1.root_hash, root_v2.root_hash);
    }

    #[test]
    fn test_removed_entry_detected_by_count_mismatch() {
        let entries = ["row-a", "row-b", "row-c"];
        let root = compute_state_root(&entries, 1, 3_000);
        // Provide only 2 of 3 entries.
        let truncated = &entries[..2];
        let err = assert_state_root(&root, truncated).unwrap_err();
        assert!(matches!(err, StateRootError::CountMismatch { expected: 3, actual: 2 }));
    }

    #[test]
    fn test_tampered_entry_detected_by_hash_mismatch() {
        let entries = ["row-a", "row-b"];
        let root = compute_state_root(&entries, 1, 1_000);
        let tampered = ["row-a", "row-TAMPERED"];
        let err = assert_state_root(&root, &tampered).unwrap_err();
        assert!(matches!(err, StateRootError::HashMismatch { .. }));
    }

    #[test]
    fn test_order_independent_hash() {
        let entries_a = ["z-last", "a-first"];
        let entries_b = ["a-first", "z-last"];
        let r_a = compute_state_root(&entries_a, 1, 1_000);
        let r_b = compute_state_root(&entries_b, 1, 1_000);
        assert_eq!(r_a.root_hash, r_b.root_hash, "result must be order-independent");
    }
}
