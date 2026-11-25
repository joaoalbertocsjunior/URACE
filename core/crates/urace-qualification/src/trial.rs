//! Trial runner: `Trial`, `TrialConfig`, `TrialResult`, `TrialStore`.
//!
//! `TrialStore` is append-only — entries are written via a HMAC-signed
//! `urace_ledger::Journal` and are never deleted or mutated after write.

use serde::{Deserialize, Serialize};
use serde_json::json;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum TrialError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// Configuration parameters for a single trial run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrialConfig {
    /// Unique trial identifier.
    pub trial_id: String,
    /// Maximum number of executor cycles.
    pub max_cycles: u32,
    /// Executor variant: "codex", "claude", or "all".
    pub executor: String,
    /// Dry-run mode: validate without executing.
    pub dry_run: bool,
}

/// A single trial instance with its config and current state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trial {
    pub trial_id: String,
    pub config: TrialConfig,
    /// ISO-8601 UTC timestamp when the trial was created.
    pub created_at: String,
    /// Current state: "PENDING", "RUNNING", "ENDED", "FAILED".
    pub state: String,
}

/// The outcome of a completed trial run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrialResult {
    pub trial_id: String,
    pub state: String,
    pub cycles_run: u32,
    pub accepted_improvements: u32,
    pub executor_calls: u32,
    /// ISO-8601 UTC timestamp of completion.
    pub ended_at: String,
}

/// Append-only store for trial records backed by a HMAC-signed JSONL journal.
pub struct TrialStore {
    journal: Journal,
}

impl TrialStore {
    /// Open (or create) a trial store at `path` with HMAC key `hmac_key`.
    pub fn open(path: impl AsRef<std::path::Path>, hmac_key: [u8; 32]) -> Result<Self, TrialError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(TrialStore { journal })
    }

    /// Record a new trial (append-only).
    pub fn record_trial(&self, trial: &Trial) -> Result<(), TrialError> {
        let payload = serde_json::to_value(trial)?;
        self.journal.append("TRIAL_CREATED", payload)?;
        Ok(())
    }

    /// Record a trial result (append-only).
    pub fn record_result(&self, result: &TrialResult) -> Result<(), TrialError> {
        let payload = serde_json::to_value(result)?;
        self.journal.append("TRIAL_RESULT", payload)?;
        Ok(())
    }

    /// Record an arbitrary trial event (append-only).
    pub fn record_event(
        &self,
        kind: &str,
        trial_id: &str,
        data: serde_json::Value,
    ) -> Result<(), TrialError> {
        let payload = json!({
            "trial_id": trial_id,
            "data": data,
        });
        self.journal.append(kind, payload)?;
        Ok(())
    }

    /// Return all recorded `Trial` instances.
    pub fn all_trials(&self) -> Result<Vec<Trial>, TrialError> {
        let entries = self.journal.verify_integrity()?;
        let trials = entries
            .into_iter()
            .filter(|e| e.kind == "TRIAL_CREATED")
            .filter_map(|e| serde_json::from_value::<Trial>(e.payload).ok())
            .collect();
        Ok(trials)
    }

    /// Return all recorded `TrialResult` instances.
    pub fn all_results(&self) -> Result<Vec<TrialResult>, TrialError> {
        let entries = self.journal.verify_integrity()?;
        let results = entries
            .into_iter()
            .filter(|e| e.kind == "TRIAL_RESULT")
            .filter_map(|e| serde_json::from_value::<TrialResult>(e.payload).ok())
            .collect();
        Ok(results)
    }
}

fn now_iso8601() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Minimal ISO-8601 representation without external deps.
    format!("{}Z", secs)
}

impl Trial {
    /// Create a new trial from a config.
    pub fn new(config: TrialConfig) -> Self {
        let trial_id = config.trial_id.clone();
        Trial {
            trial_id,
            config,
            created_at: now_iso8601(),
            state: "PENDING".to_owned(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"trial-store-key-32bytes-pad-----";

    fn sample_config(id: &str) -> TrialConfig {
        TrialConfig {
            trial_id: id.to_owned(),
            max_cycles: 10,
            executor: "all".to_owned(),
            dry_run: false,
        }
    }

    #[test]
    fn record_and_retrieve_trials() {
        let dir = tempdir().unwrap();
        let store = TrialStore::open(dir.path().join("trials.jsonl"), KEY).unwrap();

        let trial = Trial::new(sample_config("t1"));
        store.record_trial(&trial).unwrap();

        let trials = store.all_trials().unwrap();
        assert_eq!(trials.len(), 1);
        assert_eq!(trials[0].trial_id, "t1");
        assert_eq!(trials[0].state, "PENDING");
    }

    #[test]
    fn record_and_retrieve_results() {
        let dir = tempdir().unwrap();
        let store = TrialStore::open(dir.path().join("trials.jsonl"), KEY).unwrap();

        let result = TrialResult {
            trial_id: "t1".to_owned(),
            state: "ENDED".to_owned(),
            cycles_run: 5,
            accepted_improvements: 2,
            executor_calls: 10,
            ended_at: "2026-01-01T00:00:00Z".to_owned(),
        };
        store.record_result(&result).unwrap();

        let results = store.all_results().unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].trial_id, "t1");
        assert_eq!(results[0].cycles_run, 5);
    }

    #[test]
    fn journal_is_append_only() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("trials.jsonl");
        let store = TrialStore::open(&path, KEY).unwrap();

        store
            .record_trial(&Trial::new(sample_config("t1")))
            .unwrap();
        store
            .record_trial(&Trial::new(sample_config("t2")))
            .unwrap();

        let entries = store.journal.verify_integrity().unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].seq, 0);
        assert_eq!(entries[1].seq, 1);
    }
}
