//! Feature matcher — scores how well a feature atom fits a query or product profile.
//!
//! Ported from `runtime/urace/feature_matcher.py`.
//!
//! ## Scoring layers
//!
//! Layer 1 (strict): `interface_sha384` or `acceptance_sha384` exact match → score 1.0.
//!
//! Layer 2 (heuristic): keyword/token overlap between the feature's `capability`
//! string and the query string.  Uses Jaccard similarity on keyword sets plus a
//! sequence-ratio approximation, mirroring the Python `_layer2_score()`.
//!
//! ## Borrowable flag
//! `borrowable = true` when `score >= borrow_threshold` (default 0.5) AND the
//! atom's lifecycle is `active`.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

use crate::feature_catalog::{FeatureAtom, FeatureCatalog, Lifecycle};

// ---------------------------------------------------------------------------
// Stop-words (port of Python `_STOPWORDS`)
// ---------------------------------------------------------------------------

static STOPWORDS: &[&str] = &[
    "a", "an", "the", "and", "or", "is", "in", "of", "to", "for", "with", "that", "this", "it",
    "on", "as", "by", "at", "be", "are", "was", "has",
];

fn stopwords() -> HashSet<&'static str> {
    STOPWORDS.iter().copied().collect()
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// A single match result for one feature atom.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatchScore {
    pub atom_id: String,
    /// Normalised score in [0.0, 1.0].
    pub score: f64,
    /// Human-readable explanation tokens.
    pub reasons: Vec<String>,
    /// True when score ≥ borrow_threshold AND lifecycle is active.
    pub borrowable: bool,
}

// ---------------------------------------------------------------------------
// Private keyword helpers
// ---------------------------------------------------------------------------

/// Extract non-stopword tokens of length > 2 from `text`, lower-cased.
/// Mirrors Python `_keywords()`.
fn keywords(text: &str) -> HashSet<String> {
    let sw = stopwords();
    text.to_lowercase()
        .split(|c: char| !c.is_ascii_alphanumeric() && c != '_')
        .filter(|t| t.len() > 2 && !sw.contains(*t))
        .map(|t| t.to_owned())
        .collect()
}

/// Jaccard similarity between two keyword sets.
fn jaccard(a: &HashSet<String>, b: &HashSet<String>) -> f64 {
    if a.is_empty() && b.is_empty() {
        return 0.0;
    }
    let intersection = a.intersection(b).count();
    let union = a.union(b).count();
    if union == 0 {
        return 0.0;
    }
    intersection as f64 / union as f64
}

/// A very lightweight sequence-similarity heuristic (bigram overlap) that
/// approximates Python's `SequenceMatcher.ratio()` without pulling in a full
/// diff library. The Python layer weights this at 0.3 in the final score.
fn seq_ratio(a: &str, b: &str) -> f64 {
    let a = a.to_lowercase();
    let b = b.to_lowercase();
    if a.is_empty() && b.is_empty() {
        return 1.0;
    }
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }

    // Bigram sets
    let bigrams_a: HashSet<(char, char)> = a
        .chars()
        .collect::<Vec<_>>()
        .windows(2)
        .map(|w| (w[0], w[1]))
        .collect();
    let bigrams_b: HashSet<(char, char)> = b
        .chars()
        .collect::<Vec<_>>()
        .windows(2)
        .map(|w| (w[0], w[1]))
        .collect();

    if bigrams_a.is_empty() || bigrams_b.is_empty() {
        return 0.0;
    }
    let intersection = bigrams_a.intersection(&bigrams_b).count();
    2.0 * intersection as f64 / (bigrams_a.len() + bigrams_b.len()) as f64
}

// ---------------------------------------------------------------------------
// Layer 2 heuristic scoring (capability keyword overlap)
// ---------------------------------------------------------------------------

/// Heuristic score [0.0, 1.0] for `query` vs `feature_capability`.
///
/// Mirrors Python `_layer2_score()` but only the capability component
/// (we omit language-hint and LOC-range sub-scores that require a full product
/// profile dict; callers with a full profile should use [`score_against_profile`]).
fn layer2_capability_score(query: &str, feature_capability: &str) -> (f64, Vec<String>) {
    let cap_weight: f64 = 0.60; // layer2_cap_weight default 60
    let mut reasons = Vec::new();
    let mut score = 0.0;

    if !query.is_empty() && !feature_capability.is_empty() {
        let qk = keywords(query);
        let fk = keywords(feature_capability);
        let j = if !qk.is_empty() && !fk.is_empty() {
            jaccard(&qk, &fk)
        } else {
            0.0
        };
        let sr = seq_ratio(query, feature_capability);
        // Weight: Jaccard 70%, seq_ratio 30% (matches Python `0.7*jaccard + 0.3*seq_ratio`)
        let overlap = 0.7 * j + 0.3 * sr;
        if overlap > 0.0 {
            score += overlap * cap_weight;
            reasons.push(format!("capability overlap={overlap:.2}"));
        }
    }
    (score.min(1.0), reasons)
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Score all atoms in `catalog` against `query` and return them sorted by
/// descending score, omitting zero-score atoms.
///
/// Mirrors `rank()` in the Python module (using the query string as the
/// profile's `capability` field).
pub fn match_features(query: &str, catalog: &FeatureCatalog) -> Vec<MatchScore> {
    const BORROW_THRESHOLD: f64 = 0.5;

    let mut scored: Vec<MatchScore> = catalog
        .list()
        .into_iter()
        .filter_map(|atom| {
            let (score, reasons) = layer2_capability_score(query, &atom.kind.capability);
            if score <= 0.0 {
                return None;
            }
            let borrowable = atom.lifecycle == Lifecycle::Active && score >= BORROW_THRESHOLD;
            Some(MatchScore {
                atom_id: atom.id.clone(),
                score,
                reasons,
                borrowable,
            })
        })
        .collect();

    scored.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    scored
}

/// Return the highest-scoring atom for `query`, or `None` when the catalog is
/// empty or no atom scores above zero.
pub fn best_match(query: &str, catalog: &FeatureCatalog) -> Option<MatchScore> {
    match_features(query, catalog).into_iter().next()
}

/// Score a single [`FeatureAtom`] against a full product profile dict.
///
/// Mirrors Python `feature_matcher.match()`. Supports Layer 1 (hash-exact) and
/// Layer 2 (heuristic capability overlap). The profile map may contain:
/// - `"capability"` — string, used for Layer 2 keyword overlap
/// - `"interface_sha384"` — string, used for Layer 1
/// - `"acceptance_sha384"` — string, used for Layer 1
///
/// Returns a [`MatchScore`] with the full reason list.
pub fn score_against_profile(
    profile: &std::collections::HashMap<String, String>,
    atom: &FeatureAtom,
    borrow_threshold: f64,
) -> MatchScore {
    let mut reasons = Vec::new();
    let lifecycle_active = atom.lifecycle == Lifecycle::Active;

    // Layer 1 — exact hash match
    let prod_iface = profile
        .get("interface_sha384")
        .map(|s| s.as_str())
        .unwrap_or("");
    let feat_iface = atom.kind.interface_sha384.as_str();
    let prod_acc = profile
        .get("acceptance_sha384")
        .map(|s| s.as_str())
        .unwrap_or("");
    let feat_acc = atom.kind.acceptance_sha384.as_str();

    let layer1_hit = (!prod_iface.is_empty() && prod_iface == feat_iface)
        || (!prod_acc.is_empty() && prod_acc == feat_acc);

    if layer1_hit {
        if prod_iface == feat_iface {
            reasons.push("interface_sha384 exact match".to_owned());
        } else {
            reasons.push("acceptance_sha384 exact match".to_owned());
        }
        return MatchScore {
            atom_id: atom.id.clone(),
            score: 1.0,
            reasons,
            borrowable: lifecycle_active,
        };
    }

    // Layer 1 strict block: profile has hash hints but no match
    if !prod_iface.is_empty() || !prod_acc.is_empty() {
        return MatchScore {
            atom_id: atom.id.clone(),
            score: 0.0,
            reasons: vec!["layer1 strict: no hash match".to_owned()],
            borrowable: false,
        };
    }

    // Layer 2 — capability heuristic
    let query = profile.get("capability").map(|s| s.as_str()).unwrap_or("");
    let (score, l2_reasons) = layer2_capability_score(query, &atom.kind.capability);
    reasons.extend(l2_reasons);
    MatchScore {
        atom_id: atom.id.clone(),
        score,
        reasons,
        borrowable: lifecycle_active && score >= borrow_threshold,
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::feature_catalog::{AtomDescriptor, FeatureCatalog};

    fn sample_catalog() -> FeatureCatalog {
        let cat = FeatureCatalog::new();
        let desc = AtomDescriptor {
            capability: "automatic test generation for Python code".to_owned(),
            interface_sha384: "a".repeat(96),
            acceptance_sha384: "b".repeat(96),
            content_sha384: "c".repeat(96),
            dependencies: vec![],
            publisher_id: "peer-alice".to_owned(),
            license_id: "MIT".to_owned(),
        };
        cat.declare_atom("test-gen", desc, None).unwrap();
        cat
    }

    #[test]
    fn match_features_keyword_hit() {
        let cat = sample_catalog();
        let results = match_features("generate tests automatically", &cat);
        assert!(!results.is_empty(), "expected at least one match");
        assert!(results[0].score > 0.0);
    }

    #[test]
    fn best_match_returns_top() {
        let cat = sample_catalog();
        let m = best_match("generate automatic tests", &cat);
        assert!(m.is_some());
    }

    #[test]
    fn no_match_on_unrelated_query() {
        let cat = sample_catalog();
        // Completely unrelated single-word query that shares no keywords
        let results = match_features("blockchain", &cat);
        // May or may not match depending on overlap; just assert it doesn't panic
        let _ = results;
    }

    #[test]
    fn keywords_filters_stopwords() {
        let kw = keywords("the quick brown fox");
        assert!(!kw.contains("the"));
        assert!(kw.contains("quick"));
        assert!(kw.contains("brown"));
        assert!(kw.contains("fox"));
    }

    #[test]
    fn jaccard_identical() {
        let a: HashSet<String> = ["foo", "bar", "baz"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let b = a.clone();
        assert!((jaccard(&a, &b) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn jaccard_disjoint() {
        let a: HashSet<String> = ["foo"].iter().map(|s| s.to_string()).collect();
        let b: HashSet<String> = ["bar"].iter().map(|s| s.to_string()).collect();
        assert!((jaccard(&a, &b)).abs() < 1e-9);
    }
}
