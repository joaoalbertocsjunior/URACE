//! Typed request/response structs for each MCP tool.
//!
//! All types derive `Serialize`/`Deserialize` and are used directly by
//! the axum handlers in `server.rs`.

use serde::{Deserialize, Serialize};
use serde_json::Value;

// ── JSON-RPC envelope ─────────────────────────────────────────────────────────

/// A JSON-RPC 2.0 request.
#[derive(Debug, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: Option<Value>,
    pub method: String,
    #[serde(default)]
    pub params: Value,
}

/// A JSON-RPC 2.0 success response.
#[derive(Debug, Serialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Option<Value>,
    pub result: Value,
}

impl JsonRpcResponse {
    pub fn ok(id: Option<Value>, result: impl Serialize) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            result: serde_json::to_value(result).unwrap_or(Value::Null),
        }
    }
}

/// A JSON-RPC 2.0 error response.
#[derive(Debug, Serialize)]
pub struct JsonRpcError {
    pub jsonrpc: String,
    pub id: Option<Value>,
    pub error: RpcErrorBody,
}

#[derive(Debug, Serialize)]
pub struct RpcErrorBody {
    pub code: i32,
    pub message: String,
}

impl JsonRpcError {
    pub fn new(id: Option<Value>, code: i32, message: impl Into<String>) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            error: RpcErrorBody {
                code,
                message: message.into(),
            },
        }
    }
}

// ── Tool call request/response ────────────────────────────────────────────────

/// The `tools/call` request params.
#[derive(Debug, Deserialize)]
pub struct ToolCallParams {
    pub name: String,
    #[serde(default)]
    pub arguments: Value,
}

// ── list_sources ─────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct ListSourcesRequest;

#[derive(Debug, Serialize, Deserialize)]
pub struct ListSourcesResponse {
    pub schema_version: String,
    pub sources: Vec<SourceInfo>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SourceInfo {
    pub name: String,
    pub kind: String,
    pub status: String,
    pub last_sync: Option<String>,
}

// ── sync_source ───────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct SyncSourceRequest {
    pub name: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SyncSourceResponse {
    pub schema_version: String,
    pub name: String,
    pub status: String,
    pub message: String,
}

// ── get_work_queue ────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct GetWorkQueueRequest;

#[derive(Debug, Serialize, Deserialize)]
pub struct GetWorkQueueResponse {
    pub schema_version: String,
    pub tasks: Vec<WorkTaskInfo>,
    pub total: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WorkTaskInfo {
    pub id: String,
    pub description: String,
    pub status: String,
    pub started_at: Option<String>,
}

// ── get_settlement_status ─────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct GetSettlementStatusRequest;

#[derive(Debug, Serialize, Deserialize)]
pub struct GetSettlementStatusResponse {
    pub schema_version: String,
    pub settlements: Vec<SettlementInfo>,
    pub total: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SettlementInfo {
    pub id: String,
    pub amount: String,
    pub status: String,
    pub settled_at: String,
}

// ── Health ────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub version: &'static str,
}
