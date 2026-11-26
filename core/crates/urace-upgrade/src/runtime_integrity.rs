//! M58 — Runtime integrity: verify the active runtime binary and config haven't been tampered with.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum IntegrityStatus {
    Intact,
    BinaryTampered { expected: String, actual: String },
    ConfigTampered { expected: String, actual: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeIntegrityRecord {
    pub binary_hash: String,
    pub config_hash: String,
    pub recorded_at_unix: u64,
}

/// Check whether the runtime state matches its integrity record.
pub fn verify_runtime_integrity(
    record: &RuntimeIntegrityRecord,
    current_binary_hash: &str,
    current_config_hash: &str,
) -> IntegrityStatus {
    if record.binary_hash != current_binary_hash {
        return IntegrityStatus::BinaryTampered {
            expected: record.binary_hash.clone(),
            actual: current_binary_hash.to_string(),
        };
    }
    if record.config_hash != current_config_hash {
        return IntegrityStatus::ConfigTampered {
            expected: record.config_hash.clone(),
            actual: current_config_hash.to_string(),
        };
    }
    IntegrityStatus::Intact
}

/// Compute a config hash from key-value pairs (sorted by key for determinism).
pub fn compute_config_hash(config_pairs: &[(&str, &str)]) -> String {
    let mut sorted: Vec<(&str, &str)> = config_pairs.to_vec();
    sorted.sort_by_key(|(k, _)| *k);

    let mut hasher = Sha256::new();
    for (key, value) in &sorted {
        hasher.update(key.as_bytes());
        hasher.update(b"=");
        hasher.update(value.as_bytes());
        hasher.update(b"\n");
    }
    hex::encode(hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_record(binary_hash: &str, config_hash: &str) -> RuntimeIntegrityRecord {
        RuntimeIntegrityRecord {
            binary_hash: binary_hash.to_string(),
            config_hash: config_hash.to_string(),
            recorded_at_unix: 1_000_000,
        }
    }

    #[test]
    fn matching_hashes_returns_intact() {
        let record = make_record("binhash-abc", "cfghash-xyz");
        let status = verify_runtime_integrity(&record, "binhash-abc", "cfghash-xyz");
        assert_eq!(status, IntegrityStatus::Intact);
    }

    #[test]
    fn wrong_binary_hash_returns_binary_tampered() {
        let record = make_record("binhash-abc", "cfghash-xyz");
        let status = verify_runtime_integrity(&record, "binhash-EVIL", "cfghash-xyz");
        assert!(matches!(
            status,
            IntegrityStatus::BinaryTampered { .. }
        ));
        if let IntegrityStatus::BinaryTampered { expected, actual } = status {
            assert_eq!(expected, "binhash-abc");
            assert_eq!(actual, "binhash-EVIL");
        }
    }

    #[test]
    fn wrong_config_hash_returns_config_tampered() {
        let record = make_record("binhash-abc", "cfghash-xyz");
        let status = verify_runtime_integrity(&record, "binhash-abc", "cfghash-EVIL");
        assert!(matches!(
            status,
            IntegrityStatus::ConfigTampered { .. }
        ));
        if let IntegrityStatus::ConfigTampered { expected, actual } = status {
            assert_eq!(expected, "cfghash-xyz");
            assert_eq!(actual, "cfghash-EVIL");
        }
    }

    #[test]
    fn compute_config_hash_is_deterministic() {
        // Different insertion order should yield same hash
        let pairs_a = vec![("key_b", "val_b"), ("key_a", "val_a"), ("key_c", "val_c")];
        let pairs_b = vec![("key_c", "val_c"), ("key_a", "val_a"), ("key_b", "val_b")];
        let hash_a = compute_config_hash(&pairs_a);
        let hash_b = compute_config_hash(&pairs_b);
        assert_eq!(hash_a, hash_b);

        // Different values should produce different hashes
        let pairs_c = vec![("key_a", "DIFFERENT"), ("key_b", "val_b"), ("key_c", "val_c")];
        let hash_c = compute_config_hash(&pairs_c);
        assert_ne!(hash_a, hash_c);
    }
}
