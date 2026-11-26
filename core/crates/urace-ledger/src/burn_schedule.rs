//! M38 — Gradual cap burn schedule.
//!
//! Each daemon cycle, a peer's balance is reduced by a tier-dependent fraction.
//! Balances below 40 UNIT are exempt. Higher tiers carry steeper burn rates to
//! discourage hoarding beyond the protocol-defined peer cap.
//!
//! All amounts are in **base UCR units** (not UNIT tokens).

use crate::tokenomics::UNIT;

/// A single burn tier: balances ≥ `floor_ucr` burn at `rate` per cycle.
pub struct BurnTier {
    /// Minimum balance (inclusive) for this tier, in base UCR units.
    pub floor_ucr: i64,
    /// Fraction of the balance to burn each daemon cycle.
    pub rate: f64,
}

/// Returns the ordered list of burn tiers (lowest floor first).
///
/// | Range           | Rate |
/// |-----------------|------|
/// | 0 – 40 UNIT     | 0 %  |
/// | 40 – 50 UNIT    | 0.1 %|
/// | 50 – 75 UNIT    | 0.5 %|
/// | 75 – 100 UNIT   | 2.0 %|
/// | ≥ 100 UNIT      | 5.0 %|
pub fn burn_tiers() -> Vec<BurnTier> {
    vec![
        BurnTier { floor_ucr: 0,          rate: 0.000 }, // 0–40 UNIT: no burn
        BurnTier { floor_ucr: 40 * UNIT,  rate: 0.001 }, // 40–50 UNIT: 0.1 %
        BurnTier { floor_ucr: 50 * UNIT,  rate: 0.005 }, // 50–75 UNIT: 0.5 %
        BurnTier { floor_ucr: 75 * UNIT,  rate: 0.020 }, // 75–100 UNIT: 2.0 %
        BurnTier { floor_ucr: 100 * UNIT, rate: 0.050 }, // ≥100 UNIT: 5.0 %
    ]
}

/// Compute the burn amount for `balance_ucr` in one daemon cycle.
///
/// Returns `(burn_amount_base_units, tier_index)`.
/// Returns `(0, 0)` for non-positive balances.
pub fn burn_amount(balance_ucr: i64) -> (i64, usize) {
    if balance_ucr <= 0 {
        return (0, 0);
    }
    let tiers = burn_tiers();
    let mut tier_idx = 0usize;
    for (i, tier) in tiers.iter().enumerate() {
        if balance_ucr >= tier.floor_ucr {
            tier_idx = i;
        }
    }
    let rate = tiers[tier_idx].rate;
    let burn = (balance_ucr as f64 * rate) as i64;
    (burn, tier_idx)
}

/// Apply one burn cycle: returns `max(0, balance_ucr - burn)`.
pub fn apply_burn(balance_ucr: i64) -> i64 {
    let (burn, _) = burn_amount(balance_ucr);
    (balance_ucr - burn).max(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_burn_below_40_units() {
        // 39 UNIT is in tier 0 (rate = 0)
        let balance = 39 * UNIT;
        let (burn, idx) = burn_amount(balance);
        assert_eq!(idx, 0, "expected tier 0");
        assert_eq!(burn, 0, "expected no burn below 40 UNIT");
    }

    #[test]
    fn no_burn_on_zero_balance() {
        let (burn, _) = burn_amount(0);
        assert_eq!(burn, 0);
        // negative balance
        let (burn, _) = burn_amount(-1_000);
        assert_eq!(burn, 0);
    }

    #[test]
    fn burn_at_40_units() {
        // Exactly 40 UNIT → tier 1 (0.1 %)
        let balance = 40 * UNIT;
        let (burn, idx) = burn_amount(balance);
        assert_eq!(idx, 1, "expected tier 1");
        let expected = (balance as f64 * 0.001) as i64;
        assert_eq!(burn, expected);
    }

    #[test]
    fn burn_at_50_units() {
        // Exactly 50 UNIT → tier 2 (0.5 %)
        let balance = 50 * UNIT;
        let (burn, idx) = burn_amount(balance);
        assert_eq!(idx, 2, "expected tier 2");
        let expected = (balance as f64 * 0.005) as i64;
        assert_eq!(burn, expected);
    }

    #[test]
    fn burn_at_99_units() {
        // 99 UNIT → tier 3 (2.0 %) — just below the ≥100 threshold
        let balance = 99 * UNIT;
        let (burn, idx) = burn_amount(balance);
        assert_eq!(idx, 3, "expected tier 3");
        let expected = (balance as f64 * 0.020) as i64;
        assert_eq!(burn, expected);
    }

    #[test]
    fn burn_at_100_units() {
        // 100 UNIT → tier 4 (5.0 %)
        let balance = 100 * UNIT;
        let (burn, idx) = burn_amount(balance);
        assert_eq!(idx, 4, "expected tier 4");
        let expected = (balance as f64 * 0.050) as i64;
        assert_eq!(burn, expected);
    }

    #[test]
    fn burn_at_101_units() {
        // 101 UNIT → tier 4 (5.0 %)
        let balance = 101 * UNIT;
        let (burn, idx) = burn_amount(balance);
        assert_eq!(idx, 4);
        let expected = (balance as f64 * 0.050) as i64;
        assert_eq!(burn, expected);
    }

    #[test]
    fn apply_burn_does_not_go_negative() {
        // Pathological: even a tiny positive balance should not underflow
        assert!(apply_burn(1) >= 0);
        assert!(apply_burn(0) >= 0);
        assert!(apply_burn(-1_000_000) >= 0);
    }

    #[test]
    fn apply_burn_reduces_balance() {
        let balance = 50 * UNIT;
        let after = apply_burn(balance);
        assert!(after < balance, "burn should reduce balance");
    }
}
