//! urace-state — runtime state management for URACE nodes.
//!
//! Covers: scope priority queues, asset registry, reputation categories,
//! resource usage tracking, workflow state machines, decision records,
//! bounded inbox, and node self-metrics.

pub mod asset_registry;
pub mod decision_record;
pub mod inbox;
pub mod reputation_categories;
pub mod resource_usage;
pub mod scope_priority;
pub mod self_metrics;
pub mod workflow_state;

pub use asset_registry::{Asset, AssetError, AssetRegistry};
pub use decision_record::{DecisionRecord, DecisionStore, ProvenanceStatus};
pub use inbox::{Inbox, InboxError, InboxRateGuard, InboxRateResult, Message, INBOX_MICRO_BURN_UCR, INBOX_RATE_LIMIT_PER_MIN};
pub use reputation_categories::{
    ConsensusProfile, PeerReputation, ReputationCategories, ReputationStore,
};
pub use resource_usage::{ResourceUsage, UsageTracker};
pub use scope_priority::{PriorityQueue, ScopeScore};
pub use self_metrics::{MetricEntry, MetricsCollector, NodeMetrics};
pub use workflow_state::{WorkflowError, WorkflowState, WorkflowTransition};
