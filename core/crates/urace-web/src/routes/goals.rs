//! GET /api/goals/ — list objectives from state.json
//! POST /api/goals/add — stub (daemon RPC not implemented in Rust yet)
//! POST /api/goals/:id/pin|unpin|defer|cancel — stubs
//! GET /api/goals/forecast — stub
//!
//! Ports `routes/goals.py`. The Python handler falls back to in-process CLI
//! dispatch when the daemon RPC socket is unavailable; in the Rust port we
//! read state directly (the daemon RPC path is a future TODO).

use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use crate::{AppState, auth::BearerToken, state_reader};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", get(list_goals))
        .route("/add", post(add_goal))
        .route("/forecast", get(goals_forecast))
        .route("/:goal_id/pin", post(goals_pin))
        .route("/:goal_id/unpin", post(goals_unpin))
        .route("/:goal_id/defer", post(goals_defer))
        .route("/:goal_id/cancel", post(goals_cancel))
}

async fn list_goals(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let objectives = state.get("objectives")
        .cloned()
        .unwrap_or(serde_json::Value::Array(vec![]));
    let goals = if objectives.is_array() {
        objectives
    } else {
        serde_json::Value::Array(vec![])
    };
    Json(serde_json::json!({ "goals": goals }))
}

#[derive(Deserialize)]
pub struct AddGoalBody {
    pub title: String,
    #[serde(default)]
    pub description: String,
    #[serde(default = "default_priority")]
    pub priority: i64,
}

fn default_priority() -> i64 { 50 }

async fn add_goal(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Json(_body): Json<AddGoalBody>,
) -> Json<serde_json::Value> {
    // Daemon RPC dispatch not yet implemented in Rust; return a stub response.
    // The Python equivalent fell back to in-process CLI dispatch.
    Json(serde_json::json!({
        "status": "unavailable",
        "error": "Goal creation requires a running daemon. Use `urace add-goal` from the CLI."
    }))
}

async fn goals_forecast(
    State(_s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "output": "Forecast requires a running daemon."
    }))
}

async fn goals_pin(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(goal_id): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Pin goal {goal_id}: requires a running daemon.")
    }))
}

async fn goals_unpin(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(goal_id): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Unpin goal {goal_id}: requires a running daemon.")
    }))
}

async fn goals_defer(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(goal_id): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Defer goal {goal_id}: requires a running daemon.")
    }))
}

async fn goals_cancel(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(goal_id): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Cancel goal {goal_id}: requires a running daemon.")
    }))
}
