//! Active HTTP collector for external GitHub/metric sources.
//!
//! `collect` fetches metrics from configured external sources (GitHub repos, HTTP endpoints)
//! and returns observations. `score_delta_from_external` derives a score delta from collected
//! state. `export_metrics_sink` writes observations to a configured file or HTTP sink.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use thiserror::Error;

// ── Errors ───────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ExternalMetricsError {
    #[error("HTTP request failed for {url}: {source}")]
    Http { url: String, source: reqwest::Error },

    #[error("response body exceeds {max_bytes} bytes for {url}")]
    ResponseTooLarge { url: String, max_bytes: usize },

    #[error("JSON parse error for {url}: {source}")]
    JsonParse { url: String, source: serde_json::Error },

    #[error("source schema mismatch — metric path {path:?} not found or not scalar")]
    SourceSchemaMismatch { path: String },

    #[error("unsupported source kind: {kind:?}")]
    UnsupportedKind { kind: String },

    #[error("file I/O error at {path}: {source}")]
    Io { path: PathBuf, source: std::io::Error },

    #[error("max_response_bytes must be at least 1024")]
    MaxBytesTooSmall,

    #[error("http_json source requires an http or https URL")]
    InvalidScheme,

    #[error("credential environment variable {name} is unavailable")]
    MissingCredential { name: String },

    #[error("sink configuration error: {0}")]
    Sink(String),

    #[error("GitHub repository response missing expected fields: {fields}")]
    MissingGitHubFields { fields: String },
}

// ── Public record types ───────────────────────────────────────────────────────

/// A single external event (issue, PR, release, push).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExternalEvent {
    pub kind: String,
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub number: Option<i64>,
    pub state: String,
    pub title: String,
    pub updated_at: String,
    pub url: String,
    pub untrusted_content: bool,
}

/// One observation from a single configured source.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Observation {
    pub source: String,
    pub visibility: String,
    pub values: HashMap<String, f64>,
    pub events: Vec<ExternalEvent>,
}

/// A per-source error captured during collection (non-fatal for other sources).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceError {
    pub source: String,
    pub error: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_known_good: Option<Value>,
}

/// Full result returned by `collect`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CollectResult {
    pub at: String,
    pub mode: String,
    pub observations: Vec<Observation>,
    pub errors: Vec<SourceError>,
    pub last_known_good: HashMap<String, Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sink_result: Option<ExportResult>,
}

/// Result returned by `export_metrics_sink`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportResult {
    pub sink_kind: Option<String>,
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub http_status: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

// ── Internal helpers ──────────────────────────────────────────────────────────

/// Fetch a URL and return the parsed JSON body, bounding response size.
async fn get_json(
    client: &reqwest::Client,
    url: &str,
    max_bytes: usize,
    extra_headers: Option<HashMap<String, String>>,
) -> Result<Value, ExternalMetricsError> {
    let mut req = client
        .get(url)
        .header("Accept", "application/vnd.github+json")
        .header("User-Agent", "URACE-metrics");
    if let Some(headers) = extra_headers {
        for (k, v) in headers {
            req = req.header(&k, &v);
        }
    }
    let resp = req
        .send()
        .await
        .map_err(|e| ExternalMetricsError::Http { url: url.to_owned(), source: e })?;
    let bytes = resp
        .bytes()
        .await
        .map_err(|e| ExternalMetricsError::Http { url: url.to_owned(), source: e })?;
    if bytes.len() > max_bytes {
        return Err(ExternalMetricsError::ResponseTooLarge {
            url: url.to_owned(),
            max_bytes,
        });
    }
    serde_json::from_slice(&bytes)
        .map_err(|e| ExternalMetricsError::JsonParse { url: url.to_owned(), source: e })
}

/// Fetch GitHub repository data and return (values, events).
async fn fetch_github_repository(
    client: &reqwest::Client,
    repo_slug: &str,
    max_bytes: usize,
) -> Result<(HashMap<String, f64>, Vec<ExternalEvent>), ExternalMetricsError> {
    let (owner, repo) = repo_slug
        .split_once('/')
        .ok_or_else(|| ExternalMetricsError::UnsupportedKind {
            kind: format!("invalid repository slug: {repo_slug}"),
        })?;
    let base = format!("https://api.github.com/repos/{owner}/{repo}");

    let repo_data = get_json(client, &base, max_bytes, None).await?;
    let issues_url = format!("{base}/issues?state=all&sort=updated&direction=desc&per_page=20");
    let issues: Value = get_json(client, &issues_url, max_bytes, None).await?;
    let pulls_url = format!("{base}/pulls?state=all&sort=updated&direction=desc&per_page=20");
    let pulls: Value = get_json(client, &pulls_url, max_bytes, None).await?;
    let releases_url = format!("{base}/releases?per_page=10");
    let releases: Value = get_json(client, &releases_url, max_bytes, None).await?;

    let mut events: Vec<ExternalEvent> = Vec::new();

    // Issues (excluding PRs — GitHub includes PRs in /issues endpoint)
    if let Some(arr) = issues.as_array() {
        for item in arr {
            if item.get("pull_request").is_some() {
                continue;
            }
            let updated_at = item["updated_at"].as_str().unwrap_or("").to_owned();
            if updated_at.is_empty() {
                continue;
            }
            events.push(ExternalEvent {
                kind: "issue".to_owned(),
                id: item["id"].to_string(),
                number: item["number"].as_i64(),
                state: item["state"].as_str().unwrap_or("").to_owned(),
                title: item["title"].as_str().unwrap_or("").to_owned(),
                updated_at,
                url: item["html_url"].as_str().unwrap_or("").to_owned(),
                untrusted_content: true,
            });
        }
    }

    // Pull requests
    if let Some(arr) = pulls.as_array() {
        for item in arr {
            let updated_at = item["updated_at"].as_str().unwrap_or("").to_owned();
            if updated_at.is_empty() {
                continue;
            }
            events.push(ExternalEvent {
                kind: "pull_request".to_owned(),
                id: item["id"].to_string(),
                number: item["number"].as_i64(),
                state: item["state"].as_str().unwrap_or("").to_owned(),
                title: item["title"].as_str().unwrap_or("").to_owned(),
                updated_at,
                url: item["html_url"].as_str().unwrap_or("").to_owned(),
                untrusted_content: true,
            });
        }
    }

    // Releases
    if let Some(arr) = releases.as_array() {
        for item in arr {
            let updated_at = item["published_at"]
                .as_str()
                .or_else(|| item["created_at"].as_str())
                .unwrap_or("")
                .to_owned();
            if updated_at.is_empty() {
                continue;
            }
            let state = if item["draft"].as_bool().unwrap_or(false) {
                "draft".to_owned()
            } else {
                "published".to_owned()
            };
            let title = item["name"]
                .as_str()
                .or_else(|| item["tag_name"].as_str())
                .unwrap_or("")
                .to_owned();
            events.push(ExternalEvent {
                kind: "release".to_owned(),
                id: item["id"].to_string(),
                number: None,
                state,
                title,
                updated_at,
                url: item["html_url"].as_str().unwrap_or("").to_owned(),
                untrusted_content: true,
            });
        }
    }

    // Repository push
    let pushed_at = repo_data["pushed_at"]
        .as_str()
        .or_else(|| repo_data["updated_at"].as_str())
        .unwrap_or("")
        .to_owned();
    if !pushed_at.is_empty() {
        events.push(ExternalEvent {
            kind: "repository_push".to_owned(),
            id: repo_data["full_name"].as_str().unwrap_or("").to_owned(),
            number: None,
            state: "observed".to_owned(),
            title: format!(
                "default branch {}",
                repo_data["default_branch"].as_str().unwrap_or("unknown")
            ),
            updated_at: pushed_at,
            url: repo_data["html_url"].as_str().unwrap_or("").to_owned(),
            untrusted_content: false,
        });
    }

    // Sort descending by updated_at
    events.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    events.truncate(50);

    // Build values map — fail hard on missing expected fields
    let required = ["stargazers_count", "forks_count", "subscribers_count", "open_issues_count"];
    let missing: Vec<&str> = required
        .iter()
        .copied()
        .filter(|k| repo_data.get(k).and_then(|v| v.as_i64()).is_none())
        .collect();
    if !missing.is_empty() {
        return Err(ExternalMetricsError::MissingGitHubFields {
            fields: missing.join(", "),
        });
    }
    let mut values = HashMap::new();
    values.insert("stars".to_owned(), repo_data["stargazers_count"].as_f64().unwrap_or(0.0));
    values.insert("forks".to_owned(), repo_data["forks_count"].as_f64().unwrap_or(0.0));
    values.insert("watching".to_owned(), repo_data["subscribers_count"].as_f64().unwrap_or(0.0));
    values.insert(
        "open_issues_and_pulls".to_owned(),
        repo_data["open_issues_count"].as_f64().unwrap_or(0.0),
    );

    Ok((values, events))
}

/// Walk a dotted path into a JSON value and return a finite f64 scalar.
fn lookup_path(value: &Value, path: &str) -> Result<f64, ExternalMetricsError> {
    let mut current = value;
    for part in path.split('.') {
        current = if let Some(arr) = current.as_array() {
            let idx: usize = part.parse().map_err(|_| {
                ExternalMetricsError::SourceSchemaMismatch { path: path.to_owned() }
            })?;
            arr.get(idx).ok_or_else(|| ExternalMetricsError::SourceSchemaMismatch {
                path: path.to_owned(),
            })?
        } else if let Some(obj) = current.as_object() {
            obj.get(part).ok_or_else(|| ExternalMetricsError::SourceSchemaMismatch {
                path: path.to_owned(),
            })?
        } else {
            return Err(ExternalMetricsError::SourceSchemaMismatch { path: path.to_owned() });
        };
    }
    match current {
        Value::Number(n) => {
            let v = n.as_f64().ok_or_else(|| ExternalMetricsError::SourceSchemaMismatch {
                path: path.to_owned(),
            })?;
            if !v.is_finite() {
                return Err(ExternalMetricsError::SourceSchemaMismatch { path: path.to_owned() });
            }
            Ok(v)
        }
        Value::Bool(b) => Ok(if *b { 1.0 } else { 0.0 }),
        _ => Err(ExternalMetricsError::SourceSchemaMismatch { path: path.to_owned() }),
    }
}

/// Extract a "values" map from a JSON payload using configured path mappings.
fn extract_values(
    payload: &Value,
    source_config: &Value,
) -> Result<HashMap<String, f64>, ExternalMetricsError> {
    let mut values = HashMap::new();
    if let Some(mapping) = source_config["values"].as_object() {
        for (name, path_val) in mapping {
            let path = path_val.as_str().unwrap_or("");
            values.insert(name.clone(), lookup_path(payload, path)?);
        }
    }
    Ok(values)
}

// ── Public API ────────────────────────────────────────────────────────────────

/// Collect metrics from all configured external sources.
pub async fn collect(
    root: &Path,
    settings: &Value,
    last_known_good: Option<&HashMap<String, Value>>,
) -> Result<CollectResult, ExternalMetricsError> {
    let mode = settings["mode"]
        .as_str()
        .unwrap_or("DISABLED")
        .to_uppercase();
    let observed_at = chrono_now_utc();

    if mode == "DISABLED" {
        return Ok(CollectResult {
            at: observed_at,
            mode,
            observations: Vec::new(),
            errors: Vec::new(),
            last_known_good: last_known_good.cloned().unwrap_or_default(),
            sink_result: None,
        });
    }

    let max_bytes = settings["max_response_bytes"]
        .as_u64()
        .unwrap_or(1_048_576) as usize;
    if max_bytes < 1024 {
        return Err(ExternalMetricsError::MaxBytesTooSmall);
    }

    let timeout_secs = settings["timeout_seconds"].as_f64().unwrap_or(10.0);
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs_f64(timeout_secs))
        .build()
        .map_err(|e| ExternalMetricsError::Http {
            url: "<client build>".to_owned(),
            source: e,
        })?;

    let mut observations: Vec<Observation> = Vec::new();
    let mut errors: Vec<SourceError> = Vec::new();
    let mut updated_lkg: HashMap<String, Value> =
        last_known_good.cloned().unwrap_or_default();

    let sources = settings["sources"].as_array().map(|a| a.as_slice()).unwrap_or(&[]);

    for source_cfg in sources {
        let source_id = source_cfg["id"].as_str().unwrap_or("unknown").to_owned();
        let kind = source_cfg["kind"].as_str().unwrap_or("").to_owned();
        let visibility = source_cfg["visibility"].as_str().unwrap_or("private").to_owned();

        let result: Result<Observation, (String, Option<String>)> = async {
            match kind.as_str() {
                "github_repository" => {
                    let slug = source_cfg["repository"]
                        .as_str()
                        .ok_or_else(|| ("missing 'repository' field".to_owned(), None))?;
                    fetch_github_repository(&client, slug, max_bytes)
                        .await
                        .map(|(values, events)| Observation {
                            source: source_id.clone(),
                            visibility: visibility.clone(),
                            values,
                            events,
                        })
                        .map_err(|e| (e.to_string(), None))
                }

                "json_file" => {
                    let location = source_cfg["location"]
                        .as_str()
                        .ok_or_else(|| ("missing 'location' field".to_owned(), None))?;
                    let path = {
                        let p = Path::new(location);
                        if p.is_absolute() { p.to_path_buf() } else { root.join(p) }
                    };
                    let content = std::fs::read(&path).map_err(|e| {
                        (
                            ExternalMetricsError::Io { path: path.clone(), source: e }.to_string(),
                            None,
                        )
                    })?;
                    if content.len() > max_bytes {
                        return Err((
                            format!("external JSON file exceeds {max_bytes} bytes"),
                            None,
                        ));
                    }
                    let payload: Value = serde_json::from_slice(&content).map_err(|e| {
                        (
                            ExternalMetricsError::JsonParse {
                                url: location.to_owned(),
                                source: e,
                            }
                            .to_string(),
                            None,
                        )
                    })?;
                    let values = extract_values(&payload, source_cfg).map_err(|e| {
                        let kind_str = if matches!(
                            e,
                            ExternalMetricsError::SourceSchemaMismatch { .. }
                        ) {
                            Some("SOURCE_SCHEMA_MISMATCH".to_owned())
                        } else {
                            None
                        };
                        (e.to_string(), kind_str)
                    })?;
                    Ok(Observation {
                        source: source_id.clone(),
                        visibility: visibility.clone(),
                        values,
                        events: Vec::new(),
                    })
                }

                "http_json" => {
                    let location = source_cfg["location"]
                        .as_str()
                        .ok_or_else(|| ("missing 'location' field".to_owned(), None))?;
                    let scheme = location.split(':').next().unwrap_or("");
                    if scheme != "http" && scheme != "https" {
                        return Err((ExternalMetricsError::InvalidScheme.to_string(), None));
                    }

                    let mut extra_headers: HashMap<String, String> = HashMap::new();
                    if let Some(cred_env) = source_cfg["credential_env"].as_str() {
                        let secret = std::env::var(cred_env).unwrap_or_default();
                        if secret.is_empty() {
                            return Err((
                                ExternalMetricsError::MissingCredential {
                                    name: cred_env.to_owned(),
                                }
                                .to_string(),
                                None,
                            ));
                        }
                        let header = source_cfg["credential_header"]
                            .as_str()
                            .unwrap_or("Authorization")
                            .to_owned();
                        let prefix = source_cfg["credential_prefix"]
                            .as_str()
                            .unwrap_or("Bearer ");
                        extra_headers.insert(header, format!("{prefix}{secret}"));
                    }

                    let payload = get_json(&client, location, max_bytes, Some(extra_headers))
                        .await
                        .map_err(|e| (e.to_string(), None))?;
                    let values = extract_values(&payload, source_cfg).map_err(|e| {
                        let kind_str = if matches!(
                            e,
                            ExternalMetricsError::SourceSchemaMismatch { .. }
                        ) {
                            Some("SOURCE_SCHEMA_MISMATCH".to_owned())
                        } else {
                            None
                        };
                        (e.to_string(), kind_str)
                    })?;
                    Ok(Observation {
                        source: source_id.clone(),
                        visibility: visibility.clone(),
                        values,
                        events: Vec::new(),
                    })
                }

                other => Err((
                    ExternalMetricsError::UnsupportedKind { kind: other.to_owned() }.to_string(),
                    None,
                )),
            }
        }
        .await;

        match result {
            Ok(obs) => {
                updated_lkg.insert(
                    source_id.clone(),
                    serde_json::json!({
                        "value": obs.values,
                        "at": observed_at,
                        "source": source_id
                    }),
                );
                observations.push(obs);
            }
            Err((msg, err_kind)) => {
                let prior_lkg = updated_lkg.get(&source_id).cloned();
                errors.push(SourceError {
                    source: source_id,
                    error: msg,
                    kind: err_kind,
                    last_known_good: prior_lkg,
                });
            }
        }
    }

    let mut result = CollectResult {
        at: observed_at.clone(),
        mode,
        observations: observations.clone(),
        errors,
        last_known_good: updated_lkg,
        sink_result: None,
    };

    if !settings["sink"].is_null() && settings["sink"].is_object() {
        result.sink_result = Some(
            export_metrics_sink(root, settings, &observations, &observed_at).await,
        );
    }

    Ok(result)
}

/// Compute a score delta from collected external state.
///
/// Returns `Some(mean)` only when at least one finite positive observation value exists;
/// never manufactures a positive delta from missing or zero data.
pub fn score_delta_from_external(external_state: &Value) -> Option<f64> {
    let observations = external_state["latest"].as_array()?;
    if observations.is_empty() {
        return None;
    }
    let mut scalars: Vec<f64> = Vec::new();
    for obs in observations {
        if let Some(values) = obs["values"].as_object() {
            for v in values.values() {
                if let Some(n) = v.as_f64() {
                    if n.is_finite() && !v.is_boolean() {
                        scalars.push(n);
                    }
                }
            }
        }
    }
    if scalars.is_empty() {
        return None;
    }
    let mean = scalars.iter().sum::<f64>() / scalars.len() as f64;
    // Only return a positive delta when the aggregated signal genuinely improved
    if mean <= 0.0 { None } else { Some(mean) }
}

/// Write observations to the configured metrics sink (file or HTTP POST).
pub async fn export_metrics_sink(
    root: &Path,
    settings: &Value,
    observations: &[Observation],
    cycle_at: &str,
) -> ExportResult {
    let sink = match settings["sink"].as_object() {
        Some(s) => s,
        None => {
            return ExportResult {
                sink_kind: None,
                status: "no_sink".to_owned(),
                path: None,
                http_status: None,
                error: None,
            }
        }
    };

    let kind = sink.get("kind").and_then(|k| k.as_str()).unwrap_or("");

    match kind {
        "file" => {
            let output_dir_raw = sink
                .get("output_dir")
                .and_then(|v| v.as_str())
                .unwrap_or("generated/metrics");
            let output_dir = {
                let p = Path::new(output_dir_raw);
                if p.is_absolute() { p.to_path_buf() } else { root.join(p) }
            };
            if let Err(e) = std::fs::create_dir_all(&output_dir) {
                return ExportResult {
                    sink_kind: Some("file".to_owned()),
                    status: "error".to_owned(),
                    path: None,
                    http_status: None,
                    error: Some(e.to_string()),
                };
            }
            let fmt = sink.get("format").and_then(|v| v.as_str()).unwrap_or("jsonl");
            // Sanitise timestamp for use in filename
            let safe_at: String = cycle_at
                .chars()
                .take(23)
                .map(|c| if c == ':' || c == '+' { '-' } else { c })
                .collect();
            let filepath = output_dir.join(format!("metrics-{safe_at}.{fmt}"));

            let write_result: std::io::Result<()> = (|| {
                match fmt {
                    "jsonl" => {
                        let content: String = observations
                            .iter()
                            .filter_map(|o| serde_json::to_string(o).ok())
                            .collect::<Vec<_>>()
                            .join("\n")
                            + "\n";
                        std::fs::write(&filepath, content)?;
                    }
                    "json" => {
                        let payload = serde_json::json!({
                            "at": cycle_at,
                            "observations": observations,
                        });
                        std::fs::write(
                            &filepath,
                            serde_json::to_string_pretty(&payload)
                                .unwrap_or_default(),
                        )?;
                    }
                    "csv" => {
                        // Flatten: one row per source, comma-separated key=value pairs
                        let mut lines = Vec::new();
                        if let Some(first) = observations.first() {
                            // Header from first observation's keys
                            let keys: Vec<String> =
                                first.values.keys().cloned().collect();
                            lines.push(format!("source,{}", keys.join(",")));
                            for obs in observations {
                                let row: Vec<String> = keys
                                    .iter()
                                    .map(|k| {
                                        obs.values
                                            .get(k)
                                            .map(|v| v.to_string())
                                            .unwrap_or_default()
                                    })
                                    .collect();
                                lines.push(format!("{},{}", obs.source, row.join(",")));
                            }
                        }
                        std::fs::write(&filepath, lines.join("\n"))?;
                    }
                    _ => {
                        // Unknown format: write JSON
                        let payload = serde_json::json!({
                            "at": cycle_at,
                            "observations": observations,
                        });
                        std::fs::write(
                            &filepath,
                            serde_json::to_string_pretty(&payload)
                                .unwrap_or_default(),
                        )?;
                    }
                }
                Ok(())
            })();

            match write_result {
                Ok(()) => ExportResult {
                    sink_kind: Some("file".to_owned()),
                    status: "ok".to_owned(),
                    path: Some(filepath.to_string_lossy().into_owned()),
                    http_status: None,
                    error: None,
                },
                Err(e) => ExportResult {
                    sink_kind: Some("file".to_owned()),
                    status: "error".to_owned(),
                    path: None,
                    http_status: None,
                    error: Some(e.to_string()),
                },
            }
        }

        "http_post" => {
            let url = match sink.get("url").and_then(|v| v.as_str()) {
                Some(u) if !u.is_empty() => u.to_owned(),
                _ => {
                    return ExportResult {
                        sink_kind: Some("http_post".to_owned()),
                        status: "error".to_owned(),
                        path: None,
                        http_status: None,
                        error: Some("url not configured".to_owned()),
                    }
                }
            };

            let body = serde_json::json!({
                "at": cycle_at,
                "observations": observations,
            });

            let timeout_secs = sink
                .get("timeout_seconds")
                .and_then(|v| v.as_f64())
                .unwrap_or(10.0);

            let mut req_builder = match reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs_f64(timeout_secs))
                .build()
            {
                Ok(c) => c.post(&url).json(&body),
                Err(e) => {
                    return ExportResult {
                        sink_kind: Some("http_post".to_owned()),
                        status: "error".to_owned(),
                        path: None,
                        http_status: None,
                        error: Some(e.to_string()),
                    }
                }
            };

            if let Some(cred_env) = sink.get("credential_env").and_then(|v| v.as_str()) {
                let token = std::env::var(cred_env).unwrap_or_default();
                if !token.is_empty() {
                    req_builder =
                        req_builder.header("Authorization", format!("Bearer {token}"));
                }
            }

            match req_builder.send().await {
                Ok(resp) => ExportResult {
                    sink_kind: Some("http_post".to_owned()),
                    status: "ok".to_owned(),
                    path: None,
                    http_status: Some(resp.status().as_u16()),
                    error: None,
                },
                Err(e) => ExportResult {
                    sink_kind: Some("http_post".to_owned()),
                    status: "error".to_owned(),
                    path: None,
                    http_status: None,
                    error: Some(e.to_string()),
                },
            }
        }

        other => ExportResult {
            sink_kind: Some(other.to_owned()),
            status: "error".to_owned(),
            path: None,
            http_status: None,
            error: Some(format!("unknown sink kind: {other:?}")),
        },
    }
}

// ── Internal utilities ────────────────────────────────────────────────────────

fn chrono_now_utc() -> String {
    // Use std only — no chrono dep in this crate
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Format as ISO-8601 UTC (seconds precision)
    let (y, mo, d, h, min, s) = unix_to_parts(secs);
    format!("{y:04}-{mo:02}-{d:02}T{h:02}:{min:02}:{s:02}Z")
}

fn unix_to_parts(secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    let s = secs % 60;
    let mins = secs / 60;
    let min = mins % 60;
    let hours = mins / 60;
    let h = hours % 24;
    let days = hours / 24;
    // Gregorian approximation (sufficient for ISO timestamp generation)
    let (y, doy) = {
        let mut y = 1970u64;
        let mut remaining = days;
        loop {
            let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
            let days_in_year = if leap { 366 } else { 365 };
            if remaining < days_in_year {
                break;
            }
            remaining -= days_in_year;
            y += 1;
        }
        (y, remaining)
    };
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let month_days = [31u64, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let mut mo = 1u64;
    let mut rem = doy;
    for &md in &month_days {
        if rem < md {
            break;
        }
        rem -= md;
        mo += 1;
    }
    (y, mo, rem + 1, h, min, s)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn score_delta_returns_none_when_no_observations() {
        let state = json!({ "latest": [] });
        assert!(score_delta_from_external(&state).is_none());
    }

    #[test]
    fn score_delta_returns_none_when_values_are_zero() {
        let state = json!({ "latest": [{ "values": { "stars": 0 } }] });
        assert!(score_delta_from_external(&state).is_none());
    }

    #[test]
    fn score_delta_returns_mean_of_positive_scalars() {
        let state = json!({ "latest": [{ "values": { "stars": 100.0, "forks": 50.0 } }] });
        let delta = score_delta_from_external(&state).expect("expected Some");
        assert!((delta - 75.0).abs() < 1e-9);
    }

    #[test]
    fn lookup_path_resolves_nested_key() {
        let v = json!({ "a": { "b": 42 } });
        assert_eq!(lookup_path(&v, "a.b").unwrap(), 42.0);
    }

    #[test]
    fn collect_returns_disabled_immediately() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let settings = json!({ "mode": "DISABLED" });
            let result = collect(Path::new("/tmp"), &settings, None).await.unwrap();
            assert_eq!(result.mode, "DISABLED");
            assert!(result.observations.is_empty());
        });
    }
}
