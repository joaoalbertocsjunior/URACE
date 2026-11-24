//! Portfolio runner: async executor for portfolio improvement tasks.
//!
//! Ported from `portfolio_runner.py`. Manages the autonomous improvement loop:
//! plan → mutate → evaluate → select.

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::info;

#[derive(Debug, Error)]
pub enum RunnerError {
    #[error("portfolio runner error: {0}")]
    Runner(String),
    #[error("cohort policy paused: {0}")]
    CohortPolicyPaused(String),
}

/// Phase of the autonomous improvement loop.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum RunPhase {
    Idle,
    Planned,
    Created,
    Mutated,
    Evaluated,
}

impl std::fmt::Display for RunPhase {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Idle => write!(f, "IDLE"),
            Self::Planned => write!(f, "PLANNED"),
            Self::Created => write!(f, "CREATED"),
            Self::Mutated => write!(f, "MUTATED"),
            Self::Evaluated => write!(f, "EVALUATED"),
        }
    }
}

/// Configuration for a portfolio runner cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunOptions {
    pub portfolio_id: String,
    /// Maximum number of generations (0 = unlimited).
    pub max_cycles: u32,
    /// Executor variant: "auto", "codex", "claude".
    pub executor: String,
    /// Maximum execution time per cycle in seconds.
    pub max_seconds: u32,
    /// Whether adaptive cost-aware comparison is enabled.
    pub adaptive: bool,
}

impl Default for RunOptions {
    fn default() -> Self {
        RunOptions {
            portfolio_id: String::new(),
            max_cycles: 1,
            executor: "auto".to_owned(),
            max_seconds: 480,
            adaptive: true,
        }
    }
}

/// Result of a single portfolio improvement cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CycleResult {
    pub portfolio_id: String,
    pub generation: u32,
    pub phase_completed: RunPhase,
    pub variants_evaluated: u32,
    pub accepted_improvements: u32,
    pub executor_calls: u32,
}

/// Async portfolio runner for improvement tasks.
///
/// The runner manages the lifecycle of competing variants:
/// 1. Plan the next generation.
/// 2. Create the planned cohort.
/// 3. Mutate each candidate.
/// 4. Evaluate each candidate.
/// 5. Select and archive.
pub struct PortfolioRunner {
    options: RunOptions,
}

impl PortfolioRunner {
    pub fn new(options: RunOptions) -> Self {
        PortfolioRunner { options }
    }

    /// Run a single improvement generation (synchronous stub — full async in Phase 5).
    ///
    /// Returns a `CycleResult` describing what happened.
    pub fn run_one_cycle(&self, generation: u32) -> Result<CycleResult, RunnerError> {
        info!(
            portfolio_id = %self.options.portfolio_id,
            generation,
            executor = %self.options.executor,
            "starting portfolio improvement cycle"
        );

        // Guard: check cohort policy is not paused.
        // (Full policy check deferred to Phase 5; stub always proceeds.)

        Ok(CycleResult {
            portfolio_id: self.options.portfolio_id.clone(),
            generation,
            phase_completed: RunPhase::Evaluated,
            variants_evaluated: 0,
            accepted_improvements: 0,
            executor_calls: 0,
        })
    }

    /// Run up to `max_cycles` improvement cycles.
    pub fn run(&self) -> Result<Vec<CycleResult>, RunnerError> {
        let mut results = Vec::new();
        let limit = if self.options.max_cycles == 0 {
            1 // safe default for the stub
        } else {
            self.options.max_cycles
        };

        for gen in 0..limit {
            let result = self.run_one_cycle(gen)?;
            results.push(result);
        }
        Ok(results)
    }

    /// Normalize run options with defaults for missing fields.
    pub fn normalize_options(mut opts: RunOptions) -> RunOptions {
        if opts.executor.is_empty() {
            opts.executor = "auto".to_owned();
        }
        if opts.max_seconds == 0 {
            opts.max_seconds = 480;
        }
        opts
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn run_one_cycle_returns_result() {
        let opts = RunOptions {
            portfolio_id: "p1".to_owned(),
            max_cycles: 1,
            ..Default::default()
        };
        let runner = PortfolioRunner::new(opts);
        let result = runner.run_one_cycle(0).unwrap();
        assert_eq!(result.portfolio_id, "p1");
        assert_eq!(result.generation, 0);
        assert_eq!(result.phase_completed, RunPhase::Evaluated);
    }

    #[test]
    fn run_respects_max_cycles() {
        let opts = RunOptions {
            portfolio_id: "p1".to_owned(),
            max_cycles: 3,
            ..Default::default()
        };
        let runner = PortfolioRunner::new(opts);
        let results = runner.run().unwrap();
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn normalize_options_fills_defaults() {
        let opts = RunOptions {
            portfolio_id: "p1".to_owned(),
            executor: String::new(),
            max_seconds: 0,
            ..Default::default()
        };
        let normalized = PortfolioRunner::normalize_options(opts);
        assert_eq!(normalized.executor, "auto");
        assert_eq!(normalized.max_seconds, 480);
    }
}
