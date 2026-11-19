"""Synthetic labeled fixtures for p2p_matching intent ranking.

Validates rank_candidates() produces correct ordering on known inputs.
Uses NDCG@5 and MRR to measure retrieval quality against ground truth.
"""
import sys, math, unittest
sys.path.insert(0, 'runtime')
from urace.p2p_matching import rank_candidates, intent_queries

def _dcg(relevances):
    return sum(r / math.log2(i + 2) for i, r in enumerate(relevances))

def _ndcg(ranked_ids, relevant_ids, k=5):
    gains = [1.0 if fid in relevant_ids else 0.0 for fid in ranked_ids[:k]]
    ideal = sorted(gains, reverse=True)
    dcg = _dcg(gains)
    idcg = _dcg(ideal)
    return dcg / idcg if idcg > 0 else 0.0

def _mrr(ranked_ids, relevant_ids):
    for i, fid in enumerate(ranked_ids):
        if fid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0

# Synthetic feature catalog
_FEATURES = [
    {'feature_id': 'auth-001', 'title': 'JWT authentication middleware', 'description': 'Stateless auth using JSON Web Tokens'},
    {'feature_id': 'auth-002', 'title': 'OAuth2 authorization flow', 'description': 'OAuth2 with PKCE for secure authorization'},
    {'feature_id': 'db-001',   'title': 'PostgreSQL connection pool', 'description': 'Async connection pooling for PostgreSQL'},
    {'feature_id': 'db-002',   'title': 'Redis cache layer', 'description': 'In-memory caching with Redis TTL support'},
    {'feature_id': 'api-001',  'title': 'REST API rate limiter', 'description': 'Token bucket rate limiting for HTTP APIs'},
    {'feature_id': 'api-002',  'title': 'GraphQL schema builder', 'description': 'Type-safe GraphQL schema definition'},
    {'feature_id': 'test-001', 'title': 'Unit test harness', 'description': 'Pytest fixtures and mock utilities'},
    {'feature_id': 'test-002', 'title': 'Integration test runner', 'description': 'End-to-end test automation framework'},
]

class P2PMatchingTests(unittest.TestCase):

    def _batch(self, statement):
        return {'items': [{'type': 'intent', 'parameters': {'statement': statement}, 'raw_text': statement}]}

    def test_auth_query_ranks_auth_features_first(self):
        results = rank_candidates(self._batch('add JWT authentication'), '', _FEATURES)
        ranked_ids = [r['feature_id'] for r in results]
        self.assertGreater(_ndcg(ranked_ids, {'auth-001', 'auth-002'}), 0.5,
            'NDCG@5 for auth query should exceed 0.5')

    def test_database_query_ranks_db_features_above_unrelated(self):
        results = rank_candidates(self._batch('PostgreSQL database connection'), '', _FEATURES)
        ranked_ids = [r['feature_id'] for r in results]
        self.assertGreater(_ndcg(ranked_ids, {'db-001', 'db-002'}), 0.4)

    def test_mrr_above_threshold_for_exact_title_match(self):
        results = rank_candidates(self._batch('Redis cache'), '', _FEATURES)
        ranked_ids = [r['feature_id'] for r in results]
        self.assertGreater(_mrr(ranked_ids, {'db-002'}), 0.3,
            'MRR should exceed 0.3 for near-exact title match')

    def test_empty_query_returns_empty(self):
        batch = {'items': []}
        results = rank_candidates(batch, '', _FEATURES)
        self.assertEqual(results, [])

    def test_top_n_respected(self):
        results = rank_candidates(self._batch('API authentication database'), '', _FEATURES, top_n=3)
        self.assertLessEqual(len(results), 3)

    def test_top_n_validation(self):
        with self.assertRaises(ValueError):
            rank_candidates(self._batch('auth'), '', _FEATURES, top_n=0)
        with self.assertRaises(ValueError):
            rank_candidates(self._batch('auth'), '', _FEATURES, top_n=101)

    def test_match_score_between_zero_and_one(self):
        results = rank_candidates(self._batch('authentication JWT'), '', _FEATURES)
        for r in results:
            self.assertGreaterEqual(r['match_score'], 0.0)
            self.assertLessEqual(r['match_score'], 1.0)

    def test_results_sorted_by_descending_score(self):
        results = rank_candidates(self._batch('API rate limit'), '', _FEATURES)
        scores = [r['match_score'] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_intent_queries_extracts_statement(self):
        batch = {'items': [{'type': 'intent', 'parameters': {'statement': 'add caching'}, 'raw_text': 'add caching'}]}
        queries = intent_queries(batch)
        self.assertEqual(len(queries), 1)
        self.assertIn('caching', queries[0]['query'])

    def test_match_score_interpretation_present(self):
        results = rank_candidates(self._batch('authentication'), '', _FEATURES)
        for r in results:
            self.assertIn('match_score_interpretation', r)
            self.assertIn('heuristic', r['match_score_interpretation'])

    def test_no_match_returns_empty(self):
        results = rank_candidates(self._batch('xyzzy_nonexistent_gibberish_42'), '', _FEATURES)
        self.assertEqual(results, [])

    def test_goal_type_extracted(self):
        batch = {'items': [{'type': 'goal', 'parameters': {'title': 'improve auth', 'success_measure': 'JWT implemented'}, 'raw_text': 'improve auth'}]}
        queries = intent_queries(batch)
        self.assertGreater(len(queries), 0)
        self.assertEqual(queries[0]['kind'], 'goal')

if __name__ == '__main__':
    unittest.main()
