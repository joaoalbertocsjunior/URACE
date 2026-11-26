//! M36 — Stake slashing for protocol violations.
//!
//! Computes and records slashing penalties for peers that violate the
//! URACE protocol.  Slash percentages are fixed by the security spec:
//! invalid work 10 %, protocol violation 25 %, fraud 50 %.

use serde::{Deserialize, Serialize};

// ── Slash rates ───────────────────────────────────────────────────────────────

/// Slash rate for submitting invalid work (10 %).
pub const SLASH_RATE_INVALID_WORK: f64 = 0.10;

/// Slash rate for a general protocol violation (25 %).
pub const SLASH_RATE_PROTOCOL_VIOLATION: f64 = 0.25;

/// Slash rate when fraud is confirmed (50 %).
pub const SLASH_RATE_FRAUD: f64 = 0.50;

// ── SlashReason ───────────────────────────────────────────────────────────────

/// The reason a peer's stake is being slashed.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SlashReason {
    /// The delivered work failed validation (10 % slash).
    InvalidWork,
    /// A protocol rule was violated (25 % slash).
    ProtocolViolation,
    /// Fraud was detected (50 % slash).
    FraudDetected,
}

impl SlashReason {
    /// The fractional slash rate for this reason.
    pub fn rate(&self) -> f64 {
        match self {
            SlashReason::InvalidWork => SLASH_RATE_INVALID_WORK,
            SlashReason::ProtocolViolation => SLASH_RATE_PROTOCOL_VIOLATION,
            SlashReason::FraudDetected => SLASH_RATE_FRAUD,
        }
    }
}

// ── SlashRecord ───────────────────────────────────────────────────────────────

/// An immutable record of a slashing event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SlashRecord {
    pub peer_id: String,
    /// Stake balance at the time of slashing (before deduction).
    pub stake_ucr: i64,
    /// Amount removed from stake (always ≥ 0 and ≤ stake_ucr).
    pub amount_slashed: i64,
    pub reason: SlashReason,
    pub at_unix: u64,
}

// ── Pure computation helpers ──────────────────────────────────────────────────

/// Compute the slash amount (in UCR units) for a given `stake_ucr` and reason.
///
/// Returns `floor(stake_ucr × rate)`, clamped to `[0, stake_ucr]`.
/// A zero or negative stake always produces zero.
pub fn compute_slash(stake_ucr: i64, reason: &SlashReason) -> i64 {
    if stake_ucr <= 0 {
        return 0;
    }
    let amount = (stake_ucr as f64 * reason.rate()).floor() as i64;
    amount.min(stake_ucr).max(0)
}

/// Apply a slash: return `(remaining_stake, SlashRecord)`.
///
/// `at_unix` is the UNIX timestamp to stamp the record.
pub fn apply_slash(
    peer_id: impl Into<String>,
    stake_ucr: i64,
    reason: SlashReason,
    at_unix: u64,
) -> (i64, SlashRecord) {
    let amount_slashed = compute_slash(stake_ucr, &reason);
    let remaining = stake_ucr.saturating_sub(amount_slashed).max(0);
    let record = SlashRecord {
        peer_id: peer_id.into(),
        stake_ucr,
        amount_slashed,
        reason,
        at_unix,
    };
    (remaining, record)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_work_slashes_ten_percent() {
        let slashed = compute_slash(1_000, &SlashReason::InvalidWork);
        assert_eq!(slashed, 100, "10% of 1000 = 100");
    }

    #[test]
    fn protocol_violation_slashes_twenty_five_percent() {
        let slashed = compute_slash(1_000, &SlashReason::ProtocolViolation);
        assert_eq!(slashed, 250, "25% of 1000 = 250");
    }

    #[test]
    fn fraud_slashes_fifty_percent() {
        let slashed = compute_slash(1_000, &SlashReason::FraudDetected);
        assert_eq!(slashed, 500, "50% of 1000 = 500");
    }

    #[test]
    fn slash_never_exceeds_stake() {
        // With an artificially high rate (we just test the boundary).
        // Using FraudDetected (50%) on a stake of 1 → 0 slashed (floor(0.5) = 0).
        let slashed = compute_slash(1, &SlashReason::FraudDetected);
        assert!(slashed <= 1, "slash must not exceed stake");
    }

    #[test]
    fn zero_stake_produces_zero_slash() {
        assert_eq!(compute_slash(0, &SlashReason::FraudDetected), 0);
        assert_eq!(compute_slash(0, &SlashReason::InvalidWork), 0);
        assert_eq!(compute_slash(0, &SlashReason::ProtocolViolation), 0);
    }

    #[test]
    fn negative_stake_produces_zero_slash() {
        assert_eq!(compute_slash(-100, &SlashReason::FraudDetected), 0);
    }

    #[test]
    fn apply_slash_returns_correct_remaining_and_record() {
        let (remaining, record) = apply_slash("peer-x", 2_000, SlashReason::ProtocolViolation, 99_000);
        assert_eq!(record.amount_slashed, 500, "25% of 2000 = 500");
        assert_eq!(remaining, 1_500, "2000 - 500 = 1500");
        assert_eq!(record.peer_id, "peer-x");
        assert_eq!(record.stake_ucr, 2_000);
        assert_eq!(record.at_unix, 99_000);
    }
}
