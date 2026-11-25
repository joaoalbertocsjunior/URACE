//! Decision records — append-only Journal-backed store.
//!
//! Ported from `decision_record.py`. Every authority decision is immutable after
//! write; provenance can be flagged REVISED or SUPERSEDED but the original row
//! is never deleted.

use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;
use urace_ledger::{Journal, JournalError};
use uuid::Uuid;

#[derive(Debug, Error)]
pub enum DecisionStoreError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("decision record not found: {0}")]
    NotFound(String),
    #[error("invalid state transition: {0}")]
    InvalidTransition(String),
    #[error("revision notice required")]
    RevisionNoticeRequired,
}

/// Provenance status of a decision record.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ProvenanceStatus {
    Current,
    ProvenanceRevised,
    Superseded,
}

/// A single decision record (§45 / §62d).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionRecord {
    pub id: String,
    pub kind: String,
    pub subject: String,
    pub outcome: String,
    pub governing_intent_ref: String,
    pub state_digest: String,
    pub authority_basis: Option<String>,
    pub provenance_status: ProvenanceStatus,
    pub decided_at: f64,
    pub revision_notice: Option<String>,
    /// Arbitrary evidence/context JSON blob.
    #[serde(default)]
    pub payload: serde_json::Value,
}

impl DecisionRecord {
    pub fn new(
        kind: impl Into<String>,
        subject: impl Into<String>,
        outcome: impl Into<String>,
        governing_intent_ref: impl Into<String>,
        state_digest: impl Into<String>,
        authority_basis: Option<String>,
        payload: serde_json::Value,
    ) -> Self {
        DecisionRecord {
            id: format!("dec-{}", &Uuid::new_v4().to_string()[..8]),
            kind: kind.into(),
            subject: subject.into(),
            outcome: outcome.into(),
            governing_intent_ref: governing_intent_ref.into(),
            state_digest: state_digest.into(),
            authority_basis,
            provenance_status: ProvenanceStatus::Current,
            decided_at: now_unix(),
            revision_notice: None,
            payload,
        }
    }

    pub fn flag_provenance_revised(
        mut self,
        notice: impl Into<String>,
    ) -> Result<Self, DecisionStoreError> {
        if self.provenance_status == ProvenanceStatus::Superseded {
            return Err(DecisionStoreError::InvalidTransition(
                "cannot flag PROVENANCE_REVISED on a SUPERSEDED record".into(),
            ));
        }
        let notice = notice.into();
        if notice.is_empty() {
            return Err(DecisionStoreError::RevisionNoticeRequired);
        }
        self.provenance_status = ProvenanceStatus::ProvenanceRevised;
        self.revision_notice = Some(notice);
        Ok(self)
    }

    pub fn supersede(mut self, notice: impl Into<String>) -> Result<Self, DecisionStoreError> {
        let notice = notice.into();
        if notice.is_empty() {
            return Err(DecisionStoreError::RevisionNoticeRequired);
        }
        self.provenance_status = ProvenanceStatus::Superseded;
        self.revision_notice = Some(notice);
        Ok(self)
    }
}

fn now_unix() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

/// Append-only Journal-backed decision store.
pub struct DecisionStore {
    journal: Arc<Journal>,
    /// In-memory index: id → record (rebuilt from journal on open).
    index: Arc<parking_lot::RwLock<Vec<DecisionRecord>>>,
}

impl DecisionStore {
    pub fn open(journal: Journal) -> Result<Self, DecisionStoreError> {
        let store = DecisionStore {
            journal: Arc::new(journal),
            index: Arc::new(parking_lot::RwLock::new(Vec::new())),
        };
        store.replay()?;
        Ok(store)
    }

    fn replay(&self) -> Result<(), DecisionStoreError> {
        let entries = self.journal.verify_integrity()?;
        let mut index = self.index.write();
        index.clear();
        for entry in &entries {
            if entry.kind == "DECISION_RECORD" {
                if let Ok(rec) = serde_json::from_value::<DecisionRecord>(entry.payload.clone()) {
                    // Apply any subsequent mutation events (append-only revisions)
                    index.push(rec);
                }
            } else if entry.kind == "DECISION_REVISED" {
                let id = entry.payload["id"].as_str().unwrap_or("");
                let notice = entry.payload["notice"].as_str().unwrap_or("").to_owned();
                if let Some(rec) = index.iter_mut().find(|r| r.id == id) {
                    rec.provenance_status = ProvenanceStatus::ProvenanceRevised;
                    rec.revision_notice = Some(notice);
                }
            } else if entry.kind == "DECISION_SUPERSEDED" {
                let id = entry.payload["id"].as_str().unwrap_or("");
                let notice = entry.payload["notice"].as_str().unwrap_or("").to_owned();
                if let Some(rec) = index.iter_mut().find(|r| r.id == id) {
                    rec.provenance_status = ProvenanceStatus::Superseded;
                    rec.revision_notice = Some(notice);
                }
            }
        }
        Ok(())
    }

    /// Append a new decision record. Returns the stored record.
    pub fn append(&self, record: DecisionRecord) -> Result<DecisionRecord, DecisionStoreError> {
        let payload = serde_json::to_value(&record).expect("serializable");
        self.journal.append("DECISION_RECORD", payload)?;
        self.index.write().push(record.clone());
        Ok(record)
    }

    /// Flag an existing record as PROVENANCE_REVISED. Appends a mutation event.
    pub fn flag_revised(
        &self,
        id: &str,
        notice: impl Into<String>,
    ) -> Result<(), DecisionStoreError> {
        let notice = notice.into();
        {
            let index = self.index.read();
            let rec = index
                .iter()
                .find(|r| r.id == id)
                .ok_or_else(|| DecisionStoreError::NotFound(id.to_owned()))?;
            if rec.provenance_status == ProvenanceStatus::Superseded {
                return Err(DecisionStoreError::InvalidTransition(
                    "cannot revise a SUPERSEDED record".into(),
                ));
            }
        }
        self.journal
            .append("DECISION_REVISED", json!({ "id": id, "notice": notice }))?;
        if let Some(rec) = self.index.write().iter_mut().find(|r| r.id == id) {
            rec.provenance_status = ProvenanceStatus::ProvenanceRevised;
            rec.revision_notice = Some(notice);
        }
        Ok(())
    }

    /// All records in append order.
    pub fn all(&self) -> Vec<DecisionRecord> {
        self.index.read().clone()
    }

    /// Look up by id.
    pub fn get(&self, id: &str) -> Option<DecisionRecord> {
        self.index.read().iter().find(|r| r.id == id).cloned()
    }

    /// IDs with provenance status PROVENANCE_REVISED.
    pub fn revised_ids(&self) -> Vec<String> {
        self.index
            .read()
            .iter()
            .filter(|r| r.provenance_status == ProvenanceStatus::ProvenanceRevised)
            .map(|r| r.id.clone())
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    const KEY: [u8; 32] = *b"decision-store-key-32bytes-pad--";

    fn make_store() -> (TempDir, DecisionStore) {
        let dir = TempDir::new().unwrap();
        let j = Journal::open(dir.path().join("decisions.jsonl"), KEY).unwrap();
        let store = DecisionStore::open(j).unwrap();
        (dir, store)
    }

    fn make_record(kind: &str) -> DecisionRecord {
        DecisionRecord::new(
            kind,
            "subject",
            "outcome",
            "intent-1",
            "digest-abc",
            None,
            json!({}),
        )
    }

    #[test]
    fn append_and_retrieve() {
        let (_dir, store) = make_store();
        let rec = store.append(make_record("WORK_SELECTION")).unwrap();
        let got = store.get(&rec.id).unwrap();
        assert_eq!(got.kind, "WORK_SELECTION");
    }

    #[test]
    fn flag_revised() {
        let (_dir, store) = make_store();
        let rec = store.append(make_record("BUDGET")).unwrap();
        store.flag_revised(&rec.id, "changed assumptions").unwrap();
        assert_eq!(
            store.get(&rec.id).unwrap().provenance_status,
            ProvenanceStatus::ProvenanceRevised
        );
        assert_eq!(store.revised_ids(), vec![rec.id]);
    }

    #[test]
    fn supersede() {
        let (_dir, _store) = make_store();
        let rec = make_record("GOAL");
        let superseded = rec.supersede("replaced by new goal").unwrap();
        assert_eq!(superseded.provenance_status, ProvenanceStatus::Superseded);
    }

    #[test]
    fn append_only_no_delete() {
        let (_dir, store) = make_store();
        store.append(make_record("R1")).unwrap();
        store.append(make_record("R2")).unwrap();
        assert_eq!(store.all().len(), 2);
        // No removal method exists — append-only invariant held by type system.
    }
}
