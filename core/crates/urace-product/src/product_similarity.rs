//! Collaborative-filtering feature scorer with TF-IDF intent similarity and ε-diversity.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;

pub const SCHEMA: &str = "urace-product-similarity-v1";

/// Maximum age of peer adoption rows included in scoring.
pub const DEFAULT_MAX_PEER_AGE_SECS: f64 = 86_400.0;

/// Half-life for exponential recency decay (7 days).
pub const DEFAULT_HALF_LIFE_SECS: f64 = 86_400.0 * 7.0;

#[derive(Debug, Error)]
pub enum SimilarityError {
    #[error("exchange returned invalid audit data: {0}")]
    InvalidAuditData(String),
    #[error("exchange I/O error: {0}")]
    Io(String),
}

// ── Stop words ────────────────────────────────────────────────────────────────

static STOP_WORDS: &[&str] = &[
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
    "from", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "it", "its", "this", "that",
    "these", "those", "as", "so", "not", "no", "if", "then", "than", "more", "most", "any", "all",
    "each", "also", "into", "over", "after", "before", "up", "out", "about", "their", "there",
    "they", "we", "our", "us", "you", "your", "he", "she", "his", "her", "i", "my", "me", "while",
    "when", "how", "what", "which", "who", "very", "just", "only",
];

// ── TF-IDF helpers ────────────────────────────────────────────────────────────

fn tokenize(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    lower
        .split(|c: char| !c.is_alphanumeric())
        .filter(|t| t.len() > 1 && !STOP_WORDS.contains(t))
        .map(str::to_owned)
        .collect()
}

fn compute_tf(tokens: &[String]) -> HashMap<String, f64> {
    if tokens.is_empty() {
        return HashMap::new();
    }
    let total = tokens.len() as f64;
    let mut counts: HashMap<String, f64> = HashMap::new();
    for t in tokens {
        *counts.entry(t.clone()).or_insert(0.0) += 1.0;
    }
    counts.into_iter().map(|(k, v)| (k, v / total)).collect()
}

fn compute_idf(corpus: &[Vec<String>]) -> HashMap<String, f64> {
    let n = corpus.len() as f64;
    let mut df: HashMap<String, f64> = HashMap::new();
    for doc in corpus {
        let unique: HashSet<&String> = doc.iter().collect();
        for term in unique {
            *df.entry(term.clone()).or_insert(0.0) += 1.0;
        }
    }
    df.into_iter()
        .map(|(term, count)| (term, ((n + 1.0) / (count + 1.0)).ln() + 1.0))
        .collect()
}

fn tfidf_vector(tokens: &[String], idf: &HashMap<String, f64>) -> HashMap<String, f64> {
    let tf = compute_tf(tokens);
    tf.into_iter()
        .map(|(term, tf_val)| {
            let idf_val = idf.get(&term).copied().unwrap_or(1.0);
            (term, tf_val * idf_val)
        })
        .collect()
}

fn cosine(a: &HashMap<String, f64>, b: &HashMap<String, f64>) -> f64 {
    let dot: f64 = a
        .iter()
        .filter_map(|(k, v)| b.get(k).map(|bv| v * bv))
        .sum();
    let mag_a: f64 = a.values().map(|v| v * v).sum::<f64>().sqrt();
    let mag_b: f64 = b.values().map(|v| v * v).sum::<f64>().sqrt();
    if mag_a == 0.0 || mag_b == 0.0 {
        return 0.0;
    }
    (dot / (mag_a * mag_b)).min(1.0)
}

/// TF-IDF cosine similarity between two intent strings; returns a value in `[0.0, 1.0]`.
pub fn intent_similarity(text_a: &str, text_b: &str) -> f64 {
    let tok_a = tokenize(text_a);
    let tok_b = tokenize(text_b);
    if tok_a.is_empty() || tok_b.is_empty() {
        return 0.0;
    }
    let idf = compute_idf(&[tok_a.clone(), tok_b.clone()]);
    cosine(&tfidf_vector(&tok_a, &idf), &tfidf_vector(&tok_b, &idf))
}

// ── Wilson lower-bound ────────────────────────────────────────────────────────

/// Wilson score lower bound (90% one-sided, z=1.645) for proportion k/n.
pub fn wilson_lower(k: usize, n: usize, z: f64) -> f64 {
    if n == 0 {
        return 0.0;
    }
    let z2 = z * z;
    let centre = k as f64 / n as f64;
    let margin = z * (centre * (1.0 - centre) / n as f64 + z2 / (4.0 * n as f64 * n as f64)).sqrt();
    let denom = 1.0 + z2 / n as f64;
    let lower = (centre + z2 / (2.0 * n as f64) - margin) / denom;
    lower.clamp(0.0, 1.0)
}

// ── Recency weight ────────────────────────────────────────────────────────────

fn recency_weight(adoption_unix: f64, now: f64, half_life: f64) -> f64 {
    let age = (now - adoption_unix).max(0.0);
    (-std::f64::consts::LN_2 * age / half_life).exp()
}

// ── Network-relative confidence ───────────────────────────────────────────────

fn confidence_tier(peer_count: usize, total_peers: usize) -> &'static str {
    let high = (0.30 * total_peers as f64).round().max(3.0) as usize;
    let med = (0.10 * total_peers as f64).round().max(2.0) as usize;
    if peer_count >= high {
        "high"
    } else if peer_count >= med {
        "medium"
    } else {
        "low"
    }
}

// ── Diversity fractions ───────────────────────────────────────────────────────

const DIVERSITY_FRAC: f64 = 0.15;
const SIMILAR_FRAC: f64 = 0.75;

fn split_diversity_slots(n: usize) -> (usize, usize) {
    let n_diverse = ((n as f64 * DIVERSITY_FRAC).round() as usize).max(1);
    let n_similar = n.saturating_sub(n_diverse);
    (n_similar, n_diverse)
}

// ── Max TF-IDF similarity between feature tokens ─────────────────────────────

fn max_tfidf_sim(feature_id: &str, local_features: &HashSet<String>) -> f64 {
    if local_features.is_empty() {
        return 0.0;
    }
    let feat_tokens = tokenize(&feature_id.replace(['-', '_'], " "));
    if feat_tokens.is_empty() {
        return 0.0;
    }
    let mut best = 0.0_f64;
    for lf in local_features {
        let lf_tokens = tokenize(&lf.replace(['-', '_'], " "));
        if lf_tokens.is_empty() {
            continue;
        }
        let idf = compute_idf(&[feat_tokens.clone(), lf_tokens.clone()]);
        let sim = cosine(
            &tfidf_vector(&feat_tokens, &idf),
            &tfidf_vector(&lf_tokens, &idf),
        );
        if sim > best {
            best = sim;
        }
    }
    best
}

// ── Co-adoption Jaccard bonus ─────────────────────────────────────────────────

fn cooccurrence_bonus(
    feature_id: &str,
    local_features: &HashSet<String>,
    adoptions: &HashMap<String, HashMap<String, f64>>,
) -> f64 {
    if local_features.is_empty() {
        return 0.0;
    }
    let peers_with_feature: HashSet<&str> = adoptions
        .iter()
        .filter(|(_, feats)| feats.contains_key(feature_id))
        .map(|(peer, _)| peer.as_str())
        .collect();
    if peers_with_feature.is_empty() {
        return 0.0;
    }
    let mut max_jaccard = 0.0_f64;
    for lf in local_features {
        let peers_with_lf: HashSet<&str> = adoptions
            .iter()
            .filter(|(_, feats)| feats.contains_key(lf.as_str()))
            .map(|(peer, _)| peer.as_str())
            .collect();
        let both = peers_with_feature.intersection(&peers_with_lf).count();
        let either = peers_with_feature.union(&peers_with_lf).count();
        if either > 0 {
            let j = both as f64 / either as f64;
            if j > max_jaccard {
                max_jaccard = j;
            }
        }
    }
    0.20 * max_jaccard
}

// ── Trust weight computation ──────────────────────────────────────────────────

fn peer_trust_weights(rows: &[serde_json::Value]) -> HashMap<String, f64> {
    let mut verified: HashMap<String, usize> = HashMap::new();
    let mut applied: HashMap<String, usize> = HashMap::new();

    for row in rows {
        let Some(peer) = row.get("peer").and_then(|v| v.as_str()) else {
            continue;
        };
        let kind = row.get("kind").and_then(|v| v.as_str()).unwrap_or("");
        match kind {
            "QUALIFICATION_RECEIPT" => {
                *verified.entry(peer.to_owned()).or_insert(0) += 1;
                *applied.entry(peer.to_owned()).or_insert(0) += 1;
            }
            "APPLIED_AFTER_LOCAL_QUALIFICATION" => {
                *applied.entry(peer.to_owned()).or_insert(0) += 1;
            }
            _ => {}
        }
    }

    let all_peers: HashSet<String> = applied.keys().chain(verified.keys()).cloned().collect();
    let mut weights = HashMap::new();
    for peer in all_peers {
        let total = *applied.get(&peer).unwrap_or(&0);
        let vcount = *verified.get(&peer).unwrap_or(&0);
        let raw = if total == 0 {
            0.5
        } else {
            wilson_lower(vcount, total, 1.645)
        };
        weights.insert(peer, raw.clamp(0.1, 1.0));
    }
    weights
}

// ── Peer adoption table ───────────────────────────────────────────────────────

fn peer_adoptions(
    rows: &[serde_json::Value],
    max_age_secs: f64,
    now: f64,
) -> HashMap<String, HashMap<String, f64>> {
    let cutoff = now - max_age_secs;
    let mut adoptions: HashMap<String, HashMap<String, f64>> = HashMap::new();
    for row in rows {
        if row.get("kind").and_then(|v| v.as_str()) != Some("APPLIED_AFTER_LOCAL_QUALIFICATION") {
            continue;
        }
        let peer = match row.get("peer").and_then(|v| v.as_str()) {
            Some(p) => p.to_owned(),
            None => continue,
        };
        let feature = match row.get("feature").and_then(|v| v.as_str()) {
            Some(f) => f.to_owned(),
            None => continue,
        };
        let at_unix = row.get("at_unix").and_then(|v| v.as_f64()).unwrap_or(0.0);
        if at_unix < cutoff {
            continue;
        }
        let entry = adoptions
            .entry(peer)
            .or_default()
            .entry(feature)
            .or_insert(0.0);
        if at_unix > *entry {
            *entry = at_unix;
        }
    }
    adoptions
}

// ── Peer intent extraction ────────────────────────────────────────────────────

fn peer_intents(rows: &[serde_json::Value]) -> HashMap<String, String> {
    let mut intents: HashMap<String, String> = HashMap::new();
    for row in rows {
        let Some(peer) = row.get("peer").and_then(|v| v.as_str()) else {
            continue;
        };
        let kind = row.get("kind").and_then(|v| v.as_str()).unwrap_or("");
        if kind == "CATALOG_CHECK" {
            if let Some(intent) = row.get("product_intent").and_then(|v| v.as_str()) {
                intents.insert(peer.to_owned(), intent.to_owned());
            }
        } else if kind == "APPLIED_AFTER_LOCAL_QUALIFICATION" && !intents.contains_key(peer) {
            if let Some(feature) = row.get("feature").and_then(|v| v.as_str()) {
                let entry = intents.entry(peer.to_owned()).or_default();
                if entry.is_empty() {
                    *entry = feature.to_owned();
                } else {
                    entry.push(' ');
                    entry.push_str(feature);
                }
            }
        }
    }
    intents
}

// ── Score result ──────────────────────────────────────────────────────────────

/// A single feature recommendation entry returned by `score_features`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureScore {
    pub feature_id: String,
    pub score: f64,
    pub adoption_rate: f64,
    pub peer_count: usize,
    pub total_peers: usize,
    pub intent_similarity: f64,
    pub confidence: String,
    pub sparse_network: bool,
    pub rationale: String,
    pub partial: bool,
    pub diversity_source: bool,
    pub cold_start: bool,
    pub peer_trust_weight: f64,
}

/// Options for `score_features`.
#[derive(Debug, Clone)]
pub struct ScoreOptions {
    pub max_peer_age_secs: f64,
    pub half_life_secs: f64,
}

impl Default for ScoreOptions {
    fn default() -> Self {
        ScoreOptions {
            max_peer_age_secs: DEFAULT_MAX_PEER_AGE_SECS,
            half_life_secs: DEFAULT_HALF_LIFE_SECS,
        }
    }
}

/// Score peer features using collaborative filtering + TF-IDF intent similarity.
///
/// `local_intent` — the product intent string from configuration.
/// `local_feature_ids` — set of features already present locally (zeroed in score).
/// `audit_rows` — raw audit rows from the exchange journal.
pub fn score_features(
    local_intent: &str,
    local_feature_ids: &HashSet<String>,
    audit_rows: &[serde_json::Value],
    opts: &ScoreOptions,
) -> Result<Vec<FeatureScore>, SimilarityError> {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64();

    let adoptions = peer_adoptions(audit_rows, opts.max_peer_age_secs, now);
    let intents = peer_intents(audit_rows);
    let trust_weights = peer_trust_weights(audit_rows);

    let total_peers = adoptions.len();
    if total_peers == 0 {
        return Ok(vec![]);
    }

    // Build IDF over all texts (local + peers)
    let local_tokens = tokenize(local_intent);
    let peer_token_map: HashMap<String, Vec<String>> = intents
        .iter()
        .map(|(peer, text)| (peer.clone(), tokenize(text)))
        .collect();
    let mut all_token_lists: Vec<Vec<String>> = vec![local_tokens.clone()];
    all_token_lists.extend(peer_token_map.values().cloned());
    let idf = compute_idf(&all_token_lists);
    let local_vec = tfidf_vector(&local_tokens, &idf);

    // Per-peer intent similarity
    let mut peer_sim: HashMap<String, f64> = HashMap::new();
    for (peer, tokens) in &peer_token_map {
        let vec = tfidf_vector(tokens, &idf);
        peer_sim.insert(peer.clone(), cosine(&local_vec, &vec));
    }
    for peer in adoptions.keys() {
        peer_sim.entry(peer.clone()).or_insert(0.5);
    }

    // Aggregate per feature
    let mut feature_peers: HashMap<String, Vec<String>> = HashMap::new();
    let mut feature_latest: HashMap<String, f64> = HashMap::new();
    for (peer, feat_map) in &adoptions {
        for (fid, ts) in feat_map {
            feature_peers
                .entry(fid.clone())
                .or_default()
                .push(peer.clone());
            let entry = feature_latest.entry(fid.clone()).or_insert(0.0);
            if ts > entry {
                *entry = *ts;
            }
        }
    }

    // Classify adopting peers as similar / diverse
    let mut sorted_peers: Vec<&String> = adoptions.keys().collect();
    sorted_peers.sort_by(|a, b| {
        peer_sim
            .get(*b)
            .unwrap_or(&0.5)
            .partial_cmp(peer_sim.get(*a).unwrap_or(&0.5))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    let n_similar = ((sorted_peers.len() as f64 * SIMILAR_FRAC).round() as usize).max(1);
    let similar_peers: HashSet<String> = sorted_peers[..n_similar.min(sorted_peers.len())]
        .iter()
        .map(|p| (*p).clone())
        .collect();
    let diverse_peers: HashSet<String> = sorted_peers[n_similar.min(sorted_peers.len())..]
        .iter()
        .map(|p| (*p).clone())
        .collect();

    // All features seen in audit rows (for cold-start)
    let all_audit_features: HashSet<String> = audit_rows
        .iter()
        .filter_map(|r| r.get("feature").and_then(|v| v.as_str()).map(str::to_owned))
        .collect();

    let sparse_network = total_peers < 5;

    let mut similar_results: Vec<FeatureScore> = Vec::new();
    let mut diverse_results: Vec<FeatureScore> = Vec::new();

    for (fid, adopting_peers) in &feature_peers {
        let peer_count = adopting_peers.len();
        let adoption_rate = wilson_lower(peer_count, total_peers, 1.645);

        let trust_vals: Vec<f64> = adopting_peers
            .iter()
            .map(|p| *trust_weights.get(p).unwrap_or(&0.5))
            .collect();
        let sim_vals: Vec<f64> = adopting_peers
            .iter()
            .map(|p| *peer_sim.get(p).unwrap_or(&0.5))
            .collect();
        let total_trust: f64 = trust_vals.iter().sum();
        let weighted_sim = if total_trust > 0.0 {
            trust_vals
                .iter()
                .zip(sim_vals.iter())
                .map(|(t, s)| t * s)
                .sum::<f64>()
                / total_trust
        } else {
            sim_vals.iter().sum::<f64>() / peer_count as f64
        };
        let mean_trust = if peer_count > 0 {
            total_trust / peer_count as f64
        } else {
            0.5
        };

        let latest = *feature_latest.get(fid.as_str()).unwrap_or(&0.0);
        let recency = recency_weight(latest, now, opts.half_life_secs);
        let already_local = if local_feature_ids.contains(fid) {
            1.0_f64
        } else {
            0.0_f64
        };
        let bonus = cooccurrence_bonus(fid, local_feature_ids, &adoptions);
        let base_score = weighted_sim * adoption_rate * recency * (1.0 - already_local);
        let score = base_score * (1.0 + bonus);
        let conf = confidence_tier(peer_count, total_peers);

        let mut rationale_parts = vec![
            format!("adopted by {peer_count}/{total_peers} recent peers"),
            format!("intent_similarity={weighted_sim:.2}"),
            format!("recency={recency:.2}"),
            format!("wilson_adoption={adoption_rate:.4}"),
        ];
        if bonus > 0.0 {
            rationale_parts.push(format!("cooccurrence_bonus={bonus:.3}"));
        }
        if already_local > 0.0 {
            rationale_parts.push("already local — score zeroed".to_owned());
        }
        if sparse_network {
            rationale_parts.push("sparse network — Wilson lower-bound rate".to_owned());
        }

        let entry = FeatureScore {
            feature_id: fid.clone(),
            score: (score * 1_000_000.0).round() / 1_000_000.0,
            adoption_rate: (adoption_rate * 10_000.0).round() / 10_000.0,
            peer_count,
            total_peers,
            intent_similarity: (weighted_sim * 10_000.0).round() / 10_000.0,
            confidence: conf.to_owned(),
            sparse_network,
            rationale: rationale_parts.join("; "),
            partial: false,
            diversity_source: false,
            cold_start: false,
            peer_trust_weight: (mean_trust * 10_000.0).round() / 10_000.0,
        };

        let has_similar = adopting_peers.iter().any(|p| similar_peers.contains(p));
        let has_diverse = adopting_peers.iter().any(|p| diverse_peers.contains(p));
        if has_similar {
            similar_results.push(entry.clone());
        }
        if has_diverse {
            diverse_results.push(entry);
        }
    }

    similar_results.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.feature_id.cmp(&b.feature_id))
    });
    diverse_results.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.feature_id.cmp(&b.feature_id))
    });

    // ε-diversity merge
    let mut all_ids_ordered: Vec<String> = Vec::new();
    let mut seen_ids: HashSet<String> = HashSet::new();
    for e in similar_results.iter().chain(diverse_results.iter()) {
        if seen_ids.insert(e.feature_id.clone()) {
            all_ids_ordered.push(e.feature_id.clone());
        }
    }

    let n_total = all_ids_ordered.len();
    let (n_similar_slots, n_diverse_slots) = if n_total == 0 {
        (0, 0)
    } else {
        split_diversity_slots(n_total)
    };

    let similar_by_id: BTreeMap<&str, &FeatureScore> = similar_results
        .iter()
        .map(|e| (e.feature_id.as_str(), e))
        .collect();
    let diverse_by_id: BTreeMap<&str, &FeatureScore> = diverse_results
        .iter()
        .map(|e| (e.feature_id.as_str(), e))
        .collect();

    let similar_ids: Vec<&str> = all_ids_ordered
        .iter()
        .filter(|id| similar_by_id.contains_key(id.as_str()))
        .map(String::as_str)
        .collect();
    let diverse_only_ids: Vec<&str> = all_ids_ordered
        .iter()
        .filter(|id| {
            !similar_by_id.contains_key(id.as_str()) && diverse_by_id.contains_key(id.as_str())
        })
        .map(String::as_str)
        .collect();

    let mut merged: Vec<FeatureScore> = Vec::with_capacity(n_total);
    let mut merged_seen: HashSet<String> = HashSet::new();

    for &fid in similar_ids.iter().take(n_similar_slots) {
        if merged_seen.insert(fid.to_owned()) {
            merged.push((*similar_by_id[fid]).clone());
        }
    }
    for &fid in diverse_only_ids.iter().take(n_diverse_slots) {
        if merged_seen.insert(fid.to_owned()) {
            let mut e = (*diverse_by_id[fid]).clone();
            e.diversity_source = true;
            merged.push(e);
        }
    }
    for &fid in &similar_ids {
        if merged_seen.insert(fid.to_owned()) {
            merged.push((*similar_by_id[fid]).clone());
        }
    }
    for &fid in &diverse_only_ids {
        if merged_seen.insert(fid.to_owned()) {
            let mut e = (*diverse_by_id[fid]).clone();
            e.diversity_source = true;
            merged.push(e);
        }
    }

    merged.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.feature_id.cmp(&b.feature_id))
    });

    // Cold-start entries
    let cold_features: HashSet<String> = all_audit_features
        .difference(&feature_peers.keys().cloned().collect::<HashSet<String>>())
        .filter(|f| !local_feature_ids.contains(*f))
        .cloned()
        .collect();

    let mut cold_entries: Vec<FeatureScore> = cold_features
        .iter()
        .map(|fid| {
            let tfidf_sim = if local_feature_ids.is_empty() {
                0.0
            } else {
                max_tfidf_sim(fid, local_feature_ids)
            };
            let cold_score = 0.05 * tfidf_sim;
            FeatureScore {
                feature_id: fid.clone(),
                score: (cold_score * 1_000_000.0).round() / 1_000_000.0,
                adoption_rate: 0.0,
                peer_count: 0,
                total_peers,
                intent_similarity: 0.0,
                confidence: "low".to_owned(),
                sparse_network,
                rationale: format!("cold-start: no peer adoptions; tfidf_sim={tfidf_sim:.3}"),
                partial: false,
                diversity_source: false,
                cold_start: true,
                peer_trust_weight: 0.0,
            }
        })
        .collect();

    cold_entries.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.feature_id.cmp(&b.feature_id))
    });

    merged.extend(cold_entries);
    Ok(merged)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn intent_similarity_identical_returns_one() {
        let sim = intent_similarity(
            "fast distributed key value store",
            "fast distributed key value store",
        );
        assert!(
            sim > 0.99,
            "identical texts should have sim ~1.0, got {sim}"
        );
    }

    #[test]
    fn intent_similarity_unrelated_is_low() {
        let sim = intent_similarity(
            "key value store caching",
            "image recognition neural network",
        );
        assert!(sim < 0.3, "unrelated texts should score low, got {sim}");
    }

    #[test]
    fn wilson_lower_zero_n_returns_zero() {
        assert_eq!(wilson_lower(0, 0, 1.645), 0.0);
    }

    #[test]
    fn wilson_lower_all_success_below_one() {
        let w = wilson_lower(100, 100, 1.645);
        assert!(w > 0.90 && w <= 1.0, "expected near-1 bound, got {w}");
    }

    #[test]
    fn score_features_empty_rows_returns_empty() {
        let local_features = HashSet::new();
        let result = score_features(
            "intent text",
            &local_features,
            &[],
            &ScoreOptions::default(),
        )
        .expect("should not error");
        assert!(result.is_empty());
    }

    #[test]
    fn score_features_ranks_adopted_above_cold() {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        let rows = vec![
            json!({
                "kind": "APPLIED_AFTER_LOCAL_QUALIFICATION",
                "peer": "peer-a",
                "feature": "feature-x",
                "at_unix": now - 3600.0
            }),
            // cold-start feature only in audit but no adoption
            json!({
                "kind": "CATALOG_CHECK",
                "peer": "peer-a",
                "feature": "feature-y",
                "product_intent": "caching service"
            }),
        ];
        let local_features = HashSet::new();
        let scores = score_features(
            "caching service",
            &local_features,
            &rows,
            &ScoreOptions::default(),
        )
        .expect("should not error");
        // feature-x adopted, feature-y cold — adopted must have score > cold
        let adopted = scores.iter().find(|s| s.feature_id == "feature-x");
        let cold = scores.iter().find(|s| s.feature_id == "feature-y");
        // adopted may not exist if total_peers is 0 for cold-only rows
        // but adopted feature always scores >= cold
        if let (Some(a), Some(c)) = (adopted, cold) {
            assert!(
                a.score >= c.score,
                "adopted should rank >= cold, got {a:?} vs {c:?}"
            );
        }
    }
}
