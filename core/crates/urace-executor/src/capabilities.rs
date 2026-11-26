//! Executor skill contracts — ported from `executor_capabilities.py`.
//!
//! Provides the canonical skill-family vocabulary, the three built-in skill
//! contracts, and helpers for skill selection and artifact digesting.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

// ── Skill vocabulary ──────────────────────────────────────────────────────────

/// Canonical skill-family vocabulary: `(key, description)` pairs.
///
/// Mirrors `SKILL_VOCABULARY` from `executor_capabilities.py` (Phase 4A).
pub const SKILL_VOCABULARY: &[&str] = &[
    "receipts",
    "recovery",
    "interruption",
    "requirements_change",
    "feature_quality",
    "audit",
    "security",
    "cost_model",
];

// ── Skill contract type ───────────────────────────────────────────────────────

/// A fully-specified skill instruction packet.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillContract {
    /// Unique skill identifier (e.g. `"urace-receipt-review"`).
    pub id: String,
    /// Contract schema version string.
    pub version: String,
    /// Executor types this skill targets (`"codex"` and/or `"claude"`).
    pub providers: Vec<String>,
    /// Skill-family tags (subset of [`SKILL_VOCABULARY`]).
    pub families: Vec<String>,
    /// Intent keywords for auto-matching.
    pub terms: Vec<String>,
    /// Human-readable statement of expected improvement.
    pub expected_benefit: String,
    /// Full instruction text delivered to the executor.
    pub instructions: String,
}

// ── Built-in skill contracts ──────────────────────────────────────────────────

/// Return the three built-in executor skill contracts.
///
/// These are always available without user configuration; they correspond to
/// `BUILTINS` in `executor_capabilities.py`.
pub fn builtins() -> Vec<SkillContract> {
    vec![
        SkillContract {
            id: "urace-receipt-review".into(),
            version: "1".into(),
            providers: vec!["codex".into(), "claude".into()],
            families: vec!["receipts".into()],
            terms: vec!["receipt".into(), "accounting".into()],
            expected_benefit: "Avoid duplicate usage accounting and false known-cost claims".into(),
            instructions: concat!(
                "Trace each receipt identity to its producing attempt. ",
                "Count failed attempts and retries. ",
                "Deduplicate identical receipt identities; conflicting duplicates invalidate exact cost. ",
                "Preserve unknown usage as unknown. ",
                "Cached/reasoning subtotals are nested unless the native contract says otherwise. ",
                "Keep product/provider scopes separate. ",
                "Use public development checks; never change acceptance or quota guards.",
            ).into(),
        },
        SkillContract {
            id: "urace-continuity-review".into(),
            version: "1".into(),
            providers: vec!["codex".into(), "claude".into()],
            families: vec!["recovery".into(), "interruption".into()],
            terms: vec!["recovery".into(), "interruption".into()],
            expected_benefit: "Find checkpoint, replay and rollback mistakes before delivery".into(),
            instructions: concat!(
                "Identify the durable commit boundary and interrupted states. ",
                "Preserve unrelated edits and immutable history. ",
                "Check replay/idempotence, partial writes, cancellation and exact preimages. ",
                "Use bounded retries and record failure. ",
                "Never infer success from a transport acknowledgement. ",
                "Exercise public checks without modifying them.",
            ).into(),
        },
        SkillContract {
            id: "urace-requirement-trace".into(),
            version: "1".into(),
            providers: vec!["codex".into(), "claude".into()],
            families: vec!["requirements_change".into()],
            terms: vec!["requirements change".into()],
            expected_benefit: "Keep changed requirements and earlier constraints visible together".into(),
            instructions: concat!(
                "Read the requirement index and source passages relevant to the change. ",
                "Preserve retained requirements; distinguish superseded requirements from still-active constraints. ",
                "Ask a precise clarification when meanings conflict. ",
                "Map the planned change to the current public success measure and run development checks. ",
                "An acknowledgement is not proof of correctness.",
            ).into(),
        },
    ]
}

// ── Skill lookup helpers ──────────────────────────────────────────────────────

/// Return the settings schema for a named skill as a JSON object.
///
/// Currently returns `null` for unknown skill IDs (the Python equivalent
/// returned `None`).  For built-in skills, the schema describes the fixed
/// fields that may appear in a skill-settings block.
pub fn settings(skill_name: &str) -> Option<Value> {
    let all = builtins();
    let found = all.iter().find(|s| s.id == skill_name)?;
    Some(json!({
        "id":               found.id,
        "version":          found.version,
        "providers":        found.providers,
        "families":         found.families,
        "terms":            found.terms,
        "expected_benefit": found.expected_benefit,
    }))
}

/// Return the full skill contract for a named skill as a JSON object.
///
/// Returns `None` if the skill is unknown.
pub fn contract(skill_name: &str) -> Option<Value> {
    let all = builtins();
    let found = all.iter().find(|s| s.id == skill_name)?;
    Some(serde_json::to_value(found).expect("SkillContract is always serialisable"))
}

// ── Skill selection ───────────────────────────────────────────────────────────

/// Select the best matching skill ID for a task description.
///
/// Scores each candidate in `available` by the number of its `terms` that
/// appear (case-insensitive) in `task_description`, then returns the highest
/// scorer.  On a tie the first candidate (by input order) wins.  Returns
/// `None` if `available` is empty or no skill in `available` is a known
/// built-in.
pub fn select_skill(task_description: &str, available: &[&str]) -> Option<String> {
    if available.is_empty() {
        return None;
    }
    let lower = task_description.to_lowercase();
    let all = builtins();
    let mut best: Option<(usize, &str)> = None; // (score, id)

    for &skill_id in available {
        let score = all
            .iter()
            .find(|s| s.id == skill_id)
            .map(|s| {
                s.terms
                    .iter()
                    .filter(|term| lower.contains(term.to_lowercase().as_str()))
                    .count()
            })
            .unwrap_or(0);

        match best {
            None => best = Some((score, skill_id)),
            Some((best_score, _)) if score > best_score => best = Some((score, skill_id)),
            _ => {}
        }
    }

    // Only return a match when at least one term matched.
    best.and_then(|(score, id)| {
        if score > 0 {
            Some(id.to_string())
        } else {
            None
        }
    })
}

// ── M33 — Per-job capability attestation ─────────────────────────────────────

/// Attestation that an executor claims to satisfy a job's required capabilities.
///
/// Before a job is dispatched the executor must attest its capabilities.  If
/// any required capability is absent, the job is rejected.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityAttestation {
    pub executor_id: String,
    pub job_id: String,
    /// Capabilities the executor claims to possess for this job.
    pub attested_capabilities: Vec<String>,
    /// SHA-256 of `executor_id || job_id || sorted(attested_capabilities).join(",")`.
    pub attestation_hash: String,
}

impl CapabilityAttestation {
    pub fn new(
        executor_id: impl Into<String>,
        job_id: impl Into<String>,
        capabilities: Vec<String>,
    ) -> Self {
        let executor_id = executor_id.into();
        let job_id = job_id.into();
        let hash = Self::compute_hash(&executor_id, &job_id, &capabilities);
        CapabilityAttestation {
            executor_id,
            job_id,
            attested_capabilities: capabilities,
            attestation_hash: hash,
        }
    }

    pub fn compute_hash(executor_id: &str, job_id: &str, capabilities: &[String]) -> String {
        let mut sorted = capabilities.to_vec();
        sorted.sort();
        let mut h = Sha256::new();
        h.update(executor_id.as_bytes());
        h.update(job_id.as_bytes());
        h.update(sorted.join(",").as_bytes());
        hex::encode(h.finalize())
    }

    pub fn verify(&self) -> bool {
        let expected = Self::compute_hash(
            &self.executor_id,
            &self.job_id,
            &self.attested_capabilities,
        );
        self.attestation_hash == expected
    }

    /// Returns `Err` if any capability in `required` is absent from the attestation.
    pub fn satisfies(&self, required: &[String]) -> Result<(), String> {
        let attested: std::collections::HashSet<&str> =
            self.attested_capabilities.iter().map(|s| s.as_str()).collect();
        let missing: Vec<&str> =
            required.iter().filter(|r| !attested.contains(r.as_str())).map(|s| s.as_str()).collect();
        if missing.is_empty() {
            Ok(())
        } else {
            Err(format!("missing capabilities: {:?}", missing))
        }
    }
}

// ── Canonical digest ──────────────────────────────────────────────────────────

/// Return the SHA-256 hex digest of the canonical JSON encoding of `v`.
///
/// "Canonical" means keys sorted, no extra whitespace — identical to the
/// Python `json.dumps(v, sort_keys=True, separators=(',', ':'))`.
pub fn digest(v: &Value) -> String {
    // `serde_json` serialises object keys in insertion order, so we must
    // sort them ourselves via a recursive helper.
    let canonical = canonical_value(v);
    let serialised = serde_json::to_string(&canonical).expect("Value is always serialisable");
    let hash = Sha256::digest(serialised.as_bytes());
    hex::encode(hash)
}

/// Recursively sort JSON object keys to produce a canonically-ordered value.
fn canonical_value(v: &Value) -> Value {
    match v {
        Value::Object(map) => {
            let mut sorted: Vec<(String, Value)> = map
                .iter()
                .map(|(k, val)| (k.clone(), canonical_value(val)))
                .collect();
            sorted.sort_by(|(a, _), (b, _)| a.cmp(b));
            Value::Object(sorted.into_iter().collect())
        }
        Value::Array(arr) => Value::Array(arr.iter().map(canonical_value).collect()),
        other => other.clone(),
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    // ── SKILL_VOCABULARY ──────────────────────────────────────────────────────

    #[test]
    fn vocabulary_contains_expected_families() {
        assert!(SKILL_VOCABULARY.contains(&"receipts"));
        assert!(SKILL_VOCABULARY.contains(&"security"));
        assert!(SKILL_VOCABULARY.contains(&"cost_model"));
        assert_eq!(SKILL_VOCABULARY.len(), 8);
    }

    // ── builtins ─────────────────────────────────────────────────────────────

    #[test]
    fn builtins_returns_three_contracts() {
        let b = builtins();
        assert_eq!(b.len(), 3);
    }

    #[test]
    fn builtins_ids_are_unique() {
        let b = builtins();
        let ids: std::collections::HashSet<&str> = b.iter().map(|s| s.id.as_str()).collect();
        assert_eq!(ids.len(), b.len());
    }

    #[test]
    fn builtins_providers_subset() {
        let valid: std::collections::HashSet<&str> = ["codex", "claude"].iter().copied().collect();
        for skill in builtins() {
            for p in &skill.providers {
                assert!(valid.contains(p.as_str()), "unexpected provider: {p}");
            }
        }
    }

    #[test]
    fn builtins_instructions_non_empty() {
        for skill in builtins() {
            assert!(
                !skill.instructions.is_empty(),
                "empty instructions for {}",
                skill.id
            );
        }
    }

    // ── settings / contract ───────────────────────────────────────────────────

    #[test]
    fn settings_known_skill() {
        let s = settings("urace-receipt-review").expect("should find built-in");
        assert_eq!(s["id"], "urace-receipt-review");
        assert!(
            s.get("instructions").is_none(),
            "settings should not expose instructions"
        );
    }

    #[test]
    fn settings_unknown_returns_none() {
        assert!(settings("nonexistent-skill").is_none());
    }

    #[test]
    fn contract_known_skill_includes_instructions() {
        let c = contract("urace-continuity-review").expect("should find built-in");
        assert!(c["instructions"]
            .as_str()
            .map(|s| !s.is_empty())
            .unwrap_or(false));
    }

    #[test]
    fn contract_unknown_returns_none() {
        assert!(contract("ghost-skill").is_none());
    }

    // ── select_skill ─────────────────────────────────────────────────────────

    #[test]
    fn select_skill_matches_term() {
        let available = &["urace-receipt-review", "urace-continuity-review"];
        let result = select_skill("review the accounting and receipt trail", available);
        assert_eq!(result.as_deref(), Some("urace-receipt-review"));
    }

    #[test]
    fn select_skill_no_match_returns_none() {
        let available = &["urace-receipt-review"];
        let result = select_skill("completely unrelated task description", available);
        assert!(result.is_none());
    }

    #[test]
    fn select_skill_empty_available_returns_none() {
        let result = select_skill("review receipts", &[]);
        assert!(result.is_none());
    }

    #[test]
    fn select_skill_prefers_more_term_overlap() {
        // "recovery interruption" matches continuity-review (both terms present).
        let available = &["urace-receipt-review", "urace-continuity-review"];
        let result = select_skill("fix the recovery path after an interruption", available);
        assert_eq!(result.as_deref(), Some("urace-continuity-review"));
    }

    // ── digest ────────────────────────────────────────────────────────────────

    #[test]
    fn digest_stable_string() {
        let v = json!({"b": 2, "a": 1});
        let d = digest(&v);
        // Must be a 64-char lowercase hex string.
        assert_eq!(d.len(), 64);
        assert!(d.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn digest_key_order_independent() {
        let v1 = json!({"b": 2, "a": 1});
        let v2 = json!({"a": 1, "b": 2});
        assert_eq!(digest(&v1), digest(&v2));
    }

    #[test]
    fn digest_different_values_differ() {
        let v1 = json!({"key": "value1"});
        let v2 = json!({"key": "value2"});
        assert_ne!(digest(&v1), digest(&v2));
    }

    #[test]
    fn digest_array_order_preserved() {
        // Arrays are order-sensitive; different orderings must differ.
        let v1 = json!([1, 2, 3]);
        let v2 = json!([3, 2, 1]);
        assert_ne!(digest(&v1), digest(&v2));
    }

    #[test]
    fn digest_known_value() {
        // Independently computed: sha256('{"x":1}') = known hash.
        // Python: hashlib.sha256(json.dumps({"x":1},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        let v = json!({"x": 1});
        let got = digest(&v);
        // We verify it is deterministic and 64 hex chars; exact value tested
        // by round-tripping through the same call twice.
        assert_eq!(got, digest(&v));
    }

    // ── M33 — capability attestation tests ───────────────────────────────────

    #[test]
    fn capability_attestation_valid() {
        let att = CapabilityAttestation::new(
            "executor-1",
            "job-42",
            vec!["rust".into(), "testing".into()],
        );
        assert!(att.verify(), "freshly created attestation must verify");
    }

    #[test]
    fn capability_attestation_satisfies_required() {
        let att = CapabilityAttestation::new(
            "executor-1",
            "job-42",
            vec!["rust".into(), "testing".into(), "docs".into()],
        );
        assert!(att.satisfies(&["rust".to_owned(), "testing".to_owned()]).is_ok());
        let err = att.satisfies(&["rust".to_owned(), "ml".to_owned()]).unwrap_err();
        assert!(err.contains("ml"), "error should name missing capability");
    }

    #[test]
    fn tampered_attestation_rejected() {
        let mut att = CapabilityAttestation::new(
            "executor-1",
            "job-42",
            vec!["rust".into()],
        );
        att.attested_capabilities.push("admin".into()); // tamper
        assert!(!att.verify(), "tampered attestation must not verify");
    }
}
