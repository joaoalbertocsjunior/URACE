//! MCP/JSON-RPC server exposing URACE capabilities.
//!
//! Every tool call passes through the §62z `AuthorityGate` before execution.
//! Corresponds to `mcp_server.py`, `api_interface.py`, and `command_surface.py`.

pub mod api_interface;
pub mod server;
pub mod tools;

pub use server::{McpServer, McpServerConfig};
pub use tools::{McpTool, ToolRegistry};
