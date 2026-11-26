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

// ---------------------------------------------------------------------------
// M41 — Supply schedule enforcement
// ---------------------------------------------------------------------------

/// Maximum total UCR that may be minted across all peers in a single epoch.
///
/// `0` means uncapped (default during bootstrap). Set via governance vote.
pub const DEFAULT_EPOCH_SUPPLY_CAP: i64 = 0;

/// Returns `true` if minting `amount` more UCR would not breach `epoch_cap`.
///
/// If `epoch_cap == 0` the protocol is uncapped and this always returns `true`.
pub fn within_epoch_supply_cap(epoch_minted_so_far: i64, amount: i64, epoch_cap: i64) -> bool {
    if epoch_cap == 0 {
        return true;
    }
    epoch_minted_so_far + amount <= epoch_cap
}

/// Returns `true` iff crediting `amount` to a peer with `balance` would not
/// exceed `PEER_CAP`.
pub fn within_peer_cap(balance: i64, amount: i64) -> bool {
    balance + amount <= PEER_CAP
}

// ── M42 — Peer-cap cliff smoothing ───────────────────────────────────────────

/// Soft-capped mint amount with linear tapering in the top 20% of PEER_CAP.
///
/// - Below 80% of PEER_CAP: returns `requested_amount` clamped to remaining headroom.
/// - 80–100%: applies a linear taper from 100% → 50% of requested amount.
/// - At or beyond PEER_CAP: returns 0.
pub fn soft_capped_mint(balance_ucr: i64, requested_amount: i64) -> i64 {
    if balance_ucr >= PEER_CAP {
        return 0;
    }
    let headroom = PEER_CAP - balance_ucr;
    let threshold = PEER_CAP * 4 / 5; // 80%
    if balance_ucr < threshold {
        return requested_amount.min(headroom).max(0);
    }
    // In the top 20%: taper linearly from 1.0 at threshold to 0.5 at PEER_CAP.
    let top_band = (PEER_CAP - threshold) as f64; // = PEER_CAP / 5
    let pos_in_band = (balance_ucr - threshold) as f64;
    let fraction_used = (pos_in_band / top_band).min(1.0);
    let taper = (1.0 - fraction_used * 0.5).max(0.0);
    let tapered = (requested_amount as f64 * taper) as i64;
    tapered.min(headroom).max(0)
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

    // M41 tests

    #[test]
    fn epoch_cap_zero_always_allowed() {
        assert!(within_epoch_supply_cap(0, 1_000_000, 0));
        assert!(within_epoch_supply_cap(i64::MAX - 1, 1, 0));
    }

    #[test]
    fn epoch_cap_enforced_when_nonzero() {
        let cap = 500 * UNIT;
        // Right at the cap: allowed
        assert!(within_epoch_supply_cap(400 * UNIT, 100 * UNIT, cap));
        // One base unit over: denied
        assert!(!within_epoch_supply_cap(400 * UNIT, 100 * UNIT + 1, cap));
        // Already at cap, any further mint denied
        assert!(!within_epoch_supply_cap(cap, 1, cap));
    }

    // M42 — soft cap tests

    #[test]
    fn soft_cap_below_80_percent_full_amount() {
        // Balance at 50% of PEER_CAP — no taper
        let balance = PEER_CAP / 2;
        let result = soft_capped_mint(balance, 1_000_000);
        assert_eq!(result, 1_000_000);
    }

    #[test]
    fn soft_cap_at_90_percent_tapered() {
        // Balance at 90% — fraction_used = 0.5, taper = 0.75
        let balance = PEER_CAP * 9 / 10;
        let requested = 1_000_000i64;
        let result = soft_capped_mint(balance, requested);
        // taper = 1 - 0.5*0.5 = 0.75; tapered = 750000; headroom = PEER_CAP/10
        assert!(result > 0 && result < requested, "result {result} should be between 0 and {requested}");
        assert!(result <= PEER_CAP - balance);
    }

    #[test]
    fn soft_cap_at_100_percent_zero() {
        assert_eq!(soft_capped_mint(PEER_CAP, 1_000_000), 0);
        assert_eq!(soft_capped_mint(PEER_CAP + 1, 1_000_000), 0);
    }

    #[test]
    fn peer_cap_enforcement() {
        // Balance + amount exactly equals PEER_CAP: allowed
        assert!(within_peer_cap(0, PEER_CAP));
        // One over: denied
        assert!(!within_peer_cap(0, PEER_CAP + 1));
        assert!(!within_peer_cap(PEER_CAP, 1));
        // Zero mint always allowed (vacuously)
        assert!(within_peer_cap(PEER_CAP, 0));
    }
}
