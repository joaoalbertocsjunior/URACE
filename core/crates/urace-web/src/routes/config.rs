//! GET /api/config/values — returns flattened config key/value map from config.json
//!
//! Ports `routes/config_router.py`. Full field schema and set endpoint are
//! stubs pending a Rust config_schema module; reading values is implemented.

use crate::{auth::BearerToken, AppState};
use axum::{extract::State, routing::get, Json, Router};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/values", get(config_values))
        .route("/fields", get(config_fields))
}

async fn config_values(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    // Read config.json from the root directory
    let config_path = s.root.join("config.json");
    let config: serde_json::Value = if config_path.exists() {
        std::fs::read_to_string(&config_path)
            .ok()
            .and_then(|c| serde_json::from_str(&c).ok())
            .unwrap_or(serde_json::Value::Object(Default::default()))
    } else {
        serde_json::Value::Object(Default::default())
    };
    Json(config)
}

async fn config_fields(State(_s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    // Field schema enumeration is a stub pending Rust config_schema module.
    Json(serde_json::json!([]))
}
