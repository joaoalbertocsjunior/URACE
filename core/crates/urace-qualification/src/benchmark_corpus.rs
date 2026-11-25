//! Benchmark corpus — 10 BudgetTracker improvement tasks + frozen corpus management.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use thiserror::Error;

/// Sha-256 hex of a canonically-serialized value.
pub fn canonical_sha256(value: &serde_json::Value) -> String {
    let canonical = serde_json::to_string(value).unwrap_or_default();
    let mut h = Sha256::new();
    h.update(canonical.as_bytes());
    hex::encode(h.finalize())
}

fn sha256_bytes(data: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(data);
    hex::encode(h.finalize())
}

#[derive(Debug, Error)]
pub enum CorpusError {
    #[error("corpus is frozen: an arm has already started")]
    Frozen,
    #[error("task list must be non-empty")]
    EmptyTasks,
    #[error("task {0} is missing required field: {1}")]
    MissingField(String, &'static str),
    #[error("duplicate task_id: {0}")]
    DuplicateTaskId(String),
    #[error("corpus file modified after freezing")]
    IntegrityError,
    #[error("corpus not found; call freeze_corpus first")]
    NotFound,
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

/// A single benchmark improvement task.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkTask {
    pub task_id: String,
    pub difficulty: String,
    pub title: String,
    pub input: String,
    pub acceptance_criteria: String,
    pub value_rubric: String,
    pub target_method: String,
    pub gap_kind: String,
}

/// Frozen corpus record (one JSONL line).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorpusRecord {
    pub schema: String,
    pub task_id: String,
    pub task_sha256: String,
    pub input: String,
    pub acceptance_criteria: String,
    pub value_rubric: String,
    pub product_id: String,
    pub source_ref: String,
    pub frozen_at: i64,
}

/// Corpus manifest (corpus_manifest.json).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorpusManifest {
    pub schema: String,
    pub task_count: usize,
    pub corpus_sha256: String,
    pub product_id: String,
    pub source_ref: String,
    pub frozen_at: i64,
}

/// Canonical 10-task benchmark corpus for BudgetTracker v1.
pub fn benchmark_tasks() -> Vec<BenchmarkTask> {
    vec![
        BenchmarkTask {
            task_id: "easy-001".into(),
            difficulty: "easy".into(),
            title: "Fix off-by-one in export_summary".into(),
            input: "The export_summary() method skips the last transaction because it iterates \
                    range(len(transactions)-1). Fix the loop so all transactions are included."
                .into(),
            acceptance_criteria: "test_export_summary_includes_all passes".into(),
            value_rubric: "1.0 if test passes; 0.0 otherwise".into(),
            target_method: "export_summary".into(),
            gap_kind: "bug".into(),
        },
        BenchmarkTask {
            task_id: "easy-002".into(),
            difficulty: "easy".into(),
            title: "Fix top_categories returns n+1 items".into(),
            input: "top_categories(n) returns n+1 items due to slice [:n+1]. Fix it to return \
                    exactly n categories."
                .into(),
            acceptance_criteria: "test_top_categories_returns_n passes".into(),
            value_rubric: "1.0 if test passes; 0.0 otherwise".into(),
            target_method: "top_categories".into(),
            gap_kind: "bug".into(),
        },
        BenchmarkTask {
            task_id: "easy-003".into(),
            difficulty: "easy".into(),
            title: "Fix days_since_last_transaction returns negative value".into(),
            input: "days_since_last_transaction computes (last_date - today) instead of \
                    (today - last_date). Fix the sign."
                .into(),
            acceptance_criteria: "test_days_since_last_transaction_positive passes".into(),
            value_rubric: "1.0 if test passes; 0.0 otherwise".into(),
            target_method: "days_since_last_transaction".into(),
            gap_kind: "bug".into(),
        },
        BenchmarkTask {
            task_id: "medium-001".into(),
            difficulty: "medium".into(),
            title: "Implement import_csv".into(),
            input: "Implement import_csv(filepath). Read a CSV with columns id, amount, category, \
                    description, date. Call add_transaction() per row. Raise ValueError on missing column."
                .into(),
            acceptance_criteria: "test_import_csv_implemented passes".into(),
            value_rubric: "1.0 if import_csv no longer raises NotImplementedError and correctly \
                           imports transactions; 0.0 otherwise"
                .into(),
            target_method: "import_csv".into(),
            gap_kind: "stub".into(),
        },
        BenchmarkTask {
            task_id: "medium-002".into(),
            difficulty: "medium".into(),
            title: "Implement forecast_spending".into(),
            input: "Implement forecast_spending(months_ahead). Compute average monthly spending per \
                    category. Return [{month_offset, category, projected_amount}]."
                .into(),
            acceptance_criteria: "test_forecast_spending_implemented passes".into(),
            value_rubric: "1.0 if implemented and returns valid list; 0.0 otherwise".into(),
            target_method: "forecast_spending".into(),
            gap_kind: "stub".into(),
        },
        BenchmarkTask {
            task_id: "medium-003".into(),
            difficulty: "medium".into(),
            title: "Implement categorize_uncategorized".into(),
            input: "Implement categorize_uncategorized(rules) mapping category names to keyword \
                    lists. Return count of transactions updated."
                .into(),
            acceptance_criteria: "test_categorize_uncategorized_implemented passes".into(),
            value_rubric: "1.0 if implemented and returns int count; 0.0 otherwise".into(),
            target_method: "categorize_uncategorized".into(),
            gap_kind: "stub".into(),
        },
        BenchmarkTask {
            task_id: "medium-004".into(),
            difficulty: "medium".into(),
            title: "Implement merge_accounts".into(),
            input: "Implement merge_accounts(other_tracker) which copies all transactions from \
                    other_tracker into this tracker. Duplicates allowed."
                .into(),
            acceptance_criteria: "test_merge_accounts_implemented passes".into(),
            value_rubric: "1.0 if implemented and transactions are merged correctly; 0.0 otherwise"
                .into(),
            target_method: "merge_accounts".into(),
            gap_kind: "stub".into(),
        },
        BenchmarkTask {
            task_id: "hard-001".into(),
            difficulty: "hard".into(),
            title: "Reduce cyclomatic complexity of find_anomalies".into(),
            input: "find_anomalies() has cyclomatic complexity > 10 due to 4+ levels of nested \
                    ifs. Refactor to flat logic or helper functions. Behavior must be unchanged."
                .into(),
            acceptance_criteria: "test_find_anomalies_refactored passes".into(),
            value_rubric: "1.0 if complexity reduced and behavior unchanged; 0.0 otherwise".into(),
            target_method: "find_anomalies".into(),
            gap_kind: "complexity".into(),
        },
        BenchmarkTask {
            task_id: "hard-002".into(),
            difficulty: "hard".into(),
            title: "Optimize transaction_report from O(n^2) to O(n)".into(),
            input: "transaction_report() has O(n^2) complexity. Refactor to use a dict or Counter \
                    for a single O(n) pass."
                .into(),
            acceptance_criteria: "test_transaction_report_linear_pass passes".into(),
            value_rubric: "1.0 if O(n) implementation and output matches; 0.0 otherwise".into(),
            target_method: "transaction_report".into(),
            gap_kind: "complexity".into(),
        },
        BenchmarkTask {
            task_id: "hard-003".into(),
            difficulty: "hard".into(),
            title: "Remove code duplication in validate_all".into(),
            input: "validate_all() has the same 3-line validation block copy-pasted 3 times. \
                    Extract into _validate_transaction(t) and call once per transaction."
                .into(),
            acceptance_criteria: "test_validate_all_no_duplication passes".into(),
            value_rubric: "1.0 if duplication removed and validation correct; 0.0 otherwise"
                .into(),
            target_method: "validate_all".into(),
            gap_kind: "complexity".into(),
        },
    ]
}

/// Freeze tasks into output_dir/corpus.jsonl + corpus_manifest.json.
pub fn freeze_corpus(
    tasks: &[BenchmarkTask],
    output_dir: &Path,
    product_id: &str,
    source_ref: &str,
) -> Result<CorpusManifest, CorpusError> {
    if output_dir.join("arm_started.marker").exists() {
        return Err(CorpusError::Frozen);
    }
    if tasks.is_empty() {
        return Err(CorpusError::EmptyTasks);
    }

    let frozen_at = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let mut seen: HashMap<String, bool> = HashMap::new();
    let mut records: Vec<CorpusRecord> = Vec::new();

    for task in tasks {
        let tid = &task.task_id;
        if tid.trim().is_empty() {
            return Err(CorpusError::MissingField(tid.clone(), "task_id"));
        }
        if seen.insert(tid.clone(), true).is_some() {
            return Err(CorpusError::DuplicateTaskId(tid.clone()));
        }
        for (field_val, field_name) in [
            (&task.input, "input"),
            (&task.acceptance_criteria, "acceptance_criteria"),
            (&task.value_rubric, "value_rubric"),
        ] {
            if field_val.trim().is_empty() {
                return Err(CorpusError::MissingField(tid.clone(), field_name));
            }
        }
        let task_sha256 = canonical_sha256(&serde_json::json!({
            "task_id": tid,
            "input": task.input,
            "acceptance_criteria": task.acceptance_criteria,
            "value_rubric": task.value_rubric,
        }));
        records.push(CorpusRecord {
            schema: "urace-measurement-corpus-v1".into(),
            task_id: tid.clone(),
            task_sha256,
            input: task.input.clone(),
            acceptance_criteria: task.acceptance_criteria.clone(),
            value_rubric: task.value_rubric.clone(),
            product_id: product_id.to_string(),
            source_ref: source_ref.to_string(),
            frozen_at,
        });
    }

    std::fs::create_dir_all(output_dir)?;
    let lines: Vec<String> = records
        .iter()
        .map(|r| serde_json::to_string(r).unwrap_or_default())
        .collect();
    let corpus_bytes = (lines.join("\n") + "\n").into_bytes();
    let corpus_path = output_dir.join("corpus.jsonl");
    std::fs::write(&corpus_path, &corpus_bytes)?;

    let manifest = CorpusManifest {
        schema: "urace-corpus-manifest-v1".into(),
        task_count: records.len(),
        corpus_sha256: sha256_bytes(&corpus_bytes),
        product_id: product_id.to_string(),
        source_ref: source_ref.to_string(),
        frozen_at,
    };
    std::fs::write(
        output_dir.join("corpus_manifest.json"),
        serde_json::to_string_pretty(&manifest)?,
    )?;
    Ok(manifest)
}

/// Load and integrity-verify a frozen corpus from output_dir.
pub fn load_corpus(corpus_dir: &Path) -> Result<Vec<CorpusRecord>, CorpusError> {
    let manifest_path = corpus_dir.join("corpus_manifest.json");
    let corpus_path = corpus_dir.join("corpus.jsonl");
    if !manifest_path.exists() || !corpus_path.exists() {
        return Err(CorpusError::NotFound);
    }
    let manifest: CorpusManifest = serde_json::from_str(&std::fs::read_to_string(&manifest_path)?)?;
    let corpus_bytes = std::fs::read(&corpus_path)?;
    let actual_sha = sha256_bytes(&corpus_bytes);
    if actual_sha != manifest.corpus_sha256 {
        return Err(CorpusError::IntegrityError);
    }
    let records: Vec<CorpusRecord> = std::str::from_utf8(&corpus_bytes)
        .unwrap_or_default()
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(serde_json::from_str)
        .collect::<Result<_, _>>()?;
    if records.len() != manifest.task_count {
        return Err(CorpusError::IntegrityError);
    }
    Ok(records)
}

/// Mark arm as started (makes corpus immutable to freeze_corpus).
pub fn mark_arm_started(corpus_dir: &Path, arm: &str) -> Result<(), CorpusError> {
    if !corpus_dir.exists() {
        return Err(CorpusError::NotFound);
    }
    let marker = corpus_dir.join("arm_started.marker");
    if !marker.exists() {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        std::fs::write(
            &marker,
            serde_json::to_string(&serde_json::json!({"arm": arm, "started_at": now}))?,
        )?;
    }
    Ok(())
}

/// Qualification corpus: bad implementations that pass the narrow gate but fail the extended gate.
pub fn qualification_bad_fix_ids() -> Vec<&'static str> {
    vec![
        "qbad-easy-001",
        "qbad-easy-002",
        "qbad-medium-001",
        "qbad-hard-002",
        "qbad-hard-003",
    ]
}

/// Map bad-fix task id to the corresponding good task id.
pub fn bad_to_good_task(bad_id: &str) -> Option<&'static str> {
    match bad_id {
        "qbad-easy-001" => Some("easy-001"),
        "qbad-easy-002" => Some("easy-002"),
        "qbad-medium-001" => Some("medium-001"),
        "qbad-hard-002" => Some("hard-002"),
        "qbad-hard-003" => Some("hard-003"),
        _ => None,
    }
}

/// Fully-qualified path to a corpus dir within output_dir.
pub fn corpus_dir(output_dir: &Path) -> PathBuf {
    output_dir.join("corpus")
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn benchmark_tasks_count() {
        assert_eq!(benchmark_tasks().len(), 10);
    }

    #[test]
    fn all_tasks_have_non_empty_fields() {
        for t in benchmark_tasks() {
            assert!(!t.task_id.is_empty());
            assert!(!t.input.is_empty());
            assert!(!t.acceptance_criteria.is_empty());
            assert!(!t.gap_kind.is_empty());
        }
    }

    #[test]
    fn freeze_and_load_roundtrip() {
        let dir = TempDir::new().unwrap();
        let tasks = benchmark_tasks();
        let manifest = freeze_corpus(&tasks, dir.path(), "test-product", "test-ref").unwrap();
        assert_eq!(manifest.task_count, 10);
        let loaded = load_corpus(dir.path()).unwrap();
        assert_eq!(loaded.len(), 10);
    }

    #[test]
    fn freeze_rejects_already_started_arm() {
        let dir = TempDir::new().unwrap();
        let tasks = benchmark_tasks();
        freeze_corpus(&tasks, dir.path(), "prod", "ref").unwrap();
        mark_arm_started(dir.path(), "control").unwrap();
        let err = freeze_corpus(&tasks, dir.path(), "prod", "ref").unwrap_err();
        assert!(matches!(err, CorpusError::Frozen));
    }

    #[test]
    fn load_detects_corpus_tampering() {
        let dir = TempDir::new().unwrap();
        let tasks = benchmark_tasks();
        freeze_corpus(&tasks, dir.path(), "prod", "ref").unwrap();
        // Corrupt the corpus file
        let path = dir.path().join("corpus.jsonl");
        let mut content = std::fs::read_to_string(&path).unwrap();
        content.push_str("corruption");
        std::fs::write(&path, content).unwrap();
        assert!(matches!(
            load_corpus(dir.path()),
            Err(CorpusError::IntegrityError)
        ));
    }
}
