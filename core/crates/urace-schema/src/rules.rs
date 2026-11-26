//! Rule ledger — governance model.
//!
//! Rust port of `rules.py`. Implements the Rule enum, immutability levels,
//! a simple `RuleEngine` that evaluates a set of rules against a context,
//! and a `RuleStore` that tracks rule-change relationships, conflict detection,
//! and derivation chains.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ── Rule kinds ────────────────────────────────────────────────────────────────

/// Immutability level of a rule kind.
///
/// | Level | Kinds | Mutability |
/// |-------|-------|------------|
/// | 0 | PURPOSE | Immutable post-bootstrap |
/// | 1 | DIRECTIVE, PERMISSION, PROHIBITION | Operator-mutable |
/// | 2 | OBJECTIVE, POLICY | Lifecycle-managed |
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuleKind {
    Purpose,
    Directive,
    Permission,
    Prohibition,
    Objective,
    Policy,
}

impl RuleKind {
    pub fn level(self) -> u8 {
        match self {
            RuleKind::Purpose => 0,
            RuleKind::Directive | RuleKind::Permission | RuleKind::Prohibition => 1,
            RuleKind::Objective | RuleKind::Policy => 2,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            RuleKind::Purpose => "PURPOSE",
            RuleKind::Directive => "DIRECTIVE",
            RuleKind::Permission => "PERMISSION",
            RuleKind::Prohibition => "PROHIBITION",
            RuleKind::Objective => "OBJECTIVE",
            RuleKind::Policy => "POLICY",
        }
    }
}

// ── Rule ──────────────────────────────────────────────────────────────────────

/// A single governance rule.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rule {
    pub id: String,
    pub kind: RuleKind,
    pub statement: String,
    pub scope: Vec<String>,
    pub confidence: f64,
    pub source: String,
    pub active: bool,
    pub tags: Vec<String>,
    /// ID of the rule this rule was directly derived from (derivation ancestry).
    pub parent_id: Option<String>,
}

impl Rule {
    pub fn new(id: impl Into<String>, kind: RuleKind, statement: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            kind,
            statement: statement.into(),
            scope: vec!["*".into()],
            confidence: 1.0,
            source: String::new(),
            active: true,
            tags: vec![],
            parent_id: None,
        }
    }
}

// ── RuleViolation ─────────────────────────────────────────────────────────────

/// A rule that was violated during evaluation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuleViolation {
    pub rule_id: String,
    pub kind: RuleKind,
    pub statement: String,
    pub detail: String,
}

// ── RuleEngine ────────────────────────────────────────────────────────────────

/// Evaluates a set of rules against an execution context.
///
/// The context is a flat `HashMap<String, String>` with keys like
/// `"scope"`, `"action"`, `"content_type"` etc.
#[derive(Debug, Default)]
pub struct RuleEngine;

impl RuleEngine {
    pub fn new() -> Self {
        Self
    }

    /// Evaluate `rules` against `context`.
    ///
    /// Returns the list of violated rules (empty = no violations).
    /// Never panics.
    pub fn evaluate(
        &self,
        rules: &[Rule],
        context: &HashMap<String, String>,
    ) -> Vec<RuleViolation> {
        let mut violations = Vec::new();

        for rule in rules {
            if !rule.active {
                continue;
            }

            // Scope filter: "*" matches everything; otherwise must intersect.
            let scope_matches = rule.scope.contains(&"*".to_string())
                || context
                    .get("scope")
                    .map(|s| rule.scope.contains(s))
                    .unwrap_or(false);

            if !scope_matches {
                continue;
            }

            if rule.kind == RuleKind::Prohibition
                && self.statement_matches_context(&rule.statement, context)
            {
                violations.push(RuleViolation {
                    rule_id: rule.id.clone(),
                    kind: rule.kind,
                    statement: rule.statement.clone(),
                    detail: format!("Prohibited action matches rule: {}", rule.id),
                });
                // PURPOSE, DIRECTIVE, PERMISSION, OBJECTIVE, POLICY are advisory
                // at this evaluation layer; they do not block by themselves.
            }
        }

        violations
    }

    /// Heuristic: a statement "matches" the context if any context value
    /// contains a significant keyword from the statement.
    ///
    /// This is intentionally conservative — false negatives are safer than
    /// false positives for a prohibition check.
    fn statement_matches_context(
        &self,
        statement: &str,
        context: &HashMap<String, String>,
    ) -> bool {
        let statement_lower = statement.to_lowercase();
        // Collect long words (>= 4 chars) from the statement as keywords.
        let keywords: Vec<&str> = statement_lower
            .split_whitespace()
            .filter(|w| w.len() >= 4)
            .collect();

        if keywords.is_empty() {
            return false;
        }

        let context_text: String = context
            .values()
            .map(|v| v.to_lowercase())
            .collect::<Vec<_>>()
            .join(" ");

        // Violation if at least 2 keywords match (reduce false positives).
        let matches = keywords
            .iter()
            .filter(|kw| context_text.contains(**kw))
            .count();
        matches >= 2.min(keywords.len())
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn ctx(pairs: &[(&str, &str)]) -> HashMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect()
    }

    #[test]
    fn no_rules_no_violations() {
        let engine = RuleEngine::new();
        let result = engine.evaluate(&[], &ctx(&[("action", "deploy")]));
        assert!(result.is_empty());
    }

    #[test]
    fn inactive_rule_not_evaluated() {
        let engine = RuleEngine::new();
        let mut rule = Rule::new("r1", RuleKind::Prohibition, "spend money on deploy");
        rule.active = false;
        let result = engine.evaluate(&[rule], &ctx(&[("action", "spend money on deploy")]));
        assert!(result.is_empty());
    }

    #[test]
    fn prohibition_matches_context() {
        let engine = RuleEngine::new();
        let rule = Rule::new("r1", RuleKind::Prohibition, "spend money transfer funds");
        let result = engine.evaluate(
            &[rule],
            &ctx(&[("action", "spend money transfer to wallet")]),
        );
        assert!(!result.is_empty());
    }

    #[test]
    fn permission_does_not_produce_violation() {
        let engine = RuleEngine::new();
        let rule = Rule::new("r2", RuleKind::Permission, "allowed to deploy runtime");
        let result = engine.evaluate(&[rule], &ctx(&[("action", "allowed to deploy runtime")]));
        assert!(
            result.is_empty(),
            "permissions should not produce violations"
        );
    }

    #[test]
    fn scope_mismatch_skips_rule() {
        let engine = RuleEngine::new();
        let mut rule = Rule::new("r3", RuleKind::Prohibition, "spend money transfer");
        rule.scope = vec!["runtime".into()];
        // Context scope is "documentation" — rule should not apply.
        let result = engine.evaluate(
            &[rule],
            &ctx(&[
                ("scope", "documentation"),
                ("action", "spend money transfer"),
            ]),
        );
        assert!(result.is_empty());
    }

    #[test]
    fn rule_kind_levels() {
        assert_eq!(RuleKind::Purpose.level(), 0);
        assert_eq!(RuleKind::Directive.level(), 1);
        assert_eq!(RuleKind::Objective.level(), 2);
    }
}

// ── RuleConflict ──────────────────────────────────────────────────────────────

// ── M07: Governance binary floors ────────────────────────────────────────────

/// Hard-coded minimum values for governance-settable parameters.
/// These are code constants — they cannot be changed via governance.
pub struct GovernanceFloor {
    pub parameter: &'static str,
    pub min_value: f64,
    pub description: &'static str,
}

pub static GOVERNANCE_FLOORS: &[GovernanceFloor] = &[
    GovernanceFloor {
        parameter: "quorum_threshold",
        min_value: 0.51,
        description: "Minimum quorum fraction for governance votes",
    },
    GovernanceFloor {
        parameter: "supermajority_threshold",
        min_value: 0.66,
        description: "Minimum supermajority fraction for high-value governance changes",
    },
    GovernanceFloor {
        parameter: "time_lock_secs",
        min_value: 60.0,
        description: "Minimum time-lock delay for high-value operations (seconds)",
    },
    GovernanceFloor {
        parameter: "reputation_decay_rate",
        min_value: 0.001,
        description: "Minimum reputation decay rate per cycle",
    },
    GovernanceFloor {
        parameter: "inbox_rate_limit",
        min_value: 1.0,
        description: "Minimum inbox messages per peer per cycle (must be at least 1)",
    },
];

#[derive(Debug, Clone, PartialEq)]
pub enum FloorCheckResult {
    Valid,
    BelowFloor { parameter: String, proposed: f64, floor: f64 },
    UnknownParameter,
}

/// Check if a proposed governance change respects hard-coded floors.
pub fn check_governance_floor(parameter: &str, proposed_value: f64) -> FloorCheckResult {
    for floor in GOVERNANCE_FLOORS {
        if floor.parameter == parameter {
            if proposed_value < floor.min_value {
                return FloorCheckResult::BelowFloor {
                    parameter: parameter.to_string(),
                    proposed: proposed_value,
                    floor: floor.min_value,
                };
            }
            return FloorCheckResult::Valid;
        }
    }
    FloorCheckResult::UnknownParameter
}

/// Validate a batch of governance changes.
/// Returns Err with the first violation found.
pub fn validate_governance_changes(
    changes: &HashMap<String, f64>,
) -> Result<(), FloorCheckResult> {
    for (param, &value) in changes {
        match check_governance_floor(param, value) {
            FloorCheckResult::Valid | FloorCheckResult::UnknownParameter => {}
            violation => return Err(violation),
        }
    }
    Ok(())
}

// ── M53: Uncontested quorum spec ──────────────────────────────────────────────

/// Conditions for a governance change to qualify as "uncontested" (can proceed with lower quorum).
/// ALL conditions must be met simultaneously.
#[derive(Debug, Clone)]
pub struct UncontestedQuorumSpec {
    pub min_wait_secs: u64,            // Minimum 7 days = 604800 seconds
    pub operation_class: &'static str, // "operational" only (not economic, not identity)
    pub min_reviewer_signoffs: usize,  // >= 3
    pub anti_gaming_clause: bool,      // Must be true to prevent staged weakening
}

impl UncontestedQuorumSpec {
    pub fn default_spec() -> Self {
        UncontestedQuorumSpec {
            min_wait_secs: 7 * 24 * 3600, // 7 days
            operation_class: "operational",
            min_reviewer_signoffs: 3,
            anti_gaming_clause: true,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum UncontestedEligibility {
    Eligible,
    TooSoon { waited_secs: u64, required_secs: u64 },
    WrongClass { got: String },
    InsufficientSignoffs { got: usize, required: usize },
    AntiGamingClauseNotSatisfied,
}

pub fn check_uncontested_eligible(
    waited_secs: u64,
    operation_class: &str,
    reviewer_signoffs: usize,
    anti_gaming_satisfied: bool,
    spec: &UncontestedQuorumSpec,
) -> UncontestedEligibility {
    if waited_secs < spec.min_wait_secs {
        return UncontestedEligibility::TooSoon { waited_secs, required_secs: spec.min_wait_secs };
    }
    if operation_class != spec.operation_class {
        return UncontestedEligibility::WrongClass { got: operation_class.to_string() };
    }
    if reviewer_signoffs < spec.min_reviewer_signoffs {
        return UncontestedEligibility::InsufficientSignoffs { got: reviewer_signoffs, required: spec.min_reviewer_signoffs };
    }
    if spec.anti_gaming_clause && !anti_gaming_satisfied {
        return UncontestedEligibility::AntiGamingClauseNotSatisfied;
    }
    UncontestedEligibility::Eligible
}

// ── RuleConflict ──────────────────────────────────────────────────────────────

/// A detected contradiction between two active rules.
///
/// Returned by [`detect_conflicts`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuleConflict {
    pub rule_a: String,
    pub rule_b: String,
    pub reason: String,
}

// ── RuleStore ─────────────────────────────────────────────────────────────────

/// A mutable store that holds rules and their relationships to changes.
///
/// Provides:
/// - Rule-to-change bindings via [`record_relationship`] / [`rules_for_change`] /
///   [`changes_for_rule`].
/// - Conflict detection via [`detect_conflicts`].
/// - Derivation chain walking via [`derivation_chain`].
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct RuleStore {
    /// All rules held in this store (active and inactive).
    pub rules: Vec<Rule>,
    /// Maps rule_id → list of change_ids that the rule governs.
    pub rule_changes: HashMap<String, Vec<String>>,
}

impl RuleStore {
    /// Create an empty `RuleStore`.
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a rule to the store.  Does nothing if a rule with the same ID already
    /// exists.
    pub fn add_rule(&mut self, rule: Rule) {
        if !self.rules.iter().any(|r| r.id == rule.id) {
            self.rules.push(rule);
        }
    }

    /// Return a reference to a rule by ID, or `None`.
    pub fn get_rule(&self, rule_id: &str) -> Option<&Rule> {
        self.rules.iter().find(|r| r.id == rule_id)
    }
}

// ── Free functions ────────────────────────────────────────────────────────────

/// Bind `rule_id` to `change_id`, recording that the rule governed the change.
///
/// Bindings are deduplicated — calling this multiple times with the same
/// `(rule_id, change_id)` pair has no effect.
///
/// Corresponds to `bind_change` / `governed_changes` bookkeeping in `rules.py`.
pub fn record_relationship(store: &mut RuleStore, rule_id: &str, change_id: &str) {
    let changes = store.rule_changes.entry(rule_id.to_owned()).or_default();
    if !changes.contains(&change_id.to_owned()) {
        changes.push(change_id.to_owned());
    }
}

/// Return the rule IDs that govern `change_id`.
///
/// Iterates every rule in the store and collects those whose change list
/// contains `change_id`.
///
/// Corresponds to `rules_for_change` in `rules.py`.
pub fn rules_for_change(store: &RuleStore, change_id: &str) -> Vec<String> {
    store
        .rule_changes
        .iter()
        .filter_map(|(rule_id, changes)| {
            if changes.iter().any(|c| c == change_id) {
                Some(rule_id.clone())
            } else {
                None
            }
        })
        .collect()
}

/// Return the change IDs governed by `rule_id`.
///
/// Corresponds to `changes_for_rule` in `rules.py`.
pub fn changes_for_rule(store: &RuleStore, rule_id: &str) -> Vec<String> {
    store.rule_changes.get(rule_id).cloned().unwrap_or_default()
}

/// Find rules with contradictory effects: a `Permission` and a `Prohibition`
/// that share at least 3 significant keywords (≥ 4 chars) in their statements,
/// indicating they cover the same subject with opposite actions.
///
/// Corresponds to `detect_conflicts` in `rules.py`.
pub fn detect_conflicts(store: &RuleStore) -> Vec<RuleConflict> {
    let active: Vec<&Rule> = store.rules.iter().filter(|r| r.active).collect();

    let permissions: Vec<&Rule> = active
        .iter()
        .copied()
        .filter(|r| r.kind == RuleKind::Permission)
        .collect();
    let prohibitions: Vec<&Rule> = active
        .iter()
        .copied()
        .filter(|r| r.kind == RuleKind::Prohibition)
        .collect();

    let mut conflicts = Vec::new();

    for perm in &permissions {
        for proh in &prohibitions {
            let perm_words = significant_words(&perm.statement);
            let proh_words = significant_words(&proh.statement);

            // Count overlapping significant keywords.
            let overlap_count = perm_words
                .iter()
                .filter(|w| proh_words.contains(*w))
                .count();

            if overlap_count >= 3 {
                // Build a reason string listing the overlapping terms.
                let mut overlap_terms: Vec<&str> = perm_words
                    .iter()
                    .filter(|w| proh_words.contains(*w))
                    .copied()
                    .collect();
                overlap_terms.sort_unstable();
                conflicts.push(RuleConflict {
                    rule_a: perm.id.clone(),
                    rule_b: proh.id.clone(),
                    reason: format!(
                        "PERMISSION_PROHIBITION_OVERLAP: shared terms: {}",
                        overlap_terms.join(", ")
                    ),
                });
            }
        }
    }

    // Level invariant: a DIRECTIVE that explicitly negates PURPOSE keywords.
    let purposes: Vec<&Rule> = active
        .iter()
        .copied()
        .filter(|r| r.kind == RuleKind::Purpose)
        .collect();
    let directives: Vec<&Rule> = active
        .iter()
        .copied()
        .filter(|r| r.kind == RuleKind::Directive)
        .collect();

    const NEGATION_WORDS: &[&str] = &["not", "never", "avoid", "remove", "abandon", "drop"];

    for purpose in &purposes {
        let purpose_words = significant_words(&purpose.statement);
        for directive in &directives {
            let dir_lower = directive.statement.to_lowercase();
            let has_negation = NEGATION_WORDS.iter().any(|neg| dir_lower.contains(neg));
            if has_negation {
                let dir_words = significant_words(&directive.statement);
                let overlap_count = purpose_words
                    .iter()
                    .filter(|w| dir_words.contains(*w))
                    .count();
                if overlap_count >= 2 {
                    conflicts.push(RuleConflict {
                        rule_a: purpose.id.clone(),
                        rule_b: directive.id.clone(),
                        reason: "DIRECTIVE_CONTRADICTS_PURPOSE".to_owned(),
                    });
                }
            }
        }
    }

    conflicts
}

/// Walk the `parent_id` derivation chain for `rule_id`, returning IDs from
/// the root ancestor down to (and including) `rule_id`.
///
/// Cycles are broken by tracking visited IDs — a repeated node is not
/// included again.
///
/// Corresponds to `derivation_chain` in `rules.py`.
pub fn derivation_chain(store: &RuleStore, rule_id: &str) -> Vec<String> {
    let mut chain = Vec::new();
    let mut visited = std::collections::HashSet::new();
    derivation_chain_inner(store, rule_id, &mut chain, &mut visited);
    chain
}

fn derivation_chain_inner(
    store: &RuleStore,
    rule_id: &str,
    chain: &mut Vec<String>,
    visited: &mut std::collections::HashSet<String>,
) {
    if visited.contains(rule_id) {
        return;
    }
    visited.insert(rule_id.to_owned());

    if let Some(rule) = store.get_rule(rule_id) {
        // Recurse to the parent first (root-first ordering).
        if let Some(parent_id) = &rule.parent_id {
            let parent_id = parent_id.clone();
            derivation_chain_inner(store, &parent_id, chain, visited);
        }
        chain.push(rule_id.to_owned());
    }
}

/// Collect lowercase words of ≥ 4 characters from `text` as a deduplicated
/// `Vec<&str>`.  Used by [`detect_conflicts`] for keyword overlap analysis.
fn significant_words(text: &str) -> Vec<&str> {
    let mut words: Vec<&str> = text
        .split(|c: char| !c.is_alphanumeric())
        .filter(|w| w.len() >= 4)
        .collect();
    words.sort_unstable();
    words.dedup();
    words
}

// ── M54 — Jurisdictional compliance logging ───────────────────────────────────

/// A jurisdictional compliance advisory — logged when a network action may
/// be subject to jurisdiction-specific regulation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JurisdictionalAdvisory {
    pub peer_id: String,
    pub jurisdiction_code: String,
    pub action: String,
    pub advisory_text: String,
    pub at_unix: u64,
}

/// Advisory issued when a peer from a regulated jurisdiction attempts an action
/// that may require local compliance verification.
static REGULATED_JURISDICTIONS: &[&str] = &["US", "EU", "GB", "CN", "JP", "KR", "SG", "AU"];

/// Returns `Some(advisory_text)` if `jurisdiction_code` is in the regulated list
/// and the `action` is one of the high-risk categories.
pub fn check_jurisdictional_compliance(
    peer_id: &str,
    jurisdiction_code: &str,
    action: &str,
    now_unix: u64,
) -> Option<JurisdictionalAdvisory> {
    let high_risk_actions = ["token_transfer", "settlement", "governance_vote", "key_ceremony"];
    let jc = jurisdiction_code.to_uppercase();
    if !REGULATED_JURISDICTIONS.contains(&jc.as_str()) {
        return None;
    }
    if !high_risk_actions.iter().any(|a| action.contains(a)) {
        return None;
    }
    Some(JurisdictionalAdvisory {
        peer_id: peer_id.to_owned(),
        jurisdiction_code: jc.clone(),
        action: action.to_owned(),
        advisory_text: format!(
            "Peer '{peer_id}' in jurisdiction '{jc}' performed '{action}' — local compliance verification may be required."
        ),
        at_unix: now_unix,
    })
}

// ── M07 governance floor tests ────────────────────────────────────────────────

#[cfg(test)]
mod governance_floor_tests {
    use super::*;

    #[test]
    fn quorum_below_floor_rejected() {
        let result = check_governance_floor("quorum_threshold", 0.4);
        assert!(matches!(result, FloorCheckResult::BelowFloor { .. }));
    }

    #[test]
    fn supermajority_at_floor_accepted() {
        let result = check_governance_floor("supermajority_threshold", 0.66);
        assert_eq!(result, FloorCheckResult::Valid);
    }

    #[test]
    fn batch_validation_stops_at_first_violation() {
        let mut changes = HashMap::new();
        changes.insert("quorum_threshold".to_string(), 0.3); // below floor
        changes.insert("time_lock_secs".to_string(), 120.0); // valid
        let result = validate_governance_changes(&changes);
        assert!(result.is_err());
        if let Err(FloorCheckResult::BelowFloor { parameter, .. }) = result {
            assert_eq!(parameter, "quorum_threshold");
        } else {
            // The only Err variant is BelowFloor (UnknownParameter is treated as valid)
        }
    }

    #[test]
    fn unknown_parameter_treated_as_valid() {
        let result = check_governance_floor("nonexistent_param", 0.0);
        assert_eq!(result, FloorCheckResult::UnknownParameter);

        // validate_governance_changes treats UnknownParameter as valid (no error)
        let mut changes = HashMap::new();
        changes.insert("nonexistent_param".to_string(), 0.0);
        assert!(validate_governance_changes(&changes).is_ok());
    }
}

// ── M53 uncontested quorum tests ──────────────────────────────────────────────

#[cfg(test)]
mod uncontested_quorum_tests {
    use super::*;

    fn default_spec() -> UncontestedQuorumSpec {
        UncontestedQuorumSpec::default_spec()
    }

    #[test]
    fn all_conditions_met_eligible() {
        let spec = default_spec();
        let result = check_uncontested_eligible(
            spec.min_wait_secs,     // exactly at the threshold
            "operational",
            3,
            true,
            &spec,
        );
        assert_eq!(result, UncontestedEligibility::Eligible);
    }

    #[test]
    fn too_soon_rejected() {
        let spec = default_spec();
        let result = check_uncontested_eligible(100, "operational", 3, true, &spec);
        assert!(matches!(result, UncontestedEligibility::TooSoon { .. }));
    }

    #[test]
    fn wrong_class_rejected() {
        let spec = default_spec();
        let result = check_uncontested_eligible(
            spec.min_wait_secs,
            "economic",
            3,
            true,
            &spec,
        );
        assert!(matches!(result, UncontestedEligibility::WrongClass { .. }));
    }

    #[test]
    fn insufficient_signoffs_rejected() {
        let spec = default_spec();
        let result = check_uncontested_eligible(
            spec.min_wait_secs,
            "operational",
            2, // below the required 3
            true,
            &spec,
        );
        assert!(matches!(result, UncontestedEligibility::InsufficientSignoffs { .. }));
    }
}

// ── RuleStore tests ───────────────────────────────────────────────────────────

#[cfg(test)]
mod store_tests {
    use super::*;

    fn make_rule(id: &str, kind: RuleKind, statement: &str) -> Rule {
        Rule::new(id, kind, statement)
    }

    fn make_rule_with_parent(id: &str, kind: RuleKind, statement: &str, parent: &str) -> Rule {
        let mut r = Rule::new(id, kind, statement);
        r.parent_id = Some(parent.to_owned());
        r
    }

    // ── record_relationship / rules_for_change / changes_for_rule ────────────

    #[test]
    fn record_and_query_relationships() {
        let mut store = RuleStore::new();
        store.add_rule(make_rule("r1", RuleKind::Prohibition, "must not spend"));

        record_relationship(&mut store, "r1", "chg-001");
        record_relationship(&mut store, "r1", "chg-002");

        let rule_changes = changes_for_rule(&store, "r1");
        assert_eq!(rule_changes, vec!["chg-001", "chg-002"]);

        let rules = rules_for_change(&store, "chg-001");
        assert!(rules.contains(&"r1".to_owned()));
    }

    #[test]
    fn deduplication_of_bindings() {
        let mut store = RuleStore::new();
        record_relationship(&mut store, "r1", "chg-001");
        record_relationship(&mut store, "r1", "chg-001"); // duplicate
        assert_eq!(changes_for_rule(&store, "r1").len(), 1);
    }

    #[test]
    fn unknown_rule_returns_empty_vec() {
        let store = RuleStore::new();
        assert!(changes_for_rule(&store, "nonexistent").is_empty());
        assert!(rules_for_change(&store, "nonexistent").is_empty());
    }

    #[test]
    fn multiple_rules_govern_same_change() {
        let mut store = RuleStore::new();
        record_relationship(&mut store, "r1", "chg-X");
        record_relationship(&mut store, "r2", "chg-X");
        let rules = rules_for_change(&store, "chg-X");
        assert!(rules.contains(&"r1".to_owned()));
        assert!(rules.contains(&"r2".to_owned()));
    }

    // ── detect_conflicts ──────────────────────────────────────────────────────

    #[test]
    fn no_conflicts_when_no_overlap() {
        let mut store = RuleStore::new();
        store.add_rule(make_rule(
            "p1",
            RuleKind::Permission,
            "allowed to deploy runtime artifacts",
        ));
        store.add_rule(make_rule(
            "proh1",
            RuleKind::Prohibition,
            "never commit secrets keys tokens",
        ));
        // Overlap: none of the significant words match across both.
        // "deploy" "runtime" "artifacts" vs "commit" "secrets" "keys" "never" "tokens"
        assert!(detect_conflicts(&store).is_empty());
    }

    #[test]
    fn permission_prohibition_conflict_detected() {
        let mut store = RuleStore::new();
        store.add_rule(make_rule(
            "perm1",
            RuleKind::Permission,
            "allowed to spend transfer send funds externally",
        ));
        store.add_rule(make_rule(
            "proh1",
            RuleKind::Prohibition,
            "must not spend transfer send funds anywhere",
        ));
        // "spend", "transfer", "send", "funds" overlap ≥ 3 words.
        let conflicts = detect_conflicts(&store);
        assert!(!conflicts.is_empty());
        assert!(conflicts[0].rule_a == "perm1" || conflicts[0].rule_b == "perm1");
    }

    #[test]
    fn inactive_rule_not_included_in_conflict() {
        let mut store = RuleStore::new();
        let mut perm = make_rule(
            "perm1",
            RuleKind::Permission,
            "allowed spend transfer send funds",
        );
        perm.active = false;
        store.add_rule(perm);
        store.add_rule(make_rule(
            "proh1",
            RuleKind::Prohibition,
            "must not spend transfer send funds",
        ));
        // perm is inactive — no conflict.
        assert!(detect_conflicts(&store).is_empty());
    }

    #[test]
    fn directive_contradicts_purpose_detected() {
        let mut store = RuleStore::new();
        store.add_rule(make_rule(
            "purp1",
            RuleKind::Purpose,
            "build robust reliable runtime system",
        ));
        store.add_rule(make_rule(
            "dir1",
            RuleKind::Directive,
            "never build runtime — abandon system",
        ));
        // "build" and "runtime" overlap; has negation word "never" / "abandon".
        let conflicts = detect_conflicts(&store);
        assert!(!conflicts.is_empty());
        let c = &conflicts[0];
        assert!(c.reason.contains("PURPOSE"));
    }

    // ── derivation_chain ──────────────────────────────────────────────────────

    #[test]
    fn single_rule_chain() {
        let mut store = RuleStore::new();
        store.add_rule(make_rule("r1", RuleKind::Purpose, "root purpose"));
        let chain = derivation_chain(&store, "r1");
        assert_eq!(chain, vec!["r1"]);
    }

    #[test]
    fn two_level_chain() {
        let mut store = RuleStore::new();
        store.add_rule(make_rule("root", RuleKind::Purpose, "root"));
        store.add_rule(make_rule_with_parent(
            "child",
            RuleKind::Directive,
            "child",
            "root",
        ));

        let chain = derivation_chain(&store, "child");
        // root-first ordering
        assert_eq!(chain, vec!["root", "child"]);
    }

    #[test]
    fn three_level_chain() {
        let mut store = RuleStore::new();
        store.add_rule(make_rule("a", RuleKind::Purpose, "a"));
        store.add_rule(make_rule_with_parent("b", RuleKind::Directive, "b", "a"));
        store.add_rule(make_rule_with_parent("c", RuleKind::Policy, "c", "b"));

        let chain = derivation_chain(&store, "c");
        assert_eq!(chain, vec!["a", "b", "c"]);
    }

    #[test]
    fn missing_rule_returns_empty_chain() {
        let store = RuleStore::new();
        assert!(derivation_chain(&store, "nonexistent").is_empty());
    }

    #[test]
    fn cycle_does_not_loop_forever() {
        // Build a cycle: a -> b -> a
        let mut store = RuleStore::new();
        let mut a = make_rule("a", RuleKind::Purpose, "a");
        a.parent_id = Some("b".to_owned());
        let mut b = make_rule("b", RuleKind::Directive, "b");
        b.parent_id = Some("a".to_owned());
        store.add_rule(a);
        store.add_rule(b);

        // Should terminate without panic; exact order is implementation-defined.
        let chain = derivation_chain(&store, "a");
        assert!(!chain.is_empty());
        // No duplicates.
        let unique: std::collections::HashSet<_> = chain.iter().collect();
        assert_eq!(unique.len(), chain.len());
    }

    // ── parent_id field on Rule ───────────────────────────────────────────────

    #[test]
    fn rule_default_has_no_parent() {
        let r = Rule::new("x", RuleKind::Permission, "some statement");
        assert!(r.parent_id.is_none());
    }

    #[test]
    fn rule_with_parent_id() {
        let mut r = Rule::new("child", RuleKind::Policy, "derived rule");
        r.parent_id = Some("parent-rule".to_owned());
        assert_eq!(r.parent_id.as_deref(), Some("parent-rule"));
    }

    // M54 — jurisdictional compliance logging tests

    #[test]
    fn regulated_jurisdiction_high_risk_action_flagged() {
        let advisory = check_jurisdictional_compliance("peer-1", "US", "token_transfer", 1000);
        assert!(advisory.is_some());
        let adv = advisory.unwrap();
        assert_eq!(adv.jurisdiction_code, "US");
        assert!(adv.advisory_text.contains("token_transfer"));
    }

    #[test]
    fn unregulated_jurisdiction_not_flagged() {
        let advisory = check_jurisdictional_compliance("peer-2", "ZZ", "token_transfer", 1000);
        assert!(advisory.is_none());
    }

    #[test]
    fn low_risk_action_not_flagged() {
        let advisory = check_jurisdictional_compliance("peer-3", "US", "ping", 1000);
        assert!(advisory.is_none());
    }
}
