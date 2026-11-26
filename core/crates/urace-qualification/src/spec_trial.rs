//! Versioned spec-document improvement: snapshot management, section selection,
//! patch validation, and resource metrics.
//!
//! Ported from `trial/spec_trial.py`. Source text is treated as data, never as
//! executable authority. The §62z boundary (authority.py) is preserved via the
//! `AuthorityGate` wrapper.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

use crate::trial_common::SCORE_DELTA_THRESHOLD;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Errors that can occur during spec trial operations.
#[derive(Debug, Error)]
pub enum SpecTrialError {
    #[error("version integrity failure: {0}")]
    Integrity(String),
    #[error("patch rejected: {0}")]
    PatchRejected(String),
    #[error("authority gate rejected: {0}")]
    AuthorityDenied(String),
    #[error("review rejected: {0}")]
    ReviewRejected(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// Record types
// ---------------------------------------------------------------------------

/// A frozen version snapshot record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionManifest {
    pub version: u64,
    pub parent_version: u64,
    pub parent_sha256: String,
    pub sha256: String,
    pub accepted_at: String,
    /// Whether any normative requirement sentences changed (must be `false`).
    pub normative_sentences_unchanged: bool,
    pub claim: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trial_id: Option<String>,
    #[serde(flatten)]
    pub extra: std::collections::HashMap<String, serde_json::Value>,
}

/// A proposed editorial patch.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Proposal {
    /// The unique exact passage to replace.
    pub old: String,
    /// The replacement text.
    pub new: String,
    /// An existing verbatim quote (≥30 chars) supporting the edit.
    pub evidence_quote: String,
    /// Specific material benefit of the change.
    pub reason: String,
    /// Concrete bounded failure case resolved by the edit (40–2000 chars).
    pub failure_case: String,
}

/// Quality-review result returned by the independent reviewer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReviewResult {
    pub preserves_existing_semantics: bool,
    pub no_new_runtime_behavior: bool,
    pub no_weakened_authority_or_evidence: bool,
    pub material_quality_improved: bool,
    pub failure_case_supported: bool,
    pub scores: ScoreComparison,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub explanation: Option<String>,
    #[serde(flatten)]
    pub extra: std::collections::HashMap<String, serde_json::Value>,
}

/// Before/after quality scores for clarity, consistency, and conciseness.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreComparison {
    pub before: QualityScores,
    pub after: QualityScores,
}

/// Per-dimension quality scores (1–5).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityScores {
    pub clarity: u8,
    pub consistency: u8,
    pub conciseness: u8,
}

impl QualityScores {
    /// Return `true` if all scores are within the valid 1–5 range.
    pub fn is_valid(&self) -> bool {
        [self.clarity, self.consistency, self.conciseness]
            .iter()
            .all(|&s| (1..=5).contains(&s))
    }
}

/// Resource usage metrics for a set of executor events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceMetrics {
    pub native_calls: usize,
    pub known_tokens: u64,
    pub missing_usage: usize,
    pub known_executor_seconds: f64,
    pub inflight_calls: usize,
}

// ---------------------------------------------------------------------------
// SHA-256 helpers
// ---------------------------------------------------------------------------

/// Compute the hex-encoded SHA-256 of a UTF-8 string.
pub fn digest_text(text: &str) -> String {
    let mut h = Sha256::new();
    h.update(text.as_bytes());
    hex::encode(h.finalize())
}

// ---------------------------------------------------------------------------
// Patch validation
// ---------------------------------------------------------------------------

/// Extract normative requirement sentences from `text`.
///
/// A sentence is normative when it contains one of the RFC 2119 keywords.
pub fn normative_sentences(text: &str) -> Vec<String> {
    let keywords = ["MUST", "SHALL", "SHOULD", "MAY", "REQUIRED"];
    // Split on blank lines or list/heading markers, then on sentence boundaries.
    let mut result = Vec::new();
    for block in text.split("\n\n") {
        // Simple sentence split on ". " followed by an uppercase letter.
        let mut sentence = String::new();
        let chars: Vec<char> = block.chars().collect();
        let mut i = 0;
        while i < chars.len() {
            sentence.push(chars[i]);
            // Check for sentence boundary: ". " followed by uppercase.
            if i + 2 < chars.len()
                && chars[i] == '.'
                && chars[i + 1] == ' '
                && chars[i + 2].is_uppercase()
            {
                let trimmed = sentence.trim().to_owned();
                if keywords.iter().any(|kw| trimmed.contains(kw)) {
                    result.push(trimmed);
                }
                sentence.clear();
            }
            i += 1;
        }
        let trimmed = sentence.trim().to_owned();
        if !trimmed.is_empty() && keywords.iter().any(|kw| trimmed.contains(kw)) {
            result.push(trimmed);
        }
    }
    result
}

/// Extract top-level headings (`#` through `######`) from `text`.
pub fn extract_headings(text: &str) -> Vec<String> {
    text.lines()
        .filter(|line| {
            let trimmed = line.trim_start_matches('#');
            let n = line.len() - trimmed.len();
            (1..=6).contains(&n) && trimmed.starts_with(' ')
        })
        .map(|s| s.to_owned())
        .collect()
}

/// Return `true` iff `review` passes all acceptance gates.
pub fn review_passes(review: &ReviewResult) -> bool {
    if !review.preserves_existing_semantics
        || !review.no_new_runtime_behavior
        || !review.no_weakened_authority_or_evidence
        || !review.material_quality_improved
        || !review.failure_case_supported
    {
        return false;
    }
    if !review.scores.before.is_valid() || !review.scores.after.is_valid() {
        return false;
    }
    if review.explanation.as_deref().unwrap_or("").is_empty() {
        return false;
    }
    // After scores must be >= before in every dimension, and strictly > in at least one.
    let before = &review.scores.before;
    let after = &review.scores.after;
    after.clarity >= before.clarity
        && after.consistency >= before.consistency
        && after.conciseness >= before.conciseness
        && (after.clarity > before.clarity
            || after.consistency > before.consistency
            || after.conciseness > before.conciseness)
}

/// Validate a proposed editorial patch against `section`.
///
/// Returns the patched section text on success.
///
/// # Errors
/// - `PatchRejected` when the proposal violates any structural guard.
pub fn validate_patch(section: &str, proposal: &Proposal) -> Result<String, SpecTrialError> {
    if proposal.old.is_empty() || proposal.old == proposal.new {
        return Err(SpecTrialError::PatchRejected(
            "old and new must differ and old must be non-empty".into(),
        ));
    }
    if proposal.old.len() > 5000 || proposal.new.len() > 5000 {
        return Err(SpecTrialError::PatchRejected(
            "old or new text exceeds 5000 character limit".into(),
        ));
    }
    let occurrences = section.matches(&proposal.old as &str).count();
    if occurrences != 1 {
        return Err(SpecTrialError::PatchRejected(format!(
            "old text must appear exactly once in section (found {})",
            occurrences
        )));
    }
    if proposal.failure_case.len() < 40 || proposal.failure_case.len() > 2000 {
        return Err(SpecTrialError::PatchRejected(
            "failure_case must be 40–2000 characters".into(),
        ));
    }
    if proposal.evidence_quote.len() < 30 || !section.contains(&proposal.evidence_quote as &str) {
        return Err(SpecTrialError::PatchRejected(
            "evidence_quote must be ≥30 chars and present in the section".into(),
        ));
    }
    let candidate = section.replacen(&proposal.old, &proposal.new, 1);
    // Guard: normative sentences must be unchanged.
    if normative_sentences(section) != normative_sentences(&candidate) {
        return Err(SpecTrialError::PatchRejected(
            "normative requirement sentences are immutable".into(),
        ));
    }
    // Guard: headings must be unchanged.
    if extract_headings(section) != extract_headings(&candidate) {
        return Err(SpecTrialError::PatchRejected(
            "section heading structure is immutable".into(),
        ));
    }
    // Guard: no unbounded expansion.
    if candidate.len() > section.len() + 2000 {
        return Err(SpecTrialError::PatchRejected(
            "proposed replacement causes unbounded expansion".into(),
        ));
    }
    Ok(candidate)
}

// ---------------------------------------------------------------------------
// §62z authority gate
// ---------------------------------------------------------------------------

/// Outcomes of the §62z authority check.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuthorityOutcome {
    AutonomouslyAuthorized,
    Denied,
    RequiresAuthoritativeDecision,
    Unresolved,
}

/// Lightweight §62z gate for spec-trial operations.
///
/// Any action whose `score_delta` does not exceed `SCORE_DELTA_THRESHOLD`
/// is treated as `Denied`. Reserved phrases trigger hard rejection.
pub struct AuthorityGate;

impl AuthorityGate {
    /// Check whether a qualifying action (score_delta improvement) is authorized.
    ///
    /// Returns `Denied` for zero or negative deltas (no mint may occur).
    /// Returns `Denied` on reserved phrases.
    pub fn check(description: &str, score_delta: f64) -> AuthorityOutcome {
        let lower = description.to_lowercase();
        for phrase in &["override authority", "bypass authority", "ignore authority"] {
            if lower.contains(phrase) {
                return AuthorityOutcome::Denied;
            }
        }
        if score_delta <= SCORE_DELTA_THRESHOLD {
            return AuthorityOutcome::Denied;
        }
        AuthorityOutcome::AutonomouslyAuthorized
    }

    /// Return `true` only when the outcome is `AutonomouslyAuthorized`.
    pub fn is_authorized(outcome: &AuthorityOutcome) -> bool {
        *outcome == AuthorityOutcome::AutonomouslyAuthorized
    }
}

// ── M52 — Peer-review gate ────────────────────────────────────────────────────

/// Minimum number of peer reviewers required before a spec change is accepted.
pub const MIN_PEER_REVIEWERS: usize = 2;

/// A single peer review for a spec proposal.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerReview {
    pub reviewer_id: String,
    pub proposal_id: String,
    pub passed: bool,
    pub comment: String,
}

/// Peer-review registry for spec proposals.
pub struct PeerReviewGate {
    reviews: std::collections::HashMap<String, Vec<PeerReview>>,
    min_reviewers: usize,
}

impl PeerReviewGate {
    pub fn new(min_reviewers: usize) -> Self {
        PeerReviewGate {
            reviews: std::collections::HashMap::new(),
            min_reviewers,
        }
    }

    /// Submit a review. Deduplicates by `reviewer_id` per proposal.
    pub fn submit(&mut self, review: PeerReview) {
        let list = self.reviews.entry(review.proposal_id.clone()).or_default();
        if !list.iter().any(|r| r.reviewer_id == review.reviewer_id) {
            list.push(review);
        }
    }

    /// Returns `true` iff `proposal_id` has received at least `min_reviewers`
    /// distinct reviews ALL of which passed.
    pub fn gate_passed(&self, proposal_id: &str) -> bool {
        let reviews = match self.reviews.get(proposal_id) {
            Some(r) => r,
            None => return false,
        };
        reviews.len() >= self.min_reviewers && reviews.iter().all(|r| r.passed)
    }

    pub fn review_count(&self, proposal_id: &str) -> usize {
        self.reviews.get(proposal_id).map(|r| r.len()).unwrap_or(0)
    }
}

impl Default for PeerReviewGate {
    fn default() -> Self {
        Self::new(MIN_PEER_REVIEWERS)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn patch_valid_non_normative_edit() {
        let section = "This is a prose section.\n\nIt explains something useful here.";
        let proposal = Proposal {
            old: "It explains something useful here.".to_owned(),
            new: "It clarifies something useful here.".to_owned(),
            evidence_quote: "It explains something useful here".to_owned(),
            reason: "Improve clarity".to_owned(),
            failure_case: "A".repeat(40),
        };
        let result = validate_patch(section, &proposal);
        assert!(result.is_ok(), "{:?}", result);
        assert!(result.unwrap().contains("clarifies"));
    }

    #[test]
    fn patch_normative_mutation_rejected() {
        let section = "Items MUST be validated before use. Other text here.";
        let proposal = Proposal {
            old: "MUST".to_owned(),
            new: "SHOULD".to_owned(),
            evidence_quote: "Items MUST be validated".to_owned(),
            reason: "Relaxing requirement".to_owned(),
            failure_case: "A".repeat(40),
        };
        // normative_sentences differ → rejected
        assert!(validate_patch(section, &proposal).is_err());
    }

    #[test]
    fn authority_gate_zero_delta_denied() {
        let outcome = AuthorityGate::check("editorial improvement", 0.0);
        assert_eq!(outcome, AuthorityOutcome::Denied);
    }

    #[test]
    fn authority_gate_positive_delta_authorized() {
        let outcome = AuthorityGate::check("editorial improvement", 0.1);
        assert_eq!(outcome, AuthorityOutcome::AutonomouslyAuthorized);
    }

    #[test]
    fn authority_gate_reserved_phrase_denied() {
        let outcome = AuthorityGate::check("override authority and proceed", 1.0);
        assert_eq!(outcome, AuthorityOutcome::Denied);
    }

    // M52 — peer review gate tests

    #[test]
    fn peer_review_gate_requires_min_reviewers() {
        let mut gate = PeerReviewGate::new(2);
        assert!(!gate.gate_passed("prop-1"));

        gate.submit(PeerReview {
            reviewer_id: "r1".into(),
            proposal_id: "prop-1".into(),
            passed: true,
            comment: "LGTM".into(),
        });
        assert!(!gate.gate_passed("prop-1"), "1 review < 2 required");

        gate.submit(PeerReview {
            reviewer_id: "r2".into(),
            proposal_id: "prop-1".into(),
            passed: true,
            comment: "Also LGTM".into(),
        });
        assert!(gate.gate_passed("prop-1"), "2 passing reviews → gate passed");
    }

    #[test]
    fn peer_review_gate_failed_review_blocks() {
        let mut gate = PeerReviewGate::new(2);
        gate.submit(PeerReview {
            reviewer_id: "r1".into(),
            proposal_id: "prop-2".into(),
            passed: true,
            comment: "ok".into(),
        });
        gate.submit(PeerReview {
            reviewer_id: "r2".into(),
            proposal_id: "prop-2".into(),
            passed: false, // one reviewer rejects
            comment: "issues found".into(),
        });
        assert!(!gate.gate_passed("prop-2"), "one failed review blocks gate");
    }

    #[test]
    fn peer_review_duplicate_not_counted() {
        let mut gate = PeerReviewGate::new(2);
        for _ in 0..5 {
            gate.submit(PeerReview {
                reviewer_id: "same-reviewer".into(),
                proposal_id: "prop-3".into(),
                passed: true,
                comment: "ok".into(),
            });
        }
        assert_eq!(gate.review_count("prop-3"), 1);
        assert!(!gate.gate_passed("prop-3"));
    }

    #[test]
    fn review_passes_requires_improvement() {
        let scores = ScoreComparison {
            before: QualityScores {
                clarity: 3,
                consistency: 3,
                conciseness: 3,
            },
            after: QualityScores {
                clarity: 4,
                consistency: 3,
                conciseness: 3,
            },
        };
        let review = ReviewResult {
            preserves_existing_semantics: true,
            no_new_runtime_behavior: true,
            no_weakened_authority_or_evidence: true,
            material_quality_improved: true,
            failure_case_supported: true,
            scores,
            explanation: Some("improved clarity".to_owned()),
            extra: Default::default(),
        };
        assert!(review_passes(&review));
    }
}
