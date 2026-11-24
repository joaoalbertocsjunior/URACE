//! Product profile with similarity scoring.
//!
//! Ported from `product_profile.py` and parts of `product_similarity.py`.
//!
//! The profile is the canonical input to feature matching. No authority —
//! observations only; profile data never grants permissions.

use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum ProfileError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("invalid profile: {0}")]
    Invalid(String),
}

/// Observed capability and baseline metrics for a managed product.
///
/// No authority — observations only; profile data never grants permissions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObservedProfile {
    pub product_id: String,
    /// Human-readable product capability description (required for feature matching).
    pub capability: String,
    /// Lines of code in the codebase.
    pub codebase_loc: Option<i64>,
    /// Programming languages detected.
    pub codebase_languages: Vec<String>,
    /// Number of passing tests.
    pub test_pass_count: Option<i64>,
    /// Number of failing tests.
    pub test_fail_count: Option<i64>,
    /// ISO-8601 UTC timestamp of last update.
    pub updated_at: String,
}

impl ObservedProfile {
    /// Validate and return any warnings. Empty = ready for matching.
    pub fn validate(&self) -> Vec<String> {
        let mut warnings = Vec::new();
        if self.capability.trim().is_empty() {
            warnings.push(
                "product_profile missing required field for matching: 'capability'".to_owned(),
            );
        }
        if let Some(loc) = self.codebase_loc {
            if loc < 0 {
                warnings.push("product_profile.codebase_loc must be non-negative".to_owned());
            }
        }
        warnings
    }

    /// Returns `true` if the profile is ready for feature matching.
    pub fn ready_for_matching(&self) -> bool {
        self.validate().is_empty()
    }

    /// Returns a serialisable snapshot suitable for embedding in audit events.
    pub fn snapshot(&self) -> serde_json::Value {
        json!({
            "capability": self.capability,
            "codebase_loc": self.codebase_loc,
            "codebase_languages": self.codebase_languages,
            "test_pass_count": self.test_pass_count,
            "test_fail_count": self.test_fail_count,
            "ready_for_matching": self.ready_for_matching(),
        })
    }
}

/// TF-IDF cosine similarity between two capability strings.
///
/// Returns a float in `[0.0, 1.0]`. Both documents form the local corpus so IDF
/// is computed over the pair — sufficient for pairwise comparison.
pub fn intent_similarity(text_a: &str, text_b: &str) -> f64 {
    let tok_a = tokenize(text_a);
    let tok_b = tokenize(text_b);
    if tok_a.is_empty() || tok_b.is_empty() {
        return 0.0;
    }
    let idf = compute_idf(&[tok_a.clone(), tok_b.clone()]);
    let vec_a = tfidf_vector(&tok_a, &idf);
    let vec_b = tfidf_vector(&tok_b, &idf);
    cosine(&vec_a, &vec_b)
}

// ── TF-IDF helpers ─────────────────────────────────────────────────────────────

static STOP_WORDS: &[&str] = &[
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "it", "its", "this", "that", "as",
    "so", "not", "no", "if", "then", "than", "more", "most", "any", "all",
];

fn tokenize(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    lower
        .split(|c: char| !c.is_alphanumeric())
        .filter(|t| t.len() > 1 && !STOP_WORDS.contains(t))
        .map(str::to_owned)
        .collect()
}

fn compute_idf(corpus: &[Vec<String>]) -> HashMap<String, f64> {
    let n = corpus.len() as f64;
    let mut df: HashMap<String, f64> = HashMap::new();
    for doc in corpus {
        let unique: std::collections::HashSet<&String> = doc.iter().collect();
        for term in unique {
            *df.entry(term.clone()).or_insert(0.0) += 1.0;
        }
    }
    df.into_iter()
        .map(|(term, count)| (term, ((n + 1.0) / (count + 1.0)).ln() + 1.0))
        .collect()
}

fn tfidf_vector(tokens: &[String], idf: &HashMap<String, f64>) -> HashMap<String, f64> {
    if tokens.is_empty() {
        return HashMap::new();
    }
    let total = tokens.len() as f64;
    let mut tf: HashMap<String, f64> = HashMap::new();
    for t in tokens {
        *tf.entry(t.clone()).or_insert(0.0) += 1.0;
    }
    tf.into_iter()
        .map(|(term, count)| {
            let idf_val = idf.get(&term).copied().unwrap_or(1.0);
            (term, (count / total) * idf_val)
        })
        .collect()
}

fn cosine(a: &HashMap<String, f64>, b: &HashMap<String, f64>) -> f64 {
    let dot: f64 = a.iter().filter_map(|(k, v)| b.get(k).map(|bv| v * bv)).sum();
    let mag_a: f64 = a.values().map(|v| v * v).sum::<f64>().sqrt();
    let mag_b: f64 = b.values().map(|v| v * v).sum::<f64>().sqrt();
    if mag_a == 0.0 || mag_b == 0.0 {
        return 0.0;
    }
    (dot / (mag_a * mag_b)).min(1.0)
}

/// Append-only store for product profiles backed by a HMAC-signed JSONL journal.
pub struct ProfileStore {
    journal: Journal,
}

impl ProfileStore {
    /// Open (or create) a profile store at `path` with HMAC key `hmac_key`.
    pub fn open(
        path: impl AsRef<std::path::Path>,
        hmac_key: [u8; 32],
    ) -> Result<Self, ProfileError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(ProfileStore { journal })
    }

    /// Record (append) a product profile observation.
    pub fn record(&self, profile: &ObservedProfile) -> Result<(), ProfileError> {
        let warnings = profile.validate();
        for w in &warnings {
            tracing::warn!("{}", w);
        }
        let payload = serde_json::to_value(profile)?;
        self.journal.append("PRODUCT_PROFILE_OBSERVED", payload)?;
        Ok(())
    }

    /// Return the latest observed profile for `product_id`, or `None`.
    pub fn latest_for(&self, product_id: &str) -> Result<Option<ObservedProfile>, ProfileError> {
        let entries = self.journal.verify_integrity()?;
        let profile = entries
            .into_iter()
            .filter(|e| e.kind == "PRODUCT_PROFILE_OBSERVED")
            .filter_map(|e| serde_json::from_value::<ObservedProfile>(e.payload).ok())
            .filter(|p| p.product_id == product_id)
            .last();
        Ok(profile)
    }

    /// Return all profile observations for `product_id`.
    pub fn all_for(&self, product_id: &str) -> Result<Vec<ObservedProfile>, ProfileError> {
        let entries = self.journal.verify_integrity()?;
        let profiles = entries
            .into_iter()
            .filter(|e| e.kind == "PRODUCT_PROFILE_OBSERVED")
            .filter_map(|e| serde_json::from_value::<ObservedProfile>(e.payload).ok())
            .filter(|p| p.product_id == product_id)
            .collect();
        Ok(profiles)
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

impl ObservedProfile {
    pub fn new(product_id: impl Into<String>, capability: impl Into<String>) -> Self {
        ObservedProfile {
            product_id: product_id.into(),
            capability: capability.into(),
            codebase_loc: None,
            codebase_languages: Vec::new(),
            test_pass_count: None,
            test_fail_count: None,
            updated_at: now_iso8601(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"profile-store-key-32bytes-pad---";

    #[test]
    fn profile_validates_capability_required() {
        let p = ObservedProfile::new("p1", "");
        let warnings = p.validate();
        assert!(!warnings.is_empty());
        assert!(warnings[0].contains("capability"));
    }

    #[test]
    fn profile_valid_when_capability_set() {
        let p = ObservedProfile::new("p1", "a fast key-value cache");
        assert!(p.validate().is_empty());
        assert!(p.ready_for_matching());
    }

    #[test]
    fn intent_similarity_identical_texts() {
        let sim = intent_similarity("fast key value store", "fast key value store");
        assert!(sim > 0.99, "identical texts must have similarity ~1.0, got {}", sim);
    }

    #[test]
    fn intent_similarity_different_texts() {
        let sim = intent_similarity("key value store", "image recognition neural network");
        assert!(sim < 0.3, "unrelated texts must have low similarity, got {}", sim);
    }

    #[test]
    fn profile_store_roundtrip() {
        let dir = tempdir().unwrap();
        let store = ProfileStore::open(dir.path().join("profiles.jsonl"), KEY).unwrap();

        let mut p = ObservedProfile::new("prod-1", "a web api service");
        p.codebase_loc = Some(5000);
        p.test_pass_count = Some(120);
        store.record(&p).unwrap();

        let latest = store.latest_for("prod-1").unwrap().unwrap();
        assert_eq!(latest.capability, "a web api service");
        assert_eq!(latest.codebase_loc, Some(5000));
    }
}
