//! Portfolio management: `Portfolio`, `PortfolioEntry`, `PortfolioStore`.
//!
//! `PortfolioStore` is append-only — entries are written via a HMAC-signed
//! `urace_ledger::Journal` and are never deleted or mutated after write.
//!
//! Ported from `portfolio.py` / `portfolio_storage.py`.

use serde::{Deserialize, Serialize};
use serde_json::json;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum PortfolioError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("invalid portfolio entry: {0}")]
    Invalid(String),
}

/// A single variant entry in the portfolio.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortfolioEntry {
    /// Unique variant name (1–64 safe chars).
    pub name: String,
    /// Parent variant name, or `None` for the baseline.
    pub parent: Option<String>,
    /// Generation number.
    pub generation: u32,
    /// Current lifecycle state.
    pub status: String,
    /// The mutation description applied to produce this variant.
    pub mutation: String,
    /// Expected improvement hypothesis.
    pub hypothesis: String,
    /// ISO-8601 UTC timestamp.
    pub created_at: String,
}

impl PortfolioEntry {
    /// Validate the entry name against the safe-name rules from `portfolio_storage.py`.
    pub fn validate_name(name: &str) -> Result<(), PortfolioError> {
        if name.is_empty() || name.len() > 64 {
            return Err(PortfolioError::Invalid(
                "name must be 1–64 characters".to_owned(),
            ));
        }
        let valid = name.chars().enumerate().all(|(i, c)| {
            if i == 0 {
                c.is_alphanumeric()
            } else {
                c.is_alphanumeric() || c == '.' || c == '_' || c == '-'
            }
        });
        if !valid {
            return Err(PortfolioError::Invalid(format!(
                "name {:?} contains invalid characters; use alphanumeric, '.', '_', '-'",
                name
            )));
        }
        Ok(())
    }
}

/// An overall portfolio containing its contract, metadata, and variant entries.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Portfolio {
    pub portfolio_id: String,
    pub metric: String,
    /// "maximize" or "minimize".
    pub direction: String,
    pub objective: String,
    pub minimum_evidence: u32,
    pub max_active: u32,
    /// Currently selected variant name, if any.
    pub selected: Option<String>,
    /// ISO-8601 UTC timestamp.
    pub created_at: String,
}

/// Append-only store for portfolio records backed by a HMAC-signed JSONL journal.
pub struct PortfolioStore {
    journal: Journal,
}

impl PortfolioStore {
    /// Open (or create) a portfolio store at `path` with HMAC key `hmac_key`.
    pub fn open(
        path: impl AsRef<std::path::Path>,
        hmac_key: [u8; 32],
    ) -> Result<Self, PortfolioError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(PortfolioStore { journal })
    }

    /// Record (append) a portfolio initialisation event.
    pub fn record_portfolio(&self, portfolio: &Portfolio) -> Result<(), PortfolioError> {
        let payload = serde_json::to_value(portfolio)?;
        self.journal.append("PORTFOLIO_CREATED", payload)?;
        Ok(())
    }

    /// Add a new variant entry to the portfolio (append-only).
    pub fn add_entry(&self, entry: &PortfolioEntry) -> Result<(), PortfolioError> {
        PortfolioEntry::validate_name(&entry.name)?;
        let payload = serde_json::to_value(entry)?;
        self.journal.append("PORTFOLIO_ENTRY_ADDED", payload)?;
        Ok(())
    }

    /// Record a selection event (which variant was selected).
    pub fn record_selection(
        &self,
        portfolio_id: &str,
        variant_name: &str,
    ) -> Result<(), PortfolioError> {
        let payload = json!({
            "portfolio_id": portfolio_id,
            "selected": variant_name,
        });
        self.journal.append("PORTFOLIO_SELECTION", payload)?;
        Ok(())
    }

    /// Return all portfolio creation records.
    pub fn all_portfolios(&self) -> Result<Vec<Portfolio>, PortfolioError> {
        let entries = self.journal.verify_integrity()?;
        let portfolios = entries
            .into_iter()
            .filter(|e| e.kind == "PORTFOLIO_CREATED")
            .filter_map(|e| serde_json::from_value::<Portfolio>(e.payload).ok())
            .collect();
        Ok(portfolios)
    }

    /// Return all portfolio entries (variants).
    pub fn all_entries(&self) -> Result<Vec<PortfolioEntry>, PortfolioError> {
        let entries = self.journal.verify_integrity()?;
        let variants = entries
            .into_iter()
            .filter(|e| e.kind == "PORTFOLIO_ENTRY_ADDED")
            .filter_map(|e| serde_json::from_value::<PortfolioEntry>(e.payload).ok())
            .collect();
        Ok(variants)
    }

    /// Return all entries for a given portfolio.
    pub fn entries_for_portfolio(
        &self,
        portfolio_id: &str,
    ) -> Result<Vec<PortfolioEntry>, PortfolioError> {
        // Entries don't directly carry portfolio_id; return all and let the caller filter.
        // This is a simplified view — in a full port the entry would carry portfolio_id.
        let _ = portfolio_id;
        self.all_entries()
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

impl Portfolio {
    /// Create a new portfolio.
    pub fn new(
        portfolio_id: impl Into<String>,
        metric: impl Into<String>,
        direction: impl Into<String>,
        objective: impl Into<String>,
        minimum_evidence: u32,
        max_active: u32,
    ) -> Self {
        Portfolio {
            portfolio_id: portfolio_id.into(),
            metric: metric.into(),
            direction: direction.into(),
            objective: objective.into(),
            minimum_evidence,
            max_active,
            selected: None,
            created_at: now_iso8601(),
        }
    }
}

impl PortfolioEntry {
    /// Create a new portfolio entry.
    pub fn new(
        name: impl Into<String>,
        parent: Option<String>,
        generation: u32,
        mutation: impl Into<String>,
        hypothesis: impl Into<String>,
    ) -> Self {
        PortfolioEntry {
            name: name.into(),
            parent,
            generation,
            status: "PENDING".to_owned(),
            mutation: mutation.into(),
            hypothesis: hypothesis.into(),
            created_at: now_iso8601(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"portfolio-store-32bytes-pad-----";

    #[test]
    fn add_and_list_entries() {
        let dir = tempdir().unwrap();
        let store = PortfolioStore::open(dir.path().join("portfolio.jsonl"), KEY).unwrap();

        let p = Portfolio::new("p1", "test_pass_rate", "maximize", "improve tests", 3, 5);
        store.record_portfolio(&p).unwrap();

        let e1 = PortfolioEntry::new("alpha", None, 1, "add caching", "cache reduces latency");
        let e2 = PortfolioEntry::new(
            "beta",
            Some("alpha".to_owned()),
            2,
            "tune params",
            "better defaults",
        );
        store.add_entry(&e1).unwrap();
        store.add_entry(&e2).unwrap();

        let entries = store.all_entries().unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].name, "alpha");
        assert_eq!(entries[1].name, "beta");
        assert_eq!(entries[1].parent, Some("alpha".to_owned()));
    }

    #[test]
    fn store_roundtrip_preserves_data() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("portfolio.jsonl");

        {
            let store = PortfolioStore::open(&path, KEY).unwrap();
            let e = PortfolioEntry::new("v1", None, 1, "baseline", "control");
            store.add_entry(&e).unwrap();
        }

        // Re-open: data must persist.
        {
            let store = PortfolioStore::open(&path, KEY).unwrap();
            let entries = store.all_entries().unwrap();
            assert_eq!(entries.len(), 1);
            assert_eq!(entries[0].name, "v1");
        }
    }

    #[test]
    fn invalid_name_rejected() {
        let dir = tempdir().unwrap();
        let store = PortfolioStore::open(dir.path().join("portfolio.jsonl"), KEY).unwrap();
        let mut e = PortfolioEntry::new("valid-name", None, 1, "m", "h");
        e.name = "has spaces here".to_owned();
        assert!(store.add_entry(&e).is_err());
    }

    #[test]
    fn name_starts_with_non_alphanumeric_rejected() {
        assert!(PortfolioEntry::validate_name("-invalid").is_err());
        assert!(PortfolioEntry::validate_name("valid-name").is_ok());
        assert!(PortfolioEntry::validate_name("v1.2_a").is_ok());
    }
}
