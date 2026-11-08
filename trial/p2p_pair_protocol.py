"""Evidence checks for P2P-borrow versus direct-executor matched pairs.

This verifier reports resource dimensions separately. URACE reputation units are
not converted to money or provider tokens without an explicit, verified rate.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import math
import random
from pathlib import Path

SCHEMA = 'urace-p2p-executor-pair-v2'
COST_SCHEMA = 'urace-p2p-paired-cost-v1'
ARMS = ('direct_executor', 'p2p_borrow')
FAMILIES = ('navigation', 'recovery', 'receipts', 'requirements_change', 'integration')
MIN_PAIRS = 30
MIN_PER_FAMILY = 6
ECONOMIC_CLAIM_POLICY = {
    'schema': 'urace-p2p-economic-claim-policy-v1',
    'scope': 'cohort_specific_end_to_end_usd',
    'bootstrap': 'paired_percentile', 'confidence_level': 0.95,
    'replicates': 10000, 'minimum_valid_pairs': MIN_PAIRS,
    'minimum_pairs_per_family': MIN_PER_FAMILY,
    'require_both_arms_accepted_each_pair': True,
    'require_p2p_value_not_below_direct_each_pair': True,
    'require_zero_urace_units_paid': True,
    'provider_cost_bases': ['ACTUAL_MARGINAL', 'SUBSCRIPTION_ALLOCATED'],
    'independent_claim_reviewers': 2,
}


def _safe_file(root: Path, relative: str) -> Path:
    if root.is_symlink():
        raise ValueError('Study root cannot be a symlink')
    rel = Path(relative)
    if not isinstance(relative, str) or not relative or rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Evidence paths must be relative to the study root')
    root = root.resolve()
    candidate = root / rel
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Evidence path cannot traverse symlinks')
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('Evidence file must remain inside the study root')
    return resolved


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _token_breakdown(receipts: list[dict]) -> dict:
    parts = {'input_tokens': [], 'output_tokens': [], 'cache_creation_input_tokens': [],
             'cache_read_input_tokens': []}
    for receipt in receipts:
        details = receipt.get('accounting_details') or {}
        if not details.get('known'):
            return {key: None for key in parts}
        if receipt.get('provider') == 'claude':
            models = details.get('models')
            if not isinstance(models, dict) or not models:
                return {key: None for key in parts}
            for name in parts:
                source = {'input_tokens': 'uncached_input_tokens',
                          'output_tokens': 'output_tokens',
                          'cache_creation_input_tokens': 'cache_creation_input_tokens',
                          'cache_read_input_tokens': 'cache_read_input_tokens'}[name]
                vals = [m.get(source) for m in models.values()]
                if any(type(v) is not int or v < 0 for v in vals):
                    return {key: None for key in parts}
                parts[name].append(sum(vals))
        elif receipt.get('provider') == 'codex':
            incoming = details.get('input_tokens')
            outgoing = details.get('output_tokens')
            cached = details.get('cached_input_tokens_included_in_input', 0)
            if any(type(v) is not int or v < 0 for v in (incoming, outgoing, cached)) or cached > incoming:
                return {key: None for key in parts}
            parts['input_tokens'].append(incoming)
            parts['output_tokens'].append(outgoing)
            parts['cache_creation_input_tokens'].append(0)
            parts['cache_read_input_tokens'].append(cached)
        else:
            return {key: None for key in parts}
    return {key: sum(values) if values else 0 for key, values in parts.items()}


def _acceptance(arm: dict, root: Path, expected: dict) -> dict:
    from urace.ledger_crypto import public_id, verify
    path = _safe_file(root, arm.get('acceptance_receipt_path'))
    raw = path.read_bytes()
    if _sha256(raw) != arm.get('acceptance_receipt_sha256'):
        raise ValueError('Acceptance receipt hash mismatch')
    envelope = json.loads(raw)
    if not isinstance(envelope, dict) or not isinstance(envelope.get('payload'), dict):
        raise ValueError('Acceptance receipt envelope is malformed')
    receipt = envelope['payload']
    required = {
        'pair_id': expected['pair_id'],
        'task_sha256': expected['task_sha256'],
        'acceptance_contract_sha256': expected['acceptance_contract_sha256'],
        'value_rubric_sha256': expected['value_rubric_sha256'],
        'arm': arm['arm'],
        'evaluator_id': expected['independent_evaluator_id'],
        'measurement_complete': True,
    }
    if (any(receipt.get(key) != value for key, value in required.items())
            or type(receipt.get('passed')) is not bool
            or type(receipt.get('value_score')) not in (int, float)
            or not math.isfinite(receipt['value_score'])
            or not 0.0 <= receipt['value_score'] <= 1.0):
        raise ValueError('Acceptance receipt is incomplete or mismatched')
    public = expected.get('independent_evaluator_public')
    if not isinstance(public, dict) or public_id(public) != expected['independent_evaluator_id']:
        raise ValueError('Independent evaluator key is not bound to the frozen study identity')
    verify(public, receipt, envelope.get('signature'), 'p2p-pair-acceptance')
    return receipt


def _no_call_receipt(arm: dict, root: Path, task: dict, identity: dict) -> dict:
    """Validate signed evidence that an accepted P2P arm made zero provider calls."""
    from urace.ledger_crypto import public_id, verify
    path = _safe_file(root, arm.get('no_call_receipt_path'))
    raw = path.read_bytes()
    if _sha256(raw) != arm.get('no_call_receipt_sha256'):
        raise ValueError('No-call receipt hash mismatch')
    envelope = json.loads(raw)
    if not isinstance(envelope, dict) or not isinstance(envelope.get('payload'), dict):
        raise ValueError('No-call receipt envelope is malformed')
    receipt = envelope['payload']
    required = {'pair_id': task['pair_id'], 'task_sha256': task['task_sha256'],
                'arm': 'p2p_borrow', 'evaluator_id': identity.get('independent_evaluator_id'),
                'measurement_complete': True, 'provider_call_count': 0,
                'provider_tokens': 0, 'provider_usage_known': True}
    if any(receipt.get(key) != value for key, value in required.items()):
        raise ValueError('No-call receipt is incomplete or claims provider usage')
    public = identity.get('independent_evaluator_public')
    if not isinstance(public, dict) or public_id(public) != identity.get('independent_evaluator_id'):
        raise ValueError('No-call attestation key is not pinned to the study identity')
    verify(public, receipt, envelope.get('signature'), 'p2p-pair-no-call')
    return receipt


def _exchange_fill(arm: dict, root: Path, task: dict, identity: dict) -> tuple[dict, dict]:
    from urace.peer_exchange import Exchange
    from urace.ledger_crypto import public_id, verify

    exchange_root = _safe_file(root, arm.get('exchange_marker_path')).parent
    if exchange_root.is_symlink():
        raise ValueError('Exchange evidence cannot be a symlink')
    exchange = Exchange(exchange_root)
    rows = exchange.audit_rows()  # verifies local hash chain and signed ledger sidecar
    listing_id = arm.get('listing_id')
    feature_id = arm.get('feature_id')
    artifact_sha256 = arm.get('artifact_sha256')
    listings = [r for r in rows if r.get('kind') == 'EQUITY_LISTING' and r.get('listing_id') == listing_id]
    fills = [r for r in rows if r.get('kind') == 'EQUITY_LISTING_FILLED' and r.get('listing_id') == listing_id]
    grants = [r for r in rows if r.get('kind') == 'EQUITY_GRANT' and r.get('feature_id') == feature_id]
    if len(listings) != 1 or len(fills) != 1 or len(grants) != 1:
        raise ValueError('Exchange snapshot lacks one matching listing, fill, and feature grant')
    listing, fill = listings[0], fills[0]
    if listing.get('feature_id') != feature_id or fill.get('feature_id') != feature_id:
        raise ValueError('Filled feature does not match the declared asset')
    if fill.get('seller_id') != listing.get('seller_id'):
        raise ValueError('Fill seller differs from the seller attested on the listing')
    if grants[0].get('peer_id') != listing.get('seller_id'):
        raise ValueError('Feature grant owner differs from the listing seller')
    if fill.get('price_units') != listing.get('ask_price_units'):
        raise ValueError('Fill price differs from the signed listing')
    if fill.get('buyer_id') != arm.get('exchange_buyer_id'):
        raise ValueError('Fill buyer does not match the P2P study arm')
    fee_rows = [r for r in rows if r.get('kind') == 'CREDIT_DELTA'
                and r.get('direction') == 'protocol_fee' and r.get('listing_id') == listing_id]
    delivery_rows = [r for r in rows if r.get('kind') == 'DELIVERY_FEE'
                     and r.get('listing_id') == listing_id]
    unlinked_delivery_rows = [r for r in rows if r.get('kind') == 'DELIVERY_FEE'
                              and r.get('feature_id') == feature_id
                              and r.get('buyer_peer_id') == fill.get('buyer_id')
                              and not r.get('listing_id')]
    if unlinked_delivery_rows:
        raise ValueError('Delivery-fee ledger rows lack listing identity; fee reconciliation is incomplete')
    protocol_fee_units = sum(int(r.get('amount_units', 0)) for r in fee_rows)
    delivery_fee_units = sum(int(r.get('fee_units', 0)) for r in delivery_rows)
    if not any(r.get('artifact_ref') == artifact_sha256 for r in grants):
        raise ValueError('Feature artifact digest is not bound to the exchange grant')
    artifact_path = _safe_file(root, arm.get('artifact_path'))
    digest = hashlib.sha256()
    with artifact_path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != artifact_sha256:
        raise ValueError('Delivered artifact bytes do not match the feature digest')

    seller_id = listing.get('seller_id')
    attestation = arm.get('seller_attestation')
    if not isinstance(attestation, dict):
        raise ValueError('Seller-signed listing/fill attestation is required')
    payload = attestation.get('payload')
    expected_payload = {'listing_id': listing_id, 'feature_id': feature_id,
                        'artifact_sha256': artifact_sha256, 'seller_id': seller_id,
                        'price_units': listing.get('ask_price_units')}
    if payload != expected_payload:
        raise ValueError('Seller attestation does not bind the listing, asset, seller, and price')
    public = identity.get('seller_public_keys', {}).get(seller_id)
    pinned_public = exchange.load().get('peers', {}).get(seller_id, {}).get('post_quantum')
    if (not isinstance(public, dict) or public != pinned_public
            or public_id(public) != attestation.get('seller_key_id')):
        raise ValueError('Seller signing key is not pinned to the listing peer')
    verify(public, payload, attestation.get('signature'), 'p2p-benchmark-listing')

    costs_path = _safe_file(root, arm.get('p2p_cost_receipt_path'))
    costs_raw = costs_path.read_bytes()
    if _sha256(costs_raw) != arm.get('p2p_cost_receipt_sha256'):
        raise ValueError('P2P cost receipt hash mismatch')
    costs_envelope = json.loads(costs_raw)
    costs = costs_envelope.get('payload')
    if (costs.get('schema') != COST_SCHEMA
            or costs.get('pair_id') != task['pair_id'] or costs.get('task_sha256') != task['task_sha256']
            or costs.get('feature_id') != feature_id or costs.get('artifact_sha256') != artifact_sha256
            or costs.get('listing_id') != listing_id
            or costs.get('measurement_contract_sha256') != identity.get('cost_measurement_contract_sha256')):
        raise ValueError('P2P cost receipt does not bind to this frozen pair and measurement contract')
    if (costs.get('protocol_fee_units') != protocol_fee_units
            or costs.get('delivery_fee_units') != delivery_fee_units):
        raise ValueError('Signed fee receipt does not reconcile to the buyer exchange ledger')
    evaluator_public = identity.get('independent_evaluator_public')
    if (not isinstance(evaluator_public, dict)
            or public_id(evaluator_public) != identity.get('independent_evaluator_id')):
        raise ValueError('Independent cost-measurement key is not pinned to the study')
    verify(evaluator_public, costs, costs_envelope.get('signature'), 'p2p-pair-cost')
    return {'listing_id': listing_id, 'feature_id': feature_id,
            'artifact_sha256': artifact_sha256, 'ask_price_units': fill['price_units'],
            'protocol_fee_units': protocol_fee_units, 'delivery_fee_units': delivery_fee_units,
            'fill_event_sha256': fill.get('sha256'),
            'seller_attestation_key_id': attestation['seller_key_id']}, costs


def _open_asset_delivery(arm: dict, root: Path, task: dict, identity: dict) -> tuple[dict, dict]:
    """Verify buyer quarantine and a portable seller-signed acknowledgement."""
    from urace.peer_exchange import Exchange
    from urace.ledger_crypto import verify
    buyer_marker = _safe_file(root, arm.get('exchange_marker_path'))
    buyer = Exchange(buyer_marker.parent)
    buyer_rows = buyer.audit_rows()
    bundle_id = arm.get('bundle_id')
    asset_id = arm.get('asset_id')
    feature_id = arm.get('feature_id')
    seller_id = arm.get('seller_peer_id')
    buyer_id = arm.get('exchange_buyer_id')
    received = [r for r in buyer_rows if r.get('kind') == 'RECEIVED_QUARANTINED'
                and r.get('bundle') == bundle_id and r.get('peer') == seller_id
                and r.get('feature') == feature_id]
    ack_rows = [r for r in buyer_rows if r.get('kind') == 'OPEN_ASSET_SELLER_ACK_RECEIVED'
                and r.get('bundle') == bundle_id and r.get('peer') == seller_id
                and r.get('asset_id') == asset_id]
    if len(received) != 1 or len(ack_rows) != 1:
        raise ValueError('Buyer quarantine or portable seller acknowledgement is missing/non-unique')
    bundle = buyer.inspect(bundle_id)['bundle']
    payload = bundle.get('payload', {})
    if (payload.get('sender') != seller_id or payload.get('recipient') != buyer_id
            or payload.get('feature') != feature_id or payload.get('artifact_ref') != arm.get('artifact_sha256')):
        raise ValueError('Delivered bundle does not match declared seller, buyer, feature, and artifact')
    seller_public = identity.get('seller_public_keys', {}).get(seller_id)
    buyer_pin = buyer.load().get('peers', {}).get(seller_id, {}).get('post_quantum')
    if not isinstance(seller_public, dict) or seller_public != buyer_pin:
        raise ValueError('Seller signing key is not pinned to the buyer exchange peer')
    verify(seller_public, payload, bundle.get('signature'), 'peer-bundle')
    from urace.feature_policy import effective, validate
    terms = payload.get('distribution_terms')
    if not isinstance(terms, dict):
        raise ValueError('Bundle lacks open-use terms')
    declared = validate({key: terms[key] for key in ('schema', 'access', 'license_id', 'essential', 'open_after_unix', 'resale')})
    if terms != effective(declared, payload.get('created_unix')) or terms.get('effective_access') != 'open' or terms.get('usage_price_units') != 0:
        raise ValueError('P2P benchmark asset is not explicitly open-use and free of usage price')
    raw_b64 = payload.get('artifact_b64')
    if not isinstance(raw_b64, str):
        raise ValueError('Delivered bundle does not contain the transferred bytes')
    import base64
    raw = base64.b64decode(raw_b64, validate=True)
    if _sha256(raw) != arm.get('artifact_sha256'):
        raise ValueError('Transferred artifact bytes do not match the frozen digest')
    source_asset = task.get('source_asset')
    if source_asset is not None:
        if (source_asset.get('feature_id') != feature_id
                or source_asset.get('artifact_sha256') != arm.get('artifact_sha256')):
            raise ValueError('Transferred asset differs from the source feature frozen in the cohort task')
        from p2p_local_feature_assets import verify_bundle
        verify_bundle(raw, feature_id=feature_id, artifact_sha256=arm['artifact_sha256'],
                      source_manifest_sha256=source_asset.get('source_manifest_sha256'),
                      repo_root=Path(__file__).resolve().parent.parent)
    artifact_path = _safe_file(root, arm.get('artifact_path'))
    if _sha256(artifact_path.read_bytes()) != arm.get('artifact_sha256'):
        raise ValueError('P2P arm workspace artifact bytes do not match the borrowed asset')

    ack = ack_rows[0]
    receipt_envelope = ack.get('buyer_receipt')
    buyer_public = identity.get('exchange_buyer_public')
    from urace.ledger_crypto import validate_public
    expected_receipt = {'schema': 'urace-delivery-receipt-v1', 'bundle_id': bundle_id,
                        'sender': seller_id, 'recipient': buyer_id, 'feature': feature_id,
                        'artifact_sha256': arm['artifact_sha256'],
                        'claim': 'BYTES_QUARANTINED_NOT_QUALIFIED'}
    if (not isinstance(receipt_envelope, dict) or receipt_envelope.get('payload') != expected_receipt
            or not isinstance(buyer_public, dict)):
        raise ValueError('Seller ledger lacks matching buyer-signed quarantine receipt')
    validate_public(buyer_public)
    verify(buyer_public, expected_receipt, receipt_envelope.get('signature'), 'delivery-receipt')
    seller_attestation = ack.get('seller_attestation')
    seller_ack_payload = {
        'schema': 'urace-open-asset-seller-ack-v1', 'bundle_id': bundle_id,
        'asset_id': asset_id, 'seller_peer_id': seller_id, 'buyer_peer_id': buyer_id,
        'artifact_sha256': arm['artifact_sha256'],
        'buyer_receipt_sha256': _sha256(json.dumps(receipt_envelope, sort_keys=True,
                                                   separators=(',', ':'), allow_nan=False).encode()),
        'seller_audit_event_sha256': ack.get('seller_attestation', {}).get('payload', {}).get('seller_audit_event_sha256'),
        'buyer_status': ack.get('buyer_status'),
    }
    if (not isinstance(seller_attestation, dict)
            or seller_attestation.get('payload') != seller_ack_payload
            or seller_ack_payload['buyer_status'] not in ('QUARANTINED', 'ALREADY_QUARANTINED')
            or ack.get('artifact_sha256') != arm['artifact_sha256']):
        raise ValueError('Portable seller acknowledgement does not bind the received bundle and buyer receipt')
    verify(seller_public, seller_ack_payload, seller_attestation.get('signature'), 'open-asset-seller-ack')
    discovery_metrics = arm.get('discovery_network_metrics')
    fetch_metrics = arm.get('fetch_network_metrics')
    for metrics in (discovery_metrics, fetch_metrics):
        if (not isinstance(metrics, dict)
                or type(metrics.get('application_payload_bytes')) is not int
                or metrics['application_payload_bytes'] < 0
                or type(metrics.get('elapsed_seconds')) not in (int, float)
                or not math.isfinite(metrics['elapsed_seconds']) or metrics['elapsed_seconds'] < 0):
            raise ValueError('P2P discovery and fetch transport measurements are required')
    measured_bytes = (discovery_metrics['application_payload_bytes']
                      + fetch_metrics['application_payload_bytes'])

    costs_path = _safe_file(root, arm.get('p2p_cost_receipt_path'))
    costs_raw = costs_path.read_bytes()
    if _sha256(costs_raw) != arm.get('p2p_cost_receipt_sha256'):
        raise ValueError('P2P cost receipt hash mismatch')
    envelope = json.loads(costs_raw)
    costs = envelope.get('payload')
    if (costs.get('schema') != COST_SCHEMA
            or costs.get('pair_id') != task['pair_id'] or costs.get('task_sha256') != task['task_sha256']
            or costs.get('delivery_kind') != 'open_asset' or costs.get('asset_id') != asset_id
            or costs.get('bundle_id') != bundle_id or costs.get('feature_id') != feature_id
            or costs.get('artifact_sha256') != arm['artifact_sha256']
            or costs.get('measurement_contract_sha256') != identity.get('cost_measurement_contract_sha256')):
        raise ValueError('P2P cost receipt does not bind to this open-asset pair and measurement contract')
    if (costs.get('network_transfer_bytes') != measured_bytes
            or not math.isclose(costs.get('discovery_seconds', -1), discovery_metrics['elapsed_seconds'], rel_tol=0, abs_tol=0.01)
            or not math.isclose(costs.get('fetch_seconds', -1), fetch_metrics['elapsed_seconds'], rel_tol=0, abs_tol=0.01)):
        raise ValueError('Signed cost receipt does not reconcile to measured discovery/fetch traffic and time')
    evaluator_public = identity.get('independent_evaluator_public')
    from urace.ledger_crypto import public_id
    if not isinstance(evaluator_public, dict) or public_id(evaluator_public) != identity.get('independent_evaluator_id'):
        raise ValueError('Independent cost-measurement key is not pinned to the study')
    verify(evaluator_public, costs, envelope.get('signature'), 'p2p-pair-cost')
    return {'delivery_kind': 'open_asset', 'bundle_id': bundle_id,
            'asset_id': asset_id, 'feature_id': feature_id,
            'artifact_sha256': arm['artifact_sha256'], 'ask_price_units': 0,
            'protocol_fee_units': 0, 'delivery_fee_units': 0,
            'buyer_receipt_event_sha256': received[0].get('sha256'),
            'buyer_ack_event_sha256': ack.get('sha256'),
            'seller_ack_event_sha256': seller_ack_payload['seller_audit_event_sha256'],
            'seller_signature_verified': True}, costs


def verify_pair(pair: dict, study_root: str | Path, identity: dict) -> dict:
    """Verify one pair's task, profile, native receipts, acceptance, and P2P fill.

    A valid pair supports a per-provider native-resource comparison. It does not
    itself establish that URACE credits are cheaper than an executor in money.
    """
    root = Path(study_root)
    observed_resources = {}
    try:
        if pair.get('schema') != SCHEMA or not isinstance(pair.get('arms'), dict):
            raise ValueError('Unknown pair schema or missing arms')
        if set(pair['arms']) != set(ARMS):
            raise ValueError('Pair must include direct_executor and p2p_borrow arms')
        task = pair.get('task', {})
        for key in ('pair_id', 'task_id', 'task_sha256', 'acceptance_contract_sha256',
                    'value_rubric_sha256', 'family', 'repeat'):
            if task.get(key) is None:
                raise ValueError('Missing task identity field: ' + key)
        if task['family'] not in FAMILIES:
            raise ValueError('Task family is outside the frozen protocol')
        planned = identity.get('planned_pairs', {}).get(task['pair_id'])
        if identity.get('planned_pairs') is not None:
            if not isinstance(planned, dict) or planned.get('task') != task or planned.get('arm_order') != pair.get('arm_order'):
                raise ValueError('Pair identity or arm order differs from the frozen cohort plan')
        if task.get('task_sha256') != identity.get('task_sha256_by_id', {}).get(task['task_id']):
            raise ValueError('Task hash does not match the frozen study task')
        if task.get('acceptance_contract_sha256') != identity.get('acceptance_contract_sha256_by_family', {}).get(task['family']):
            raise ValueError('Acceptance contract does not match the frozen study protocol')
        if task.get('value_rubric_sha256') != identity.get('value_rubric_sha256_by_family', {}).get(task['family']):
            raise ValueError('Value rubric does not match the frozen study protocol')
        evaluator = identity.get('independent_evaluator_id')
        if not isinstance(evaluator, str) or not evaluator:
            raise ValueError('Study identity lacks a frozen independent evaluator')

        arms = pair['arms']
        rows = {}
        acceptances = {}
        for arm_name in ARMS:
            arm = arms[arm_name]
            if arm.get('arm') != arm_name or arm.get('pair_id') != task['pair_id']:
                raise ValueError('Arm identity does not match its pair')
            for key in ('product_id', 'provider', 'model', 'client_version', 'effort', 'actual_providers'):
                if key not in arm:
                    raise ValueError('Missing arm profile field: ' + key)
            if arm.get('actual_providers') != [arm.get('provider')]:
                raise ValueError('Each arm must use exactly the same single declared provider')
            if arm.get('task_sha256') != task['task_sha256'] or arm.get('acceptance_contract_sha256') != task['acceptance_contract_sha256']:
                raise ValueError('Arm task or acceptance contract differs from the pair')
            if arm.get('product_id') != identity.get('product_id'):
                raise ValueError('Arm product scope differs from the frozen study')
            receipts = arm.get('native_receipts')
            if arm_name == 'p2p_borrow' and not receipts:
                no_call = _no_call_receipt(arm, root, task, identity)
                rows[arm_name] = {'tokens': 0, 'native_seconds': 0, 'receipt_ids': [],
                                  'authoritative_receipts_match': True, 'all_cost_known': True,
                                  'cached_tokens_match': True, 'no_call_receipt': no_call}
                observed_resources[arm_name] = {
                    'native_tokens': 0, 'native_seconds': 0, 'receipt_ids': [],
                    'token_breakdown': {'input_tokens': 0, 'output_tokens': 0,
                                        'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0},
                    'no_call_receipt_sha256': arm.get('no_call_receipt_sha256')}
                continue
            if not isinstance(receipts, list) or not receipts:
                raise ValueError('Direct executor arm requires attributable native receipts')
            row = {**arm, 'native_receipts': receipts}
            from qualification_protocol import reconcile
            reconciled = reconcile(row, root)
            if reconciled['authoritative_receipts_match'] is not True or not reconciled['all_cost_known'] or not reconciled['cached_tokens_match']:
                raise ValueError('Native usage receipts do not reconcile authoritatively')
            rows[arm_name] = reconciled
            observed_resources[arm_name] = {
                'native_tokens': reconciled['tokens'],
                'native_seconds': reconciled['native_seconds'],
                'receipt_ids': reconciled['receipt_ids'],
                'token_breakdown': _token_breakdown(receipts),
            }
        for arm_name in ARMS:
            arm = arms[arm_name]
            acceptances[arm_name] = _acceptance(arm, root, {
                'pair_id': task['pair_id'], 'task_sha256': task['task_sha256'],
                'acceptance_contract_sha256': task['acceptance_contract_sha256'],
                'value_rubric_sha256': task['value_rubric_sha256'],
                'independent_evaluator_id': evaluator,
                'independent_evaluator_public': identity.get('independent_evaluator_public'),
            })

        direct, p2p = arms['direct_executor'], arms['p2p_borrow']
        profile_keys = ('product_id', 'provider', 'model', 'client_version', 'effort')
        if any(direct.get(key) != p2p.get(key) for key in profile_keys):
            raise ValueError('Pair arms do not use the same product and executor profile')
        profile = identity.get('executor_profile')
        if (not isinstance(profile, dict)
                or any(direct.get(key) != profile.get(key)
                       for key in ('provider', 'model', 'client_version', 'effort'))):
            raise ValueError('Pair executor profile differs from the frozen cohort profile')
        if p2p.get('delivery_kind') == 'open_asset':
            exchange_fill, costs = _open_asset_delivery(p2p, root, task, identity)
        else:
            exchange_fill, costs = _exchange_fill(p2p, root, task, identity)
        integer_costs = ('protocol_fee_units', 'delivery_fee_units', 'network_transfer_bytes')
        for key in integer_costs:
            value = costs.get(key)
            if type(value) is not int or value < 0:
                raise ValueError('P2P cost receipt missing or invalid: ' + key)
        if (costs['protocol_fee_units'] != exchange_fill.get('protocol_fee_units')
                or costs['delivery_fee_units'] != exchange_fill.get('delivery_fee_units')):
            raise ValueError('P2P fee receipt does not reconcile to the verified exchange evidence')
        required_costs = ('network_cost_usd', 'discovery_seconds', 'fetch_seconds',
                          'integration_seconds', 'validation_seconds')
        for key in required_costs:
            value = costs.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('P2P cost receipt missing or invalid: ' + key)
        provider_costs = costs.get('provider_cost_usd_by_arm')
        non_provider_costs = costs.get('non_provider_cost_usd_by_arm')
        cost_basis = costs.get('provider_cost_basis')
        completeness = costs.get('non_provider_cost_complete_by_arm')
        if (not isinstance(provider_costs, dict) or set(provider_costs) != set(ARMS)
                or not isinstance(non_provider_costs, dict) or set(non_provider_costs) != set(ARMS)
                or not isinstance(completeness, dict) or set(completeness) != set(ARMS)
                or any(completeness[arm] is not True for arm in ARMS)
                or cost_basis not in ('ACTUAL_MARGINAL', 'API_EQUIVALENT', 'SUBSCRIPTION_ALLOCATED')):
            raise ValueError('Signed paired cost receipt must cover both arms and declare one provider billing basis')
        for arm_name in ARMS:
            for amounts, label in ((provider_costs, 'provider'), (non_provider_costs, 'non-provider')):
                value = amounts[arm_name]
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError(f'Signed {label} cost for {arm_name} is missing or invalid')
        p2p_units = (exchange_fill['ask_price_units'] + exchange_fill['protocol_fee_units']
                     + exchange_fill['delivery_fee_units'])
        direct_tokens = rows['direct_executor']['tokens']
        p2p_tokens = rows['p2p_borrow']['tokens']
        usd_by_arm = {arm_name: provider_costs[arm_name] + non_provider_costs[arm_name]
                      for arm_name in ARMS}
        usd_costs_comparable = (p2p_units == 0
                                and costs.get('provider_cost_basis') in
                                ('ACTUAL_MARGINAL', 'API_EQUIVALENT', 'SUBSCRIPTION_ALLOCATED'))
        p2p_minus_direct_usd = (usd_by_arm['p2p_borrow'] - usd_by_arm['direct_executor']
                                if usd_costs_comparable else None)
        end_to_end_cost_candidate = bool(
            usd_costs_comparable and p2p_minus_direct_usd is not None
            and p2p_minus_direct_usd < 0
            and acceptances['p2p_borrow']['passed']
            and acceptances['direct_executor']['passed']
            and acceptances['p2p_borrow']['value_score'] >= acceptances['direct_executor']['value_score'])
        direct_breakdown = observed_resources['direct_executor']['token_breakdown']
        p2p_breakdown = observed_resources['p2p_borrow']['token_breakdown']
        return {
            'status': 'PAIR_VALID_RESOURCE_COMPARISON',
            'pair_id': task['pair_id'], 'task_id': task['task_id'], 'family': task['family'],
            'repeat': task['repeat'],
            'provider': direct['provider'], 'model': direct['model'], 'effort': direct['effort'],
            'acceptance': {'direct_executor': acceptances['direct_executor']['passed'],
                           'p2p_borrow': acceptances['p2p_borrow']['passed'],
                           'independent_evaluator_id': evaluator,
                           'contract_sha256': task['acceptance_contract_sha256']},
            'value_produced': {
                'scale': 'independent evaluator normalized score [0,1] under the frozen acceptance contract',
                'direct_executor': acceptances['direct_executor']['value_score'],
                'p2p_borrow': acceptances['p2p_borrow']['value_score'],
                'p2p_minus_direct': (acceptances['p2p_borrow']['value_score']
                                     - acceptances['direct_executor']['value_score']),
            },
            'native_tokens': {'direct_executor': direct_tokens, 'p2p_borrow': p2p_tokens,
                              'p2p_minus_direct': p2p_tokens - direct_tokens,
                              'direct_breakdown': direct_breakdown,
                              'p2p_breakdown': p2p_breakdown,
                              'breakdown_delta': {key: (p2p_breakdown[key] - direct_breakdown[key]
                                                         if type(p2p_breakdown[key]) is int and type(direct_breakdown[key]) is int else None)
                                                  for key in direct_breakdown}},
            'p2p_costs': {'urace_units_paid': p2p_units,
                          'network_cost_usd': costs['network_cost_usd'],
                          'discovery_seconds': costs['discovery_seconds'],
                          'fetch_seconds': costs['fetch_seconds'],
                          'integration_seconds': costs['integration_seconds'],
                          'validation_seconds': costs['validation_seconds'],
                          'network_transfer_bytes': costs['network_transfer_bytes']},
            'cost_comparison': {
                'currency': 'USD', 'provider_cost_basis': cost_basis,
                'provider_cost_usd_by_arm': provider_costs,
                'non_provider_cost_usd_by_arm': non_provider_costs,
                'measured_partial_usd_by_arm': {
                    **usd_by_arm},
                'p2p_urace_units': p2p_units,
                'costs_complete_under_frozen_measurement_contract': True,
                'total_comparable_cost': usd_costs_comparable,
                'p2p_minus_direct_usd': p2p_minus_direct_usd,
                'end_to_end_cost_savings_candidate': end_to_end_cost_candidate,
                'p2p_price_comparison': {
                    'p2p_price_units': exchange_fill['ask_price_units'],
                    'p2p_price_unit': 'URACE_LOCAL_REPUTATION_UNITS',
                    'p2p_total_urace_units': p2p_units,
                    'executor_cost_currency': 'USD',
                    'status': 'INCOMMENSURATE_NO_VERIFIED_URACE_UNIT_CONVERSION',
                },
                'status': ('USD_COMPONENTS_COMPARABLE_FOR_ZERO_PRICE_TRANSFER'
                           if usd_costs_comparable else
                           'INCOMMENSURATE_UNTIL_URACE_UNIT_VALUATION_IS_VERIFIED'),
            },
            'executor_reported_cost_usd': {
                'direct_executor': direct.get('provider_reported_cost_usd'),
                'p2p_borrow': p2p.get('provider_reported_cost_usd'),
                'billing_kind': 'provider-reported; may be API-equivalent rather than actual subscription charge'},
            'total_cost_savings': (p2p_minus_direct_usd if usd_costs_comparable else None),
            'total_cost_status': ('COMPARABLE_BUYER_USD_COMPONENTS; SYNTHETIC_OR_LIVE_COHORT_REVIEW_REQUIRED'
                                  if usd_costs_comparable else
                                  'INCOMMENSURATE_UNTIL_URACE_UNIT_VALUATION_IS_VERIFIED'),
            'remote_fill_status': ('SELLER_BUNDLE_AND_BUYER_QUARANTINE_RECEIPT_VERIFIED; open-use transfer, no payment'
                                   if exchange_fill.get('delivery_kind') == 'open_asset'
                                   else 'SELLER_LISTING_SIGNATURE_VERIFIED; fill is from the buyer local signed ledger, not global consensus'),
            'evidence': {'native_receipts': {k: v['receipt_ids'] for k, v in rows.items()},
                         'exchange_fill': exchange_fill,
                         'acceptance_receipts': {k: arms[k]['acceptance_receipt_sha256'] for k in ARMS}},
            'observed_resources': observed_resources,
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        return {'status': 'PAIR_INELIGIBLE', 'pair_id': pair.get('task', {}).get('pair_id'),
                'reason': str(error), 'observed_resources': observed_resources}


def summarize_pairs(results: list[dict], *, cohort_sha256: str,
                    expected_pair_ids: list[str] | None = None,
                    evidence_mode: str = 'UNSPECIFIED',
                    claim_policy: dict | None = None,
                    workload_provenance: dict | None = None) -> dict:
    """Keep every attempted pair visible; readiness requires full frozen coverage."""
    if not isinstance(cohort_sha256, str) or len(cohort_sha256) != 64 or any(c not in '0123456789abcdef' for c in cohort_sha256):
        raise ValueError('cohort_sha256 must be lowercase SHA-256 hex')
    valid = [r for r in results if r.get('status') == 'PAIR_VALID_RESOURCE_COMPARISON']
    from collections import Counter
    attempted_ids = [r.get('pair_id') for r in results]
    duplicates = len(attempted_ids) != len(set(attempted_ids))
    unique_valid = []
    seen = set()
    for row in valid:
        if row.get('pair_id') not in seen:
            unique_valid.append(row); seen.add(row.get('pair_id'))
    valid = unique_valid
    counts = Counter(r.get('family') for r in valid)
    acceptance_counts = {arm: sum(r.get('acceptance', {}).get(arm) is True for r in valid)
                         for arm in ARMS}
    pair_outcomes = {
        'both_accepted': sum(all(r.get('acceptance', {}).get(arm) is True for arm in ARMS) for r in valid),
        'direct_only': sum(r.get('acceptance', {}).get('direct_executor') is True
                           and r.get('acceptance', {}).get('p2p_borrow') is False for r in valid),
        'p2p_only': sum(r.get('acceptance', {}).get('direct_executor') is False
                        and r.get('acceptance', {}).get('p2p_borrow') is True for r in valid),
        'neither': sum(all(r.get('acceptance', {}).get(arm) is False for arm in ARMS) for r in valid),
    }
    plan_covered = (expected_pair_ids is None or
                    (len(expected_pair_ids) == len(set(expected_pair_ids))
                     and set(attempted_ids) == set(expected_pair_ids)
                     and len(attempted_ids) == len(expected_pair_ids)))
    value_deltas = [r['value_produced']['p2p_minus_direct'] for r in valid
                    if isinstance(r.get('value_produced'), dict)]
    value_coverage_complete = len(value_deltas) == len(valid)
    acceptance_coverage_complete = all(
        isinstance(r.get('acceptance'), dict)
        and all(type(r['acceptance'].get(arm)) is bool for arm in ARMS) for r in valid)
    cost_coverage_complete = bool(valid) and all(
        isinstance(r.get('cost_comparison'), dict)
        and r['cost_comparison'].get('costs_complete_under_frozen_measurement_contract') is True
        and r['cost_comparison'].get('provider_cost_basis') in
        ('ACTUAL_MARGINAL', 'API_EQUIVALENT', 'SUBSCRIPTION_ALLOCATED')
        and set(r['cost_comparison'].get('measured_partial_usd_by_arm', {})) == set(ARMS)
        for r in valid)
    complete = (plan_covered and not duplicates and len(valid) == len(results)
                and value_coverage_complete and acceptance_coverage_complete
                and cost_coverage_complete
                and len(valid) >= MIN_PAIRS
                and all(counts[f] >= MIN_PER_FAMILY for f in FAMILIES))
    deltas = [r['native_tokens']['p2p_minus_direct'] for r in valid]
    attempted_tokens = {
        arm: sum(result.get('observed_resources', {}).get(arm, {}).get('native_tokens', 0)
                 for result in results)
        for arm in ARMS
    }
    interval = None
    if deltas:
        rng = random.Random(int(cohort_sha256[:16], 16))
        means = []
        for _ in range(10000):
            sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
            means.append(sum(sample) / len(sample))
        means.sort()
        interval = {'mean_native_token_delta': sum(deltas) / len(deltas),
                    'bootstrap_95pct': [means[int(0.025 * len(means))], means[min(len(means)-1, int(0.975 * len(means)))]]}
    value_interval = None
    if value_deltas:
        rng = random.Random(int(cohort_sha256[16:32], 16))
        means = []
        for _ in range(10000):
            sample = [value_deltas[rng.randrange(len(value_deltas))] for _ in value_deltas]
            means.append(sum(sample) / len(sample))
        means.sort()
        value_interval = {'mean_p2p_minus_direct': sum(value_deltas) / len(value_deltas),
                          'bootstrap_95pct': [means[int(0.025 * len(means))],
                                              means[min(len(means)-1, int(0.975 * len(means)))]]}
    direct_total = sum(r['native_tokens']['direct_executor'] for r in valid)
    p2p_total = sum(r['native_tokens']['p2p_borrow'] for r in valid)
    value_direct = [r['value_produced']['direct_executor'] for r in valid
                    if isinstance(r.get('value_produced'), dict)]
    value_p2p = [r['value_produced']['p2p_borrow'] for r in valid
                 if isinstance(r.get('value_produced'), dict)]
    direct_rate = acceptance_counts['direct_executor'] / len(valid) if valid else None
    p2p_rate = acceptance_counts['p2p_borrow'] / len(valid) if valid else None
    cost_deltas = [r['cost_comparison']['p2p_minus_direct_usd'] for r in valid
                   if isinstance(r.get('cost_comparison'), dict)
                   and r['cost_comparison'].get('total_comparable_cost') is True
                   and type(r['cost_comparison'].get('p2p_minus_direct_usd')) in (int, float)]
    cost_interval = None
    if cost_deltas:
        rng = random.Random(int(cohort_sha256[32:48], 16))
        means = []
        for _ in range(ECONOMIC_CLAIM_POLICY['replicates']):
            sample = [cost_deltas[rng.randrange(len(cost_deltas))] for _ in cost_deltas]
            means.append(sum(sample) / len(sample))
        means.sort()
        low = int(((1 - ECONOMIC_CLAIM_POLICY['confidence_level']) / 2) * len(means))
        high = min(len(means) - 1, int((1 - (1 - ECONOMIC_CLAIM_POLICY['confidence_level']) / 2) * len(means)))
        cost_interval = {'mean_p2p_minus_direct_usd': sum(cost_deltas) / len(cost_deltas),
                         'bootstrap_95pct': [means[low], means[high]],
                         'method': 'paired percentile bootstrap; deterministic from cohort hash'}
    bases = {r.get('cost_comparison', {}).get('provider_cost_basis') for r in valid}
    costs_comparable = (len(cost_deltas) == len(valid) and len(bases) == 1
                        and bool(valid) and all(r.get('cost_comparison', {}).get('total_comparable_cost') is True
                                                for r in valid))
    zero_credit_costs = costs_comparable and all(
        r.get('cost_comparison', {}).get('p2p_urace_units') == 0 for r in valid)
    provider_basis_eligible = bool(bases) and bases <= set(ECONOMIC_CLAIM_POLICY['provider_cost_bases'])
    all_pairs_accepted = bool(valid) and pair_outcomes['both_accepted'] == len(valid)
    value_noninferior = bool(valid) and all(
        type(r.get('value_produced', {}).get('p2p_minus_direct')) in (int, float)
        and r['value_produced']['p2p_minus_direct'] >= 0 for r in valid)
    preregistered_policy = claim_policy == ECONOMIC_CLAIM_POLICY
    claim_review_eligible = bool(
        evidence_mode == 'LIVE' and preregistered_policy and complete and all_pairs_accepted
        and value_noninferior and zero_credit_costs and provider_basis_eligible
        and cost_interval is not None and cost_interval['bootstrap_95pct'][1] < 0
        and isinstance(workload_provenance, dict)
        and workload_provenance.get('kind') == 'real_product_workloads')
    if evidence_mode not in ('LIVE', 'SYNTHETIC', 'UNSPECIFIED'):
        raise ValueError('evidence_mode must be LIVE, SYNTHETIC, or UNSPECIFIED')
    scenario_cost_result = None
    if evidence_mode == 'SYNTHETIC' and costs_comparable and cost_interval is not None:
        scenario_cost_result = {
            'status': 'SYNTHETIC_SCENARIO_ONLY',
            'p2p_minus_direct_usd': cost_interval['mean_p2p_minus_direct_usd'],
            'bootstrap_95pct': cost_interval['bootstrap_95pct'],
            'statement_scope': 'constructed inputs only; not observed costs or a real-world claim'}
    return {
        'schema': SCHEMA,
        'cohort_sha256': cohort_sha256,
        'status': 'READY_FOR_INDEPENDENT_REVIEW' if complete else 'INSUFFICIENT_OR_INVALID',
        'attempted_pairs': len(results), 'valid_pairs': len(valid),
        'ineligible_pairs': len(results) - len(valid), 'duplicate_pair_ids': duplicates, 'family_counts': dict(counts),
        'planned_pair_coverage_complete': plan_covered,
        'value_score_coverage_complete': value_coverage_complete,
        'acceptance_coverage_complete': acceptance_coverage_complete,
        'paired_cost_coverage_complete': cost_coverage_complete,
        'independent_acceptance_passes': acceptance_counts,
        'paired_acceptance_outcomes': pair_outcomes,
        'acceptance_rates': {'direct_executor': direct_rate, 'p2p_borrow': p2p_rate,
                             'p2p_minus_direct': p2p_rate - direct_rate if valid else None},
        'mean_value_score_by_arm': {
            'direct_executor': sum(value_direct) / len(value_direct) if value_direct else None,
            'p2p_borrow': sum(value_p2p) / len(value_p2p) if value_p2p else None,
            'p2p_minus_direct': sum(value_deltas) / len(value_deltas) if value_deltas else None,
            'scale': 'independent evaluator normalized score [0,1] under frozen acceptance contract',
        },
        'paired_value_delta': value_interval,
        'native_token_reduction_candidate': bool(complete and p2p_rate >= direct_rate
                                                   and value_p2p and value_direct
                                                   and sum(value_p2p) / len(value_p2p) >= sum(value_direct) / len(value_direct)
                                                   and p2p_total < direct_total),
        'all_attempted_native_tokens_by_arm': attempted_tokens,
        'family_deficits': {f: max(0, MIN_PER_FAMILY-counts[f]) for f in FAMILIES},
        'native_token_delta': interval,
        'valid_pair_native_tokens': {'direct_executor_total': direct_total,
                                     'p2p_borrow_total': p2p_total,
                                     'p2p_to_direct_ratio': p2p_total / direct_total if direct_total else None},
        'p2p_observed_overheads': {key: sum(r['p2p_costs'][key] for r in valid)
                                   for key in ('network_cost_usd', 'discovery_seconds',
                                               'fetch_seconds', 'integration_seconds',
                                               'validation_seconds') if valid and all(key in r.get('p2p_costs', {}) for r in valid)},
        'paired_cost_usd_totals': {
            arm: sum(r['cost_comparison']['measured_partial_usd_by_arm'][arm] for r in valid)
            if valid and all('cost_comparison' in r for r in valid) else None
            for arm in ARMS},
        'paired_cost_basis': (valid[0].get('cost_comparison', {}).get('provider_cost_basis')
                              if valid and all(r.get('cost_comparison', {}).get('provider_cost_basis')
                                               == valid[0].get('cost_comparison', {}).get('provider_cost_basis')
                                               for r in valid) else None),
        'paired_cost_delta_usd': cost_interval,
        'synthetic_scenario_cost_result': scenario_cost_result,
        'evidence_mode': evidence_mode,
        'economic_claim_policy': claim_policy,
        'workload_provenance': workload_provenance,
        'economic_claim_review_eligible': claim_review_eligible,
        'economic_claim_gate': {
            'complete_preregistered_cohort': complete,
            'both_arms_accepted_every_pair': all_pairs_accepted,
            'p2p_value_not_below_direct_every_pair': value_noninferior,
            'complete_comparable_usd_costs': costs_comparable,
            'zero_urace_units_paid': zero_credit_costs,
            'provider_billing_basis_allowed': provider_basis_eligible,
            'paired_cost_95pct_upper_bound_below_zero': bool(
                cost_interval and cost_interval['bootstrap_95pct'][1] < 0),
            'independent_reviewers_required': ECONOMIC_CLAIM_POLICY['independent_claim_reviewers'],
        },
        'end_to_end_cost_savings_candidate': bool(
            complete and valid and all(r.get('cost_comparison', {}).get('end_to_end_cost_savings_candidate')
                                       is True for r in valid)),
        'qualified_total_cost_savings': False,
        'cost_claim_status': ('AWAITING_TWO_INDEPENDENT_REVIEWS' if claim_review_eligible else
                              'SYNTHETIC_SCENARIO_ONLY' if evidence_mode == 'SYNTHETIC' and scenario_cost_result else
                              'NOT_QUALIFIED'),
        'interpretation': 'Synthetic cost arithmetic is scenario-only. Live cohort eligibility requires the exact preregistered gate, task acceptance in both arms, P2P value no lower in every pair, zero URACE units, complete comparable USD costs, and the paired 95% bootstrap upper bound below zero. A live result remains unqualified until two pinned independent reviewers sign the cohort-specific claim review.',
    }


def main(argv: list[str] | None = None) -> int:
    """Read a frozen study identity and JSONL pair manifests; print an audit report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study-root', required=True, help='root containing immutable evidence files')
    parser.add_argument('--identity', help='frozen study identity JSON (legacy; prefer --plan)')
    parser.add_argument('--pairs', required=True, help='JSONL of attempted pair manifests')
    parser.add_argument('--cohort-sha256', help='SHA-256 of frozen cohort manifest (legacy; prefer --plan)')
    parser.add_argument('--plan', help='immutable output from p2p_study_plan.py')
    args = parser.parse_args(argv)
    try:
        if args.plan:
            from p2p_study_plan import verify_plan
            plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
            if not verify_plan(plan):
                raise ValueError('Frozen cohort plan hash or design validation failed')
            identity = plan['identity']
            cohort_sha256 = plan['cohort_sha256']
            expected_ids = [p['task']['pair_id'] for p in plan['pairs']]
        else:
            if not args.identity or not args.cohort_sha256:
                raise ValueError('Pass --plan or both --identity and --cohort-sha256')
            identity = json.loads(Path(args.identity).read_text(encoding='utf-8'))
            cohort_sha256 = args.cohort_sha256
            expected_ids = None
        lines = Path(args.pairs).read_text(encoding='utf-8').splitlines()
        pairs = [json.loads(line) for line in lines if line.strip()]
        results = [verify_pair(pair, args.study_root, identity) for pair in pairs]
        report = summarize_pairs(results, cohort_sha256=cohort_sha256,
                                 expected_pair_ids=expected_ids,
                                 evidence_mode=identity.get('evidence_mode', 'UNSPECIFIED'),
                                 claim_policy=identity.get('economic_claim_policy'),
                                 workload_provenance=identity.get('workload_provenance'))
        report['pair_results'] = results
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 0 if report['status'] == 'READY_FOR_INDEPENDENT_REVIEW' else 2
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({'status': 'ERROR', 'error': str(error)}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
