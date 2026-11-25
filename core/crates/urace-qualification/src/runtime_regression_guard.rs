//! Runtime regression guard: blocks state persistence when the latest quality delta is a regression.
//!
//! Ported from `runtime/urace/runtime_regression_guard.py`. This is a soft gate —
//! it emits a `REGRESSION_BLOCKED` decision record and returns `GuardStatus::Regression`
//! so the cycle caller can suppress the state save. It never raises and never
//! modifies state without being explicitly asked to record a decision.

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::trial_common::{now_iso, trial_identifier};

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum RegressionGuardError {
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// Guard status
// ---------------------------------------------------------------------------

/// Result of running the regression guard.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum GuardStatus {
    /// No regression detected — state persistence is allowed.
    Ok,
    /// Most recent quality delta is a regression; state persistence is blocked.
    Regression,
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// A quality delta record stored in `state["quality_deltas"]`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityDelta {
    /// Unique identifier for this delta record.
    pub id: String,
    /// Scope the delta applies to (e.g. a file path or feature id).
    pub scope: String,
    /// Numeric delta value (positive = improvement, negative = regression).
    pub delta: f64,
    /// Classification: "IMPROVEMENT", "REGRESSION", or "NEUTRAL".
    pub classification: String,
    /// ISO-8601 timestamp when this delta was measured.
    pub measured_at: String,
}

/// A decision record stored in `state["decision_records"]`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionRecord {
    /// Unique identifier for this decision record.
    pub id: String,
    /// Kind of decision (e.g. "REGRESSION_BLOCKED", "CHECKPOINT_ACCEPTANCE").
    pub kind: String,
    /// ISO-8601 timestamp when the decision was made.
    pub decided_at: String,
    /// Disposition string mirroring `kind`.
    pub disposition: String,
    /// Subject the decision applies to (scope name or "all-scopes").
    pub subject: String,
    /// Human-readable rationale.
    pub rationale: String,
}

// ---------------------------------------------------------------------------
// Guard functions
// ---------------------------------------------------------------------------

/// Check whether the most recent quality delta for `scope` (or all scopes) is
/// a REGRESSION with no subsequent CHECKPOINT_ACCEPTANCE decision record.
///
/// Returns `GuardStatus::Ok` when persistence is safe, `GuardStatus::Regression`
/// when it must be suppressed.
pub fn check(
    deltas: &[QualityDelta],
    decisions: &[DecisionRecord],
    scope: Option<&str>,
) -> GuardStatus {
    if deltas.is_empty() {
        return GuardStatus::Ok;
    }

    let scopes_to_check: Vec<&str> = if let Some(s) = scope {
        vec![s]
    } else {
        let mut seen = std::collections::HashSet::new();
        deltas
            .iter()
            .filter_map(|d| {
                if seen.insert(d.scope.as_str()) {
                    Some(d.scope.as_str())
                } else {
                    None
                }
            })
            .collect()
    };

    for s in scopes_to_check {
        let scope_deltas: Vec<&QualityDelta> = deltas.iter().filter(|d| d.scope == s).collect();
        if scope_deltas.is_empty() {
            continue;
        }
        let latest = scope_deltas
            .iter()
            .max_by(|a, b| a.measured_at.cmp(&b.measured_at))
            .expect("non-empty after filter");

        if latest.classification != "REGRESSION" {
            continue;
        }

        // Check for a subsequent CHECKPOINT_ACCEPTANCE that covers this scope.
        let regression_at = latest.measured_at.as_str();
        let accepted = decisions.iter().any(|r| {
            r.kind == "CHECKPOINT_ACCEPTANCE"
                && r.decided_at.as_str() >= regression_at
                && r.subject.contains(s)
        });

        if !accepted {
            return GuardStatus::Regression;
        }
    }

    GuardStatus::Ok
}

/// Build a `REGRESSION_BLOCKED` decision record for the given scope.
///
/// The caller is responsible for appending the returned record to their
/// `decision_records` collection.
pub fn build_blocked_record(scope: Option<&str>) -> DecisionRecord {
    DecisionRecord {
        id: trial_identifier(),
        kind: "REGRESSION_BLOCKED".into(),
        decided_at: now_iso(),
        disposition: "REGRESSION_BLOCKED".into(),
        subject: scope.unwrap_or("all-scopes").to_owned(),
        rationale: "Cycle blocked: most recent quality delta is REGRESSION with no subsequent CHECKPOINT_ACCEPTANCE".into(),
    }
}

/// Return a summary status object for display (e.g. `urace check --guard`).
pub fn guard_summary(deltas: &[QualityDelta], decisions: &[DecisionRecord]) -> serde_json::Value {
    let status = check(deltas, decisions, None);
    let scopes: std::collections::HashMap<&str, serde_json::Value> = {
        let mut seen = std::collections::HashSet::new();
        deltas
            .iter()
            .filter(|d| seen.insert(d.scope.as_str()))
            .map(|_| ())
            .for_each(drop);

        seen.clear();
        let unique_scopes: Vec<&str> = deltas
            .iter()
            .filter_map(|d| {
                if seen.insert(d.scope.as_str()) {
                    Some(d.scope.as_str())
                } else {
                    None
                }
            })
            .collect();

        unique_scopes
            .into_iter()
            .filter_map(|s| {
                let latest = deltas
                    .iter()
                    .filter(|d| d.scope == s)
                    .max_by(|a, b| a.measured_at.cmp(&b.measured_at))?;
                Some((
                    s,
                    serde_json::json!({
                        "classification": latest.classification,
                        "measured_at": latest.measured_at,
                        "delta": latest.delta,
                    }),
                ))
            })
            .collect()
    };

    serde_json::json!({
        "status": match status { GuardStatus::Ok => "OK", GuardStatus::Regression => "REGRESSION" },
        "checked_scopes": scopes.len(),
        "per_scope": scopes,
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn delta(scope: &str, classification: &str, measured_at: &str, value: f64) -> QualityDelta {
        QualityDelta {
            id: trial_identifier(),
            scope: scope.into(),
            delta: value,
            classification: classification.into(),
            measured_at: measured_at.into(),
        }
    }

    fn acceptance(scope: &str, decided_at: &str) -> DecisionRecord {
        DecisionRecord {
            id: trial_identifier(),
            kind: "CHECKPOINT_ACCEPTANCE".into(),
            decided_at: decided_at.into(),
            disposition: "CHECKPOINT_ACCEPTANCE".into(),
            subject: scope.into(),
            rationale: "manually accepted".into(),
        }
    }

    #[test]
    fn ok_when_no_deltas() {
        assert_eq!(check(&[], &[], None), GuardStatus::Ok);
    }

    #[test]
    fn ok_when_latest_is_improvement() {
        let deltas = vec![
            delta("scope-a", "REGRESSION", "2026-01-01T00:00:00Z", -0.5),
            delta("scope-a", "IMPROVEMENT", "2026-01-02T00:00:00Z", 0.3),
        ];
        assert_eq!(check(&deltas, &[], None), GuardStatus::Ok);
    }

    #[test]
    fn regression_when_latest_is_regression() {
        let deltas = vec![delta("scope-b", "REGRESSION", "2026-01-03T00:00:00Z", -0.2)];
        assert_eq!(check(&deltas, &[], None), GuardStatus::Regression);
    }

    #[test]
    fn ok_when_checkpoint_acceptance_follows_regression() {
        let deltas = vec![delta("scope-c", "REGRESSION", "2026-01-04T00:00:00Z", -0.1)];
        let decisions = vec![acceptance("scope-c", "2026-01-05T00:00:00Z")];
        assert_eq!(check(&deltas, &decisions, None), GuardStatus::Ok);
    }

    #[test]
    fn blocked_record_has_correct_kind() {
        let record = build_blocked_record(Some("scope-d"));
        assert_eq!(record.kind, "REGRESSION_BLOCKED");
        assert_eq!(record.disposition, "REGRESSION_BLOCKED");
        assert_eq!(record.subject, "scope-d");
        assert!(!record.id.is_empty());
    }
}
