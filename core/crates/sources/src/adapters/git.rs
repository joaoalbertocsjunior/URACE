#![allow(dead_code)]

use std::path::PathBuf;

use async_trait::async_trait;
use git2::Repository;

use crate::adapter::{AdapterError, SourceAdapter, SourceEvent};

/// Emits events for the most recent commits in a git repository.
pub struct GitAdapter {
    id: String,
    repo_path: PathBuf,
    /// How many recent commits to report on each sync.
    last_n: usize,
    /// OID of the last commit seen, used to avoid re-emitting.
    last_seen: Option<String>,
}

impl GitAdapter {
    pub fn new(id: impl Into<String>, repo_path: impl Into<PathBuf>, last_n: usize) -> Self {
        Self {
            id: id.into(),
            repo_path: repo_path.into(),
            last_n,
            last_seen: None,
        }
    }

    fn collect_commits(&mut self) -> Result<Vec<SourceEvent>, AdapterError> {
        let repo = Repository::open(&self.repo_path)
            .map_err(|e| AdapterError::Git(e.to_string()))?;

        let mut revwalk = repo.revwalk().map_err(|e| AdapterError::Git(e.to_string()))?;
        revwalk.push_head().map_err(|e| AdapterError::Git(e.to_string()))?;

        let mut events = vec![];
        for (i, oid_result) in revwalk.enumerate() {
            if i >= self.last_n {
                break;
            }
            let oid = oid_result.map_err(|e| AdapterError::Git(e.to_string()))?;
            let oid_str = oid.to_string();

            // Skip commits we have already reported.
            if self.last_seen.as_deref() == Some(&oid_str) {
                break;
            }

            let commit = repo.find_commit(oid).map_err(|e| AdapterError::Git(e.to_string()))?;
            let message = commit.message().unwrap_or("").to_owned();
            let author = commit.author().name().unwrap_or("unknown").to_owned();
            let time = commit.time().seconds() as f64;

            let payload = serde_json::json!({
                "oid": oid_str,
                "message": message,
                "author": author,
            });

            events.push(SourceEvent {
                source_id: self.id.clone(),
                kind: "git.commit".to_owned(),
                payload,
                at_unix: time,
            });
        }

        // Remember the most recent commit.
        if let Some(first) = events.first() {
            self.last_seen = Some(
                first
                    .payload
                    .get("oid")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_owned(),
            );
        }

        Ok(events)
    }
}

#[async_trait]
impl SourceAdapter for GitAdapter {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> &str {
        "git"
    }

    async fn sync(&mut self) -> Result<Vec<SourceEvent>, AdapterError> {
        self.collect_commits()
    }
}
