"""Produce a measurement table from frozen corpus, executor receipts, and evaluations.

P2P arm is NOT_AVAILABLE until live peers supply real assets and receipts.
qualification_labels state what each row's data source actually is so callers
know exactly what claim each number supports.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

REPORT_SCHEMA = 'urace-measurement-report-v1'

_NOT_AVAILABLE = 'NOT_AVAILABLE'
_NOT_RUN = 'NOT_RUN'


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _load_evaluations(evaluations_dir: Path | None) -> dict[str, dict]:
    if not evaluations_dir or not Path(evaluations_dir).exists():
        return {}
    out: dict[str, dict] = {}
    for path in sorted(Path(evaluations_dir).glob('eval_*.json')):
        ev = _load_json(path)
        if isinstance(ev, dict) and isinstance(ev.get('task_id'), str):
            out[ev['task_id']] = ev
    return out


def build_report(
    corpus_dir: Path,
    receipts_dir: Path | None = None,
    evaluations_dir: Path | None = None,
    p2p_receipts_dir: Path | None = None,
    *,
    urace_ledger_entries: list[dict] | None = None,
) -> dict:
    """Build the measurement report.

    executor receipts_dir  — executor_receipt_*.json files
    p2p_receipts_dir       — p2p_receipt_*.json files (integration steps)
    evaluations_dir        — eval_*.json files with accepted + value_score per arm
    urace_ledger_entries   — list of {task_id, executor_urace_units, p2p_urace_units}

    P2P provider USD = sum of integration step receipts (asset_analysis,
    context_adaptation, validation, gap_fill). Zero when no calls happen.
    P2P URACE units are reported separately; no USD conversion is applied.
    """
    from measurement_corpus import load_corpus
    from executor_receipt import load_receipts, load_p2p_receipts

    corpus = load_corpus(corpus_dir)

    receipts: list[dict] = []
    if receipts_dir and Path(receipts_dir).exists():
        receipts = load_receipts(Path(receipts_dir))
    receipt_map = {r['task_id']: r for r in receipts}

    p2p_step_map: dict[str, list[dict]] = {}
    if p2p_receipts_dir and Path(p2p_receipts_dir).exists():
        p2p_step_map = load_p2p_receipts(Path(p2p_receipts_dir))

    eval_map = _load_evaluations(evaluations_dir)

    ledger_map: dict[str, dict] = {}
    for entry in (urace_ledger_entries or []):
        if isinstance(entry, dict) and isinstance(entry.get('task_id'), str):
            ledger_map[entry['task_id']] = entry

    p2p_dir_provided = bool(p2p_receipts_dir and Path(p2p_receipts_dir).exists())

    per_task: list[dict] = []
    for task in corpus:
        tid = task['task_id']
        receipt = receipt_map.get(tid)
        evaluation = eval_map.get(tid)
        ledger = ledger_map.get(tid)
        p2p_steps = p2p_step_map.get(tid, [])

        if p2p_dir_provided:
            # Zero steps = clean pair (no provider calls); still a real measurement.
            p2p_provider_usd: float | str = round(
                sum(s['usd_observed'] for s in p2p_steps), 10
            )
            p2p_api_tokens: int | str = sum(
                s.get('input_tokens', 0) + s.get('output_tokens', 0) for s in p2p_steps
            )
            p2p_status = 'PARTIAL' if p2p_steps else 'ZERO_CALLS'
            p2p_usd_source: str = 'provider_published_rate'
        else:
            p2p_provider_usd = _NOT_AVAILABLE
            p2p_api_tokens = _NOT_AVAILABLE
            p2p_status = _NOT_AVAILABLE
            p2p_usd_source = _NOT_AVAILABLE

        per_task.append({
            'task_id': tid,
            'task_sha256': task['task_sha256'],
            'executor': {
                'accepted': evaluation.get('executor_accepted') if evaluation else _NOT_RUN,
                'value_score': evaluation.get('executor_value_score') if evaluation else _NOT_RUN,
                'usd_observed': receipt['usd_observed'] if receipt else _NOT_RUN,
                'usd_source': 'provider_published_rate' if receipt else _NOT_RUN,
                'api_tokens': (
                    receipt.get('input_tokens', 0) + receipt.get('output_tokens', 0)
                    if receipt else _NOT_RUN
                ),
                'urace_units': ledger.get('executor_urace_units') if ledger else _NOT_RUN,
            },
            'p2p': {
                'status': p2p_status,
                'accepted': evaluation.get('p2p_accepted') if evaluation else _NOT_RUN,
                'value_score': evaluation.get('p2p_value_score') if evaluation else _NOT_RUN,
                'provider_usd': p2p_provider_usd,
                'usd_source': p2p_usd_source,
                'api_tokens': p2p_api_tokens,
                'urace_units': ledger.get('p2p_urace_units') if ledger else _NOT_RUN,
                'integration_steps': [s['p2p_step'] for s in p2p_steps],
            },
        })

    # --- aggregate ---
    total = len(per_task)
    has_evals = bool(eval_map)
    has_exec_receipts = bool(receipt_map)
    has_p2p_receipts = bool(p2p_step_map)

    accepted_exec = sum(1 for r in per_task if r['executor']['accepted'] is True)
    accepted_p2p = sum(1 for r in per_task if r['p2p']['accepted'] is True)

    exec_value_scores = [
        r['executor']['value_score'] for r in per_task
        if isinstance(r['executor']['value_score'], (int, float))
    ]
    p2p_value_scores = [
        r['p2p']['value_score'] for r in per_task
        if isinstance(r['p2p']['value_score'], (int, float))
    ]
    exec_usd = [
        r['executor']['usd_observed'] for r in per_task
        if isinstance(r['executor']['usd_observed'], (int, float))
    ]
    p2p_usd = [
        r['p2p']['provider_usd'] for r in per_task
        if isinstance(r['p2p']['provider_usd'], (int, float))
    ]
    exec_tokens = [
        r['executor']['api_tokens'] for r in per_task
        if isinstance(r['executor']['api_tokens'], int)
    ]
    p2p_tokens = [
        r['p2p']['api_tokens'] for r in per_task
        if isinstance(r['p2p']['api_tokens'], int)
    ]
    exec_urace = [
        r['executor']['urace_units'] for r in per_task
        if isinstance(r['executor']['urace_units'], (int, float))
    ]
    p2p_urace = [
        r['p2p']['urace_units'] for r in per_task
        if isinstance(r['p2p']['urace_units'], (int, float))
    ]

    # comparison is valid only when both arms have complete receipts + evals
    both_arms_complete = has_exec_receipts and has_p2p_receipts and has_evals
    exec_usd_total = round(sum(exec_usd), 6) if exec_usd else None
    p2p_usd_total = round(sum(p2p_usd), 6) if p2p_usd else None
    usd_diff = (
        round(p2p_usd_total - exec_usd_total, 6)
        if exec_usd_total is not None and p2p_usd_total is not None else None
    )

    if not both_arms_complete:
        blocked_reason = (
            'P2P arm NOT_AVAILABLE — requires live peer supply with real receipts'
            if not has_p2p_receipts
            else 'Evaluations incomplete — both arms require accepted + value_score per task'
        )
    elif usd_diff is not None and usd_diff >= 0:
        blocked_reason = 'P2P provider USD >= executor USD; no savings to claim'
    else:
        blocked_reason = (
            'URACE unit → USD conversion not established; '
            'report P2P cost as usd_provider + urace_units separately'
        )

    comparison_valid = both_arms_complete and usd_diff is not None and usd_diff < 0

    summary_table = {
        'acceptance': {
            'executor': f'{accepted_exec}/{total}' if has_evals else _NOT_RUN,
            'p2p': f'{accepted_p2p}/{total}' if has_evals and has_p2p_receipts else _NOT_AVAILABLE,
            'qualification': 'REAL' if has_evals else _NOT_RUN,
            'note': 'Real tasks + blind independent evaluator',
        },
        'mean_value_score': {
            'executor': round(statistics.mean(exec_value_scores), 4) if exec_value_scores else _NOT_RUN,
            'p2p': round(statistics.mean(p2p_value_scores), 4) if p2p_value_scores else _NOT_AVAILABLE,
            'qualification': 'REAL' if exec_value_scores else _NOT_RUN,
            'note': 'Real outputs scored by frozen rubric',
        },
        'api_tokens_total': {
            'executor': sum(exec_tokens) if exec_tokens else _NOT_RUN,
            'p2p': sum(p2p_tokens) if p2p_tokens else _NOT_AVAILABLE,
            'qualification': 'REAL' if exec_tokens else _NOT_RUN,
            'note': 'Actual observed token counts; P2P counts integration steps only',
        },
        'urace_units_total': {
            'executor': sum(exec_urace) if exec_urace else _NOT_RUN,
            'p2p': sum(p2p_urace) if p2p_urace else _NOT_AVAILABLE,
            'qualification': 'REAL' if exec_urace or p2p_urace else _NOT_RUN,
            'note': 'Actual URACE ledger deductions; not converted to USD',
        },
        'provider_usd_total': {
            'executor': exec_usd_total if exec_usd_total is not None else _NOT_RUN,
            'p2p': p2p_usd_total if p2p_usd_total is not None else _NOT_AVAILABLE,
            'p2p_note': (
                'Integration steps only (asset_analysis, context_adaptation, '
                'validation, gap_fill). Zero if no provider calls during integration.'
            ),
            'qualification': (
                'PROVIDER_RATE' if exec_usd_total is not None else _NOT_RUN
            ),
            'usd_source': 'provider_published_rate',
            'note': (
                'Published per-token price, not reconciled invoice. '
                'Reconcile against provider billing for a defensible cost claim.'
            ),
        },
        'usd_difference': {
            'value': usd_diff if usd_diff is not None else _NOT_AVAILABLE,
            'interpretation': (
                f'P2P integration saves ${abs(usd_diff):.6f} in provider calls'
                if usd_diff is not None and usd_diff < 0
                else 'Not computable' if usd_diff is None
                else 'No provider-USD savings'
            ),
            'qualification': 'PROVIDER_RATE' if usd_diff is not None else _NOT_AVAILABLE,
        },
        'comparison_valid': comparison_valid,
        'comparison_blocked_reason': blocked_reason if not comparison_valid else None,
        'qualified_total_cost_savings': False,
        'qualified_note': (
            'qualified_total_cost_savings requires: both arms complete, '
            'P2P provider USD < executor USD, and URACE unit → USD rate established.'
        ),
    }

    return {
        'schema': REPORT_SCHEMA,
        'task_count': total,
        'summary_table': summary_table,
        'per_task': per_task,
        'qualification_note': (
            'REAL = real tasks + real API calls + independent evaluation. '
            'PROVIDER_RATE = real tokens × published rate; not an invoice. '
            'NOT_AVAILABLE = P2P arm requires live network peers. '
            'NOT_RUN = data not yet collected. '
            'P2P provider_usd covers integration steps only; URACE units are separate.'
        ),
    }


def print_table(report: dict) -> None:
    t = report['summary_table']
    header = f"{'Measure':<28} {'Executor':<22} {'P2P':<22} {'Qualification'}"
    print()
    print(header)
    print('-' * len(header))
    skip = {
        'comparison_valid', 'comparison_blocked_reason',
        'qualified_total_cost_savings', 'qualified_note', 'usd_difference',
    }
    for key, row in t.items():
        if key in skip or not isinstance(row, dict) or 'executor' not in row:
            continue
        print(f'{key:<28} {str(row["executor"]):<22} {str(row["p2p"]):<22} {row.get("qualification", "")}')
    diff = t.get('usd_difference', {})
    if isinstance(diff, dict) and diff.get('value') != _NOT_AVAILABLE:
        print(f"{'usd_difference':<28} {str(diff.get('value', '')):<22} {'':22} {diff.get('qualification', '')}")
    print()
    print(f'comparison_valid:             {t["comparison_valid"]}')
    print(f'qualified_total_cost_savings: {t["qualified_total_cost_savings"]}')
    if not t['comparison_valid']:
        print(f'blocked: {t["comparison_blocked_reason"]}')
    print()
    print(report.get('qualification_note', ''))
    print()


def write_report(report: dict, output_path: Path) -> None:
    Path(output_path).write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding='utf-8'
    )
