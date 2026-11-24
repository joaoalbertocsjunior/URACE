//! Field-level validators.
//!
//! Each validator implements `Validator` and returns `Vec<ValidationError>`.
//! No validator ever panics — invalid inputs produce errors, not panics.

use regex_lite::Regex;
use serde::{Deserialize, Serialize};
use std::fmt;

// ── Error type ───────────────────────────────────────────────────────────────

/// A single validation failure.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ValidationError {
    /// The field or path that failed.
    pub field: String,
    /// Human-readable explanation.
    pub message: String,
}

impl fmt::Display for ValidationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.field, self.message)
    }
}

impl std::error::Error for ValidationError {}

// ── Validator trait ──────────────────────────────────────────────────────────

/// A stateless validator that checks a string value and returns any errors.
pub trait Validator: fmt::Debug + Send + Sync {
    /// Validate `value` for `field`. Returns an empty vec on success.
    fn validate(&self, field: &str, value: &str) -> Vec<ValidationError>;
}

// ── Required ─────────────────────────────────────────────────────────────────

/// Rejects empty strings.
#[derive(Debug, Clone, Default)]
pub struct Required;

impl Validator for Required {
    fn validate(&self, field: &str, value: &str) -> Vec<ValidationError> {
        if value.trim().is_empty() {
            vec![ValidationError {
                field: field.to_owned(),
                message: "field is required".into(),
            }]
        } else {
            vec![]
        }
    }
}

// ── MinLength ────────────────────────────────────────────────────────────────

/// Rejects strings shorter than `min` characters (Unicode char count).
#[derive(Debug, Clone)]
pub struct MinLength(pub usize);

impl Validator for MinLength {
    fn validate(&self, field: &str, value: &str) -> Vec<ValidationError> {
        if value.chars().count() < self.0 {
            vec![ValidationError {
                field: field.to_owned(),
                message: format!("must be at least {} characters", self.0),
            }]
        } else {
            vec![]
        }
    }
}

// ── MaxLength ────────────────────────────────────────────────────────────────

/// Rejects strings longer than `max` characters (Unicode char count).
#[derive(Debug, Clone)]
pub struct MaxLength(pub usize);

impl Validator for MaxLength {
    fn validate(&self, field: &str, value: &str) -> Vec<ValidationError> {
        if value.chars().count() > self.0 {
            vec![ValidationError {
                field: field.to_owned(),
                message: format!("must be at most {} characters", self.0),
            }]
        } else {
            vec![]
        }
    }
}

// ── RegexValidator ───────────────────────────────────────────────────────────

/// Rejects strings that do not match a regex pattern.
#[derive(Debug, Clone)]
pub struct RegexValidator {
    pattern: String,
    compiled: Regex,
}

impl RegexValidator {
    /// Build a new `RegexValidator`.  Returns an error if `pattern` is invalid.
    pub fn new(pattern: &str) -> Result<Self, regex_lite::Error> {
        let compiled = Regex::new(pattern)?;
        Ok(Self {
            pattern: pattern.to_owned(),
            compiled,
        })
    }

    pub fn pattern(&self) -> &str {
        &self.pattern
    }
}

impl Validator for RegexValidator {
    fn validate(&self, field: &str, value: &str) -> Vec<ValidationError> {
        if !self.compiled.is_match(value) {
            vec![ValidationError {
                field: field.to_owned(),
                message: format!("must match pattern: {}", self.pattern),
            }]
        } else {
            vec![]
        }
    }
}

// ── Range ────────────────────────────────────────────────────────────────────

/// Rejects parsed numbers outside `[min, max]`.
/// The value string is parsed as `f64`; integer inputs work fine.
#[derive(Debug, Clone)]
pub struct Range {
    pub min: f64,
    pub max: f64,
}

impl Validator for Range {
    fn validate(&self, field: &str, value: &str) -> Vec<ValidationError> {
        match value.trim().parse::<f64>() {
            Err(_) => vec![ValidationError {
                field: field.to_owned(),
                message: format!("must be a number between {} and {}", self.min, self.max),
            }],
            Ok(n) if n < self.min || n > self.max => vec![ValidationError {
                field: field.to_owned(),
                message: format!("must be between {} and {} (got {n})", self.min, self.max),
            }],
            Ok(_) => vec![],
        }
    }
}

// ── OneOf ────────────────────────────────────────────────────────────────────

/// Rejects values not in an explicit allowlist.
#[derive(Debug, Clone)]
pub struct OneOf(pub Vec<String>);

impl OneOf {
    pub fn new(options: &[&str]) -> Self {
        Self(options.iter().map(|s| s.to_string()).collect())
    }
}

impl Validator for OneOf {
    fn validate(&self, field: &str, value: &str) -> Vec<ValidationError> {
        if !self.0.iter().any(|o| o == value) {
            vec![ValidationError {
                field: field.to_owned(),
                message: format!("must be one of: {}", self.0.join(", ")),
            }]
        } else {
            vec![]
        }
    }
}

// ── Composite helper ─────────────────────────────────────────────────────────

/// Run a slice of validators against a value and collect all errors.
pub fn run_all(validators: &[Box<dyn Validator>], field: &str, value: &str) -> Vec<ValidationError> {
    validators.iter().flat_map(|v| v.validate(field, value)).collect()
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn required_rejects_empty() {
        let errs = Required.validate("name", "");
        assert!(!errs.is_empty());
    }

    #[test]
    fn required_accepts_nonempty() {
        let errs = Required.validate("name", "hello");
        assert!(errs.is_empty());
    }

    #[test]
    fn min_length_rejects_short() {
        let errs = MinLength(5).validate("field", "hi");
        assert!(!errs.is_empty());
    }

    #[test]
    fn min_length_accepts_long_enough() {
        let errs = MinLength(3).validate("field", "hello");
        assert!(errs.is_empty());
    }

    #[test]
    fn max_length_rejects_too_long() {
        let errs = MaxLength(3).validate("field", "toolong");
        assert!(!errs.is_empty());
    }

    #[test]
    fn regex_match_passes() {
        let v = RegexValidator::new(r"^\d{4}-\d{2}-\d{2}$").unwrap();
        assert!(v.validate("date", "2026-11-24").is_empty());
    }

    #[test]
    fn regex_no_match_fails() {
        let v = RegexValidator::new(r"^\d{4}-\d{2}-\d{2}$").unwrap();
        assert!(!v.validate("date", "not-a-date").is_empty());
    }

    #[test]
    fn range_accepts_in_bounds() {
        let v = Range { min: 1.0, max: 100.0 };
        assert!(v.validate("score", "50").is_empty());
    }

    #[test]
    fn range_rejects_out_of_bounds() {
        let v = Range { min: 1.0, max: 10.0 };
        assert!(!v.validate("score", "99").is_empty());
    }

    #[test]
    fn one_of_accepts_valid() {
        let v = OneOf::new(&["low", "medium", "high"]);
        assert!(v.validate("effort", "medium").is_empty());
    }

    #[test]
    fn one_of_rejects_invalid() {
        let v = OneOf::new(&["low", "medium", "high"]);
        assert!(!v.validate("effort", "extreme").is_empty());
    }
}
