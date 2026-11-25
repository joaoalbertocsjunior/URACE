#![allow(dead_code)]

use std::time::Duration;

use async_trait::async_trait;
use reqwest::Client;

use crate::adapter::{AdapterError, SourceAdapter, SourceEvent};

/// Polls an HTTP endpoint at a fixed interval and emits the response body.
pub struct HttpPollAdapter {
    id: String,
    url: String,
    interval: Duration,
    client: Client,
    /// Timestamp of the last successful poll.
    last_poll: Option<std::time::Instant>,
}

impl HttpPollAdapter {
    pub fn new(id: impl Into<String>, url: impl Into<String>, interval: Duration) -> Self {
        Self {
            id: id.into(),
            url: url.into(),
            interval,
            client: Client::new(),
            last_poll: None,
        }
    }

    fn is_due(&self) -> bool {
        match self.last_poll {
            None => true,
            Some(last) => last.elapsed() >= self.interval,
        }
    }
}

#[async_trait]
impl SourceAdapter for HttpPollAdapter {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> &str {
        "http_poll"
    }

    async fn sync(&mut self) -> Result<Vec<SourceEvent>, AdapterError> {
        if !self.is_due() {
            return Ok(vec![]);
        }

        let response = self
            .client
            .get(&self.url)
            .send()
            .await
            .map_err(|e| AdapterError::Http(e.to_string()))?;

        let status = response.status().as_u16();
        let body = response
            .text()
            .await
            .map_err(|e| AdapterError::Http(e.to_string()))?;

        self.last_poll = Some(std::time::Instant::now());

        // Try to parse body as JSON; fall back to a string value.
        let body_value: serde_json::Value = serde_json::from_str(&body)
            .unwrap_or_else(|_| serde_json::Value::String(body));

        let payload = serde_json::json!({
            "url": self.url,
            "status": status,
            "body": body_value,
        });

        Ok(vec![SourceEvent {
            source_id: self.id.clone(),
            kind: "http.poll".to_owned(),
            payload,
            at_unix: unix_now(),
        }])
    }
}

fn unix_now() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}
