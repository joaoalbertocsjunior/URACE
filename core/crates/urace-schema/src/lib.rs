//! Schema validation, MIME policy enforcement, and rule engine for URACE.
//!
//! Corresponds to `schema_export.py`, `validation.py`, `config_schema.py`,
//! `mime_policy.py`, `mime_validator.py`, and `rules.py`.

pub mod adaptive_params;
pub mod compliance_export;
pub mod emergency_vote;
pub mod governance_veto;
pub mod mime_policy;
pub mod param_bounds;
pub mod proposal_expiry;
pub mod rules;
pub mod schema_export;
pub mod spec_hash;
pub mod validation;

pub use adaptive_params::{
    market_param_bounds, AdaptiveParam, AdaptiveParamError, AdaptiveParamRegistry,
    ParamHistoryEntry, DEFAULT_GOVERNANCE_QUORUM, DEFAULT_INBOX_RATE_PER_HOUR,
    DEFAULT_MARKET_FLOOR_UCR, DEFAULT_MINT_RATE_CIRCUIT_THRESHOLD, DEFAULT_TASK_RATE_PER_MIN,
    DEFAULT_TIMELOCK_SECS,
};
pub use compliance_export::{
    generate_compliance_report, ComplianceEvent, ComplianceEventKind, ComplianceReport,
};
pub use emergency_vote::{
    EmergencyAction, EmergencyProposal, EmergencyVote, EMERGENCY_QUORUM_FRACTION,
    EMERGENCY_VOTE_WINDOW_SECS,
};
pub use governance_veto::{VetoError, VetoRecord, VetoRegistry, VETO_THRESHOLD_FRACTION};
pub use mime_policy::MimePolicy;
pub use param_bounds::{check_all_params, ParamBound, ParamBoundsError, ParamViolation};
pub use proposal_expiry::{
    GovernanceProposal, ProposalError, ProposalExpiryStatus, PROPOSAL_EXPIRY_SECS,
};
pub use rules::{
    changes_for_rule, check_jurisdictional_compliance, derivation_chain, detect_conflicts,
    record_relationship, rules_for_change, JurisdictionalAdvisory, Rule, RuleConflict, RuleEngine,
    RuleKind, RuleStore, RuleViolation,
};
pub use schema_export::SchemaExporter;
pub use validation::{
    MaxLength, MinLength, OneOf, Range, RegexValidator, Required, ValidationError, Validator,
};
