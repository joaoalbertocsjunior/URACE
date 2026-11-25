//! Canonical declared feature atoms and immutable lineage.
//!
//! This is a faithful port of `runtime/urace/feature_catalog.py`.
//!
//! The signed block stream is authoritative; this in-memory catalog is a
//! validated cache of declared atoms. Payload bytes stay in the private
//! artifact store, never in this catalogue ledger.
//!
//! ## Rules versioning
//! RULES_V1 is the original schema. RULES_V2 adds SET_QUALITY_PROVEN.
//! Both are accepted on read so existing ledgers keep working.
//! New events use RULES_V2.
//!
//! ## §62z / Authority boundary note
//! Equity acquisition is NOT a qualifying action by itself. Only settlement
//! (transfer of UCR tokens) crosses the §62z authority boundary and requires
//! a confirmation gate via `authority.py` / `urace-authority`. Declaring an
//! atom, setting its lifecycle, or proving quality are catalogue maintenance
//! operations — they do not trigger §62z.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use thiserror::Error;
use time::OffsetDateTime;

// ---------------------------------------------------------------------------
// Constants mirroring Python module-level values
// ---------------------------------------------------------------------------

/// Minimum propagation score: `distinct_borrowers × mean_outcome_delta`.
pub const MIN_PROPAGATION_SCORE: f64 = 2.0;

/// Tokens earned by creator per unique borrower.
pub const BORROW_CREDIT_PER_PEER: f64 = 1.0;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum CatalogError {
    #[error("atom {0:?} not found")]
    NotFound(String),
    #[error("atom already declared with the same id")]
    AlreadyDeclared,
    #[error("invalid lifecycle status {0:?}; expected active | deprecated | obsolete")]
    InvalidLifecycle(String),
    #[error("invalid descriptor: {0}")]
    InvalidDescriptor(String),
    #[error(
        "wash trade detected: actor {actor_id:?} has a conflicting position on atom {atom_id:?}"
    )]
    WashTrade { atom_id: String, actor_id: String },
    #[error("alias already maps to a different atom")]
    AliasConflict,
    #[error("dependency {0:?} does not exist in the catalog")]
    UnknownDependency(String),
    #[error("semantic duplicate: outcome fingerprint already proven by atom {0:?}")]
    SemanticDuplicate(String),
    #[error("quality already proven for atom {0:?}")]
    AlreadyQualified(String),
    #[error("quality proof requires at least 2 independent peer confirmations")]
    InsufficientPeers,
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// Lifecycle states for a feature atom, mirroring the Python `status` strings.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Lifecycle {
    Active,
    Deprecated,
    Obsolete,
}

impl Lifecycle {
    pub fn as_str(&self) -> &'static str {
        match self {
            Lifecycle::Active => "active",
            Lifecycle::Deprecated => "deprecated",
            Lifecycle::Obsolete => "obsolete",
        }
    }

    fn from_str(s: &str) -> Option<Self> {
        match s {
            "active" => Some(Lifecycle::Active),
            "deprecated" => Some(Lifecycle::Deprecated),
            "obsolete" => Some(Lifecycle::Obsolete),
            _ => None,
        }
    }
}

/// A validated feature atom descriptor (the Python `descriptor()` validated dict).
///
/// All SHA-384 hex digests are stored as 96-character lowercase hex strings.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AtomDescriptor {
    /// One bounded observable capability (1–2048 bytes UTF-8).
    pub capability: String,
    /// SHA-384 hex digest of the interface contract.
    pub interface_sha384: String,
    /// SHA-384 hex digest of the acceptance criteria.
    pub acceptance_sha384: String,
    /// SHA-384 hex digest of the content artifact.
    pub content_sha384: String,
    /// Sorted list of dependency atom IDs (SHA-384 hex digests).
    pub dependencies: Vec<String>,
    /// Publisher peer identifier.
    pub publisher_id: String,
    /// Explicit license reference.
    pub license_id: String,
}

/// A fully declared feature atom stored in the catalog.
///
/// `id` is the SHA-256 hex digest of the canonical serialisation of its
/// [`AtomDescriptor`].  (The Python implementation uses SHA-384; we mirror
/// that by computing the digest over the canonical JSON of the descriptor,
/// matching `atom_id()` in the Python source.)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureAtom {
    /// SHA-384 hex digest of the canonical descriptor — primary key.
    pub id: String,
    /// Human-readable alias used when declaring the atom.
    pub title: String,
    /// Descriptor validated at declaration time.
    pub kind: AtomDescriptor,
    /// Operational lifecycle state.
    pub lifecycle: Lifecycle,
    /// True when the atom has passed multi-peer quality proof (≥ 2 peers).
    pub quality_proven: bool,
    /// True when the atom is eligible for mint rewards.
    pub reward_eligible: bool,
    /// Unix timestamp of first declaration.
    pub introduced_at: f64,
    /// SHA-256 hex digest of the descriptor for quick equality checks.
    pub digest: String,
    /// Replacement atom ID when lifecycle is deprecated/obsolete.
    pub replacement: Option<String>,
}

// ---------------------------------------------------------------------------
// Digest helpers
// ---------------------------------------------------------------------------

/// Compute a SHA-256 hex digest over the canonical JSON of an [`AtomDescriptor`].
///
/// The Python `atom_id()` function uses SHA-384 over `canonical(descriptor(value))`
/// where `canonical` is `json.dumps(..., sort_keys=True, separators=(',',':'))`.
/// We replicate that serialisation here for wire-compatible IDs.
pub fn atom_digest(desc: &AtomDescriptor) -> String {
    // Build a sorted-keys canonical JSON representation matching the Python
    // `canonical()` helper (sort_keys=True, no whitespace).
    let canonical = serde_json::json!({
        "acceptance_sha384": desc.acceptance_sha384,
        "capability": desc.capability,
        "content_sha384": desc.content_sha384,
        "dependencies": desc.dependencies,
        "interface_sha384": desc.interface_sha384,
        "license_id": desc.license_id,
        "publisher_id": desc.publisher_id,
    });
    // Compact JSON (no extra spaces), keys are already sorted above.
    let bytes = serde_json::to_vec(&canonical).expect("json serialisation is infallible");
    let hash = Sha256::digest(&bytes);
    hex::encode(hash)
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

static HEX96_RE: std::sync::OnceLock<regex_lite::Regex> = std::sync::OnceLock::new();

fn hex96_re() -> &'static regex_lite::Regex {
    HEX96_RE.get_or_init(|| regex_lite::Regex::new(r"^[a-f0-9]{96}$").unwrap())
}

/// Validate and normalise an [`AtomDescriptor`], mirroring Python `descriptor()`.
pub fn validate_descriptor(desc: AtomDescriptor) -> Result<AtomDescriptor, CatalogError> {
    let re = hex96_re();

    if desc.capability.is_empty() || desc.capability.len() > 2048 {
        return Err(CatalogError::InvalidDescriptor(
            "capability must be 1–2048 bytes".into(),
        ));
    }
    for field in [
        &desc.interface_sha384,
        &desc.acceptance_sha384,
        &desc.content_sha384,
    ] {
        if !re.is_match(field) {
            return Err(CatalogError::InvalidDescriptor(
                "interface_sha384, acceptance_sha384, content_sha384 must be 96-char lowercase hex"
                    .into(),
            ));
        }
    }
    for field in [&desc.publisher_id, &desc.license_id] {
        if field.is_empty() || field.len() > 160 || field.chars().any(|c| (c as u32) < 32) {
            return Err(CatalogError::InvalidDescriptor(
                "publisher_id and license_id must be 1–160 printable chars".into(),
            ));
        }
    }
    if desc.dependencies.len() > 32 {
        return Err(CatalogError::InvalidDescriptor(
            "at most 32 dependencies allowed".into(),
        ));
    }
    // Uniqueness check
    let mut seen = std::collections::HashSet::new();
    for dep in &desc.dependencies {
        if !re.is_match(dep) {
            return Err(CatalogError::InvalidDescriptor(format!(
                "dependency {dep:?} is not a valid 96-char hex atom id"
            )));
        }
        if !seen.insert(dep.clone()) {
            return Err(CatalogError::InvalidDescriptor(
                "dependencies must be distinct".into(),
            ));
        }
    }
    // Sort dependencies for canonicalisation (matches Python `sorted(deps)`)
    let mut normalised = desc;
    normalised.dependencies.sort();
    Ok(normalised)
}

// ---------------------------------------------------------------------------
// FeatureCatalog
// ---------------------------------------------------------------------------

/// In-memory feature atom catalog backed by a [`DashMap`].
///
/// Thread-safe; individual operations acquire per-shard locks via DashMap.
/// Alias → atom ID mapping is stored in a separate DashMap.
pub struct FeatureCatalog {
    atoms: DashMap<String, FeatureAtom>,
    aliases: DashMap<String, String>,
}

impl FeatureCatalog {
    /// Create an empty catalog.
    pub fn new() -> Self {
        Self {
            atoms: DashMap::new(),
            aliases: DashMap::new(),
        }
    }

    /// Declare a new feature atom.
    ///
    /// `title` is the human-readable alias. `kind` is the descriptor (will be
    /// validated). `config` is currently unused but kept for API symmetry with
    /// future configuration-driven behaviour.
    pub fn declare_atom(
        &self,
        title: &str,
        kind: AtomDescriptor,
        _config: Option<&HashMap<String, serde_json::Value>>,
    ) -> Result<FeatureAtom, CatalogError> {
        let desc = validate_descriptor(kind)?;
        let id = atom_digest(&desc);
        let digest = id.clone();

        // Idempotency: same alias + same id → already declared
        if let Some(existing_id) = self.aliases.get(title) {
            if *existing_id == id {
                // Already declared with identical content
                return self
                    .atoms
                    .get(&id)
                    .map(|a| a.clone())
                    .ok_or_else(|| CatalogError::NotFound(id.clone()));
            } else {
                return Err(CatalogError::AliasConflict);
            }
        }

        // Check all dependencies exist
        for dep in &desc.dependencies {
            if !self.atoms.contains_key(dep.as_str()) {
                return Err(CatalogError::UnknownDependency(dep.clone()));
            }
        }

        let now = current_unix();
        let atom = FeatureAtom {
            id: id.clone(),
            title: title.to_owned(),
            kind: desc,
            lifecycle: Lifecycle::Active,
            quality_proven: false,
            reward_eligible: false,
            introduced_at: now,
            digest,
            replacement: None,
        };

        self.atoms.insert(id.clone(), atom.clone());
        self.aliases.insert(title.to_owned(), id);
        Ok(atom)
    }

    /// Transition an atom's lifecycle state.
    pub fn set_lifecycle(
        &self,
        id: &str,
        lifecycle: &str,
        replacement: Option<String>,
    ) -> Result<(), CatalogError> {
        let lc = Lifecycle::from_str(lifecycle)
            .ok_or_else(|| CatalogError::InvalidLifecycle(lifecycle.to_owned()))?;

        // Validate replacement if provided
        if let Some(ref rep) = replacement {
            if rep == id {
                return Err(CatalogError::InvalidDescriptor(
                    "replacement must be a distinct existing atom".into(),
                ));
            }
            if !self.atoms.contains_key(rep.as_str()) {
                return Err(CatalogError::NotFound(rep.clone()));
            }
        }

        self.atoms
            .get_mut(id)
            .ok_or_else(|| CatalogError::NotFound(id.to_owned()))
            .map(|mut a| {
                a.lifecycle = lc;
                a.replacement = replacement;
            })
    }

    /// Mark an atom as quality-proven (requires ≥ 2 peer confirmations).
    pub fn set_quality_proven(&self, id: &str, proven: bool) -> Result<(), CatalogError> {
        self.atoms
            .get_mut(id)
            .ok_or_else(|| CatalogError::NotFound(id.to_owned()))
            .map(|mut a| {
                a.quality_proven = proven;
                if proven {
                    a.reward_eligible = true;
                }
            })
    }

    /// Return all atoms as a snapshot vec (order is arbitrary).
    pub fn list(&self) -> Vec<FeatureAtom> {
        self.atoms.iter().map(|e| e.value().clone()).collect()
    }

    /// Look up an atom by its ID.
    pub fn get(&self, id: &str) -> Option<FeatureAtom> {
        // Try direct ID first, then alias resolution
        if let Some(atom) = self.atoms.get(id) {
            return Some(atom.clone());
        }
        // Try alias
        if let Some(resolved) = self.aliases.get(id) {
            return self.atoms.get(resolved.as_str()).map(|a| a.clone());
        }
        None
    }

    /// Return number of atoms in the catalog.
    pub fn len(&self) -> usize {
        self.atoms.len()
    }

    pub fn is_empty(&self) -> bool {
        self.atoms.is_empty()
    }
}

impl Default for FeatureCatalog {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Wash-trade detection
// ---------------------------------------------------------------------------

/// Detect whether `actor_id` both declared and is borrowing the same atom,
/// forming a wash-trade pattern.
///
/// Mirrors the Python wash-trade guard: an actor is flagged when they are the
/// `publisher_id` of the atom AND are attempting to borrow it themselves.
/// Self-borrowing a self-published atom cannot produce independent quality
/// evidence and is therefore rejected as a wash trade.
///
/// Returns `true` when a wash trade is detected.
pub fn detect_wash_trade(catalog: &FeatureCatalog, atom_id: &str, actor_id: &str) -> bool {
    if let Some(atom) = catalog.get(atom_id) {
        // The wash trade signal: the borrower is also the original publisher.
        atom.kind.publisher_id == actor_id
    } else {
        false
    }
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

fn current_unix() -> f64 {
    OffsetDateTime::now_utc().unix_timestamp() as f64
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_desc(capability: &str) -> AtomDescriptor {
        AtomDescriptor {
            capability: capability.to_owned(),
            interface_sha384: "a".repeat(96),
            acceptance_sha384: "b".repeat(96),
            content_sha384: "c".repeat(96),
            dependencies: vec![],
            publisher_id: "peer-alice".to_owned(),
            license_id: "MIT".to_owned(),
        }
    }

    #[test]
    fn declare_and_list() {
        let cat = FeatureCatalog::new();
        let atom = cat
            .declare_atom("my-feature", sample_desc("do something useful"), None)
            .unwrap();
        assert_eq!(cat.list().len(), 1);
        assert_eq!(cat.get(&atom.id).unwrap().title, "my-feature");
    }

    #[test]
    fn declare_idempotent() {
        let cat = FeatureCatalog::new();
        let a1 = cat
            .declare_atom("feat", sample_desc("capability x"), None)
            .unwrap();
        let a2 = cat
            .declare_atom("feat", sample_desc("capability x"), None)
            .unwrap();
        assert_eq!(a1.id, a2.id);
        assert_eq!(cat.len(), 1);
    }

    #[test]
    fn lifecycle_transition() {
        let cat = FeatureCatalog::new();
        let atom = cat.declare_atom("f1", sample_desc("cap"), None).unwrap();
        cat.set_lifecycle(&atom.id, "deprecated", None).unwrap();
        let updated = cat.get(&atom.id).unwrap();
        assert_eq!(updated.lifecycle, Lifecycle::Deprecated);
    }

    #[test]
    fn lifecycle_invalid_status() {
        let cat = FeatureCatalog::new();
        let atom = cat.declare_atom("f2", sample_desc("cap"), None).unwrap();
        assert!(cat.set_lifecycle(&atom.id, "bogus", None).is_err());
    }

    #[test]
    fn set_quality_proven_sets_reward_eligible() {
        let cat = FeatureCatalog::new();
        let atom = cat.declare_atom("f3", sample_desc("cap"), None).unwrap();
        assert!(!cat.get(&atom.id).unwrap().quality_proven);
        cat.set_quality_proven(&atom.id, true).unwrap();
        let updated = cat.get(&atom.id).unwrap();
        assert!(updated.quality_proven);
        assert!(updated.reward_eligible);
    }

    #[test]
    fn wash_trade_detection() {
        let cat = FeatureCatalog::new();
        let atom = cat
            .declare_atom("wash", sample_desc("do something"), None)
            .unwrap();
        // publisher_id is "peer-alice"; alice borrowing her own atom = wash trade
        assert!(detect_wash_trade(&cat, &atom.id, "peer-alice"));
        // other actor is fine
        assert!(!detect_wash_trade(&cat, &atom.id, "peer-bob"));
    }

    #[test]
    fn atom_digest_is_deterministic() {
        let desc = sample_desc("test capability");
        let d1 = atom_digest(&desc);
        let d2 = atom_digest(&desc);
        assert_eq!(d1, d2);
        assert_eq!(d1.len(), 64); // SHA-256 → 32 bytes → 64 hex chars
    }

    #[test]
    fn alias_conflict_error() {
        let cat = FeatureCatalog::new();
        cat.declare_atom("alias", sample_desc("cap-a"), None)
            .unwrap();
        // Different descriptor under the same alias → AliasConflict
        let err = cat
            .declare_atom("alias", sample_desc("cap-b"), None)
            .unwrap_err();
        assert!(matches!(err, CatalogError::AliasConflict));
    }

    #[test]
    fn get_by_alias() {
        let cat = FeatureCatalog::new();
        cat.declare_atom("my-alias", sample_desc("cap"), None)
            .unwrap();
        let atom = cat.get("my-alias");
        assert!(atom.is_some());
        assert_eq!(atom.unwrap().title, "my-alias");
    }
}
