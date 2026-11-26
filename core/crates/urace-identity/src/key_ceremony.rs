//! M61 — Key ceremony record.
//!
//! A key ceremony produces a verifiable record that a key was generated under
//! proper conditions with witnesses present.  The ceremony hash binds the
//! ceremony id, the new public key, and the sorted witness list so that any
//! tampering is detectable.

use serde::{Deserialize, Serialize};

/// A verifiable record that a key was generated during a formal ceremony.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CeremonyRecord {
    pub ceremony_id: String,
    pub generated_key_id: String,
    pub public_key_hex: String,
    pub witness_peer_ids: Vec<String>,
    pub conducted_at: String,
    /// SHA-256 of `ceremony_id || public_key_hex || sorted(witness_ids)`.
    pub ceremony_hash: String,
}

impl CeremonyRecord {
    /// Construct a new `CeremonyRecord`, computing the ceremony hash on creation.
    pub fn new(
        ceremony_id: impl Into<String>,
        generated_key_id: impl Into<String>,
        public_key_hex: impl Into<String>,
        witness_peer_ids: Vec<String>,
    ) -> Self {
        let ceremony_id = ceremony_id.into();
        let generated_key_id = generated_key_id.into();
        let public_key_hex = public_key_hex.into();
        let conducted_at = now_secs_str();
        let ceremony_hash =
            compute_ceremony_hash(&ceremony_id, &public_key_hex, &witness_peer_ids);
        CeremonyRecord {
            ceremony_id,
            generated_key_id,
            public_key_hex,
            witness_peer_ids,
            conducted_at,
            ceremony_hash,
        }
    }

    /// Verify ceremony record integrity by re-computing and comparing the hash.
    ///
    /// Returns `false` if any field that is part of the hash has been tampered with.
    pub fn verify_integrity(&self) -> bool {
        let expected =
            compute_ceremony_hash(&self.ceremony_id, &self.public_key_hex, &self.witness_peer_ids);
        expected == self.ceremony_hash
    }
}

fn compute_ceremony_hash(ceremony_id: &str, public_key_hex: &str, witnesses: &[String]) -> String {
    use sha2::{Digest, Sha256};
    let mut sorted = witnesses.to_vec();
    sorted.sort();
    let mut h = Sha256::new();
    h.update(ceremony_id.as_bytes());
    h.update(public_key_hex.as_bytes());
    for w in &sorted {
        h.update(w.as_bytes());
    }
    hex::encode(h.finalize())
}

fn now_secs_str() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn witnesses() -> Vec<String> {
        vec!["peer-c".into(), "peer-a".into(), "peer-b".into()]
    }

    #[test]
    fn ceremony_record_verifies() {
        let rec = CeremonyRecord::new(
            "ceremony-001",
            "key-abc",
            "deadbeefdeadbeef",
            witnesses(),
        );
        assert!(
            rec.verify_integrity(),
            "freshly created ceremony record must verify"
        );
    }

    #[test]
    fn tampered_record_fails_verify() {
        let mut rec = CeremonyRecord::new(
            "ceremony-002",
            "key-def",
            "cafebabecafebabe",
            witnesses(),
        );
        // Tamper with the public_key_hex after creation.
        rec.public_key_hex = "0000000000000000".into();
        assert!(
            !rec.verify_integrity(),
            "tampered public_key_hex must fail integrity check"
        );
    }

    #[test]
    fn witness_order_independent() {
        let ordered = vec!["peer-a".into(), "peer-b".into(), "peer-c".into()];
        let reversed = vec!["peer-c".into(), "peer-b".into(), "peer-a".into()];

        let rec_ordered =
            CeremonyRecord::new("ceremony-003", "key-ghi", "aabbccdd", ordered);
        let rec_reversed =
            CeremonyRecord::new("ceremony-003", "key-ghi", "aabbccdd", reversed);

        assert_eq!(
            rec_ordered.ceremony_hash, rec_reversed.ceremony_hash,
            "witness order must not affect ceremony hash"
        );
        assert!(rec_ordered.verify_integrity());
        assert!(rec_reversed.verify_integrity());
    }
}
