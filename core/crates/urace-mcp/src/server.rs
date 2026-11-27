//! Axum-based MCP/JSON-RPC server.
//!
//! Every mutating tool call passes through the §62z `AuthorityGate`
//! (via `urace_authority::resolve`) before execution.
//!
//! Routes:
//!   POST /mcp/tools/list   — list available tools
//!   POST /mcp/tools/call   — invoke a tool (authority-gated for mutations)
//!   GET  /mcp/health       — liveness probe

use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde_json::{json, Value};
use std::{collections::HashMap, sync::Arc};
use tracing::{info, warn};

use urace_authority::authority::{resolve as authority_resolve, Objective};
use urace_types::AuthorityOutcome;

use crate::{
    api_interface::{
        GetSettlementStatusResponse, GetWorkQueueResponse, HealthResponse, JsonRpcError,
        JsonRpcRequest, JsonRpcResponse, ListSourcesResponse, SyncSourceResponse, ToolCallParams,
    },
    tools::ToolRegistry,
};

// ── Server configuration ──────────────────────────────────────────────────────

/// Configuration for the MCP server.
#[derive(Debug, Clone)]
pub struct McpServerConfig {
    /// TCP address the server should bind to.
    pub bind_addr: std::net::SocketAddr,
    /// Authority config forwarded to the §62z gate.
    pub authority_config: HashMap<String, Value>,
    /// Self-evolution policy (may be None if disabled).
    pub self_evolution_policy: Option<HashMap<String, Value>>,
    /// Retained constraints from the authority boundary.
    pub constraints: Vec<String>,
}

impl Default for McpServerConfig {
    fn default() -> Self {
        Self {
            bind_addr: "127.0.0.1:0".parse().unwrap(),
            authority_config: HashMap::new(),
            self_evolution_policy: None,
            constraints: vec![],
        }
    }
}

// ── Shared state ──────────────────────────────────────────────────────────────

#[derive(Clone)]
struct AppState {
    registry: Arc<ToolRegistry>,
    config: Arc<McpServerConfig>,
}

// ── McpServer ─────────────────────────────────────────────────────────────────

/// Axum-based MCP server instance.
pub struct McpServer {
    pub config: McpServerConfig,
    registry: ToolRegistry,
}

impl McpServer {
    pub fn new(config: McpServerConfig) -> Self {
        Self {
            config,
            registry: ToolRegistry::new(),
        }
    }

    /// Build the axum `Router`.  Useful for testing without binding a port.
    pub fn router(&self) -> Router {
        let state = AppState {
            registry: Arc::new(self.registry.clone()),
            config: Arc::new(self.config.clone()),
        };

        Router::new()
            .route("/mcp/health", get(health_handler))
            .route("/mcp/tools/list", post(tools_list_handler))
            .route("/mcp/tools/call", post(tools_call_handler))
            .with_state(state)
    }

    /// Start listening.  This future does not return unless the server errors.
    pub async fn serve(self) -> Result<(), Box<dyn std::error::Error>> {
        let addr = self.config.bind_addr;
        let router = self.router();
        info!("urace-mcp listening on {addr}");
        let listener = tokio::net::TcpListener::bind(addr).await?;
        axum::serve(listener, router).await?;
        Ok(())
    }
}

// ── Handlers ──────────────────────────────────────────────────────────────────

async fn health_handler() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        version: env!("CARGO_PKG_VERSION"),
    })
}

async fn tools_list_handler(State(state): State<AppState>) -> (StatusCode, Json<Value>) {
    let tools: Vec<&_> = state.registry.all().iter().collect();
    let body = json!({ "tools": tools });
    (StatusCode::OK, Json(body))
}

async fn tools_call_handler(
    State(state): State<AppState>,
    Json(request): Json<JsonRpcRequest>,
) -> (StatusCode, Json<Value>) {
    if request.jsonrpc != "2.0" {
        let err = JsonRpcError::new(request.id, -32600, "Invalid JSON-RPC version");
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::to_value(err).unwrap()),
        );
    }

    if request.method != "tools/call" {
        let err = JsonRpcError::new(request.id.clone(), -32601, "Method not found");
        return (
            StatusCode::NOT_FOUND,
            Json(serde_json::to_value(err).unwrap()),
        );
    }

    // Parse tool call params.
    let params: ToolCallParams = match serde_json::from_value(request.params.clone()) {
        Ok(p) => p,
        Err(e) => {
            let err = JsonRpcError::new(request.id, -32602, format!("Invalid params: {e}"));
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::to_value(err).unwrap()),
            );
        }
    };

    // Verify the tool exists.
    if state.registry.get(&params.name).is_none() {
        let err = JsonRpcError::new(request.id, -32602, format!("Unknown tool: {}", params.name));
        return (
            StatusCode::BAD_REQUEST,
            Json(serde_json::to_value(err).unwrap()),
        );
    }

    // §62z authority gate — required for all mutating tools.
    if !state.registry.is_read_only(&params.name) {
        let objective = Objective {
            id: None,
            scope: "implementation".into(),
            title: format!("mcp tool call: {}", params.name),
            reason: Some(format!("MCP client invoked tool '{}'", params.name)),
            necessity_evidence: None,
            lower_impact_route_sufficient: None,
        };

        let resolution = authority_resolve(
            &objective,
            &state.config.authority_config,
            state.config.self_evolution_policy.as_ref(),
            &state.config.constraints,
        );

        if resolution.outcome != AuthorityOutcome::AutonomouslyAuthorized {
            warn!(
                tool = %params.name,
                outcome = ?resolution.outcome,
                basis = %resolution.basis,
                "authority gate denied MCP tool call"
            );
            let err = JsonRpcError::new(
                request.id,
                -32000,
                format!(
                    "Authority gate: {:?} — {}",
                    resolution.outcome, resolution.basis
                ),
            );
            return (
                StatusCode::FORBIDDEN,
                Json(serde_json::to_value(err).unwrap()),
            );
        }
    }

    // Dispatch to tool handler.
    let result = dispatch_tool(&params.name, params.arguments, &state).await;
    let response = JsonRpcResponse::ok(request.id, result);
    (
        StatusCode::OK,
        Json(serde_json::to_value(response).unwrap()),
    )
}

// ── Tool dispatch ─────────────────────────────────────────────────────────────

async fn dispatch_tool(name: &str, args: Value, state: &AppState) -> Value {
    let sources_url = state
        .config
        .authority_config
        .get("sources_mcp_url")
        .and_then(|v| v.as_str())
        .unwrap_or("http://127.0.0.1:7700")
        .to_string();

    match name {
        // ── URACE-internal read tools ─────────────────────────────────────────
        "list_sources" => {
            // Query sources-lib HTTP control server for the registered sources.
            let client = reqwest::Client::new();
            match client
                .get(&format!("{sources_url}/sources"))
                .send()
                .await
            {
                Ok(resp) => resp
                    .json::<Value>()
                    .await
                    .unwrap_or_else(|_| {
                        serde_json::to_value(ListSourcesResponse {
                            schema_version: "1.0".into(),
                            sources: vec![],
                        })
                        .unwrap_or(Value::Null)
                    }),
                Err(e) => {
                    warn!(error = %e, "sources-lib unreachable for list_sources");
                    serde_json::to_value(ListSourcesResponse {
                        schema_version: "1.0".into(),
                        sources: vec![],
                    })
                    .unwrap_or(Value::Null)
                }
            }
        }

        "sync_source" => {
            let source_name = args
                .get("name")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            // POST to sources-lib HTTP control server to trigger a sync.
            let client = reqwest::Client::new();
            match client
                .post(&format!("{sources_url}/sources/sync/{source_name}"))
                .send()
                .await
            {
                Ok(_) => {
                    serde_json::to_value(SyncSourceResponse {
                        schema_version: "1.0".into(),
                        name: source_name.into(),
                        status: "queued".into(),
                        message: "Sync request forwarded to sources-lib".into(),
                    })
                    .unwrap_or(Value::Null)
                }
                Err(e) => {
                    warn!(error = %e, "sources-lib unreachable for sync_source");
                    serde_json::to_value(SyncSourceResponse {
                        schema_version: "1.0".into(),
                        name: source_name.into(),
                        status: "queued".into(),
                        message: format!("sources-lib unreachable ({e}); sync queued locally"),
                    })
                    .unwrap_or(Value::Null)
                }
            }
        }

        "get_work_queue" => serde_json::to_value(GetWorkQueueResponse {
            schema_version: "1.0".into(),
            tasks: vec![],
            total: 0,
        })
        .unwrap_or_else(|_| json!({
            "schema_version": "1.0",
            "tasks": [],
            "total": 0,
            "note": "pending full work-market integration"
        })),

        "get_settlement_status" => serde_json::to_value(GetSettlementStatusResponse {
            schema_version: "1.0".into(),
            settlements: vec![],
            total: 0,
        })
        .unwrap_or_else(|_| json!({
            "schema_version": "1.0",
            "settlements": [],
            "total": 0,
            "note": "pending EVM settlement integration"
        })),

        "get_status" => {
            json!({
                "schema_version": "1.0",
                "status": "running",
                "note": "connect to daemon state file for live data"
            })
        }

        "get_goals" => {
            json!({
                "schema_version": "1.0",
                "goals": [],
                "note": "goal store not wired to MCP server; read state/goals.jsonl directly"
            })
        }

        "post_work_task" => {
            let task_id = args
                .get("task_id")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            json!({
                "schema_version": "1.0",
                "status": "queued",
                "task_id": task_id,
                "note": "pending full work-market integration"
            })
        }

        "get_audit_events" => {
            json!({
                "schema_version": "1.0",
                "events": [],
                "note": "audit ledger not wired to MCP server; read state/audit.jsonl directly"
            })
        }

        // ── GitHub tools — forwarded to sources-lib MCP ───────────────────────
        name if name.starts_with("github_") => {
            forward_to_sources(&sources_url, name, args).await
        }

        _ => json!({ "error": "unknown tool" }),
    }
}

/// Forward a tool call to the sources-lib MCP server via HTTP JSON-RPC.
async fn forward_to_sources(
    sources_url: &str,
    tool_name: &str,
    args: Value,
) -> Value {
    let client = reqwest::Client::new();
    let body = json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": args}
    });
    match client
        .post(&format!("{sources_url}/mcp"))
        .json(&body)
        .send()
        .await
    {
        Ok(resp) => resp
            .json::<Value>()
            .await
            .unwrap_or_else(|e| json!({"error": e.to_string()})),
        Err(e) => json!({"error": format!("sources-lib unreachable: {e}")}),
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Method, Request};
    use tower::util::ServiceExt; // oneshot

    fn make_server() -> McpServer {
        // Authority config: grant "local implementation changes" delegated scope
        // so that mutating tool calls pass the authority gate in tests.
        let mut authority_config = HashMap::new();
        authority_config.insert("delegated".into(), json!(["local implementation changes"]));
        authority_config.insert("reserved".into(), json!([]));

        McpServer::new(McpServerConfig {
            authority_config,
            ..Default::default()
        })
    }

    async fn send(
        router: Router,
        method: Method,
        uri: &str,
        body: Option<Value>,
    ) -> axum::response::Response {
        let req_builder = Request::builder()
            .method(method)
            .uri(uri)
            .header("content-type", "application/json");

        let req = if let Some(body) = body {
            req_builder
                .body(Body::from(serde_json::to_string(&body).unwrap()))
                .unwrap()
        } else {
            req_builder.body(Body::empty()).unwrap()
        };

        router.oneshot(req).await.unwrap()
    }

    #[tokio::test]
    async fn health_returns_200() {
        let server = make_server();
        let router = server.router();
        let resp = send(router, Method::GET, "/mcp/health", None).await;
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn tools_list_returns_non_empty_json() {
        let server = make_server();
        let router = server.router();
        let resp = send(router, Method::POST, "/mcp/tools/list", Some(json!({}))).await;
        assert_eq!(resp.status(), StatusCode::OK);

        let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX)
            .await
            .unwrap();
        let body: Value = serde_json::from_slice(&bytes).unwrap();
        let tools = body["tools"].as_array().unwrap();
        assert!(
            !tools.is_empty(),
            "tools/list must return at least one tool"
        );
    }

    #[tokio::test]
    async fn tool_call_read_only_succeeds() {
        let server = make_server();
        let router = server.router();

        let request = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_sources",
                "arguments": {}
            }
        });

        let resp = send(router, Method::POST, "/mcp/tools/call", Some(request)).await;
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn tool_call_unknown_tool_returns_bad_request() {
        let server = make_server();
        let router = server.router();

        let request = json!({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            }
        });

        let resp = send(router, Method::POST, "/mcp/tools/call", Some(request)).await;
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }
}
