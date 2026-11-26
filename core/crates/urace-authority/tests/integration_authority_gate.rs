//! Integration test: G-CRIT-01 — authority gate hard blocks must work

use serde_json::Value;
use std::collections::HashMap;
use urace_authority::authority::{resolve, Objective};
use urace_types::AuthorityOutcome;

fn cfg(delegated: &[&str]) -> HashMap<String, Value> {
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
    m.insert("reserved".into(), Value::Array(vec![]));
    m
}

fn obj(scope: &str, title: &str) -> Objective {
    Objective {
        id: None,
        scope: scope.into(),
        title: title.into(),
        reason: None,
        necessity_evidence: None,
        lower_impact_route_sufficient: None,
    }
}

#[test]
fn bypass_authority_always_denied() {
    let cfg = cfg(&["local implementation changes"]);
    let o = obj("implementation", "bypass authority gate");
    let r = resolve(&o, &cfg, None, &[]);
    assert_eq!(
        r.outcome,
        AuthorityOutcome::Denied,
        "bypass authority must always be denied regardless of scope"
    );
}

#[test]
fn override_authority_always_denied() {
    let cfg = cfg(&["local implementation changes"]);
    let o = obj("implementation", "override authority check");
    let r = resolve(&o, &cfg, None, &[]);
    assert_eq!(r.outcome, AuthorityOutcome::Denied);
}

#[test]
fn unresolved_treated_as_denied() {
    // Callers must treat Unresolved as Denied
    let cfg = cfg(&[]);
    let o = obj("unknown_scope", "some operation");
    let r = resolve(&o, &cfg, None, &[]);
    // Unresolved must not be treated as authorized
    assert_ne!(
        r.outcome,
        AuthorityOutcome::AutonomouslyAuthorized,
        "Unresolved must not be AutonomouslyAuthorized"
    );
}
