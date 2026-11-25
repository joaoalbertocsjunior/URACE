//! Source/claim coverage is explicit; text coverage never proves semantic understanding.
//!
//! Rust port of `intent_trace.py`. Ports both public functions faithfully:
//! - `source_coverage` — byte-level coverage of text by cited source sections.
//! - `assessment` — requirement-to-claim evidence linkage trace.
//!
//! Additionally exposes two convenience helpers that return f64 ratios for
//! programmatic use:
//! - `source_covered_ratio` — fraction of non-whitespace tokens covered by sources.
//! - `claim_coverage` — fraction of claims that have VERIFIED evidence.

use serde_json::Value;
use sha2::{Digest, Sha256};

/// Compute byte-level source coverage of `text` by the given `sections`.
///
/// Each section is a JSON object with a `"raw_text"` field. Covered bytes are
/// marked; uncovered non-whitespace tokens are reported as `"unassigned"`.
///
/// Returns a JSON object with schema `"intent-source-coverage-v1"`:
/// ```json
/// {
///   "schema": "intent-source-coverage-v1",
///   "source_sha256": "<hex>",
///   "status": "SOURCE_COVERED" | "UNASSIGNED_SOURCE",
///   "unassigned": [ {"start": N, "end": N, "text": "..."}, ... ],
///   "semantic_completeness_proven": false,
///   "meaning": "..."
/// }
/// ```
pub fn source_coverage(text: &str, sections: &[Value]) -> Value {
    let text_bytes = text.as_bytes();
    let mut covered = vec![false; text_bytes.len()];

    for section in sections {
        let part = match section.get("raw_text").and_then(|v| v.as_str()) {
            Some(s) if !s.is_empty() => s,
            _ => continue,
        };
        let part_bytes = part.as_bytes();
        let part_len = part_bytes.len();
        if part_len == 0 {
            continue;
        }
        // Find all (possibly overlapping) occurrences and mark them covered.
        let mut start = 0usize;
        while start + part_len <= text_bytes.len() {
            if &text_bytes[start..start + part_len] == part_bytes {
                for item in covered.iter_mut().skip(start).take(part_len) {
                    *item = true;
                }
                start += part_len;
            } else {
                start += 1;
            }
        }
    }

    // Collect uncovered non-whitespace tokens.
    // A token is uncovered if any of its bytes are both alphanumeric in `text`
    // and not covered. Skip common filler words.
    let stop_words: std::collections::HashSet<&str> =
        ["and", "or", "also", "please", "then", "e", "ou"]
            .iter()
            .copied()
            .collect();

    let mut unassigned: Vec<Value> = Vec::new();

    // Iterate over whitespace-delimited tokens using byte offsets.
    let mut i = 0usize;
    while i < text.len() {
        // Skip whitespace.
        let ch = &text[i..].chars().next();
        match ch {
            Some(c) if c.is_whitespace() => {
                i += c.len_utf8();
                continue;
            }
            None => break,
            _ => {}
        }

        // Find token end.
        let token_start = i;
        let mut j = i;
        while j < text.len() {
            let c = text[j..].chars().next().unwrap();
            if c.is_whitespace() {
                break;
            }
            j += c.len_utf8();
        }
        let token_end = j;
        let token = &text[token_start..token_end];

        // Normalise word: strip punctuation, lowercase.
        let word: String = token
            .chars()
            .filter(|c| {
                !matches!(
                    c,
                    '.' | ',' | ';' | ':' | '!' | '?' | '(' | ')' | '[' | ']' | '{' | '}'
                )
            })
            .collect::<String>()
            .to_lowercase();

        // Check whether any byte in the token range is both alphanumeric
        // in the original text and not covered.
        let has_uncovered_alnum = (token_start..token_end).any(|bi| {
            bi < covered.len() && !covered[bi] && (text_bytes[bi] as char).is_alphanumeric()
        });

        if has_uncovered_alnum && !stop_words.contains(word.as_str()) && !word.is_empty() {
            unassigned.push(serde_json::json!({
                "start": token_start,
                "end": token_end,
                "text": token,
            }));
        }

        i = token_end;
    }

    let source_sha256 = {
        let mut hasher = Sha256::new();
        hasher.update(text.as_bytes());
        hex::encode(hasher.finalize())
    };

    let status = if unassigned.is_empty() {
        "SOURCE_COVERED"
    } else {
        "UNASSIGNED_SOURCE"
    };

    serde_json::json!({
        "schema": "intent-source-coverage-v1",
        "source_sha256": source_sha256,
        "status": status,
        "unassigned": unassigned,
        "semantic_completeness_proven": false,
        "meaning": "Every source section must be accounted for; interpretation and outcome still require validation",
    })
}

/// Return the fraction of non-whitespace tokens in `text` that are covered by
/// the given source sections (0.0 – 1.0). Convenience helper over `source_coverage`.
pub fn source_covered_ratio(text: &str, sections: &[Value]) -> f64 {
    if text.is_empty() {
        return 1.0;
    }
    let result = source_coverage(text, sections);
    let unassigned_count = result
        .get("unassigned")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    // Count total non-whitespace tokens.
    let total_tokens = text.split_whitespace().count();
    if total_tokens == 0 {
        return 1.0;
    }
    let covered = total_tokens.saturating_sub(unassigned_count);
    covered as f64 / total_tokens as f64
}

/// Return the fraction of `claims` that have at least one item in `evidence` (0.0 – 1.0).
///
/// A claim is "covered" if any entry in `evidence` is a non-empty string that
/// is a substring of the claim or equals it (case-insensitive).
pub fn claim_coverage(claims: &[&str], evidence: &[&str]) -> f64 {
    if claims.is_empty() {
        return 1.0;
    }
    let covered = claims
        .iter()
        .filter(|claim| {
            let claim_lower = claim.to_lowercase();
            evidence.iter().any(|ev| {
                let ev_lower = ev.to_lowercase();
                !ev_lower.is_empty()
                    && (claim_lower.contains(&ev_lower) || ev_lower.contains(&claim_lower))
            })
        })
        .count();
    covered as f64 / claims.len() as f64
}

/// Requirement-to-claim evidence linkage trace.
///
/// Each `requirement` is a JSON object with at minimum an `"id"` field.
/// Each `claim` is a JSON object with optional `"requirement_ids"`,
/// `"status"` (`"VERIFIED"`), and `"evidence_refs"` fields.
///
/// Returns a JSON object with schema `"request-claim-evidence-trace-v1"`.
pub fn assessment(requirements: &[Value], claims: &[Value]) -> Value {
    // Build requirement index by id.
    let by_id: std::collections::HashMap<String, &Value> = requirements
        .iter()
        .filter_map(|r| {
            r.get("id")
                .and_then(|v| v.as_str())
                .map(|id| (id.to_string(), r))
        })
        .collect();

    let mut mapped: std::collections::HashMap<String, Vec<&Value>> =
        by_id.keys().map(|k| (k.clone(), Vec::new())).collect();

    let mut unsupported: Vec<Value> = Vec::new();

    for claim in claims {
        let targets: Vec<String> = claim
            .get("requirement_ids")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default();

        if targets.is_empty() || targets.iter().any(|k| !by_id.contains_key(k)) {
            let mut unsup = claim.clone();
            if let Value::Object(ref mut m) = unsup {
                m.insert(
                    "reason".to_string(),
                    Value::String("Unknown or absent request linkage".to_string()),
                );
            }
            unsupported.push(unsup);
            continue;
        }

        for key in &targets {
            if let Some(list) = mapped.get_mut(key) {
                list.push(claim);
            }
        }
    }

    let rows: Vec<Value> = by_id
        .iter()
        .map(|(key, requirement)| {
            let linked: Vec<&Value> = mapped.get(key).cloned().unwrap_or_default();
            let verified: Vec<&&Value> = linked
                .iter()
                .filter(|c| {
                    c.get("status").and_then(|v| v.as_str()) == Some("VERIFIED")
                        && c.get("evidence_refs")
                            .and_then(|v| v.as_array())
                            .map(|a| !a.is_empty())
                            .unwrap_or(false)
                })
                .collect();
            let pending: Vec<&&Value> = linked
                .iter()
                .filter(|c| !verified.contains(c))
                .collect();

            let fully_linked = !verified.is_empty() && pending.is_empty();
            let status = if fully_linked {
                "LINKED_EVIDENCE_REQUIRES_AUTHENTICATION"
            } else {
                "UNVERIFIED_OR_INCOMPLETE"
            };
            let unproven_reason = if fully_linked {
                Value::Null
            } else {
                Value::String(
                    "Missing implementation/evidence, unresolved claims, or incomplete validation scope"
                        .to_string(),
                )
            };
            let next_action = requirement
                .get("validation_plan")
                .cloned()
                .unwrap_or_else(|| {
                    Value::String(
                        "Provide independent source-bound acceptance evidence and state its limits"
                            .to_string(),
                    )
                });
            let resume_when = requirement
                .get("resume_when")
                .cloned()
                .unwrap_or_else(|| {
                    Value::String(
                        "New evidence, clarified requirement or changed implementation".to_string(),
                    )
                });

            serde_json::json!({
                "id": key,
                "request": requirement,
                "claims": linked,
                "status": status,
                "unproven_reason": unproven_reason,
                "next_action": next_action,
                "resume_when": resume_when,
                "native_model_calls": 0,
            })
        })
        .collect();

    let linkage_complete = !rows.is_empty()
        && rows.iter().all(|r| {
            r.get("status").and_then(|v| v.as_str())
                == Some("LINKED_EVIDENCE_REQUIRES_AUTHENTICATION")
        })
        && unsupported.is_empty();

    serde_json::json!({
        "schema": "request-claim-evidence-trace-v1",
        "requirements": rows,
        "unsupported_claims": unsupported,
        "linkage_complete": linkage_complete,
        "complete_assessment_proven": false,
        "evidence_truth_independently_verified": false,
        "meaning": "This is linkage/coverage validation; cited evidence must itself be authenticated and relevant. No universal success or comprehension claim.",
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // ----- source_coverage -----

    #[test]
    fn fully_covered_text() {
        let text = "hello world";
        let sections = vec![serde_json::json!({ "raw_text": "hello world" })];
        let result = source_coverage(text, &sections);
        assert_eq!(result["status"].as_str().unwrap(), "SOURCE_COVERED");
        assert!(result["unassigned"].as_array().unwrap().is_empty());
    }

    #[test]
    fn partially_covered_text() {
        let text = "hello world goodbye";
        let sections = vec![serde_json::json!({ "raw_text": "hello" })];
        let result = source_coverage(text, &sections);
        assert_eq!(result["status"].as_str().unwrap(), "UNASSIGNED_SOURCE");
        let unassigned = result["unassigned"].as_array().unwrap();
        // "world" and "goodbye" should be unassigned
        assert!(!unassigned.is_empty());
        let texts: Vec<&str> = unassigned
            .iter()
            .map(|u| u["text"].as_str().unwrap())
            .collect();
        assert!(texts.contains(&"world"));
        assert!(texts.contains(&"goodbye"));
    }

    #[test]
    fn empty_sections_marks_all_tokens_unassigned() {
        let text = "some important content";
        let result = source_coverage(text, &[]);
        assert_eq!(result["status"].as_str().unwrap(), "UNASSIGNED_SOURCE");
    }

    #[test]
    fn stop_words_not_reported_as_unassigned() {
        // "and", "or", "also" are stop words and should not appear in unassigned
        let text = "this and that or also here";
        let sections = vec![
            serde_json::json!({ "raw_text": "this" }),
            serde_json::json!({ "raw_text": "that" }),
            serde_json::json!({ "raw_text": "here" }),
        ];
        let result = source_coverage(text, &sections);
        let unassigned = result["unassigned"].as_array().unwrap();
        let texts: Vec<&str> = unassigned
            .iter()
            .map(|u| u["text"].as_str().unwrap())
            .collect();
        assert!(
            !texts.contains(&"and"),
            "stop word 'and' should not be unassigned"
        );
        assert!(
            !texts.contains(&"or"),
            "stop word 'or' should not be unassigned"
        );
        assert!(
            !texts.contains(&"also"),
            "stop word 'also' should not be unassigned"
        );
    }

    #[test]
    fn source_coverage_has_correct_schema_fields() {
        let result = source_coverage("test", &[]);
        assert_eq!(
            result["schema"].as_str().unwrap(),
            "intent-source-coverage-v1"
        );
        assert!(result.get("source_sha256").is_some());
        assert!(!result["semantic_completeness_proven"].as_bool().unwrap());
        // SHA-256 is 64 hex chars
        assert_eq!(result["source_sha256"].as_str().unwrap().len(), 64);
    }

    #[test]
    fn source_sha256_is_stable() {
        let text = "hello world";
        let r1 = source_coverage(text, &[]);
        let r2 = source_coverage(text, &[]);
        assert_eq!(r1["source_sha256"], r2["source_sha256"]);
    }

    #[test]
    fn section_without_raw_text_is_skipped() {
        let text = "hello world";
        // section with no raw_text field — should not panic, just skip
        let sections = vec![serde_json::json!({ "other_field": "hello world" })];
        let result = source_coverage(text, &sections);
        // "hello" and "world" remain uncovered
        assert_eq!(result["status"].as_str().unwrap(), "UNASSIGNED_SOURCE");
    }

    // ----- source_covered_ratio -----

    #[test]
    fn ratio_fully_covered() {
        let text = "hello world";
        let sections = vec![serde_json::json!({ "raw_text": "hello world" })];
        assert_eq!(source_covered_ratio(text, &sections), 1.0);
    }

    #[test]
    fn ratio_empty_text() {
        assert_eq!(source_covered_ratio("", &[]), 1.0);
    }

    // ----- claim_coverage -----

    #[test]
    fn claim_coverage_all_covered() {
        let claims = &["feature A is implemented", "test B passes"];
        let evidence = &["feature A", "test B"];
        let ratio = claim_coverage(claims, evidence);
        assert_eq!(ratio, 1.0);
    }

    #[test]
    fn claim_coverage_none_covered() {
        let claims = &["feature A", "feature B"];
        let evidence = &["feature C"];
        let ratio = claim_coverage(claims, evidence);
        assert_eq!(ratio, 0.0);
    }

    #[test]
    fn claim_coverage_partial() {
        let claims = &["feature A is done", "feature B is done"];
        let evidence = &["feature A"];
        let ratio = claim_coverage(claims, evidence);
        assert_eq!(ratio, 0.5);
    }

    #[test]
    fn claim_coverage_empty_claims_returns_one() {
        assert_eq!(claim_coverage(&[], &["something"]), 1.0);
    }

    // ----- assessment -----

    fn req(id: &str) -> Value {
        serde_json::json!({ "id": id })
    }

    fn verified_claim(req_ids: &[&str]) -> Value {
        serde_json::json!({
            "requirement_ids": req_ids,
            "status": "VERIFIED",
            "evidence_refs": ["ref-1"],
        })
    }

    fn unverified_claim(req_ids: &[&str]) -> Value {
        serde_json::json!({
            "requirement_ids": req_ids,
            "status": "PENDING",
        })
    }

    #[test]
    fn assessment_has_correct_schema() {
        let result = assessment(&[], &[]);
        assert_eq!(
            result["schema"].as_str().unwrap(),
            "request-claim-evidence-trace-v1"
        );
        assert!(!result["complete_assessment_proven"].as_bool().unwrap());
        assert!(
            !result["evidence_truth_independently_verified"]
                .as_bool()
                .unwrap()
        );
    }

    #[test]
    fn assessment_linkage_complete_when_all_verified() {
        let requirements = vec![req("R1"), req("R2")];
        let claims = vec![verified_claim(&["R1"]), verified_claim(&["R2"])];
        let result = assessment(&requirements, &claims);
        assert!(
            result["linkage_complete"].as_bool().unwrap(),
            "All requirements have verified claims → linkage_complete should be true"
        );
    }

    #[test]
    fn assessment_incomplete_when_unverified_claim() {
        let requirements = vec![req("R1")];
        let claims = vec![unverified_claim(&["R1"])];
        let result = assessment(&requirements, &claims);
        assert!(!result["linkage_complete"].as_bool().unwrap());
    }

    #[test]
    fn assessment_unsupported_claim_for_unknown_requirement() {
        let requirements = vec![req("R1")];
        let claims = vec![
            verified_claim(&["R1"]),
            serde_json::json!({
                "requirement_ids": ["R999"],  // unknown
                "status": "VERIFIED",
                "evidence_refs": ["ref"],
            }),
        ];
        let result = assessment(&requirements, &claims);
        let unsupported = result["unsupported_claims"].as_array().unwrap();
        assert_eq!(unsupported.len(), 1);
        assert_eq!(
            unsupported[0]["reason"].as_str().unwrap(),
            "Unknown or absent request linkage"
        );
    }

    #[test]
    fn assessment_claim_with_no_requirement_ids_is_unsupported() {
        let requirements = vec![req("R1")];
        let claims = vec![serde_json::json!({
            "status": "VERIFIED",
            "evidence_refs": ["ref"],
        })];
        let result = assessment(&requirements, &claims);
        let unsupported = result["unsupported_claims"].as_array().unwrap();
        assert_eq!(unsupported.len(), 1);
    }

    #[test]
    fn assessment_empty_requirements_and_claims() {
        let result = assessment(&[], &[]);
        assert_eq!(result["requirements"].as_array().unwrap().len(), 0);
        assert!(!result["linkage_complete"].as_bool().unwrap());
    }
}
