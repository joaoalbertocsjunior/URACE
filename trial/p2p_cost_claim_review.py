"""Verify two pinned independent reviews for one live paired-cost cohort.

This emits a cohort-scoped claim receipt only. It cannot establish a global
price guarantee or qualify synthetic evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from p2p_pair_protocol import ECONOMIC_CLAIM_POLICY
from p2p_study_plan import verify_plan

DOMAIN = 'p2p-economic-claim-review'
APPROVAL = 'APPROVE_COHORT_SPECIFIC_COST_SAVINGS'


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def verify_reviews(plan: dict, summary: dict, summary_bytes: bytes,
                   reviews: list[dict]) -> dict:
    """Verify pinned reviewer signatures over the exact plan and summary bytes."""
    if not verify_plan(plan):
        raise ValueError('Frozen plan failed integrity or design validation')
    try:
        if json.loads(summary_bytes) != summary:
            raise ValueError('Parsed summary differs from the exact bytes reviewed')
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Summary bytes are not valid JSON') from error
    identity = plan['identity']
    if (identity.get('evidence_mode') != 'LIVE'
            or identity.get('economic_claim_policy') != ECONOMIC_CLAIM_POLICY):
        raise ValueError('Only a preregistered LIVE cohort can be reviewed')
    if summary.get('evidence_mode') != 'LIVE' or summary.get('cohort_sha256') != plan['cohort_sha256']:
        raise ValueError('Summary is not for this LIVE cohort')
    if summary.get('economic_claim_review_eligible') is not True:
        raise ValueError('Cohort has not passed the preregistered economic claim gates')
    if summary.get('qualified_total_cost_savings') is not False:
        raise ValueError('Summary must remain unqualified until these reviews are verified')
    reviewer_keys = identity.get('claim_reviewer_public_keys')
    if not isinstance(reviewer_keys, dict) or len(reviewer_keys) != 2 or len(reviews) != 2:
        raise ValueError('Exactly two pinned reviewers and signed review envelopes are required')
    expected_payload_base = {
        'schema': 'urace-p2p-economic-claim-review-v1',
        'cohort_sha256': plan['cohort_sha256'],
        'summary_sha256': hashlib.sha256(summary_bytes).hexdigest(),
        'economic_claim_policy_sha256': canonical_sha256(ECONOMIC_CLAIM_POLICY),
        'decision': APPROVAL,
        'full_evidence_reviewed': True,
        'workload_provenance_reviewed': True,
        'reviewer_independence_attested': True,
        'claim_scope': 'this cohort only; no general executor-price guarantee',
    }
    from urace.ledger_crypto import public_id, verify
    accepted = set()
    for envelope in reviews:
        if not isinstance(envelope, dict) or not isinstance(envelope.get('payload'), dict):
            raise ValueError('Malformed reviewer envelope')
        payload = envelope['payload']
        reviewer_id = payload.get('reviewer_id')
        if reviewer_id not in reviewer_keys or reviewer_id in accepted:
            raise ValueError('Reviewer is unpinned or duplicated')
        public = reviewer_keys[reviewer_id]
        if public_id(public) != reviewer_id:
            raise ValueError('Pinned reviewer key does not match reviewer ID')
        expected = {**expected_payload_base, 'reviewer_id': reviewer_id}
        if payload != expected:
            raise ValueError('Reviewer approval does not bind to the exact cohort and summary')
        try:
            verify(public, payload, envelope.get('signature'), DOMAIN)
        except Exception as error:
            raise ValueError('Reviewer signature is invalid') from error
        accepted.add(reviewer_id)
    if accepted != set(reviewer_keys):
        raise ValueError('Both distinct pinned reviewers must approve')
    return {
        'schema': 'urace-p2p-qualified-cost-claim-v1',
        'status': 'QUALIFIED_COHORT_SPECIFIC_COST_SAVINGS',
        'qualified_total_cost_savings': True,
        'cohort_sha256': plan['cohort_sha256'],
        'summary_sha256': expected_payload_base['summary_sha256'],
        'reviewer_ids': sorted(accepted),
        'paired_cost_delta_usd': summary['paired_cost_delta_usd'],
        'claim_scope': expected_payload_base['claim_scope'],
        'does_not_establish_global_claim': True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--reviews', required=True,
                        help='JSON file containing exactly two signed reviewer envelopes')
    args = parser.parse_args(argv)
    try:
        plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
        summary_bytes = Path(args.summary).read_bytes()
        summary = json.loads(summary_bytes)
        reviews = json.loads(Path(args.reviews).read_text(encoding='utf-8'))
        result = verify_reviews(plan, summary, summary_bytes, reviews)
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({'status': 'CLAIM_REVIEW_REJECTED', 'error': str(error)}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
