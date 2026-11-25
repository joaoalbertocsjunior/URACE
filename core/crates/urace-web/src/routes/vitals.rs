//! GET /api/vitals/ — runtime vitals summary from state.json.
//!
//! Ports `routes/vitals.py` to Rust. Reads state from ~/.urace/state/state.json
//! and extracts the same fields the Python handler produced.

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{extract::State, routing::get, Json, Router};

pub fn router() -> Router<AppState> {
    Router::new().route("/", get(get_vitals))
}

async fn get_vitals(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);

    let lifecycle_state = state
        .get("lifecycle_state")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN")
        .to_string();

    // last_cycle_at: max of completed_at / started_at across checkpoints
    let last_cycle_at: Option<String> = state
        .get("checkpoints")
        .and_then(|v| v.as_array())
        .and_then(|cps| {
            cps.iter()
                .filter_map(|c| {
                    c.get("completed_at")
                        .or_else(|| c.get("started_at"))
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string())
                })
                .max()
        });

    let aps_score = state
        .get("aps_score")
        .or_else(|| state.get("current_aps_score"));

    let cycle_count = state
        .get("checkpoints")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    let objectives_count = state
        .get("objectives")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    let evidence_count = state
        .get("evidence")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    Json(serde_json::json!({
        "lifecycle_state": lifecycle_state,
        "last_cycle_at": last_cycle_at,
        "aps_score": aps_score,
        "cycle_count": cycle_count,
        "objectives_count": objectives_count,
        "evidence_count": evidence_count,
    }))
}
