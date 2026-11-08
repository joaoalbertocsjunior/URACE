"""Run frozen direct-executor/P2P-first pairs through pinned local adapters.

This controller never claims savings. Product-specific adapters perform task
setup/executor work, independent acceptance, and cost measurement; their exact
source hashes must be pinned in the immutable cohort plan.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

from p2p_pair_protocol import ARMS, COST_SCHEMA, SCHEMA
from p2p_study_plan import verify_plan


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_adapter(path: str, expected_sha: str, name: str):
    source = _no_symlink_path(path)
    if not source.is_file() or _digest(source) != expected_sha:
        raise ValueError(f'{name} adapter is missing, symlinked, or differs from the frozen plan')
    spec = importlib.util.spec_from_file_location('urace_p2p_' + name, source.resolve())
    if spec is None or spec.loader is None:
        raise ValueError(f'Cannot load {name} adapter')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def _append_jsonl(path: Path, value: dict) -> None:
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(raw + '\n'); stream.flush(); os.fsync(stream.fileno())


def _confined(root: Path, path: str | Path) -> Path:
    candidate = _no_symlink_path(path, strict=True)
    resolved = candidate
    if not resolved.is_file() or not resolved.is_relative_to(root.resolve()):
        raise ValueError('Adapter output must be a regular file inside its arm workspace')
    return resolved


def _no_symlink_path(path: str | Path, *, strict: bool = True) -> Path:
    candidate = Path(path).expanduser().absolute()
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError('Benchmark paths cannot traverse symlinks')
    return candidate.resolve(strict=strict)


def _reject_symlink_path(root: Path, path: Path) -> Path:
    root = _no_symlink_path(root)
    resolved = _no_symlink_path(path)
    if not resolved.is_relative_to(root):
        raise ValueError('Study evidence path escapes the frozen study root')
    current = root
    for part in resolved.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Study evidence path cannot traverse symlinks')
    return resolved


def _check_exchange(identity: dict, exchange_root: str | Path):
    exchange_path = _no_symlink_path(exchange_root)
    if not exchange_path.is_dir():
        raise ValueError('Preconfigured exchange root must already exist')
    from urace.peer_exchange import Exchange
    exchange = Exchange(exchange_path)
    policy = exchange.load()
    if not policy.get('enabled') or not policy.get('network'):
        raise ValueError('Benchmark exchange must be explicitly enabled for networking')
    for name in ('identity-key.pem', 'identity-cert.pem', 'hybrid-identity.json'):
        path = exchange_path / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Preflight requires an existing regular buyer identity: ' + name)
    import ssl
    cert_der = ssl.PEM_cert_to_DER_cert((exchange_path / 'identity-cert.pem').read_text())
    buyer_id = hashlib.sha256(cert_der).hexdigest()
    if identity.get('exchange_buyer_id') != buyer_id:
        raise ValueError('Buyer exchange identity differs from frozen cohort plan')
    if exchange.crypto_identity().public() != identity.get('exchange_buyer_public'):
        raise ValueError('Buyer hybrid identity differs from frozen cohort plan')
    sellers = set(identity.get('allowed_seller_peer_ids', []))
    if not sellers or not sellers <= set(policy.get('peers', {})):
        raise ValueError('Cohort-pinned sellers are missing from the buyer exchange peer set')
    pins = identity.get('seller_public_keys', {})
    for seller in sellers:
        peer = policy['peers'][seller]
        if peer.get('blocked') or not peer.get('endpoint') or pins.get(seller) != peer.get('post_quantum'):
            raise ValueError('Pinned seller endpoint, trust state, or hybrid key differs from the frozen plan')
    exchange.audit_rows()  # Read-only verification of the buyer's current signed ledger.
    return exchange, exchange_path


def preflight(plan_path: str, study_root: str, exchange_root: str,
              arm_adapter_path: str, evaluator_adapter_path: str,
              cost_adapter_path: str) -> dict:
    """Read-only checks; does not contact peers or invoke provider clients."""
    plan_file = _no_symlink_path(plan_path)
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    if not verify_plan(plan):
        raise ValueError('Frozen plan hash or design verification failed')
    identity = plan['identity']
    if _digest(Path(__file__)) != identity['runner_sha256']:
        raise ValueError('Runner source differs from the frozen cohort plan')
    adapters = identity['adapter_sha256']
    modules = {
        'arm': _load_adapter(arm_adapter_path, adapters['arm'], 'arm'),
        'evaluator': _load_adapter(evaluator_adapter_path, adapters['evaluator'], 'evaluator'),
        'cost': _load_adapter(cost_adapter_path, adapters['cost'], 'cost'),
    }
    methods = {'arm': 'run_arm', 'evaluator': 'evaluate', 'cost': 'measure'}
    if any(not callable(getattr(modules[key], method, None)) for key, method in methods.items()):
        raise ValueError('One or more adapters do not implement the frozen runner interface')
    requested_root = Path(study_root)
    if requested_root.is_symlink():
        raise ValueError('Study root cannot be a symlink')
    root = _no_symlink_path(requested_root)
    if not root.is_dir():
        raise ValueError('Study root must exist for read-only preflight')
    _check_exchange(identity, exchange_root)
    return {'status': 'PREFLIGHT_READY', 'cohort_sha256': plan['cohort_sha256'],
            'pairs_planned': len(plan['pairs']), 'profile': identity['executor_profile'],
            'pinned_sellers': identity['allowed_seller_peer_ids'],
            'adapter_hashes_verified': True,
            'network_reachability_checked': False, 'provider_calls_made': 0,
            'cost_claim': 'NOT_ESTABLISHED'}


def _acceptance_receipt(envelope: dict, identity: dict, pair: dict, arm: str) -> dict:
    from urace.ledger_crypto import public_id, verify
    if not isinstance(envelope, dict) or not isinstance(envelope.get('payload'), dict):
        raise ValueError('Evaluator must return a signed acceptance envelope')
    payload = envelope['payload']
    required = {'pair_id': pair['pair_id'], 'task_sha256': pair['task_sha256'],
                'acceptance_contract_sha256': pair['acceptance_contract_sha256'],
                'value_rubric_sha256': pair['value_rubric_sha256'],
                'arm': arm, 'evaluator_id': identity['independent_evaluator_id'],
                'measurement_complete': True}
    if (any(payload.get(key) != value for key, value in required.items())
            or type(payload.get('passed')) is not bool
            or type(payload.get('value_score')) not in (int, float)
            or not math.isfinite(payload['value_score'])
            or not 0.0 <= payload['value_score'] <= 1.0):
        raise ValueError('Acceptance receipt must bind pass/fail and a normalized value score to this arm')
    public = identity['independent_evaluator_public']
    if public_id(public) != identity['independent_evaluator_id']:
        raise ValueError('Evaluator key differs from the frozen cohort identity')
    verify(public, payload, envelope.get('signature'), 'p2p-pair-acceptance')
    return envelope


def _receipt_records(result: dict, profile: dict, product_id: str,
                     transport_root: Path, evidence_root: Path) -> list[dict]:
    receipts = result.get('native_receipts')
    if not isinstance(receipts, list):
        raise ValueError('Arm adapter must return native_receipts as a list')
    ids, copied = set(), []
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError('Native usage receipt must be an object')
        identifier = receipt.get('id')
        if not isinstance(identifier, str) or not identifier.isalnum() or identifier in ids:
            raise ValueError('Native receipt IDs must be unique alphanumeric identifiers')
        ids.add(identifier)
        authoritative = transport_root / (identifier + '.json')
        if authoritative.is_symlink() or not authoritative.is_file():
            raise ValueError('Native receipt is absent from the authoritative executor transport log')
        if json.loads(authoritative.read_text(encoding='utf-8')) != receipt:
            raise ValueError('Adapter native receipt differs from the authoritative transport log')
        if (receipt.get('provider') != profile['provider']
                or receipt.get('requested_model') != profile['model']
                or receipt.get('effort') != profile['effort']
                or receipt.get('client_version') != profile['client_version']
                or receipt.get('product_id') != product_id):
            raise ValueError('Native receipt differs from the frozen provider profile or product')
        target = evidence_root / 'transport' / (identifier + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if json.loads(target.read_text()) != receipt:
                raise ValueError('Conflicting native receipt already exists in the study evidence')
        else:
            _write_json(target, receipt)
        copied.append(receipt)
    return copied


def _snapshot_exchange_evidence(exchange, study_root: Path, pair_id: str, bundle_id: str) -> str:
    """Copy public verifiable evidence only; private identity keys stay local."""
    source = exchange.root
    root = _no_symlink_path(study_root)
    target = _no_symlink_path(root / 'exchange-evidence' / pair_id, strict=False)
    if not target.is_relative_to(root):
        raise ValueError('Exchange evidence snapshot path escapes the study root')
    target.mkdir(parents=True, exist_ok=False)
    for name in ('policy.json', 'audit.jsonl'):
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Exchange evidence lacks a regular ' + name)
        shutil.copyfile(path, target / name)
    ledger_source = source / 'signed-audit'
    ledger_target = target / 'signed-audit'
    if ledger_source.is_symlink() or not ledger_source.is_dir():
        raise ValueError('Exchange signed audit evidence is missing')
    ledger_target.mkdir()
    for path in ledger_source.iterdir():
        if path.name == 'identity.json':
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError('Signed audit snapshot contains an unsafe entry')
        if path.name not in ('public.json', 'head.json', 'writer.lock') and not path.name.endswith('.block'):
            continue
        shutil.copyfile(path, ledger_target / path.name)
    bundle_path = source / 'quarantine' / (bundle_id + '.json')
    if bundle_path.is_symlink() or not bundle_path.is_file():
        raise ValueError('Transferred quarantined bundle evidence is missing')
    (target / 'quarantine').mkdir()
    shutil.copyfile(bundle_path, target / 'quarantine' / bundle_path.name)
    from urace.peer_exchange import Exchange
    Exchange(target).audit_rows()
    return str((target / 'audit.jsonl').relative_to(study_root))


def _prepare_asset(exchange, task: dict, identity: dict, peer_limit: int,
                   study_root: Path, pair_id: str) -> tuple[dict, dict]:
    from urace import remote_assets
    started = time.monotonic()
    discovery = remote_assets.discover(exchange, query=task['task_specification'], peer_limit=peer_limit)
    discovery_metrics = discovery['network_metrics']
    allowed_sellers = set(identity.get('allowed_seller_peer_ids', []))
    seller_keys = identity.get('seller_public_keys', {})
    policy = exchange.load()
    candidates = [item for item in discovery['open_assets']
                  if item.get('seller_peer_id') in allowed_sellers
                  and seller_keys.get(item.get('seller_peer_id'))
                  == policy.get('peers', {}).get(item.get('seller_peer_id'), {}).get('post_quantum')]
    threshold = identity.get('minimum_asset_match_score', 0.0)
    candidates = [item for item in candidates if item.get('match_score', 0.0) >= threshold]
    if not candidates:
        raise ValueError('No eligible pinned open-use asset meets the frozen selection threshold')
    selected = candidates[0]  # remote_assets returns stable score/peer/feature ordering
    fetched = remote_assets.fetch_open_asset(exchange, selected['seller_peer_id'], selected['asset_id'])
    fetch_metrics = fetched.get('network_metrics')
    if (fetched.get('status') not in ('QUARANTINED', 'ALREADY_QUARANTINED')
            or fetched.get('seller_ack', {}).get('status') != 'BUYER_QUARANTINE_RECEIPT_VERIFIED'
            or not isinstance(fetch_metrics, dict)):
        raise ValueError('Open asset fetch or portable seller acknowledgement did not verify')
    bundle = exchange.inspect(fetched['bundle_id'])['bundle']
    encoded = bundle['payload'].get('artifact_b64')
    import base64
    raw = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != selected['artifact_sha256']:
        raise ValueError('Quarantined bytes differ from the pinned catalog digest')
    marker_path = _snapshot_exchange_evidence(exchange, study_root, pair_id, fetched['bundle_id'])
    return ({'seller_peer_id': selected['seller_peer_id'], 'asset_id': selected['asset_id'],
             'feature_id': selected['feature_id'], 'license_id': selected['license_id'],
             'bundle_id': fetched['bundle_id'], 'artifact_sha256': digest,
             'artifact_bytes': raw, 'discovery_network_metrics': discovery_metrics,
             'fetch_network_metrics': fetch_metrics,
             'exchange_marker_path': marker_path,
             'discovery_elapsed_seconds': max(0.0, time.monotonic() - started)}, fetched)


def run_cohort(plan_path: str, study_root: str, exchange_root: str,
               arm_adapter_path: str, evaluator_adapter_path: str,
               cost_adapter_path: str, *, max_pairs: int = 1,
               peer_limit: int | None = None, transport_root: str | None = None,
               live: bool = False) -> dict:
    """Execute up to ``max_pairs`` once each; never retries an attempted pair."""
    if not live:
        raise ValueError('Live provider/network work requires explicit live=True / --run-live')
    if type(max_pairs) is not int or not 1 <= max_pairs <= 30:
        raise ValueError('max_pairs must be between 1 and 30')
    if peer_limit is not None and (type(peer_limit) is not int or not 1 <= peer_limit <= 10):
        raise ValueError('peer_limit must be between 1 and 10')
    plan_file = _no_symlink_path(plan_path)
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    if not verify_plan(plan):
        raise ValueError('Frozen plan integrity or design verification failed')
    identity = plan['identity']
    if _digest(Path(__file__)) != identity.get('runner_sha256'):
        raise ValueError('Runner source differs from the frozen cohort plan')
    hashes = identity.get('adapter_sha256', {})
    arm_adapter = _load_adapter(arm_adapter_path, hashes.get('arm'), 'arm')
    evaluator_adapter = _load_adapter(evaluator_adapter_path, hashes.get('evaluator'), 'evaluator')
    cost_adapter = _load_adapter(cost_adapter_path, hashes.get('cost'), 'cost')
    for module, method in ((arm_adapter, 'run_arm'), (evaluator_adapter, 'evaluate'),
                           (cost_adapter, 'measure')):
        if not callable(getattr(module, method, None)):
            raise ValueError(f'Adapter must implement {method}(request)')

    requested_root = Path(study_root)
    if requested_root.is_symlink():
        raise ValueError('Study root cannot be a symlink')
    root = _no_symlink_path(requested_root, strict=False)
    root.mkdir(parents=True, exist_ok=True)
    exchange, exchange_path = _check_exchange(identity, exchange_root)
    exchange_policy = exchange.load()
    buyer_id = exchange.identity()['peer_id']
    peer_limit = identity.get('peer_search_limit') if peer_limit is None else peer_limit
    if peer_limit != identity.get('peer_search_limit'):
        raise ValueError('Peer search limit differs from the frozen cohort identity')
    if not set(identity.get('allowed_seller_peer_ids', [])) <= set(exchange_policy.get('peers', {})):
        raise ValueError('A cohort-pinned seller is not present in the exchange peer set')

    plan_copy = root / 'cohort-plan.json'
    if plan_copy.exists():
        if json.loads(plan_copy.read_text()) != plan:
            raise ValueError('Study root already contains a different frozen plan')
    else:
        _write_json(plan_copy, plan)
    pair_file = root / 'pairs.jsonl'
    launches = root / 'launches'
    launches.mkdir(exist_ok=True)
    lock_path = root / 'runner.lock'
    transport = Path(transport_root).resolve() if transport_root else Path(__file__).parent / 'transport'
    from urace.ledger_crypto import public_id
    if public_id(identity['independent_evaluator_public']) != identity['independent_evaluator_id']:
        raise ValueError('Independent evaluator key does not match frozen identity')

    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = [json.loads(line) for line in pair_file.read_text().splitlines() if line.strip()] if pair_file.exists() else []
        completed_ids = {row.get('task', {}).get('pair_id') for row in existing}
        attempted = 0
        for planned in plan['pairs']:
            task_ref = planned['task']; pair_id = task_ref['pair_id']
            if pair_id in completed_ids:
                continue
            if attempted >= max_pairs:
                break
            attempted += 1
            launch_path = launches / (pair_id + '.json')
            launch_record = {'pair_id': pair_id, 'cohort_sha256': plan['cohort_sha256'],
                             'arm_order': planned['arm_order'], 'started_unix': time.time(),
                             'attempted_once': True}
            if launch_path.exists():
                # A crash after launch is retained as an incomplete attempt, never retried.
                incomplete = {'schema': SCHEMA, 'task': task_ref, 'arm_order': planned['arm_order'],
                              'arms': {}, 'attempt_failure': 'INCOMPLETE_PRIOR_LAUNCH_NOT_RETRIED'}
                _append_jsonl(pair_file, incomplete)
                completed_ids.add(pair_id)
                continue
            _write_json(launch_path, launch_record)
            task = next(item for item in plan['tasks'] if item['task_id'] == task_ref['task_id'])
            arms, arm_results, arm_errors = {}, {}, {}
            delivery = None
            for arm_name in planned['arm_order']:
                workspace = root / 'workspaces' / pair_id / arm_name
                workspace.mkdir(parents=True, exist_ok=False)
                borrowed_path = None
                p2p_data = None
                started = time.monotonic()
                try:
                    if arm_name == 'p2p_borrow':
                        p2p_data, fetched = _prepare_asset(exchange, task, identity, peer_limit,
                                                           root, pair_id)
                        asset_dir = root / 'assets'; asset_dir.mkdir(exist_ok=True)
                        borrowed_path = asset_dir / (pair_id + '-' + p2p_data['artifact_sha256'] + '.bin')
                        if not borrowed_path.exists():
                            borrowed_path.write_bytes(p2p_data['artifact_bytes']); borrowed_path.chmod(0o400)
                        p2p_data['artifact_path'] = str(borrowed_path.relative_to(root))
                        p2p_data.pop('artifact_bytes')
                        delivery = p2p_data
                    request = {'pair_id': pair_id, 'task': task,
                               'task_specification': task['task_specification'],
                               'acceptance_contract': task['acceptance_contract'],
                               'value_rubric': task['value_rubric'],
                               'arm': arm_name, 'workspace': str(workspace),
                               'profile': identity['executor_profile'],
                               'borrowed_asset_path': str(borrowed_path) if borrowed_path else None,
                               'borrowed_asset': ({k: v for k, v in p2p_data.items()
                                                   if k not in ('discovery_network_metrics','fetch_network_metrics')}
                                                  if p2p_data else None)}
                    result = arm_adapter.run_arm(request)
                    if not isinstance(result, dict):
                        raise ValueError('run_arm must return an object')
                    receipts = _receipt_records(result, identity['executor_profile'],
                                                identity['product_id'], transport, root)
                    if arm_name == 'direct_executor' and not receipts:
                        raise ValueError('Direct-executor arm requires at least one attributable native call')
                    if result.get('provider') != identity['executor_profile']['provider']:
                        raise ValueError('Adapter result provider differs from the frozen profile')
                    if result.get('actual_providers') != [identity['executor_profile']['provider']]:
                        raise ValueError('Arm must use exactly the one frozen provider')
                    artifact_out = _confined(workspace, result.get('artifact_path'))
                    evaluator_request = {**request, 'execution': result,
                                         'artifact_path': str(artifact_out),
                                         'native_receipts': receipts}
                    acceptance = _acceptance_receipt(evaluator_adapter.evaluate(evaluator_request),
                                                     identity, task_ref, arm_name)
                    acceptance_rel = f"acceptance/{pair_id}-{arm_name}.json"
                    acceptance_hash = _write_json(root / acceptance_rel, acceptance)
                    row = {
                        'arm': arm_name, 'pair_id': pair_id, 'product_id': identity['product_id'],
                        'provider': identity['executor_profile']['provider'],
                        'model': identity['executor_profile']['model'],
                        'client_version': identity['executor_profile']['client_version'],
                        'effort': identity['executor_profile']['effort'],
                        'actual_providers': [identity['executor_profile']['provider']],
                        'task_sha256': task_ref['task_sha256'],
                        'acceptance_contract_sha256': task_ref['acceptance_contract_sha256'],
                        'native_receipts': receipts,
                        'elapsed_seconds': max(0.001, time.monotonic() - started),
                        'tokens': sum(receipt['tokens'] for receipt in receipts)
                                  if receipts and all(type(r.get('tokens')) is int for r in receipts) else None,
                        'acceptance_receipt_path': acceptance_rel,
                        'acceptance_receipt_sha256': acceptance_hash,
                        'provider_reported_cost_usd': result.get('provider_reported_cost_usd'),
                    }
                    if arm_name == 'p2p_borrow' and delivery:
                        row.update({'delivery_kind': 'open_asset',
                                    'exchange_marker_path': delivery['exchange_marker_path'],
                                    'exchange_buyer_id': buyer_id,
                                    'seller_peer_id': delivery['seller_peer_id'],
                                    'asset_id': delivery['asset_id'], 'bundle_id': delivery['bundle_id'],
                                    'feature_id': delivery['feature_id'],
                                    'artifact_sha256': delivery['artifact_sha256'],
                                    'artifact_path': delivery['artifact_path'],
                                    'discovery_network_metrics': delivery['discovery_network_metrics'],
                                    'fetch_network_metrics': delivery['fetch_network_metrics']})
                        if not receipts:
                            no_call = acceptance.get('no_call_receipt')
                            if not isinstance(no_call, dict):
                                raise ValueError('Zero-call P2P arm requires evaluator-signed no-call evidence')
                            from p2p_pair_protocol import _no_call_receipt
                            no_call_rel = f'no-call/{pair_id}.json'
                            no_call_hash = _write_json(root / no_call_rel, no_call)
                            row.update({'native_receipts': [], 'no_call_receipt_path': no_call_rel,
                                        'no_call_receipt_sha256': no_call_hash})
                            _no_call_receipt(row, root, task_ref, identity)
                    arms[arm_name] = row
                    arm_results[arm_name] = result
                except Exception as error:
                    arm_errors[arm_name] = type(error).__name__ + ': ' + str(error)[:400]

            if delivery and 'direct_executor' in arm_results and 'p2p_borrow' in arm_results:
                try:
                    p2p_row = arms['p2p_borrow']
                    request = {'pair_id': pair_id, 'task': task, 'task_ref': task_ref,
                               'identity': identity, 'delivery': {k: v for k, v in delivery.items()
                                                                  if k != 'artifact_bytes'},
                               'direct_arm': arm_results['direct_executor'],
                               'p2p_arm': arm_results['p2p_borrow'],
                               'discovery_network_metrics': delivery['discovery_network_metrics'],
                               'fetch_network_metrics': delivery['fetch_network_metrics']}
                    costs = cost_adapter.measure(request)
                    if not isinstance(costs, dict) or not isinstance(costs.get('payload'), dict):
                        raise ValueError('Cost adapter must return an evaluator-signed cost envelope')
                    payload = costs['payload']
                    from urace.ledger_crypto import verify
                    verify(identity['independent_evaluator_public'], payload,
                           costs.get('signature'), 'p2p-pair-cost')
                    expected_cost_fields = {
                        'schema': COST_SCHEMA, 'pair_id': pair_id,
                        'task_sha256': task_ref['task_sha256'],
                        'delivery_kind': 'open_asset', 'asset_id': delivery['asset_id'],
                        'bundle_id': delivery['bundle_id'], 'feature_id': delivery['feature_id'],
                        'artifact_sha256': delivery['artifact_sha256'],
                        'measurement_contract_sha256': identity['cost_measurement_contract_sha256'],
                    }
                    if any(payload.get(key) != value for key, value in expected_cost_fields.items()):
                        raise ValueError('Signed cost receipt does not bind to this pair and transferred asset')
                    discovery = delivery['discovery_network_metrics']; fetch = delivery['fetch_network_metrics']
                    if (payload.get('network_transfer_bytes') != discovery['application_payload_bytes'] + fetch['application_payload_bytes']
                            or not math.isclose(payload.get('discovery_seconds', -1), discovery['elapsed_seconds'], rel_tol=0, abs_tol=0.01)
                            or not math.isclose(payload.get('fetch_seconds', -1), fetch['elapsed_seconds'], rel_tol=0, abs_tol=0.01)):
                        raise ValueError('Cost receipt does not reconcile to measured network discovery/fetch observations')
                    if (type(payload.get('network_cost_usd')) not in (int, float)
                            or not math.isfinite(payload['network_cost_usd']) or payload['network_cost_usd'] < 0
                            or any(type(payload.get(key)) not in (int, float)
                                   or not math.isfinite(payload[key]) or payload[key] < 0
                                   for key in ('integration_seconds', 'validation_seconds'))):
                        raise ValueError('Signed cost receipt lacks complete finite measured cost fields')
                    for field in ('provider_cost_usd_by_arm', 'non_provider_cost_usd_by_arm'):
                        values = payload.get(field)
                        if (not isinstance(values, dict) or set(values) != set(ARMS)
                                or any(type(values[arm]) not in (int, float)
                                       or not math.isfinite(values[arm]) or values[arm] < 0
                                       for arm in ARMS)):
                            raise ValueError('Signed cost receipt must include finite paired cost dimensions')
                    if (payload.get('provider_cost_basis') not in
                            ('ACTUAL_MARGINAL', 'API_EQUIVALENT', 'SUBSCRIPTION_ALLOCATED')
                            or payload.get('non_provider_cost_complete_by_arm') !=
                            {'direct_executor': True, 'p2p_borrow': True}):
                        raise ValueError('Signed cost receipt must declare paired cost basis and complete non-provider costs')
                    cost_rel = f'costs/{pair_id}-p2p.json'
                    p2p_row['p2p_cost_receipt_path'] = cost_rel
                    p2p_row['p2p_cost_receipt_sha256'] = _write_json(root / cost_rel, costs)
                except Exception as error:
                    arm_errors['cost_measurement'] = type(error).__name__ + ': ' + str(error)[:400]

            pair_result = {'schema': SCHEMA, 'task': task_ref,
                           'arm_order': planned['arm_order'], 'arms': arms,
                           'runner_errors': arm_errors,
                           'cohort_sha256': plan['cohort_sha256']}
            _append_jsonl(pair_file, pair_result)
            completed_ids.add(pair_id)
        summary = {'status': 'ATTEMPTS_RECORDED', 'cohort_sha256': plan['cohort_sha256'],
                   'attempted_this_run': attempted, 'recorded_pairs': len(completed_ids),
                   'planned_pairs': len(plan['pairs']), 'qualified_savings_claim': False,
                   'pair_manifest': str(pair_file.relative_to(root))}
        return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--study-root', required=True)
    parser.add_argument('--exchange-root', required=True, help='preconfigured benchmark peer identity under study root')
    parser.add_argument('--arm-adapter', required=True)
    parser.add_argument('--evaluator-adapter', required=True)
    parser.add_argument('--cost-adapter', required=True)
    parser.add_argument('--max-pairs', type=int, default=1)
    parser.add_argument('--peer-limit', type=int)
    parser.add_argument('--transport-root')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight', action='store_true', help='read-only plan/adapter/peer configuration checks')
    parser.add_argument('--run-live', action='store_true', help='explicitly authorize provider and network activity')
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            result = preflight(args.plan, args.study_root, args.exchange_root,
                               args.arm_adapter, args.evaluator_adapter, args.cost_adapter)
        else:
            result = run_cohort(args.plan, args.study_root, args.exchange_root,
                                args.arm_adapter, args.evaluator_adapter, args.cost_adapter,
                                max_pairs=args.max_pairs,
                                peer_limit=args.peer_limit,
                                transport_root=args.transport_root, live=args.run_live)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, ImportError) as error:
        print(json.dumps({'status': 'ERROR', 'error': str(error)}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
