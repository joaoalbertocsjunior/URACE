//! Ledger schema versioning.
//!
//! Rust port of the `LEDGER_SCHEMA_VERSION` / `can_read_schema` logic from
//! `signed_ledger.py`, plus a `validate_row_schema` helper for use when
//! reading individual journal rows.
//!
//! The Python file treated `schema_version` as an opaque string
//! (`"urace-signed-block-v1"`); for the Rust port we normalise it to a
//! monotonically increasing `u32` to enable forward-compatibility checks:
//! a row is readable if `row_version <= current_version`.

use serde_json::Value;
use thiserror::Error;

/// The schema version written into every new journal row.
///
/// Bump this when the row format changes in a backward-incompatible way.
/// Rows with `schema_version <= CURRENT_SCHEMA_VERSION` can always be read.
pub const CURRENT_SCHEMA_VERSION: u32 = 1;

/// Errors raised when a journal row's schema cannot be validated.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum SchemaVersionError {
    #[error("missing schema_version field")]
    Missing,
    #[error("unsupported schema version {found} (current: {current})")]
    Unsupported { found: u32, current: u32 },
}

// ── Public API ────────────────────────────────────────────────────────────────

/// Return `true` if this runtime can interpret a row that was written with
/// `row_version`.
///
/// A row is readable as long as it was written with a version ≤ the current
/// runtime's schema version (forward compatibility — newer rows require a
/// runtime upgrade).
///
/// ```
/// # use urace_ledger::schema_version::{can_read_schema, CURRENT_SCHEMA_VERSION};
/// assert!(can_read_schema(1, CURRENT_SCHEMA_VERSION));
/// assert!(can_read_schema(0, CURRENT_SCHEMA_VERSION));
/// assert!(!can_read_schema(2, CURRENT_SCHEMA_VERSION));
/// ```
pub fn can_read_schema(row_version: u32, current_version: u32) -> bool {
    row_version <= current_version
}

/// Check that `row["schema_version"]` exists and is readable by this runtime.
///
/// # Errors
/// - [`SchemaVersionError::Missing`] — the field is absent or not a number.
/// - [`SchemaVersionError::Unsupported`] — the version exceeds
///   [`CURRENT_SCHEMA_VERSION`].
pub fn validate_row_schema(row: &Value) -> Result<(), SchemaVersionError> {
    let version_val = row
        .get("schema_version")
        .ok_or(SchemaVersionError::Missing)?;

    let found = version_val
        .as_u64()
        .map(|v| v as u32)
        .ok_or(SchemaVersionError::Missing)?;

    if can_read_schema(found, CURRENT_SCHEMA_VERSION) {
        Ok(())
    } else {
        Err(SchemaVersionError::Unsupported {
            found,
            current: CURRENT_SCHEMA_VERSION,
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    // ── can_read_schema ───────────────────────────────────────────────────────

    #[test]
    fn current_version_is_readable() {
        assert!(can_read_schema(CURRENT_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION));
    }

    #[test]
    fn zero_is_always_readable() {
        assert!(can_read_schema(0, CURRENT_SCHEMA_VERSION));
    }

    #[test]
    fn future_version_is_unreadable() {
        assert!(!can_read_schema(CURRENT_SCHEMA_VERSION + 1, CURRENT_SCHEMA_VERSION));
    }

    #[test]
    fn past_version_is_readable() {
        // If we bump CURRENT_SCHEMA_VERSION in the future, old rows must still pass.
        assert!(can_read_schema(1, 2));
        assert!(can_read_schema(1, 100));
    }

    // ── validate_row_schema ───────────────────────────────────────────────────

    #[test]
    fn valid_row_passes() {
        let row = json!({ "schema_version": 1, "kind": "CREDIT_DELTA" });
        assert!(validate_row_schema(&row).is_ok());
    }

    #[test]
    fn version_zero_passes() {
        let row = json!({ "schema_version": 0 });
        assert!(validate_row_schema(&row).is_ok());
    }

    #[test]
    fn missing_field_returns_error() {
        let row = json!({ "kind": "CREDIT_DELTA" });
        assert_eq!(validate_row_schema(&row), Err(SchemaVersionError::Missing));
    }

    #[test]
    fn non_numeric_field_returns_error() {
        let row = json!({ "schema_version": "v1" });
        assert_eq!(validate_row_schema(&row), Err(SchemaVersionError::Missing));
    }

    #[test]
    fn future_version_returns_unsupported() {
        let future = CURRENT_SCHEMA_VERSION + 1;
        let row = json!({ "schema_version": future });
        assert_eq!(
            validate_row_schema(&row),
            Err(SchemaVersionError::Unsupported {
                found: future,
                current: CURRENT_SCHEMA_VERSION,
            })
        );
    }

    #[test]
    fn negative_field_treated_as_missing() {
        // JSON -1 cannot be represented as u64, so as_u64() returns None → Missing.
        let row = json!({ "schema_version": -1i64 });
        assert_eq!(validate_row_schema(&row), Err(SchemaVersionError::Missing));
    }
}
