//! In-memory product store backed by an append-only JSONL file.
//!
//! All mutations persist to `products.jsonl` via `urace-ledger::atomic_append_jsonl`.

use std::path::{Path, PathBuf};

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::product::ProductProfile;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ProductError {
    #[error("product {0} already exists")]
    AlreadyExists(String),
    #[error("product {0} not found")]
    NotFound(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}

// ── JSONL row ─────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
struct ProductRow {
    op: String, // "create" | "update"
    profile: ProductProfile,
}

// ── ProductStore ──────────────────────────────────────────────────────────────

/// Thread-safe in-memory product registry.
///
/// Mutations are appended to `products.jsonl` for durability. On construction,
/// the store replays the log to restore state.
pub struct ProductStore {
    map: DashMap<String, ProductProfile>,
    log_path: PathBuf,
}

impl ProductStore {
    /// Create or rehydrate a product store from `root/products.jsonl`.
    pub fn new(root: &Path) -> Result<Self, ProductError> {
        std::fs::create_dir_all(root)?;
        let log_path = root.join("products.jsonl");
        let map: DashMap<String, ProductProfile> = DashMap::new();

        // Replay log.
        if log_path.exists() {
            let text = std::fs::read_to_string(&log_path)?;
            for line in text.lines() {
                if let Ok(row) = serde_json::from_str::<ProductRow>(line) {
                    map.insert(row.profile.product_id.clone(), row.profile);
                }
            }
        }

        Ok(Self { map, log_path })
    }

    /// Persist `profile` to the JSONL log.
    fn append(&self, op: &str, profile: &ProductProfile) -> Result<(), ProductError> {
        let row = serde_json::json!({
            "op": op,
            "profile": profile,
        });
        urace_ledger::atomic_append_jsonl(&self.log_path, &row)
            .map_err(|e| ProductError::Io(std::io::Error::other(e.to_string())))
    }

    /// Register a new product profile.
    ///
    /// Returns `Err(AlreadyExists)` if `product_id` is already registered.
    pub fn create(&self, profile: ProductProfile) -> Result<(), ProductError> {
        if self.map.contains_key(&profile.product_id) {
            return Err(ProductError::AlreadyExists(profile.product_id.clone()));
        }
        self.append("create", &profile)?;
        self.map.insert(profile.product_id.clone(), profile);
        Ok(())
    }

    /// Return a clone of `ProductProfile` for `id`, or `None` if not found.
    pub fn get(&self, id: &str) -> Option<ProductProfile> {
        self.map.get(id).map(|v| v.clone())
    }

    /// Return a snapshot of all registered profiles.
    pub fn list(&self) -> Vec<ProductProfile> {
        self.map.iter().map(|e| e.value().clone()).collect()
    }

    /// Update an existing profile.
    ///
    /// Returns `Err(NotFound)` if `id` is not registered.
    pub fn update(&self, id: &str, profile: ProductProfile) -> Result<(), ProductError> {
        if !self.map.contains_key(id) {
            return Err(ProductError::NotFound(id.to_owned()));
        }
        self.append("update", &profile)?;
        self.map.insert(id.to_owned(), profile);
        Ok(())
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::product::ProductType;

    fn make_profile(id: &str, name: &str) -> ProductProfile {
        ProductProfile {
            product_id: id.to_owned(),
            name: name.to_owned(),
            product_type: ProductType::Software,
            description: "test product".into(),
            tags: vec!["rust".into(), "test".into()],
            version: "0.1.0".into(),
            created_at: "2024-01-01T00:00:00Z".into(),
            updated_at: "2024-01-01T00:00:00Z".into(),
        }
    }

    #[test]
    fn create_and_get() {
        let dir = tempfile::tempdir().unwrap();
        let store = ProductStore::new(dir.path()).unwrap();
        store.create(make_profile("p1", "Product One")).unwrap();
        let p = store.get("p1").unwrap();
        assert_eq!(p.name, "Product One");
    }

    #[test]
    fn create_duplicate_fails() {
        let dir = tempfile::tempdir().unwrap();
        let store = ProductStore::new(dir.path()).unwrap();
        store.create(make_profile("p1", "Product One")).unwrap();
        let r = store.create(make_profile("p1", "Product One Again"));
        assert!(matches!(r, Err(ProductError::AlreadyExists(_))));
    }

    #[test]
    fn update_existing() {
        let dir = tempfile::tempdir().unwrap();
        let store = ProductStore::new(dir.path()).unwrap();
        store.create(make_profile("p1", "Old Name")).unwrap();
        let mut updated = make_profile("p1", "New Name");
        updated.version = "0.2.0".into();
        store.update("p1", updated).unwrap();
        assert_eq!(store.get("p1").unwrap().name, "New Name");
    }

    #[test]
    fn update_missing_fails() {
        let dir = tempfile::tempdir().unwrap();
        let store = ProductStore::new(dir.path()).unwrap();
        let r = store.update("missing", make_profile("missing", "X"));
        assert!(matches!(r, Err(ProductError::NotFound(_))));
    }

    #[test]
    fn list_returns_all() {
        let dir = tempfile::tempdir().unwrap();
        let store = ProductStore::new(dir.path()).unwrap();
        store.create(make_profile("p1", "P1")).unwrap();
        store.create(make_profile("p2", "P2")).unwrap();
        assert_eq!(store.list().len(), 2);
    }

    #[test]
    fn rehydrate_from_log() {
        let dir = tempfile::tempdir().unwrap();
        {
            let store = ProductStore::new(dir.path()).unwrap();
            store.create(make_profile("p1", "Persistent Product")).unwrap();
        }
        // Re-open — should replay log.
        let store2 = ProductStore::new(dir.path()).unwrap();
        let p = store2.get("p1").unwrap();
        assert_eq!(p.name, "Persistent Product");
    }
}
