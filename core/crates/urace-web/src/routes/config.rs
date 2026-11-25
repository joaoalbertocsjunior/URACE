use crate::{auth::BearerToken, AppState};
use axum::{extract::State, routing::{get, post}, Json, Router};
use serde::Deserialize;
use serde_json::Value;
use std::io::Write as _;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/values", get(config_values))
        .route("/fields", get(config_fields))
        .route("/set", post(config_set))
}

async fn config_values(State(s): State<AppState>, _auth: BearerToken) -> Json<Value> {
    let config_path = s.root.join("config.json");
    let config: Value = if config_path.exists() {
        std::fs::read_to_string(&config_path)
            .ok()
            .and_then(|c| serde_json::from_str(&c).ok())
            .unwrap_or(Value::Object(Default::default()))
    } else {
        Value::Object(Default::default())
    };
    Json(config)
}

async fn config_fields(State(_s): State<AppState>, _auth: BearerToken) -> Json<Value> {
    Json(serde_json::json!([]))
}

#[derive(Deserialize)]
struct SetRequest {
    key: String,
    value: String,
}

async fn config_set(
    State(s): State<AppState>,
    _auth: BearerToken,
    Json(req): Json<SetRequest>,
) -> Json<Value> {
    // Validate key: only word chars and dots, no traversal
    if !req.key.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '.') || req.key.is_empty() {
        return Json(serde_json::json!({"ok": false, "detail": "invalid key"}));
    }

    let config_path = s.root.join("config.json");
    let mut config: serde_json::Map<String, Value> = if config_path.exists() {
        std::fs::read_to_string(&config_path)
            .ok()
            .and_then(|c| serde_json::from_str(&c).ok())
            .unwrap_or_default()
    } else {
        Default::default()
    };

    // Set nested value via dotted path
    let parts: Vec<&str> = req.key.splitn(2, '.').collect();
    let typed_val = parse_value(&req.value);
    if parts.len() == 2 {
        let section = config
            .entry(parts[0].to_string())
            .or_insert_with(|| Value::Object(Default::default()));
        if let Value::Object(map) = section {
            map.insert(parts[1].to_string(), typed_val);
        }
    } else {
        config.insert(req.key.clone(), typed_val);
    }

    let serialized = match serde_json::to_string_pretty(&Value::Object(config)) {
        Ok(s) => s,
        Err(e) => return Json(serde_json::json!({"ok": false, "detail": e.to_string()})),
    };

    // Atomic write via temp file + rename
    let tmp_path = config_path.with_extension("json.tmp");
    let write_result = (|| -> std::io::Result<()> {
        let mut f = std::fs::File::create(&tmp_path)?;
        f.write_all(serialized.as_bytes())?;
        f.sync_all()?;
        std::fs::rename(&tmp_path, &config_path)?;
        Ok(())
    })();

    match write_result {
        Ok(()) => Json(serde_json::json!({"ok": true})),
        Err(e) => Json(serde_json::json!({"ok": false, "detail": e.to_string()})),
    }
}

fn parse_value(s: &str) -> Value {
    if s == "true" { return Value::Bool(true); }
    if s == "false" { return Value::Bool(false); }
    if let Ok(n) = s.parse::<i64>() { return Value::Number(n.into()); }
    if let Ok(f) = s.parse::<f64>() {
        if let Some(n) = serde_json::Number::from_f64(f) { return Value::Number(n); }
    }
    Value::String(s.to_string())
}
