pub mod authority;
pub mod cognitive_resume;
pub mod destination;
pub mod fleet_policy;
pub mod intent_trace;
pub mod policy_store;

pub use authority::{
    classify_operation, resolve, resolve_with_budget, timelock_elapsed, HIGH_VALUE_TIMELOCK_SECS,
    Objective, OperationClass, SessionBudget,
};
pub use destination::{anchor_from_config, drift_score, DriftOutcome, DRIFT_BLOCK, DRIFT_FLAG};
pub use fleet_policy::{FleetPolicy, FleetPolicyError, PolicyRule, PolicyStore};
pub use policy_store::{
    ExchangePolicy, ExchangePolicyStore, PolicyStoreError, PROTOCOL_VERSION, SCHEMA,
};

// regex_lite is a no-std-compatible regex engine (MIT), no PCRE dependency.
// Used only in authority.rs for weakening-verb pattern matching.
