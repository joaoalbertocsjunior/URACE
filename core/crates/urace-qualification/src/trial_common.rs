//! Shared types and helpers for trial sessions.
//!
//! Ported from `trial/common.py`. Provides the `TrialContext` struct,
//! timestamp helpers, and shared constants used across all trial modules.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Shared constants (from trial/common.py + qualification_protocol.py)
// ---------------------------------------------------------------------------

/// Default wall-clock budget for a single trial session, in milliseconds.
pub const DEFAULT_WALL_BUDGET_MS: u64 = 480_000; // 480 s

/// Maximum active wall budget seconds (from qualification_protocol.py).
pub const ACTIVE_WALL_BUDGET_SECONDS: u64 = 480;

/// Minimum matched ordinary pairs required for qualification readiness.
pub const MINIMUM_PAIRS: usize = 30;

/// Minimum pairs per task family.
pub const MINIMUM_PER_FAMILY: usize = 6;

/// Scoring threshold: score_delta must exceed this to consider improvement meaningful.
pub const SCORE_DELTA_THRESHOLD: f64 = 0.0;

/// Peer cap: 50 UCR expressed in base units (10^8 per UCR).
pub const PEER_CAP_UCR: u64 = 50 * 100_000_000;

// ---------------------------------------------------------------------------
// TrialContext
// ---------------------------------------------------------------------------

/// Shared context for a trial run.
///
/// Carries the filesystem root, operator config snapshot, and the identifier
/// of the provider under evaluation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrialContext {
    /// Absolute path to the trial root directory.
    pub root: PathBuf,
    /// Operator config snapshot (from `config.json`).
    pub config: serde_json::Value,
    /// Provider identifier, e.g. `"claude"` or `"codex"`.
    pub provider_id: String,
}

impl TrialContext {
    /// Create a new `TrialContext`.
    pub fn new(
        root: impl Into<PathBuf>,
        config: serde_json::Value,
        provider_id: impl Into<String>,
    ) -> Self {
        TrialContext {
            root: root.into(),
            config,
            provider_id: provider_id.into(),
        }
    }
}

// ---------------------------------------------------------------------------
// Timestamp and ID helpers
// ---------------------------------------------------------------------------

/// Return the current UTC time as an ISO 8601 string (`YYYY-MM-DDTHH:MM:SSZ`).
///
/// Uses only `std` — no external chrono/time dependency required.
pub fn now_iso() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Build a minimal but correct ISO-8601 representation.
    let s = secs;
    let days_since_epoch = s / 86400;
    let time_of_day = s % 86400;
    let hh = time_of_day / 3600;
    let mm = (time_of_day % 3600) / 60;
    let ss = time_of_day % 60;

    // Gregorian calendar decomposition from Unix epoch (1970-01-01).
    let (year, month, day) = days_to_ymd(days_since_epoch);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        year, month, day, hh, mm, ss
    )
}

/// Return a new UUID v4 as the trial session identifier string.
pub fn trial_identifier() -> String {
    Uuid::new_v4().to_string()
}

// ---------------------------------------------------------------------------
// Internal calendar helper
// ---------------------------------------------------------------------------

/// Convert days since the Unix epoch to (year, month, day) in the proleptic
/// Gregorian calendar. This avoids pulling in `chrono` for a simple timestamp.
fn days_to_ymd(days: u64) -> (u64, u64, u64) {
    // Algorithm: https://www.researchgate.net/publication/316558298
    // Adapted from Howard Hinnant's civil-from-days.
    let days = days as i64 + 719_468; // shift to 1 Mar 0000
    let era = if days >= 0 { days } else { days - 146_096 } / 146_097;
    let doe = (days - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146_096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y as u64, m, d)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn now_iso_format() {
        let ts = now_iso();
        // Must match YYYY-MM-DDTHH:MM:SSZ
        assert_eq!(ts.len(), 20, "timestamp length: {}", ts);
        assert!(ts.ends_with('Z'), "must end with Z: {}", ts);
        assert_eq!(&ts[4..5], "-");
        assert_eq!(&ts[7..8], "-");
        assert_eq!(&ts[10..11], "T");
        assert_eq!(&ts[13..14], ":");
        assert_eq!(&ts[16..17], ":");
    }

    #[test]
    fn trial_identifier_is_uuid_format() {
        let id = trial_identifier();
        // UUID v4: 8-4-4-4-12 hex groups separated by hyphens, 36 chars total.
        assert_eq!(id.len(), 36);
        let parts: Vec<&str> = id.split('-').collect();
        assert_eq!(parts.len(), 5);
        assert_eq!(parts[0].len(), 8);
        assert_eq!(parts[1].len(), 4);
        assert_eq!(parts[2].len(), 4);
        assert_eq!(parts[3].len(), 4);
        assert_eq!(parts[4].len(), 12);
    }

    #[test]
    fn trial_identifiers_are_unique() {
        let id1 = trial_identifier();
        let id2 = trial_identifier();
        assert_ne!(id1, id2, "each call must return a fresh UUID");
    }

    #[test]
    fn trial_context_roundtrip() {
        let ctx = TrialContext::new(
            PathBuf::from("/trial/root"),
            serde_json::json!({"executor": {"enabled": true}}),
            "claude",
        );
        assert_eq!(ctx.provider_id, "claude");
        assert_eq!(ctx.root, PathBuf::from("/trial/root"));
    }

    #[test]
    fn constants_are_sensible() {
        assert_eq!(DEFAULT_WALL_BUDGET_MS, 480_000);
        assert_eq!(ACTIVE_WALL_BUDGET_SECONDS, 480);
        assert_eq!(MINIMUM_PAIRS, 30);
        assert_eq!(MINIMUM_PER_FAMILY, 6);
        assert_eq!(PEER_CAP_UCR, 5_000_000_000);
    }
}
