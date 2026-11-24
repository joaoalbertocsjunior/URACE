//! `urace-goals` — goal lifecycle, auto-goals, analytics, and telemetry.
//!
//! # Key invariant
//! `GoalStore::complete` only sets `should_mint = true` when `score_delta > 0`.
//! Zero or negative deltas never trigger minting (§CLAUDE.md token economics).

pub mod analytics;
pub mod auto_goals;
pub mod goal;
pub mod telemetry;

pub use analytics::{AnalyticsError, Metric, MetricStore};
pub use auto_goals::AutoGoalEngine;
pub use goal::{Goal, GoalError, GoalStatus, GoalStore};
pub use telemetry::{TelemetryEmitter, TelemetryError, TelemetryEvent, BUFFER_LIMIT};
