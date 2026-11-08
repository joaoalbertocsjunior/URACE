"""Tests for cohort-bound, two-reviewer economic claim receipts."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'runtime'))

import p2p_cost_claim_review as claims
import p2p_study_plan
from urace.ledger_crypto import Identity, public_id


class CostClaimReviewTests(unittest.TestCase):
    def test_live_workload_attestation_binds_source_hash_and_exact_frozen_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            keys = [Identity(Path(directory) / f'identity-{index}.json') for index in range(6)]
            evaluator, buyer, seller, attestor, reviewer = keys[:5]
            tasks = [{'task_id': 'work-1', 'task_specification': 'source-derived task'}]
            provenance = {'kind': 'real_product_workloads', 'source_sha256': 'f' * 64,
                           'description': 'Product issue export, reviewed and redacted',
                           'attestor_id': public_id(attestor.public()),
                           'attestor_public': attestor.public(),
                           'selected_task_manifest_sha256': p2p_study_plan.canonical_sha256(tasks)}
            identity = {
                'product_id': 'real-product',
                'independent_evaluator_id': public_id(evaluator.public()),
                'exchange_buyer_id': public_id(buyer.public()),
                'allowed_seller_peer_ids': [public_id(seller.public())],
                'claim_reviewer_public_keys': {public_id(reviewer.public()): reviewer.public(),
                                               public_id(keys[5].public()): keys[5].public()},
                'workload_provenance': provenance,
            }
            payload = p2p_study_plan.workload_attestation_payload('real-product', provenance, tasks)
            provenance['attestation_signature'] = attestor.sign(
                payload, 'p2p-workload-source-attestation')
            p2p_study_plan._validate_live_workload_identity(identity, tasks)
            changed_tasks = [{'task_id': 'work-1', 'task_specification': 'invented replacement'}]
            with self.assertRaises(ValueError):
                p2p_study_plan._validate_live_workload_identity(identity, changed_tasks)
            provenance['source_sha256'] = 'e' * 64
            with self.assertRaises(ValueError):
                p2p_study_plan._validate_live_workload_identity(identity, tasks)

    def test_two_pinned_reviewer_signatures_qualify_only_the_bound_live_cohort(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Identity(Path(directory) / 'reviewer-a.json')
            second = Identity(Path(directory) / 'reviewer-b.json')
            public_keys = {public_id(first.public()): first.public(),
                           public_id(second.public()): second.public()}
            cohort_hash = 'a' * 64
            plan = {'cohort_sha256': cohort_hash, 'identity': {
                'evidence_mode': 'LIVE',
                'economic_claim_policy': claims.ECONOMIC_CLAIM_POLICY,
                'claim_reviewer_public_keys': public_keys}}
            summary = {'evidence_mode': 'LIVE', 'cohort_sha256': cohort_hash,
                       'economic_claim_review_eligible': True,
                       'qualified_total_cost_savings': False,
                       'paired_cost_delta_usd': {'mean_p2p_minus_direct_usd': -0.1,
                                                 'bootstrap_95pct': [-0.2, -0.01]}}
            summary_bytes = json.dumps(summary, sort_keys=True, separators=(',', ':')).encode()
            base = {'schema': 'urace-p2p-economic-claim-review-v1',
                    'cohort_sha256': cohort_hash,
                    'summary_sha256': hashlib.sha256(summary_bytes).hexdigest(),
                    'economic_claim_policy_sha256': claims.canonical_sha256(claims.ECONOMIC_CLAIM_POLICY),
                    'decision': claims.APPROVAL,
                    'full_evidence_reviewed': True,
                    'workload_provenance_reviewed': True,
                    'reviewer_independence_attested': True,
                    'claim_scope': 'this cohort only; no general executor-price guarantee'}
            identities = {public_id(first.public()): first,
                          public_id(second.public()): second}
            envelopes = []
            for reviewer_id, identity in identities.items():
                payload = {**base, 'reviewer_id': reviewer_id}
                envelopes.append({'payload': payload,
                                  'signature': identity.sign(payload, claims.DOMAIN)})
            with patch.object(claims, 'verify_plan', return_value=True):
                result = claims.verify_reviews(plan, summary, summary_bytes, envelopes)
                self.assertTrue(result['qualified_total_cost_savings'])
                self.assertEqual(result['status'], 'QUALIFIED_COHORT_SPECIFIC_COST_SAVINGS')
                altered = dict(summary, paired_cost_delta_usd={'mean_p2p_minus_direct_usd': 0})
                with self.assertRaises(ValueError):
                    claims.verify_reviews(plan, altered, summary_bytes, envelopes)

    def test_synthetic_or_ineligible_summary_cannot_be_review_qualified(self):
        plan = {'cohort_sha256': 'a' * 64, 'identity': {'evidence_mode': 'SYNTHETIC'}}
        with patch.object(claims, 'verify_plan', return_value=True):
            with self.assertRaises(ValueError):
                claims.verify_reviews(plan, {'evidence_mode': 'SYNTHETIC'}, b'{}', [])


if __name__ == '__main__':
    unittest.main()
