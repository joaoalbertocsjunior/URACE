//! M34 — Reputation source diversity.
//!
//! Reputation sourced entirely from one /24 subnet is discounted by 50%.
//! Uses the same `subnet24_from_endpoint` helper as the Kademlia module.

use crate::kademlia::subnet24_from_endpoint;

/// If more than this fraction of endorsers come from a single /24 subnet,
/// apply the discount.
pub const MAX_SUBNET_FRACTION: f64 = 0.5;

/// Multiplicative discount applied when the dominant subnet exceeds
/// `MAX_SUBNET_FRACTION`.
pub const DISCOUNT_FACTOR: f64 = 0.5;

/// Compute the discount multiplier based on endorser subnet diversity.
///
/// `endorsers` is a slice of `(peer_endpoint, weight)` pairs. The weight
/// is not used for the diversity check itself — only the fraction of
/// endorsers from the dominant /24 subnet matters.
///
/// Returns `DISCOUNT_FACTOR` (0.5) if the dominant subnet contributes more
/// than `MAX_SUBNET_FRACTION` of endorsers; otherwise returns `1.0`.
pub fn diversity_discount(endorsers: &[(&str, f64)]) -> f64 {
    if endorsers.is_empty() {
        return 1.0;
    }

    // Count endorsers per /24 subnet (unparseable endpoints fall into a None bucket).
    let mut subnet_counts: std::collections::HashMap<Option<[u8; 3]>, usize> =
        std::collections::HashMap::new();

    for &(endpoint, _weight) in endorsers {
        let key = subnet24_from_endpoint(endpoint).map(|s| s.0);
        *subnet_counts.entry(key).or_insert(0) += 1;
    }

    let total = endorsers.len();
    let max_count = subnet_counts.values().copied().max().unwrap_or(0);
    let dominant_fraction = max_count as f64 / total as f64;

    if dominant_fraction > MAX_SUBNET_FRACTION {
        DISCOUNT_FACTOR
    } else {
        1.0
    }
}

/// Apply subnet diversity discount to a raw reputation score.
pub fn adjusted_reputation(raw_score: f64, endorsers: &[(&str, f64)]) -> f64 {
    raw_score * diversity_discount(endorsers)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_same_subnet_discounted() {
        // 4 endorsers all from 1.2.3.x → 100% from same /24 → discount
        let endorsers = [
            ("1.2.3.1:9000", 1.0),
            ("1.2.3.2:9000", 1.0),
            ("1.2.3.3:9000", 1.0),
            ("1.2.3.4:9000", 1.0),
        ];
        let d = diversity_discount(&endorsers);
        assert!(
            (d - DISCOUNT_FACTOR).abs() < 1e-10,
            "all same subnet must yield DISCOUNT_FACTOR={DISCOUNT_FACTOR}"
        );
        // Adjusted reputation must be halved.
        let adj = adjusted_reputation(1.0, &endorsers);
        assert!((adj - 0.5).abs() < 1e-10);
    }

    #[test]
    fn diverse_subnets_no_discount() {
        // 4 endorsers from 4 different /24s → 25% each → no discount
        let endorsers = [
            ("1.2.3.1:9000", 1.0),
            ("10.0.0.1:9000", 1.0),
            ("172.16.0.1:9000", 1.0),
            ("192.168.1.1:9000", 1.0),
        ];
        let d = diversity_discount(&endorsers);
        assert!(
            (d - 1.0).abs() < 1e-10,
            "diverse subnets must yield no discount (1.0)"
        );
    }

    #[test]
    fn borderline_threshold() {
        // Exactly 50% from same subnet — not strictly greater, so no discount.
        let endorsers = [
            ("1.2.3.1:9000", 1.0),
            ("1.2.3.2:9000", 1.0),
            ("10.0.0.1:9000", 1.0),
            ("10.0.1.1:9000", 1.0),
        ];
        // 2/4 = 0.5, which is NOT > 0.5, so discount must NOT apply.
        let d = diversity_discount(&endorsers);
        assert!(
            (d - 1.0).abs() < 1e-10,
            "exactly 50% must not trigger discount (threshold is strictly greater)"
        );
    }
}
