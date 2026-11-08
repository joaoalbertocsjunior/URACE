"""Run the zero-provider, localhost-only 30-pair protocol validation cohort.

This deliberately emits synthetic product/value/token/cost inputs. Its P2P
catalog, fetch, quarantine, signed receipt, and seller acknowledgement traverse
the real URACE mutual-TLS exchange between loopback fixture peers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'runtime'))

from test_p2p_pair_protocol import P2PPairProtocolTests


def verify_evidence(root_path: str | Path) -> dict:
    """Verify every published receipt, hash, seller audit link, and paired result."""
    import p2p_pair_protocol as protocol
    from p2p_study_plan import verify_plan
    from urace.peer_exchange import Exchange

    root = Path(root_path).resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Evidence root must be a regular directory')
    manifest_path = root / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema') != 'urace-p2p-synthetic-evidence-v1':
        raise ValueError('Unknown synthetic evidence manifest schema')
    expected_files = manifest.get('files')
    if not isinstance(expected_files, dict):
        raise ValueError('Evidence manifest has no file inventory')
    all_paths = list(root.rglob('*'))
    if any(path.is_symlink() for path in all_paths):
        raise ValueError('Evidence bundle cannot contain symlinks')
    files = [path for path in all_paths if path.is_file()]
    actual = {str(path.relative_to(root)) for path in files if path != manifest_path}
    if actual != set(expected_files):
        raise ValueError('Evidence bundle files differ from the manifest inventory')
    private_names = {'identity-key.pem', 'identity-cert.pem', 'hybrid-identity.json', 'identity.json'}
    if any(Path(name).name in private_names for name in actual):
        raise ValueError('Evidence bundle includes private identity material')
    for name, metadata in expected_files.items():
        data = (root / name).read_bytes()
        if (len(data) != metadata.get('bytes')
                or hashlib.sha256(data).hexdigest() != metadata.get('sha256')):
            raise ValueError('Evidence file hash/size mismatch: ' + name)

    plan = json.loads((root / 'cohort-plan.json').read_text(encoding='utf-8'))
    if not verify_plan(plan) or plan.get('cohort_sha256') != manifest.get('cohort_sha256'):
        raise ValueError('Frozen plan is invalid or differs from the evidence manifest')
    pairs = [json.loads(line) for line in (root / 'pairs.jsonl').read_text(encoding='utf-8').splitlines()
             if line.strip()]
    if len(pairs) != 30:
        raise ValueError('Synthetic evidence must contain exactly 30 pair manifests')
    results = [protocol.verify_pair(pair, root, plan['identity']) for pair in pairs]
    report = protocol.summarize_pairs(
        results, cohort_sha256=plan['cohort_sha256'],
        expected_pair_ids=[pair['task']['pair_id'] for pair in plan['pairs']],
        evidence_mode=plan['identity']['evidence_mode'],
        claim_policy=plan['identity']['economic_claim_policy'],
        workload_provenance=plan['identity'].get('workload_provenance'))
    if report.get('status') != 'READY_FOR_INDEPENDENT_REVIEW':
        raise ValueError('One or more P2P/direct pair evidence rows failed verification')

    seller_rows = Exchange(root / 'seller-exchange').audit_rows()
    seller_acks = {row.get('sha256'): row for row in seller_rows
                   if row.get('kind') == 'OPEN_ASSET_QUARANTINE_ACK'}
    attestations = [row for row in seller_rows
                    if row.get('kind') == 'OPEN_ASSET_QUARANTINE_ACK_ATTESTED']
    if len(seller_acks) != 30 or len(attestations) != 30:
        raise ValueError('Seller audit chain lacks 30 retained receipt/attestation pairs')
    for pair in pairs:
        arm = pair['arms']['p2p_borrow']
        buyer_rows = Exchange((root / arm['exchange_marker_path']).parent).audit_rows()
        acknowledgements = [row for row in buyer_rows
                            if row.get('kind') == 'OPEN_ASSET_SELLER_ACK_RECEIVED'
                            and row.get('bundle') == arm['bundle_id']]
        if len(acknowledgements) != 1:
            raise ValueError('Buyer audit lacks a unique seller acknowledgement')
        attestation = acknowledgements[0].get('seller_attestation')
        event_hash = (attestation or {}).get('payload', {}).get('seller_audit_event_sha256')
        seller_event = seller_acks.get(event_hash)
        if (seller_event is None or seller_event.get('bundle') != arm['bundle_id']
                or seller_event.get('peer') != arm['exchange_buyer_id']
                or not any(row.get('bundle') == arm['bundle_id']
                           and row.get('seller_attestation') == attestation
                           for row in attestations)):
            raise ValueError('Buyer receipt does not match seller-retained signed audit evidence')

    synthetic_summary = json.loads((root / 'summary.json').read_text(encoding='utf-8'))
    if (synthetic_summary.get('evidence_mode') != 'SYNTHETIC_LOCAL_ONLY'
            or synthetic_summary.get('qualified_total_cost_savings') is not False
            or synthetic_summary.get('empirical_savings_claim') is not False
            or synthetic_summary.get('synthetic_inputs', {}).get('provider_calls') != 0):
        raise ValueError('Synthetic evidence improperly claims empirical savings or provider usage')
    return {'status': 'SYNTHETIC_EVIDENCE_VERIFIED_NOT_ECONOMIC_PROOF',
            'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'cohort_sha256': plan['cohort_sha256'], 'valid_pairs': report['valid_pairs'],
            'seller_retained_acknowledgements': len(seller_acks),
            'acceptance_rates': report['acceptance_rates'],
            'mean_value_score_by_arm': report['mean_value_score_by_arm'],
            'valid_pair_native_tokens': report['valid_pair_native_tokens'],
            'paired_cost_usd_totals': report['paired_cost_usd_totals'],
            'paired_cost_delta_usd': report['paired_cost_delta_usd'],
            'cost_claim_status': report['cost_claim_status'],
            'qualified_total_cost_savings': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='new directory to hold public, independently verifiable synthetic evidence')
    parser.add_argument('--verify-evidence', help='verify a previously published synthetic evidence directory')
    args = parser.parse_args()
    if args.verify_evidence:
        try:
            print(json.dumps(verify_evidence(args.verify_evidence), sort_keys=True, separators=(',', ':')))
            return 0
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            print(json.dumps({'status': 'EVIDENCE_REJECTED', 'error': str(error)}, sort_keys=True))
            return 2
    case = P2PPairProtocolTests(
        'test_30_pair_synthetic_cohort_compares_value_tokens_and_cost_without_savings_claim')
    case.setUp()
    try:
        case.evidence_output = args.output
        case.test_30_pair_synthetic_cohort_compares_value_tokens_and_cost_without_savings_claim()
        print(json.dumps(case.synthetic_report, sort_keys=True, separators=(',', ':')))
        return 0
    finally:
        case.tearDown()


if __name__ == '__main__':
    raise SystemExit(main())
