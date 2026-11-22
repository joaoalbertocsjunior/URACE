"""Intent-aware P2P asset retrieval. Scores rank candidates; they are not quality probabilities."""
from __future__ import annotations

import collections as _collections
import functools as _functools
import hashlib as _hashlib
import json as _json
import math
import threading as _threading_dm
import time as _time_dm

from . import freeform_routing as _legacy


class DemandCounter:
    """Tracks per-executor rolling request rate (requests/minute).

    Thread-safe. Bounded deque per executor — older than window_seconds entries
    are ignored in get_demand(). Max 1000 entries per executor.
    """
    _MAX_ENTRIES = 1000

    def __init__(self) -> None:
        self._counts: dict[str, _collections.deque] = {}
        self._lock = _threading_dm.Lock()

    def record_request(self, executor_id: str, model: str = '', at: float | None = None) -> None:
        at = at if at is not None else _time_dm.time()
        key = executor_id
        with self._lock:
            if key not in self._counts:
                self._counts[key] = _collections.deque(maxlen=self._MAX_ENTRIES)
            self._counts[key].append(at)

    def get_demand(self, executor_id: str, window_seconds: int = 60) -> float:
        """Return requests per minute within the rolling window."""
        cutoff = _time_dm.time() - window_seconds
        with self._lock:
            entries = list(self._counts.get(executor_id, []))
        recent = [t for t in entries if t >= cutoff]
        if not recent:
            return 0.0
        return len(recent) / (window_seconds / 60.0)

    def demand_gossip_payload(self, executor_ids: list[str], window_seconds: int = 60) -> list[dict]:
        """Return demand summary suitable for inclusion in gossip."""
        return [
            {
                'executor_id': eid,
                'req_per_min': self.get_demand(eid, window_seconds),
                'window_seconds': window_seconds,
            }
            for eid in executor_ids
        ]


_DEMAND = DemandCounter()


# Throughput tracking constants (concept-borrowed from mesh-llm Apache 2.0:
# mesh/crates/mesh-llm-membership/src/advertised_throughput.rs)
TPS_WEIGHT_MIN: float = 0.3   # floor weight for slow/cold executors
TPS_WEIGHT_MAX: float = 2.0   # ceiling weight for fast executors
THROUGHPUT_SCALE_MILLI: int = 1000  # fixed-point precision for TPS calculations
_TPS_MIN_SAMPLES: int = 3     # cold node threshold — fewer samples → neutral weight


class ThroughputTracker:
    """Rolling per-executor token throughput tracker.

    Thread-safe. Maintains bounded deque of (tokens, elapsed_secs, timestamp)
    per (executor_id, model) key. get_routing_weight() returns 1.0 (neutral)
    for cold nodes (fewer than _TPS_MIN_SAMPLES samples).
    """
    _MAX_ENTRIES = 500

    def __init__(self) -> None:
        self._records: dict[str, _collections.deque] = {}
        self._lock = _threading_dm.Lock()

    def _key(self, executor_id: str, model: str) -> str:
        return f"{executor_id}\x00{model}"

    def record_tps(
        self,
        executor_id: str,
        model: str,
        tokens_generated: int,
        elapsed_seconds: float,
        at: float | None = None,
    ) -> None:
        at = at if at is not None else _time_dm.time()
        if elapsed_seconds <= 0 or tokens_generated <= 0:
            return
        key = self._key(executor_id, model)
        with self._lock:
            if key not in self._records:
                self._records[key] = _collections.deque(maxlen=self._MAX_ENTRIES)
            self._records[key].append((tokens_generated / elapsed_seconds, at))

    def get_mean_tps(
        self, executor_id: str, model: str, window_seconds: int = 900
    ) -> float | None:
        """Return mean tok/s in window, or None if cold (< _TPS_MIN_SAMPLES)."""
        cutoff = _time_dm.time() - window_seconds
        key = self._key(executor_id, model)
        with self._lock:
            entries = [(tps, t) for tps, t in self._records.get(key, []) if t >= cutoff]
        if len(entries) < _TPS_MIN_SAMPLES:
            return None
        return sum(tps for tps, _ in entries) / len(entries)

    def get_routing_weight(
        self,
        executor_id: str,
        model: str,
        window_seconds: int = 900,
        reference_tps: float = 10.0,
        weight_min: float = TPS_WEIGHT_MIN,
        weight_max: float = TPS_WEIGHT_MAX,
    ) -> float:
        """Routing weight: 1.0 neutral for cold nodes, clamped [min, max] otherwise."""
        mean = self.get_mean_tps(executor_id, model, window_seconds)
        if mean is None:
            return 1.0  # neutral — cold node gets equal chance
        raw = mean / max(reference_tps, 0.001)
        return max(weight_min, min(weight_max, raw))


_THROUGHPUT = ThroughputTracker()


@_functools.lru_cache(maxsize=4)
def _cached_idf(feature_corpus_hash: str, features_json: str) -> dict:
    return _legacy._build_idf(_json.loads(features_json))


def _get_idf(features: list[dict]) -> dict:
    corpus_hash = _hashlib.md5(_json.dumps([f.get('id', '') for f in features], sort_keys=True).encode()).hexdigest()
    features_json = _json.dumps(features, sort_keys=True)
    return _cached_idf(corpus_hash, features_json)

MATCHER_VERSION = 'intent-fields-v1'
_ACTIONABLE = {'goal': ('title', 'success_measure'), 'intent': ('statement',)}


def intent_queries(batch: dict, raw_text: str = '') -> list[dict]:
    """Build bounded, source-grounded asset queries from validated actionable sections."""
    queries = []
    for index, item in enumerate(batch.get('items', [])):
        kind = item.get('type')
        fields = _ACTIONABLE.get(kind)
        if not fields:
            continue
        params = item.get('parameters', {})
        parts = [params.get(field, '').strip() for field in fields]
        source = item.get('raw_text', '').strip()
        query = ' '.join(dict.fromkeys(part for part in parts if part))
        if query:
            queries.append({'intent_id': f'{kind}-{index + 1}', 'kind': kind,
                            'query': query[:4096], 'source_text': source})
    return queries


def rank_candidates(batch: dict, raw_text: str, features: list[dict], *,
                    top_n: int = 10, scorer: str = 'tfidf',
                    throughput_tracker=None, model: str = '', **kwargs) -> list[dict]:
    """Rank catalog candidates against each extracted intent, retaining match provenance."""
    if type(top_n) is not int or not 1 <= top_n <= 100:
        raise ValueError('top_n must be between 1 and 100')
    queries = intent_queries(batch, raw_text)
    # Build IDF once over the full corpus for TF-IDF scoring
    idf = _get_idf(features) if scorer == 'tfidf' and features else {}
    # Embedding scorer: single pass over raw_text for all features; falls back to tfidf on error
    emb_map: dict[str, float] = {}
    _effective_scorer = scorer
    if scorer == 'embedding' and features:
        try:
            import litellm as _ll, math as _m
            corpus_texts = [
                f"{f.get('feature_id', '')} {f.get('description', '')} {' '.join(f.get('tags') or [])}".strip()
                for f in features
            ]
            resp = _ll.embedding(model='text-embedding-3-small', input=[raw_text] + corpus_texts)
            vecs = [item['embedding'] for item in resp.data]
            q_vec = vecs[0]
            def _cos(a: list, b: list) -> float:
                d = sum(x * y for x, y in zip(a, b))
                ma = _m.sqrt(sum(x * x for x in a)); mb = _m.sqrt(sum(x * x for x in b))
                return d / (ma * mb) if ma and mb else 0.0
            emb_map = {str(f.get('feature_id') or i): _cos(q_vec, vecs[i + 1])
                       for i, f in enumerate(features)}
        except Exception:
            emb_map = {}
            _effective_scorer = 'tfidf'
            idf = _get_idf(features) if features else {}
    scored = []
    for feature in features:
        fid = str(feature.get('feature_id') or id(feature))
        matches = []
        if _effective_scorer == 'embedding':
            score = emb_map.get(fid, 0.0)
            if score > 0:
                # Use a synthetic intent_id covering the whole raw_text
                matches.append({'intent_id': 'raw-embedding', 'kind': 'embedding',
                                'score': round(score, 4)})
        else:
            for query in queries:
                if _effective_scorer == 'tfidf' and idf:
                    score = _legacy._semantic_score_tfidf(query['query'], feature, idf)
                else:
                    score = _legacy._semantic_score(query['query'], feature)
                if score > 0:
                    matches.append({'intent_id': query['intent_id'], 'kind': query['kind'],
                                    'score': round(score, 4)})
        if not matches:
            continue
        item = dict(feature)
        item['match_score'] = max(match['score'] for match in matches)
        if throughput_tracker is not None:
            _seller = item.get('seller_peer_id', '')
            _weight = throughput_tracker.get_routing_weight(_seller, model)
            item['match_score'] = item['match_score'] * _weight
        item['match_method'] = MATCHER_VERSION
        item['match_score_interpretation'] = 'heuristic lexical relevance; not calibrated quality or equivalence'
        item['local_implementation_available'] = (
            item.get('local_implementation_status') == 'VERIFIED_LOCAL_IMPLEMENTATION')
        item['candidate_route'] = ('LOCAL_IMPLEMENTATION_SOURCE_AVAILABLE'
                                   if item['local_implementation_available']
                                   else 'CATALOG_MATCH_REQUIRES_EXTERNAL_ASSET')
        item['matched_intents'] = sorted(matches, key=lambda row: (-row['score'], row['intent_id']))
        scored.append(item)
    scored.sort(key=lambda row: (-row['match_score'], row.get('feature_id', ''),
                                 row.get('seller_peer_id', ''), row.get('asset_id', '')))
    return scored[:top_n]


def _candidate_id(feature: dict) -> str:
    return str(feature.get('asset_id') or feature.get('feature_id') or '')


def _dcg(relevant: list[str], ranked: list[str], k: int) -> float:
    positives = set(relevant)
    return sum((1.0 / math.log2(index + 2)) for index, candidate in enumerate(ranked[:k])
               if candidate in positives)


def benchmark(rows: list[dict], *, ks: tuple[int, ...] = (1, 3, 5)) -> dict:
    """Compare raw-request ranking with intent-field ranking on externally labeled cases."""
    if not rows:
        raise ValueError('A labeled retrieval dataset is required')
    if any(type(k) is not int or k < 1 for k in ks):
        raise ValueError('k values must be positive integers')
    totals = {'raw_request': {k: {'recall': 0.0, 'ndcg': 0.0, 'mrr': 0.0} for k in ks},
              'classified_intent': {k: {'recall': 0.0, 'ndcg': 0.0, 'mrr': 0.0} for k in ks}}
    for row in rows:
        if (not isinstance(row.get('raw_text'), str) or not row['raw_text'].strip()
                or not isinstance(row.get('batch'), dict)
                or not isinstance(row['batch'].get('items'), list)
                or not isinstance(row.get('features'), list)
                or not isinstance(row.get('relevant_candidate_ids'), list)
                or not row['relevant_candidate_ids']):
            raise ValueError('Each case needs raw_text, validated batch, features, and nonempty human relevance labels')
        if any(not isinstance(item, dict) or not isinstance(item.get('parameters'), dict)
               for item in row['batch']['items']):
            raise ValueError('Each batch item needs structured parameters')
        if any(not isinstance(feature, dict) for feature in row['features']):
            raise ValueError('Candidate features must be objects')
        relevant = list(dict.fromkeys(row['relevant_candidate_ids']))
        if any(not isinstance(value, str) or not value for value in relevant):
            raise ValueError('Relevant candidate IDs must be nonempty strings')
        candidate_ids = [_candidate_id(feature) for feature in row['features']]
        if (any(not value for value in candidate_ids) or len(set(candidate_ids)) != len(candidate_ids)
                or not set(relevant).issubset(candidate_ids)):
            raise ValueError('Candidate IDs must be unique and contain every labeled-relevant candidate')
        raw_ranked = _legacy._rank_p2p_features(row['raw_text'], row['features'],
                                                 top_n=len(row['features']), scorer='lexical')
        intent_ranked = rank_candidates(row['batch'], row['raw_text'], row['features'],
                                        top_n=len(row['features']), scorer='lexical')
        rankings = {'raw_request': [_candidate_id(item) for item in raw_ranked],
                    'classified_intent': [_candidate_id(item) for item in intent_ranked]}
        for method, ranked in rankings.items():
            for k in ks:
                found = sum(candidate in set(relevant) for candidate in ranked[:k])
                first = next((i for i, candidate in enumerate(ranked[:k], 1)
                              if candidate in set(relevant)), None)
                totals[method][k]['recall'] += found / len(relevant)
                totals[method][k]['ndcg'] += (_dcg(relevant, ranked, k) /
                                               (_dcg(relevant, relevant, k) or 1.0))
                totals[method][k]['mrr'] += 1.0 / first if first else 0.0
    count = len(rows)
    metrics = {method: {str(k): {metric: round(value / count, 6)
                                 for metric, value in values.items()}
                        for k, values in by_k.items()}
               for method, by_k in totals.items()}
    deltas = {str(k): {metric: round(metrics['classified_intent'][str(k)][metric]
                                     - metrics['raw_request'][str(k)][metric], 6)
                       for metric in ('recall', 'ndcg', 'mrr')} for k in ks}
    return {'schema': 'urace-p2p-retrieval-benchmark-v1', 'matcher_version': MATCHER_VERSION,
            'labeled_cases': count, 'metrics': metrics, 'intent_minus_raw_delta': deltas,
            'scope': 'retrieval ranking only; does not measure task acceptance, value, or cost'}
