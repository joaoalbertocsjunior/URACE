//! `urace-goals` — goal lifecycle, auto-goals, analytics, and telemetry.
//!
//! # Key invariant
//! `GoalStore::complete` only sets `should_mint = true` when `score_delta > 0`.
//! Zero or negative deltas never trigger minting (§CLAUDE.md token economics).

pub mod analytics;
pub mod auto_goals;
pub mod decision_feedback;
pub mod external_metrics;
pub mod goal;
pub mod goal_selector;
pub mod telemetry;

pub use analytics::{AnalyticsError, Metric, MetricStore};
pub use auto_goals::AutoGoalEngine;
pub use external_metrics::{
    collect, export_metrics_sink, score_delta_from_external, CollectResult, ExportResult,
    ExternalEvent, ExternalMetricsError, Observation, SourceError,
};
pub use goal::{Goal, GoalError, GoalStatus, GoalStore};
pub use goal_selector::{DefaultGoalSelector, GoalSelector, SelectedGoal};
pub use telemetry::{TelemetryEmitter, TelemetryError, TelemetryEvent, BUFFER_LIMIT};
