//! Adaptive governance parameters — market rigidity mitigation.
//!
//! All market-sensitive thresholds (floor, rate limits, circuit breakers,
//! time-locks) are stored here as runtime-adjustable values, not compile-time
//! constants. Governance can tune them to match market conditions without a
//! code change. Each parameter has a safety envelope (min/max) that cannot
//! itself be changed without a supermajority vote (M07).
//!
//! # Design principle
//! Hardcoded constants stale market dynamics. `AdaptiveParamRegistry` lets
//! the network vote values up or down within safe bounds, so mechanisms like
//! the market floor, circuit breaker, and rate limits track the market rather
//! than constraining it permanently.

use crate::param_bounds::ParamBound;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

// ── Default market parameter values ──────────────────────────────────────────
//
// These are starting points, not permanent constraints.
// All are adjustable via `AdaptiveParamRegistry::set`.

/// Minimum accepted price per work unit in UCR base units (10^8 = 1 UCR).
/// Default = 0 (no floor). Governance may raise this to protect against
/// race-to-bottom, or lower it back to zero in a healthy market.
pub const DEFAULT_MARKET_FLOOR_UCR: f64 = 0.0;

/// Maximum new tasks per peer per minute (M06 session authority budget).
/// Default = 60 (1/sec). High enough for burst work; low enough to slow
/// automated chaining attacks.
pub const DEFAULT_TASK_RATE_PER_MIN: f64 = 60.0;

/// Aggregate mint rate ceiling across all peers per hour (M17 circuit breaker).
/// At 0 = disabled. Default = 0 (off) until governance enables it.
pub const DEFAULT_MINT_RATE_CIRCUIT_THRESHOLD: f64 = 0.0;

/// Maximum governance proposals per peer per hour (M14 inbox rate limit).
/// Default = 10. High enough for active governance; filters flood attacks.
pub const DEFAULT_INBOX_RATE_PER_HOUR: f64 = 10.0;

/// Minimum time-lock window in seconds for high-value operations (M05).
/// Default = 0 (disabled). Governance enables it when the network is mature.
pub const DEFAULT_TIMELOCK_SECS: f64 = 0.0;

/// Minimum fraction of voters required for a proposal to be valid (quorum).
/// Default = 0.1 (10%). Prevents minority capture without blocking participation.
pub const DEFAULT_GOVERNANCE_QUORUM: f64 = 0.1;

// ── Safety envelopes — cannot be changed without supermajority (M07) ─────────

pub fn market_param_bounds() -> Vec<ParamBound> {
    vec![
        ParamBound::new("market_floor_ucr", 0.0, 1_000_000.0),
        ParamBound::new("task_rate_per_min", 1.0, 1_000.0),
        ParamBound::new("mint_rate_circuit_threshold", 0.0, f64::MAX),
        ParamBound::new("inbox_rate_per_hour", 1.0, 1_000.0),
        ParamBound::new("timelock_secs", 0.0, 86_400.0), // max 24h
        ParamBound::new("governance_quorum", 0.01, 0.67), // 1%–67%
    ]
}

// ── Registry ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParamHistoryEntry {
    pub old_value: f64,
    pub new_value: f64,
    pub changed_at: u64,
    pub changed_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdaptiveParam {
    pub name: String,
    pub value: f64,
    pub history: Vec<ParamHistoryEntry>,
}

#[derive(Debug, Error)]
pub enum AdaptiveParamError {
    #[error("unknown parameter '{0}'")]
    UnknownParam(String),
    #[error("value {value} for '{name}' is outside safety envelope [{min}, {max}]")]
    OutsideEnvelope {
        name: String,
        value: f64,
        min: f64,
        max: f64,
    },
}

/// Governance-adjustable parameter store.
///
/// Call `set(name, value, changed_by)` to update a parameter after a governance
/// vote. Call `get(name)` to read the current market-operative value.
pub struct AdaptiveParamRegistry {
    params: HashMap<String, AdaptiveParam>,
    bounds: Vec<ParamBound>,
}

impl AdaptiveParamRegistry {
    /// Create a registry loaded with market defaults.
    pub fn with_defaults() -> Self {
        let mut params = HashMap::new();
        let defaults = [
            ("market_floor_ucr", DEFAULT_MARKET_FLOOR_UCR),
            ("task_rate_per_min", DEFAULT_TASK_RATE_PER_MIN),
            ("mint_rate_circuit_threshold", DEFAULT_MINT_RATE_CIRCUIT_THRESHOLD),
            ("inbox_rate_per_hour", DEFAULT_INBOX_RATE_PER_HOUR),
            ("timelock_secs", DEFAULT_TIMELOCK_SECS),
            ("governance_quorum", DEFAULT_GOVERNANCE_QUORUM),
        ];
        for (name, value) in defaults {
            params.insert(
                name.to_owned(),
                AdaptiveParam {
                    name: name.to_owned(),
                    value,
                    history: Vec::new(),
                },
            );
        }
        Self {
            params,
            bounds: market_param_bounds(),
        }
    }

    /// Read the current value of a parameter.
    pub fn get(&self, name: &str) -> Result<f64, AdaptiveParamError> {
        self.params
            .get(name)
            .map(|p| p.value)
            .ok_or_else(|| AdaptiveParamError::UnknownParam(name.to_owned()))
    }

    /// Update a parameter after a governance vote.
    ///
    /// Fails if `value` is outside the safety envelope for `name`.
    pub fn set(
        &mut self,
        name: &str,
        value: f64,
        changed_by: &str,
    ) -> Result<(), AdaptiveParamError> {
        // Check safety envelope.
        for bound in &self.bounds {
            if bound.name == name {
                if bound.check(value).is_err() {
                    return Err(AdaptiveParamError::OutsideEnvelope {
                        name: name.to_owned(),
                        value,
                        min: bound.min,
                        max: bound.max,
                    });
                }
                break;
            }
        }

        let param = self
            .params
            .get_mut(name)
            .ok_or_else(|| AdaptiveParamError::UnknownParam(name.to_owned()))?;

        param.history.push(ParamHistoryEntry {
            old_value: param.value,
            new_value: value,
            changed_at: now_secs(),
            changed_by: changed_by.to_owned(),
        });
        param.value = value;
        Ok(())
    }

    /// Snapshot all current parameter values (for audit/export).
    pub fn snapshot(&self) -> HashMap<String, f64> {
        self.params
            .iter()
            .map(|(k, v)| (k.clone(), v.value))
            .collect()
    }
}

fn now_secs() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_are_readable() {
        let reg = AdaptiveParamRegistry::with_defaults();
        assert_eq!(reg.get("market_floor_ucr").unwrap(), DEFAULT_MARKET_FLOOR_UCR);
        assert_eq!(reg.get("task_rate_per_min").unwrap(), DEFAULT_TASK_RATE_PER_MIN);
    }

    #[test]
    fn governance_can_raise_market_floor() {
        let mut reg = AdaptiveParamRegistry::with_defaults();
        reg.set("market_floor_ucr", 500.0, "governance-vote-42").unwrap();
        assert_eq!(reg.get("market_floor_ucr").unwrap(), 500.0);
    }

    #[test]
    fn governance_can_lower_floor_back_to_zero() {
        let mut reg = AdaptiveParamRegistry::with_defaults();
        reg.set("market_floor_ucr", 1000.0, "vote-1").unwrap();
        reg.set("market_floor_ucr", 0.0, "vote-2").unwrap();
        assert_eq!(reg.get("market_floor_ucr").unwrap(), 0.0);
    }

    #[test]
    fn value_outside_envelope_rejected() {
        let mut reg = AdaptiveParamRegistry::with_defaults();
        // task_rate_per_min max is 1000.0
        let err = reg.set("task_rate_per_min", 9999.0, "attacker").unwrap_err();
        assert!(matches!(err, AdaptiveParamError::OutsideEnvelope { .. }));
        // Value unchanged
        assert_eq!(reg.get("task_rate_per_min").unwrap(), DEFAULT_TASK_RATE_PER_MIN);
    }

    #[test]
    fn history_is_recorded() {
        let mut reg = AdaptiveParamRegistry::with_defaults();
        reg.set("market_floor_ucr", 100.0, "vote-a").unwrap();
        reg.set("market_floor_ucr", 200.0, "vote-b").unwrap();
        let history = &reg.params["market_floor_ucr"].history;
        assert_eq!(history.len(), 2);
        assert_eq!(history[0].new_value, 100.0);
        assert_eq!(history[1].new_value, 200.0);
        assert_eq!(history[1].changed_by, "vote-b");
    }

    #[test]
    fn timelock_disabled_by_default() {
        let reg = AdaptiveParamRegistry::with_defaults();
        assert_eq!(reg.get("timelock_secs").unwrap(), 0.0);
    }

    #[test]
    fn snapshot_contains_all_params() {
        let reg = AdaptiveParamRegistry::with_defaults();
        let snap = reg.snapshot();
        assert!(snap.contains_key("market_floor_ucr"));
        assert!(snap.contains_key("task_rate_per_min"));
        assert!(snap.contains_key("mint_rate_circuit_threshold"));
        assert!(snap.contains_key("inbox_rate_per_hour"));
        assert!(snap.contains_key("timelock_secs"));
        assert!(snap.contains_key("governance_quorum"));
    }

    #[test]
    fn unknown_param_returns_error() {
        let reg = AdaptiveParamRegistry::with_defaults();
        assert!(matches!(
            reg.get("does_not_exist"),
            Err(AdaptiveParamError::UnknownParam(_))
        ));
    }
}
