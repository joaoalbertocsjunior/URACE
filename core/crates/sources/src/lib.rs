//! `urace-sources` — source adapters, registry, M2M bridge, and HTTP control server.
//!
//! Replaces the external Python `sources-lib` git dependency with a native Rust
//! implementation that uses real crates from the workspace.
//!
//! # Quick start
//!
//! ```rust,no_run
//! use urace_sources::{SourceRegistry, SourceBridge};
//! use urace_sources::adapters::shell::ShellAdapter;
//! use std::time::Duration;
//!
//! # async fn example() {
//! let registry = SourceRegistry::new();
//! registry.register(Box::new(ShellAdapter::new("uname", "uname -a")));
//! let (bridge, mut rx) = SourceBridge::new(registry, Duration::from_secs(30));
//! tokio::spawn(bridge.run());
//! while let Some(event) = rx.recv().await {
//!     println!("{}: {}", event.kind, event.payload);
//! }
//! # }
//! ```

#![allow(dead_code)]

pub mod adapter;
pub mod adapters;
pub mod bridge;
pub mod events;
pub mod http;
pub mod m2m;
pub mod registry;

// Re-export the most commonly used types at the crate root.
pub use adapter::{AdapterError, SourceAdapter, SourceEvent};
pub use bridge::SourceBridge;
pub use events::EventBus;
pub use http::HttpControlServer;
pub use m2m::M2MServer;
pub use registry::SourceRegistry;
