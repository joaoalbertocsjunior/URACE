//! Schema validation, MIME policy enforcement, and rule engine for URACE.
//!
//! Corresponds to `schema_export.py`, `validation.py`, `config_schema.py`,
//! `mime_policy.py`, `mime_validator.py`, and `rules.py`.

pub mod mime_policy;
pub mod rules;
pub mod schema_export;
pub mod spec_hash;
pub mod validation;

pub use mime_policy::MimePolicy;
pub use rules::{
    changes_for_rule, derivation_chain, detect_conflicts, record_relationship, rules_for_change,
    Rule, RuleConflict, RuleEngine, RuleKind, RuleStore, RuleViolation,
};
pub use schema_export::SchemaExporter;
pub use validation::{
    MaxLength, MinLength, OneOf, Range, RegexValidator, Required, ValidationError, Validator,
};
