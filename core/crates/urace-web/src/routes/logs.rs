//! Log history and stream endpoints.
//!
//! Ports `routes/logs.py` to Rust.
//!
//! * `GET /api/logs/history`    — return recent log entries read from `<root>/logs/`
//! * `GET /api/logs/stream`     — SSE stream (snapshot then keep-alive)
//! * `GET /api/logs/components` — list per-component enable/disable status (stub)
//! * `POST /api/logs/components/{name}/enable`  — enable a component (stub)
//! * `POST /api/logs/components/{name}/disable` — disable a component (stub)

use crate::{auth::BearerToken, AppState};
use axum::{
    extract::{Path, State},
    response::sse::{Event, KeepAlive, Sse},
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use futures::stream;
use serde_json::Value;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/history", get(log_history))
        .route("/stream", get(log_stream))
        .route("/components", get(list_components))
        .route("/components/{name}/enable", post(enable_component))
        .route("/components/{name}/disable", post(disable_component))
}

/// Read the last `limit` log entries from `<root>/logs/*.log` files.
/// Each non-empty line becomes a plain-text entry object.
/// Returns gracefully with an empty list when the directory is absent.
fn read_log_entries(root: &std::path::Path, limit: usize) -> Vec<Value> {
    let logs_dir = root.join("logs");
    if !logs_dir.exists() {
        return vec![];
    }

    let mut entries: Vec<Value> = Vec::new();

    // Collect all *.log files; ignore errors opening individual files.
    let mut log_files: Vec<std::path::PathBuf> = std::fs::read_dir(&logs_dir)
        .ok()
        .into_iter()
        .flatten()
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("log"))
        .collect();
    log_files.sort();

    for path in &log_files {
        if let Ok(contents) = std::fs::read_to_string(path) {
            let stem = path
                .file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or("unknown")
                .to_string();
            for line in contents.lines() {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                // Try to parse as a JSON object first (structured log lines).
                let entry: Value = if let Ok(v) = serde_json::from_str::<Value>(trimmed) {
                    v
                } else {
                    serde_json::json!({
                        "logger": stem,
                        "msg": trimmed,
                    })
                };
                entries.push(entry);
            }
        }
    }

    // Keep the last `limit` entries (ring-buffer semantics matching the Python 500-entry cap).
    let cap = limit.min(500);
    if entries.len() > cap {
        entries = entries.split_off(entries.len() - cap);
    }
    entries
}

async fn log_history(State(s): State<AppState>, _auth: BearerToken) -> Json<Value> {
    let entries = read_log_entries(&s.root, 100);
    let count = entries.len();
    Json(serde_json::json!({
        "entries": entries,
        "count": count,
    }))
}

async fn log_stream(State(s): State<AppState>, _auth: BearerToken) -> Response {
    // Emit a snapshot of the last 50 entries then keep the connection alive.
    // Full live-streaming would require a shared ring-buffer; that is a future
    // enhancement once a Rust logging sink is wired in.
    let entries = read_log_entries(&s.root, 50);

    let events: Vec<Result<Event, std::convert::Infallible>> = entries
        .into_iter()
        .map(|e| {
            let data = serde_json::to_string(&e).unwrap_or_default();
            Ok(Event::default().data(data))
        })
        .collect();

    Sse::new(stream::iter(events))
        .keep_alive(KeepAlive::default())
        .into_response()
}

async fn list_components(State(_s): State<AppState>, _auth: BearerToken) -> Json<Value> {
    // Component registry is not yet wired to the Rust logging layer.
    // Returns an empty list; the Python original also had limited impl here.
    Json(serde_json::json!({ "components": [] }))
}

async fn enable_component(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(name): Path<String>,
) -> Json<Value> {
    Json(serde_json::json!({ "ok": true, "component": name, "enabled": true }))
}

async fn disable_component(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(name): Path<String>,
) -> Json<Value> {
    Json(serde_json::json!({ "ok": true, "component": name, "enabled": false }))
}
