//! Token economics constants and unit arithmetic for URACE.
//!
//! This crate is the single source of truth for `UNIT`, `PEER_CAP`,
//! `MINT_MIN_SCORE_DELTA`, and all UCR unit-arithmetic functions.
//! It has no ledger engine dependency — any crate can use these
//! constants without pulling the full ledger.
//!
//! `UNIT = 100_000_000` — one UCR expressed in raw base units (8 decimal places).
//! On-chain (EVM) scaling is 1:1 for now; `to_chain_units` / `from_chain_units`
//! are stubs for future 18-decimal EVM settlement.

use thiserror::Error;

/// One UCR expressed in raw base units (8 decimal places, same as `ledger_primitives.py`).
pub const UNIT: u64 = 100_000_000;

/// Maximum UCR balance per peer (50 tokens, expressed as i64 for signed arithmetic).
///
/// This is the single source of truth — previously duplicated in
/// `credit_ledger.rs` and `tokenomics.rs`.
pub const PEER_CAP: i64 = 50 * UNIT as i64;

/// Minimum `score_delta` required to trigger a mint.
///
/// Tokens are minted **only** when `score_delta > MINT_MIN_SCORE_DELTA`
/// at a quality gate pass. This is the single valid earn path.
pub const MINT_MIN_SCORE_DELTA: f64 = 0.0;

/// Errors returned by unit helper functions.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum UnitsError {
    #[error("overflow: result exceeds u64::MAX")]
    Overflow,
    #[error("underflow: insufficient balance ({balance} < {amount})")]
    InsufficientFunds { balance: u64, amount: u64 },
    #[error("parse error: {0}")]
    Parse(String),
}

// ── Display ──────────────────────────────────────────────────────────────────

/// Format `raw` base units as `"{whole}.{frac} UCR"` with 8 decimal places,
/// trailing zeros trimmed.
///
/// Examples:
/// ```
/// # use urace_economics::{to_display, UNIT};
/// assert_eq!(to_display(0),              "0 UCR");
/// assert_eq!(to_display(UNIT),           "1 UCR");
/// assert_eq!(to_display(UNIT / 2),       "0.5 UCR");
/// assert_eq!(to_display(150_000_000),    "1.5 UCR");
/// assert_eq!(to_display(100_000_001),    "1.00000001 UCR");
/// ```
pub fn to_display(raw: u64) -> String {
    let whole = raw / UNIT;
    let frac = raw % UNIT;
    if frac == 0 {
        format!("{whole} UCR")
    } else {
        // Build 8-digit zero-padded fraction, then trim trailing zeros.
        let frac_str = format!("{frac:08}");
        let trimmed = frac_str.trim_end_matches('0');
        format!("{whole}.{trimmed} UCR")
    }
}

/// Parse a string like `"1.5 UCR"`, `"1.5"`, `"0"`, or `"0.00000001"` into raw
/// base units.  Rejects strings whose integer part would overflow u64.
///
/// # Errors
/// Returns [`UnitsError::Parse`] for unparseable input.
/// Returns [`UnitsError::Overflow`] if the result would exceed `u64::MAX`.
pub fn from_display(s: &str) -> Result<u64, UnitsError> {
    // Strip optional " UCR" suffix (case-insensitive).
    let s = s.trim();
    let s = if let Some(stripped) = s.strip_suffix(" UCR").or_else(|| s.strip_suffix(" ucr")) {
        stripped.trim()
    } else {
        s
    };

    if let Some((whole_str, frac_str)) = s.split_once('.') {
        let whole: u64 = whole_str
            .parse()
            .map_err(|_| UnitsError::Parse(format!("invalid integer part: '{whole_str}'")))?;

        // Pad or truncate to exactly 8 decimal places.
        let frac_padded: String = if frac_str.len() <= 8 {
            format!("{frac_str:0<8}") // right-pad with zeros
        } else {
            frac_str[..8].to_string() // truncate beyond 8 decimals
        };
        let frac: u64 = frac_padded
            .parse()
            .map_err(|_| UnitsError::Parse(format!("invalid fractional part: '{frac_str}'")))?;

        // whole * UNIT + frac — check overflow at each step.
        let whole_units = whole.checked_mul(UNIT).ok_or(UnitsError::Overflow)?;
        whole_units.checked_add(frac).ok_or(UnitsError::Overflow)
    } else {
        // No decimal point — treat as whole UCR.
        let whole: u64 = s
            .parse()
            .map_err(|_| UnitsError::Parse(format!("cannot parse as integer: '{s}'")))?;
        whole.checked_mul(UNIT).ok_or(UnitsError::Overflow)
    }
}

// ── Chain unit conversion ────────────────────────────────────────────────────

/// Convert internal 8-decimal base units to EVM-compatible on-chain units.
///
/// Currently 1:1.  Reserved for future 18-decimal EVM scaling.
#[inline]
pub fn to_chain_units(raw: u64) -> u64 {
    raw
}

/// Convert EVM on-chain units back to internal 8-decimal base units.
///
/// Currently 1:1.  Reserved for future 18-decimal EVM scaling.
#[inline]
pub fn from_chain_units(chain: u64) -> u64 {
    chain
}

// ── Arithmetic ───────────────────────────────────────────────────────────────

/// Add `amount` to `balance`, returning the new balance.
///
/// # Errors
/// Returns [`UnitsError::Overflow`] if the result would exceed `u64::MAX`.
pub fn earn_units(balance: u64, amount: u64) -> Result<u64, UnitsError> {
    balance.checked_add(amount).ok_or(UnitsError::Overflow)
}

/// Subtract `amount` from `balance`, returning the new balance.
///
/// # Errors
/// Returns [`UnitsError::InsufficientFunds`] if `balance < amount`.
pub fn spend_units(balance: u64, amount: u64) -> Result<u64, UnitsError> {
    balance
        .checked_sub(amount)
        .ok_or(UnitsError::InsufficientFunds { balance, amount })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── PEER_CAP / MINT_MIN_SCORE_DELTA constants ─────────────────────────────

    #[test]
    fn peer_cap_is_fifty_units() {
        assert_eq!(PEER_CAP, 50 * UNIT as i64);
    }

    #[test]
    fn mint_min_score_delta_is_zero() {
        assert_eq!(MINT_MIN_SCORE_DELTA, 0.0);
    }

    // ── to_display ────────────────────────────────────────────────────────────

    #[test]
    fn display_zero() {
        assert_eq!(to_display(0), "0 UCR");
    }

    #[test]
    fn display_one_unit() {
        assert_eq!(to_display(UNIT), "1 UCR");
    }

    #[test]
    fn display_half_unit() {
        assert_eq!(to_display(UNIT / 2), "0.5 UCR");
    }

    #[test]
    fn display_one_and_half_units() {
        assert_eq!(to_display(150_000_000), "1.5 UCR");
    }

    #[test]
    fn display_smallest_fraction() {
        assert_eq!(to_display(1), "0.00000001 UCR");
    }

    #[test]
    fn display_large_value() {
        // 50 UCR (peer cap)
        assert_eq!(to_display(50 * UNIT), "50 UCR");
    }

    // ── from_display ──────────────────────────────────────────────────────────

    #[test]
    fn parse_with_ucr_suffix() {
        assert_eq!(from_display("1.5 UCR"), Ok(150_000_000));
    }

    #[test]
    fn parse_without_suffix() {
        assert_eq!(from_display("1.5"), Ok(150_000_000));
    }

    #[test]
    fn parse_integer_string() {
        assert_eq!(from_display("3"), Ok(3 * UNIT));
    }

    #[test]
    fn parse_zero() {
        assert_eq!(from_display("0"), Ok(0));
    }

    #[test]
    fn parse_fractional_zero() {
        assert_eq!(from_display("0.0"), Ok(0));
    }

    #[test]
    fn parse_smallest_fraction() {
        assert_eq!(from_display("0.00000001"), Ok(1));
    }

    #[test]
    fn parse_invalid_string() {
        assert!(matches!(
            from_display("not_a_number"),
            Err(UnitsError::Parse(_))
        ));
    }

    #[test]
    fn parse_overflow_very_large_whole() {
        // u64::MAX / UNIT ≈ 184_467_440_737, so 999_999_999_999 * UNIT overflows.
        assert_eq!(from_display("999999999999 UCR"), Err(UnitsError::Overflow));
    }

    // ── Round-trip: from_display(to_display(x)) == x ──────────────────────────

    #[test]
    fn round_trip_zero() {
        assert_eq!(from_display(&to_display(0)), Ok(0));
    }

    #[test]
    fn round_trip_one() {
        assert_eq!(from_display(&to_display(1)), Ok(1));
    }

    #[test]
    fn round_trip_unit() {
        assert_eq!(from_display(&to_display(UNIT)), Ok(UNIT));
    }

    #[test]
    fn round_trip_half_unit() {
        assert_eq!(from_display(&to_display(UNIT / 2)), Ok(UNIT / 2));
    }

    #[test]
    fn round_trip_large() {
        let v = u64::MAX / 2;
        assert_eq!(from_display(&to_display(v)), Ok(v));
    }

    // ── Chain unit stubs ──────────────────────────────────────────────────────

    #[test]
    fn chain_units_round_trip() {
        assert_eq!(from_chain_units(to_chain_units(UNIT)), UNIT);
        assert_eq!(from_chain_units(to_chain_units(0)), 0);
    }

    // ── earn_units ────────────────────────────────────────────────────────────

    #[test]
    fn earn_normal() {
        assert_eq!(earn_units(10 * UNIT, 5 * UNIT), Ok(15 * UNIT));
    }

    #[test]
    fn earn_overflow() {
        assert_eq!(earn_units(u64::MAX, 1), Err(UnitsError::Overflow));
    }

    #[test]
    fn earn_zero_amount() {
        assert_eq!(earn_units(UNIT, 0), Ok(UNIT));
    }

    // ── spend_units ───────────────────────────────────────────────────────────

    #[test]
    fn spend_normal() {
        assert_eq!(spend_units(10 * UNIT, 3 * UNIT), Ok(7 * UNIT));
    }

    #[test]
    fn spend_exact_balance() {
        assert_eq!(spend_units(UNIT, UNIT), Ok(0));
    }

    #[test]
    fn spend_insufficient() {
        assert_eq!(
            spend_units(5 * UNIT, 10 * UNIT),
            Err(UnitsError::InsufficientFunds {
                balance: 5 * UNIT,
                amount: 10 * UNIT,
            })
        );
    }

    #[test]
    fn spend_zero_balance() {
        assert_eq!(
            spend_units(0, 1),
            Err(UnitsError::InsufficientFunds {
                balance: 0,
                amount: 1
            })
        );
    }
}
