//! GET /api/rules/list      — list governance rules from state.json
//! GET /api/rules/graph     — rule relationship graph from state.json
//! GET /api/rules/conflicts — detected rule conflicts from state.json
//!
//! Ports `routes/rules.py`. Python dispatched to daemon RPC; Rust reads
//! state directly (rule data stored under "rules" / "rule_relationships" /
//! "rule_conflicts" in state.json).

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{extract::State, routing::get, Json, Router};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/list", get(rules_list))
        .route("/graph", get(rules_graph))
        .route("/conflicts", get(rules_conflicts))
}

async fn rules_list(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let rules = state
        .get("rules")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    Json(serde_json::Value::Array(rules))
}

async fn rules_graph(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let rules = state
        .get("rules")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let relationships = state
        .get("rule_relationships")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    Json(serde_json::json!({
        "rules": rules,
        "relationships": relationships,
    }))
}

async fn rules_conflicts(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let conflicts = state
        .get("rule_conflicts")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    Json(serde_json::Value::Array(conflicts))
}
