//! Resolve minted initial-ledger feature IDs to verified local source modules.
//!
//! Ported from `runtime/urace/local_feature_sources.py`.
//!
//! This module never imports or executes source files.  It only reads bytes
//! from disk and validates SHA-256 digests against stored manifests.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use thiserror::Error;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum SourceBindingError {
    #[error("I/O error reading {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("manifest JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("path traversal rejected: {0}")]
    PathTraversal(String),
    #[error("symlink rejected: {0}")]
    Symlink(String),
    #[error("invalid file-entry fields in source binding")]
    InvalidEntry,
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// A single source file recorded in an artifact_discovery binding.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SourceFileEntry {
    pub path: String,
    pub sha256: String,
    pub bytes: u64,
}

/// Outcome of a source-binding resolution attempt.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BindingStatus {
    /// Stored hashes matched all files on disk.
    VerifiedLocalImplementation,
    /// No binding info in the feature record; hashes computed fresh from tags.
    ComputedLocalBinding,
    /// No local source files found for any tag.
    NoLocalSourceBinding,
    /// Stored binding is structurally invalid (bad hash, wrong license, etc.).
    InvalidLocalSourceBinding,
    /// Stored binding was valid when published but files have changed since.
    StaleLocalSourceBinding,
}

/// Full result of a source-binding resolution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceBindingResult {
    pub status: BindingStatus,
    pub source_files: Vec<SourceFileEntry>,
    pub source_license_id: Option<String>,
    pub source_manifest_sha256: Option<String>,
    /// Always false — this module never imports or executes sources.
    pub executes_source: bool,
}

impl SourceBindingResult {
    fn no_binding() -> Self {
        Self {
            status: BindingStatus::NoLocalSourceBinding,
            source_files: vec![],
            source_license_id: None,
            source_manifest_sha256: None,
            executes_source: false,
        }
    }

    fn invalid() -> Self {
        Self {
            status: BindingStatus::InvalidLocalSourceBinding,
            source_files: vec![],
            source_license_id: None,
            source_manifest_sha256: None,
            executes_source: false,
        }
    }

    fn stale() -> Self {
        Self {
            status: BindingStatus::StaleLocalSourceBinding,
            source_files: vec![],
            source_license_id: None,
            source_manifest_sha256: None,
            executes_source: false,
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn sha256_hex(data: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(data);
    hex::encode(h.finalize())
}

fn is_valid_module_tag(tag: &str) -> bool {
    !tag.is_empty() && tag.len() <= 80 && tag.chars().all(|c| c.is_ascii_alphanumeric() || c == '_')
}

fn is_valid_source_path(path: &str) -> bool {
    let re = "runtime/urace/";
    if !path.starts_with(re) {
        return false;
    }
    let basename = &path[re.len()..];
    if !basename.ends_with(".py") {
        return false;
    }
    let stem = &basename[..basename.len() - 3];
    is_valid_module_tag(stem)
}

fn is_valid_sha256(s: &str) -> bool {
    s.len() == 64 && s.chars().all(|c| c.is_ascii_hexdigit())
}

/// Compute SHA-256 of a file on disk and return `(hex_digest, byte_count)`.
fn file_digest(path: &Path) -> Result<(String, u64), SourceBindingError> {
    let data = std::fs::read(path).map_err(|e| SourceBindingError::Io {
        path: path.to_owned(),
        source: e,
    })?;
    let len = data.len() as u64;
    Ok((sha256_hex(&data), len))
}

/// Build the canonical source-contract JSON used for the manifest hash.
/// Format matches Python: `{"files": [...sorted by path...], "license_id": "Apache-2.0"}`
fn manifest_hash(files: &[SourceFileEntry], license_id: &str) -> String {
    #[derive(Serialize)]
    struct Contract<'a> {
        files: &'a [SourceFileEntry],
        license_id: &'a str,
    }
    let contract = Contract { files, license_id };
    let json = serde_json::to_string(&contract).unwrap_or_default();
    sha256_hex(json.as_bytes())
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Verify a `SourceBindingRecord`'s stored hashes against the given checkout root.
///
/// Used for `SourceBindingRecord` entries (signed ledger) where hashes were
/// recorded at publish time.  For initial-ledger entries (no stored hashes)
/// use [`compute_local_source_binding`] instead.
pub fn resolve_local_source_binding(
    feature: &serde_json::Value,
    repo_root: &Path,
) -> Result<SourceBindingResult, SourceBindingError> {
    let discovery = match feature
        .get("artifact_discovery")
        .and_then(|v| v.as_object())
    {
        Some(d) => d,
        None => return Ok(SourceBindingResult::no_binding()),
    };

    let files_val = discovery
        .get("local_source_files")
        .and_then(|v| v.as_array());
    let license_id = discovery
        .get("source_license_id")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let manifest_sha = discovery
        .get("source_manifest_sha256")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let files_arr = match files_val {
        Some(f) if !f.is_empty() => f,
        _ => {
            // No stored binding — delegate to compute
            return compute_local_source_binding(feature, repo_root);
        }
    };

    if license_id != "Apache-2.0" || !is_valid_sha256(manifest_sha) {
        return Ok(SourceBindingResult::invalid());
    }

    let tags: Vec<&str> = feature
        .get("tags")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|t| t.as_str()).collect())
        .unwrap_or_default();

    let expected_paths: std::collections::HashSet<String> = tags
        .iter()
        .filter(|&&tag| is_valid_module_tag(tag))
        .filter_map(|&tag| {
            let rel = format!("runtime/urace/{tag}.py");
            if repo_root.join(&rel).is_file() {
                Some(rel)
            } else {
                None
            }
        })
        .collect();

    // Parse and validate supplied entries
    let mut entries: Vec<SourceFileEntry> = Vec::with_capacity(files_arr.len());
    let mut seen_paths: std::collections::HashSet<String> = std::collections::HashSet::new();

    for item in files_arr {
        let obj = match item.as_object() {
            Some(o) => o,
            None => return Ok(SourceBindingResult::invalid()),
        };
        let path = obj.get("path").and_then(|v| v.as_str()).unwrap_or("");
        let bytes = obj.get("bytes").and_then(|v| v.as_u64());
        let sha = obj.get("sha256").and_then(|v| v.as_str()).unwrap_or("");

        if !is_valid_source_path(path) || bytes.is_none() || !is_valid_sha256(sha) {
            return Ok(SourceBindingResult::invalid());
        }
        let bytes = bytes.ok_or(SourceBindingError::InvalidEntry)?;
        if !seen_paths.insert(path.to_owned()) {
            return Ok(SourceBindingResult::invalid()); // duplicate
        }
        entries.push(SourceFileEntry {
            path: path.to_owned(),
            sha256: sha.to_owned(),
            bytes,
        });
    }

    let supplied_paths: std::collections::HashSet<String> =
        entries.iter().map(|e| e.path.clone()).collect();
    if supplied_paths != expected_paths {
        return Ok(SourceBindingResult::stale());
    }

    // Verify manifest hash matches stored value
    let mut sorted_entries = entries.clone();
    sorted_entries.sort_by(|a, b| a.path.cmp(&b.path));
    let calc_manifest = manifest_hash(&sorted_entries, license_id);
    if calc_manifest != manifest_sha {
        return Ok(SourceBindingResult::invalid());
    }

    // Verify each file on disk
    let base = repo_root.join("runtime/urace");
    let base = base.canonicalize().map_err(|e| SourceBindingError::Io {
        path: base.clone(),
        source: e,
    })?;

    for entry in &entries {
        let path = repo_root.join(&entry.path);
        if path.is_symlink() {
            return Ok(SourceBindingResult::stale());
        }
        let resolved = path.canonicalize().map_err(|e| SourceBindingError::Io {
            path: path.clone(),
            source: e,
        })?;
        if !resolved.starts_with(&base) {
            return Ok(SourceBindingResult::invalid());
        }
        let (digest, size) = file_digest(&resolved)?;
        if digest != entry.sha256 || size != entry.bytes {
            return Ok(SourceBindingResult::stale());
        }
    }

    Ok(SourceBindingResult {
        status: BindingStatus::VerifiedLocalImplementation,
        source_files: sorted_entries,
        source_license_id: Some(license_id.to_owned()),
        source_manifest_sha256: Some(manifest_sha.to_owned()),
        executes_source: false,
    })
}

/// Compute a fresh source binding from feature tags without stored hashes.
///
/// Used for initial-ledger entries (which do not store source hashes in
/// `artifact_discovery`).  Returns `COMPUTED_LOCAL_BINDING` when files are
/// found, `NO_LOCAL_SOURCE_BINDING` when none match.
pub fn compute_local_source_binding(
    feature: &serde_json::Value,
    repo_root: &Path,
) -> Result<SourceBindingResult, SourceBindingError> {
    let tags: Vec<&str> = feature
        .get("tags")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|t| t.as_str()).collect())
        .unwrap_or_default();

    if tags.is_empty() {
        return Ok(SourceBindingResult::no_binding());
    }

    let base = repo_root.join("runtime/urace");
    let base_canon = match base.canonicalize() {
        Ok(p) => p,
        Err(_) => return Ok(SourceBindingResult::no_binding()),
    };

    let mut entries: Vec<SourceFileEntry> = Vec::new();
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();

    for tag in tags {
        if !is_valid_module_tag(tag) {
            continue;
        }
        let rel = format!("runtime/urace/{tag}.py");
        let path = repo_root.join(&rel);
        if path.is_symlink() || !path.is_file() {
            continue;
        }
        let resolved = match path.canonicalize() {
            Ok(p) => p,
            Err(_) => continue,
        };
        if !resolved.starts_with(&base_canon) {
            continue;
        }
        if !seen.insert(rel.clone()) {
            continue; // deduplicate
        }
        let (digest, size) = file_digest(&resolved)?;
        entries.push(SourceFileEntry {
            path: rel,
            sha256: digest,
            bytes: size,
        });
    }

    if entries.is_empty() {
        return Ok(SourceBindingResult::no_binding());
    }

    entries.sort_by(|a, b| a.path.cmp(&b.path));
    let manifest = manifest_hash(&entries, "Apache-2.0");

    Ok(SourceBindingResult {
        status: BindingStatus::ComputedLocalBinding,
        source_files: entries,
        source_license_id: Some("Apache-2.0".to_owned()),
        source_manifest_sha256: Some(manifest),
        executes_source: false,
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::io::Write;

    fn temp_repo() -> tempfile::TempDir {
        tempfile::tempdir().expect("tempdir")
    }

    fn write_file(root: &Path, rel: &str, content: &[u8]) {
        let full = root.join(rel);
        std::fs::create_dir_all(full.parent().unwrap()).unwrap();
        let mut f = std::fs::File::create(&full).unwrap();
        f.write_all(content).unwrap();
    }

    #[test]
    fn no_discovery_returns_no_binding() {
        let feature = json!({ "tags": ["my_module"] });
        let dir = temp_repo();
        let result = resolve_local_source_binding(&feature, dir.path()).unwrap();
        assert_eq!(result.status, BindingStatus::NoLocalSourceBinding);
        assert!(!result.executes_source);
    }

    #[test]
    fn compute_binding_finds_tagged_file() {
        let dir = temp_repo();
        write_file(dir.path(), "runtime/urace/my_mod.py", b"# module");
        let feature = json!({ "tags": ["my_mod"] });
        let result = compute_local_source_binding(&feature, dir.path()).unwrap();
        assert_eq!(result.status, BindingStatus::ComputedLocalBinding);
        assert_eq!(result.source_files.len(), 1);
        assert_eq!(result.source_files[0].path, "runtime/urace/my_mod.py");
        assert!(!result.executes_source);
    }

    #[test]
    fn compute_binding_no_files_gives_no_binding() {
        let dir = temp_repo();
        let feature = json!({ "tags": ["nonexistent_module"] });
        let result = compute_local_source_binding(&feature, dir.path()).unwrap();
        assert_eq!(result.status, BindingStatus::NoLocalSourceBinding);
    }

    #[test]
    fn manifest_hash_is_deterministic() {
        let entries = vec![
            SourceFileEntry {
                path: "a.py".to_owned(),
                sha256: "aa".repeat(32),
                bytes: 10,
            },
            SourceFileEntry {
                path: "b.py".to_owned(),
                sha256: "bb".repeat(32),
                bytes: 20,
            },
        ];
        let h1 = manifest_hash(&entries, "Apache-2.0");
        let h2 = manifest_hash(&entries, "Apache-2.0");
        assert_eq!(h1, h2);
        assert_eq!(h1.len(), 64);
    }

    #[test]
    fn invalid_tag_chars_rejected() {
        assert!(!is_valid_module_tag("bad-tag"));
        assert!(!is_valid_module_tag(""));
        assert!(is_valid_module_tag("good_tag_123"));
    }
}
