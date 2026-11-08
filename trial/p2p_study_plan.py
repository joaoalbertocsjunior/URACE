"""Freeze a counterbalanced P2P-first versus direct-executor cohort.

The planner embeds and hash-checks the exact task and acceptance text. It does
not run model calls, select P2P assets, or create a cost claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import copy
from pathlib import Path

from p2p_pair_protocol import (ARMS, ECONOMIC_CLAIM_POLICY, FAMILIES,
                               MIN_PAIRS, MIN_PER_FAMILY, SCHEMA)


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def workload_attestation_payload(product_id: str, provenance: dict, tasks: list[dict]) -> dict:
    """Payload a product workload custodian signs before the cohort is frozen."""
    return {
        'schema': 'urace-p2p-real-workload-attestation-v1',
        'product_id': product_id,
        'kind': 'real_product_workloads',
        'source_sha256': provenance['source_sha256'],
        'selected_task_manifest_sha256': canonical_sha256(tasks),
        'description': provenance['description'],
    }


def _validate_live_workload_identity(identity: dict, tasks: list[dict]) -> None:
    provenance = identity.get('workload_provenance')
    reviewers = identity.get('claim_reviewer_public_keys')
    seller_ids = identity.get('allowed_seller_peer_ids')
    if (not isinstance(provenance, dict)
            or provenance.get('kind') != 'real_product_workloads'
            or not isinstance(provenance.get('source_sha256'), str)
            or len(provenance['source_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in provenance['source_sha256'])
            or not isinstance(provenance.get('description'), str)
            or not provenance['description'].strip()
            or not isinstance(reviewers, dict) or len(reviewers) != 2
            or not isinstance(seller_ids, list)):
        raise ValueError('LIVE cohorts require source provenance and two independent claim reviewers')
    from urace.ledger_crypto import public_id, validate_public, verify
    attestor_id = provenance.get('attestor_id')
    attestor_public = provenance.get('attestor_public')
    if not isinstance(attestor_public, dict):
        raise ValueError('LIVE workload provenance must pin a source-custodian public key')
    validate_public(attestor_public)
    if public_id(attestor_public) != attestor_id:
        raise ValueError('Workload custodian ID does not match its pinned key')
    if attestor_id in {identity.get('independent_evaluator_id'), identity.get('exchange_buyer_id'), *seller_ids, *reviewers}:
        raise ValueError('Workload custodian must be distinct from evaluator, buyer, sellers and claim reviewers')
    payload = workload_attestation_payload(identity.get('product_id'), provenance, tasks)
    if provenance.get('selected_task_manifest_sha256') != payload['selected_task_manifest_sha256']:
        raise ValueError('Workload attestation does not bind the selected frozen task manifest')
    try:
        verify(attestor_public, payload, provenance.get('attestation_signature'),
               'p2p-workload-source-attestation')
    except Exception as error:
        # Cryptographic libraries use InvalidSignature exceptions that are
        # not ValueError; normalize malformed attestations to plan rejection.
        raise ValueError('Workload source-custodian signature is invalid') from error
    for reviewer_id, public in reviewers.items():
        if not isinstance(reviewer_id, str) or not isinstance(public, dict):
            raise ValueError('Claim reviewer identities must be pinned public keys')
        validate_public(public)
        if public_id(public) != reviewer_id:
            raise ValueError('Claim reviewer identity does not match its pinned public key')
    if set(reviewers) & {identity.get('independent_evaluator_id'), identity.get('exchange_buyer_id'), *seller_ids}:
        raise ValueError('Claim reviewers must be distinct from evaluator, buyer, and sellers')


def freeze_plan(tasks: list[dict], identity: dict, *, seed: int) -> dict:
    """Create exactly 30 predeclared pairs with balanced order per family."""
    # Do not retain caller-owned containers in a hash-frozen cohort plan.
    tasks = copy.deepcopy(tasks)
    identity = copy.deepcopy(identity)
    evidence_mode = identity.get('evidence_mode', 'UNSPECIFIED')
    if evidence_mode not in ('LIVE', 'SYNTHETIC', 'UNSPECIFIED'):
        raise ValueError('evidence_mode must be LIVE, SYNTHETIC, or UNSPECIFIED')
    supplied_policy = identity.get('economic_claim_policy', ECONOMIC_CLAIM_POLICY)
    if supplied_policy != ECONOMIC_CLAIM_POLICY:
        raise ValueError('economic claim policy must match the preregistered protocol policy')
    identity['evidence_mode'] = evidence_mode
    identity['economic_claim_policy'] = copy.deepcopy(ECONOMIC_CLAIM_POLICY)
    if type(seed) is not int or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    if not isinstance(identity, dict) or not identity.get('product_id'):
        raise ValueError('identity must pin a product_id')
    if not isinstance(identity.get('independent_evaluator_id'), str) or not identity.get('independent_evaluator_public'):
        raise ValueError('identity must pin an independent evaluator and public key')
    if not isinstance(identity.get('cost_measurement_contract_sha256'), str):
        raise ValueError('identity must pin the cost measurement contract hash')
    profile = identity.get('executor_profile')
    if (not isinstance(profile, dict)
            or not all(isinstance(profile.get(key), str) and profile[key]
                       for key in ('provider', 'model', 'client_version', 'effort'))
            or profile.get('provider') not in ('codex', 'claude')
            or profile.get('effort') not in ('low', 'medium', 'high')):
        raise ValueError('identity must pin one provider/model/client-version/native-effort profile')
    adapters = identity.get('adapter_sha256')
    if (not isinstance(adapters, dict) or set(adapters) != {'arm', 'evaluator', 'cost'}
            or any(not isinstance(value, str) or len(value) != 64
                   or any(c not in '0123456789abcdef' for c in value)
                   for value in adapters.values())):
        raise ValueError('identity must pin SHA-256 for arm, independent evaluator, and cost adapters')
    for field in ('runner_sha256', 'exchange_buyer_id'):
        if not isinstance(identity.get(field), str) or not identity[field]:
            raise ValueError(f'identity must pin {field}')
    if (len(identity['runner_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in identity['runner_sha256'])):
        raise ValueError('runner_sha256 must be lowercase SHA-256 hex')
    buyer_public = identity.get('exchange_buyer_public')
    if not isinstance(buyer_public, dict):
        raise ValueError('identity must pin the buyer hybrid public key')
    from urace.ledger_crypto import validate_public
    validate_public(buyer_public)
    sellers = identity.get('allowed_seller_peer_ids')
    seller_keys = identity.get('seller_public_keys')
    if (not isinstance(sellers, list) or not sellers
            or any(not isinstance(seller, str) or not seller for seller in sellers)
            or len(sellers) != len(set(sellers)) or not isinstance(seller_keys, dict)
            or set(seller_keys) != set(sellers)):
        raise ValueError('identity must pin each allowed seller and its peer key')
    for seller_key in seller_keys.values():
        validate_public(seller_key)
    if (type(identity.get('minimum_asset_match_score', 0.0)) not in (int, float)
            or not 0.0 <= identity.get('minimum_asset_match_score', 0.0) <= 1.0):
        raise ValueError('minimum_asset_match_score must be between 0 and 1')
    if type(identity.get('peer_search_limit')) is not int or not 1 <= identity['peer_search_limit'] <= 10:
        raise ValueError('identity must pin peer_search_limit between 1 and 10')
    cost_hash = identity['cost_measurement_contract_sha256']
    if len(cost_hash) != 64 or any(c not in '0123456789abcdef' for c in cost_hash):
        raise ValueError('cost measurement contract hash must be lowercase SHA-256 hex')
    from urace.ledger_crypto import public_id
    if public_id(identity['independent_evaluator_public']) != identity['independent_evaluator_id']:
        raise ValueError('independent evaluator ID does not match its pinned public key')
    if not isinstance(tasks, list) or len(tasks) != MIN_PAIRS:
        raise ValueError(f'exactly {MIN_PAIRS} task manifests are required')
    if evidence_mode == 'LIVE':
        _validate_live_workload_identity(identity, tasks)
    ids = [task.get('task_id') for task in tasks if isinstance(task, dict)]
    if (len(ids) != len(tasks) or len(set(ids)) != len(ids)
            or any(not isinstance(i, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', i) for i in ids)):
        raise ValueError('task manifests need unique filesystem-safe task_id values')
    counts = {family: sum(task.get('family') == family for task in tasks) for family in FAMILIES}
    if any(counts[family] < MIN_PER_FAMILY for family in FAMILIES):
        raise ValueError('tasks need at least six members in every frozen family')
    task_by_id = {}
    contracts_by_family = {}
    value_rubrics_by_family = {}
    for task in tasks:
        if task.get('family') not in FAMILIES:
            raise ValueError('unknown task family')
        for field in ('task_sha256', 'acceptance_contract_sha256', 'value_rubric_sha256'):
            value = task.get(field)
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError(f'{field} must be lowercase SHA-256 hex')
        for content_field, hash_field in (('task_specification', 'task_sha256'),
                                          ('acceptance_contract', 'acceptance_contract_sha256'),
                                          ('value_rubric', 'value_rubric_sha256')):
            content = task.get(content_field)
            if not isinstance(content, str) or not content.strip() or len(content.encode()) > 131072:
                raise ValueError(f'{content_field} must be nonempty UTF-8 text no larger than 128 KiB')
            if hashlib.sha256(content.encode()).hexdigest() != task[hash_field]:
                raise ValueError(f'{hash_field} does not match frozen {content_field}')
        source_asset = task.get('source_asset')
        if source_asset is not None:
            if (not isinstance(source_asset, dict)
                    or not isinstance(source_asset.get('feature_id'), str)
                    or not isinstance(source_asset.get('artifact_sha256'), str)
                    or not isinstance(source_asset.get('source_manifest_sha256'), str)
                    or any(len(source_asset[field]) != 64
                           or any(c not in '0123456789abcdef' for c in source_asset[field])
                           for field in ('artifact_sha256', 'source_manifest_sha256'))
                    or not isinstance(source_asset.get('source_paths'), list)
                    or not source_asset['source_paths']
                    or any(not isinstance(path, str) or not path.startswith('runtime/urace/')
                           or not path.endswith('.py') or '..' in Path(path).parts
                           for path in source_asset['source_paths'])):
                raise ValueError('source_asset provenance manifest is malformed')
        task_by_id[task['task_id']] = task
        prior_contract = contracts_by_family.setdefault(task['family'], task['acceptance_contract_sha256'])
        if prior_contract != task['acceptance_contract_sha256']:
            raise ValueError('Each family must use one frozen acceptance contract hash')
        prior_rubric = value_rubrics_by_family.setdefault(task['family'], task['value_rubric_sha256'])
        if prior_rubric != task['value_rubric_sha256']:
            raise ValueError('Each family must use one frozen value rubric hash')

    rng = random.Random(seed)
    pairs = []
    by_family = {family: [t for t in tasks if t['family'] == family] for family in FAMILIES}
    for family in FAMILIES:
        family_tasks = by_family[family]
        rng.shuffle(family_tasks)
        orders = [['direct_executor', 'p2p_borrow']] * (len(family_tasks) // 2)
        orders += [['p2p_borrow', 'direct_executor']] * (len(family_tasks) - len(orders))
        rng.shuffle(orders)
        for repeat, (task, order) in enumerate(zip(family_tasks, orders)):
            pair_id = f"{family}-{repeat + 1:02d}-{task['task_id']}"
            pairs.append({'task': {'pair_id': pair_id, 'task_id': task['task_id'],
                                   'task_sha256': task['task_sha256'],
                                   'acceptance_contract_sha256': task['acceptance_contract_sha256'],
                                   'value_rubric_sha256': task['value_rubric_sha256'],
                                   'family': family, 'repeat': repeat,
                                   **({'source_asset': task['source_asset']}
                                      if task.get('source_asset') is not None else {})},
                          'arm_order': order})
    # Stable output order; randomization is frozen in each pair's arm_order.
    pairs.sort(key=lambda pair: (FAMILIES.index(pair['task']['family']), pair['task']['repeat']))
    frozen_identity = {**identity,
                       'task_sha256_by_id': {k: v['task_sha256'] for k, v in task_by_id.items()},
                       'acceptance_contract_sha256_by_family': contracts_by_family,
                       'value_rubric_sha256_by_family': value_rubrics_by_family,
                       'planned_pairs': {p['task']['pair_id']: p for p in pairs}}
    plan = {'schema': SCHEMA + '-cohort-plan-v2', 'seed': seed,
            'minimum_pairs': MIN_PAIRS, 'minimum_per_family': MIN_PER_FAMILY,
            'arms': list(ARMS), 'tasks': tasks, 'pairs': pairs,
            'identity': frozen_identity}
    plan['cohort_sha256'] = canonical_sha256(plan)
    return plan


def verify_plan(plan: dict) -> bool:
    try:
        return _verify_plan(plan)
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def _verify_plan(plan: dict) -> bool:
    if not isinstance(plan, dict) or plan.get('schema') != SCHEMA + '-cohort-plan-v2':
        return False
    supplied = plan.get('cohort_sha256')
    body = {key: value for key, value in plan.items() if key != 'cohort_sha256'}
    if supplied != canonical_sha256(body):
        return False
    tasks = plan.get('tasks')
    pairs = plan.get('pairs')
    identity = plan.get('identity')
    if not isinstance(tasks, list) or len(tasks) != MIN_PAIRS or not isinstance(pairs, list) or len(pairs) != MIN_PAIRS or not isinstance(identity, dict):
        return False
    ids = [task.get('task_id') for task in tasks if isinstance(task, dict)]
    if (len(ids) != MIN_PAIRS or len(set(ids)) != MIN_PAIRS
            or any(not isinstance(task_id, str)
                   or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', task_id) for task_id in ids)):
        return False
    profile = identity.get('executor_profile')
    evidence_mode = identity.get('evidence_mode')
    if (evidence_mode not in ('LIVE', 'SYNTHETIC', 'UNSPECIFIED')
            or identity.get('economic_claim_policy') != ECONOMIC_CLAIM_POLICY):
        return False
    if evidence_mode == 'LIVE':
        try:
            _validate_live_workload_identity(identity, tasks)
        except (ImportError, TypeError, ValueError):
            return False
    if (not isinstance(profile, dict)
            or profile.get('provider') not in ('codex', 'claude')
            or profile.get('effort') not in ('low', 'medium', 'high')
            or any(not isinstance(profile.get(key), str) or not profile[key]
                   for key in ('provider', 'model', 'client_version', 'effort'))):
        return False
    adapters = identity.get('adapter_sha256')
    if (not isinstance(adapters, dict) or set(adapters) != {'arm', 'evaluator', 'cost'}
            or any(not isinstance(value, str) or len(value) != 64
                   or any(c not in '0123456789abcdef' for c in value)
                   for value in adapters.values())):
        return False
    if (not isinstance(identity.get('runner_sha256'), str)
            or len(identity['runner_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in identity['runner_sha256'])
            or not isinstance(identity.get('exchange_buyer_id'), str)):
        return False
    if not isinstance(identity.get('exchange_buyer_public'), dict):
        return False
    sellers = identity.get('allowed_seller_peer_ids')
    seller_keys = identity.get('seller_public_keys')
    if (not isinstance(sellers, list) or not sellers or len(sellers) != len(set(sellers))
            or not isinstance(seller_keys, dict) or set(seller_keys) != set(sellers)
            or type(identity.get('minimum_asset_match_score', 0.0)) not in (int, float)
            or not 0.0 <= identity.get('minimum_asset_match_score', 0.0) <= 1.0
            or type(identity.get('peer_search_limit')) is not int
            or not 1 <= identity['peer_search_limit'] <= 10):
        return False
    try:
        from urace.ledger_crypto import validate_public
        validate_public(identity['exchange_buyer_public'])
        for seller_key in seller_keys.values():
            validate_public(seller_key)
    except (ImportError, TypeError, ValueError):
        return False
    rubrics_by_family = {}
    contracts_by_family = {}
    for source in tasks:
        if source.get('family') not in FAMILIES:
            return False
        for content_field, hash_field in (('task_specification', 'task_sha256'),
                                          ('acceptance_contract', 'acceptance_contract_sha256'),
                                          ('value_rubric', 'value_rubric_sha256')):
            content = source.get(content_field)
            digest = source.get(hash_field)
            if (not isinstance(content, str) or not content.strip() or len(content.encode()) > 131072
                    or not isinstance(digest, str)
                    or hashlib.sha256(content.encode()).hexdigest() != digest):
                return False
        source_asset = source.get('source_asset')
        if source_asset is not None:
            if (not isinstance(source_asset, dict)
                    or not isinstance(source_asset.get('feature_id'), str)
                    or not isinstance(source_asset.get('artifact_sha256'), str)
                    or not isinstance(source_asset.get('source_manifest_sha256'), str)
                    or any(len(source_asset[field]) != 64
                           or any(c not in '0123456789abcdef' for c in source_asset[field])
                           for field in ('artifact_sha256', 'source_manifest_sha256'))
                    or not isinstance(source_asset.get('source_paths'), list)
                    or not source_asset['source_paths']
                    or any(not isinstance(path, str) or not path.startswith('runtime/urace/')
                           or not path.endswith('.py') or '..' in Path(path).parts
                           for path in source_asset['source_paths'])):
                return False
        previous = rubrics_by_family.setdefault(source['family'], source['value_rubric_sha256'])
        if previous != source['value_rubric_sha256']:
            return False
        previous_contract = contracts_by_family.setdefault(source['family'], source['acceptance_contract_sha256'])
        if previous_contract != source['acceptance_contract_sha256']:
            return False
    task_by_id = {task['task_id']: task for task in tasks}
    counts = {family: sum(task.get('family') == family for task in tasks) for family in FAMILIES}
    if any(counts[f] < MIN_PER_FAMILY for f in FAMILIES):
        return False
    if identity.get('value_rubric_sha256_by_family') != rubrics_by_family:
        return False
    if identity.get('acceptance_contract_sha256_by_family') != contracts_by_family:
        return False
    pair_ids = [p.get('task', {}).get('pair_id') for p in pairs if isinstance(p, dict)]
    if len(pair_ids) != MIN_PAIRS or len(set(pair_ids)) != MIN_PAIRS:
        return False
    seen_tasks = set()
    order_counts = {family: {tuple(ARMS): 0, tuple(reversed(ARMS)): 0} for family in FAMILIES}
    planned = identity.get('planned_pairs')
    if not isinstance(planned, dict) or set(planned) != set(pair_ids):
        return False
    for pair in pairs:
        task = pair.get('task', {})
        task_id = task.get('task_id')
        source = task_by_id.get(task_id)
        if source is None or task_id in seen_tasks or task.get('family') != source.get('family'):
            return False
        seen_tasks.add(task_id)
        if (task.get('task_sha256') != source.get('task_sha256')
                or task.get('acceptance_contract_sha256') != source.get('acceptance_contract_sha256')
                or task.get('value_rubric_sha256') != source.get('value_rubric_sha256')
                or task.get('source_asset') != source.get('source_asset')
                or hashlib.sha256(source.get('task_specification', '').encode()).hexdigest() != source.get('task_sha256')
                or hashlib.sha256(source.get('acceptance_contract', '').encode()).hexdigest() != source.get('acceptance_contract_sha256')
                or hashlib.sha256(source.get('value_rubric', '').encode()).hexdigest() != source.get('value_rubric_sha256')):
            return False
        order = pair.get('arm_order')
        if order not in (list(ARMS), list(reversed(ARMS))):
            return False
        order_counts[source['family']][tuple(order)] += 1
        if planned[pair['task']['pair_id']] != pair:
            return False
    return seen_tasks == set(task_by_id) and all(
        counts[family] == 6
        and order_counts[family][tuple(ARMS)] == 3
        and order_counts[family][tuple(reversed(ARMS))] == 3
        for family in FAMILIES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks', required=True, help='JSON array of 30 frozen task manifests')
    parser.add_argument('--identity', required=True, help='JSON frozen evaluator/product/cost contract identity')
    parser.add_argument('--seed', required=True, type=int, help='recorded randomization seed')
    parser.add_argument('--output', required=True, help='new cohort plan JSON path; refuses overwrite')
    args = parser.parse_args(argv)
    try:
        output = Path(args.output)
        if output.exists():
            raise ValueError('output already exists; frozen cohort plans are immutable')
        tasks = json.loads(Path(args.tasks).read_text(encoding='utf-8'))
        identity = json.loads(Path(args.identity).read_text(encoding='utf-8'))
        plan = freeze_plan(tasks, identity, seed=args.seed)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': 'PLAN_FROZEN', 'cohort_sha256': plan['cohort_sha256'],
                          'pairs': len(plan['pairs']), 'family_counts': {
                              f: sum(p['task']['family'] == f for p in plan['pairs']) for f in FAMILIES},
                          'output': str(output)}, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({'status': 'ERROR', 'error': str(error)}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
