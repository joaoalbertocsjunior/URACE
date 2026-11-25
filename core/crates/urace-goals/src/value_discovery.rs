//! Value signal discovery — port of `value_discovery.py`.
//!
//! Discovers and ranks value signals derived from project state and config.
//! Signals are advisory only and never confer authority (§62z invariant).

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::{SystemTime, UNIX_EPOCH};

// Known indicator names from the Python module.
const INDICATOR_NAMES: &[&str] = &[
    "correctness",
    "completion_seconds",
    "tokens",
    "interventions",
    "rework",
    "retention",
];

fn now_unix() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

fn iso_now() -> String {
    // RFC-3339 approximation using seconds since epoch; real code would use chrono.
    let secs = now_unix() as u64;
    format!("{}Z", secs) // placeholder ISO representation
}

/// Compute a stable hex digest of any serialisable value.
pub fn value_digest(v: &Value) -> String {
    let canonical = serde_json::to_string(v).unwrap_or_default();
    let hash = Sha256::digest(canonical.as_bytes());
    format!("{:x}", hash)
}

// ── ValueSignal ───────────────────────────────────────────────────────────────

/// A single observable value signal extracted from project state.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ValueSignal {
    /// Stable identifier derived from signal content.
    pub id: String,
    /// Signal kind: "declared_intent" | "provided_observation" | "market_signal" |
    /// "engineering" | "real_user" | "synthetic".
    pub kind: String,
    /// Strength in `[0.0, 1.0]`; higher means more evidence.
    pub strength: f64,
    /// Human-readable origin description.
    pub source: String,
    /// ISO-8601 timestamp when the signal was recorded.
    pub at: String,
}

impl ValueSignal {
    fn new(kind: impl Into<String>, strength: f64, source: impl Into<String>) -> Self {
        let kind = kind.into();
        let source = source.into();
        let at = iso_now();
        let id_input = serde_json::json!({ "kind": &kind, "source": &source });
        let id = "signal-".to_string() + &value_digest(&id_input)[..24];
        ValueSignal { id, kind, strength, source, at }
    }
}

// ── ValueDiscovery ────────────────────────────────────────────────────────────

/// Stateless engine that extracts `ValueSignal`s from project state.
#[derive(Debug, Default)]
pub struct ValueDiscovery;

impl ValueDiscovery {
    pub fn new() -> Self {
        ValueDiscovery
    }

    /// Extract all value signals observable in `state` given `config`.
    ///
    /// Mirrors the Python `proposed()` / `sync()` logic without I/O:
    /// reads project intent, requirements, hypotheses, and indicator observations.
    pub fn discover_signals(&self, state: &Value, config: &Value) -> Vec<ValueSignal> {
        let mut signals: Vec<ValueSignal> = Vec::new();

        // 1. Declared-intent signals from project.requirements in config or state.
        let project = state
            .get("project")
            .or_else(|| config.get("project"))
            .and_then(|p| p.as_object());

        if let Some(proj) = project {
            let intent = proj.get("intent").and_then(|v| v.as_str()).unwrap_or("");
            if !intent.trim().is_empty() {
                // One high-strength declared intent signal.
                signals.push(ValueSignal::new(
                    "declared_intent",
                    0.9,
                    "project.intent",
                ));

                // One signal per declared requirement.
                if let Some(reqs) = proj.get("requirements").and_then(|r| r.as_array()) {
                    for req in reqs {
                        if let (Some(title), Some(id)) = (
                            req.get("title").and_then(|v| v.as_str()),
                            req.get("id").and_then(|v| v.as_str()),
                        ) {
                            if !title.trim().is_empty() {
                                signals.push(ValueSignal::new(
                                    "declared_intent",
                                    0.75,
                                    format!("project.requirements:{}", id),
                                ));
                            }
                        }
                    }
                }
            }
        }

        // 2. Engineering signals from operations / checkpoints.
        if let Some(ops) = state.get("operations").and_then(|v| v.as_array()) {
            let verified_ops: Vec<&Value> = ops
                .iter()
                .filter(|op| {
                    op.get("outcome")
                        .and_then(|o| o.get("status"))
                        .and_then(|s| s.as_str())
                        .map(|s| s == "OUTCOME_VERIFIED" || s == "REAL_USER_VALUE_VERIFIED")
                        .unwrap_or(false)
                })
                .collect();

            if !verified_ops.is_empty() {
                let strength = (0.4 + 0.05 * verified_ops.len() as f64).min(1.0);
                signals.push(ValueSignal::new(
                    "engineering",
                    strength,
                    format!("operations.verified_count:{}", verified_ops.len()),
                ));
            }
        }

        // 3. Observation signals from value_discovery.observations in state.
        if let Some(observations) = state
            .get("value_discovery")
            .and_then(|vd| vd.get("observations"))
            .and_then(|v| v.as_array())
        {
            // Count observations per indicator.
            let mut by_indicator: HashMap<&str, usize> = HashMap::new();
            for obs in observations {
                if let Some(metric) = obs.get("metric").and_then(|m| m.as_str()) {
                    if INDICATOR_NAMES.contains(&metric) {
                        *by_indicator.entry(metric).or_insert(0) += 1;
                    }
                }
            }
            for (metric, count) in &by_indicator {
                let strength = (0.3 + 0.07 * *count as f64).min(0.95);
                signals.push(ValueSignal::new(
                    "provided_observation",
                    strength,
                    format!("value_discovery.observations:{}", metric),
                ));
            }
        }

        // 4. Market signals from external metric state.
        if let Some(ext) = state.get("external_metric_state") {
            if let Some(latest) = ext.get("latest").and_then(|l| l.as_array()) {
                if !latest.is_empty() {
                    signals.push(ValueSignal::new(
                        "market_signal",
                        0.6,
                        format!("external_metrics.observations:{}", latest.len()),
                    ));
                }
            }
        }

        // 5. Real-user signals from hypotheses with verified benefit.
        if let Some(hypotheses) = state
            .get("value_discovery")
            .and_then(|vd| vd.get("hypotheses"))
            .and_then(|v| v.as_array())
        {
            let verified_count = hypotheses
                .iter()
                .filter(|h| {
                    h.get("real_user_benefit_verified")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false)
                })
                .count();
            if verified_count > 0 {
                signals.push(ValueSignal::new(
                    "real_user",
                    (0.5 + 0.1 * verified_count as f64).min(1.0),
                    format!("value_discovery.real_user_verified:{}", verified_count),
                ));
            }
        }

        signals
    }
}

// ── Free functions ────────────────────────────────────────────────────────────

/// Discover signals then rank them (descending by strength).
pub fn discover_signals(state: &Value, config: &Value) -> Vec<ValueSignal> {
    ValueDiscovery::new().discover_signals(state, config)
}

/// Sort `signals` by strength descending. Returns a new `Vec`.
pub fn rank_signals(signals: &[ValueSignal]) -> Vec<ValueSignal> {
    let mut sorted = signals.to_vec();
    sorted.sort_by(|a, b| b.strength.partial_cmp(&a.strength).unwrap_or(std::cmp::Ordering::Equal));
    sorted
}

/// Convenience: discover, rank, and return the top `n` signals.
pub fn top_signals(state: &Value, config: &Value, n: usize) -> Vec<ValueSignal> {
    let signals = discover_signals(state, config);
    let ranked = rank_signals(&signals);
    ranked.into_iter().take(n).collect()
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn project_state() -> Value {
        json!({
            "project": {
                "intent": "Improve developer productivity via AI-assisted coding",
                "requirements": [
                    { "id": "r1", "title": "Reduce review time", "success_measure": "30% less" },
                    { "id": "r2", "title": "Increase test coverage", "success_measure": "90%" }
                ]
            },
            "operations": [
                { "outcome": { "status": "OUTCOME_VERIFIED" } },
                { "outcome": { "status": "OUTCOME_VERIFIED" } }
            ]
        })
    }

    #[test]
    fn discovers_declared_intent_and_engineering_signals() {
        let state = project_state();
        let config = json!({});
        let signals = discover_signals(&state, &config);
        assert!(!signals.is_empty(), "must find at least one signal");

        let kinds: Vec<&str> = signals.iter().map(|s| s.kind.as_str()).collect();
        assert!(kinds.contains(&"declared_intent"), "should find declared_intent");
        assert!(kinds.contains(&"engineering"), "should find engineering");
    }

    #[test]
    fn rank_signals_orders_by_strength_descending() {
        let s1 = ValueSignal {
            id: "a".into(),
            kind: "engineering".into(),
            strength: 0.3,
            source: "s".into(),
            at: "now".into(),
        };
        let s2 = ValueSignal {
            id: "b".into(),
            kind: "declared_intent".into(),
            strength: 0.9,
            source: "s".into(),
            at: "now".into(),
        };
        let s3 = ValueSignal {
            id: "c".into(),
            kind: "market_signal".into(),
            strength: 0.6,
            source: "s".into(),
            at: "now".into(),
        };
        let ranked = rank_signals(&[s1, s2, s3]);
        assert_eq!(ranked[0].strength, 0.9);
        assert_eq!(ranked[1].strength, 0.6);
        assert_eq!(ranked[2].strength, 0.3);
    }

    #[test]
    fn top_signals_limits_count() {
        let state = project_state();
        let config = json!({});
        let top2 = top_signals(&state, &config, 2);
        assert!(top2.len() <= 2);
    }

    #[test]
    fn empty_state_returns_no_signals() {
        let signals = discover_signals(&json!({}), &json!({}));
        assert!(signals.is_empty());
    }
}
