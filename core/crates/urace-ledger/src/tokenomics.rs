//! Token unit definition and mint rules.
//!
//! Ported from `tokenomics.py` and `token_ledger.py`.
//!
//! # Constants
//! - `UNIT = 100_000_000` — 1 UCR token in base units (satoshi model, 8 decimals)
//! - `PEER_CAP = 50 * UNIT` — maximum balance per peer
//!
//! # Mint rule
//! Tokens are minted **only** when `score_delta > 0` at a quality gate pass.
//! This is the single valid earn path.
//!
//! # Lightning passthrough
//! UCR↔SAT conversion rate is 1:1 (settlement deferred to `urace-settlement`).

/// 1 token = 100_000_000 base units (8 decimal places, satoshi-style).
pub const UNIT: i64 = 100_000_000;

/// Maximum UCR balance per peer (50 tokens).
pub const PEER_CAP: i64 = 50 * UNIT;

/// UCR to Lightning satoshi conversion rate (1:1 passthrough).
pub const UCR_TO_SAT: i64 = 1;

/// Schema label — mirrors `token_ledger.py`'s `SCHEMA`.
pub const SCHEMA: &str = "urace-tokenomics-v1";

/// Returns `true` iff `score_delta > 0` — the **only** valid mint condition.
///
/// Called at quality gate pass. Any path that mints without a positive
/// score_delta violates the earn invariant.
pub fn mint_on_qualified_acceptance(score_delta: i64) -> bool {
    score_delta > 0
}

/// Compute the mint amount for a single qualified acceptance.
///
/// Returns the number of base units to credit, clamped to `[1, PEER_CAP]`.
/// Returns `None` (no mint) if `score_delta <= 0`.
pub fn mint_amount(score_delta: i64) -> Option<i64> {
    if score_delta <= 0 {
        return None;
    }
    // Simple 1:1 score-delta → base-unit mapping, clamped.
    let amount = score_delta.clamp(1, PEER_CAP);
    Some(amount)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unit_constant() {
        assert_eq!(UNIT, 100_000_000);
    }

    #[test]
    fn peer_cap_constant() {
        assert_eq!(PEER_CAP, 50 * UNIT);
    }

    #[test]
    fn mint_on_positive_delta() {
        assert!(mint_on_qualified_acceptance(1));
        assert!(mint_on_qualified_acceptance(42));
        assert!(mint_on_qualified_acceptance(i64::MAX));
    }

    #[test]
    fn no_mint_on_zero_or_negative() {
        assert!(!mint_on_qualified_acceptance(0));
        assert!(!mint_on_qualified_acceptance(-1));
        assert!(!mint_on_qualified_acceptance(i64::MIN));
    }

    #[test]
    fn mint_amount_none_for_non_positive() {
        assert!(mint_amount(0).is_none());
        assert!(mint_amount(-5).is_none());
    }

    #[test]
    fn mint_amount_positive() {
        assert_eq!(mint_amount(1), Some(1));
        assert_eq!(mint_amount(100), Some(100));
    }

    #[test]
    fn mint_amount_clamped_to_peer_cap() {
        assert_eq!(mint_amount(PEER_CAP + 1), Some(PEER_CAP));
    }
}
