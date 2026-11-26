//! M50 — Qualification score discounting.
//!
//! When a peer's qualification trial is conducted under uncertain or adversarial
//! conditions, the resulting score must be discounted before use in settlement.
//!
//! Discount factors:
//! - `self_reported`: 0.7 (self-attestation penalised)
//! - `single_evaluator`: 0.85 (non-consensus evaluation)
//! - `under_appeal`: 0.5 (score frozen at half pending appeal resolution)
//! - `no_delivery_proof`: 0.0 (no proof → zero score)

/// Flags that modify the effective qualification score.
#[derive(Debug, Clone, Default)]
pub struct ScoreDiscountFlags {
    /// Score was self-reported by the executor without independent verification.
    pub self_reported: bool,
    /// Only a single evaluator assessed the work (no multi-evaluator consensus).
    pub single_evaluator: bool,
    /// An appeal is currently active for this work item.
    pub under_appeal: bool,
    /// No delivery proof was registered for this work item.
    pub no_delivery_proof: bool,
}

/// Apply all active discount factors to `raw_score` ∈ [0.0, 1.0].
///
/// Discount factors are multiplicative and applied in order.
/// Returns 0.0 when `no_delivery_proof` is set regardless of other flags.
pub fn apply_discounts(raw_score: f64, flags: &ScoreDiscountFlags) -> f64 {
    if flags.no_delivery_proof {
        return 0.0;
    }
    let mut score = raw_score.clamp(0.0, 1.0);
    if flags.self_reported {
        score *= 0.70;
    }
    if flags.single_evaluator {
        score *= 0.85;
    }
    if flags.under_appeal {
        score *= 0.50;
    }
    score
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_flags_returns_raw() {
        let flags = ScoreDiscountFlags::default();
        let result = apply_discounts(0.9, &flags);
        assert!((result - 0.9).abs() < 1e-9);
    }

    #[test]
    fn no_delivery_proof_zeroes_score() {
        let flags = ScoreDiscountFlags { no_delivery_proof: true, ..Default::default() };
        assert_eq!(apply_discounts(1.0, &flags), 0.0);
    }

    #[test]
    fn self_reported_applies_70pct_discount() {
        let flags = ScoreDiscountFlags { self_reported: true, ..Default::default() };
        let result = apply_discounts(1.0, &flags);
        assert!((result - 0.70).abs() < 1e-9);
    }

    #[test]
    fn multiple_flags_compound() {
        let flags = ScoreDiscountFlags {
            self_reported: true,
            single_evaluator: true,
            ..Default::default()
        };
        let result = apply_discounts(1.0, &flags);
        // 0.70 * 0.85 = 0.595
        assert!((result - 0.595).abs() < 1e-6, "result={result}");
    }

    #[test]
    fn under_appeal_halves_score() {
        let flags = ScoreDiscountFlags { under_appeal: true, ..Default::default() };
        let result = apply_discounts(0.8, &flags);
        assert!((result - 0.4).abs() < 1e-9);
    }
}
