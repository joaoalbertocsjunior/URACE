//! §62z Authority gate — Rust port of `authority.py`.
//!
//! Before any qualifying action (spend, transfer, goal creation), authority
//! MUST be resolved. UNRESOLVED is always treated as DENIED.
//!
//! Hard-block phrases: "override authority", "bypass authority", "ignore authority".
//! These trigger hard rejection regardless of delegated authority.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use urace_types::{AuthorityOutcome, AuthorityResolution};

/// An Objective submitted for authority resolution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Objective {
    pub id: Option<String>,
    pub scope: String,
    pub title: String,
    pub reason: Option<String>,
    pub necessity_evidence: Option<String>,
    pub lower_impact_route_sufficient: Option<bool>,
}

static RESERVED_SIGNAL_PHRASES: &[&str] = &[
    "change retained purpose",
    "weaken normative invariants",
    "publish externally",
    "spend money",
    "destructive external effects",
    "remove invariant",
    "delete invariant",
    "override authority",
    "bypass authority",
    "ignore authority",
    "disable authority",
];

static WEAKENING_VERBS: &[&str] = &[
    "remove", "delete", "weaken", "relax", "bypass", "ignore", "disable", "override",
];

fn scope_required_authorities(scope: &str) -> Option<HashSet<&'static str>> {
    match scope {
        "implementation" => Some(HashSet::from(["local implementation changes"])),
        "documentation" => Some(HashSet::from([
            "assessment",
            "objectives",
            "priority",
            "plans",
            "local implementation changes",
            "urace.md specification evolution within the retained purpose, authority boundaries, and normative invariants",
        ])),
        "metrics" => Some(HashSet::from(["measurement"])),
        "runtime" => Some(HashSet::from([
            "runtime self-evolution and re-bootstrap with validated rollback",
        ])),
        "rebootstrap" => Some(HashSet::from([
            "runtime self-evolution and re-bootstrap with validated rollback",
            "urace.md specification evolution within the retained purpose, authority boundaries, and normative invariants",
        ])),
        _ => None,
    }
}

fn has_weakening_request(text: &str) -> bool {
    // Strip negated verb patterns: "do not/must not/don't/never <verb>"
    let prohibition_re = regex_lite::Regex::new(
        r"(?i)\b(?:do\s+not|must\s+not|don't|never)\s+(?:remove|delete|weaken|relax|bypass|ignore|disable|override)\b",
    );
    let cleaned = match prohibition_re {
        Ok(re) => re.replace_all(text, " ").into_owned(),
        Err(_) => text.to_owned(),
    };
    WEAKENING_VERBS.iter().any(|v| {
        let pat = format!(r"\b{v}\b");
        regex_lite::Regex::new(&pat)
            .map(|re| re.is_match(&cleaned))
            .unwrap_or(false)
    })
}

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{secs}")
}

fn resolution(
    outcome: AuthorityOutcome,
    basis: impl Into<String>,
    gate: impl Into<String>,
) -> AuthorityResolution {
    AuthorityResolution {
        outcome,
        basis: basis.into(),
        gate: gate.into(),
        resolved_at: now_iso(),
    }
}

/// Operations classified as "high-value" require a time-lock check.
/// The lock delay is in seconds; the caller must track when the operation was first requested.
pub const HIGH_VALUE_TIMELOCK_SECS: u64 = 300; // 5 minutes

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum OperationClass {
    Standard,   // No time-lock required
    HighValue,  // Requires HIGH_VALUE_TIMELOCK_SECS to elapse before execution
    Critical,   // Requires governance vote (not handled here — returns RequiresAuthoritativeDecision)
}

/// Classify an objective's scope into an OperationClass.
pub fn classify_operation(scope: &str) -> OperationClass {
    match scope.to_lowercase().as_str() {
        "implementation" | "documentation" | "metrics" => OperationClass::Standard,
        "runtime" | "rebootstrap" => OperationClass::HighValue,
        _ => OperationClass::Critical,
    }
}

/// Check whether a time-lock has elapsed.
/// `first_requested_secs`: Unix timestamp when operation was first requested.
/// `now_secs`: Current Unix timestamp.
pub fn timelock_elapsed(first_requested_secs: u64, now_secs: u64, lock_secs: u64) -> bool {
    now_secs >= first_requested_secs + lock_secs
}

/// Tracks the total "authority budget" consumed in a session.
/// Each AUTONOMOUSLY_AUTHORIZED resolution consumes 1 unit.
/// When budget is exhausted, further resolutions return RequiresAuthoritativeDecision.
#[derive(Debug, Clone)]
pub struct SessionBudget {
    max_ops: u64,
    consumed: u64,
    session_id: String,
}

impl SessionBudget {
    pub fn new(max_ops: u64, session_id: impl Into<String>) -> Self {
        SessionBudget { max_ops, consumed: 0, session_id: session_id.into() }
    }

    /// Returns true if budget is not yet exhausted.
    pub fn has_capacity(&self) -> bool {
        self.consumed < self.max_ops
    }

    /// Consume 1 unit. Returns Err if already exhausted.
    pub fn consume(&mut self) -> Result<u64, &'static str> {
        if !self.has_capacity() {
            return Err("session budget exhausted");
        }
        self.consumed += 1;
        Ok(self.consumed)
    }

    pub fn remaining(&self) -> u64 {
        self.max_ops.saturating_sub(self.consumed)
    }

    pub fn consumed(&self) -> u64 { self.consumed }
    pub fn max_ops(&self) -> u64 { self.max_ops }
    pub fn session_id(&self) -> &str { &self.session_id }
}

/// Resolve with session budget enforcement.
/// If budget is provided and exhausted, returns RequiresAuthoritativeDecision.
/// If resolve returns AutonomouslyAuthorized and budget is provided, consumes 1 unit.
pub fn resolve_with_budget(
    objective: &Objective,
    authority_config: &HashMap<String, Value>,
    self_evolution_policy: Option<&HashMap<String, Value>>,
    constraints: &[String],
    budget: Option<&mut SessionBudget>,
) -> AuthorityResolution {
    if let Some(ref b) = budget {
        if !b.has_capacity() {
            return resolution(
                AuthorityOutcome::RequiresAuthoritativeDecision,
                "Session budget exhausted; further operations require authoritative decision",
                "session_budget",
            );
        }
    }
    let result = resolve(objective, authority_config, self_evolution_policy, constraints);
    if result.outcome == AuthorityOutcome::AutonomouslyAuthorized {
        if let Some(b) = budget {
            let _ = b.consume();
        }
    }
    result
}

/// Evaluate whether an Objective is within the delegated Authority boundary.
pub fn resolve(
    objective: &Objective,
    authority_config: &HashMap<String, Value>,
    self_evolution_policy: Option<&HashMap<String, Value>>,
    constraints: &[String],
) -> AuthorityResolution {
    let delegated: HashSet<String> = authority_config
        .get("delegated")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.to_lowercase())
                .collect()
        })
        .unwrap_or_default();

    let reserved: HashSet<String> = authority_config
        .get("reserved")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.to_lowercase())
                .collect()
        })
        .unwrap_or_default();

    let scope = objective.scope.to_lowercase();
    let title = objective.title.to_lowercase();
    let reason = objective.reason.as_deref().unwrap_or("").to_lowercase();
    let combined = format!("{title} {reason}");

    // 1. Hard-block: reserved decision match.
    for phrase in reserved.iter() {
        if combined.contains(phrase.as_str()) {
            return resolution(
                AuthorityOutcome::Denied,
                format!("Objective matches reserved decision: '{phrase}'"),
                "reserved_decision",
            );
        }
    }
    for signal in RESERVED_SIGNAL_PHRASES {
        if combined.contains(signal) {
            return resolution(
                AuthorityOutcome::Denied,
                format!("Objective contains reserved-decision signal phrase: '{signal}'"),
                "reserved_decision_signal",
            );
        }
    }

    // 2. Scope must map to delegated authority.
    let required_opt = scope_required_authorities(&scope);
    if let Some(ref required) = required_opt {
        let matched: HashSet<&str> = required
            .iter()
            .copied()
            .filter(|r| delegated.contains(*r))
            .collect();
        if !required.is_empty() && matched.is_empty() {
            return resolution(
                AuthorityOutcome::RequiresAuthoritativeDecision,
                format!(
                    "Scope '{scope}' requires authority not found in delegated boundary. \
                     Required one of: {:?}. Delegated: {:?}",
                    {
                        let mut v: Vec<_> = required.iter().collect();
                        v.sort();
                        v
                    },
                    {
                        let mut v: Vec<_> = delegated.iter().collect();
                        v.sort();
                        v
                    }
                ),
                "scope_boundary",
            );
        }
    }

    // 3. Constraint-weakening check.
    for constraint in constraints {
        let constraint_lower = constraint.to_lowercase();
        let keywords: HashSet<&str> = constraint_lower
            .split_whitespace()
            .filter(|w| w.len() > 4)
            .collect();
        if has_weakening_request(&combined) && keywords.iter().any(|kw| combined.contains(kw)) {
            return resolution(
                AuthorityOutcome::RequiresAuthoritativeDecision,
                format!("Objective appears to weaken retained constraint: '{constraint}'"),
                "constraint_protection",
            );
        }
    }

    // 4. Self-evolution gate for runtime/rebootstrap.
    if matches!(scope.as_str(), "runtime" | "rebootstrap") {
        let policy_mode = self_evolution_policy
            .and_then(|p| p.get("mode"))
            .and_then(|v| v.as_str())
            .unwrap_or("DISABLED")
            .to_uppercase();

        if policy_mode == "DISABLED" {
            return resolution(
                AuthorityOutcome::Denied,
                "Self-evolution policy is DISABLED; runtime/rebootstrap scope not authorized",
                "self_evolution_policy",
            );
        }
        if policy_mode == "NECESSARY_ONLY" {
            let necessity = objective
                .necessity_evidence
                .as_deref()
                .unwrap_or("")
                .trim()
                .to_owned();
            let lower_impact = objective.lower_impact_route_sufficient.unwrap_or(true);
            if necessity.is_empty() || lower_impact {
                return resolution(
                    AuthorityOutcome::RequiresAuthoritativeDecision,
                    "Self-evolution policy NECESSARY_ONLY requires non-empty necessity_evidence \
                     and lower_impact_route_sufficient=false",
                    "necessity_gate",
                );
            }
        }
    }

    // 5. Unknown scope → UNRESOLVED (treat as DENIED at call site).
    if required_opt.is_none() {
        return resolution(
            AuthorityOutcome::Unresolved,
            format!("Unknown scope '{scope}'; cannot map to delegated authority boundary"),
            "unknown_scope",
        );
    }

    resolution(
        AuthorityOutcome::AutonomouslyAuthorized,
        format!("Scope '{scope}' matched delegated authority"),
        "passed",
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn authority_config(delegated: &[&str], reserved: &[&str]) -> HashMap<String, Value> {
        let mut m = HashMap::new();
        m.insert(
            "delegated".into(),
            Value::Array(
                delegated
                    .iter()
                    .map(|s| Value::String(s.to_string()))
                    .collect(),
            ),
        );
        m.insert(
            "reserved".into(),
            Value::Array(
                reserved
                    .iter()
                    .map(|s| Value::String(s.to_string()))
                    .collect(),
            ),
        );
        m
    }

    fn obj(scope: &str, title: &str) -> Objective {
        Objective {
            id: Some("test".into()),
            scope: scope.into(),
            title: title.into(),
            reason: None,
            necessity_evidence: None,
            lower_impact_route_sufficient: None,
        }
    }

    #[test]
    fn implementation_scope_allowed() {
        let cfg = authority_config(&["local implementation changes"], &[]);
        let r = resolve(&obj("implementation", "add feature"), &cfg, None, &[]);
        assert_eq!(r.outcome, AuthorityOutcome::AutonomouslyAuthorized);
    }

    #[test]
    fn reserved_decision_denied() {
        let cfg = authority_config(&["local implementation changes"], &["spend money"]);
        let r = resolve(
            &obj("implementation", "spend money on infra"),
            &cfg,
            None,
            &[],
        );
        assert_eq!(r.outcome, AuthorityOutcome::Denied);
    }

    #[test]
    fn bypass_authority_hard_block() {
        let cfg = authority_config(&["local implementation changes"], &[]);
        let r = resolve(
            &obj("implementation", "bypass authority gate"),
            &cfg,
            None,
            &[],
        );
        assert_eq!(r.outcome, AuthorityOutcome::Denied);
    }

    #[test]
    fn override_authority_hard_block() {
        let cfg = authority_config(&["local implementation changes"], &[]);
        let r = resolve(
            &obj("implementation", "override authority check"),
            &cfg,
            None,
            &[],
        );
        assert_eq!(r.outcome, AuthorityOutcome::Denied);
    }

    #[test]
    fn missing_delegation_requires_decision() {
        let cfg = authority_config(&[], &[]);
        let r = resolve(&obj("implementation", "add feature"), &cfg, None, &[]);
        assert_eq!(r.outcome, AuthorityOutcome::RequiresAuthoritativeDecision);
    }

    #[test]
    fn runtime_disabled_policy_denied() {
        let cfg = authority_config(
            &["runtime self-evolution and re-bootstrap with validated rollback"],
            &[],
        );
        let policy = HashMap::from([("mode".to_string(), Value::String("DISABLED".into()))]);
        let r = resolve(&obj("runtime", "upgrade runtime"), &cfg, Some(&policy), &[]);
        assert_eq!(r.outcome, AuthorityOutcome::Denied);
    }

    #[test]
    fn unresolved_on_unknown_scope() {
        let cfg = authority_config(&["local implementation changes"], &[]);
        let r = resolve(&obj("unknown_scope_xyz", "do something"), &cfg, None, &[]);
        assert_eq!(r.outcome, AuthorityOutcome::Unresolved);
    }

    #[test]
    fn session_budget_exhausted_returns_decision() {
        let cfg = authority_config(&["local implementation changes"], &[]);
        let mut budget = SessionBudget::new(2, "test-session");

        // First two succeed
        let r1 = resolve_with_budget(&obj("implementation", "task one"), &cfg, None, &[], Some(&mut budget));
        assert_eq!(r1.outcome, AuthorityOutcome::AutonomouslyAuthorized);
        let r2 = resolve_with_budget(&obj("implementation", "task two"), &cfg, None, &[], Some(&mut budget));
        assert_eq!(r2.outcome, AuthorityOutcome::AutonomouslyAuthorized);

        // Third is blocked by budget
        let r3 = resolve_with_budget(&obj("implementation", "task three"), &cfg, None, &[], Some(&mut budget));
        assert_eq!(r3.outcome, AuthorityOutcome::RequiresAuthoritativeDecision);
        assert_eq!(r3.gate, "session_budget");
    }

    #[test]
    fn session_budget_not_consumed_on_denied() {
        let cfg = authority_config(&["local implementation changes"], &["spend money"]);
        let mut budget = SessionBudget::new(5, "test-session");

        // Denied resolution — budget should not be decremented
        let r = resolve_with_budget(
            &obj("implementation", "spend money on infra"),
            &cfg,
            None,
            &[],
            Some(&mut budget),
        );
        assert_eq!(r.outcome, AuthorityOutcome::Denied);
        assert_eq!(budget.consumed(), 0);
        assert_eq!(budget.remaining(), 5);
    }

    #[test]
    fn timelock_elapsed_check() {
        assert!(timelock_elapsed(100, 405, 300));
        assert!(!timelock_elapsed(100, 399, 300));
    }

    #[test]
    fn classify_runtime_is_high_value() {
        assert_eq!(classify_operation("runtime"), OperationClass::HighValue);
    }
}
