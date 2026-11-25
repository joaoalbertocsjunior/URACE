//! MCP tool definitions.
//!
//! Each `McpTool` is a static description of a URACE capability exposed
//! to MCP clients.  Actual execution happens in `server.rs` after the
//! §62z authority gate is checked.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

/// A single MCP tool descriptor (matches the MCP `tools/list` schema).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpTool {
    pub name: String,
    pub description: String,
    #[serde(rename = "inputSchema")]
    pub input_schema: Value,
    pub annotations: ToolAnnotations,
}

/// Annotations describing the safety properties of a tool.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolAnnotations {
    #[serde(rename = "readOnlyHint")]
    pub read_only: bool,
    #[serde(rename = "destructiveHint")]
    pub destructive: bool,
}

impl McpTool {
    fn read_only(name: &str, description: &str, schema: Value) -> Self {
        Self {
            name: name.into(),
            description: description.into(),
            input_schema: schema,
            annotations: ToolAnnotations {
                read_only: true,
                destructive: false,
            },
        }
    }

    fn mutating(name: &str, description: &str, schema: Value) -> Self {
        Self {
            name: name.into(),
            description: description.into(),
            input_schema: schema,
            annotations: ToolAnnotations {
                read_only: false,
                destructive: false,
            },
        }
    }
}

/// The registry of all tools exposed by this MCP server.
#[derive(Debug, Clone)]
pub struct ToolRegistry {
    tools: Vec<McpTool>,
}

impl ToolRegistry {
    /// Build the default URACE tool registry.
    pub fn new() -> Self {
        Self {
            tools: vec![
                McpTool::read_only(
                    "list_sources",
                    "List all registered URACE sources and their current sync status.",
                    json!({
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": false,
                    }),
                ),
                McpTool::mutating(
                    "sync_source",
                    "Trigger a sync for a named source. Requires authority confirmation.",
                    json!({
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The registered name of the source to sync."
                            }
                        },
                        "required": ["name"],
                        "additionalProperties": false,
                    }),
                ),
                McpTool::read_only(
                    "get_work_queue",
                    "Return the current work queue with pending and active tasks.",
                    json!({
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": false,
                    }),
                ),
                McpTool::read_only(
                    "get_settlement_status",
                    "Return recent settlement results from the ledger.",
                    json!({
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": false,
                    }),
                ),
                McpTool::read_only(
                    "get_status",
                    "Return the runtime loop status (running, cycle count, last outcome).",
                    json!({
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": false,
                    }),
                ),
                McpTool::read_only(
                    "get_goals",
                    "Return the list of tracked goals and their current status.",
                    json!({
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": false,
                    }),
                ),
                McpTool::mutating(
                    "post_work_task",
                    "Post a work task to the market. Requires §62z authority confirmation.",
                    json!({
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Unique task identifier"},
                            "capabilities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Required executor capabilities"
                            },
                            "budget_ucr": {"type": "integer", "description": "Budget in UCR base units"}
                        },
                        "required": ["task_id"],
                        "additionalProperties": false,
                    }),
                ),
                McpTool::read_only(
                    "get_audit_events",
                    "Return recent audit events from the signed audit ledger.",
                    json!({
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Maximum number of events to return (default 50)"}
                        },
                        "required": [],
                        "additionalProperties": false,
                    }),
                ),
            ],
        }
    }

    /// Return all tools (for `tools/list`).
    pub fn all(&self) -> &[McpTool] {
        &self.tools
    }

    /// Look up a tool by name.
    pub fn get(&self, name: &str) -> Option<&McpTool> {
        self.tools.iter().find(|t| t.name == name)
    }

    /// Whether a tool is read-only (no authority gate needed for reads).
    pub fn is_read_only(&self, name: &str) -> bool {
        self.get(name)
            .map(|t| t.annotations.read_only)
            .unwrap_or(false)
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_has_eight_tools() {
        let reg = ToolRegistry::new();
        assert_eq!(reg.all().len(), 8);
    }

    #[test]
    fn list_sources_is_read_only() {
        let reg = ToolRegistry::new();
        assert!(reg.is_read_only("list_sources"));
    }

    #[test]
    fn sync_source_is_mutating() {
        let reg = ToolRegistry::new();
        assert!(!reg.is_read_only("sync_source"));
    }

    #[test]
    fn unknown_tool_returns_none() {
        let reg = ToolRegistry::new();
        assert!(reg.get("does_not_exist").is_none());
    }
}
