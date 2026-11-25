//! GET /api/compliance/           — compliance summary
//! GET /api/compliance/domain/:d  — per-domain compliance detail
//! GET /api/compliance/history    — recent compliance records
//!
//! Ports `routes/compliance.py`. The Python handler dispatched to the daemon
//! via RPC; in Rust we read compliance records directly from state.json.

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{
    extract::{Path, Query, State},
    routing::get,
    Json, Router,
};
use serde::Deserialize;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", get(compliance_summary))
        .route("/domain/:domain", get(compliance_domain))
        .route("/history", get(compliance_history))
}

fn extract_compliance(
    state: &serde_json::Value,
) -> (Vec<serde_json::Value>, Vec<serde_json::Value>) {
    let domains = state
        .get("compliance_domains")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let records = state
        .get("compliance_records")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    (domains, records)
}

async fn compliance_summary(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let (domains, records) = extract_compliance(&state);
    let all: Vec<_> = records.to_vec();
    let start = all.len().saturating_sub(20);
    let recent = all[start..].to_vec();
    Json(serde_json::json!({
        "domains": domains,
        "recent_records": recent,
    }))
}

async fn compliance_domain(
    State(s): State<AppState>,
    _auth: BearerToken,
    Path(domain): Path<String>,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let (domains, records) = extract_compliance(&state);
    let filtered_domains: Vec<_> = domains
        .iter()
        .filter(|d| d.get("domain").and_then(|v| v.as_str()) == Some(&domain))
        .cloned()
        .collect();
    let filtered_records: Vec<_> = records
        .iter()
        .filter(|r| r.get("domain").and_then(|v| v.as_str()) == Some(&domain))
        .cloned()
        .collect();
    let start = filtered_records.len().saturating_sub(20);
    let filtered_records = filtered_records[start..].to_vec();
    Json(serde_json::json!({
        "domains": filtered_domains,
        "recent_records": filtered_records,
    }))
}

#[derive(Deserialize)]
pub struct HistoryQuery {
    #[serde(default = "default_history_limit")]
    pub limit: usize,
}
fn default_history_limit() -> usize {
    20
}

async fn compliance_history(
    State(s): State<AppState>,
    _auth: BearerToken,
    Query(q): Query<HistoryQuery>,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let records = state
        .get("compliance_records")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let recent: Vec<_> = records.iter().rev().take(q.limit).rev().cloned().collect();
    Json(serde_json::json!({
        "domains": [],
        "recent_records": recent,
    }))
}
