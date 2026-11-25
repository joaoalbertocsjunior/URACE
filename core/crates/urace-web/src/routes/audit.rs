//! GET /api/audit/decisions — authority decision records from state.json
//! GET /api/audit/evidence  — evidence records from state.json
//!
//! Ports `routes/audit.py`. Filtering by `outcome`/`kind` and `since` is
//! replicated faithfully; the `since` field is compared lexicographically
//! (ISO-8601 strings sort correctly).

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{
    extract::{Query, State},
    routing::get,
    Json, Router,
};
use serde::Deserialize;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/decisions", get(audit_decisions))
        .route("/evidence", get(audit_evidence))
}

#[derive(Deserialize)]
pub struct DecisionsQuery {
    pub outcome: Option<String>,
    pub since: Option<String>,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

#[derive(Deserialize)]
pub struct EvidenceQuery {
    pub kind: Option<String>,
    pub since: Option<String>,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

fn default_limit() -> usize {
    50
}

async fn audit_decisions(
    State(s): State<AppState>,
    _auth: BearerToken,
    Query(q): Query<DecisionsQuery>,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let mut decisions: Vec<serde_json::Value> = state
        .get("decision_records")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    if let Some(outcome) = &q.outcome {
        decisions.retain(|d| d.get("outcome").and_then(|v| v.as_str()) == Some(outcome.as_str()));
    }

    if let Some(since) = &q.since {
        // ISO-8601 strings compare lexicographically
        decisions.retain(|d| {
            d.get("at")
                .and_then(|v| v.as_str())
                .map(|at| at >= since.as_str())
                .unwrap_or(true)
        });
    }

    let limit = q.limit.clamp(1, 500);
    decisions.reverse();
    decisions.truncate(limit);
    decisions.reverse();

    Json(serde_json::json!({ "decisions": decisions }))
}

async fn audit_evidence(
    State(s): State<AppState>,
    _auth: BearerToken,
    Query(q): Query<EvidenceQuery>,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let mut evidence: Vec<serde_json::Value> = state
        .get("evidence")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    if let Some(kind) = &q.kind {
        evidence.retain(|e| e.get("kind").and_then(|v| v.as_str()) == Some(kind.as_str()));
    }

    if let Some(since) = &q.since {
        evidence.retain(|e| {
            e.get("at")
                .and_then(|v| v.as_str())
                .map(|at| at >= since.as_str())
                .unwrap_or(true)
        });
    }

    let limit = q.limit.clamp(1, 500);
    evidence.reverse();
    evidence.truncate(limit);
    evidence.reverse();

    Json(serde_json::json!({ "evidence": evidence }))
}
