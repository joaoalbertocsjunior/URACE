//! GET /api/portfolio/feedback — portfolio feedback / variant data from state.json
//! GET /api/portfolio/status   — portfolio status summary from state.json
//!
//! Ports `routes/portfolio.py`.

use axum::{
    extract::State,
    routing::get,
    Json, Router,
};
use crate::{AppState, auth::BearerToken, state_reader};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/feedback", get(portfolio_feedback))
        .route("/status", get(portfolio_status))
}

async fn portfolio_feedback(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let feedback = state.get("portfolio_feedback")
        .cloned()
        .unwrap_or_else(|| serde_json::json!({
            "phase": "UNKNOWN",
            "variants": [],
            "last_error": null,
        }));
    Json(feedback)
}

async fn portfolio_status(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let status = state.get("portfolio_status")
        .cloned()
        .unwrap_or_else(|| serde_json::json!({ "error": "unavailable" }));
    Json(status)
}
