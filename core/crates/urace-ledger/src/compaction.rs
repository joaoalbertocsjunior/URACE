//! §62f governed list-field compaction: ARCHIVE and ROLLING_EVICTION modes.
//!
//! Ported from `compaction.py`. `ledger_compaction.rs` handles HMAC-chain journal
//! compaction; this module handles governed list field compaction for state dicts.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use thiserror::Error;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum CompactionFieldError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("compaction error: {0}")]
    Compaction(String),
}

// ── Governance table (§62f) ───────────────────────────────────────────────────

/// Compaction mode for a governed list field.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum CompactionMode {
    Archive,
    RollingEviction,
    Prohibited,
}

/// Retention policy for one governed list field.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionPolicy {
    pub compaction_mode: CompactionMode,
    pub max_entries: Option<usize>,
    pub max_age_days: Option<f64>,
    pub archive_subpath: Option<String>,
}

/// Built-in governance entries.
pub fn default_governance() -> HashMap<&'static str, RetentionPolicy> {
    let mut m = HashMap::new();
    let archive = |max: usize, sub: &'static str| RetentionPolicy {
        compaction_mode: CompactionMode::Archive,
        max_entries: Some(max),
        max_age_days: None,
        archive_subpath: Some(sub.to_owned()),
    };
    let rolling = |max: usize| RetentionPolicy {
        compaction_mode: CompactionMode::RollingEviction,
        max_entries: Some(max),
        max_age_days: None,
        archive_subpath: None,
    };
    let prohibited = || RetentionPolicy {
        compaction_mode: CompactionMode::Prohibited,
        max_entries: None,
        max_age_days: None,
        archive_subpath: None,
    };
    m.insert("external_metric_state.latest", rolling(1000));
    m.insert("executor_state.failures", archive(500, "archives/executor-failures"));
    m.insert("decision_records", archive(2000, "archives/decision-records"));
    m.insert("status_transitions", archive(500, "archives/status-transitions"));
    m.insert("evidence", archive(5000, "archives/evidence"));
    m.insert("operations", archive(2000, "archives/operations"));
    m.insert("trace_records", archive(1000, "archives/trace-records"));
    m.insert("community_signals", rolling(500));
    m.insert("patch_proposals", archive(500, "archives/patch-proposals"));
    m.insert("wake_registrations", archive(200, "archives/wake-registrations"));
    m.insert("compaction_manifest.events", prohibited());
    m.insert("change_history", prohibited());
    m.insert("integrity_gaps", prohibited());
    m.insert("objectives", prohibited());
    m
}

const ACTIVE_GUARD_FIELDS: &[&str] =
    &["integrity_gaps", "community_signals", "patch_proposals"];

// ── Helpers ───────────────────────────────────────────────────────────────────

/// SHA-256 of the canonical JSON serialization of `records`.
fn canonical_digest(records: &[Value]) -> String {
    let serialized = serde_json::to_string(records).unwrap_or_default();
    let hash = Sha256::digest(serialized.as_bytes());
    hex::encode(hash)
}

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    // RFC-3339 approximation (seconds-only resolution is sufficient for archive metadata)
    format!("{secs}")
}

fn make_id(prefix: &str) -> String {
    let raw: [u8; 5] = std::array::from_fn(|_| rand_byte());
    format!("{prefix}-{}", hex::encode(raw))
}

fn rand_byte() -> u8 {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    use std::time::{SystemTime, UNIX_EPOCH};
    let mut h = DefaultHasher::new();
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0)
        .hash(&mut h);
    h.finish() as u8
}

// ── Compaction manifest ───────────────────────────────────────────────────────

const MANIFEST_FILENAME: &str = "compaction-manifest.json";

/// A compaction event recorded in the manifest.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompactionEvent {
    pub id: String,
    pub target_field: String,
    pub compacted_at: String,
    pub record_count_before: usize,
    pub record_count_after: usize,
    pub compaction_mode: CompactionMode,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub archive_path: Option<String>,
    pub original_digest: String,
    pub authorized_by: String,
}

/// On-disk compaction manifest.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompactionManifest {
    pub id: String,
    pub version: usize,
    pub updated_at: String,
    pub last_compacted_at: Option<String>,
    pub events: Vec<CompactionEvent>,
}

fn manifest_path(state_path: &Path) -> PathBuf {
    state_path.join(MANIFEST_FILENAME)
}

/// Load `CompactionManifest` from disk. Returns `None` if absent.
pub fn load_manifest(state_path: &Path) -> Result<Option<CompactionManifest>, CompactionFieldError> {
    let p = manifest_path(state_path);
    if !p.exists() {
        return Ok(None);
    }
    let raw = std::fs::read_to_string(&p)?;
    let m: CompactionManifest = serde_json::from_str(&raw)?;
    Ok(Some(m))
}

fn save_manifest(state_path: &Path, manifest: &CompactionManifest) -> Result<(), CompactionFieldError> {
    let p = manifest_path(state_path);
    let tmp = p.with_extension("tmp");
    let data = serde_json::to_string_pretty(manifest)?;
    use std::io::Write;
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open(&tmp)?;
    f.write_all(data.as_bytes())?;
    f.flush()?;
    f.sync_all()?;
    drop(f);
    std::fs::rename(&tmp, &p)?;
    Ok(())
}

fn append_manifest_event(
    state_path: &Path,
    event: CompactionEvent,
) -> Result<CompactionManifest, CompactionFieldError> {
    let mut manifest = load_manifest(state_path)?.unwrap_or_else(|| CompactionManifest {
        id: make_id("man"),
        version: 0,
        updated_at: now_iso(),
        last_compacted_at: None,
        events: vec![],
    });
    manifest.events.push(event);
    manifest.version = manifest.events.len();
    manifest.updated_at = now_iso();
    manifest.last_compacted_at = Some(now_iso());
    save_manifest(state_path, &manifest)?;
    Ok(manifest)
}

// ── CompactionIndex ───────────────────────────────────────────────────────────

/// O(1) lookup index for a single archive file (§62e r3).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompactionIndex {
    pub compaction_event_id: String,
    pub archive_path: String,
    pub generated_at: String,
    pub record_count: usize,
    pub id_to_offset: HashMap<String, usize>,
    pub kind_to_ids: HashMap<String, Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub time_buckets: Option<HashMap<String, Vec<String>>>,
}

fn index_path(archive_path: &Path) -> PathBuf {
    archive_path.with_extension("idx.json")
}

fn write_index(
    archive_path: &Path,
    compaction_event_id: &str,
    records: &[Value],
) -> Result<(), CompactionFieldError> {
    let mut id_to_offset: HashMap<String, usize> = HashMap::new();
    let mut kind_to_ids: HashMap<String, Vec<String>> = HashMap::new();
    let mut time_buckets: HashMap<String, Vec<String>> = HashMap::new();

    for (i, rec) in records.iter().enumerate() {
        if let Some(obj) = rec.as_object() {
            let rid = obj.get("id").and_then(Value::as_str);
            if let Some(id) = rid {
                id_to_offset.insert(id.to_owned(), i);
                if let Some(kind) = obj.get("kind").and_then(Value::as_str) {
                    kind_to_ids.entry(kind.to_owned()).or_default().push(id.to_owned());
                }
                let ts_str = obj.get("decided_at")
                    .or_else(|| obj.get("created_at"))
                    .or_else(|| obj.get("at"))
                    .and_then(Value::as_str)
                    .unwrap_or("");
                if ts_str.len() >= 7 {
                    let bucket = &ts_str[..7];
                    time_buckets.entry(bucket.to_owned()).or_default().push(id.to_owned());
                }
            }
        }
    }

    let index = CompactionIndex {
        compaction_event_id: compaction_event_id.to_owned(),
        archive_path: archive_path.to_string_lossy().into_owned(),
        generated_at: now_iso(),
        record_count: records.len(),
        id_to_offset,
        kind_to_ids,
        time_buckets: if time_buckets.is_empty() { None } else { Some(time_buckets) },
    };

    let idx_p = index_path(archive_path);
    let tmp = idx_p.with_extension("tmp");
    use std::io::Write;
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open(&tmp)?;
    f.write_all(serde_json::to_string_pretty(&index)?.as_bytes())?;
    f.flush()?;
    f.sync_all()?;
    drop(f);
    std::fs::rename(&tmp, &idx_p)?;
    Ok(())
}

/// Load the `CompactionIndex` for `archive_path`. Returns `None` if absent or unreadable.
pub fn load_index(archive_path: &Path) -> Option<CompactionIndex> {
    let idx_p = index_path(archive_path);
    let raw = std::fs::read_to_string(&idx_p).ok()?;
    serde_json::from_str(&raw).ok()
}

// ── ArchiveAmendmentLog ───────────────────────────────────────────────────────

fn amendments_path(archive_path: &Path) -> PathBuf {
    let stem = archive_path.file_stem().unwrap_or_default().to_string_lossy();
    archive_path
        .parent()
        .unwrap_or(Path::new("."))
        .join(format!("{stem}.amendments.jsonl"))
}

/// A single in-archive record amendment (§62e r3).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArchiveAmendment {
    pub id: String,
    pub archive_path: String,
    pub record_id: String,
    pub amended_at: String,
    pub amendment_kind: String,
    pub amendment_note: String,
    pub authorized_by: String,
    pub before_digest: String,
    pub after_digest: String,
}

/// Load all `ArchiveAmendment` records for `archive_path`.
pub fn load_amendments(archive_path: &Path) -> Vec<ArchiveAmendment> {
    let p = amendments_path(archive_path);
    if !p.exists() {
        return vec![];
    }
    let raw = match std::fs::read_to_string(&p) {
        Ok(r) => r,
        Err(_) => return vec![],
    };
    raw.lines()
        .filter(|l| !l.trim().is_empty())
        .filter_map(|l| serde_json::from_str(l).ok())
        .collect()
}

fn append_amendment(
    archive_path: &Path,
    amendment: &ArchiveAmendment,
) -> Result<(), CompactionFieldError> {
    use std::io::Write;
    let p = amendments_path(archive_path);
    let mut line = serde_json::to_string(amendment)?;
    line.push('\n');
    let mut f = std::fs::OpenOptions::new().create(true).append(true).open(&p)?;
    f.write_all(line.as_bytes())?;
    f.flush()?;
    Ok(())
}

fn get_expected_digest(archive_path: &Path, original_digest: &str) -> String {
    let amendments = load_amendments(archive_path);
    if let Some(last) = amendments.last() {
        last.after_digest.clone()
    } else {
        original_digest.to_owned()
    }
}

// ── Retention threshold checking ──────────────────────────────────────────────

/// A lightweight integrity gap record emitted when retention limits are exceeded.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionGap {
    pub id: String,
    pub kind: String,
    pub at: String,
    pub description: String,
    pub severity: String,
    pub source: String,
    pub active: bool,
}

fn make_gap(kind: &str, description: &str, severity: &str) -> RetentionGap {
    RetentionGap {
        id: make_id("gap"),
        kind: kind.to_owned(),
        at: now_iso(),
        description: description.to_owned(),
        severity: severity.to_owned(),
        source: "compaction".to_owned(),
        active: true,
    }
}

/// Check whether governed list fields in `state` exceed configured ceilings.
pub fn check_retention_violations(state: &HashMap<String, Value>) -> Vec<RetentionGap> {
    let gov = default_governance();
    let mut gaps = vec![];

    let check = |field: &str, count: usize, gaps: &mut Vec<RetentionGap>| {
        if let Some(policy) = gov.get(field) {
            if policy.compaction_mode == CompactionMode::Prohibited {
                return;
            }
            if let Some(ceiling) = policy.max_entries {
                if count > ceiling {
                    gaps.push(make_gap(
                        "retention-policy-violated",
                        &format!("Field '{field}' has {count} entries, exceeding ceiling of {ceiling}"),
                        "WARNING",
                    ));
                }
            }
        }
    };

    let list_len = |key: &str| {
        state.get(key).and_then(Value::as_array).map(Vec::len).unwrap_or(0)
    };

    check("decision_records", list_len("decision_records"), &mut gaps);
    check("status_transitions", list_len("status_transitions"), &mut gaps);
    check("evidence", list_len("evidence"), &mut gaps);
    check("operations", list_len("operations"), &mut gaps);
    check("trace_records", list_len("trace_records"), &mut gaps);
    check("community_signals", list_len("community_signals"), &mut gaps);
    check("patch_proposals", list_len("patch_proposals"), &mut gaps);
    check("wake_registrations", list_len("wake_registrations"), &mut gaps);

    // Nested field: executor_state.failures
    if let Some(Value::Object(es)) = state.get("executor_state") {
        let count = es.get("failures").and_then(Value::as_array).map(Vec::len).unwrap_or(0);
        check("executor_state.failures", count, &mut gaps);
    }
    // Nested field: external_metric_state.latest
    if let Some(Value::Object(em)) = state.get("external_metric_state") {
        let count = em.get("latest").and_then(Value::as_array).map(Vec::len).unwrap_or(0);
        check("external_metric_state.latest", count, &mut gaps);
    }

    gaps
}

// ── CompactionSummary ─────────────────────────────────────────────────────────

/// Summary record injected into the live list after compaction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompactionSummary {
    pub compaction_event_id: String,
    pub record_count: usize,
    pub original_digest: String,
    pub is_decompactable: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub record_ids: Option<Vec<String>>,
}

// ── CompactionEngine ──────────────────────────────────────────────────────────

/// Performs ARCHIVE and ROLLING_EVICTION compaction on governed list fields.
pub struct CompactionEngine {
    state_path: PathBuf,
}

impl CompactionEngine {
    /// Create a new engine rooted at `state_path`.
    pub fn new(state_path: impl AsRef<Path>) -> Self {
        Self { state_path: state_path.as_ref().to_path_buf() }
    }

    /// Determine which indices in `records` are eligible for compaction under `policy`.
    fn eligible_indices(
        records: &[Value],
        policy: &RetentionPolicy,
        field_path: &str,
    ) -> Vec<usize> {
        let active_guard = ACTIVE_GUARD_FIELDS.contains(&field_path);
        let mut eligible: std::collections::BTreeSet<usize> = Default::default();

        let is_summary = |rec: &Value| {
            rec.as_object()
                .and_then(|o| o.get("compaction_event_id"))
                .is_some()
        };
        let is_active = |rec: &Value| -> bool {
            if !active_guard {
                return false;
            }
            rec.as_object()
                .and_then(|o| o.get("active"))
                .and_then(Value::as_bool)
                .unwrap_or(false)
        };
        let rec_ts = |rec: &Value| -> String {
            rec.as_object()
                .and_then(|o| {
                    o.get("decided_at")
                        .or_else(|| o.get("created_at"))
                        .or_else(|| o.get("at"))
                })
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_owned()
        };

        if let Some(max_entries) = policy.max_entries {
            if records.len() > max_entries {
                let excess = records.len() - max_entries;
                let mut with_ts: Vec<(String, usize)> = vec![];
                let mut no_ts: Vec<usize> = vec![];
                for (i, rec) in records.iter().enumerate() {
                    if is_summary(rec) || is_active(rec) {
                        continue;
                    }
                    let ts = rec_ts(rec);
                    if !ts.is_empty() {
                        with_ts.push((ts, i));
                    } else {
                        no_ts.push(i);
                    }
                }
                with_ts.sort_by(|a, b| a.0.cmp(&b.0));
                let ordered: Vec<usize> = with_ts.into_iter().map(|(_, i)| i).chain(no_ts).collect();
                for &i in ordered.iter().take(excess) {
                    eligible.insert(i);
                }
            }
        }

        eligible.into_iter().collect()
    }

    /// Compact a single governed list field in `state`.
    ///
    /// Returns `(CompactionSummary, CompactionEvent)`. Mutates `state` in place.
    pub fn compact_field(
        &self,
        state: &mut HashMap<String, Value>,
        field_path: &str,
        policy: &RetentionPolicy,
        authorized_by: &str,
    ) -> Result<(CompactionSummary, CompactionEvent), CompactionFieldError> {
        if policy.compaction_mode == CompactionMode::Prohibited {
            return Err(CompactionFieldError::Compaction(format!(
                "Compaction is PROHIBITED for field '{field_path}'"
            )));
        }

        let records = self.get_list(state, field_path)?;
        if records.is_empty() {
            return Err(CompactionFieldError::Compaction(format!(
                "Field '{field_path}' is empty; nothing to compact"
            )));
        }

        let eligible_idx = Self::eligible_indices(&records, policy, field_path);
        if eligible_idx.is_empty() {
            return Err(CompactionFieldError::Compaction(format!(
                "Field '{field_path}' has {} entries which does not exceed the configured ceiling",
                records.len()
            )));
        }

        let eligible_set: std::collections::HashSet<usize> = eligible_idx.iter().copied().collect();
        let to_compact: Vec<Value> = eligible_idx.iter().map(|&i| records[i].clone()).collect();
        let remaining: Vec<Value> = records
            .iter()
            .enumerate()
            .filter(|(i, _)| !eligible_set.contains(i))
            .map(|(_, v)| v.clone())
            .collect();

        let original_digest = canonical_digest(&to_compact);
        let event_id = make_id("cmp");

        let record_ids: Vec<String> = to_compact
            .iter()
            .filter_map(|r| r.as_object()?.get("id")?.as_str().map(str::to_owned))
            .collect();

        let mut archive_path: Option<String> = None;

        if policy.compaction_mode == CompactionMode::Archive {
            let subpath = policy
                .archive_subpath
                .as_deref()
                .unwrap_or("archives");
            let archive_dir = self
                .state_path
                .join(subpath);
            std::fs::create_dir_all(&archive_dir)?;
            let archive_filename = format!("{event_id}.json");
            let full_archive = archive_dir.join(&archive_filename);

            use std::io::Write;
            let mut f = std::fs::OpenOptions::new()
                .write(true)
                .create(true)
                .truncate(true)
                .open(&full_archive)?;
            f.write_all(serde_json::to_string_pretty(&to_compact)?.as_bytes())?;
            f.flush()?;
            f.sync_all()?;
            drop(f);

            archive_path = Some(format!("{subpath}/{archive_filename}"));

            write_index(&full_archive, &event_id, &to_compact)?;

            let manifest_event = CompactionEvent {
                id: event_id.clone(),
                target_field: field_path.to_owned(),
                compacted_at: now_iso(),
                record_count_before: records.len(),
                record_count_after: remaining.len() + 1,
                compaction_mode: CompactionMode::Archive,
                archive_path: archive_path.clone(),
                original_digest: original_digest.clone(),
                authorized_by: authorized_by.to_owned(),
            };
            append_manifest_event(&self.state_path, manifest_event)?;
        }

        let summary = CompactionSummary {
            compaction_event_id: event_id.clone(),
            record_count: to_compact.len(),
            original_digest: original_digest.clone(),
            is_decompactable: policy.compaction_mode == CompactionMode::Archive,
            record_ids: if record_ids.is_empty() { None } else { Some(record_ids) },
        };

        let summary_val = serde_json::to_value(&summary)?;
        let mut new_list = vec![summary_val];
        new_list.extend(remaining);
        self.set_list(state, field_path, new_list)?;

        let event = CompactionEvent {
            id: event_id,
            target_field: field_path.to_owned(),
            compacted_at: now_iso(),
            record_count_before: records.len(),
            record_count_after: state
                .get(field_path)
                .and_then(Value::as_array)
                .map(Vec::len)
                .unwrap_or(0),
            compaction_mode: policy.compaction_mode.clone(),
            archive_path,
            original_digest,
            authorized_by: authorized_by.to_owned(),
        };

        Ok((summary, event))
    }

    /// Restore original records from an ARCHIVE-mode compaction event.
    pub fn decompact_field(
        &self,
        state: &mut HashMap<String, Value>,
        field_path: &str,
        compaction_event_id: &str,
        authorized_by: &str,
    ) -> Result<CompactionEvent, CompactionFieldError> {
        let manifest = load_manifest(&self.state_path)?.ok_or_else(|| {
            CompactionFieldError::Compaction("No CompactionManifest found".to_owned())
        })?;

        let original_event = manifest
            .events
            .iter()
            .find(|e| e.id == compaction_event_id)
            .cloned()
            .ok_or_else(|| {
                CompactionFieldError::Compaction(format!(
                    "CompactionEvent '{compaction_event_id}' not found in manifest"
                ))
            })?;

        if original_event.compaction_mode == CompactionMode::RollingEviction {
            return Err(CompactionFieldError::Compaction(format!(
                "CompactionEvent '{compaction_event_id}' used ROLLING_EVICTION; decompaction impossible"
            )));
        }

        let archive_rel = original_event.archive_path.as_deref().ok_or_else(|| {
            CompactionFieldError::Compaction(format!(
                "CompactionEvent '{compaction_event_id}' has no archive_path"
            ))
        })?;

        let full_archive = self.state_path.join(archive_rel);
        if !full_archive.exists() {
            return Err(CompactionFieldError::Compaction(format!(
                "Archive file not found: {}", full_archive.display()
            )));
        }

        let raw = std::fs::read_to_string(&full_archive)?;
        let originals: Vec<Value> = serde_json::from_str(&raw)?;

        let restored_digest = canonical_digest(&originals);
        let expected = get_expected_digest(&full_archive, &original_event.original_digest);
        if restored_digest != expected {
            return Err(CompactionFieldError::Compaction(format!(
                "Archive digest mismatch for event '{compaction_event_id}': expected {expected}, got {restored_digest}"
            )));
        }

        let records = self.get_list(state, field_path)?;
        let summary_idx = records
            .iter()
            .position(|r| {
                r.as_object()
                    .and_then(|o| o.get("compaction_event_id"))
                    .and_then(Value::as_str)
                    == Some(compaction_event_id)
            })
            .ok_or_else(|| {
                CompactionFieldError::Compaction(format!(
                    "CompactionSummary for event '{compaction_event_id}' not found in field '{field_path}'"
                ))
            })?;

        let mut new_list = records[..summary_idx].to_vec();
        new_list.extend_from_slice(&originals);
        new_list.extend_from_slice(&records[summary_idx + 1..]);
        let count_after = new_list.len();
        self.set_list(state, field_path, new_list)?;

        let inverse_event = CompactionEvent {
            id: make_id("cmp"),
            target_field: field_path.to_owned(),
            compacted_at: now_iso(),
            record_count_before: records.len(),
            record_count_after: count_after,
            compaction_mode: CompactionMode::Archive,
            archive_path: Some(archive_rel.to_owned()),
            original_digest: original_event.original_digest.clone(),
            authorized_by: authorized_by.to_owned(),
        };

        append_manifest_event(&self.state_path, inverse_event.clone())?;

        Ok(inverse_event)
    }

    /// Amend a single record in an archive file without a full round-trip.
    pub fn amend_archived_record(
        &self,
        compaction_event_id: &str,
        record_id: &str,
        amendment_kind: &str,
        amendment_note: &str,
        authorized_by: &str,
        apply_fn: impl FnOnce(Value) -> Value,
    ) -> Result<ArchiveAmendment, CompactionFieldError> {
        let manifest = load_manifest(&self.state_path)?.ok_or_else(|| {
            CompactionFieldError::Compaction("No CompactionManifest found".to_owned())
        })?;

        let original_event = manifest
            .events
            .iter()
            .find(|e| e.id == compaction_event_id)
            .cloned()
            .ok_or_else(|| {
                CompactionFieldError::Compaction(format!(
                    "CompactionEvent '{compaction_event_id}' not found in manifest"
                ))
            })?;

        if original_event.compaction_mode == CompactionMode::RollingEviction {
            return Err(CompactionFieldError::Compaction(format!(
                "CompactionEvent '{compaction_event_id}' used ROLLING_EVICTION; amendment impossible"
            )));
        }

        let archive_rel = original_event.archive_path.as_deref().ok_or_else(|| {
            CompactionFieldError::Compaction(format!(
                "CompactionEvent '{compaction_event_id}' has no archive_path"
            ))
        })?;

        let full_archive = self.state_path.join(archive_rel);
        if !full_archive.exists() {
            return Err(CompactionFieldError::Compaction(format!(
                "Archive file not found: {}", full_archive.display()
            )));
        }

        let raw = std::fs::read_to_string(&full_archive)?;
        let mut originals: Vec<Value> = serde_json::from_str(&raw)?;

        let actual_digest = canonical_digest(&originals);
        let expected = get_expected_digest(&full_archive, &original_event.original_digest);
        if actual_digest != expected {
            return Err(CompactionFieldError::Compaction(
                "Archive digest mismatch".to_owned(),
            ));
        }

        let target_idx = originals
            .iter()
            .position(|r| {
                r.as_object()
                    .and_then(|o| o.get("id"))
                    .and_then(Value::as_str)
                    == Some(record_id)
            })
            .ok_or_else(|| {
                CompactionFieldError::Compaction(format!(
                    "Record '{record_id}' not found in archive for event '{compaction_event_id}'"
                ))
            })?;

        let before_record = originals[target_idx].clone();
        let before_digest = canonical_digest(&[before_record.clone()]);
        let after_record = apply_fn(before_record);
        let after_digest = canonical_digest(&[after_record.clone()]);
        originals[target_idx] = after_record;

        use std::io::Write;
        let tmp = full_archive.with_extension("tmp");
        let mut f = std::fs::OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&tmp)?;
        f.write_all(serde_json::to_string_pretty(&originals)?.as_bytes())?;
        f.flush()?;
        f.sync_all()?;
        drop(f);
        std::fs::rename(&tmp, &full_archive)?;

        let amendment = ArchiveAmendment {
            id: make_id("amd"),
            archive_path: full_archive.to_string_lossy().into_owned(),
            record_id: record_id.to_owned(),
            amended_at: now_iso(),
            amendment_kind: amendment_kind.to_owned(),
            amendment_note: amendment_note.to_owned(),
            authorized_by: authorized_by.to_owned(),
            before_digest,
            after_digest,
        };

        append_amendment(&full_archive, &amendment)?;
        write_index(&full_archive, compaction_event_id, &originals)?;

        Ok(amendment)
    }

    /// Return a report of what `compact_field` would do without committing.
    pub fn dry_run(
        &self,
        state: &HashMap<String, Value>,
        field_path: &str,
        policy: &RetentionPolicy,
    ) -> Result<serde_json::Map<String, Value>, CompactionFieldError> {
        let records = self.get_list_ref(state, field_path)?;
        let eligible_idx = Self::eligible_indices(&records, policy, field_path);
        let to_compact: Vec<Value> = eligible_idx.iter().map(|&i| records[i].clone()).collect();

        let mut report = serde_json::Map::new();
        report.insert("field_path".into(), Value::String(field_path.to_owned()));
        report.insert("record_count".into(), Value::Number(records.len().into()));
        report.insert("eligible_count".into(), Value::Number(to_compact.len().into()));
        report.insert("would_compact".into(), Value::Bool(!to_compact.is_empty()));
        report.insert(
            "mode".into(),
            Value::String(format!("{:?}", policy.compaction_mode)),
        );
        if !to_compact.is_empty() {
            report.insert(
                "original_digest".into(),
                Value::String(canonical_digest(&to_compact)),
            );
        }
        Ok(report)
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    fn get_list(
        &self,
        state: &HashMap<String, Value>,
        field_path: &str,
    ) -> Result<Vec<Value>, CompactionFieldError> {
        self.get_list_ref(state, field_path)
    }

    fn get_list_ref(
        &self,
        state: &HashMap<String, Value>,
        field_path: &str,
    ) -> Result<Vec<Value>, CompactionFieldError> {
        // Only supports one level of nesting (top-level key or "parent.child")
        let parts: Vec<&str> = field_path.splitn(2, '.').collect();
        let arr = if parts.len() == 1 {
            state.get(parts[0]).and_then(Value::as_array)
        } else {
            state
                .get(parts[0])
                .and_then(Value::as_object)
                .and_then(|o| o.get(parts[1]))
                .and_then(Value::as_array)
        };
        Ok(arr.cloned().unwrap_or_default())
    }

    fn set_list(
        &self,
        state: &mut HashMap<String, Value>,
        field_path: &str,
        new_list: Vec<Value>,
    ) -> Result<(), CompactionFieldError> {
        let parts: Vec<&str> = field_path.splitn(2, '.').collect();
        if parts.len() == 1 {
            state.insert(parts[0].to_owned(), Value::Array(new_list));
        } else {
            let parent = state
                .entry(parts[0].to_owned())
                .or_insert_with(|| Value::Object(serde_json::Map::new()));
            if let Value::Object(map) = parent {
                map.insert(parts[1].to_owned(), Value::Array(new_list));
            } else {
                return Err(CompactionFieldError::Compaction(format!(
                    "Field '{}' is not an object",
                    parts[0]
                )));
            }
        }
        Ok(())
    }
}

// ── Compaction status ─────────────────────────────────────────────────────────

/// Return compaction status summary for operator visibility.
pub fn get_compaction_status(state_path: &Path) -> Result<serde_json::Map<String, Value>, CompactionFieldError> {
    let manifest = load_manifest(state_path)?;
    let gov = default_governance();
    let mut archive_counts = serde_json::Map::new();

    for (field, policy) in &gov {
        if policy.compaction_mode != CompactionMode::Archive {
            continue;
        }
        if let Some(sub) = &policy.archive_subpath {
            let dir = state_path.join(sub);
            if dir.exists() {
                let count = std::fs::read_dir(&dir)
                    .map(|rd| {
                        rd.filter_map(|e| e.ok())
                            .filter(|e| {
                                let p = e.path();
                                p.extension().map(|x| x == "json").unwrap_or(false)
                                    && !p.file_stem()
                                        .and_then(|s| s.to_str())
                                        .map(|s| s.ends_with(".idx"))
                                        .unwrap_or(false)
                            })
                            .count()
                    })
                    .unwrap_or(0);
                archive_counts.insert((*field).to_owned(), Value::Number(count.into()));
            }
        }
    }

    let mut result = serde_json::Map::new();
    match manifest {
        None => {
            result.insert("has_manifest".into(), Value::Bool(false));
            result.insert("event_count".into(), Value::Number(0.into()));
            result.insert("last_compacted_at".into(), Value::Null);
        }
        Some(m) => {
            result.insert("has_manifest".into(), Value::Bool(true));
            result.insert("event_count".into(), Value::Number(m.version.into()));
            result.insert(
                "last_compacted_at".into(),
                m.last_compacted_at.map(Value::String).unwrap_or(Value::Null),
            );
        }
    }
    result.insert("archive_counts".into(), Value::Object(archive_counts));
    Ok(result)
}

// ── Startup verification ──────────────────────────────────────────────────────

/// Verify `CompactionManifest` integrity on lifecycle start. Returns gaps (may be empty).
pub fn verify_manifest_on_startup(state_path: &Path) -> Vec<RetentionGap> {
    let mut gaps = vec![];

    let manifest = match load_manifest(state_path) {
        Ok(Some(m)) => m,
        Ok(None) => return gaps,
        Err(e) => {
            gaps.push(make_gap(
                "compaction-manifest-divergence",
                &format!("CompactionManifest failed to load: {e}"),
                "BLOCKING",
            ));
            return gaps;
        }
    };

    if manifest.version != manifest.events.len() {
        gaps.push(make_gap(
            "compaction-manifest-divergence",
            &format!(
                "CompactionManifest.version={} != len(events)={}",
                manifest.version,
                manifest.events.len()
            ),
            "BLOCKING",
        ));
    }

    for event in &manifest.events {
        if event.compaction_mode != CompactionMode::Archive {
            continue;
        }
        match &event.archive_path {
            None => {
                gaps.push(make_gap(
                    "compaction-manifest-divergence",
                    &format!("CompactionEvent {} has mode ARCHIVE but no archive_path", event.id),
                    "BLOCKING",
                ));
            }
            Some(rel) => {
                let full = state_path.join(rel);
                if !full.exists() {
                    gaps.push(make_gap(
                        "compaction-manifest-divergence",
                        &format!("Archive file missing for CompactionEvent {}: {rel}", event.id),
                        "BLOCKING",
                    ));
                } else {
                    match std::fs::read_to_string(&full)
                        .ok()
                        .and_then(|s| serde_json::from_str::<Vec<Value>>(&s).ok())
                    {
                        None => {
                            gaps.push(make_gap(
                                "compaction-manifest-divergence",
                                &format!("Archive file unreadable for CompactionEvent {}", event.id),
                                "BLOCKING",
                            ));
                        }
                        Some(data) => {
                            let actual = canonical_digest(&data);
                            let expected = get_expected_digest(&full, &event.original_digest);
                            if !expected.is_empty() && actual != expected {
                                gaps.push(make_gap(
                                    "compaction-manifest-divergence",
                                    &format!(
                                        "Archive digest mismatch for CompactionEvent {}: expected {expected}, got {actual}",
                                        event.id
                                    ),
                                    "BLOCKING",
                                ));
                            }
                        }
                    }
                }
            }
        }
    }

    gaps
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tempfile::tempdir;

    fn make_state(count: usize) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        let records: Vec<Value> = (0..count)
            .map(|i| json!({"id": format!("rec-{i:04}"), "kind": "DECISION", "at": format!("2024-01-{:02}T00:00:00Z", (i % 28) + 1)}))
            .collect();
        state.insert("decision_records".to_owned(), Value::Array(records));
        state
    }

    #[test]
    fn eligible_indices_selects_oldest_first() {
        let records: Vec<Value> = vec![
            json!({"id": "a", "at": "2024-01-01"}),
            json!({"id": "b", "at": "2024-06-01"}),
            json!({"id": "c", "at": "2024-03-01"}),
        ];
        let policy = RetentionPolicy {
            compaction_mode: CompactionMode::Archive,
            max_entries: Some(2),
            max_age_days: None,
            archive_subpath: None,
        };
        let idx = CompactionEngine::eligible_indices(&records, &policy, "decision_records");
        assert_eq!(idx, vec![0]); // oldest by "at" field
    }

    #[test]
    fn compact_field_archive_produces_manifest() {
        let dir = tempdir().unwrap();
        let engine = CompactionEngine::new(dir.path());
        let mut state = make_state(2010);
        let policy = RetentionPolicy {
            compaction_mode: CompactionMode::Archive,
            max_entries: Some(2000),
            max_age_days: None,
            archive_subpath: Some("archives/decision-records".to_owned()),
        };
        let (summary, _event) = engine
            .compact_field(&mut state, "decision_records", &policy, "test-auth")
            .unwrap();
        assert!(summary.is_decompactable);
        assert!(summary.record_count > 0);
        let m = load_manifest(dir.path()).unwrap().unwrap();
        assert_eq!(m.events.len(), 1);
    }

    #[test]
    fn prohibited_field_rejected() {
        let dir = tempdir().unwrap();
        let engine = CompactionEngine::new(dir.path());
        let mut state = HashMap::new();
        state.insert("change_history".to_owned(), Value::Array(vec![json!({"id": "x"}); 10]));
        let policy = RetentionPolicy {
            compaction_mode: CompactionMode::Prohibited,
            max_entries: Some(5),
            max_age_days: None,
            archive_subpath: None,
        };
        let res = engine.compact_field(&mut state, "change_history", &policy, "auth");
        assert!(res.is_err());
    }

    #[test]
    fn retention_violations_detected() {
        let mut state = HashMap::new();
        let records: Vec<Value> = (0..2500).map(|i| json!({"id": i})).collect();
        state.insert("decision_records".to_owned(), Value::Array(records));
        let gaps = check_retention_violations(&state);
        assert!(!gaps.is_empty());
        assert_eq!(gaps[0].kind, "retention-policy-violated");
    }

    #[test]
    fn rolling_eviction_compact_and_no_archive() {
        let dir = tempdir().unwrap();
        let engine = CompactionEngine::new(dir.path());
        let mut state = HashMap::new();
        let records: Vec<Value> = (0..600).map(|i| json!({"id": format!("sig-{i}")})).collect();
        state.insert("community_signals".to_owned(), Value::Array(records));
        let policy = RetentionPolicy {
            compaction_mode: CompactionMode::RollingEviction,
            max_entries: Some(500),
            max_age_days: None,
            archive_subpath: None,
        };
        let (summary, _event) = engine
            .compact_field(&mut state, "community_signals", &policy, "auth")
            .unwrap();
        assert!(!summary.is_decompactable);
        // No manifest created for rolling eviction
        assert!(load_manifest(dir.path()).unwrap().is_none());
    }
}
