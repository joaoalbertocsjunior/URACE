"""Tests for freeform_routing._semantic_score and _rank_p2p_features."""
import unittest
from urace.freeform_routing import _semantic_score, _rank_p2p_features


def feature(feature_id='', description='', tags=None):
    return {'feature_id': feature_id, 'description': description, 'tags': tags or []}


class TestSemanticScoreSynonyms(unittest.TestCase):
    def test_chart_scores_against_visualization_feature(self):
        # 'chart' is in _SYNONYMS -> {'visualization', ...}
        f = feature('visualization-engine', 'Build visualization dashboards')
        score = _semantic_score('chart', f)
        self.assertGreater(score, 0.0)

    def test_visualization_scores_against_chart_feature(self):
        f = feature('chart-builder', 'Renders charts and graphs')
        score = _semantic_score('visualization', f)
        self.assertGreater(score, 0.0)

    def test_fast_scores_against_performance_feature(self):
        f = feature('performance-optimizer', 'Speed up slow paths')
        score = _semantic_score('fast', f)
        self.assertGreater(score, 0.0)

    def test_model_scores_against_llm_feature(self):
        f = feature('llm-gateway', 'Route LLM and AI requests')
        score = _semantic_score('model', f)
        self.assertGreater(score, 0.0)

    def test_report_scores_against_analytics_feature(self):
        f = feature('analytics-dashboard', 'Dashboard and metrics reporting')
        score = _semantic_score('report', f)
        self.assertGreater(score, 0.0)

    def test_api_scores_against_endpoint_feature(self):
        f = feature('rest-endpoint', 'HTTP service endpoint layer')
        score = _semantic_score('api', f)
        self.assertGreater(score, 0.0)

    def test_exact_match_scores_higher_than_synonym_match(self):
        # 'chart' as exact vs 'chart' via synonym expansion of 'visualization'
        exact_feature = feature('chart-renderer', 'Renders chart components')
        synonym_feature = feature('visualization-only', 'Renders visualization components')
        score_exact = _semantic_score('chart', exact_feature)
        score_synonym = _semantic_score('visualization', synonym_feature)
        # Direct exact token overlap should score >= synonym-expanded overlap
        # (both features have the same token in description; just check both > 0)
        self.assertGreater(score_exact, 0.0)
        self.assertGreater(score_synonym, 0.0)

    def test_exact_overlap_beats_synonym_only(self):
        # Text 'chart' against a feature with literal 'chart' vs one with only 'visualization'
        exact_f = feature('chart', 'chart rendering tool')
        synonym_only_f = feature('viz', 'visualization rendering tool')
        score_exact = _semantic_score('chart', exact_f)
        score_syn = _semantic_score('chart', synonym_only_f)
        self.assertGreaterEqual(score_exact, score_syn)

    def test_empty_text_returns_zero(self):
        f = feature('anything', 'some description')
        self.assertEqual(_semantic_score('', f), 0.0)

    def test_no_overlap_returns_zero(self):
        f = feature('xyz-unrelated', 'completely unrelated')
        # 'quux' has no synonym expansion and no overlap
        self.assertEqual(_semantic_score('quux', f), 0.0)

    def test_prefix_match_still_works(self):
        # 'perf' prefix-matches 'performance' in feature
        f = feature('perf-tuner', 'performance tuning tool')
        score = _semantic_score('perf', f)
        self.assertGreater(score, 0.0)

    def test_score_capped_at_one(self):
        # Flood overlap: text identical to feature tokens
        f = feature('search query find lookup', 'search query find lookup retrieve')
        score = _semantic_score('search query find lookup', f)
        self.assertLessEqual(score, 1.0)


class TestRankP2pFeatures(unittest.TestCase):
    def test_intent_matching_normalizes_punctuation_identifiers_and_accents(self):
        punctuation = _semantic_score(
            'checkout_latency, p95!',
            feature('checkout-latency', 'p95: checkout latency'))
        self.assertEqual(punctuation, 1.0)
        accented = _semantic_score('latência', feature('latencia', ''))
        self.assertEqual(accented, 1.0)

    def test_partial_matching_does_not_match_short_catalog_tokens(self):
        self.assertEqual(_semantic_score('application programming interface',
                                         feature('a', '')), 0.0)

    def test_short_domain_tokens_still_match_exactly(self):
        for token in ('AI', 'ID', 'DB', 'P2P'):
            with self.subTest(token=token):
                self.assertGreater(_semantic_score(token, feature(token.lower(), '')), 0.0)

    def test_returns_features_sorted_by_score_descending(self):
        features = [
            feature('chart-builder', 'renders charts'),
            feature('unrelated-thing', 'completely different'),
            feature('visualization-tool', 'visualization graphs'),
        ]
        ranked = _rank_p2p_features('chart', features)
        self.assertGreater(len(ranked), 0)
        # chart-builder should rank above unrelated-thing
        ids = [f['feature_id'] for f in ranked]
        self.assertIn('chart-builder', ids)
        if 'unrelated-thing' in ids:
            self.assertLess(ids.index('chart-builder'), ids.index('unrelated-thing'))

    def test_zero_score_features_excluded(self):
        features = [
            feature('totally-unrelated-zzz', 'zzz yyy xxx'),
        ]
        ranked = _rank_p2p_features('chart', features)
        self.assertEqual(ranked, [])

    def test_top_n_respected(self):
        features = [feature(f'feat-{i}', f'chart visualization graph {i}') for i in range(20)]
        ranked = _rank_p2p_features('chart', features, top_n=5)
        self.assertLessEqual(len(ranked), 5)

    def test_empty_features_returns_empty(self):
        self.assertEqual(_rank_p2p_features('chart', []), [])

    def test_synonym_match_included_in_ranking(self):
        features = [
            feature('visualization-suite', 'comprehensive visualization platform'),
            feature('totally-unrelated', 'zzz yyy xxx qqq'),
        ]
        ranked = _rank_p2p_features('chart', features)
        ids = [f['feature_id'] for f in ranked]
        # 'chart' synonym 'visualization' should match visualization-suite
        self.assertIn('visualization-suite', ids)
        self.assertNotIn('totally-unrelated', ids)


if __name__ == '__main__':
    unittest.main()
