pub mod authority;
pub mod fleet_policy;

pub use authority::{resolve, Objective};
pub use fleet_policy::{FleetPolicy, FleetPolicyError, PolicyRule, PolicyStore};

// regex_lite is a no-std-compatible regex engine (MIT), no PCRE dependency.
// Used only in authority.rs for weakening-verb pattern matching.
