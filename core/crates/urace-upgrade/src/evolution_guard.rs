//! Evolution guard — prevents regressions across runtime upgrades.
//!
//! Rust port of `evolution_guard.py`.
//! Records baseline metric snapshots and rejects candidates that regress them.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum EvolutionGuardError {
    #[error("regression in metric '{metric}': baseline={baseline}, candidate={candidate}")]
    Regression {
        metric: String,
        baseline: f64,
        candidate: f64,
    },

    #[error("missing metric '{metric}' in candidate snapshot")]
    MissingMetric { metric: String },

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// Snapshot of numeric metrics for a runtime version.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MetricSnapshot {
    pub metrics: HashMap<String, f64>,
    pub version: String,
}

/// Guards against metric regressions when activating a new runtime.
pub struct EvolutionGuard {
    baseline: MetricSnapshot,
    /// Allowed regression fraction (0.0 = zero tolerance, 0.05 = 5% allowed).
    tolerance: f64,
}

impl EvolutionGuard {
    pub fn new(baseline: MetricSnapshot, tolerance: f64) -> Self {
        EvolutionGuard {
            baseline,
            tolerance,
        }
    }

    /// Checks whether `candidate` regresses any metric beyond `tolerance`.
    pub fn check(&self, candidate: &MetricSnapshot) -> Result<(), EvolutionGuardError> {
        for (metric, &base_val) in &self.baseline.metrics {
            match candidate.metrics.get(metric) {
                None => {
                    return Err(EvolutionGuardError::MissingMetric {
                        metric: metric.clone(),
                    });
                }
                Some(&cand_val) => {
                    // For metrics where higher is better (e.g. throughput), regression = cand < base.
                    // We use: regression if cand < base * (1 - tolerance).
                    let floor = base_val * (1.0 - self.tolerance);
                    if cand_val < floor {
                        return Err(EvolutionGuardError::Regression {
                            metric: metric.clone(),
                            baseline: base_val,
                            candidate: cand_val,
                        });
                    }
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn snapshot(pairs: &[(&str, f64)], version: &str) -> MetricSnapshot {
        MetricSnapshot {
            metrics: pairs.iter().map(|(k, v)| (k.to_string(), *v)).collect(),
            version: version.to_owned(),
        }
    }

    #[test]
    fn no_regression_passes() {
        let guard = EvolutionGuard::new(snapshot(&[("throughput", 100.0)], "v1"), 0.05);
        assert!(guard
            .check(&snapshot(&[("throughput", 100.0)], "v2"))
            .is_ok());
    }

    #[test]
    fn within_tolerance_passes() {
        let guard = EvolutionGuard::new(snapshot(&[("throughput", 100.0)], "v1"), 0.05);
        assert!(guard
            .check(&snapshot(&[("throughput", 96.0)], "v2"))
            .is_ok());
    }

    #[test]
    fn beyond_tolerance_fails() {
        let guard = EvolutionGuard::new(snapshot(&[("throughput", 100.0)], "v1"), 0.05);
        let err = guard
            .check(&snapshot(&[("throughput", 90.0)], "v2"))
            .unwrap_err();
        assert!(matches!(err, EvolutionGuardError::Regression { .. }));
    }

    #[test]
    fn missing_metric_fails() {
        let guard = EvolutionGuard::new(snapshot(&[("throughput", 100.0)], "v1"), 0.0);
        let err = guard.check(&snapshot(&[], "v2")).unwrap_err();
        assert!(matches!(err, EvolutionGuardError::MissingMetric { .. }));
    }
}
