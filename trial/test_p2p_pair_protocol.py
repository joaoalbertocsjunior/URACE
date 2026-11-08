"""Evidence integrity tests for the P2P versus direct executor study protocol."""
import hashlib
import json
import copy
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'runtime'))

import p2p_pair_protocol as protocol
import p2p_study_plan as study_plan
from urace.peer_exchange import Exchange, atomic as exchange_atomic
from urace.ledger_crypto import Identity, public_id


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _publish_synthetic_evidence(source_root, target_root, plan, pairs, summary, seller):
    """Publish a reproducible evidence bundle containing public evidence only."""
    import shutil
    target = Path(target_root).expanduser().absolute()
    if target.exists() or target.is_symlink():
        raise ValueError('Synthetic evidence output must be a new path')
    target.mkdir(parents=True, exist_ok=False)
    write_json(target / 'cohort-plan.json', plan)
    pair_path = target / 'pairs.jsonl'
    pair_path.parent.mkdir(parents=True, exist_ok=True)
    with pair_path.open('x', encoding='utf-8') as stream:
        for pair in pairs:
            stream.write(json.dumps(pair, sort_keys=True, separators=(',', ':')) + '\n')
    for directory in ('acceptance', 'costs', 'transport', 'artifacts', 'exchange-evidence'):
        source = Path(source_root) / directory
        if source.is_dir():
            for item in source.rglob('*'):
                if item.is_symlink():
                    raise ValueError('Synthetic evidence cannot contain symlinks')
            shutil.copytree(source, target / directory)

    # Publish the seller's signed audit chain without any private identity files.
    seller_target = target / 'seller-exchange'
    seller_target.mkdir()
    for name in ('policy.json', 'audit.jsonl'):
        shutil.copyfile(seller.root / name, seller_target / name)
    ledger_source = seller.root / 'signed-audit'
    ledger_target = seller_target / 'signed-audit'
    ledger_target.mkdir()
    for item in ledger_source.iterdir():
        if item.name == 'identity.json':
            continue
        if item.is_symlink() or not item.is_file():
            raise ValueError('Seller evidence contains an unsafe file')
        if item.name not in ('public.json', 'head.json', 'writer.lock') and not item.name.endswith('.block'):
            continue
        shutil.copyfile(item, ledger_target / item.name)
    from urace.peer_exchange import Exchange
    seller_rows = Exchange(seller_target).audit_rows()
    seller_acks = {row['sha256']: row for row in seller_rows
                   if row.get('kind') == 'OPEN_ASSET_QUARANTINE_ACK'}
    seller_attestations = [row for row in seller_rows
                           if row.get('kind') == 'OPEN_ASSET_QUARANTINE_ACK_ATTESTED']
    if len(seller_acks) != 30 or len(seller_attestations) != 30:
        raise ValueError('Seller audit evidence does not contain 30 receipt/attestation pairs')
    for pair in pairs:
        arm = pair['arms']['p2p_borrow']
        marker = target / arm['exchange_marker_path']
        buyer_rows = Exchange(marker.parent).audit_rows()
        acknowledgements = [row for row in buyer_rows
                            if row.get('kind') == 'OPEN_ASSET_SELLER_ACK_RECEIVED'
                            and row.get('bundle') == arm['bundle_id']]
        if len(acknowledgements) != 1:
            raise ValueError('Buyer portable seller acknowledgement is missing/non-unique')
        attestation = acknowledgements[0].get('seller_attestation')
        seller_event_hash = (attestation or {}).get('payload', {}).get('seller_audit_event_sha256')
        retained = seller_acks.get(seller_event_hash)
        if (retained is None or retained.get('bundle') != arm['bundle_id']
                or retained.get('peer') != arm['exchange_buyer_id']
                or not any(row.get('bundle') == arm['bundle_id']
                           and row.get('seller_attestation') == attestation
                           for row in seller_attestations)):
            raise ValueError('Portable buyer acknowledgement does not link to seller-retained signed audit')

    summary = {**summary, 'evidence_mode': 'SYNTHETIC_LOCAL_ONLY',
               'status': 'SYNTHETIC_PIPELINE_VALIDATION_ONLY',
               'empirical_savings_claim': False,
               'proof_scope': 'protocol, signatures, artifacts, accounting schema, and cohort gates only'}
    write_json(target / 'summary.json', summary)
    private_names = {'identity-key.pem', 'identity-cert.pem', 'hybrid-identity.json', 'identity.json'}
    evidence_files = sorted(path for path in target.rglob('*') if path.is_file())
    if any(path.name in private_names for path in evidence_files):
        raise ValueError('Synthetic evidence bundle would expose private identity material')
    manifest_files = {
        str(path.relative_to(target)): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                        'bytes': path.stat().st_size}
        for path in evidence_files
    }
    manifest = {'schema': 'urace-p2p-synthetic-evidence-v1',
                'cohort_sha256': plan['cohort_sha256'],
                'pair_count': len(pairs), 'seller_retained_ack_count': len(seller_acks),
                'private_identity_material_included': False,
                'evidence_mode': 'SYNTHETIC_LOCAL_ONLY', 'files': manifest_files}
    write_json(target / 'manifest.json', manifest)
    return {'path': str(target), 'manifest_sha256': hashlib.sha256(
        (target / 'manifest.json').read_bytes()).hexdigest(),
        'files': len(manifest_files), 'seller_retained_ack_count': len(seller_acks)}


class P2PPairProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.task_sha = 'a' * 64
        self.accept_sha = 'b' * 64
        self.value_rubric = 'Score value from 0 to 1: task usefulness, correctness, and integration quality.'
        self.value_rubric_sha = hashlib.sha256(self.value_rubric.encode()).hexdigest()
        self.artifact_bytes = b'fixture artifact bytes\n'
        self.artifact_sha = hashlib.sha256(self.artifact_bytes).hexdigest()
        self.cost_contract_sha = 'd' * 64
        self.evaluator = Identity(self.root / 'evaluator-identity.json')
        evaluator_public = self.evaluator.public()
        self.buyer = Identity(self.root / 'buyer-identity.json')
        buyer_public = self.buyer.public()
        self.identity = {
            'product_id': 'prod-1',
            'evidence_mode': 'SYNTHETIC',
            'exchange_buyer_id': public_id(buyer_public),
            'exchange_buyer_public': buyer_public,
            'independent_evaluator_id': public_id(evaluator_public),
            'independent_evaluator_public': evaluator_public,
            'executor_profile': {'provider': 'codex', 'model': 'model-v1',
                                 'client_version': 'client-1', 'effort': 'medium'},
            'task_sha256_by_id': {'task-1': self.task_sha},
            'acceptance_contract_sha256_by_family': {'navigation': self.accept_sha},
            'value_rubric_sha256_by_family': {'navigation': self.value_rubric_sha},
            'cost_measurement_contract_sha256': self.cost_contract_sha,
        }
        self.pair = self._pair()

    def tearDown(self):
        self.temp.cleanup()

    def _arm(self, arm_name, tokens):
        receipt_id = ('direct' if arm_name == 'direct_executor' else 'p2p') + 'receipt1'
        receipt = {
            'id': receipt_id, 'provider': 'codex', 'requested_model': 'model-v1',
            'effort': 'medium', 'tokens': tokens, 'wall_seconds': 1,
            'product_id': 'prod-1', 'accounting_details': {
                'known': True, 'tokens': tokens, 'input_tokens': tokens - 20,
                'output_tokens': 20, 'cached_input_tokens_included_in_input': 0,
            },
        }
        write_json(self.root / 'transport' / (receipt_id + '.json'), receipt)
        receipt_path = 'acceptance/' + arm_name + '.json'
        acceptance_payload = {
            'pair_id': 'pair-1', 'task_sha256': self.task_sha,
            'acceptance_contract_sha256': self.accept_sha, 'arm': arm_name,
            'value_rubric_sha256': self.value_rubric_sha,
            'evaluator_id': self.identity['independent_evaluator_id'], 'measurement_complete': True,
            'passed': True, 'value_score': 0.8 if arm_name == 'direct_executor' else 0.85,
        }
        acceptance_hash = write_json(self.root / receipt_path, {
            'payload': acceptance_payload,
            'signature': self.evaluator.sign(acceptance_payload, 'p2p-pair-acceptance'),
        })
        return {
            'arm': arm_name, 'pair_id': 'pair-1', 'product_id': 'prod-1',
            'provider': 'codex', 'model': 'model-v1', 'client_version': 'client-1',
            'effort': 'medium', 'actual_providers': ['codex'],
            'task_sha256': self.task_sha, 'acceptance_contract_sha256': self.accept_sha,
            'native_receipts': [receipt], 'tokens': tokens, 'elapsed_seconds': 2,
            'acceptance_receipt_path': receipt_path,
            'acceptance_receipt_sha256': acceptance_hash,
        }

    def _pair(self):
        direct = self._arm('direct_executor', 100)
        p2p = self._arm('p2p_borrow', 40)
        exchange_root = self.root / 'exchange_snapshot'
        exchange = Exchange(exchange_root)
        seller = Identity(self.root / 'seller-identity.json')
        seller_public = seller.public()
        seller_id = 'seller-1'
        self.identity['seller_public_keys'] = {seller_id: seller_public}
        policy_data = exchange.load()
        policy_data.setdefault('peers', {})[seller_id] = {
            'blocked': False, 'post_quantum': seller_public,
        }
        exchange_atomic(exchange_root / 'policy.json', policy_data)
        artifact_path = self.root / 'artifacts' / 'feature.bin'
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(self.artifact_bytes)
        exchange.append_audit_row({'kind': 'EQUITY_GRANT', 'feature_id': 'feat-1',
                                   'peer_id': seller_id, 'artifact_ref': self.artifact_sha})
        exchange.append_audit_row({'kind': 'EQUITY_LISTING', 'listing_id': 'listing-1',
                                   'feature_id': 'feat-1', 'seller_id': seller_id,
                                   'ask_price_units': 12})
        exchange.append_audit_row({'kind': 'EQUITY_LISTING_FILLED', 'listing_id': 'listing-1',
                                   'feature_id': 'feat-1', 'seller_id': seller_id,
                                   'buyer_id': 'buyer-1', 'price_units': 12})
        exchange.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'protocol_fee',
                                   'listing_id': 'listing-1', 'amount_units': 1})
        attested = {'listing_id': 'listing-1', 'feature_id': 'feat-1',
                    'artifact_sha256': self.artifact_sha, 'seller_id': seller_id,
                    'buyer_id': 'buyer-1', 'price_units': 12}
        costs_receipt = {
            'schema': protocol.COST_SCHEMA,
            'pair_id': 'pair-1', 'task_sha256': self.task_sha,
            'feature_id': 'feat-1', 'artifact_sha256': self.artifact_sha,
            'listing_id': 'listing-1',
            'measurement_contract_sha256': self.cost_contract_sha,
            'protocol_fee_units': 1, 'delivery_fee_units': 0,
            'network_transfer_bytes': 1024, 'network_cost_usd': 0.01,
            'discovery_seconds': 1.5, 'fetch_seconds': 2.0,
            'integration_seconds': 30, 'validation_seconds': 10,
            'provider_cost_basis': 'API_EQUIVALENT',
            'provider_cost_usd_by_arm': {'direct_executor': 0.08, 'p2p_borrow': 0.02},
            'non_provider_cost_usd_by_arm': {'direct_executor': 0.01, 'p2p_borrow': 0.03},
            'non_provider_cost_complete_by_arm': {'direct_executor': True, 'p2p_borrow': True},
        }
        cost_receipt_path = 'costs/p2p-costs.json'
        cost_receipt_sha = write_json(self.root / cost_receipt_path, {
            'payload': costs_receipt,
            'signature': self.evaluator.sign(costs_receipt, 'p2p-pair-cost'),
        })
        seller_listing_payload = {'listing_id': 'listing-1', 'feature_id': 'feat-1',
                                  'artifact_sha256': self.artifact_sha,
                                  'seller_id': seller_id, 'price_units': 12}
        p2p.update({
            'listing_id': 'listing-1', 'feature_id': 'feat-1',
            'artifact_sha256': self.artifact_sha, 'exchange_buyer_id': 'buyer-1',
            'seller_attestation': {'payload': seller_listing_payload,
                                   'seller_key_id': public_id(seller_public),
                                   'signature': seller.sign(seller_listing_payload, 'p2p-benchmark-listing')},
            'artifact_path': 'artifacts/feature.bin',
            'p2p_cost_receipt_path': cost_receipt_path,
            'p2p_cost_receipt_sha256': cost_receipt_sha,
            'exchange_marker_path': 'exchange_snapshot/audit.jsonl',
        })
        return {
            'schema': protocol.SCHEMA,
            'task': {'pair_id': 'pair-1', 'task_id': 'task-1', 'task_sha256': self.task_sha,
                     'acceptance_contract_sha256': self.accept_sha,
                     'value_rubric_sha256': self.value_rubric_sha,
                     'family': 'navigation', 'repeat': 0},
            'arms': {'direct_executor': direct, 'p2p_borrow': p2p},
        }

    def test_valid_pair_reconciles_native_acceptance_and_signed_fill(self):
        result = protocol.verify_pair(self.pair, self.root, self.identity)
        self.assertEqual(result['status'], 'PAIR_VALID_RESOURCE_COMPARISON')
        self.assertEqual(result['native_tokens']['p2p_minus_direct'], -60)
        self.assertEqual(result['native_tokens']['breakdown_delta']['input_tokens'], -60)
        self.assertEqual(result['p2p_costs']['urace_units_paid'], 13)
        self.assertIsNone(result['total_cost_savings'])

    def test_open_asset_pair_requires_buyer_and_seller_quarantine_evidence(self):
        from urace import remote_assets
        buyer = Exchange(self.root / 'buyer-exchange')
        seller = Exchange(self.root / 'seller-exchange')
        for exchange in (buyer, seller):
            exchange.configure(enabled=True)
        buyer_id = buyer.identity()['peer_id']; seller_id = seller.identity()['peer_id']
        self.identity['exchange_buyer_id'] = buyer_id
        self.identity['exchange_buyer_public'] = buyer.identity()['post_quantum']
        buyer.peer(seller.identity()['certificate'], post_quantum=seller.identity()['post_quantum'])
        seller.peer(buyer.identity()['certificate'], post_quantum=buyer.identity()['post_quantum'])
        seller.feature('feat-open', [], offered=True)
        seller.feature_policy('feat-open', {'access': 'open', 'license_id': 'MIT'})
        seller.rule(buyer_id, 'feat-open', 'send', True)
        artifact = b'open benchmark asset bytes'
        artifact_sha = hashlib.sha256(artifact).hexdigest()
        from urace.peer_exchange import _store_artifact
        _store_artifact(seller.root, artifact_sha, artifact)
        seller.append_audit_row({'kind': 'EQUITY_GRANT', 'feature_id': 'feat-open',
                                 'peer_id': seller_id, 'visibility': 'public',
                                 'description': 'frozen task asset', 'tags': ['task'],
                                 'artifact_ref': artifact_sha, 'artifact_size_bytes': len(artifact),
                                 'content_type': 'application/octet-stream'})
        catalog = remote_assets.public_catalog(seller, buyer_id)
        asset = catalog['open_assets'][0]
        bundle = remote_assets._make_open_bundle(seller, buyer_id, asset['asset_id'])
        artifact_path = self.root / 'artifacts' / 'open.bin'
        artifact_path.parent.mkdir(parents=True, exist_ok=True); artifact_path.write_bytes(artifact)
        received = remote_assets.receive_open_bundle(buyer, seller_id, bundle)
        seller_ack = remote_assets.record_quarantine_receipt(seller, buyer_id, {
            'asset_id': asset['asset_id'], 'status': received['status'],
            'receipt': received['receipt']})
        remote_assets.accept_seller_ack(buyer, seller_id, asset['asset_id'], received, seller_ack)
        p2p = self.pair['arms']['p2p_borrow']
        p2p.update({'delivery_kind': 'open_asset', 'exchange_marker_path': 'buyer-exchange/audit.jsonl',
                    'bundle_id': received['bundle_id'], 'asset_id': asset['asset_id'],
                    'seller_peer_id': seller_id, 'exchange_buyer_id': buyer_id,
                    'feature_id': 'feat-open', 'artifact_sha256': artifact_sha,
                    'artifact_path': 'artifacts/open.bin',
                    'discovery_network_metrics': {'application_payload_bytes': 1024,
                                                  'elapsed_seconds': 1.0},
                    'fetch_network_metrics': {'application_payload_bytes': 1024,
                                              'elapsed_seconds': 2.0}})
        self.identity['seller_public_keys'] = {seller_id: seller.identity()['post_quantum']}
        costs = {'schema': protocol.COST_SCHEMA,
                 'pair_id': 'pair-1', 'task_sha256': self.task_sha,
                 'delivery_kind': 'open_asset', 'asset_id': asset['asset_id'],
                 'bundle_id': received['bundle_id'], 'feature_id': 'feat-open',
                 'artifact_sha256': artifact_sha,
                 'measurement_contract_sha256': self.cost_contract_sha,
                 'protocol_fee_units': 0, 'delivery_fee_units': 0,
                 'network_transfer_bytes': 2048, 'network_cost_usd': 0.0,
                 'discovery_seconds': 1.0, 'fetch_seconds': 2.0,
                 'integration_seconds': 30, 'validation_seconds': 10,
                 'provider_cost_basis': 'API_EQUIVALENT',
                 'provider_cost_usd_by_arm': {'direct_executor': 0.08, 'p2p_borrow': 0.02},
                 'non_provider_cost_usd_by_arm': {'direct_executor': 0.01, 'p2p_borrow': 0.03},
                 'non_provider_cost_complete_by_arm': {'direct_executor': True, 'p2p_borrow': True}}
        cost_path = self.root / 'costs' / 'open-costs.json'
        cost_hash = write_json(cost_path, {'payload': costs,
                                           'signature': self.evaluator.sign(costs, 'p2p-pair-cost')})
        p2p['p2p_cost_receipt_path'] = str(cost_path.relative_to(self.root))
        p2p['p2p_cost_receipt_sha256'] = cost_hash
        result = protocol.verify_pair(self.pair, self.root, self.identity)
        self.assertEqual(result['status'], 'PAIR_VALID_RESOURCE_COMPARISON', result.get('reason'))
        self.assertEqual(result['p2p_costs']['urace_units_paid'], 0)
        self.assertIn('BUYER_QUARANTINE_RECEIPT_VERIFIED', result['remote_fill_status'])

    def test_receipt_mismatch_invalidates_pair(self):
        self.pair['arms']['direct_executor']['tokens'] = 99
        result = protocol.verify_pair(self.pair, self.root, self.identity)
        self.assertEqual(result['status'], 'PAIR_INELIGIBLE')

    def test_predeclared_pair_order_is_enforced(self):
        arm_order = ['direct_executor', 'p2p_borrow']
        self.pair['arm_order'] = arm_order
        self.identity['planned_pairs'] = {
            'pair-1': {'task': self.pair['task'], 'arm_order': arm_order}}
        self.assertEqual(protocol.verify_pair(self.pair, self.root, self.identity)['status'],
                         'PAIR_VALID_RESOURCE_COMPARISON')
        self.pair['arm_order'] = list(reversed(arm_order))
        self.assertEqual(protocol.verify_pair(self.pair, self.root, self.identity)['status'],
                         'PAIR_INELIGIBLE')

    def test_nonidentical_executor_profiles_do_not_pair(self):
        self.pair['arms']['p2p_borrow']['effort'] = 'high'
        result = protocol.verify_pair(self.pair, self.root, self.identity)
        self.assertEqual(result['status'], 'PAIR_INELIGIBLE')

    def test_failed_acceptance_is_measured_as_an_outcome_not_dropped(self):
        arm = self.pair['arms']['p2p_borrow']
        path = self.root / arm['acceptance_receipt_path']
        envelope = json.loads(path.read_text())
        envelope['payload']['passed'] = False
        envelope['signature'] = self.evaluator.sign(envelope['payload'], 'p2p-pair-acceptance')
        arm['acceptance_receipt_sha256'] = write_json(path, envelope)
        result = protocol.verify_pair(self.pair, self.root, self.identity)
        self.assertEqual(result['status'], 'PAIR_VALID_RESOURCE_COMPARISON')
        self.assertFalse(result['acceptance']['p2p_borrow'])
        self.assertEqual(result['native_tokens']['p2p_minus_direct'], -60)

    def test_value_score_is_signed_and_reported_for_both_arms(self):
        result = protocol.verify_pair(self.pair, self.root, self.identity)
        self.assertEqual(result['status'], 'PAIR_VALID_RESOURCE_COMPARISON')
        self.assertEqual(result['value_produced']['direct_executor'], 0.8)
        self.assertEqual(result['value_produced']['p2p_borrow'], 0.85)
        self.assertAlmostEqual(result['value_produced']['p2p_minus_direct'], 0.05)

    def test_value_score_outside_frozen_scale_invalidates_pair(self):
        arm = self.pair['arms']['p2p_borrow']
        path = self.root / arm['acceptance_receipt_path']
        envelope = json.loads(path.read_text())
        envelope['payload']['value_score'] = 1.01
        envelope['signature'] = self.evaluator.sign(envelope['payload'], 'p2p-pair-acceptance')
        arm['acceptance_receipt_sha256'] = write_json(path, envelope)
        self.assertEqual(protocol.verify_pair(self.pair, self.root, self.identity)['status'],
                         'PAIR_INELIGIBLE')

    def test_signed_no_call_p2p_arm_is_zero_usage_not_missing_usage(self):
        arm = self.pair['arms']['p2p_borrow']
        arm['native_receipts'] = []
        payload = {'pair_id': 'pair-1', 'task_sha256': self.task_sha,
                   'arm': 'p2p_borrow', 'evaluator_id': self.identity['independent_evaluator_id'],
                   'measurement_complete': True, 'provider_call_count': 0,
                   'provider_tokens': 0, 'provider_usage_known': True}
        rel = 'no-call/p2p.json'
        digest = write_json(self.root / rel, {
            'payload': payload,
            'signature': self.evaluator.sign(payload, 'p2p-pair-no-call'),
        })
        arm['no_call_receipt_path'] = rel
        arm['no_call_receipt_sha256'] = digest
        result = protocol.verify_pair(self.pair, self.root, self.identity)
        self.assertEqual(result['status'], 'PAIR_VALID_RESOURCE_COMPARISON')
        self.assertEqual(result['native_tokens']['p2p_borrow'], 0)
        self.assertEqual(result['native_tokens']['p2p_minus_direct'], -100)

    def test_pair_paths_cannot_escape_or_traverse_symlinks(self):
        self.pair['arms']['p2p_borrow']['exchange_marker_path'] = '../outside/audit.jsonl'
        result = protocol.verify_pair(self.pair, self.root, self.identity)
        self.assertEqual(result['status'], 'PAIR_INELIGIBLE')

    def test_summary_requires_30_valid_unique_pairs_and_family_coverage(self):
        rows = [{'status': 'PAIR_VALID_RESOURCE_COMPARISON', 'pair_id': 'pair-' + str(i),
                 'family': 'navigation',
                 'native_tokens': {'direct_executor': 2, 'p2p_borrow': 1,
                                   'p2p_minus_direct': -1}} for i in range(30)]
        result = protocol.summarize_pairs(rows, cohort_sha256='d' * 64)
        self.assertEqual(result['status'], 'INSUFFICIENT_OR_INVALID')
        self.assertFalse(result['qualified_total_cost_savings'])

    def test_30_unique_pairs_with_family_coverage_are_review_ready_only(self):
        rows = [{'status': 'PAIR_VALID_RESOURCE_COMPARISON', 'pair_id': 'pair-' + str(i),
                 'family': protocol.FAMILIES[i % len(protocol.FAMILIES)],
                 'acceptance': {'direct_executor': True, 'p2p_borrow': True},
                 'value_produced': {'direct_executor': 0.7, 'p2p_borrow': 0.7,
                                    'p2p_minus_direct': 0.0},
                 'cost_comparison': {'provider_cost_basis': 'API_EQUIVALENT',
                                     'costs_complete_under_frozen_measurement_contract': True,
                                     'measured_partial_usd_by_arm': {
                                         'direct_executor': 0.10, 'p2p_borrow': 0.08}},
                 'native_tokens': {'direct_executor': 2, 'p2p_borrow': 1,
                                   'p2p_minus_direct': -1}} for i in range(30)]
        result = protocol.summarize_pairs(rows, cohort_sha256='d' * 64)
        self.assertEqual(result['status'], 'READY_FOR_INDEPENDENT_REVIEW')
        self.assertFalse(result['qualified_total_cost_savings'])

    def test_plan_freezes_balanced_order_and_pair_coverage(self):
        self.identity.update({
            'executor_profile': {'provider': 'codex', 'model': 'model-v1',
                                 'client_version': 'client-1', 'effort': 'medium'},
            'adapter_sha256': {'arm': '1' * 64, 'evaluator': '2' * 64, 'cost': '3' * 64},
            'runner_sha256': '4' * 64, 'exchange_buyer_id': 'buyer-1',
            'allowed_seller_peer_ids': ['seller-1'],
            'minimum_asset_match_score': 0.25,
            'peer_search_limit': 3,
        })
        tasks = []
        rubrics = {}
        for family in protocol.FAMILIES:
            for i in range(6):
                task_specification = f'Frozen task: {family}-{i}'
                acceptance_contract = f'Frozen independent acceptance: {family}'
                value_rubric = f'Frozen value rubric for {family}: score task utility from zero to one.'
                rubric_hash = hashlib.sha256(value_rubric.encode()).hexdigest()
                rubrics[family] = rubric_hash
                tasks.append({'task_id': f'{family}-{i}', 'family': family,
                              'task_specification': task_specification,
                              'acceptance_contract': acceptance_contract,
                              'value_rubric': value_rubric,
                              'value_rubric_sha256': rubric_hash,
                              'task_sha256': hashlib.sha256(task_specification.encode()).hexdigest(),
                              'acceptance_contract_sha256': hashlib.sha256(acceptance_contract.encode()).hexdigest()})
        self.identity['value_rubric_sha256_by_family'] = rubrics
        plan = study_plan.freeze_plan(tasks, self.identity, seed=42)
        self.assertTrue(study_plan.verify_plan(plan))
        self.assertEqual(len(plan['pairs']), 30)
        for family in protocol.FAMILIES:
            orders = [p['arm_order'] for p in plan['pairs'] if p['task']['family'] == family]
            self.assertEqual(orders.count(['direct_executor', 'p2p_borrow']), 3)
            self.assertEqual(orders.count(['p2p_borrow', 'direct_executor']), 3)

    def test_plan_rejects_task_or_acceptance_content_drift(self):
        self.identity.update({
            'executor_profile': {'provider': 'codex', 'model': 'model-v1',
                                 'client_version': 'client-1', 'effort': 'medium'},
            'adapter_sha256': {'arm': '1' * 64, 'evaluator': '2' * 64, 'cost': '3' * 64},
            'runner_sha256': '4' * 64, 'exchange_buyer_id': 'buyer-1',
            'allowed_seller_peer_ids': ['seller-1'],
            'minimum_asset_match_score': 0.25,
            'peer_search_limit': 3,
        })
        tasks = []
        rubrics = {}
        for family in protocol.FAMILIES:
            for i in range(6):
                task_specification = f'Frozen task: {family}-{i}'
                acceptance_contract = f'Frozen independent acceptance: {family}'
                value_rubric = f'Frozen value rubric for {family}: score task utility from zero to one.'
                rubric_hash = hashlib.sha256(value_rubric.encode()).hexdigest()
                rubrics[family] = rubric_hash
                tasks.append({'task_id': f'{family}-{i}', 'family': family,
                              'task_specification': task_specification,
                              'acceptance_contract': acceptance_contract,
                              'value_rubric': value_rubric,
                              'value_rubric_sha256': rubric_hash,
                              'task_sha256': hashlib.sha256(task_specification.encode()).hexdigest(),
                              'acceptance_contract_sha256': hashlib.sha256(acceptance_contract.encode()).hexdigest()})
        self.identity['value_rubric_sha256_by_family'] = rubrics
        plan = study_plan.freeze_plan(tasks, self.identity, seed=9)
        self.assertTrue(study_plan.verify_plan(plan))
        plan['tasks'][0]['task_specification'] += ' changed'
        self.assertFalse(study_plan.verify_plan(plan))
        plan = study_plan.freeze_plan(tasks, self.identity, seed=10)
        plan['tasks'][0]['value_rubric'] += ' changed'
        self.assertFalse(study_plan.verify_plan(plan))

    def test_summary_reports_acceptance_separately_from_token_delta(self):
        rows = [{'status': 'PAIR_VALID_RESOURCE_COMPARISON', 'pair_id': f'p-{i}',
                 'family': protocol.FAMILIES[i % len(protocol.FAMILIES)],
                 'acceptance': {'direct_executor': True, 'p2p_borrow': i != 0},
                 'value_produced': {'direct_executor': 0.8, 'p2p_borrow': 0.8,
                                    'p2p_minus_direct': 0.0},
                 'native_tokens': {'direct_executor': 10, 'p2p_borrow': 5,
                                   'p2p_minus_direct': -5}} for i in range(30)]
        report = protocol.summarize_pairs(rows, cohort_sha256='d' * 64)
        self.assertEqual(report['acceptance_rates']['direct_executor'], 1.0)
        self.assertAlmostEqual(report['acceptance_rates']['p2p_borrow'], 29 / 30)
        self.assertFalse(report['native_token_reduction_candidate'])

    def test_30_pair_synthetic_cohort_compares_value_tokens_and_cost_without_savings_claim(self):
        import threading
        import shutil
        from urace import peer_exchange as pe, remote_assets
        seller = Exchange(self.root / 'synthetic-seller')
        buyer = Exchange(self.root / 'synthetic-buyer-template')
        seller.configure(enabled=True, network=True)
        buyer.configure(enabled=True, network=True)
        for exchange in (seller, buyer):
            exchange.configure(max_transfers_per_day=100,
                               max_transfers_per_peer_per_day=100,
                               max_bytes_per_day=10_000_000,
                               max_rpc_per_day=500,
                               max_rpc_per_peer_per_day=500)
        seller_id = seller.identity()['peer_id']
        buyer_id = buyer.identity()['peer_id']
        seller_public = seller.identity()['post_quantum']
        buyer_public = buyer.identity()['post_quantum']
        seller.peer(buyer.identity()['certificate'], post_quantum=buyer_public)
        self.identity.update({'exchange_buyer_id': buyer_id,
                              'exchange_buyer_public': buyer_public,
                              'seller_public_keys': {seller_id: seller_public}})
        task_specs = {}
        acceptance_by_family = {
            family: f'Synthetic acceptance contract for {family}: artifact is safe and meets task requirements.'
            for family in protocol.FAMILIES}
        rubric_by_family = {
            family: f'Synthetic value rubric for {family}: score usefulness and correctness from 0 to 1.'
            for family in protocol.FAMILIES}
        from p2p_local_feature_assets import family_assets
        source_assets = family_assets(Path(__file__).resolve().parent.parent)
        tasks = []
        for index in range(30):
            family = protocol.FAMILIES[index // 6]
            source_asset = source_assets[family][index % 6]
            feature_id = source_asset['feature_id']
            artifact = source_asset['artifact_bytes']
            digest = hashlib.sha256(artifact).hexdigest()
            task_id = f'synthetic-{family}-{index + 1:02d}'
            task_text = (f'Synthetic URACE scenario {family}: assess reuse of the existing '
                         f'feature {feature_id}, {source_asset["name"]}.')
            task_hash = hashlib.sha256(task_text.encode()).hexdigest()
            acceptance_contract = acceptance_by_family[family]
            acceptance_hash = hashlib.sha256(acceptance_contract.encode()).hexdigest()
            value_rubric = rubric_by_family[family]
            rubric_hash = hashlib.sha256(value_rubric.encode()).hexdigest()
            tasks.append({'task_id': task_id, 'family': family,
                          'task_specification': task_text, 'task_sha256': task_hash,
                          'acceptance_contract': acceptance_contract,
                          'acceptance_contract_sha256': acceptance_hash,
                          'value_rubric': value_rubric,
                          'value_rubric_sha256': rubric_hash,
                          'source_asset': {'feature_id': feature_id,
                                           'artifact_sha256': digest,
                                           'source_manifest_sha256': source_asset['source_manifest_sha256'],
                                           'source_paths': source_asset['source_paths']}})
            seller.feature(feature_id, [], offered=True)
            seller.feature_policy(feature_id, {'access': 'open', 'license_id': 'Apache-2.0'})
            pe._store_artifact(seller.root, digest, artifact)
            seller.rule(buyer_id, feature_id, 'send', True)
            seller.append_audit_row({'kind': 'EQUITY_GRANT', 'feature_id': feature_id,
                                     'peer_id': seller_id, 'visibility': 'public',
                                     'description': source_asset['description'],
                                     'tags': source_asset['tags'],
                                     'artifact_ref': digest, 'artifact_size_bytes': len(artifact),
                                     'content_type': 'application/zip'})
            task_specs[index] = (family, feature_id, digest, artifact, task_id, source_asset,
                                 task_text, task_hash, acceptance_hash, rubric_hash)

        self.identity.update({
            'executor_profile': {'provider': 'codex', 'model': 'synthetic-model',
                                 'client_version': 'synthetic-client', 'effort': 'medium'},
            'adapter_sha256': {'arm': '1' * 64, 'evaluator': '2' * 64, 'cost': '3' * 64},
            'runner_sha256': '4' * 64,
            'allowed_seller_peer_ids': [seller_id],
            'minimum_asset_match_score': 1.0,
            'peer_search_limit': 1,
        })
        frozen_plan = study_plan.freeze_plan(tasks, self.identity, seed=20261108)
        self.assertTrue(study_plan.verify_plan(frozen_plan))
        self.identity = frozen_plan['identity']
        planned_by_task = {pair['task']['task_id']: pair for pair in frozen_plan['pairs']}
        results = []
        pair_rows = []
        pair_ids = [pair['task']['pair_id'] for pair in frozen_plan['pairs']]
        with pe.server(seller, host='127.0.0.1', port=0) as local_server:
            thread = threading.Thread(target=local_server.serve_forever, daemon=True)
            thread.start()
            try:
                buyer.peer(seller.identity()['certificate'],
                           f'https://127.0.0.1:{local_server.server_port}',
                           post_quantum=seller_public)
                for index in range(30):
                    if index:
                        buyer_root = self.root / f'synthetic-buyer-{index:02d}'
                        buyer_root.mkdir()
                        for identity_file in ('identity-key.pem', 'identity-cert.pem',
                                              'hybrid-identity.json'):
                            shutil.copy2(buyer.root / identity_file, buyer_root / identity_file)
                        buyer = Exchange(buyer_root)
                        buyer.configure(enabled=True, network=True,
                                        max_transfers_per_day=100,
                                        max_transfers_per_peer_per_day=100,
                                        max_bytes_per_day=10_000_000,
                                        max_rpc_per_day=500,
                                        max_rpc_per_peer_per_day=500)
                        buyer.peer(seller.identity()['certificate'],
                                   f'https://127.0.0.1:{local_server.server_port}',
                                   post_quantum=seller_public)
                    (family, feature_id, artifact_digest, artifact, task_id, source_asset,
                     task_text, task_hash, acceptance_hash, rubric_hash) = task_specs[index]
                    planned = planned_by_task[task_id]
                    task_ref = planned['task']
                    pair_id = task_ref['pair_id']
                    discovered = remote_assets.discover(buyer, query=feature_id, peer_limit=1)
                    selected = next(item for item in discovered['open_assets']
                                    if item['feature_id'] == feature_id)
                    fetched = remote_assets.fetch_open_asset(buyer, seller_id, selected['asset_id'])
                    self.assertEqual(fetched['seller_ack']['status'],
                                     'BUYER_QUARANTINE_RECEIPT_VERIFIED')
                    from p2p_study_runner import _snapshot_exchange_evidence
                    exchange_marker = _snapshot_exchange_evidence(
                        buyer, self.root, pair_id, fetched['bundle_id'])
                    evidence_dir = self.root / 'exchange-evidence' / pair_id
                    self.assertFalse((evidence_dir / 'identity-key.pem').exists())
                    self.assertFalse((evidence_dir / 'hybrid-identity.json').exists())
                    artifact_path = f'artifacts/{pair_id}.zip'
                    (self.root / artifact_path).parent.mkdir(parents=True, exist_ok=True)
                    (self.root / artifact_path).write_bytes(artifact)
                    pair = copy.deepcopy(self.pair)
                    pair['task'] = task_ref
                    pair['arm_order'] = planned['arm_order']
                    pair['cohort_sha256'] = frozen_plan['cohort_sha256']
                    p2p = pair['arms']['p2p_borrow']
                    p2p.update({'delivery_kind': 'open_asset',
                                'exchange_marker_path': exchange_marker,
                                'bundle_id': fetched['bundle_id'], 'asset_id': selected['asset_id'],
                                'seller_peer_id': seller_id, 'exchange_buyer_id': buyer_id,
                                'feature_id': feature_id, 'artifact_sha256': artifact_digest,
                                'artifact_path': artifact_path,
                                'discovery_network_metrics': discovered['network_metrics'],
                                'fetch_network_metrics': fetched['network_metrics']})
                    for arm_name, arm in pair['arms'].items():
                        arm.update({'pair_id': pair_id, 'task_sha256': task_hash,
                                    'acceptance_contract_sha256': task_ref['acceptance_contract_sha256'],
                                    'model': 'synthetic-model',
                                    'client_version': 'synthetic-client'})
                        for receipt_index, old in enumerate(arm['native_receipts']):
                            receipt = copy.deepcopy(old)
                            receipt['id'] = f'sim{index:02d}{arm_name[:1]}{receipt_index}'
                            receipt['tokens'] = 100 if arm_name == 'direct_executor' else 40
                            receipt['requested_model'] = 'synthetic-model'
                            details = receipt['accounting_details']
                            details['tokens'] = receipt['tokens']
                            details['input_tokens'] = receipt['tokens'] - 20
                            details['output_tokens'] = 20
                            write_json(self.root / 'transport' / (receipt['id'] + '.json'), receipt)
                            arm['native_receipts'][receipt_index] = receipt
                        acceptance_path = f'acceptance/{pair_id}-{arm_name}.json'
                        payload = {'pair_id': pair_id, 'task_sha256': task_hash,
                                   'acceptance_contract_sha256': task_ref['acceptance_contract_sha256'],
                                   'value_rubric_sha256': task_ref['value_rubric_sha256'],
                                   'arm': arm_name,
                                   'evaluator_id': self.identity['independent_evaluator_id'],
                                   'measurement_complete': True, 'passed': True,
                                   'value_score': 0.78 if arm_name == 'direct_executor' else 0.82}
                        envelope = {'payload': payload,
                                    'signature': self.evaluator.sign(payload, 'p2p-pair-acceptance')}
                        arm['acceptance_receipt_path'] = acceptance_path
                        arm['acceptance_receipt_sha256'] = write_json(self.root / acceptance_path, envelope)
                    costs = {'schema': protocol.COST_SCHEMA,
                             'pair_id': pair_id, 'task_sha256': task_hash,
                             'delivery_kind': 'open_asset', 'asset_id': selected['asset_id'],
                             'bundle_id': fetched['bundle_id'], 'feature_id': feature_id,
                             'artifact_sha256': artifact_digest,
                             'measurement_contract_sha256': self.cost_contract_sha,
                             'protocol_fee_units': 0, 'delivery_fee_units': 0,
                             'network_transfer_bytes': (discovered['network_metrics']['application_payload_bytes']
                                                       + fetched['network_metrics']['application_payload_bytes']),
                             'network_cost_usd': 0.0001,
                             'discovery_seconds': discovered['network_metrics']['elapsed_seconds'],
                             'fetch_seconds': fetched['network_metrics']['elapsed_seconds'],
                             'integration_seconds': 30, 'validation_seconds': 10,
                             'provider_cost_basis': 'API_EQUIVALENT',
                             'provider_cost_usd_by_arm': {'direct_executor': 0.08,
                                                          'p2p_borrow': 0.02},
                             'non_provider_cost_usd_by_arm': {'direct_executor': 0.01,
                                                             'p2p_borrow': 0.03},
                             'non_provider_cost_complete_by_arm': {'direct_executor': True,
                                                                  'p2p_borrow': True}}
                    cost_envelope = {'payload': costs,
                                     'signature': self.evaluator.sign(costs, 'p2p-pair-cost')}
                    cost_path = f'costs/{pair_id}.json'
                    p2p['p2p_cost_receipt_path'] = cost_path
                    p2p['p2p_cost_receipt_sha256'] = write_json(self.root / cost_path, cost_envelope)
                    results.append(protocol.verify_pair(pair, self.root, self.identity))
                    pair_rows.append(pair)
            finally:
                local_server.shutdown()
                thread.join(timeout=5)
        report = protocol.summarize_pairs(
            results, cohort_sha256=frozen_plan['cohort_sha256'],
            expected_pair_ids=pair_ids,
            evidence_mode=frozen_plan['identity']['evidence_mode'],
            claim_policy=frozen_plan['identity']['economic_claim_policy'],
            workload_provenance=frozen_plan['identity'].get('workload_provenance'))
        self.assertEqual(report['status'], 'READY_FOR_INDEPENDENT_REVIEW',
                         json.dumps({'summary': report,
                                     'first_invalid': [row for row in results
                                                       if row.get('status') != 'PAIR_VALID_RESOURCE_COMPARISON'][:2]},
                                    sort_keys=True))
        self.assertEqual(report['valid_pairs'], 30)
        self.assertAlmostEqual(report['mean_value_score_by_arm']['p2p_minus_direct'], 0.04)
        self.assertEqual(report['valid_pair_native_tokens']['p2p_to_direct_ratio'], 0.4)
        self.assertAlmostEqual(report['paired_cost_usd_totals']['direct_executor'], 2.7)
        self.assertAlmostEqual(report['paired_cost_usd_totals']['p2p_borrow'], 1.5)
        self.assertFalse(report['qualified_total_cost_savings'])
        self.assertEqual(report['cost_claim_status'], 'SYNTHETIC_SCENARIO_ONLY')
        self.assertFalse(report['economic_claim_review_eligible'])
        self.assertEqual(report['economic_claim_policy'], protocol.ECONOMIC_CLAIM_POLICY)
        report['evidence_mode'] = 'SYNTHETIC_LOCAL_ONLY'
        report['status'] = 'SYNTHETIC_PIPELINE_VALIDATION_ONLY'
        report['empirical_savings_claim'] = False
        report['native_token_reduction_candidate'] = False
        report['end_to_end_cost_savings_candidate'] = False
        report['synthetic_inputs'] = {
            'product_tasks': 30,
            'assets': 30,
            'asset_basis': 'actual local implementations bound by initial-ledger tags and bundled with per-file SHA-256 manifests',
            'asset_license': 'Apache-2.0 as declared by the repository LICENSE',
            'asset_materialization_is_not_qualification': True,
            'representative_of_real_workloads': False,
            'task_source': 'synthetic scenarios grounded in actual initial-ledger URACE feature descriptions and source modules; outcomes remain synthetic',
            'provider_calls': 0,
            'provider_tokens': 'synthetically generated native-receipt fixtures',
            'value_scores': 'deterministic synthetic evaluator scores',
            'usd_costs': 'synthetic cost fixtures; network transfer bytes/time measured locally, but USD costs are not provider bills or measured economic costs',
            'network': 'localhost mutual-TLS P2P catalog, fetch, quarantine, and signed seller acknowledgement',
        }
        evidence_output = getattr(self, 'evidence_output', None)
        if evidence_output:
            report['proof_artifact'] = _publish_synthetic_evidence(
                self.root, evidence_output, frozen_plan, pair_rows, report, seller)
        self.synthetic_report = report

    def test_summary_requires_every_predeclared_pair_including_failures(self):
        rows = [{'status': 'PAIR_VALID_RESOURCE_COMPARISON', 'pair_id': f'p-{i}',
                 'family': protocol.FAMILIES[i % len(protocol.FAMILIES)],
                 'native_tokens': {'direct_executor': 2, 'p2p_borrow': 1,
                                   'p2p_minus_direct': -1}} for i in range(30)]
        expected = [f'p-{i}' for i in range(30)] + ['missing']
        result = protocol.summarize_pairs(rows, cohort_sha256='d' * 64,
                                          expected_pair_ids=expected)
        self.assertEqual(result['status'], 'INSUFFICIENT_OR_INVALID')
        self.assertFalse(result['planned_pair_coverage_complete'])


if __name__ == '__main__':
    unittest.main()
