//! Owner-declared distribution terms.
//!
//! Ported from `runtime/urace/feature_policy.py` (21 lines of dense Python).
//!
//! These are local rules declared by the atom's owner. They are **never** a
//! proof of rights or a guarantee of a fair price. The policy merely expresses
//! the owner's current distribution intent.
//!
//! ## Schema
//! Schema identifier: `"urace-feature-policy-v1"`.
//!
//! ## Access modes
//! - `reviewed-direct` — owner must review before access is granted
//! - `open` — freely accessible (requires a reusable license reference, not
//!   `LicenseRef-Owner-Reviewed-*`)
//!
//! ## §62z / Authority boundary note
//! Policies are informational declarations. They do not by themselves trigger
//! any qualifying action. Setting `payment_enabled = true` in the effective
//! policy output is a future stub — actual UCR transfer always goes through
//! `urace-authority`.

use serde::{Deserialize, Serialize};
use thiserror::Error;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

pub const SCHEMA: &str = "urace-feature-policy-v1";
pub const ACCESS_REVIEWED_DIRECT: &str = "reviewed-direct";
pub const ACCESS_OPEN: &str = "open";

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum PolicyError {
    #[error("unsupported feature policy schema")]
    UnsupportedSchema,
    #[error("unknown feature access policy {0:?}")]
    UnknownAccess(String),
    #[error("explicit bounded license reference required")]
    InvalidLicenseId,
    #[error("boolean feature controls required")]
    InvalidBooleanControl,
    #[error("invalid explicit release time")]
    InvalidReleaseTime,
    #[error("essential shared-core features cannot be exclusively paywalled")]
    EssentialMustBeOpen,
    #[error(
        "open sharing requires explicit reusable license terms (not LicenseRef-Owner-Reviewed-*)"
    )]
    OpenRequiresReusableLicense,
    #[error("timed open release requires explicit reusable license terms")]
    TimedReleaseRequiresReusableLicense,
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// A validated feature distribution policy.
///
/// Mirrors the Python `DEFAULT` dict structure plus the validated/effective
/// fields returned by `validate()` / `effective()`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FeaturePolicy {
    pub schema: String,
    /// `"reviewed-direct"` or `"open"`.
    pub access: String,
    /// Explicit license reference string (1–160 printable chars).
    pub license_id: String,
    /// True when this feature is a shared-core essential (cannot be paywalled).
    pub essential: bool,
    /// Optional Unix timestamp after which the feature becomes open.
    pub open_after_unix: Option<f64>,
    /// True when resale of this feature is permitted.
    pub resale: bool,
}

/// The effective resolved policy, computed at a given `now` timestamp.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectivePolicy {
    #[serde(flatten)]
    pub base: FeaturePolicy,
    /// `"open"` or `"reviewed-direct"` after evaluating `open_after_unix`.
    pub effective_access: String,
    /// 0 when access is open; `None` when owner review is required.
    pub usage_price_units: Option<u64>,
    /// Always false — rights require external independent verification.
    pub rights_independently_verified: bool,
    /// Always false — ownership transfer not handled by policy.
    pub ownership_transfer: bool,
    /// Always false — payment is a future settlement stub.
    pub payment_enabled: bool,
    /// `"OWNER_PRECOMMITTED_TERMS"` when open, `"OWNER_REVIEW_REQUIRED"` otherwise.
    pub release_reason: String,
    /// Always false — copy prevention cannot be guaranteed by this runtime.
    pub copy_prevention_guaranteed: bool,
}

// ---------------------------------------------------------------------------
// Default policy
// ---------------------------------------------------------------------------

/// The default policy matching the Python `DEFAULT` dict.
pub fn default_policy() -> FeaturePolicy {
    FeaturePolicy {
        schema: SCHEMA.to_owned(),
        access: ACCESS_REVIEWED_DIRECT.to_owned(),
        license_id: "LicenseRef-Owner-Reviewed-Export".to_owned(),
        essential: false,
        open_after_unix: None,
        resale: false,
    }
}

// ---------------------------------------------------------------------------
// Validate
// ---------------------------------------------------------------------------

/// Validate a [`FeaturePolicy`], mirroring Python `validate()`.
///
/// Returns the validated (possibly normalised) policy or a [`PolicyError`].
pub fn validate(policy: FeaturePolicy) -> Result<FeaturePolicy, PolicyError> {
    if policy.schema != SCHEMA {
        return Err(PolicyError::UnsupportedSchema);
    }
    if policy.access != ACCESS_REVIEWED_DIRECT && policy.access != ACCESS_OPEN {
        return Err(PolicyError::UnknownAccess(policy.access.clone()));
    }
    if policy.license_id.is_empty()
        || policy.license_id.len() > 160
        || policy.license_id.chars().any(|c| (c as u32) < 32)
    {
        return Err(PolicyError::InvalidLicenseId);
    }
    // Validate open_after_unix is a finite non-negative number if set
    if let Some(t) = policy.open_after_unix {
        if !t.is_finite() || t < 0.0 {
            return Err(PolicyError::InvalidReleaseTime);
        }
    }
    // essential → must be open
    if policy.essential && policy.access != ACCESS_OPEN {
        return Err(PolicyError::EssentialMustBeOpen);
    }
    // open access → cannot use the owner-review placeholder license
    if policy.access == ACCESS_OPEN && policy.license_id.starts_with("LicenseRef-Owner-Reviewed") {
        return Err(PolicyError::OpenRequiresReusableLicense);
    }
    // timed open release → must have a reusable license
    if policy.open_after_unix.is_some()
        && policy.license_id.starts_with("LicenseRef-Owner-Reviewed")
    {
        return Err(PolicyError::TimedReleaseRequiresReusableLicense);
    }
    Ok(policy)
}

// ---------------------------------------------------------------------------
// Effective policy
// ---------------------------------------------------------------------------

/// Compute the effective resolved policy at `now` (Unix seconds).
///
/// Mirrors Python `effective()`.
pub fn effective(policy: FeaturePolicy, now: f64) -> Result<EffectivePolicy, PolicyError> {
    let policy = validate(policy)?;
    let released =
        policy.access == ACCESS_OPEN || policy.open_after_unix.map(|t| now >= t).unwrap_or(false);
    let effective_access = if released {
        ACCESS_OPEN.to_owned()
    } else {
        ACCESS_REVIEWED_DIRECT.to_owned()
    };
    let usage_price_units = if released { Some(0) } else { None };
    let release_reason = if released {
        "OWNER_PRECOMMITTED_TERMS".to_owned()
    } else {
        "OWNER_REVIEW_REQUIRED".to_owned()
    };
    Ok(EffectivePolicy {
        base: policy,
        effective_access,
        usage_price_units,
        rights_independently_verified: false,
        ownership_transfer: false,
        payment_enabled: false,
        release_reason,
        copy_prevention_guaranteed: false,
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_policy_validates() {
        assert!(validate(default_policy()).is_ok());
    }

    #[test]
    fn open_policy_requires_reusable_license() {
        let mut p = default_policy();
        p.access = ACCESS_OPEN.to_owned();
        // Still has LicenseRef-Owner-Reviewed-Export → should fail
        assert!(matches!(
            validate(p),
            Err(PolicyError::OpenRequiresReusableLicense)
        ));
    }

    #[test]
    fn open_policy_with_valid_license() {
        let p = FeaturePolicy {
            schema: SCHEMA.to_owned(),
            access: ACCESS_OPEN.to_owned(),
            license_id: "Apache-2.0".to_owned(),
            essential: false,
            open_after_unix: None,
            resale: true,
        };
        assert!(validate(p).is_ok());
    }

    #[test]
    fn essential_must_be_open() {
        let mut p = default_policy();
        p.essential = true; // but access = reviewed-direct
        assert!(matches!(validate(p), Err(PolicyError::EssentialMustBeOpen)));
    }

    #[test]
    fn effective_open_has_zero_price() {
        let p = FeaturePolicy {
            schema: SCHEMA.to_owned(),
            access: ACCESS_OPEN.to_owned(),
            license_id: "MIT".to_owned(),
            essential: false,
            open_after_unix: None,
            resale: false,
        };
        let eff = effective(p, 1_000_000.0).unwrap();
        assert_eq!(eff.effective_access, ACCESS_OPEN);
        assert_eq!(eff.usage_price_units, Some(0));
        assert_eq!(eff.release_reason, "OWNER_PRECOMMITTED_TERMS");
    }

    #[test]
    fn effective_timed_release_before_time() {
        let p = FeaturePolicy {
            schema: SCHEMA.to_owned(),
            access: ACCESS_REVIEWED_DIRECT.to_owned(),
            license_id: "MIT".to_owned(),
            essential: false,
            open_after_unix: Some(2_000_000.0),
            resale: false,
        };
        // now < open_after_unix → still reviewed-direct
        let eff = effective(p, 1_000_000.0).unwrap();
        assert_eq!(eff.effective_access, ACCESS_REVIEWED_DIRECT);
        assert_eq!(eff.usage_price_units, None);
    }

    #[test]
    fn effective_timed_release_after_time() {
        let p = FeaturePolicy {
            schema: SCHEMA.to_owned(),
            access: ACCESS_REVIEWED_DIRECT.to_owned(),
            license_id: "MIT".to_owned(),
            essential: false,
            open_after_unix: Some(1_000_000.0),
            resale: false,
        };
        // now >= open_after_unix → open
        let eff = effective(p, 2_000_000.0).unwrap();
        assert_eq!(eff.effective_access, ACCESS_OPEN);
        assert_eq!(eff.usage_price_units, Some(0));
    }

    #[test]
    fn invalid_schema_rejected() {
        let mut p = default_policy();
        p.schema = "wrong-schema".to_owned();
        assert!(matches!(validate(p), Err(PolicyError::UnsupportedSchema)));
    }

    #[test]
    fn timed_release_with_owner_reviewed_license_rejected() {
        let p = FeaturePolicy {
            schema: SCHEMA.to_owned(),
            access: ACCESS_REVIEWED_DIRECT.to_owned(),
            license_id: "LicenseRef-Owner-Reviewed-Export".to_owned(),
            essential: false,
            open_after_unix: Some(1_000_000.0),
            resale: false,
        };
        assert!(matches!(
            validate(p),
            Err(PolicyError::TimedReleaseRequiresReusableLicense)
        ));
    }
}
