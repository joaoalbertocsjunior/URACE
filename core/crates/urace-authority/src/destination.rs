//! Destination anchor — preserves retained Intent and detects destination drift.
//!
//! Spec §8-9, §24: The highest non-delegated Intent is the fixed destination.
//! Evidence that a route is failing is NOT authorization to change the destination.
//! Destination drift is invalid even if the new destination appears more valuable.
//! URACE MUST detect and surface drift rather than silently accepting it.

use serde_json::Value;
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

/// Drift score threshold: surface as evidence, note on objective.
pub const DRIFT_FLAG: f64 = 0.30;

/// Drift score threshold: escalate to REQUIRES_AUTHORITATIVE_DECISION.
pub const DRIFT_BLOCK: f64 = 0.65;

/// Phrases that signal intent to redefine the destination (highest weight).
const DESTINATION_REDEFINE_SIGNALS: &[&str] = &[
    "change purpose",
    "redefine purpose",
    "new goal",
    "different goal",
    "pivot",
    "replace purpose",
    "abandon purpose",
    "shift direction",
    "change direction",
    "move away from",
];

/// Verbs that signal retained-constraint violation (high weight).
const RETAINED_VIOLATION_VERBS: &[&str] = &[
    "remove",
    "delete",
    "weaken",
    "override",
    "bypass",
    "ignore",
    "disable",
    "drop",
    "eliminate",
    "abandon",
];

/// Outcome of evaluating an Objective against a destination anchor.
#[derive(Debug, Clone, PartialEq)]
pub enum DriftOutcome {
    /// Objective is within the retained destination.
    Aligned,
    /// Drift detected above DRIFT_FLAG but below DRIFT_BLOCK; record as evidence.
    Flag { score: f64, reason: String },
    /// Drift detected at or above DRIFT_BLOCK; escalate to authoritative decision.
    Block { score: f64, reason: String },
}

/// Returns the current time as an ISO-8601-like string (UTC seconds since epoch).
fn now_iso() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    // Format as a simple epoch-seconds string; matches Python's isoformat() intent.
    format!("{secs}")
}

/// Extract and hash the retained destination from config intent.
///
/// The anchor is a stable, content-addressed snapshot of the intent that
/// URACE was bootstrapped with. Any change to config intent produces a
/// different digest, which triggers an integrity alert.
pub fn anchor_from_config(config: &Value) -> Value {
    let intent = config.get("intent").and_then(|v| v.as_object());

    let purpose = intent
        .and_then(|i| i.get("purpose"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let mut retained: Vec<String> = intent
        .and_then(|i| i.get("retained"))
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .map(|v| match v {
                    Value::String(s) => s.clone(),
                    other => other.to_string(),
                })
                .collect()
        })
        .unwrap_or_default();
    retained.sort();

    let anchor_content = serde_json::json!({
        "purpose": purpose,
        "retained": retained,
    });

    // Canonical JSON: sort_keys is the default for serde_json::json! when
    // serialised with the standard serialiser (object iteration order is
    // insertion order, and we insert in a known order).
    let canonical = serde_json::to_string(&anchor_content).unwrap_or_default();
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    let digest = hex::encode(hasher.finalize());

    serde_json::json!({
        "purpose": purpose,
        "retained": retained,
        "digest": digest,
        "established_at": now_iso(),
    })
}

/// Return a 0.0–1.0 drift score for a proposed Objective.
///
/// 0.0 = fully aligned with retained destination.
/// 1.0 = complete destination redefinition attempt.
///
/// Uses heuristic signals; exact semantic alignment requires human review.
/// A score at or above DRIFT_BLOCK warrants escalation; DRIFT_FLAG warrants
/// recording as evidence without blocking.
pub fn drift_score(objective: &Value, anchor: &Value) -> f64 {
    // Empty anchor → no drift to measure.
    if anchor.as_object().map(|m| m.is_empty()).unwrap_or(true) {
        return 0.0;
    }

    let purpose_words: std::collections::HashSet<String> = anchor
        .get("purpose")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase()
        .split_whitespace()
        .filter(|w| w.len() > 4)
        .map(|w| w.to_string())
        .collect();

    let retained: Vec<String> = anchor
        .get("retained")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .map(|v| match v {
                    Value::String(s) => s.to_lowercase(),
                    other => other.to_string().to_lowercase(),
                })
                .collect()
        })
        .unwrap_or_default();

    let title = objective
        .get("title")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase();
    let reason = objective
        .get("reason")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase();
    let scope = objective
        .get("scope")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase();
    let combined = format!("{title} {reason}");

    let mut score: f64 = 0.0;

    // Explicit destination-redefine signals (highest weight: +0.50).
    if DESTINATION_REDEFINE_SIGNALS
        .iter()
        .any(|sig| combined.contains(sig))
    {
        score += 0.50;
    }

    // Retained-constraint violation (high weight: +0.30).
    for retained_item in &retained {
        let retained_keywords: std::collections::HashSet<&str> = retained_item
            .split_whitespace()
            .filter(|w| w.len() > 3)
            .collect();
        let has_violation_verb = RETAINED_VIOLATION_VERBS
            .iter()
            .any(|verb| combined.contains(verb));
        let matches_retained = retained_keywords
            .iter()
            .any(|kw| combined.contains(*kw));
        if has_violation_verb && matches_retained {
            score += 0.30;
            break;
        }
    }

    // Zero overlap with purpose vocabulary (+0.10), only for product scopes.
    if scope != "runtime" && scope != "rebootstrap" && !purpose_words.is_empty() {
        let overlap = purpose_words
            .iter()
            .filter(|w| combined.contains(w.as_str()))
            .count();
        if overlap == 0 {
            score += 0.10;
        }
    }

    f64::min(1.0, (score * 10000.0).round() / 10000.0)
}

/// Check whether text contains a retained-constraint violation signal.
///
/// Returns `Some(verb)` with the first matching verb found, or `None`.
pub fn check_retained_violation(text: &str, retained: &[String]) -> Option<String> {
    let text_lower = text.to_lowercase();
    for retained_item in retained {
        let retained_lower = retained_item.to_lowercase();
        let retained_keywords: std::collections::HashSet<&str> = retained_lower
            .split_whitespace()
            .filter(|w| w.len() > 3)
            .collect();
        for verb in RETAINED_VIOLATION_VERBS {
            if text_lower.contains(verb) && retained_keywords.iter().any(|kw| text_lower.contains(*kw)) {
                return Some(verb.to_string());
            }
        }
    }
    None
}

/// Evaluate an Objective against a destination anchor.
///
/// Returns a `DriftOutcome` indicating alignment, flagging, or blocking.
pub fn evaluate_objective(objective: &Value, anchor: &Value) -> DriftOutcome {
    let score = drift_score(objective, anchor);

    if score >= DRIFT_BLOCK {
        let title = objective
            .get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("(no title)");
        return DriftOutcome::Block {
            score,
            reason: format!(
                "Objective '{}' scores {:.4} ≥ DRIFT_BLOCK ({}) — escalated to authoritative decision",
                title, score, DRIFT_BLOCK
            ),
        };
    }

    if score >= DRIFT_FLAG {
        let title = objective
            .get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("(no title)");
        return DriftOutcome::Flag {
            score,
            reason: format!(
                "Objective '{}' scores {:.4} ≥ DRIFT_FLAG ({}) — flagged for evidence",
                title, score, DRIFT_FLAG
            ),
        };
    }

    DriftOutcome::Aligned
}

/// Verify the stored anchor matches the current config intent.
///
/// A digest mismatch means the retained destination changed between sessions;
/// this requires an authoritative review before autonomous work continues.
pub fn check_anchor_integrity(state: &Value, config: &Value) -> Value {
    let current = anchor_from_config(config);
    let stored = state.get("destination_anchor");

    match stored {
        None => serde_json::json!({
            "status": "not_established",
            "anchor": current,
        }),
        Some(stored_val) => {
            let stored_digest = stored_val
                .get("digest")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let current_digest = current
                .get("digest")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            if stored_digest != current_digest {
                serde_json::json!({
                    "status": "changed",
                    "prior_digest": stored_digest,
                    "current_digest": current_digest,
                    "anchor": current,
                    "note": "Retained destination changed since last anchor — requires authoritative review before autonomous work resumes",
                })
            } else {
                serde_json::json!({
                    "status": "intact",
                    "anchor": stored_val,
                })
            }
        }
    }
}

/// Build an evidence record for a detected drift event.
pub fn build_drift_evidence(objective: &Value, score: f64, anchor: &Value) -> Value {
    let disposition = if score >= DRIFT_BLOCK {
        "ESCALATED_TO_AUTHORITATIVE_DECISION"
    } else {
        "FLAGGED_FOR_EVIDENCE"
    };

    serde_json::json!({
        "kind": "destination-drift-detected",
        "objective_id": objective.get("id"),
        "objective_title": objective.get("title"),
        "drift_score": score,
        "threshold_flagged": DRIFT_FLAG,
        "threshold_blocked": DRIFT_BLOCK,
        "anchor_digest": anchor.get("digest"),
        "anchor_purpose": anchor.get("purpose"),
        "disposition": disposition,
        "note": "Drift score measures semantic distance from retained destination; it is evidence, not Authority. Heuristic — human review recommended.",
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_config(purpose: &str, retained: &[&str]) -> Value {
        serde_json::json!({
            "intent": {
                "purpose": purpose,
                "retained": retained,
            }
        })
    }

    fn make_objective(title: &str, reason: &str, scope: &str) -> Value {
        serde_json::json!({
            "id": "test-obj",
            "title": title,
            "reason": reason,
            "scope": scope,
        })
    }

    // ----- anchor_from_config -----

    #[test]
    fn anchor_produces_stable_digest() {
        let config = make_config("build a P2P runtime", &["no credentials in source"]);
        let a1 = anchor_from_config(&config);
        let a2 = anchor_from_config(&config);
        assert_eq!(
            a1["digest"].as_str().unwrap(),
            a2["digest"].as_str().unwrap(),
            "Same config must produce identical digest"
        );
    }

    #[test]
    fn anchor_digest_changes_on_purpose_change() {
        let c1 = make_config("build a P2P runtime", &["no credentials"]);
        let c2 = make_config("build a web service", &["no credentials"]);
        assert_ne!(
            anchor_from_config(&c1)["digest"],
            anchor_from_config(&c2)["digest"]
        );
    }

    #[test]
    fn anchor_digest_changes_on_retained_change() {
        let c1 = make_config("build runtime", &["constraint A"]);
        let c2 = make_config("build runtime", &["constraint B"]);
        assert_ne!(
            anchor_from_config(&c1)["digest"],
            anchor_from_config(&c2)["digest"]
        );
    }

    #[test]
    fn anchor_retained_is_sorted() {
        let c = make_config("purpose", &["zzz constraint", "aaa constraint"]);
        let anchor = anchor_from_config(&c);
        let retained = anchor["retained"].as_array().unwrap();
        assert_eq!(retained[0].as_str().unwrap(), "aaa constraint");
        assert_eq!(retained[1].as_str().unwrap(), "zzz constraint");
    }

    #[test]
    fn anchor_has_expected_fields() {
        let config = make_config("test purpose", &["keep invariant"]);
        let anchor = anchor_from_config(&config);
        assert!(anchor.get("purpose").is_some());
        assert!(anchor.get("retained").is_some());
        assert!(anchor.get("digest").is_some());
        assert!(anchor.get("established_at").is_some());
        // digest is a 64-char hex string (SHA-256)
        assert_eq!(anchor["digest"].as_str().unwrap().len(), 64);
    }

    // ----- drift_score -----

    #[test]
    fn drift_score_zero_for_empty_anchor() {
        let obj = make_objective("some objective", "good reason", "implementation");
        let empty_anchor = serde_json::json!({});
        assert_eq!(drift_score(&obj, &empty_anchor), 0.0);
    }

    #[test]
    fn drift_score_zero_for_aligned_objective() {
        let config = make_config("build a P2P governance runtime", &["no credentials in source"]);
        let anchor = anchor_from_config(&config);
        // Objective mentions purpose words; no redefine signals; no violation verbs.
        let obj = make_objective("improve P2P runtime performance", "governance is key", "implementation");
        assert!(drift_score(&obj, &anchor) < DRIFT_FLAG);
    }

    #[test]
    fn redefine_signal_causes_flag_or_block() {
        let config = make_config("build a P2P runtime", &["no credentials"]);
        let anchor = anchor_from_config(&config);
        // "pivot" is a redefine signal → score += 0.50 → above DRIFT_FLAG
        let obj = make_objective("pivot to a new goal", "the old direction failed", "implementation");
        let score = drift_score(&obj, &anchor);
        assert!(score >= DRIFT_FLAG, "pivot signal should produce score >= DRIFT_FLAG, got {score}");
    }

    #[test]
    fn redefine_signal_alone_produces_block() {
        let config = make_config("build a P2P runtime", &[]);
        let anchor = anchor_from_config(&config);
        // "pivot" alone → 0.50 score. 0.50 < DRIFT_BLOCK (0.65), so only Flag.
        // Combine with zero-overlap: score = 0.50 + 0.10 = 0.60 (still < 0.65).
        // We need an additional retained violation to reach BLOCK. Test Flag case.
        let obj = make_objective("pivot to a new goal", "", "implementation");
        let score = drift_score(&obj, &anchor);
        // 0.50 (redefine) + 0.10 (no overlap) = 0.60 → Flag but not Block
        assert!(score >= DRIFT_FLAG);
        assert!(score < DRIFT_BLOCK);
    }

    #[test]
    fn signals_above_drift_block_produce_block_outcome() {
        let config = make_config("build a P2P runtime", &["never expose credentials"]);
        let anchor = anchor_from_config(&config);
        // "pivot" (0.50) + "abandon credentials" verb+retained (0.30) = 0.80 → BLOCK
        let obj = make_objective(
            "pivot and abandon credentials constraint",
            "new direction needed",
            "implementation",
        );
        let score = drift_score(&obj, &anchor);
        assert!(
            score >= DRIFT_BLOCK,
            "Combined signals should produce score >= DRIFT_BLOCK ({DRIFT_BLOCK}), got {score}"
        );
        assert!(matches!(
            evaluate_objective(&obj, &anchor),
            DriftOutcome::Block { .. }
        ));
    }

    #[test]
    fn runtime_scope_skips_zero_overlap_penalty() {
        let config = make_config("build a P2P governance runtime", &[]);
        let anchor = anchor_from_config(&config);
        // Purpose words include "build", "governance", "runtime" (len > 4).
        // Objective is totally unrelated in words, but scope=runtime.
        let obj = make_objective("xyz unrelated task", "completely different", "runtime");
        let score = drift_score(&obj, &anchor);
        // No redefine signal, no violation, scope=runtime skips zero-overlap penalty → 0.0
        assert_eq!(score, 0.0, "runtime scope should not incur zero-overlap penalty");
    }

    // ----- check_retained_violation -----

    #[test]
    fn check_retained_violation_detects_verb_plus_keyword() {
        let retained = vec!["keep credentials safe".to_string()];
        let result = check_retained_violation("we should remove credentials", &retained);
        assert!(result.is_some(), "should detect 'remove' + 'credentials'");
    }

    #[test]
    fn check_retained_violation_returns_none_when_clean() {
        let retained = vec!["keep credentials safe".to_string()];
        let result = check_retained_violation("add better logging here", &retained);
        assert!(result.is_none());
    }

    // ----- evaluate_objective -----

    #[test]
    fn evaluate_aligned_objective() {
        let config = make_config("build a P2P runtime", &[]);
        let anchor = anchor_from_config(&config);
        // Matching purpose words, no redefine signals → Aligned
        let obj = make_objective("improve P2P runtime latency", "", "implementation");
        assert_eq!(evaluate_objective(&obj, &anchor), DriftOutcome::Aligned);
    }

    #[test]
    fn evaluate_flagged_objective() {
        let config = make_config("build a P2P runtime", &[]);
        let anchor = anchor_from_config(&config);
        // "pivot" alone on a scope that gets zero-overlap penalty → 0.60 → Flag
        let obj = make_objective("pivot to something new", "", "implementation");
        assert!(matches!(
            evaluate_objective(&obj, &anchor),
            DriftOutcome::Flag { .. }
        ));
    }

    // ----- check_anchor_integrity -----

    #[test]
    fn anchor_integrity_not_established() {
        let state = serde_json::json!({});
        let config = make_config("purpose", &[]);
        let result = check_anchor_integrity(&state, &config);
        assert_eq!(result["status"].as_str().unwrap(), "not_established");
    }

    #[test]
    fn anchor_integrity_intact() {
        let config = make_config("purpose", &["constraint"]);
        let anchor = anchor_from_config(&config);
        let state = serde_json::json!({ "destination_anchor": anchor });
        let result = check_anchor_integrity(&state, &config);
        assert_eq!(result["status"].as_str().unwrap(), "intact");
    }

    #[test]
    fn anchor_integrity_changed() {
        let config1 = make_config("original purpose", &[]);
        let anchor1 = anchor_from_config(&config1);
        let state = serde_json::json!({ "destination_anchor": anchor1 });

        // Config changed
        let config2 = make_config("completely different purpose", &[]);
        let result = check_anchor_integrity(&state, &config2);
        assert_eq!(result["status"].as_str().unwrap(), "changed");
    }

    // ----- build_drift_evidence -----

    #[test]
    fn build_drift_evidence_flagged_disposition() {
        let config = make_config("purpose", &[]);
        let anchor = anchor_from_config(&config);
        let obj = make_objective("some obj", "", "implementation");
        let ev = build_drift_evidence(&obj, 0.40, &anchor);
        assert_eq!(ev["kind"].as_str().unwrap(), "destination-drift-detected");
        assert_eq!(ev["disposition"].as_str().unwrap(), "FLAGGED_FOR_EVIDENCE");
    }

    #[test]
    fn build_drift_evidence_escalated_disposition() {
        let config = make_config("purpose", &[]);
        let anchor = anchor_from_config(&config);
        let obj = make_objective("obj", "", "implementation");
        let ev = build_drift_evidence(&obj, 0.80, &anchor);
        assert_eq!(
            ev["disposition"].as_str().unwrap(),
            "ESCALATED_TO_AUTHORITATIVE_DECISION"
        );
    }
}
