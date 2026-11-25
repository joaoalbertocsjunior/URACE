//! Skill query endpoints.
//!
//! Ports `routes/skills.py` to Rust.
//!
//! The Python version delegated to `executor_capabilities` (probe, SKILL_VOCABULARY,
//! BUILTINS) which is not yet wired to the Rust web layer.  All three endpoints
//! are therefore graceful stubs that return well-typed JSON — exactly the same
//! posture the Python handler took when the executor was unavailable.
//!
//! * `GET  /api/skills/`             — list available skills
//! * `GET  /api/skills/vocabulary`   — return the skill vocabulary list
//! * `GET  /api/skills/{skill_id}`   — get a specific skill's contract (404 stub)

use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::get,
    Json, Router,
};
use serde_json::Value;
use crate::{AppState, auth::BearerToken};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", get(list_skills))
        .route("/vocabulary", get(skill_vocabulary))
        .route("/{skill_id}", get(get_skill))
}

async fn list_skills(
    State(_s): State<AppState>,
    _auth: BearerToken,
) -> Json<Value> {
    // executor_capabilities is not yet wired to the Rust web layer.
    Json(serde_json::json!({
        "skills": [],
        "note": "executor not running",
    }))
}

async fn skill_vocabulary(
    State(_s): State<AppState>,
    _auth: BearerToken,
) -> Json<Value> {
    Json(serde_json::json!({ "vocabulary": [] }))
}

async fn get_skill(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(skill_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    (
        StatusCode::NOT_FOUND,
        Json(serde_json::json!({
            "error": "not_found",
            "detail": format!("Skill {skill_id:?} not found"),
        })),
    )
}
