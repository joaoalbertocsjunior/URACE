//! GET  /api/inbox/      — list patch proposals from state.json
//! GET  /api/inbox/count — count PENDING proposals
//! POST /api/inbox/:id/apply  — stub (requires daemon)
//! POST /api/inbox/:id/reject — stub (requires daemon)
//!
//! Ports `routes/inbox.py`. Proposal management actions are stubs because
//! they require daemon RPC; reading proposals from state is fully implemented.

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", get(list_inbox))
        .route("/count", get(inbox_count))
        .route("/:item_id/apply", post(inbox_apply))
        .route("/:item_id/reject", post(inbox_reject))
}

async fn list_inbox(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let proposals = state
        .get("patch_proposals")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    Json(serde_json::json!({ "items": proposals }))
}

async fn inbox_count(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let count = state
        .get("patch_proposals")
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter(|p| p.get("status").and_then(|v| v.as_str()) == Some("PENDING"))
                .count()
        })
        .unwrap_or(0);
    Json(serde_json::json!({ "count": count }))
}

async fn inbox_apply(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(item_id): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Apply {item_id}: requires a running daemon.")
    }))
}

async fn inbox_reject(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(item_id): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Reject {item_id}: requires a running daemon.")
    }))
}
