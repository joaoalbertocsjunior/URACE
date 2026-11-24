//! M2MServer — JSON-RPC 2.0 server over HTTP POST `/rpc`.
//!
//! Rust port of sources-lib `m2m/interface.py`.
//! Uses axum 0.7 for HTTP transport.

use crate::registry::SourceRegistry;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::Arc;

// ── JSON-RPC 2.0 types ────────────────────────────────────────────────────────

/// Inbound JSON-RPC 2.0 request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M2MRequest {
    pub jsonrpc: String,
    pub method: String,
    #[serde(default)]
    pub params: Value,
    pub id: Value,
}

/// JSON-RPC 2.0 error object.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M2MError {
    pub code: i64,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

/// Outbound JSON-RPC 2.0 response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M2MResponse {
    pub jsonrpc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<M2MError>,
    pub id: Value,
}

impl M2MResponse {
    fn ok(id: Value, result: Value) -> Self {
        M2MResponse { jsonrpc: "2.0".into(), result: Some(result), error: None, id }
    }

    fn err(id: Value, code: i64, message: impl Into<String>) -> Self {
        M2MResponse {
            jsonrpc: "2.0".into(),
            result: None,
            error: Some(M2MError { code, message: message.into(), data: None }),
            id,
        }
    }
}

// ── M2MServer ─────────────────────────────────────────────────────────────────

/// JSON-RPC 2.0 server backed by a `SourceRegistry`.
///
/// Methods: `sources.list`, `sources.sync`, `sources.add`, `sources.act`, `ping`.
#[derive(Clone)]
pub struct M2MServer {
    registry: Arc<SourceRegistry>,
}

impl M2MServer {
    pub fn new(registry: Arc<SourceRegistry>) -> Self {
        M2MServer { registry }
    }

    /// Dispatch a JSON-RPC request synchronously (no HTTP transport).
    /// For testing and embedded use.
    pub fn handle(&self, request: M2MRequest) -> M2MResponse {
        if request.jsonrpc != "2.0" {
            return M2MResponse::err(request.id, -32600, "Invalid Request: jsonrpc must be \"2.0\"");
        }
        let params = &request.params;
        match request.method.as_str() {
            "ping" => {
                use std::time::{SystemTime, UNIX_EPOCH};
                let at = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .map(|d| d.as_secs_f64())
                    .unwrap_or(0.0);
                M2MResponse::ok(request.id, json!({ "pong": true, "at": at }))
            }

            "sources.list" => {
                let records = self.registry.list();
                let items: Vec<Value> = records
                    .iter()
                    .map(|r| json!({ "id": r.id, "kind": r.kind, "added_at": r.added_at }))
                    .collect();
                M2MResponse::ok(request.id, Value::Array(items))
            }

            "sources.sync" => {
                let source_id = params.get("id").and_then(|v| v.as_str()).unwrap_or("");
                if source_id.is_empty() {
                    return M2MResponse::err(request.id, -32602, "params.id required");
                }
                match self.registry.get(source_id) {
                    None => M2MResponse::err(request.id, -32602, format!("unknown source: {source_id}")),
                    Some(_) => {
                        // Sync is async; in the M2M layer we return a stub acknowledging the
                        // request. Full async wiring goes through HttpControlServer + Tower.
                        M2MResponse::ok(request.id, json!({ "queued": true, "id": source_id }))
                    }
                }
            }

            "sources.add" => {
                let kind = params.get("kind").and_then(|v| v.as_str()).unwrap_or("");
                let sid = params.get("id").and_then(|v| v.as_str());
                let config: HashMap<String, Value> = params
                    .get("config")
                    .and_then(|v| serde_json::from_value(v.clone()).ok())
                    .unwrap_or_default();

                if kind.is_empty() {
                    return M2MResponse::err(request.id, -32602, "params.kind required");
                }
                match self.registry.add(kind, sid, config) {
                    Ok(record) => M2MResponse::ok(request.id, json!({ "id": record.id, "kind": record.kind })),
                    Err(e) => M2MResponse::err(request.id, -32603, e.to_string()),
                }
            }

            "sources.act" => {
                let source_id = params.get("id").and_then(|v| v.as_str()).unwrap_or("");
                let action = params.get("action").and_then(|v| v.as_str()).unwrap_or("");
                if source_id.is_empty() || action.is_empty() {
                    return M2MResponse::err(request.id, -32602, "params.id and params.action required");
                }
                // Act is async; return a stub acknowledgement.
                M2MResponse::ok(request.id, json!({ "queued": true, "id": source_id, "action": action }))
            }

            _ => M2MResponse::err(request.id, -32601, format!("Method not found: {}", request.method)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::BaseSourceAdapter;

    fn server() -> M2MServer {
        let reg = Arc::new(SourceRegistry::new());
        reg.register_kind("base", BaseSourceAdapter).unwrap();
        M2MServer::new(reg)
    }

    fn req(method: &str, params: Value) -> M2MRequest {
        M2MRequest { jsonrpc: "2.0".into(), method: method.into(), params, id: json!(1) }
    }

    #[test]
    fn ping() {
        let s = server();
        let r = s.handle(req("ping", json!({})));
        assert!(r.error.is_none());
        assert!(r.result.unwrap().get("pong").unwrap().as_bool().unwrap());
    }

    #[test]
    fn sources_list_empty() {
        let s = server();
        let r = s.handle(req("sources.list", json!({})));
        assert!(r.error.is_none());
        assert_eq!(r.result.unwrap(), json!([]));
    }

    #[test]
    fn sources_add_and_list() {
        let s = server();
        let add = s.handle(req("sources.add", json!({"kind": "base", "id": "s1", "config": {}})));
        assert!(add.error.is_none());

        let list = s.handle(req("sources.list", json!({})));
        let items = list.result.unwrap();
        assert_eq!(items.as_array().unwrap().len(), 1);
    }

    #[test]
    fn unknown_method() {
        let s = server();
        let r = s.handle(req("no.such", json!({})));
        assert_eq!(r.error.unwrap().code, -32601);
    }

    #[test]
    fn invalid_jsonrpc_version() {
        let s = server();
        let r = s.handle(M2MRequest {
            jsonrpc: "1.0".into(),
            method: "ping".into(),
            params: json!({}),
            id: json!(null),
        });
        assert_eq!(r.error.unwrap().code, -32600);
    }
}
