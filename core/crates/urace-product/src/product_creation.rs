//! Product creation: `ProductCreationRequest`, `ProductFactory`.
//!
//! Ported from `product_creation.py`. Handles explicit product bootstrap
//! requests from owner prose.
//!
//! # Key invariants
//! - A new product cannot take ownership of runtime or trial workflows.
//! - `ProductFactory::create()` requires non-empty, bounded descriptions.
//! - Creation records are append-only and never mutated.

use serde::{Deserialize, Serialize};
use thiserror::Error;
use uuid::Uuid;

pub const SCHEMA: &str = "product-intent-bootstrap-v1";
/// Maximum description size in bytes.
pub const MAX_DESCRIPTION_BYTES: usize = 65536;

#[derive(Debug, Error)]
pub enum CreationError {
    #[error("invalid description: {0}")]
    InvalidDescription(String),
    #[error("invalid name: {0}")]
    InvalidName(String),
    #[error("product already exists: {0}")]
    AlreadyExists(String),
    #[error("authority required for: {0}")]
    AuthorityRequired(String),
}

/// A validated product creation request from owner prose.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductCreationRequest {
    pub schema: String,
    pub product_id: String,
    pub name: String,
    pub description: String,
    pub description_sha256: String,
    pub bootstrap_status: String,
    /// ISO-8601 UTC timestamp.
    pub created_at: String,
    pub working_implementation_verified: bool,
    pub native_calls: u32,
}

/// Factory for creating new products from owner prose.
pub struct ProductFactory;

impl ProductFactory {
    /// Create a new product from `description`.
    ///
    /// # Invariants
    /// - Description must be non-empty and ≤ 65 536 bytes.
    /// - Name must be non-empty, ≤ 100 characters, and contain no control chars.
    /// - A new product cannot enable `runtime_workflow` (§invariant from CLAUDE.md).
    pub fn create(
        description: &str,
        name: Option<&str>,
    ) -> Result<ProductCreationRequest, CreationError> {
        // Validate description.
        if description.trim().is_empty() {
            return Err(CreationError::InvalidDescription(
                "description must be non-empty".to_owned(),
            ));
        }
        if description.len() > MAX_DESCRIPTION_BYTES {
            return Err(CreationError::InvalidDescription(format!(
                "description exceeds maximum size of {} bytes",
                MAX_DESCRIPTION_BYTES
            )));
        }

        // Derive or validate name.
        let resolved_name = match name {
            Some(n) => {
                let n = n.trim();
                if n.is_empty() || n.len() > 100 {
                    return Err(CreationError::InvalidName(
                        "name must be 1–100 non-empty characters".to_owned(),
                    ));
                }
                if n.chars().any(|c| (c as u32) < 32) {
                    return Err(CreationError::InvalidName(
                        "name must not contain control characters".to_owned(),
                    ));
                }
                n.to_owned()
            }
            None => format!("New product {}", &Uuid::new_v4().to_string()[..8]),
        };

        // Compute description SHA-256.
        let description_sha256 = {
            use sha2::{Digest, Sha256};
            let mut h = Sha256::new();
            h.update(description.as_bytes());
            hex::encode(h.finalize())
        };

        let product_id = format!("prod-{}", Uuid::new_v4().to_string().replace('-', ""));

        Ok(ProductCreationRequest {
            schema: SCHEMA.to_owned(),
            product_id,
            name: resolved_name,
            description: description.trim().to_owned(),
            description_sha256,
            bootstrap_status: "NEEDS_ACCEPTANCE_DESIGN".to_owned(),
            created_at: now_iso8601(),
            working_implementation_verified: false,
            native_calls: 0,
        })
    }

    /// Parse owner text and determine whether it is an explicit creation request.
    ///
    /// Returns `true` if the text begins with a creation verb followed by a new
    /// product reference — e.g., "create a new app", "build a service", etc.
    pub fn is_explicit_creation(text: &str) -> bool {
        let lower = text.trim().to_lowercase();

        let creation_verbs = ["create", "build", "make", "bootstrap", "start"];
        let product_nouns = [
            "new product",
            "new app",
            "new application",
            "new project",
            "new tool",
            "new service",
            "new website",
            "new system",
        ];

        let starts_with_verb = creation_verbs.iter().any(|v| {
            lower.starts_with(v)
                || lower.starts_with(&format!("please {}", v))
                || lower.starts_with(&format!("can you {}", v))
                || lower.starts_with(&format!("could you {}", v))
        });

        let contains_product_noun = product_nouns.iter().any(|n| lower.contains(n));

        starts_with_verb && contains_product_noun
    }
}

fn now_iso8601() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    format!("{}Z", secs)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn create_with_name() {
        let req = ProductFactory::create("Build a fast search engine", Some("MySearch")).unwrap();
        assert_eq!(req.name, "MySearch");
        assert_eq!(req.schema, SCHEMA);
        assert_eq!(req.bootstrap_status, "NEEDS_ACCEPTANCE_DESIGN");
        assert!(!req.working_implementation_verified);
        assert_eq!(req.native_calls, 0);
    }

    #[test]
    fn create_without_name_generates_one() {
        let req = ProductFactory::create("Build a fast search engine", None).unwrap();
        assert!(req.name.starts_with("New product "));
    }

    #[test]
    fn empty_description_rejected() {
        assert!(matches!(
            ProductFactory::create("", None),
            Err(CreationError::InvalidDescription(_))
        ));
        assert!(matches!(
            ProductFactory::create("   ", None),
            Err(CreationError::InvalidDescription(_))
        ));
    }

    #[test]
    fn description_sha256_is_stable() {
        let r1 = ProductFactory::create("hello world", Some("n1")).unwrap();
        let r2 = ProductFactory::create("hello world", Some("n2")).unwrap();
        assert_eq!(r1.description_sha256, r2.description_sha256);
    }

    #[test]
    fn control_char_in_name_rejected() {
        let result = ProductFactory::create("some description", Some("bad\x01name"));
        assert!(matches!(result, Err(CreationError::InvalidName(_))));
    }

    #[test]
    fn is_explicit_creation_detection() {
        assert!(ProductFactory::is_explicit_creation("create a new app"));
        assert!(ProductFactory::is_explicit_creation("Build a new service"));
        assert!(!ProductFactory::is_explicit_creation(
            "add a feature to the existing app"
        ));
        assert!(!ProductFactory::is_explicit_creation("how does this work?"));
    }
}
