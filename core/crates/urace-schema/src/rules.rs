//! Rule ledger — governance model.
//!
//! Rust port of `rules.py`. Implements the Rule enum, immutability levels,
//! and a simple `RuleEngine` that evaluates a set of rules against a context.

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
            RuleKind::Purpose                 => 0,
            RuleKind::Directive
            | RuleKind::Permission
            | RuleKind::Prohibition          => 1,
            RuleKind::Objective
            | RuleKind::Policy               => 2,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            RuleKind::Purpose     => "PURPOSE",
            RuleKind::Directive   => "DIRECTIVE",
            RuleKind::Permission  => "PERMISSION",
            RuleKind::Prohibition => "PROHIBITION",
            RuleKind::Objective   => "OBJECTIVE",
            RuleKind::Policy      => "POLICY",
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

            match rule.kind {
                RuleKind::Prohibition => {
                    if self.statement_matches_context(&rule.statement, context) {
                        violations.push(RuleViolation {
                            rule_id: rule.id.clone(),
                            kind: rule.kind,
                            statement: rule.statement.clone(),
                            detail: format!(
                                "Prohibited action matches rule: {}",
                                rule.id
                            ),
                        });
                    }
                }
                // PURPOSE, DIRECTIVE, PERMISSION, OBJECTIVE, POLICY are advisory
                // at this evaluation layer; they do not block by themselves.
                _ => {}
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

        let context_text: String = context.values().map(|v| v.to_lowercase()).collect::<Vec<_>>().join(" ");

        // Violation if at least 2 keywords match (reduce false positives).
        let matches = keywords.iter().filter(|kw| context_text.contains(**kw)).count();
        matches >= 2.min(keywords.len())
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn ctx(pairs: &[(&str, &str)]) -> HashMap<String, String> {
        pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect()
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
        let result = engine.evaluate(&[rule], &ctx(&[("action", "spend money transfer to wallet")]));
        assert!(!result.is_empty());
    }

    #[test]
    fn permission_does_not_produce_violation() {
        let engine = RuleEngine::new();
        let rule = Rule::new("r2", RuleKind::Permission, "allowed to deploy runtime");
        let result = engine.evaluate(&[rule], &ctx(&[("action", "allowed to deploy runtime")]));
        assert!(result.is_empty(), "permissions should not produce violations");
    }

    #[test]
    fn scope_mismatch_skips_rule() {
        let engine = RuleEngine::new();
        let mut rule = Rule::new("r3", RuleKind::Prohibition, "spend money transfer");
        rule.scope = vec!["runtime".into()];
        // Context scope is "documentation" — rule should not apply.
        let result = engine.evaluate(&[rule], &ctx(&[
            ("scope", "documentation"),
            ("action", "spend money transfer"),
        ]));
        assert!(result.is_empty());
    }

    #[test]
    fn rule_kind_levels() {
        assert_eq!(RuleKind::Purpose.level(), 0);
        assert_eq!(RuleKind::Directive.level(), 1);
        assert_eq!(RuleKind::Objective.level(), 2);
    }
}
