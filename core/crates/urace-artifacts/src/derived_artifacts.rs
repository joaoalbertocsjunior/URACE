//! Immutable derivation artifacts and verifiable saved references.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DerivedArtifactError {
    #[error("artifact exceeds 2 MiB")]
    TooLarge,
    #[error("existing immutable artifact conflicts with new content")]
    Conflict,
    #[error("legacy reference has no retained content hash")]
    LegacyReference,
    #[error("invalid stored SHA-256")]
    InvalidHash,
    #[error("path traversal or missing artifact file")]
    BadPath,
    #[error("reference or artifact fields disagree: {0}")]
    FieldMismatch(String),
    #[error("content hash changed")]
    ContentChanged,
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

const MAX_ARTIFACT_BYTES: usize = 2 * 1024 * 1024; // 2 MiB

/// Serializable artifact payload (all fields except `content_hash`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DerivedArtifact {
    #[serde(flatten)]
    pub fields: HashMap<String, serde_json::Value>,
}

/// A saved reference pointing at a stored artifact.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactRef {
    #[serde(flatten)]
    pub fields: HashMap<String, serde_json::Value>,
}

/// Compute SHA-256 of JSON-serialized artifact fields (excluding `content_hash`).
pub fn content_hash(artifact: &HashMap<String, serde_json::Value>) -> String {
    let filtered: std::collections::BTreeMap<_, _> = artifact
        .iter()
        .filter(|(k, _)| k.as_str() != "content_hash")
        .collect();
    let canonical = serde_json::to_vec(&filtered).unwrap_or_default();
    let mut h = Sha256::new();
    h.update(&canonical);
    hex::encode(h.finalize())
}

/// Compute SHA-256 of JSON-serialized reference fields (excluding `id` and `reference_sha256`).
pub fn reference_hash(ref_fields: &HashMap<String, serde_json::Value>) -> String {
    let filtered: std::collections::BTreeMap<_, _> = ref_fields
        .iter()
        .filter(|(k, _)| k.as_str() != "id" && k.as_str() != "reference_sha256")
        .collect();
    let canonical = serde_json::to_vec(&filtered).unwrap_or_default();
    let mut h = Sha256::new();
    h.update(&canonical);
    hex::encode(h.finalize())
}

fn derived_artifact_path(root: &Path, digest: &str) -> PathBuf {
    root.join("derived-artifacts")
        .join(format!("{digest}.json"))
}

/// Seal an artifact: store to disk (idempotent) and return a verifiable ref.
pub fn seal(
    mut ref_fields: HashMap<String, serde_json::Value>,
    mut artifact_fields: HashMap<String, serde_json::Value>,
    state_root: &Path,
) -> Result<ArtifactRef, DerivedArtifactError> {
    // Remove stale content_hash before computing
    artifact_fields.remove("content_hash");
    let digest = content_hash(&artifact_fields);
    artifact_fields.insert(
        "content_hash".to_owned(),
        serde_json::Value::String(digest.clone()),
    );

    let path = derived_artifact_path(state_root, &digest);
    if path.exists() {
        let existing_bytes = std::fs::read(&path)?;
        let existing: HashMap<String, serde_json::Value> = serde_json::from_slice(&existing_bytes)?;
        if existing != artifact_fields {
            return Err(DerivedArtifactError::Conflict);
        }
    } else {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let data = serde_json::to_vec_pretty(&artifact_fields)?;
        std::fs::write(&path, data)?;
    }

    let relative = format!("derived-artifacts/{digest}.json");
    ref_fields.insert("content_hash".to_owned(), serde_json::Value::String(digest));
    ref_fields.insert("artifact".to_owned(), serde_json::Value::String(relative));
    let ref_hash = reference_hash(&ref_fields);
    ref_fields.insert(
        "reference_sha256".to_owned(),
        serde_json::Value::String(ref_hash),
    );

    Ok(ArtifactRef { fields: ref_fields })
}

/// Verification outcome.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyResult {
    pub id: Option<String>,
    pub expected_hash: Option<String>,
    pub status: VerifyStatus,
    pub reason: Option<String>,
    pub computed_hash: Option<String>,
    pub artifact: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum VerifyStatus {
    Verified,
    Mismatch,
    Unverifiable,
}

/// Verify a saved reference against the stored artifact.
pub fn verify(ref_fields: &HashMap<String, serde_json::Value>, state_root: &Path) -> VerifyResult {
    let id = ref_fields
        .get("manifest_id")
        .or_else(|| ref_fields.get("construct_set_id"))
        .and_then(|v| v.as_str())
        .map(str::to_owned);

    let expected = match ref_fields.get("content_hash").and_then(|v| v.as_str()) {
        Some(h) => h.to_owned(),
        None => {
            return VerifyResult {
                id,
                expected_hash: None,
                status: VerifyStatus::Unverifiable,
                reason: Some("Legacy reference has no retained content hash".to_owned()),
                computed_hash: None,
                artifact: None,
            }
        }
    };

    let re_valid = expected.len() == 64 && expected.chars().all(|c| c.is_ascii_hexdigit());
    if !re_valid {
        return VerifyResult {
            id,
            expected_hash: Some(expected),
            status: VerifyStatus::Mismatch,
            reason: Some("Invalid stored SHA-256".to_owned()),
            computed_hash: None,
            artifact: None,
        };
    }

    let relative = match ref_fields.get("artifact").and_then(|v| v.as_str()) {
        Some(r) => r.to_owned(),
        None => {
            return VerifyResult {
                id,
                expected_hash: Some(expected),
                status: VerifyStatus::Unverifiable,
                reason: Some("Legacy reference does not retain the original artifact".to_owned()),
                computed_hash: None,
                artifact: None,
            }
        }
    };

    // Structural checks
    let expected_relative = format!("derived-artifacts/{expected}.json");
    let stored_ref_hash = ref_fields
        .get("reference_sha256")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let computed_ref_hash = reference_hash(ref_fields);
    if relative != expected_relative || stored_ref_hash != computed_ref_hash {
        return VerifyResult {
            id,
            expected_hash: Some(expected),
            status: VerifyStatus::Mismatch,
            reason: Some("Saved reference metadata changed".to_owned()),
            computed_hash: None,
            artifact: None,
        };
    }

    // Read artifact file
    let path = state_root.join(&relative);
    let result: Result<VerifyResult, DerivedArtifactError> = (|| {
        let data = std::fs::read(&path)?;
        if data.len() > MAX_ARTIFACT_BYTES {
            return Err(DerivedArtifactError::TooLarge);
        }
        let artifact: HashMap<String, serde_json::Value> = serde_json::from_slice(&data)?;
        let actual = content_hash(&artifact);
        if actual != expected {
            return Err(DerivedArtifactError::ContentChanged);
        }
        if artifact.get("content_hash").and_then(|v| v.as_str()) != Some(&expected) {
            return Err(DerivedArtifactError::ContentChanged);
        }

        for field in &[
            "manifest_id",
            "construct_set_id",
            "intent",
            "spec_version",
            "generated_at",
        ] {
            if let (Some(rv), Some(av)) = (ref_fields.get(*field), artifact.get(*field)) {
                if rv != av {
                    return Err(DerivedArtifactError::FieldMismatch(field.to_string()));
                }
            }
        }

        Ok(VerifyResult {
            id: id.clone(),
            expected_hash: Some(expected.clone()),
            status: VerifyStatus::Verified,
            reason: None,
            computed_hash: Some(actual),
            artifact: Some(relative.clone()),
        })
    })();

    result.unwrap_or_else(|e| VerifyResult {
        id,
        expected_hash: Some(expected),
        status: VerifyStatus::Mismatch,
        reason: Some(e.to_string()),
        computed_hash: None,
        artifact: None,
    })
}

/// Collect unique saved references from state arrays.
pub fn saved_refs(state: &serde_json::Value) -> Vec<HashMap<String, serde_json::Value>> {
    let mut refs: Vec<HashMap<String, serde_json::Value>> = Vec::new();
    let mut seen = std::collections::HashSet::new();

    for array_key in &[
        "derivation_refs",
        "derived_manifest_refs",
        "construct_set_refs",
    ] {
        if let Some(arr) = state.get(array_key).and_then(|v| v.as_array()) {
            for row in arr {
                if let Some(obj) = row.as_object() {
                    let key = obj
                        .get("manifest_id")
                        .or_else(|| obj.get("construct_set_id"))
                        .and_then(|v| v.as_str())
                        .map(str::to_owned);
                    if let Some(k) = key {
                        if seen.insert(k) {
                            refs.push(obj.iter().map(|(a, b)| (a.clone(), b.clone())).collect());
                        }
                    }
                }
            }
        }
    }
    refs
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn make_artifact() -> HashMap<String, serde_json::Value> {
        let mut m = HashMap::new();
        m.insert("intent".to_owned(), serde_json::json!("fix bug"));
        m.insert("spec_version".to_owned(), serde_json::json!("1"));
        m
    }

    #[test]
    fn seal_creates_file_and_returns_ref() {
        let dir = TempDir::new().unwrap();
        let artifact = make_artifact();
        let ref_fields: HashMap<String, serde_json::Value> =
            [("manifest_id".to_owned(), serde_json::json!("m-1"))].into();
        let aref = seal(ref_fields, artifact, dir.path()).unwrap();
        assert!(aref.fields.contains_key("content_hash"));
        assert!(aref.fields.contains_key("reference_sha256"));
    }

    #[test]
    fn seal_idempotent() {
        let dir = TempDir::new().unwrap();
        let artifact = make_artifact();
        let ref_fields: HashMap<String, serde_json::Value> =
            [("manifest_id".to_owned(), serde_json::json!("m-2"))].into();
        let r1 = seal(ref_fields.clone(), artifact.clone(), dir.path()).unwrap();
        let r2 = seal(ref_fields, artifact, dir.path()).unwrap();
        assert_eq!(r1.fields["content_hash"], r2.fields["content_hash"]);
    }

    #[test]
    fn verify_round_trip() {
        let dir = TempDir::new().unwrap();
        let artifact = make_artifact();
        let ref_fields: HashMap<String, serde_json::Value> =
            [("manifest_id".to_owned(), serde_json::json!("m-3"))].into();
        let aref = seal(ref_fields, artifact, dir.path()).unwrap();
        let result = verify(&aref.fields, dir.path());
        assert_eq!(result.status, VerifyStatus::Verified);
    }

    #[test]
    fn verify_missing_hash_unverifiable() {
        let ref_fields: HashMap<String, serde_json::Value> = HashMap::new();
        let dir = TempDir::new().unwrap();
        let result = verify(&ref_fields, dir.path());
        assert_eq!(result.status, VerifyStatus::Unverifiable);
    }

    #[test]
    fn saved_refs_deduplicates() {
        let state = serde_json::json!({
            "derivation_refs": [{"manifest_id": "x", "v": 1}],
            "derived_manifest_refs": [{"manifest_id": "x", "v": 2}]
        });
        let refs = saved_refs(&state);
        assert_eq!(refs.len(), 1);
    }
}
