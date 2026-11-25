#![allow(dead_code)]

use async_trait::async_trait;
use octocrab::Octocrab;

use crate::adapter::{AdapterError, SourceAdapter, SourceEvent};

/// Fetches open issues and pull requests from a GitHub repository.
pub struct GitHubAdapter {
    id: String,
    owner: String,
    repo: String,
    client: Octocrab,
}

impl GitHubAdapter {
    /// Create using the default (unauthenticated) octocrab client.
    pub fn new(id: impl Into<String>, owner: impl Into<String>, repo: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            owner: owner.into(),
            repo: repo.into(),
            client: Octocrab::default(),
        }
    }

    /// Create with a personal access token for authenticated requests.
    pub fn with_token(
        id: impl Into<String>,
        owner: impl Into<String>,
        repo: impl Into<String>,
        token: impl Into<String>,
    ) -> Result<Self, AdapterError> {
        let client = Octocrab::builder()
            .personal_token(token.into())
            .build()
            .map_err(|e| AdapterError::Other(e.to_string()))?;
        Ok(Self {
            id: id.into(),
            owner: owner.into(),
            repo: repo.into(),
            client,
        })
    }
}

#[async_trait]
impl SourceAdapter for GitHubAdapter {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> &str {
        "github"
    }

    async fn sync(&mut self) -> Result<Vec<SourceEvent>, AdapterError> {
        let issues = self
            .client
            .issues(&self.owner, &self.repo)
            .list()
            .send()
            .await
            .map_err(|e| AdapterError::Http(e.to_string()))?;

        let mut events = vec![];
        let now = unix_now();

        for issue in issues {
            let kind = if issue.pull_request.is_some() {
                "github.pull_request"
            } else {
                "github.issue"
            };

            let payload = serde_json::json!({
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "url": issue.html_url,
            });

            events.push(SourceEvent {
                source_id: self.id.clone(),
                kind: kind.to_owned(),
                payload,
                at_unix: now,
            });
        }

        Ok(events)
    }
}

fn unix_now() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}
