"""Core lifecycle boundary and replayable observations for the specification adapter.

The core owns Intent, Authority, input consumption, lifecycle controls and history.
Accepted version evidence remains authoritative for the adapter's Product effects.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


class WorkflowConflict(RuntimeError):
    pass


def _read(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def product_copy(config: dict, base: Path) -> Path | None:
    value = config.get('specification_workflow', {}).get('product_copy')
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        from ._common import ROOT
        path = ROOT / path
    path = path.resolve()
    if not path.is_relative_to(base.resolve() / 'product'):
        raise WorkflowConflict('Specification Product copy must stay inside trial/product')
    return path


def _version_folder(base: Path, number: int) -> Path:
    if type(number) is not int or number < 0:
        raise WorkflowConflict('Invalid specification version identity')
    series = _read(base/'version-series.json')['root']
    folder = (base/series/f'v{number:06d}').resolve()
    if not folder.is_relative_to(base.resolve()/'versions'):
        raise WorkflowConflict('Specification version escapes version storage')
    return folder


def _context(state: dict, config: dict, base: 'Path | None' = None) -> dict:
    from . import rules, inspection
    # Context describes retained operator work, including work currently blocked or
    # active. Scheduling eligibility must not erase owner intent from the prompt.
    goals = [g for g in state.get('objectives', []) if g.get('status') not in
             {'completed', 'cancelled', 'rejected', 'superseded'}]
    goals = sorted(goals, key=lambda g: (g.get('id') != state.get('current_objective'),
                                        -g.get('priority', 50)))
    active = rules.active_rules(state.get('rule_ledger', {}), include_inferred=False)
    value = {
        'intent': state.get('intent', config.get('intent')),
        'authority': state.get('authority', config.get('authority')),
        'constraints': state.get('constraints', config.get('constraints', [])),
        'explicit_rules': [{k: r.get(k) for k in ('id', 'kind', 'statement', 'scope', 'source')}
                           for r in active],
        'user_context': [{k: r.get(k) for k in ('id', 'text', 'content', 'source', 'source_text')}
                         for r in state.get('context_inputs', [])],
        'objectives': [{k: g.get(k) for k in ('id', 'title', 'scope', 'status', 'success_measure', 'priority', 'source')}
                       for g in goals],
        'paused': state.get('lifecycle_state') == 'PAUSED',
    }
    if base is not None and config.get('runtime_workflow', {}).get('enabled'):
        try:
            import sys as _sys
            _sys.path.insert(0, str(base.parent / 'trial'))
            import runtime_snapshot as _rs
            # Discover extra product bases from products.json
            extra_bases = []
            products_path = base / 'products.json'
            if products_path.exists():
                try:
                    _products = json.loads(products_path.read_text())
                    if isinstance(_products, list):
                        _items = _products
                    elif isinstance(_products, dict):
                        _items = _products.get('products', [])
                    else:
                        _items = []
                    for _p in _items:
                        if (isinstance(_p, dict)
                                and _p.get('kind') == 'runtime'
                                and _p.get('snapshots_base')):
                            _eb = Path(_p['snapshots_base'])
                            if not _eb.is_absolute():
                                _eb = base / _eb
                            if _eb != base and _eb not in extra_bases:
                                extra_bases.append(_eb)
                except Exception:
                    pass
            ctx = _rs.planning_context(base, limit=3, extra_bases=extra_bases if extra_bases else None)
            if ctx['count'] > 0:
                value['runtime_improvement_history'] = ctx['runtime_improvement_history']
                if ctx.get('product_bases'):
                    value['runtime_improvement_product_bases'] = ctx['product_bases']
        except Exception:
            pass
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    if len(encoded) > 6000:
        raise WorkflowConflict('Owner context exceeds the bounded adapter context; not silently truncated')
    return {'value': value, 'sha256': _sha(encoded), 'bytes': len(encoded)}


def _import_observations(config: dict, state: dict, base: Path) -> None:
    """Project verified adapter work without treating editorial acceptance as value proof."""
    from . import cli
    trial = _read(base/'trial-clock.json', {})['trial_id']
    jobs = _read(base/'state.json', {'jobs': []})['jobs']
    operations = state.setdefault('operations', [])
    known = {o.get('id') for o in operations}
    withdrawal = _read(base/'withdrawn-acceptances.json', {})
    withdrawn = withdrawal.get('versions', []) if withdrawal.get('trial_id') == trial else []
    if not isinstance(withdrawn, list) or any(type(v) is not int or v <= 0 for v in withdrawn):
        raise WorkflowConflict('Invalid withdrawn editorial version identity')
    withdrawn = set(withdrawn)
    def reconcile_claim(operation, job):
        if (job.get('outcome') != 'ACCEPTED_EDITORIAL_IMPROVEMENT'
                or job.get('accepted_version') not in withdrawn):
            return
        if operation.get('editorial_acceptance_withdrawn'):
            return
        # The historical verdict and snapshot are immutable; the current claim is not.
        operation['quality_improvement_claimed'] = False
        operation['editorial_acceptance_withdrawn'] = True
        operation['quality_claim_withdrawal'] = {'version':job['accepted_version'],
            'source':str(base/'withdrawn-acceptances.json'), 'trial_id':trial}
        cli._emit_trace(state, 'OPERATION', 'Editorial quality claim withdrawn',
                        operation_id=job['id'], detail=json.dumps(operation['quality_claim_withdrawal'], sort_keys=True))
    by_id = {o.get('id'):o for o in operations if o.get('trial_id') == trial}
    for job in jobs:
        if job.get('trial_id') == trial and job.get('id') in by_id:
            reconcile_claim(by_id[job['id']], job)
    for job in jobs:
        if job.get('trial_id') != trial or job['id'] in known:
            continue
        if not isinstance(job['id'], str) or not job['id'].startswith('spec-') or '/' in job['id']:
            raise WorkflowConflict('Invalid adapter task identity')
        accepted = job.get('outcome') == 'ACCEPTED_EDITORIAL_IMPROVEMENT'
        restored = job.get('outcome') == 'CORRECTIVE_RESTORE'
        snapshot = None
        review = {}
        if accepted or restored:
            from snapshot_metadata import inspect_snapshot
            folder = _version_folder(base, job['accepted_version'])
            checked = inspect_snapshot(folder)
            if bool(checked['manifest'].get('restoration')) != restored:
                raise WorkflowConflict('Corrective restoration classification mismatch')
            if checked['manifest'].get('trial_id') != trial:
                raise WorkflowConflict('Accepted task does not match the active trial')
            if Path(checked['manifest']['job']).name != job['id']:
                raise WorkflowConflict('Accepted task/snapshot linkage mismatch')
            snapshot = str(folder)
            review = checked['manifest']['validation']
            if checked['metadata']['validation']['model_review'] != review:
                raise WorkflowConflict('Accepted review conflicts with immutable metadata')
            completion = checked.get('completion')
            if not completion or completion.get('task_id') != job['id'] or completion.get('task_outcome') != job['outcome']:
                raise WorkflowConflict('Accepted task lacks matching completion evidence')
        status = 'ACCEPTED' if accepted or restored else ('OBSERVED_NO_EFFECT' if job.get('outcome') == 'AUDITED_NO_CHANGE' else 'REJECTED_EDITORIAL')
        operation = {
            'id': job['id'], 'change_id': job['id'], 'created_at': job['started_at'],
            'updated_at': job['finished_at'], 'attempted_at': job['started_at'],
            'accepted_at': job['finished_at'] if accepted or restored else None,
            'status': status, 'scope': 'documentation', 'trial_id': trial,
            'objective_reference': job.get('core_objective'), 'plan_reference': None,
            'decision': job['section'], 'source': 'verified specification adapter observations',
            'changed_files': [str(product_copy(config, base))] if accepted or restored else [],
            'snapshot': snapshot, 'task_report': str(base/'runs'/trial/job['id']/'report.json'),
            'executor': {'executor_id': job.get('proposer_provider', 'unknown'),
                         'reviewer_provider': job.get('reviewer_provider')},
            'executor_source_summary': review.get('explanation', job.get('error', job['outcome'])),
            'independent_validation': {'verdict': 'ACCEPTED' if accepted or restored else status,
                                       'method': ('Exact earlier immutable snapshot restoration' if restored else 'Separate editorial review plus static preservation gates'),
                                       'scope': 'Bounded editorial judgment; not executable or customer-value proof'},
            'outcome': {'status': 'AWAITING_OUTCOME', 'real_user_value_verified': False,
                        'reason': 'Task acceptance does not establish sustained real-user benefit'},
            'quality_improvement_claimed': accepted,
            'real_user_value_verified': False, 'attribution_state': 'UNATTRIBUTED',
        }
        reconcile_claim(operation, job)
        operations.append(operation); known.add(job['id'])
        cli._emit_trace(state, 'OPERATION', 'Specification adapter task reconciled',
                        operation_id=job['id'], detail=json.dumps({'outcome': job['outcome'], 'snapshot': snapshot}, sort_keys=True))
    # Native receipts already have stable ids; never invent or duplicate invocations.
    calls = state.setdefault('executor_state', {}).setdefault('executor_calls', [])
    known_calls = {c.get('id') for c in calls}
    for line in (base/'ledger.jsonl').read_text().splitlines() if (base/'ledger.jsonl').exists() else []:
        row = json.loads(line)
        if row.get('kind') != 'finished' or row.get('trial_id') != trial or row['id'] in known_calls:
            continue
        usage = {'source': 'retained native transport receipt'}
        if row.get('tokens') is not None:
            usage['total_tokens'] = row['tokens']
        calls.append({'id': row['id'], 'at': row['at'], 'created_at': row['at'],
                      'updated_at': row['at'], 'stage': 'specification_adapter',
                      'outcome': 'failed' if row.get('failure') else 'observed',
                      'usage': usage, 'usage_missing': row.get('tokens') is None,
                      'elapsed_seconds': row.get('wall_seconds'), 'trial_id': trial,
                      'executor_attribution': {'executor_id': row['provider']},
                      'native_receipt': str(base/'transport'/(row['id']+'.json'))})
        state['executor_state'].setdefault('workflow_observations', {})[row['provider']] = {
            'native_call_id':row['id'], 'at':row['at'], 'failure':row.get('failure'),
            'tokens':row.get('tokens'), 'wall_seconds':row.get('wall_seconds'),
            'scope':'Last observed artifact-only call; not a promise of current credits or workspace-write capability'}
        known_calls.add(row['id'])


def _synchronize_copy(config: dict, state: dict, base: Path) -> None:
    from ._common import atomic_write_text
    target = product_copy(config, base)
    if target is None:
        return
    pointer = _read(base/'active-version.json')
    folder = _version_folder(base, pointer['version'])
    manifest = _read(folder/'manifest.json'); data = (folder/'URACE.md').read_bytes()
    if _sha(data) != pointer['sha256'] or manifest['sha256'] != pointer['sha256']:
        raise WorkflowConflict('Active Product content failed integrity validation')
    if target.exists():
        current = _sha(target.read_bytes())
        prior = state.get('specification_adapter', {}).get('product_sha256')
        if current not in {pointer['sha256'], prior}:
            raise WorkflowConflict('Product copy changed externally; preserving the edit')
    if not target.exists() or _sha(target.read_bytes()) != pointer['sha256']:
        atomic_write_text(target, data.decode())
    state['specification_adapter'] = {'trial_id': _read(base/'trial-clock.json')['trial_id'],
                                    'version': pointer['version'], 'product_sha256': pointer['sha256']}


def boundary(base: Path, *, assess: bool = True) -> dict[str, Any]:
    """Use the existing core controls, deterministic lifecycle and authoritative inbox."""
    from . import cli, cognitive_resume
    base = Path(base)
    config = cli.load_config()
    with cli.state_lock(cli.state_path(config)):
        state = cli.load_state(config)
        consumed = cli.consume_inputs(config, state)
        _synchronize_copy(config, state, base)
        _import_observations(config, state, base)
        if state.get('lifecycle_state') == 'PAUSED':
            gate = {'outcome': 'paused', 'reason': 'Operator paused the core lifecycle'}
        else:
            gate = cli._run_onboard_gate(config, state)
        outcome = gate
        if gate is None and assess:
            delegated = copy.deepcopy(config)
            # The adapter provides actual native execution. Deterministic core phases still run.
            delegated.setdefault('executor', {})['enabled'] = False
            cli._check_scheduled_tasks(state, delegated)
            outcome = cli.cycle(delegated, state, allow_execution=False)
        state['cognitive_resume_context'] = cognitive_resume.generate(state)
        context = _context(state, config, base)
        if state.get('lifecycle_state') in {'BLOCKED','PAUSED','ONBOARDING','WAITING_FOR_AUTHORITATIVE_DECISION'}:
            gate = gate or {'outcome':'core_control_wait','reason':state['lifecycle_state']}
        cli.save_state(config, state)
        cli.cleanup_consumed_inputs(consumed)
    return {'permitted': gate is None, 'core_outcome': outcome,
            'core_state_path': str(cli.state_path(config)),
            'core_objective': state.get('current_objective'), 'operator_context': context}
