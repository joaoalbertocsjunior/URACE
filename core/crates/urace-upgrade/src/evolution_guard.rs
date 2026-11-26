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

// ── M62 — Governance vote gate for runtime upgrades ──────────────────────────

/// Minimum number of governance approvals required to activate a runtime upgrade.
pub const MIN_GOVERNANCE_APPROVALS: usize = 3;

/// A single governance approval for a proposed upgrade.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernanceApproval {
    pub approver_id: String,
    pub upgrade_version: String,
    pub approved_at: String,
}

/// Governance vote registry for upgrade proposals.
pub struct GovernanceVoteGate {
    /// upgrade_version → approvals
    approvals: HashMap<String, Vec<GovernanceApproval>>,
    min_approvals: usize,
}

impl GovernanceVoteGate {
    pub fn new(min_approvals: usize) -> Self {
        GovernanceVoteGate {
            approvals: HashMap::new(),
            min_approvals,
        }
    }

    /// Record an approval. Deduplicates by `approver_id` per version.
    pub fn approve(&mut self, approval: GovernanceApproval) {
        let list = self.approvals.entry(approval.upgrade_version.clone()).or_default();
        if !list.iter().any(|a| a.approver_id == approval.approver_id) {
            list.push(approval);
        }
    }

    /// Returns `true` iff `upgrade_version` has received at least `min_approvals` distinct approvals.
    pub fn is_approved(&self, upgrade_version: &str) -> bool {
        self.approvals
            .get(upgrade_version)
            .map(|a| a.len() >= self.min_approvals)
            .unwrap_or(false)
    }

    pub fn approval_count(&self, upgrade_version: &str) -> usize {
        self.approvals.get(upgrade_version).map(|a| a.len()).unwrap_or(0)
    }
}

impl Default for GovernanceVoteGate {
    fn default() -> Self {
        Self::new(MIN_GOVERNANCE_APPROVALS)
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

    // M62 — governance vote gate tests

    #[test]
    fn upgrade_requires_min_approvals() {
        let mut gate = GovernanceVoteGate::new(3);
        assert!(!gate.is_approved("v2.0.0"));

        for i in 0..2u32 {
            gate.approve(GovernanceApproval {
                approver_id: format!("approver-{i}"),
                upgrade_version: "v2.0.0".into(),
                approved_at: "2026-01-01T00:00:00Z".into(),
            });
        }
        assert!(!gate.is_approved("v2.0.0"), "2 approvals < 3 — not yet approved");

        gate.approve(GovernanceApproval {
            approver_id: "approver-2".into(),
            upgrade_version: "v2.0.0".into(),
            approved_at: "2026-01-01T00:00:00Z".into(),
        });
        assert!(gate.is_approved("v2.0.0"), "3 approvals — approved");
    }

    #[test]
    fn duplicate_approvals_not_counted() {
        let mut gate = GovernanceVoteGate::new(2);
        for _ in 0..5 {
            gate.approve(GovernanceApproval {
                approver_id: "same-approver".into(),
                upgrade_version: "v3.0.0".into(),
                approved_at: "2026-01-01".into(),
            });
        }
        assert_eq!(gate.approval_count("v3.0.0"), 1);
        assert!(!gate.is_approved("v3.0.0"));
    }
}
