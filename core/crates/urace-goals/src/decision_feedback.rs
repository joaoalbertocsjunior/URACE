//! Decision feedback loops: outcome recording, forecast registration, and reinforcement signal.
//!
//! Forecasts are advisory only; they do not constitute authority or acceptance.
//! §62z: status resolution always delegates to `urace_authority::resolve`.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use thiserror::Error;

pub const SCHEMA: &str = "decision-benefit-feedback-v1";

// ── Errors ────────────────────────────────────────────────────────────────────

/// Errors from decision-feedback operations.
#[derive(Debug, Error)]
pub enum FeedbackError {
    #[error("invalid forecast: {reason}")]
    InvalidForecast { reason: String },

    #[error("decision record requires an id")]
    MissingDecisionId,

    #[error("forecast exceeds 12 KiB; select relevant explicit evidence")]
    ForecastTooLarge,

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

// ── Core types ────────────────────────────────────────────────────────────────

/// A single expected benefit dimension within a forecast.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenefitDimension {
    pub metric: String,
    pub unit: String,
    pub baseline: Option<f64>,
    pub expected: Option<f64>,
    pub direction: BenefitDirection,
    pub target_gain: Option<f64>,
}

/// Whether a higher or lower metric value is desirable.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum BenefitDirection {
    Higher,
    Lower,
}

/// An owner-registered forecast for a decision record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Forecast {
    #[serde(default)]
    pub benefits: Vec<BenefitDimension>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cost: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub risk: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub uncertainty: Option<String>,
    #[serde(default)]
    pub evidence_refs: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bottleneck_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub recommended_action: Option<String>,
    #[serde(default)]
    pub weights: HashMap<String, f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected_score: Option<f64>,
}

/// Stored forecast entry bound to a decision and context.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForecastEntry {
    pub id: String,
    pub decision_id: String,
    pub forecast: Forecast,
    pub at: String,
    pub timing: ForecastTiming,
    pub context_sha256: String,
    pub source: String,
    pub immutable_history: bool,
}

/// Whether the forecast was recorded before or after execution.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ForecastTiming {
    Retrospective,
    PreExecutionUnverifiedTimestamp,
}

/// Computed benefit score from a forecast.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenefitScore {
    pub value: Option<f64>,
    pub range: Option<[f64; 2]>,
    pub reason: String,
    pub calibrated: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub components: Option<Vec<ScoreComponent>>,
}

/// Per-dimension score component.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreComponent {
    pub metric: String,
    pub unit: String,
    pub expected_gain: f64,
    pub target_gain: f64,
    pub weight: f64,
    pub normalized: f64,
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn now_iso() -> String {
    // Minimal UTC timestamp without external time dep.
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    format!(
        "{}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        1970 + secs / 31_557_600,
        1 + (secs % 31_557_600) / 2_629_800,
        1 + (secs % 2_629_800) / 86_400,
        (secs % 86_400) / 3_600,
        (secs % 3_600) / 60,
        secs % 60,
    )
}

fn json_digest(value: &Value) -> String {
    let canonical = serde_json::to_string(value).unwrap_or_default();
    let hash = Sha256::digest(canonical.as_bytes());
    hex::encode(hash)
}

fn is_finite_f64(v: f64) -> bool {
    v.is_finite()
}

// ── Validation ────────────────────────────────────────────────────────────────

/// Validate a forecast; returns a clone with bounded fields or an error.
pub fn validate_forecast(forecast: &Forecast) -> Result<Forecast, FeedbackError> {
    // Evidence refs must be bounded strings.
    for r in &forecast.evidence_refs {
        if r.is_empty() || r.len() > 500 {
            return Err(FeedbackError::InvalidForecast {
                reason: "evidence_refs must be non-empty strings ≤500 chars".into(),
            });
        }
    }
    if forecast.benefits.len() > 20 {
        return Err(FeedbackError::InvalidForecast {
            reason: "at most 20 forecast dimensions".into(),
        });
    }
    let mut seen = std::collections::HashSet::new();
    for b in &forecast.benefits {
        if b.metric.is_empty() || b.metric.len() > 100 || b.unit.is_empty() || b.unit.len() > 100 {
            return Err(FeedbackError::InvalidForecast {
                reason: "metric/unit must be non-empty bounded strings".into(),
            });
        }
        if !seen.insert(b.metric.clone()) {
            return Err(FeedbackError::InvalidForecast {
                reason: format!("duplicate metric '{}'", b.metric),
            });
        }
        if let Some(tg) = b.target_gain {
            if !is_finite_f64(tg) || tg <= 0.0 {
                return Err(FeedbackError::InvalidForecast {
                    reason: "target_gain must be finite and positive".into(),
                });
            }
        }
        for v in [b.baseline, b.expected].into_iter().flatten() {
            if !is_finite_f64(v) {
                return Err(FeedbackError::InvalidForecast {
                    reason: "baseline and expected must be finite".into(),
                });
            }
        }
    }
    // Weights must be positive and reference known metrics.
    for (k, w) in &forecast.weights {
        if !seen.contains(k.as_str()) {
            return Err(FeedbackError::InvalidForecast {
                reason: format!("weight references unknown metric '{k}'"),
            });
        }
        if !is_finite_f64(*w) || *w <= 0.0 {
            return Err(FeedbackError::InvalidForecast {
                reason: "weights must be finite and positive".into(),
            });
        }
    }
    if let Some(es) = forecast.expected_score {
        if !is_finite_f64(es) || !(0.0..=100.0).contains(&es) {
            return Err(FeedbackError::InvalidForecast {
                reason: "expected_score must be in [0, 100]".into(),
            });
        }
    }
    // Size guard.
    let encoded = serde_json::to_string(forecast).map_err(FeedbackError::Serialization)?;
    if encoded.len() > 12_288 {
        return Err(FeedbackError::ForecastTooLarge);
    }
    Ok(forecast.clone())
}

// ── Scoring ───────────────────────────────────────────────────────────────────

/// Compute an advisory benefit score from a validated forecast.
pub fn score(forecast: &Forecast) -> BenefitScore {
    if forecast.evidence_refs.is_empty() {
        return BenefitScore {
            value: None,
            range: None,
            reason: "Missing attributable evidence".into(),
            calibrated: false,
            components: None,
        };
    }
    let metrics_set: std::collections::HashSet<_> = forecast
        .benefits
        .iter()
        .map(|b| b.metric.as_str())
        .collect();
    let weights_complete = !forecast.weights.is_empty()
        && forecast
            .weights
            .keys()
            .all(|k| metrics_set.contains(k.as_str()))
        && forecast.weights.len() == forecast.benefits.len();

    if !forecast.benefits.is_empty() && weights_complete {
        // Check all numeric fields are present.
        let all_known = forecast.benefits.iter().all(|b| {
            b.baseline.map(is_finite_f64).unwrap_or(false)
                && b.expected.map(is_finite_f64).unwrap_or(false)
                && b.target_gain.map(is_finite_f64).unwrap_or(false)
        });
        if !all_known {
            return BenefitScore {
                value: None,
                range: None,
                reason: "Unknown forecast baseline, expected value or owner target; no imputation"
                    .into(),
                calibrated: false,
                components: None,
            };
        }
        let mut components = Vec::new();
        let mut weighted_sum = 0.0_f64;
        let mut weight_total = 0.0_f64;
        for b in &forecast.benefits {
            let baseline = b.baseline.unwrap_or(0.0);
            let expected = b.expected.unwrap_or(0.0);
            let target = b.target_gain.unwrap_or(1.0);
            let gain = (expected - baseline)
                * if b.direction == BenefitDirection::Higher {
                    1.0
                } else {
                    -1.0
                };
            let w = forecast.weights[&b.metric];
            let normalized = (gain / target).clamp(-1.0, 1.0);
            weighted_sum += w * normalized;
            weight_total += w;
            components.push(ScoreComponent {
                metric: b.metric.clone(),
                unit: b.unit.clone(),
                expected_gain: gain,
                target_gain: target,
                weight: w,
                normalized,
            });
        }
        return BenefitScore {
            value: Some(100.0 * weighted_sum / weight_total),
            range: Some([-100.0, 100.0]),
            reason: "Owner-weighted forecast target attainment; provisional and uncalibrated"
                .into(),
            calibrated: false,
            components: Some(components),
        };
    }
    if let Some(es) = forecast.expected_score {
        return BenefitScore {
            value: Some(es),
            range: Some([0.0, 100.0]),
            reason: "Explicit owner estimate; uncalibrated, not measured benefit".into(),
            calibrated: false,
            components: None,
        };
    }
    BenefitScore {
        value: None,
        range: None,
        reason: "No explicit score or complete owner-defined dimensions/weights".into(),
        calibrated: false,
        components: None,
    }
}

// ── Forecast registration ─────────────────────────────────────────────────────

/// Register or update a forecast for a decision record in `state`.
///
/// Idempotent: returns the existing entry if the computed id matches.
pub fn register_forecast(
    state: &mut Value,
    decision_id: &str,
    forecast: &Forecast,
) -> Result<ForecastEntry, FeedbackError> {
    if decision_id.is_empty() {
        return Err(FeedbackError::MissingDecisionId);
    }
    let validated = validate_forecast(forecast)?;

    // Build context binding digest (objective fields + decision fields + intent).
    let binding_input = serde_json::json!({
        "decision_id": decision_id,
        "intent": state.get("intent"),
        "constraints": state.get("constraints"),
    });
    let context_sha256 = json_digest(&binding_input);

    let id_input = serde_json::json!({
        "decision_id": decision_id,
        "forecast": validated,
        "context_sha256": context_sha256,
    });
    let id = format!("forecast-{}", &json_digest(&id_input)[..24]);

    // Idempotency check.
    if let Some(existing) = state
        .get("decision_forecasts")
        .and_then(|m| m.get(decision_id))
    {
        if existing.get("id").and_then(Value::as_str) == Some(&id) {
            return serde_json::from_value(existing.clone()).map_err(FeedbackError::Serialization);
        }
    }

    // Determine timing: retrospective if the operation has already been attempted.
    let operation_started = state
        .get("operations")
        .and_then(Value::as_array)
        .map(|ops| {
            ops.iter().any(|op| {
                op.get("attempted_at").is_some()
                    || op.get("accepted_at").is_some()
                    || matches!(
                        op.get("status").and_then(Value::as_str),
                        Some("ACCEPTED") | Some("REJECTED") | Some("COMPLETED")
                    )
            })
        })
        .unwrap_or(false);

    let timing = if operation_started {
        ForecastTiming::Retrospective
    } else {
        ForecastTiming::PreExecutionUnverifiedTimestamp
    };

    let entry = ForecastEntry {
        id,
        decision_id: decision_id.to_owned(),
        forecast: validated,
        at: now_iso(),
        timing,
        context_sha256,
        source: "explicit owner input".into(),
        immutable_history: true,
    };

    let entry_value = serde_json::to_value(&entry).map_err(FeedbackError::Serialization)?;

    // Append to history (append-only invariant).
    state.as_object_mut().and_then(|m| {
        m.entry("decision_forecast_history")
            .or_insert_with(|| Value::Array(vec![]))
            .as_array_mut()
            .map(|arr| arr.push(entry_value.clone()))
    });

    // Update current map.
    state.as_object_mut().and_then(|m| {
        m.entry("decision_forecasts")
            .or_insert_with(|| Value::Object(Default::default()))
            .as_object_mut()
            .map(|map| map.insert(decision_id.to_owned(), entry_value))
    });

    Ok(entry)
}

// ── Compact summary ───────────────────────────────────────────────────────────

/// Compact representation of a feedback view result for display.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompactFeedback {
    pub decision_id: String,
    pub expected_benefit_score: Option<f64>,
    pub bottleneck_ids: Vec<String>,
    pub action_recommendation: Option<String>,
    pub detail_command: String,
}

/// Produce a compact summary from a forecast entry.
pub fn compact(entry: &ForecastEntry) -> CompactFeedback {
    let score_val = score(&entry.forecast).value;
    let bottleneck_ids: Vec<String> = entry.forecast.bottleneck_id.iter().cloned().collect();
    CompactFeedback {
        decision_id: entry.decision_id.clone(),
        expected_benefit_score: score_val,
        bottleneck_ids,
        action_recommendation: entry.forecast.recommended_action.clone(),
        detail_command: format!("decision inspect {}", entry.decision_id),
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn simple_forecast() -> Forecast {
        Forecast {
            benefits: vec![BenefitDimension {
                metric: "latency_ms".into(),
                unit: "ms".into(),
                baseline: Some(100.0),
                expected: Some(80.0),
                direction: BenefitDirection::Lower,
                target_gain: Some(20.0),
            }],
            cost: None,
            risk: None,
            uncertainty: None,
            evidence_refs: vec!["evidence-abc".into()],
            bottleneck_id: None,
            recommended_action: Some("reduce DB round trips".into()),
            weights: [("latency_ms".to_owned(), 1.0)].into(),
            expected_score: None,
        }
    }

    #[test]
    fn valid_forecast_scores_correctly() {
        let f = simple_forecast();
        validate_forecast(&f).expect("should be valid");
        let s = score(&f);
        assert!(s.value.is_some());
        assert!(!s.calibrated);
        assert_eq!(s.range, Some([-100.0, 100.0]));
    }

    #[test]
    fn missing_evidence_yields_no_score() {
        let mut f = simple_forecast();
        f.evidence_refs.clear();
        let s = score(&f);
        assert!(s.value.is_none());
        assert!(s.reason.contains("evidence"));
    }

    #[test]
    fn expected_score_fallback() {
        let f = Forecast {
            benefits: vec![],
            cost: None,
            risk: None,
            uncertainty: None,
            evidence_refs: vec!["ev-1".into()],
            bottleneck_id: None,
            recommended_action: None,
            weights: Default::default(),
            expected_score: Some(72.0),
        };
        let s = score(&f);
        assert_eq!(s.value, Some(72.0));
    }

    #[test]
    fn register_forecast_is_idempotent() {
        let mut state = json!({ "decision_forecasts": {}, "decision_forecast_history": [] });
        let f = simple_forecast();
        let e1 = register_forecast(&mut state, "dec-1", &f).unwrap();
        let e2 = register_forecast(&mut state, "dec-1", &f).unwrap();
        assert_eq!(e1.id, e2.id);
        // History should only have one entry on duplicate.
        let hist_len = state["decision_forecast_history"]
            .as_array()
            .map(|a| a.len())
            .unwrap_or(0);
        assert_eq!(hist_len, 1);
    }

    #[test]
    fn invalid_duplicate_metric_rejected() {
        let mut f = simple_forecast();
        f.benefits.push(f.benefits[0].clone()); // duplicate metric
        assert!(validate_forecast(&f).is_err());
    }
}
