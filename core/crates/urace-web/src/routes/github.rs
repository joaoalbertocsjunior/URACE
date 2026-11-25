//! GET  /api/github/status           — GitHub adapter status from state.json
//! POST /api/github/push-goals       — stub (requires daemon)
//! POST /api/github/trigger-workflow — stub (requires daemon)
//!
//! Ports `routes/github_router.py`.

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/status", get(github_status))
        .route("/push-goals", post(github_push_goals))
        .route("/trigger-workflow", post(github_trigger_workflow))
}

async fn github_status(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    // Look for github adapter status under sources or a dedicated github_status key
    let github = state.get("github_status").cloned().unwrap_or_else(|| {
        // Try to find from sources.github
        state
            .get("sources")
            .and_then(|s| s.as_object())
            .and_then(|m| {
                m.values()
                    .find(|v| v.get("kind").and_then(|k| k.as_str()) == Some("github"))
            })
            .cloned()
            .unwrap_or_else(|| {
                serde_json::json!({
                    "connected": false,
                    "github_token_set": false,
                })
            })
    });
    Json(github)
}

#[derive(Deserialize)]
pub struct PushGoalsBody {
    #[serde(default = "default_dry_run")]
    pub dry_run: bool,
}
fn default_dry_run() -> bool {
    true
}

async fn github_push_goals(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Json(body): Json<PushGoalsBody>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "dry_run": body.dry_run,
        "error": "GitHub push-goals requires a running daemon.",
        "objectives_pushed": 0,
    }))
}

#[derive(Deserialize)]
pub struct TriggerWorkflowBody {
    pub workflow: String,
    #[serde(default = "default_ref")]
    pub r#ref: String,
}
fn default_ref() -> String {
    "main".to_string()
}

async fn github_trigger_workflow(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Json(body): Json<TriggerWorkflowBody>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "workflow": body.workflow,
        "ref": body.r#ref,
        "error": "Trigger workflow requires a running daemon.",
    }))
}
