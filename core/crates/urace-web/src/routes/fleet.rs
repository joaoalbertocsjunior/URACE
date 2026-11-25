//! GET  /api/fleet/status   — fleet member status from state.json
//! GET  /api/fleet/capacity — fleet capacity summary from state.json
//! POST /api/fleet/run      — stub (requires daemon)
//! POST /api/fleet/broadcast    — stub
//! POST /api/fleet/config-push  — stub
//!
//! Ports `routes/fleet.py`.

use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use crate::{AppState, auth::BearerToken, state_reader};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/status", get(fleet_status))
        .route("/capacity", get(fleet_capacity))
        .route("/run", post(fleet_run))
        .route("/broadcast", post(fleet_broadcast))
        .route("/config-push", post(fleet_config_push))
}

async fn fleet_status(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let status = state.get("fleet_status")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    Json(serde_json::Value::Array(status))
}

async fn fleet_capacity(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let capacity = state.get("fleet_capacity")
        .cloned()
        .unwrap_or_else(|| serde_json::json!({
            "fleet_size": 0,
            "fleet_available": 0,
            "parallel_capacity": 0,
            "total_calls_remaining_24h": 0,
            "members": [],
        }));
    Json(capacity)
}

#[derive(Deserialize)]
pub struct RunBody {
    #[serde(default = "default_dry_run")]
    pub dry_run: bool,
}
fn default_dry_run() -> bool { true }

async fn fleet_run(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Json(body): Json<RunBody>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "dry_run": body.dry_run,
        "error": "Fleet run requires a running daemon.",
    }))
}

#[derive(Deserialize)]
pub struct BroadcastBody {
    pub command: Option<String>,
}

async fn fleet_broadcast(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Json(_body): Json<BroadcastBody>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": "Fleet broadcast requires a running daemon.",
    }))
}

#[derive(Deserialize)]
pub struct ConfigPushBody {
    pub key: String,
    pub value: String,
}

async fn fleet_config_push(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Json(body): Json<ConfigPushBody>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "key": body.key,
        "value": body.value,
        "error": "Fleet config-push requires a running daemon.",
    }))
}
