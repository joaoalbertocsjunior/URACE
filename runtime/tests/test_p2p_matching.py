"""Tests for structured intent-to-asset retrieval and honest ranking diagnostics."""
import unittest
import json
import sys
import tempfile
from pathlib import Path

from urace.p2p_matching import benchmark, intent_queries, rank_candidates

TRIAL = Path(__file__).resolve().parents[2] / 'trial'
sys.path.insert(0, str(TRIAL))
try:
    from p2p_retrieval_benchmark import run as run_retrieval_benchmark
    from p2p_local_feature_assets import family_assets, verify_bundle
    _TRIAL_AVAILABLE = True
except ImportError:
    run_retrieval_benchmark = None
    family_assets = None
    verify_bundle = None
    _TRIAL_AVAILABLE = False


class P2PIntentMatchingTests(unittest.TestCase):
    @unittest.skipUnless(_TRIAL_AVAILABLE, 'trial/ modules not on PYTHONPATH')
    def test_initial_ledger_assets_bundle_actual_tagged_runtime_sources(self):
        repo_root = Path(__file__).resolve().parents[2]
        assets = family_assets(repo_root)
        self.assertEqual(set(assets), {'navigation', 'recovery', 'receipts',
                                      'requirements_change', 'integration'})
        for family_assets_list in assets.values():
            self.assertEqual(len(family_assets_list), 6)
            for asset in family_assets_list:
                manifest = verify_bundle(
                    asset['artifact_bytes'], feature_id=asset['feature_id'],
                    artifact_sha256=asset['artifact_sha256'],
                    source_manifest_sha256=asset['source_manifest_sha256'],
                    repo_root=repo_root)
                self.assertEqual(manifest['license_id'], 'Apache-2.0')
                self.assertTrue(asset['source_paths'])

    def test_freeform_catalog_resolves_minted_feature_to_verified_local_code(self):
        from urace.freeform_routing import _p2p_free_features
        repo_root = Path(__file__).resolve().parents[2]
        features = _p2p_free_features({'exchange': {'root': str(repo_root / 'exchange')}})
        candidate = next(feature for feature in features if feature['feature_id'] == 'rt-p2p-intent-match')
        self.assertEqual(candidate['local_implementation_status'], 'VERIFIED_LOCAL_IMPLEMENTATION')
        self.assertTrue(any(item['path'] == 'runtime/urace/p2p_matching.py'
                            for item in candidate['source_files']))
        self.assertEqual(candidate['source_license_id'], 'Apache-2.0')

    def test_goal_query_uses_task_fields_not_unrelated_constraints(self):
        batch = {'items': [
            {'type': 'goal', 'parameters': {'title': 'Improve checkout latency',
                                            'success_measure': 'p95 below 200ms'},
             'raw_text': 'Improve checkout latency'},
            {'type': 'constraint', 'parameters': {'statement': 'Never publish externally'},
             'raw_text': 'Never publish externally'},
        ]}
        queries = intent_queries(batch, 'full unrelated request')
        self.assertEqual(len(queries), 1)
        self.assertIn('checkout latency', queries[0]['query'])
        self.assertNotIn('publish', queries[0]['query'])

    def test_classified_intent_reorders_candidates_and_exposes_score_scope(self):
        batch = {'items': [{'type': 'goal',
                            'parameters': {'title': 'Improve checkout latency',
                                           'success_measure': 'p95 below 200ms'},
                            'raw_text': 'Improve checkout latency'}]}
        features = [
            {'feature_id': 'checkout-deployment',
             'description': 'checkout deployment, login layout, tests urgent'},
            {'feature_id': 'latency-optimizer',
             'description': 'checkout latency response time p95 performance optimizer'},
        ]
        ranked = rank_candidates(batch, 'urgent deployment login layout', features)
        self.assertEqual(ranked[0]['feature_id'], 'latency-optimizer')
        self.assertEqual(ranked[0]['match_method'], 'intent-fields-v1')
        self.assertIn('not calibrated quality', ranked[0]['match_score_interpretation'])

    def test_benchmark_compares_intent_ranking_without_claiming_product_value(self):
        rows = [{'case_id': 'case-1',
                 'raw_text': 'deploy login layout urgently',
                 'batch': {'items': [{'type': 'goal',
                                      'parameters': {'title': 'Improve checkout latency',
                                                     'success_measure': 'p95 response time'},
                                      'raw_text': 'Improve checkout latency'}]},
                 'features': [{'feature_id': 'deploy-login', 'description': 'deploy login layout'},
                              {'feature_id': 'latency-tool', 'description': 'checkout latency p95 response time'}],
                 'relevant_candidate_ids': ['latency-tool']}]
        result = benchmark(rows)
        self.assertEqual(result['labeled_cases'], 1)
        self.assertEqual(result['intent_minus_raw_delta']['5']['mrr'], 1.0)
        self.assertIn('does not measure task acceptance', result['scope'])

    def test_benchmark_rejects_unlabeled_cases(self):
        with self.assertRaises(ValueError):
            benchmark([{'raw_text': 'request', 'batch': {}, 'features': []}])

    @unittest.skipUnless(_TRIAL_AVAILABLE, 'trial/ modules not on PYTHONPATH')
    def test_benchmark_cli_marks_review_claims_as_self_reported_and_not_value_proof(self):
        header = {'schema': 'urace-p2p-retrieval-dataset-v1', 'dataset_kind': 'reviewed_real_work',
                  'split': 'held_out', 'independent_reviewers': 2,
                  'disagreements_adjudicated': True, 'source_description': 'fixture metadata',
                  'case_count': 1}
        case = {'case_id': 'case-1', 'raw_text': 'urgent deploy login',
                'batch': {'items': [{'type': 'goal',
                                    'parameters': {'title': 'Improve checkout latency',
                                                   'success_measure': 'p95 response time'},
                                    'raw_text': 'Improve checkout latency'}]},
                'features': [{'feature_id': 'deploy-login', 'description': 'deploy login'},
                             {'feature_id': 'checkout-latency', 'description': 'checkout latency p95 response time'}],
                'relevant_candidate_ids': ['checkout-latency']}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dataset.jsonl'
            path.write_text(json.dumps(header) + '\n' + json.dumps(case) + '\n', encoding='utf-8')
            result = run_retrieval_benchmark(path)
        self.assertEqual(result['status'], 'HELD_OUT_RETRIEVAL_DIAGNOSTIC')
        self.assertTrue(result['review_provenance_self_reported'])
        self.assertFalse(result['qualified_real_task_value_or_cost_claim'])


if __name__ == '__main__':
    unittest.main()
