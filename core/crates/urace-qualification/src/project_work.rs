//! Outcome-first project work: declaration, evaluation, publication, and
//! durable recovery for executable deliverables.
//!
//! Ported from `trial/project_work.py`. Reserved authority actions (spend,
//! transfer, external publication) are gated through `AuthorityGate`.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

use crate::spec_trial::AuthorityGate;
use crate::trial_common::{now_iso, trial_identifier, SCORE_DELTA_THRESHOLD};
use crate::UNIT;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Task families supported by the project work harness.
pub const FAMILIES: [&str; 5] = [
    "navigation",
    "recovery",
    "receipts",
    "requirements_change",
    "integration",
];

/// Maximum active wall-clock budget seconds for a single project run.
pub const MAX_ACTIVE_SECONDS: u64 = 480;

/// Maximum phases a single project may progress through.
pub const MAX_PHASES: u8 = 2;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Errors that can occur during project work operations.
#[derive(Debug, Error)]
pub enum ProjectWorkError {
    #[error("declaration invalid: {0}")]
    InvalidDeclaration(String),
    #[error("authority denied: {0}")]
    AuthorityDenied(String),
    #[error("acceptance rejected: {0}")]
    AcceptanceRejected(String),
    #[error("publication error: {0}")]
    Publication(String),
    #[error("budget exceeded: active {active_seconds}s > limit {limit_seconds}s")]
    BudgetExceeded {
        active_seconds: u64,
        limit_seconds: u64,
    },
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// Record types
// ---------------------------------------------------------------------------

/// A project work declaration manifest.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProjectDeclaration {
    pub schema: String,
    pub product_id: String,
    pub family: String,
    pub intent: String,
    pub phase: u8,
    pub adaptive: bool,
    pub authority: AuthoritySpec,
    pub requirements: Vec<Requirement>,
    pub allowed_files: Vec<String>,
}

/// Authority scope attached to a declaration.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AuthoritySpec {
    /// Actions the executor may take autonomously.
    pub delegated: Vec<String>,
    /// Actions that require explicit owner confirmation (§62z).
    pub reserved: Vec<String>,
}

/// A single implementation requirement.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Requirement {
    pub id: String,
    pub title: String,
    pub scope: String,
    pub success_measure: String,
    pub priority: u8,
}

/// The result of a single project work run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectRunResult {
    pub id: String,
    pub product_id: String,
    pub family: String,
    pub phase: u8,
    pub complete: bool,
    pub validated: bool,
    /// "PENDING", "ACCEPTED", "REJECTED", "RESOURCE_BOUND_EXCEEDED".
    pub publication: String,
    pub outcome: String,
    pub started_at: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub finished_at: Option<String>,
    /// Total native provider tokens consumed.
    pub tokens: Option<u64>,
    /// True only when score_delta > 0 and acceptance passed.
    pub should_mint: bool,
    /// Mint amount in base UCR units (None when should_mint is false).
    pub mint_amount: Option<u64>,
    /// True iff active elapsed seconds did not exceed the budget.
    pub within_elapsed_budget: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failure_category: Option<String>,
}

/// Acceptance result returned by the independent evaluator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AcceptanceResult {
    pub validated: bool,
    pub passed: usize,
    pub total: usize,
    pub quality_score: f64,
    /// True iff the quality gate passed (non-None baseline delta > 0).
    pub gate_passed: bool,
}

// ---------------------------------------------------------------------------
// Product identity helper
// ---------------------------------------------------------------------------

/// Compute a stable product identity string from an arbitrary path string.
pub fn project_identity(path: &str) -> String {
    let mut h = Sha256::new();
    h.update(path.as_bytes());
    let hex = hex::encode(h.finalize());
    format!("urace-work:{}", &hex[..24])
}

// ---------------------------------------------------------------------------
// Declaration validation
// ---------------------------------------------------------------------------

/// Validate a `ProjectDeclaration`.
///
/// Returns `Err` on the first structural violation found.
pub fn validate_declaration(decl: &ProjectDeclaration) -> Result<(), ProjectWorkError> {
    if decl.schema != "urace-project-work-v1" {
        return Err(ProjectWorkError::InvalidDeclaration(format!(
            "unexpected schema: {}",
            decl.schema
        )));
    }
    if !FAMILIES.contains(&decl.family.as_str()) {
        return Err(ProjectWorkError::InvalidDeclaration(format!(
            "unknown family: {}",
            decl.family
        )));
    }
    if decl.phase == 0 || decl.phase > MAX_PHASES {
        return Err(ProjectWorkError::InvalidDeclaration(format!(
            "phase must be 1–{}",
            MAX_PHASES
        )));
    }
    if decl.allowed_files != ["app.py", "logic.py"] {
        return Err(ProjectWorkError::InvalidDeclaration(
            "allowed_files must be [\"app.py\", \"logic.py\"]".into(),
        ));
    }
    if decl.requirements.is_empty() {
        return Err(ProjectWorkError::InvalidDeclaration(
            "at least one requirement is required".into(),
        ));
    }
    for req in &decl.requirements {
        if req.scope != "implementation" {
            return Err(ProjectWorkError::InvalidDeclaration(format!(
                "requirement {} has non-implementation scope: {}",
                req.id, req.scope
            )));
        }
    }
    // Reserved actions must include "publish externally" and "spend money".
    let reserved = &decl.authority.reserved;
    for required_phrase in &["publish externally", "spend money"] {
        if !reserved.iter().any(|r| r.contains(required_phrase)) {
            return Err(ProjectWorkError::InvalidDeclaration(format!(
                "authority.reserved must include \"{}\"",
                required_phrase
            )));
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// §62z authority check for publication
// ---------------------------------------------------------------------------

/// Check whether a project work publication action is authorized.
///
/// Publication may only proceed when `score_delta > SCORE_DELTA_THRESHOLD`.
/// Reserved authority actions require owner confirmation and are always denied
/// by the autonomous path.
pub fn check_publication_authority(
    action_description: &str,
    score_delta: f64,
) -> Result<(), ProjectWorkError> {
    let outcome = AuthorityGate::check(action_description, score_delta);
    if !AuthorityGate::is_authorized(&outcome) {
        return Err(ProjectWorkError::AuthorityDenied(format!(
            "publication denied (score_delta={}, outcome={:?})",
            score_delta, outcome
        )));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Mint-eligibility computation
// ---------------------------------------------------------------------------

/// Compute mint eligibility from an acceptance result and a score delta.
///
/// Mint may only occur when `score_delta > SCORE_DELTA_THRESHOLD` AND
/// acceptance validated. This is the sole valid mint condition.
///
/// Returns `(should_mint, mint_amount)`.
pub fn compute_mint_eligibility(
    acceptance: &AcceptanceResult,
    score_delta: f64,
    tokens_consumed: u64,
) -> (bool, Option<u64>) {
    if !acceptance.validated || !acceptance.gate_passed {
        return (false, None);
    }
    if score_delta <= SCORE_DELTA_THRESHOLD {
        return (false, None);
    }
    // Mint is proportional to tokens consumed, capped by UNIT.
    let raw_amount = tokens_consumed.min(UNIT);
    (true, Some(raw_amount))
}

// ---------------------------------------------------------------------------
// Active budget tracker
// ---------------------------------------------------------------------------

/// Tracks active execution time for a project run, mirroring `ActiveBudget` in
/// the Python harness.
pub struct ActiveBudget {
    pub limit_seconds: u64,
    pub prior_seconds: u64,
    phase_start: Option<std::time::Instant>,
    phase_elapsed_ms: u64,
}

impl ActiveBudget {
    /// Create a new budget with a prior phase total and an upper limit.
    pub fn new(prior_seconds: u64, limit_seconds: u64) -> Self {
        ActiveBudget {
            limit_seconds,
            prior_seconds,
            phase_start: None,
            phase_elapsed_ms: 0,
        }
    }

    /// Mark the start of active executor work.
    pub fn activate(&mut self) {
        if self.phase_start.is_none() {
            self.phase_start = Some(std::time::Instant::now());
        }
    }

    /// Total active elapsed seconds (prior + current phase).
    pub fn elapsed_seconds(&self) -> u64 {
        let phase_ms = self
            .phase_start
            .map(|s| s.elapsed().as_millis() as u64)
            .unwrap_or(0);
        self.prior_seconds + (self.phase_elapsed_ms + phase_ms) / 1000
    }

    /// Return `true` if the budget has not been exceeded.
    pub fn within_budget(&self) -> bool {
        self.elapsed_seconds() <= self.limit_seconds
    }

    /// Close the current phase interval and record elapsed time.
    pub fn close(&mut self) {
        if let Some(start) = self.phase_start.take() {
            self.phase_elapsed_ms += start.elapsed().as_millis() as u64;
        }
    }
}

// ---------------------------------------------------------------------------
// Run result builder
// ---------------------------------------------------------------------------

/// Build an initial `ProjectRunResult` from a declaration.
pub fn start_run(decl: &ProjectDeclaration, run_id: Option<String>) -> ProjectRunResult {
    ProjectRunResult {
        id: run_id.unwrap_or_else(trial_identifier),
        product_id: decl.product_id.clone(),
        family: decl.family.clone(),
        phase: decl.phase,
        complete: false,
        validated: false,
        publication: "PENDING".to_owned(),
        outcome: "STARTED".to_owned(),
        started_at: now_iso(),
        finished_at: None,
        tokens: None,
        should_mint: false,
        mint_amount: None,
        within_elapsed_budget: true,
        failure_category: None,
    }
}

/// Finalise a run result after acceptance.
///
/// Sets `should_mint` and `mint_amount` only when score_delta > 0 and
/// acceptance passed. Closes the budget and records `finished_at`.
pub fn finalise_run(
    result: &mut ProjectRunResult,
    acceptance: &AcceptanceResult,
    score_delta: f64,
    tokens: u64,
    budget: &mut ActiveBudget,
) {
    budget.close();
    result.tokens = Some(tokens);
    result.finished_at = Some(now_iso());
    result.validated = acceptance.validated && acceptance.gate_passed;
    let (should_mint, mint_amount) = compute_mint_eligibility(acceptance, score_delta, tokens);
    result.should_mint = should_mint;
    result.mint_amount = mint_amount;
    result.within_elapsed_budget = budget.within_budget();
    if !result.within_elapsed_budget {
        result.publication = "RESOURCE_BOUND_EXCEEDED".to_owned();
    }
    result.complete = true;
    result.outcome = if result.validated {
        "VALIDATED_PROJECT_WORK".to_owned()
    } else {
        "REJECTED_OR_DEFERRED".to_owned()
    };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_decl() -> ProjectDeclaration {
        ProjectDeclaration {
            schema: "urace-project-work-v1".to_owned(),
            product_id: "urace-work:abc123abc123abc123abc123".to_owned(),
            family: "navigation".to_owned(),
            intent: "Deliver navigation workflow".to_owned(),
            phase: 1,
            adaptive: true,
            authority: AuthoritySpec {
                delegated: vec![
                    "objectives".to_owned(),
                    "local implementation changes".to_owned(),
                ],
                reserved: vec!["publish externally".to_owned(), "spend money".to_owned()],
            },
            requirements: vec![Requirement {
                id: "deliver-navigation".to_owned(),
                title: "Deliver navigation executable".to_owned(),
                scope: "implementation".to_owned(),
                success_measure: "Independent acceptance passes contract".to_owned(),
                priority: 80,
            }],
            allowed_files: vec!["app.py".to_owned(), "logic.py".to_owned()],
        }
    }

    #[test]
    fn valid_declaration_passes() {
        assert!(validate_declaration(&sample_decl()).is_ok());
    }

    #[test]
    fn unknown_family_rejected() {
        let mut decl = sample_decl();
        decl.family = "unknown-family".to_owned();
        assert!(validate_declaration(&decl).is_err());
    }

    #[test]
    fn mint_requires_positive_score_delta() {
        let acceptance = AcceptanceResult {
            validated: true,
            passed: 10,
            total: 10,
            quality_score: 1.0,
            gate_passed: true,
        };
        // Zero delta → no mint.
        let (should_mint, _) = compute_mint_eligibility(&acceptance, 0.0, 1000);
        assert!(!should_mint);
        // Positive delta → mint.
        let (should_mint, amount) = compute_mint_eligibility(&acceptance, 0.5, 1000);
        assert!(should_mint);
        assert!(amount.is_some());
    }

    #[test]
    fn mint_capped_at_unit() {
        let acceptance = AcceptanceResult {
            validated: true,
            passed: 10,
            total: 10,
            quality_score: 1.0,
            gate_passed: true,
        };
        // tokens > UNIT → capped.
        let (_, amount) = compute_mint_eligibility(&acceptance, 1.0, UNIT * 10);
        assert_eq!(amount, Some(UNIT));
    }

    #[test]
    fn project_identity_deterministic() {
        let id1 = project_identity("/some/path");
        let id2 = project_identity("/some/path");
        assert_eq!(id1, id2);
        assert!(id1.starts_with("urace-work:"));
        assert_eq!(id1.len(), "urace-work:".len() + 24);
    }

    #[test]
    fn authority_denied_for_zero_delta() {
        let result = check_publication_authority("editorial improvement", 0.0);
        assert!(result.is_err());
    }

    #[test]
    fn start_run_initial_state() {
        let decl = sample_decl();
        let result = start_run(&decl, Some("run-1".to_owned()));
        assert_eq!(result.id, "run-1");
        assert!(!result.complete);
        assert!(!result.should_mint);
        assert!(result.mint_amount.is_none());
        assert_eq!(result.outcome, "STARTED");
    }
}
