//! Ledger economics — fee calculation, complexity scoring, distribution rules.
//!
//! Ported from `ledger_economics.py`. All amounts are in base units (1 UCR = UNIT).
//! UNIT = 100_000_000 (8 decimal places, satoshi model).

use crate::credit_ledger::UNIT;

/// Complexity score in [1.0, ∞).
/// Derived from lines-of-code, dependency count, and test count.
pub fn feature_complexity_score(loc: u64, dependency_count: u64, test_count: u64) -> f64 {
    let interface_symbols_approx = loc / 5;
    1.0 + f64::log2(
        1.0 + interface_symbols_approx as f64 / 10.0
            + dependency_count as f64
            + test_count as f64 * 3.0,
    )
}

/// Minimum borrow cost in base units. Never below UNIT/10_000 (0.0001 token).
pub fn feature_borrow_cost_units(loc: u64, dependency_count: u64, test_count: u64) -> i64 {
    let score = feature_complexity_score(loc, dependency_count, test_count);
    let raw = (score * UNIT as f64 / 10.0) as i64;
    raw.max(UNIT / 10_000)
}

/// Wilson lower bound at 90% confidence (z=1.645).
pub fn wilson_lower(successes: u64, total: u64) -> f64 {
    if total == 0 {
        return 0.0;
    }
    let z = 1.645_f64;
    let p = successes as f64 / total as f64;
    let n = total as f64;
    let centre = p + z * z / (2.0 * n);
    let spread = z * f64::sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n);
    let denom = 1.0 + z * z / n;
    ((centre - spread) / denom).max(0.0)
}

/// Borrow cost weighted by feature reputation (Wilson lower-bound).
pub fn feature_borrow_cost_with_rep(
    loc: u64,
    dependency_count: u64,
    test_count: u64,
    quality_verifications: u64,
    total_adoptions: u64,
) -> i64 {
    let score = feature_complexity_score(loc, dependency_count, test_count);
    let rep_rate = wilson_lower(quality_verifications, total_adoptions);
    let rep_multiplier = 0.5 + rep_rate;
    let base = (score * UNIT as f64 / 10.0) as i64;
    ((base as f64 * rep_multiplier) as i64).max(UNIT / 10_000)
}

/// Soft quadratic supply pressure multiplier against physics-bounded ceiling.
pub fn supply_pressure_multiplier(total_supply_units: i64, estimated_network_size: u64) -> f64 {
    let physics_max = (crate::tokenomics::PEER_CAP * 10)
        .max(crate::tokenomics::PEER_CAP * estimated_network_size.max(1) as i64);
    let cap = physics_max.max(1) as f64;
    let ratio = (total_supply_units as f64 / cap).min(1.0);
    (1.0 - ratio.powi(2)).max(0.001)
}

/// Quality-dynamic distribution fee for the feature's distributor.
pub const DISTRIBUTION_FEE_MIN: f64 = 0.02;
pub const DISTRIBUTION_FEE_MAX: f64 = 0.10;
pub const DISTRIBUTION_FEE_DEFAULT: f64 = 0.05;

pub fn distribution_fee_units(borrow_cost: i64, quality_score: Option<f64>) -> i64 {
    let frac = match quality_score {
        None => DISTRIBUTION_FEE_DEFAULT,
        Some(q) => q
            .mul_add(DISTRIBUTION_FEE_MAX, 0.0)
            .clamp(DISTRIBUTION_FEE_MIN, DISTRIBUTION_FEE_MAX),
    };
    ((borrow_cost as f64 * frac) as i64).max(0)
}

/// Maximum tokens earnable per borrow event.
pub fn feature_earn_cap_units(loc: u64, dependency_count: u64, test_count: u64) -> i64 {
    let score = feature_complexity_score(loc, dependency_count, test_count);
    ((score * UNIT as f64) as i64).min(10 * UNIT)
}

/// Per-epoch decay rate (1%).
pub const EPOCH_DECAY_RATE: f64 = 0.01;

/// Compute epoch decay amount for a balance above cap.
/// Returns 0 if balance <= cap.
pub fn epoch_decay_amount(balance: i64, cap: i64) -> i64 {
    if balance <= cap {
        return 0;
    }
    let excess = balance - cap;
    ((excess as f64 * EPOCH_DECAY_RATE) as i64).max(0)
}

/// Combined reputation F-score for work request bid ranking.
pub fn combined_rep_score(
    delivery_wilson: f64,
    quality_wilson: f64,
    beta: f64,
    min_delivery_to_bid: f64,
) -> f64 {
    if delivery_wilson < min_delivery_to_bid {
        return 0.0;
    }
    let q = quality_wilson.max(0.05);
    let d = delivery_wilson;
    let beta2 = beta * beta;
    let denom = beta2 * q + d;
    if denom == 0.0 {
        return 0.0;
    }
    (1.0 + beta2) * (d * q) / denom
}

/// Central economics struct (stateless — all methods are functions).
pub struct LedgerEconomics;

impl LedgerEconomics {
    pub const UNIT: i64 = UNIT;
    pub const PEER_CAP: i64 = crate::credit_ledger::PEER_CAP;

    pub fn borrow_cost(loc: u64, dep: u64, tests: u64) -> i64 {
        feature_borrow_cost_units(loc, dep, tests)
    }

    pub fn complexity_score(loc: u64, dep: u64, tests: u64) -> f64 {
        feature_complexity_score(loc, dep, tests)
    }

    pub fn distribution_fee(borrow_cost: i64, quality_score: Option<f64>) -> i64 {
        distribution_fee_units(borrow_cost, quality_score)
    }

    pub fn decay_amount(balance: i64, cap: i64) -> i64 {
        epoch_decay_amount(balance, cap)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn complexity_minimum() {
        // Zero inputs → score = 1.0
        let s = feature_complexity_score(0, 0, 0);
        assert!((s - 1.0).abs() < 1e-6);
    }

    #[test]
    fn complexity_grows_with_inputs() {
        let s1 = feature_complexity_score(100, 5, 10);
        let s2 = feature_complexity_score(0, 0, 0);
        assert!(s1 > s2);
    }

    #[test]
    fn borrow_cost_minimum_floor() {
        // With zero inputs complexity=1.0 → cost = 1.0 * UNIT / 10 = UNIT/10,
        // which is >> floor (UNIT/10_000). Floor only binds for sub-unit complexity.
        let cost = feature_borrow_cost_units(0, 0, 0);
        assert!(cost >= UNIT / 10_000, "cost must be >= floor");
        // The actual value should be UNIT/10 (complexity=1 → score/10)
        assert_eq!(
            cost,
            (feature_complexity_score(0, 0, 0) * UNIT as f64 / 10.0) as i64
        );
    }

    #[test]
    fn wilson_lower_zero_total() {
        assert_eq!(wilson_lower(0, 0), 0.0);
    }

    #[test]
    fn wilson_lower_all_success() {
        // 100 successes out of 100: should be close to 1 but slightly below
        let w = wilson_lower(100, 100);
        assert!(w > 0.95 && w <= 1.0);
    }

    #[test]
    fn distribution_fee_range() {
        let cost = UNIT;
        let fee = distribution_fee_units(cost, Some(0.5));
        assert!(fee >= 0);
        assert!(fee <= cost);
    }

    #[test]
    fn epoch_decay_above_cap() {
        let decay = epoch_decay_amount(60 * UNIT, 50 * UNIT);
        assert!(decay > 0);
    }

    #[test]
    fn epoch_decay_at_cap() {
        assert_eq!(epoch_decay_amount(50 * UNIT, 50 * UNIT), 0);
    }

    #[test]
    fn combined_rep_below_delivery_threshold() {
        assert_eq!(combined_rep_score(0.1, 0.9, 1.5, 0.30), 0.0);
    }

    #[test]
    fn supply_pressure_at_zero() {
        let m = supply_pressure_multiplier(0, 1);
        assert!((m - 1.0).abs() < 1e-6);
    }
}
