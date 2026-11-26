//! M65 — Parameter bounds enforcement: validate all configurable parameters are within safe ranges.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParamBound {
    pub name: String,
    pub min: f64,
    pub max: f64,
}

impl ParamBound {
    pub fn new(name: impl Into<String>, min: f64, max: f64) -> Self {
        ParamBound {
            name: name.into(),
            min,
            max,
        }
    }

    pub fn check(&self, value: f64) -> Result<(), ParamBoundsError> {
        if value < self.min || value > self.max {
            Err(ParamBoundsError::OutOfBounds {
                name: self.name.clone(),
                value,
                min: self.min,
                max: self.max,
            })
        } else {
            Ok(())
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParamViolation {
    pub param_name: String,
    pub value: f64,
    pub min: f64,
    pub max: f64,
}

#[derive(Debug, thiserror::Error)]
pub enum ParamBoundsError {
    #[error("param '{name}' value {value} out of bounds [{min}, {max}]")]
    OutOfBounds {
        name: String,
        value: f64,
        min: f64,
        max: f64,
    },
}

/// Validate a map of param_name -> value against a set of bounds.
/// Returns all violations (not just the first).
pub fn check_all_params(
    params: &HashMap<String, f64>,
    bounds: &[ParamBound],
) -> Vec<ParamViolation> {
    let mut violations = Vec::new();
    for bound in bounds {
        if let Some(&value) = params.get(&bound.name) {
            if bound.check(value).is_err() {
                violations.push(ParamViolation {
                    param_name: bound.name.clone(),
                    value,
                    min: bound.min,
                    max: bound.max,
                });
            }
        }
    }
    violations
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_params(pairs: &[(&str, f64)]) -> HashMap<String, f64> {
        pairs.iter().map(|(k, v)| (k.to_string(), *v)).collect()
    }

    #[test]
    fn in_bounds_param_ok() {
        let bound = ParamBound::new("fee_rate", 0.0, 1.0);
        assert!(bound.check(0.5).is_ok());
        assert!(bound.check(0.0).is_ok());
        assert!(bound.check(1.0).is_ok());
    }

    #[test]
    fn out_of_bounds_param_detected() {
        let bound = ParamBound::new("fee_rate", 0.0, 1.0);
        assert!(bound.check(-0.1).is_err());
        assert!(bound.check(1.1).is_err());

        let bounds = vec![bound];
        let params = make_params(&[("fee_rate", 2.5)]);
        let violations = check_all_params(&params, &bounds);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].param_name, "fee_rate");
    }

    #[test]
    fn multiple_violations_all_returned() {
        let bounds = vec![
            ParamBound::new("fee_rate", 0.0, 1.0),
            ParamBound::new("max_peers", 1.0, 100.0),
            ParamBound::new("timeout_secs", 1.0, 60.0),
        ];
        let params = make_params(&[
            ("fee_rate", 5.0),    // out of bounds
            ("max_peers", 0.0),   // out of bounds
            ("timeout_secs", 30.0), // in bounds
        ]);
        let violations = check_all_params(&params, &bounds);
        assert_eq!(violations.len(), 2);
        let names: Vec<&str> = violations.iter().map(|v| v.param_name.as_str()).collect();
        assert!(names.contains(&"fee_rate"));
        assert!(names.contains(&"max_peers"));
    }

    #[test]
    fn empty_params_is_ok() {
        let bounds = vec![ParamBound::new("fee_rate", 0.0, 1.0)];
        let params = HashMap::new();
        let violations = check_all_params(&params, &bounds);
        assert!(violations.is_empty());
    }
}
