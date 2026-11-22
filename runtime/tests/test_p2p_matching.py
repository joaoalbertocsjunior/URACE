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
        # initial_ledger entries use COMPUTED_LOCAL_BINDING (hashes derived at runtime from tags);
        # signed ledger SourceBindingRecords use VERIFIED_LOCAL_IMPLEMENTATION (stored hashes).
        self.assertIn(candidate['local_implementation_status'],
                      ('VERIFIED_LOCAL_IMPLEMENTATION', 'COMPUTED_LOCAL_BINDING'))
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


class DemandCounterTests(unittest.TestCase):

    def setUp(self):
        from urace.p2p_matching import DemandCounter
        self.counter = DemandCounter()

    def test_demand_zero_for_unknown_executor(self):
        self.assertEqual(self.counter.get_demand('never-seen'), 0.0)

    def test_demand_rolling_window_excludes_old_entries(self):
        import time
        old_time = time.time() - 200  # 200s ago, outside 60s window
        self.counter.record_request('exec-1', at=old_time)
        self.assertEqual(self.counter.get_demand('exec-1', window_seconds=60), 0.0)

    def test_demand_counts_recent_requests(self):
        for _ in range(6):
            self.counter.record_request('exec-2')
        # 6 requests in 60s window = 6 req/min
        demand = self.counter.get_demand('exec-2', window_seconds=60)
        self.assertAlmostEqual(demand, 6.0, delta=0.1)

    def test_demand_gossip_payload_shape(self):
        self.counter.record_request('exec-3')
        payload = self.counter.demand_gossip_payload(['exec-3', 'exec-unknown'])
        self.assertEqual(len(payload), 2)
        self.assertIn('executor_id', payload[0])
        self.assertIn('req_per_min', payload[0])
        self.assertIn('window_seconds', payload[0])


class ThroughputTrackerTests(unittest.TestCase):

    def setUp(self):
        from urace.p2p_matching import ThroughputTracker, TPS_WEIGHT_MIN, TPS_WEIGHT_MAX
        self.tracker = ThroughputTracker()
        self.weight_min = TPS_WEIGHT_MIN
        self.weight_max = TPS_WEIGHT_MAX

    def test_cold_node_returns_neutral_weight(self):
        # No samples → neutral 1.0
        w = self.tracker.get_routing_weight('exec-1', 'model-a')
        self.assertEqual(w, 1.0)

    def test_fewer_than_min_samples_returns_neutral(self):
        # 2 samples (< _TPS_MIN_SAMPLES=3) → still neutral
        self.tracker.record_tps('exec-2', 'model-a', tokens_generated=100, elapsed_seconds=10.0)
        self.tracker.record_tps('exec-2', 'model-a', tokens_generated=100, elapsed_seconds=10.0)
        w = self.tracker.get_routing_weight('exec-2', 'model-a')
        self.assertEqual(w, 1.0)

    def test_fast_executor_clamped_to_max(self):
        # 1000 tok/s with reference 10 → raw weight 100x, clamped to TPS_WEIGHT_MAX
        for _ in range(5):
            self.tracker.record_tps('fast-exec', 'model-b', tokens_generated=10000, elapsed_seconds=10.0)
        w = self.tracker.get_routing_weight('fast-exec', 'model-b', reference_tps=10.0)
        self.assertAlmostEqual(w, self.weight_max, places=5)

    def test_slow_executor_clamped_to_min(self):
        # 0.001 tok/s with reference 10 → raw weight ~0, clamped to TPS_WEIGHT_MIN
        for _ in range(5):
            self.tracker.record_tps('slow-exec', 'model-c', tokens_generated=1, elapsed_seconds=1000.0)
        w = self.tracker.get_routing_weight('slow-exec', 'model-c', reference_tps=10.0)
        self.assertAlmostEqual(w, self.weight_min, places=5)

    def test_rank_candidates_with_tracker_reorders_slow_peer(self):
        from urace.p2p_matching import rank_candidates, _THROUGHPUT
        # Give peer-slow very slow TPS so it should rank lower
        for _ in range(5):
            self.tracker.record_tps('peer-slow', '', tokens_generated=1, elapsed_seconds=1000.0)
        features = [
            {'id': 'f1', 'title': 'fast feature', 'seller_peer_id': 'peer-fast', 'description': 'improve routing'},
            {'id': 'f2', 'title': 'slow feature', 'seller_peer_id': 'peer-slow', 'description': 'improve routing'},
        ]
        batch = {'text': 'improve routing', 'type': 'goal'}
        results = rank_candidates(batch, 'improve routing', features,
                                  throughput_tracker=self.tracker, model='')
        # peer-slow should not be ranked first
        if len(results) >= 2:
            top_seller = results[0].get('seller_peer_id', '')
            self.assertNotEqual(top_seller, 'peer-slow')


if __name__ == '__main__':
    unittest.main()
