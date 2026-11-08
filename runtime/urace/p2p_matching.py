"""Intent-aware P2P asset retrieval. Scores rank candidates; they are not quality probabilities."""
from __future__ import annotations

import math

from . import freeform_routing as _legacy

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


def rank_candidates(batch: dict, raw_text: str, features: list[dict], *, top_n: int = 10) -> list[dict]:
    """Rank catalog candidates against each extracted intent, retaining match provenance."""
    if type(top_n) is not int or not 1 <= top_n <= 100:
        raise ValueError('top_n must be between 1 and 100')
    queries = intent_queries(batch, raw_text)
    scored = []
    for feature in features:
        matches = []
        for query in queries:
            score = _legacy._semantic_score(query['query'], feature)
            if score > 0:
                matches.append({'intent_id': query['intent_id'], 'kind': query['kind'],
                                'score': round(score, 4)})
        if not matches:
            continue
        item = dict(feature)
        item['match_score'] = max(match['score'] for match in matches)
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
        raw_ranked = _legacy._rank_p2p_features(row['raw_text'], row['features'], top_n=len(row['features']))
        intent_ranked = rank_candidates(row['batch'], row['raw_text'], row['features'],
                                         top_n=len(row['features']))
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
