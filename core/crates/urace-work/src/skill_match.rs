//! Executor skill matching — qualification-verified domain routing.
//!
//! # Design
//! Skill claims are only valid when backed by a passing qualification score.
//! An executor may declare any domain, but `SkillRouter` only uses *verified*
//! skills (those with `qualification_score >= SKILL_VERIFICATION_THRESHOLD`).
//! This closes the P02 self-attestation problem.
//!
//! # Invariants
//! - `MAX_SKILLS_PER_EXECUTOR` caps the number of skill claims per executor to
//!   limit gaming via broad skill declarations.
//! - Duplicate domain registrations for the same executor are rejected.
//! - `SKILL_MATCH_BONUS` is applied as a multiplier, not an additive bonus, so
//!   it scales with bid quality.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;

// ── Constants ─────────────────────────────────────────────────────────────────

/// Minimum qualification score for a skill claim to be considered verified.
pub const SKILL_VERIFICATION_THRESHOLD: f64 = 0.65;

/// Score multiplier applied to a bid when the executor has a verified skill
/// matching the work domain.
pub const SKILL_MATCH_BONUS: f64 = 1.5;

/// Maximum number of skill claims an executor may register.
pub const MAX_SKILLS_PER_EXECUTOR: usize = 10;

// ── Well-known domain constants ───────────────────────────────────────────────

pub const SKILL_CODE_REVIEW: &str = "code-review";
pub const SKILL_NLP: &str = "nlp";
pub const SKILL_MATH: &str = "math";
pub const SKILL_SECURITY: &str = "security";
pub const SKILL_DATA: &str = "data";

// ── SkillDomain ───────────────────────────────────────────────────────────────

/// A string tag identifying a work domain.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SkillDomain(pub String);

impl SkillDomain {
    pub fn new(s: impl Into<String>) -> Self {
        SkillDomain(s.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::fmt::Display for SkillDomain {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        self.0.fmt(f)
    }
}

// ── SkillClaim ────────────────────────────────────────────────────────────────

/// A skill claim made by an executor for a particular domain.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillClaim {
    pub executor_peer_id: String,
    pub domain: String,
    /// Must be `>= SKILL_VERIFICATION_THRESHOLD` for the claim to be active.
    pub qualification_score: f64,
    pub declared_at_secs: u64,
    /// Set to `true` when `qualification_score >= SKILL_VERIFICATION_THRESHOLD`.
    pub verified: bool,
}

// ── SkillClaimError ───────────────────────────────────────────────────────────

#[derive(Debug, Error, PartialEq, Eq)]
pub enum SkillClaimError {
    #[error("executor already has {count} skill claims (max {max})")]
    TooManySkills { count: usize, max: usize },

    #[error("executor already has a claim for domain: {0}")]
    DuplicateDomain(String),
}

// ── SkillRegistry ─────────────────────────────────────────────────────────────

/// In-memory store of skill claims, keyed by executor peer ID then domain.
#[derive(Debug, Default)]
pub struct SkillRegistry {
    /// executor_peer_id → (domain → SkillClaim)
    claims: parking_lot::RwLock<HashMap<String, HashMap<String, SkillClaim>>>,
}

impl SkillRegistry {
    pub fn new() -> Self {
        SkillRegistry::default()
    }

    /// Register a skill claim for an executor.
    ///
    /// Enforces `MAX_SKILLS_PER_EXECUTOR` and rejects duplicate domains.
    /// Sets `verified = qualification_score >= SKILL_VERIFICATION_THRESHOLD`.
    pub fn register_claim(
        &self,
        executor_peer_id: &str,
        domain: &str,
        qualification_score: f64,
        now_secs: u64,
    ) -> Result<SkillClaim, SkillClaimError> {
        let mut map = self.claims.write();
        let executor_map = map.entry(executor_peer_id.to_owned()).or_default();

        if executor_map.len() >= MAX_SKILLS_PER_EXECUTOR {
            return Err(SkillClaimError::TooManySkills {
                count: executor_map.len(),
                max: MAX_SKILLS_PER_EXECUTOR,
            });
        }

        if executor_map.contains_key(domain) {
            return Err(SkillClaimError::DuplicateDomain(domain.to_owned()));
        }

        let verified = qualification_score >= SKILL_VERIFICATION_THRESHOLD;
        let claim = SkillClaim {
            executor_peer_id: executor_peer_id.to_owned(),
            domain: domain.to_owned(),
            qualification_score,
            declared_at_secs: now_secs,
            verified,
        };
        executor_map.insert(domain.to_owned(), claim.clone());
        Ok(claim)
    }

    /// Return all *verified* skill claims for an executor.
    pub fn verified_skills(&self, executor_peer_id: &str) -> Vec<SkillClaim> {
        let map = self.claims.read();
        map.get(executor_peer_id)
            .map(|m| m.values().filter(|c| c.verified).cloned().collect())
            .unwrap_or_default()
    }

    /// Return `true` if the executor has a verified skill for `domain`.
    pub fn has_verified_skill(&self, executor_peer_id: &str, domain: &str) -> bool {
        let map = self.claims.read();
        map.get(executor_peer_id)
            .and_then(|m| m.get(domain))
            .map_or(false, |c| c.verified)
    }

    /// Return all verified claim counts per executor for a given domain.
    /// Used by `SkillConcentrationGuard`.
    pub(crate) fn verified_peers_for_domain(&self, domain: &str) -> Vec<String> {
        let map = self.claims.read();
        map.iter()
            .filter(|(_, domains)| {
                domains
                    .get(domain)
                    .map_or(false, |c| c.verified)
            })
            .map(|(peer_id, _)| peer_id.clone())
            .collect()
    }
}

// ── SkillMatchResult ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillMatchResult {
    pub executor_peer_id: String,
    pub domain: String,
    pub matched: bool,
    /// `SKILL_MATCH_BONUS` if matched, `1.0` otherwise.
    pub score_multiplier: f64,
}

// ── SkillRouter ───────────────────────────────────────────────────────────────

/// Routes work to executors based on verified skill claims.
#[derive(Debug, Clone)]
pub struct SkillRouter {
    registry: Arc<SkillRegistry>,
}

impl SkillRouter {
    pub fn new(registry: Arc<SkillRegistry>) -> Self {
        SkillRouter { registry }
    }

    /// Score a single bid, applying `SKILL_MATCH_BONUS` when the executor has
    /// a verified skill matching `work_domain`.
    ///
    /// Returns `(adjusted_score, SkillMatchResult)`.
    pub fn score_bid(
        &self,
        executor_peer_id: &str,
        work_domain: &str,
        base_bid_score: f64,
    ) -> (f64, SkillMatchResult) {
        let matched = self.registry.has_verified_skill(executor_peer_id, work_domain);
        let score_multiplier = if matched { SKILL_MATCH_BONUS } else { 1.0 };
        let adjusted = base_bid_score * score_multiplier;
        (
            adjusted,
            SkillMatchResult {
                executor_peer_id: executor_peer_id.to_owned(),
                domain: work_domain.to_owned(),
                matched,
                score_multiplier,
            },
        )
    }

    /// Select the best bid from a list of `(executor_peer_id, base_bid_score)`
    /// pairs, taking skill bonuses into account.
    ///
    /// Returns `None` if `bids` is empty.
    pub fn select_best_bid_with_skills(
        &self,
        bids: &[(String, f64)],
        work_domain: &str,
    ) -> Option<(String, f64)> {
        bids.iter()
            .map(|(peer_id, base)| {
                let (adjusted, _) = self.score_bid(peer_id, work_domain, *base);
                (peer_id.clone(), adjusted)
            })
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
    }
}

// ── DomainConcentrationStatus ─────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum DomainConcentrationStatus {
    /// Domain has healthy peer diversity.
    Healthy { peer_count: usize },
    /// One peer holds >50 % of the verified slots.
    Concentrated { dominant_peer: String, fraction: f64 },
    /// Only one verified peer in the domain.
    Monopoly { peer_id: String },
}

// ── SkillConcentrationGuard ───────────────────────────────────────────────────

/// Detects domain monopoly / concentration to prevent P2P power capture.
#[derive(Debug, Default)]
pub struct SkillConcentrationGuard;

impl SkillConcentrationGuard {
    pub fn new() -> Self {
        SkillConcentrationGuard
    }

    /// Inspect the registry and report the concentration status for `domain`.
    ///
    /// Because each peer may hold at most one verified claim per domain the
    /// "fraction" is simply that peer's presence share relative to total peers.
    /// Here we model a scenario where multiple skill slots can be granted
    /// (e.g. via reputation weighting); for now each peer counts as 1 slot.
    pub fn check_concentration(
        &self,
        registry: &SkillRegistry,
        domain: &str,
    ) -> DomainConcentrationStatus {
        let peers = registry.verified_peers_for_domain(domain);
        let total = peers.len();

        match total {
            0 => DomainConcentrationStatus::Healthy { peer_count: 0 },
            1 => DomainConcentrationStatus::Monopoly {
                peer_id: peers[0].clone(),
            },
            _ => {
                // With the current 1-slot-per-peer model the maximum fraction
                // any single peer can hold is 1/total.  A single peer can only
                // be "dominant" if total == 1 (handled above), so this branch
                // always reports Healthy — but the structure is in place for
                // future weighted-slot models.
                let fraction = 1.0_f64 / total as f64;
                if fraction > 0.5 {
                    // Safety net for future weighted models.
                    DomainConcentrationStatus::Concentrated {
                        dominant_peer: peers[0].clone(),
                        fraction,
                    }
                } else {
                    DomainConcentrationStatus::Healthy { peer_count: total }
                }
            }
        }
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn make_registry() -> Arc<SkillRegistry> {
        Arc::new(SkillRegistry::new())
    }

    // 1. Happy path: verified skill claim is accepted and detected.
    #[test]
    fn test_register_and_verify_skill() {
        let reg = make_registry();
        let claim = reg
            .register_claim("peer-1", SKILL_NLP, SKILL_VERIFICATION_THRESHOLD, 100)
            .expect("should succeed");
        assert!(claim.verified);
        assert!(reg.has_verified_skill("peer-1", SKILL_NLP));
    }

    // 2. Verification threshold enforcement: score below threshold → not verified.
    #[test]
    fn test_below_threshold_not_verified() {
        let reg = make_registry();
        let claim = reg
            .register_claim("peer-2", SKILL_MATH, 0.60, 100)
            .expect("should succeed");
        assert!(!claim.verified, "score below threshold must not be verified");
        assert!(!reg.has_verified_skill("peer-2", SKILL_MATH));
    }

    // 3. Duplicate domain rejection.
    #[test]
    fn test_duplicate_domain_rejected() {
        let reg = make_registry();
        reg.register_claim("peer-3", SKILL_CODE_REVIEW, 0.9, 100)
            .expect("first claim should succeed");
        let err = reg
            .register_claim("peer-3", SKILL_CODE_REVIEW, 0.95, 200)
            .expect_err("duplicate should fail");
        assert_eq!(err, SkillClaimError::DuplicateDomain(SKILL_CODE_REVIEW.to_owned()));
    }

    // 4. MAX_SKILLS_PER_EXECUTOR cap.
    #[test]
    fn test_max_skills_cap() {
        let reg = make_registry();
        let domains = [
            "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9", "d10",
        ];
        for d in &domains {
            reg.register_claim("peer-4", d, 0.9, 0)
                .expect("should succeed up to cap");
        }
        let err = reg
            .register_claim("peer-4", "d11", 0.9, 0)
            .expect_err("should be rejected after cap");
        assert!(matches!(err, SkillClaimError::TooManySkills { count: 10, max: 10 }));
    }

    // 5. SkillRouter applies bonus for verified skill, not for unverified.
    #[test]
    fn test_router_skill_bonus() {
        let reg = make_registry();
        reg.register_claim("peer-5", SKILL_SECURITY, 0.9, 0)
            .expect("ok");
        let router = SkillRouter::new(reg.clone());

        let (adj, result) = router.score_bid("peer-5", SKILL_SECURITY, 1.0);
        assert!(result.matched);
        assert_eq!(adj, SKILL_MATCH_BONUS);

        // Unverified peer gets no bonus.
        let (adj2, result2) = router.score_bid("peer-5", SKILL_DATA, 1.0);
        assert!(!result2.matched);
        assert_eq!(adj2, 1.0);
    }

    // 6. select_best_bid_with_skills prefers the skilled executor.
    #[test]
    fn test_select_best_bid_prefers_skilled() {
        let reg = make_registry();
        reg.register_claim("specialist", SKILL_NLP, 0.8, 0)
            .expect("ok");
        let router = SkillRouter::new(reg);

        let bids = vec![
            ("generalist".to_owned(), 2.0_f64),
            ("specialist".to_owned(), 1.5_f64),
        ];
        let (winner, score) = router
            .select_best_bid_with_skills(&bids, SKILL_NLP)
            .expect("should have winner");
        assert_eq!(winner, "specialist");
        assert!((score - 1.5 * SKILL_MATCH_BONUS).abs() < 1e-10);
    }

    // 7. Concentration detection: single peer → Monopoly.
    #[test]
    fn test_monopoly_detection() {
        let reg = SkillRegistry::new();
        reg.register_claim("solo", SKILL_MATH, 0.9, 0).expect("ok");
        let guard = SkillConcentrationGuard::new();
        let status = guard.check_concentration(&reg, SKILL_MATH);
        assert_eq!(
            status,
            DomainConcentrationStatus::Monopoly {
                peer_id: "solo".to_owned()
            }
        );
    }

    // 8. Concentration detection: multiple peers → Healthy.
    #[test]
    fn test_healthy_domain() {
        let reg = SkillRegistry::new();
        reg.register_claim("p1", SKILL_DATA, 0.9, 0).expect("ok");
        reg.register_claim("p2", SKILL_DATA, 0.8, 0).expect("ok");
        reg.register_claim("p3", SKILL_DATA, 0.7, 0).expect("ok");
        let guard = SkillConcentrationGuard::new();
        let status = guard.check_concentration(&reg, SKILL_DATA);
        assert_eq!(
            status,
            DomainConcentrationStatus::Healthy { peer_count: 3 }
        );
    }

    // 9. Exploit prevention: unverified claims do not influence routing.
    #[test]
    fn test_unverified_claim_does_not_route() {
        let reg = make_registry();
        // Register a claim with score just below threshold — attacker trying to
        // self-attest without proper qualification.
        reg.register_claim("attacker", SKILL_SECURITY, 0.64, 0)
            .expect("registration is accepted but not verified");
        let router = SkillRouter::new(reg);
        let (adj, result) = router.score_bid("attacker", SKILL_SECURITY, 10.0);
        assert!(!result.matched, "below-threshold claim must not match");
        assert_eq!(adj, 10.0, "no bonus should be applied");
    }

    // 10. select_best_bid_with_skills on empty bids returns None.
    #[test]
    fn test_select_best_bid_empty() {
        let reg = make_registry();
        let router = SkillRouter::new(reg);
        assert!(router
            .select_best_bid_with_skills(&[], SKILL_CODE_REVIEW)
            .is_none());
    }
}
