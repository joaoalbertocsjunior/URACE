"""TF-IDF + cosine intent similarity and collaborative-filtering feature scoring.

Two public functions:
  intent_similarity(text_a, text_b) -> float   [0.0, 1.0]
  score_features(config, state, exchange) -> list[dict]

score_features returns a sorted list of feature recommendation dicts:
  {feature_id, score, adoption_rate, peer_count, intent_similarity, confidence,
   rationale, diversity_source, cold_start, peer_trust_weight}

No external dependencies — stdlib only (collections, math, re, time).
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter, defaultdict
from typing import Any

SCHEMA = "urace-product-similarity-v1"

# ── TF-IDF helpers ────────────────────────────────────────────────────────────

_STOP = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "it", "its", "this", "that", "these",
    "those", "as", "so", "not", "no", "if", "then", "than", "more", "most",
    "any", "all", "each", "also", "into", "over", "after", "before", "up",
    "out", "about", "their", "there", "they", "we", "our", "us", "you",
    "your", "he", "she", "his", "her", "i", "my", "me", "while", "when",
    "how", "what", "which", "who", "very", "just", "only",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, remove stop words, split on whitespace."""
    tokens = re.findall(r"[a-z][a-z0-9]*", text.lower())
    return [t for t in tokens if t not in _STOP and len(t) > 1]


def _tf(tokens: list[str]) -> dict[str, float]:
    """Term frequency (raw count normalised by document length)."""
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def _idf(corpus: list[list[str]]) -> dict[str, float]:
    """Inverse document frequency over a small local corpus."""
    n = len(corpus)
    if n == 0:
        return {}
    df: Counter[str] = Counter()
    for doc in corpus:
        df.update(set(doc))
    return {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = _tf(tokens)
    return {term: tf_val * idf.get(term, 1.0) for term, tf_val in tf.items()}


def _cosine(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0
    dot = sum(vec_a[t] * vec_b[t] for t in common)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return min(1.0, dot / (mag_a * mag_b))


def intent_similarity(text_a: str, text_b: str) -> float:
    """TF-IDF cosine similarity between two intent strings.

    Returns a float in [0.0, 1.0].  Both documents form the local corpus so IDF
    is computed over the pair — sufficient for pairwise comparison without
    needing a background corpus.
    """
    tok_a = _tokenize(text_a)
    tok_b = _tokenize(text_b)
    if not tok_a or not tok_b:
        return 0.0
    idf = _idf([tok_a, tok_b])
    return _cosine(_tfidf_vector(tok_a, idf), _tfidf_vector(tok_b, idf))


# ── Wilson lower-bound ────────────────────────────────────────────────────────

def wilson_lower(k: int, n: int, z: float = 1.645) -> float:
    """Wilson score lower bound (90% one-sided) for a proportion k/n.

    Args:
        k: number of successes
        n: number of trials
        z: z-score for desired confidence (default 1.645 = 90%)

    Returns float in [0.0, 1.0]; returns 0.0 when n=0.
    """
    if n == 0:
        return 0.0
    z2 = z * z
    centre = k / n
    margin = z * math.sqrt(centre * (1.0 - centre) / n + z2 / (4.0 * n * n))
    denom = 1.0 + z2 / n
    lower = (centre + z2 / (2.0 * n) - margin) / denom
    return max(0.0, min(1.0, lower))


# ── Peer intent extraction ────────────────────────────────────────────────────

def _local_intent(config: dict[str, Any]) -> str:
    """Extract the product intent string from config."""
    project = config.get("project") or {}
    intent = project.get("intent", "")
    if not intent:
        intent = str(config.get("product", "")) + " " + str(config.get("intent", {}).get("purpose", ""))
    return intent.strip()


def _peer_intents(exchange: Any) -> dict[str, str]:
    """Extract per-peer intent from audit rows."""
    rows = exchange.audit_rows()
    intents: dict[str, str] = {}
    for row in rows:
        peer = row.get("peer")
        if not peer:
            continue
        if row.get("kind") == "CATALOG_CHECK" and isinstance(row.get("product_intent"), str):
            intents[peer] = row["product_intent"]
        elif row.get("kind") == "APPLIED_AFTER_LOCAL_QUALIFICATION" and peer not in intents:
            feature = row.get("feature", "")
            if feature:
                intents.setdefault(peer, "")
                intents[peer] = (intents[peer] + " " + feature).strip()
    return intents


# ── Adoption scanning ─────────────────────────────────────────────────────────

def _peer_adoptions(
    exchange: Any,
    max_peer_age_seconds: float,
    now: float,
) -> dict[str, dict[str, float]]:
    """Return {peer_id: {feature_id: latest_unix}} for recent adoptions."""
    rows = exchange.audit_rows()
    adoptions: dict[str, dict[str, float]] = defaultdict(dict)
    cutoff = now - max_peer_age_seconds
    for row in rows:
        if row.get("kind") != "APPLIED_AFTER_LOCAL_QUALIFICATION":
            continue
        peer = row.get("peer")
        feature = row.get("feature")
        at_unix = float(row.get("at_unix", 0))
        if not peer or not feature:
            continue
        if at_unix < cutoff:
            continue
        existing = adoptions[peer].get(feature, 0.0)
        if at_unix > existing:
            adoptions[peer][feature] = at_unix
    return dict(adoptions)


# ── Recency weight ────────────────────────────────────────────────────────────

def _recency_weight(adoption_unix: float, now: float, half_life_seconds: float = 86400 * 7) -> float:
    """Exponential decay; weight=1.0 at adoption time, 0.5 at half_life."""
    age = max(0.0, now - adoption_unix)
    return math.exp(-math.log(2.0) * age / half_life_seconds)


# ── Local feature presence ────────────────────────────────────────────────────

def _local_feature_ids(exchange: Any) -> set[str]:
    """Return set of feature IDs that this node has locally (declared in exchange)."""
    try:
        policy = exchange.load()
        return set(policy.get("features", {}).keys())
    except Exception:
        return set()


# ── Network size estimation ───────────────────────────────────────────────────

def _known_network_size(exchange: Any) -> int:
    """Estimate network size: max of unique peers in audit rows and policy metadata."""
    rows = exchange.audit_rows()
    unique_peers = {row.get("peer") for row in rows if row.get("peer")}
    count = len(unique_peers)
    # Check policy/metadata for estimated_network_size
    try:
        policy = exchange.load()
        estimated = policy.get("estimated_network_size")
        if isinstance(estimated, int) and estimated > count:
            count = estimated
    except Exception:
        pass
    return max(1, count)


# ── Network-relative confidence tiers ─────────────────────────────────────────

def _confidence(peer_count: int, total_peers: int = 20) -> str:
    """Network-relative confidence: thresholds scale with total known peers."""
    high_thresh = max(3, int(0.30 * total_peers))
    med_thresh = max(2, int(0.10 * total_peers))
    if peer_count >= high_thresh:
        return "high"
    if peer_count >= med_thresh:
        return "medium"
    return "low"


# ── Trust weighting ────────────────────────────────────────────────────────────

def _peer_trust_weights(exchange: Any) -> dict[str, float]:
    """Compute per-peer trust weight via Wilson lower-bound on delivery rate.

    Uses QUALIFICATION_RECEIPT and APPLIED_AFTER_LOCAL_QUALIFICATION audit rows.
    For each peer:
        delivery_rate = receipt_verified_count / total_applied_count
        trust = wilson_lower(receipt_verified, total_applied, z=1.645)
    Clamped to [0.1, 1.0]. Default 0.5 when no data.
    """
    rows = exchange.audit_rows()
    verified: dict[str, int] = defaultdict(int)
    applied: dict[str, int] = defaultdict(int)
    peers_seen: set[str] = set()

    for row in rows:
        peer = row.get("peer")
        if not peer:
            continue
        kind = row.get("kind", "")
        peers_seen.add(peer)
        if kind == "QUALIFICATION_RECEIPT":
            verified[peer] += 1
            applied[peer] += 1
        elif kind == "APPLIED_AFTER_LOCAL_QUALIFICATION":
            applied[peer] += 1

    weights: dict[str, float] = {}
    for peer in peers_seen:
        total = applied[peer]
        vcount = verified[peer]
        if total == 0:
            raw = 0.5
        else:
            raw = wilson_lower(vcount, total, z=1.645)
        # clamp to [0.1, 1.0]
        weights[peer] = max(0.1, min(1.0, raw))
    return weights


# ── Co-adoption Jaccard bonus ─────────────────────────────────────────────────

def _cooccurrence_bonus(
    feature_id: str,
    local_features: set[str],
    adoptions: dict[str, dict[str, float]],
) -> float:
    """Item-item co-adoption Jaccard bonus (max 0.20).

    For each local feature lf:
        jaccard(feature_id, lf) = |peers_with_both| / |peers_with_either|
    bonus = 0.20 * max(jaccard over all local features)
    """
    if not local_features:
        return 0.0

    # Build per-feature peer sets
    peers_with_feature: set[str] = {
        peer for peer, feats in adoptions.items() if feature_id in feats
    }
    if not peers_with_feature:
        return 0.0

    max_jaccard = 0.0
    for lf in local_features:
        peers_with_lf: set[str] = {
            peer for peer, feats in adoptions.items() if lf in feats
        }
        both = peers_with_feature & peers_with_lf
        either = peers_with_feature | peers_with_lf
        if either:
            j = len(both) / len(either)
            if j > max_jaccard:
                max_jaccard = j
    return 0.20 * max_jaccard


# ── TF-IDF cosine for token sets ─────────────────────────────────────────────

def _max_tfidf_sim(feature_id: str, local_features: set[str]) -> float:
    """Max cosine sim between feature_id tokens and any local feature_id tokens."""
    if not local_features:
        return 0.0
    feat_tokens = _tokenize(feature_id.replace("-", " ").replace("_", " "))
    if not feat_tokens:
        return 0.0
    best = 0.0
    for lf in local_features:
        lf_tokens = _tokenize(lf.replace("-", " ").replace("_", " "))
        if not lf_tokens:
            continue
        idf = _idf([feat_tokens, lf_tokens])
        sim = _cosine(_tfidf_vector(feat_tokens, idf), _tfidf_vector(lf_tokens, idf))
        if sim > best:
            best = sim
    return best


# ── ε-diversity helpers ───────────────────────────────────────────────────────

_DIVERSITY_FRAC = 0.15   # fraction of slots reserved for diverse-intent peers
_SIMILAR_FRAC = 0.75     # top fraction of adopting peers treated as "similar"


def _split_diversity_slots(n_slots: int) -> tuple[int, int]:
    """Return (n_similar_slots, n_diverse_slots) that sum to n_slots."""
    n_diverse = max(1, round(n_slots * _DIVERSITY_FRAC))
    n_similar = n_slots - n_diverse
    return n_similar, n_diverse


# ── Main entry point ──────────────────────────────────────────────────────────

def score_features(
    config: dict[str, Any],
    state: dict[str, Any],  # noqa: ARG001 — reserved for future state-based filtering
    exchange: Any,
    *,
    max_peer_age_seconds: float = 86400.0,
    timeout_seconds: float = 5.0,
) -> list[dict[str, Any]]:
    """Score peer features using collaborative filtering + TF-IDF intent similarity.

    Algorithm per feature f:
        base_score = trust_weighted_sim × wilson_adoption_rate × recency × (1 - already_local)
        score = base_score × (1 + cooccurrence_bonus)

    Returns a list sorted by score descending with ε-diversity injection.

    Each result dict:
        feature_id        str
        score             float [0, 1]
        adoption_rate     float Wilson lower-bound adoption rate
        peer_count        int   number of distinct recent peers that adopted it
        total_peers       int   total recent peers seen
        intent_similarity float trust-weighted mean intent similarity
        confidence        str   "high" / "medium" / "low" (network-relative)
        sparse_network    bool
        partial           bool
        rationale         str
        diversity_source  bool  True when included via diversity slot
        cold_start        bool  True for zero-adoption content cold-start entries
        peer_trust_weight float mean trust weight of adopting peers
    """
    start = time.monotonic()
    now = time.time()

    local_intent_text = _local_intent(config)
    local_features = _local_feature_ids(exchange)
    adoptions = _peer_adoptions(exchange, max_peer_age_seconds, now)
    peer_intents = _peer_intents(exchange)
    trust_weights = _peer_trust_weights(exchange)
    network_size = _known_network_size(exchange)

    total_peers = len(adoptions)
    if total_peers == 0:
        return []

    # Build all tokens upfront for batch IDF
    all_texts = [local_intent_text] + list(peer_intents.values())
    all_token_lists = [_tokenize(t) for t in all_texts]
    local_tokens = all_token_lists[0]
    peer_token_lists = {
        peer: all_token_lists[i + 1]
        for i, peer in enumerate(peer_intents.keys())
    }
    idf = _idf(all_token_lists) if all_token_lists else {}
    local_vec = _tfidf_vector(local_tokens, idf)

    # Cache per-peer intent similarity
    peer_sim: dict[str, float] = {}
    partial = False
    for peer, peer_tokens in peer_token_lists.items():
        if time.monotonic() - start > timeout_seconds * 0.8:
            partial = True
            break
        peer_vec = _tfidf_vector(peer_tokens, idf)
        peer_sim[peer] = _cosine(local_vec, peer_vec)

    # Default neutral similarity for peers with no intent text
    for peer in adoptions:
        if peer not in peer_sim:
            peer_sim[peer] = 0.5

    # Aggregate per feature
    feature_peers: dict[str, list[str]] = defaultdict(list)
    feature_latest: dict[str, float] = defaultdict(float)

    for peer, feat_map in adoptions.items():
        for feature_id, ts in feat_map.items():
            feature_peers[feature_id].append(peer)
            if ts > feature_latest[feature_id]:
                feature_latest[feature_id] = ts

    sparse_network = total_peers < 5

    # ── ε-diversity: classify each adopting peer as similar or diverse ──────
    # Sort all adopting peers by their intent similarity to local
    all_adopting_peers = sorted(adoptions.keys(), key=lambda p: peer_sim.get(p, 0.5), reverse=True)
    n_adopting = len(all_adopting_peers)
    n_similar_peers = max(1, int(n_adopting * _SIMILAR_FRAC))
    similar_peers: set[str] = set(all_adopting_peers[:n_similar_peers])
    diverse_peers: set[str] = set(all_adopting_peers[n_similar_peers:])

    # Collect all known feature IDs from audit rows (for cold-start)
    all_audit_features: set[str] = set()
    for row in exchange.audit_rows():
        f = row.get("feature")
        if f:
            all_audit_features.add(f)

    # ── Score features with adoptions ────────────────────────────────────────
    similar_results: list[dict[str, Any]] = []
    diverse_results: list[dict[str, Any]] = []

    for feature_id, peers_that_adopted in feature_peers.items():
        if time.monotonic() - start > timeout_seconds:
            partial = True
            break

        peer_count = len(peers_that_adopted)

        # Wilson lower-bound adoption rate
        adoption_rate = wilson_lower(peer_count, total_peers)

        # Trust-weighted mean intent similarity
        trust_vals = [trust_weights.get(p, 0.5) for p in peers_that_adopted]
        sim_vals = [peer_sim.get(p, 0.5) for p in peers_that_adopted]
        total_trust = sum(trust_vals)
        if total_trust > 0:
            weighted_sim = sum(t * s for t, s in zip(trust_vals, sim_vals)) / total_trust
        else:
            weighted_sim = sum(sim_vals) / peer_count if peer_count > 0 else 0.0

        mean_trust = total_trust / peer_count if peer_count > 0 else 0.5

        recency = _recency_weight(feature_latest[feature_id], now)
        already_local = 1.0 if feature_id in local_features else 0.0

        # Co-adoption Jaccard bonus
        bonus = _cooccurrence_bonus(feature_id, local_features, adoptions)

        base_score = weighted_sim * adoption_rate * recency * (1.0 - already_local)
        score = base_score * (1.0 + bonus)

        confidence = _confidence(peer_count, network_size)

        rationale_parts = [
            f"adopted by {peer_count}/{total_peers} recent peers",
            f"intent_similarity={weighted_sim:.2f}",
            f"recency={recency:.2f}",
            f"wilson_adoption={adoption_rate:.4f}",
        ]
        if bonus > 0:
            rationale_parts.append(f"cooccurrence_bonus={bonus:.3f}")
        if already_local:
            rationale_parts.append("already local — score zeroed")
        if sparse_network:
            rationale_parts.append("sparse network — Wilson lower-bound rate")

        entry = {
            "feature_id": feature_id,
            "score": round(score, 6),
            "adoption_rate": round(adoption_rate, 4),
            "peer_count": peer_count,
            "total_peers": total_peers,
            "intent_similarity": round(weighted_sim, 4),
            "confidence": confidence,
            "sparse_network": sparse_network,
            "rationale": "; ".join(rationale_parts),
            "partial": partial,
            "diversity_source": False,
            "cold_start": False,
            "peer_trust_weight": round(mean_trust, 4),
        }

        # Classify as similar-sourced or diverse-sourced
        # A feature is "diverse" if its adopting peers include any diverse-intent peer
        has_diverse_adopter = any(p in diverse_peers for p in peers_that_adopted)
        has_similar_adopter = any(p in similar_peers for p in peers_that_adopted)

        if has_similar_adopter:
            similar_results.append(entry)
        if has_diverse_adopter:
            diverse_results.append(entry)

    # Sort each bucket by score descending
    similar_results.sort(key=lambda r: (-r["score"], r["feature_id"]))
    diverse_results.sort(key=lambda r: (-r["score"], r["feature_id"]))

    # ── ε-diversity merging ──────────────────────────────────────────────────
    # Collect all unique scored feature IDs across both buckets
    all_scored_ids: list[str] = []
    _seen_order: set[str] = set()
    for entry in similar_results + diverse_results:
        if entry["feature_id"] not in _seen_order:
            _seen_order.add(entry["feature_id"])
            all_scored_ids.append(entry["feature_id"])

    n_total_slots = len(all_scored_ids)

    if n_total_slots == 0:
        n_diverse_slots = 0
        n_similar_slots = 0
    else:
        n_similar_slots, n_diverse_slots = _split_diversity_slots(n_total_slots)

    # Build lookup maps for O(1) access
    similar_by_id = {e["feature_id"]: e for e in similar_results}
    diverse_by_id = {e["feature_id"]: e for e in diverse_results}

    # Features that ONLY appear in diverse bucket (not in similar at all)
    diverse_only_ids = [
        fid for fid in all_scored_ids
        if fid not in similar_by_id and fid in diverse_by_id
    ]
    similar_ids = [fid for fid in all_scored_ids if fid in similar_by_id]

    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Fill similar slots first (sorted by score)
    similar_sorted = sorted(similar_ids, key=lambda fid: -similar_by_id[fid]["score"])
    for fid in similar_sorted[:n_similar_slots]:
        if fid not in seen_ids:
            seen_ids.add(fid)
            merged.append(similar_by_id[fid])

    # Fill diverse slots from diverse-only features (mark flag)
    diverse_only_sorted = sorted(diverse_only_ids, key=lambda fid: -diverse_by_id[fid]["score"])
    for fid in diverse_only_sorted[:n_diverse_slots]:
        if fid not in seen_ids:
            seen_ids.add(fid)
            diverse_entry = dict(diverse_by_id[fid])
            diverse_entry["diversity_source"] = True
            merged.append(diverse_entry)

    # Add any remaining features not yet included (similar first, then diverse-only)
    for fid in similar_sorted:
        if fid not in seen_ids:
            seen_ids.add(fid)
            merged.append(similar_by_id[fid])
    for fid in diverse_only_sorted:
        if fid not in seen_ids:
            seen_ids.add(fid)
            diverse_entry = dict(diverse_by_id[fid])
            diverse_entry["diversity_source"] = True
            merged.append(diverse_entry)

    merged.sort(key=lambda r: (-r["score"], r["feature_id"]))

    # ── Content cold-start: features with 0 peer adoptions ───────────────────
    cold_features = all_audit_features - set(feature_peers.keys()) - local_features
    cold_entries: list[dict[str, Any]] = []
    for feature_id in cold_features:
        tfidf_sim = _max_tfidf_sim(feature_id, local_features) if local_features else 0.0
        cold_score = 0.05 * tfidf_sim
        cold_entries.append({
            "feature_id": feature_id,
            "score": round(cold_score, 6),
            "adoption_rate": 0.0,
            "peer_count": 0,
            "total_peers": total_peers,
            "intent_similarity": 0.0,
            "confidence": "low",
            "sparse_network": sparse_network,
            "rationale": f"cold-start: no peer adoptions; tfidf_sim={tfidf_sim:.3f}",
            "partial": partial,
            "diversity_source": False,
            "cold_start": True,
            "peer_trust_weight": 0.0,
        })

    cold_entries.sort(key=lambda r: (-r["score"], r["feature_id"]))
    return merged + cold_entries
