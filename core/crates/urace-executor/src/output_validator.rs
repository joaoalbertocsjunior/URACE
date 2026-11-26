//! M73 — Output validator / schema enforcement.
//!
//! LLM executor output must be validated before any on-chain write occurs.
//! This module checks length, forbidden content, JSON well-formedness, and
//! required-field / type constraints.

use serde_json::Value;
use thiserror::Error;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ValidationError {
    #[error("output is not valid JSON: {0}")]
    NotJson(String),
    #[error("required field missing: {0}")]
    MissingField(String),
    #[error("field type mismatch: field '{field}' expected {expected}, got {got}")]
    TypeMismatch {
        field: String,
        expected: String,
        got: String,
    },
    #[error("output length {actual} exceeds max {max}")]
    TooLong { actual: usize, max: usize },
    #[error("output contains forbidden content: {pattern}")]
    ForbiddenContent { pattern: String },
}

// ── Limits & forbidden patterns ───────────────────────────────────────────────

/// Maximum permitted output size (1 MiB).
pub const MAX_OUTPUT_BYTES: usize = 1_048_576;

/// Substrings that must not appear in executor output.
static FORBIDDEN_OUTPUT_PATTERNS: &[&str] = &[
    "rm -rf",
    "sudo",
    "wget ",
    "curl ",
    "exec(",
    "eval(",
    "__import__",
    "subprocess",
    "os.system",
    "shell=True",
];

// ── Schema ────────────────────────────────────────────────────────────────────

/// A lightweight output schema that validators check against.
pub struct OutputSchema {
    /// Fields that must be present in the JSON object.
    pub required_fields: Vec<String>,
    /// Per-field type constraints: `(field_name, expected_type)`.
    ///
    /// `expected_type` must be one of `"string"`, `"number"`, `"bool"`,
    /// `"object"`, `"array"`, or `"null"`.
    pub field_types: Vec<(String, &'static str)>,
    /// Maximum permitted byte length of the raw output string.
    pub max_bytes: usize,
}

impl OutputSchema {
    /// Default schema for work-output payloads: requires `result` (string) and
    /// `score_delta` (number), capped at [`MAX_OUTPUT_BYTES`].
    pub fn default_work_output() -> Self {
        OutputSchema {
            required_fields: vec!["result".to_string(), "score_delta".to_string()],
            field_types: vec![
                ("result".to_string(), "string"),
                ("score_delta".to_string(), "number"),
            ],
            max_bytes: MAX_OUTPUT_BYTES,
        }
    }
}

// ── Validation ────────────────────────────────────────────────────────────────

/// Validate `raw` executor output against `schema`.
///
/// Checks (in order):
/// 1. Byte length ≤ `schema.max_bytes`.
/// 2. No forbidden content patterns.
/// 3. Valid JSON.
/// 4. All `schema.required_fields` present.
/// 5. All `schema.field_types` constraints satisfied.
///
/// Returns the parsed [`Value`] on success.
pub fn validate_output(raw: &str, schema: &OutputSchema) -> Result<Value, ValidationError> {
    // 1. Length guard.
    if raw.len() > schema.max_bytes {
        return Err(ValidationError::TooLong {
            actual: raw.len(),
            max: schema.max_bytes,
        });
    }

    // 2. Forbidden content check (case-insensitive).
    let lower = raw.to_lowercase();
    for pattern in FORBIDDEN_OUTPUT_PATTERNS {
        if lower.contains(*pattern) {
            return Err(ValidationError::ForbiddenContent {
                pattern: pattern.to_string(),
            });
        }
    }

    // 3. JSON parse.
    let val: Value =
        serde_json::from_str(raw).map_err(|e| ValidationError::NotJson(e.to_string()))?;

    // 4. Required fields.
    for field in &schema.required_fields {
        if val.get(field).is_none() {
            return Err(ValidationError::MissingField(field.clone()));
        }
    }

    // 5. Type constraints.
    for (field, expected_type) in &schema.field_types {
        if let Some(v) = val.get(field) {
            let got = match v {
                Value::String(_) => "string",
                Value::Number(_) => "number",
                Value::Bool(_) => "bool",
                Value::Object(_) => "object",
                Value::Array(_) => "array",
                Value::Null => "null",
            };
            if got != *expected_type {
                return Err(ValidationError::TypeMismatch {
                    field: field.clone(),
                    expected: expected_type.to_string(),
                    got: got.to_string(),
                });
            }
        }
    }

    Ok(val)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn schema() -> OutputSchema {
        OutputSchema::default_work_output()
    }

    #[test]
    fn valid_output_accepted() {
        let raw = r#"{"result": "looks good", "score_delta": 1.5}"#;
        let val = validate_output(raw, &schema()).expect("should be valid");
        assert_eq!(val["result"], "looks good");
        assert!((val["score_delta"].as_f64().unwrap() - 1.5).abs() < 1e-9);
    }

    #[test]
    fn missing_required_field_rejected() {
        // Missing `score_delta`.
        let raw = r#"{"result": "ok"}"#;
        match validate_output(raw, &schema()) {
            Err(ValidationError::MissingField(f)) => assert_eq!(f, "score_delta"),
            other => panic!("expected MissingField, got {:?}", other),
        }
    }

    #[test]
    fn wrong_type_rejected() {
        // `score_delta` is a string, but schema requires number.
        let raw = r#"{"result": "ok", "score_delta": "high"}"#;
        match validate_output(raw, &schema()) {
            Err(ValidationError::TypeMismatch { field, expected, got }) => {
                assert_eq!(field, "score_delta");
                assert_eq!(expected, "number");
                assert_eq!(got, "string");
            }
            other => panic!("expected TypeMismatch, got {:?}", other),
        }
    }

    #[test]
    fn too_long_rejected() {
        let tiny_schema = OutputSchema {
            required_fields: vec![],
            field_types: vec![],
            max_bytes: 10,
        };
        let raw = "this string is longer than ten bytes";
        match validate_output(raw, &tiny_schema) {
            Err(ValidationError::TooLong { actual, max }) => {
                assert!(actual > max);
            }
            other => panic!("expected TooLong, got {:?}", other),
        }
    }

    #[test]
    fn forbidden_pattern_rejected() {
        let raw = r#"{"result": "rm -rf /tmp", "score_delta": 0}"#;
        match validate_output(raw, &schema()) {
            Err(ValidationError::ForbiddenContent { pattern }) => {
                assert_eq!(pattern, "rm -rf");
            }
            other => panic!("expected ForbiddenContent, got {:?}", other),
        }
    }

    #[test]
    fn not_json_rejected() {
        let raw = "this is not json at all";
        assert!(matches!(
            validate_output(raw, &schema()),
            Err(ValidationError::NotJson(_))
        ));
    }

    #[test]
    fn sudo_forbidden() {
        let raw = r#"{"result": "sudo apt install x", "score_delta": 0}"#;
        assert!(matches!(
            validate_output(raw, &schema()),
            Err(ValidationError::ForbiddenContent { .. })
        ));
    }

    #[test]
    fn subprocess_forbidden() {
        let raw = r#"{"result": "subprocess.run(cmd)", "score_delta": 0}"#;
        assert!(matches!(
            validate_output(raw, &schema()),
            Err(ValidationError::ForbiddenContent { .. })
        ));
    }
}
