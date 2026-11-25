//! Product profile, type, similarity.
//!
//! Ports:
//!   - `product_type_detector.py` → `ProductTypeDetector` (keyword matching, no ML)
//!   - `product_profile.py`       → `ProductProfile`
//!   - `product_similarity.py`    → `similarity_score` (Jaccard + name token overlap)
//!   - `runtime_product.py`       → `RuntimeProduct`

use std::collections::HashSet;

use serde::{Deserialize, Serialize};

// ── ProductType ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProductType {
    Software,
    Documentation,
    Analysis,
    Dataset,
    Other(String),
}

impl std::fmt::Display for ProductType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Software => write!(f, "software"),
            Self::Documentation => write!(f, "documentation"),
            Self::Analysis => write!(f, "analysis"),
            Self::Dataset => write!(f, "dataset"),
            Self::Other(s) => write!(f, "other:{s}"),
        }
    }
}

// ── ProductProfile ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductProfile {
    pub product_id: String,
    pub name: String,
    pub product_type: ProductType,
    pub description: String,
    pub tags: Vec<String>,
    pub version: String,
    pub created_at: String,
    pub updated_at: String,
}

// ── ProductSimilarity ─────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductSimilarity {
    pub product_id_a: String,
    pub product_id_b: String,
    /// Jaccard + name token overlap score, clamped to [0.0, 1.0].
    pub score: f64,
    pub computed_at: String,
}

// ── Similarity computation ────────────────────────────────────────────────────

/// Compute similarity between two `ProductProfile`s.
///
/// Algorithm (no ML, no embedding deps):
///   1. Jaccard similarity on tag sets.
///   2. Token overlap on lowercased name tokens.
///   3. Final = 0.7 * jaccard + 0.3 * name_overlap
///
/// Returns a float in [0.0, 1.0].
pub fn similarity_score(a: &ProductProfile, b: &ProductProfile) -> f64 {
    let tags_a: HashSet<String> = a.tags.iter().map(|t| t.to_lowercase()).collect();
    let tags_b: HashSet<String> = b.tags.iter().map(|t| t.to_lowercase()).collect();

    let jaccard = if tags_a.is_empty() && tags_b.is_empty() {
        1.0
    } else {
        let intersection = tags_a.intersection(&tags_b).count() as f64;
        let union = tags_a.union(&tags_b).count() as f64;
        if union == 0.0 {
            0.0
        } else {
            intersection / union
        }
    };

    let name_overlap = token_overlap(&a.name, &b.name);

    let score = 0.7 * jaccard + 0.3 * name_overlap;
    score.clamp(0.0, 1.0)
}

fn tokenize(s: &str) -> HashSet<String> {
    s.to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|t| t.len() > 1)
        .map(|t| t.to_owned())
        .collect()
}

fn token_overlap(a: &str, b: &str) -> f64 {
    let ta = tokenize(a);
    let tb = tokenize(b);
    if ta.is_empty() && tb.is_empty() {
        return 1.0;
    }
    let intersection = ta.intersection(&tb).count() as f64;
    let union = ta.union(&tb).count() as f64;
    if union == 0.0 {
        0.0
    } else {
        intersection / union
    }
}

// ── ProductTypeDetector ───────────────────────────────────────────────────────

/// Keyword-based product type detector (no ML).
///
/// Mirrors `product_type_detector.py::detect_product_types` but operates on
/// text metadata (name, description, tags) rather than a filesystem scan.
pub struct ProductTypeDetector;

impl ProductTypeDetector {
    pub fn detect(name: &str, description: &str, tags: &[String]) -> ProductType {
        let combined = format!("{} {} {}", name, description, tags.join(" ")).to_lowercase();

        // Keyword sets — same signal vocabulary as the Python file scanner.
        let software_keywords = [
            "software",
            "app",
            "application",
            "api",
            "library",
            "framework",
            "tool",
            "service",
            "cli",
            "code",
            "rust",
            "python",
            "javascript",
            "typescript",
            "golang",
            "java",
            "binary",
            "executable",
            "package",
            "crate",
            "module",
            "backend",
            "frontend",
            "server",
            "client",
            "sdk",
            "plugin",
        ];
        let doc_keywords = [
            "documentation",
            "docs",
            "guide",
            "manual",
            "readme",
            "specification",
            "spec",
            "reference",
            "tutorial",
            "wiki",
            "markdown",
            "text",
            "report",
            "whitepaper",
        ];
        let analysis_keywords = [
            "analysis",
            "analytics",
            "report",
            "dashboard",
            "visualization",
            "chart",
            "metric",
            "statistics",
            "notebook",
            "jupyter",
            "data science",
            "insights",
        ];
        let dataset_keywords = [
            "dataset",
            "data",
            "csv",
            "parquet",
            "jsonl",
            "database",
            "schema",
            "corpus",
            "collection",
            "records",
            "table",
            "sqlite",
            "tsv",
        ];

        let sw = count_hits(&combined, &software_keywords);
        let doc = count_hits(&combined, &doc_keywords);
        let analysis = count_hits(&combined, &analysis_keywords);
        let ds = count_hits(&combined, &dataset_keywords);

        let max = sw.max(doc).max(analysis).max(ds);
        if max == 0 {
            return ProductType::Software; // default, same as Python
        }
        if sw == max {
            ProductType::Software
        } else if doc == max {
            ProductType::Documentation
        } else if analysis == max {
            ProductType::Analysis
        } else {
            ProductType::Dataset
        }
    }
}

fn count_hits(text: &str, keywords: &[&str]) -> usize {
    keywords.iter().filter(|&&kw| text.contains(kw)).count()
}

// ── RuntimeProduct ────────────────────────────────────────────────────────────

/// Runtime product identity (port of `runtime_product.py`).
///
/// Observations only — never confers authority.
pub struct RuntimeProduct;

impl RuntimeProduct {
    pub const PRODUCT_ID_PREFIX: &'static str = "urace-runtime";

    /// Stable content hash over a list of (filename, content) pairs.
    pub fn engine_identity(sources: &[(&str, &[u8])]) -> String {
        use sha2::{Digest, Sha256};
        let mut digest = Sha256::new();
        let mut sorted: Vec<_> = sources.iter().collect();
        sorted.sort_by_key(|(name, _)| *name);
        for (name, content) in sorted {
            digest.update(name.as_bytes());
            digest.update(b":");
            digest.update(content);
            digest.update(b"\n");
        }
        hex::encode(digest.finalize())
    }

    pub fn registration() -> serde_json::Value {
        serde_json::json!({
            "id": Self::PRODUCT_ID_PREFIX,
            "name": "urace runtime",
            "source": "runtime-codebase",
            "kind": "runtime"
        })
    }

    /// Minimum quality gate for accepting a runtime improvement.
    pub fn quality_gate(
        quality_gate_metric: Option<&str>,
        minimum_delta: Option<f64>,
    ) -> serde_json::Value {
        serde_json::json!({
            "metric": quality_gate_metric.unwrap_or("executable_benchmark_score"),
            "minimum_delta": minimum_delta.unwrap_or(5.0),
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn profile(id: &str, name: &str, tags: &[&str]) -> ProductProfile {
        ProductProfile {
            product_id: id.to_owned(),
            name: name.to_owned(),
            product_type: ProductType::Software,
            description: String::new(),
            tags: tags.iter().map(|t| t.to_string()).collect(),
            version: "0.1.0".into(),
            created_at: "2024-01-01T00:00:00Z".into(),
            updated_at: "2024-01-01T00:00:00Z".into(),
        }
    }

    #[test]
    fn similarity_identical_tags() {
        let a = profile("a", "My API", &["rust", "api", "web"]);
        let b = profile("b", "My API", &["rust", "api", "web"]);
        let s = similarity_score(&a, &b);
        assert!(
            (s - 1.0).abs() < 1e-9,
            "identical profiles should score 1.0, got {s}"
        );
    }

    #[test]
    fn similarity_no_overlap() {
        let a = profile("a", "Alpha Service", &["rust", "api"]);
        let b = profile("b", "Beta Library", &["python", "ml"]);
        let s = similarity_score(&a, &b);
        assert!(s < 0.5, "no overlap should give low score, got {s}");
    }

    #[test]
    fn similarity_partial_overlap() {
        let a = profile("a", "My Tool", &["rust", "cli", "api"]);
        let b = profile("b", "Their Tool", &["rust", "web", "api"]);
        let s = similarity_score(&a, &b);
        assert!(s > 0.0 && s < 1.0, "partial overlap: {s}");
    }

    #[test]
    fn similarity_clamped() {
        let a = profile("a", "X", &[]);
        let b = profile("b", "Y", &[]);
        let s = similarity_score(&a, &b);
        assert!((0.0..=1.0).contains(&s));
    }

    #[test]
    fn detector_software_default() {
        let pt = ProductTypeDetector::detect("My CLI Tool", "A command line application", &[]);
        assert_eq!(pt, ProductType::Software);
    }

    #[test]
    fn detector_documentation() {
        let pt = ProductTypeDetector::detect(
            "API Docs",
            "Complete documentation and reference guide for the API",
            &["documentation".to_owned(), "markdown".to_owned()],
        );
        assert_eq!(pt, ProductType::Documentation);
    }

    #[test]
    fn detector_dataset() {
        let pt = ProductTypeDetector::detect(
            "Training Dataset",
            "A large CSV dataset for machine learning",
            &["dataset".to_owned(), "csv".to_owned()],
        );
        assert_eq!(pt, ProductType::Dataset);
    }

    #[test]
    fn detector_analysis() {
        let pt = ProductTypeDetector::detect(
            "Sales Analytics Dashboard",
            "Visualization and analytics report with charts and metrics",
            &["analytics".to_owned(), "dashboard".to_owned()],
        );
        assert_eq!(pt, ProductType::Analysis);
    }

    #[test]
    fn runtime_product_engine_identity_stable() {
        let sources = [
            ("foo.rs", b"fn main() {}".as_slice()),
            ("bar.rs", b"pub fn bar() {}".as_slice()),
        ];
        let h1 = RuntimeProduct::engine_identity(&sources);
        let h2 = RuntimeProduct::engine_identity(&sources);
        assert_eq!(h1, h2);
    }

    #[test]
    fn runtime_product_engine_identity_order_independent() {
        let a = [
            ("foo.rs", b"fn main() {}".as_slice()),
            ("bar.rs", b"fn bar() {}".as_slice()),
        ];
        let b = [
            ("bar.rs", b"fn bar() {}".as_slice()),
            ("foo.rs", b"fn main() {}".as_slice()),
        ];
        assert_eq!(
            RuntimeProduct::engine_identity(&a),
            RuntimeProduct::engine_identity(&b),
            "identity should be stable regardless of source order"
        );
    }
}
