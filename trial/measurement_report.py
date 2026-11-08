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
    *,
    urace_ledger_entries: list[dict] | None = None,
) -> dict:
    """Build the measurement report.

    Missing P2P data produces NOT_AVAILABLE cells. The returned dict has:
      schema, task_count, summary_table, per_task, qualification_note.
    """
    from measurement_corpus import load_corpus
    from executor_receipt import load_receipts

    corpus = load_corpus(corpus_dir)

    receipts: list[dict] = []
    if receipts_dir and Path(receipts_dir).exists():
        receipts = load_receipts(Path(receipts_dir))
    receipt_map = {r['task_id']: r for r in receipts}

    eval_map = _load_evaluations(evaluations_dir)

    ledger_map: dict[str, dict] = {}
    for entry in (urace_ledger_entries or []):
        if isinstance(entry, dict) and isinstance(entry.get('task_id'), str):
            ledger_map[entry['task_id']] = entry

    per_task: list[dict] = []
    for task in corpus:
        tid = task['task_id']
        receipt = receipt_map.get(tid)
        evaluation = eval_map.get(tid)
        ledger = ledger_map.get(tid)

        per_task.append({
            'task_id': tid,
            'task_sha256': task['task_sha256'],
            'executor': {
                'accepted': evaluation.get('executor_accepted') if evaluation else _NOT_RUN,
                'value_score': evaluation.get('executor_value_score') if evaluation else _NOT_RUN,
                'usd_observed': receipt['usd_observed'] if receipt else _NOT_RUN,
                'usd_source': 'provider_published_rate' if receipt else _NOT_RUN,
                'api_tokens': (
                    (receipt.get('input_tokens', 0) + receipt.get('output_tokens', 0))
                    if receipt else _NOT_RUN
                ),
                'urace_units': ledger.get('executor_urace_units') if ledger else _NOT_RUN,
            },
            'p2p': {
                'status': _NOT_AVAILABLE,
                'reason': 'no live peer supply',
            },
        })

    # --- aggregate executor arm ---
    accepted_count = sum(
        1 for r in per_task
        if r['executor']['accepted'] is True
    )
    total = len(per_task)

    value_scores = [
        r['executor']['value_score'] for r in per_task
        if isinstance(r['executor']['value_score'], (int, float))
    ]
    usd_values = [
        r['executor']['usd_observed'] for r in per_task
        if isinstance(r['executor']['usd_observed'], (int, float))
    ]
    api_token_values = [
        r['executor']['api_tokens'] for r in per_task
        if isinstance(r['executor']['api_tokens'], int)
    ]
    urace_unit_values = [
        r['executor']['urace_units'] for r in per_task
        if isinstance(r['executor']['urace_units'], (int, float))
    ]

    has_evals = bool(eval_map)
    has_receipts = bool(receipt_map)
    has_ledger = bool(ledger_map)

    summary_table = {
        'acceptance': {
            'executor': f'{accepted_count}/{total}' if has_evals else _NOT_RUN,
            'p2p': _NOT_AVAILABLE,
            'qualification': 'REAL' if has_evals else _NOT_RUN,
            'note': 'Real tasks + blind independent evaluator',
        },
        'mean_value_score': {
            'executor': round(statistics.mean(value_scores), 4) if value_scores else _NOT_RUN,
            'p2p': _NOT_AVAILABLE,
            'qualification': 'REAL' if value_scores else _NOT_RUN,
            'note': 'Real outputs scored by frozen rubric',
        },
        'api_tokens_total': {
            'executor': sum(api_token_values) if api_token_values else _NOT_RUN,
            'p2p': _NOT_AVAILABLE,
            'qualification': 'REAL' if api_token_values else _NOT_RUN,
            'note': 'Actual observed token counts from provider usage objects',
        },
        'urace_units_total': {
            'executor': sum(urace_unit_values) if urace_unit_values else _NOT_RUN,
            'p2p': _NOT_AVAILABLE,
            'qualification': 'REAL' if urace_unit_values else _NOT_RUN,
            'note': 'Actual URACE ledger deductions',
        },
        'usd_total': {
            'executor': round(sum(usd_values), 6) if usd_values else _NOT_RUN,
            'p2p': _NOT_AVAILABLE,
            'qualification': 'PROVIDER_RATE' if usd_values else _NOT_RUN,
            'usd_source': 'provider_published_rate',
            'note': (
                'Published per-token price, not reconciled invoice. '
                'Reconcile against provider billing statements for a defensible cost claim.'
            ),
        },
        'comparison_valid': False,
        'comparison_blocked_reason': (
            'P2P arm NOT_AVAILABLE — requires live peer supply with real receipts'
        ),
        'qualified_total_cost_savings': False,
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
            'NOT_RUN = data not yet collected.'
        ),
    }


def print_table(report: dict) -> None:
    t = report['summary_table']
    header = f"{'Measure':<28} {'Executor':<22} {'P2P':<18} {'Qualification'}"
    print()
    print(header)
    print('-' * len(header))
    skip = {'comparison_valid', 'comparison_blocked_reason', 'qualified_total_cost_savings'}
    for key, row in t.items():
        if key in skip or not isinstance(row, dict) or 'executor' not in row:
            continue
        print(f'{key:<28} {str(row["executor"]):<22} {str(row["p2p"]):<18} {row.get("qualification", "")}')
    print()
    print(f'comparison_valid:            {t["comparison_valid"]}')
    print(f'qualified_total_cost_savings: {t["qualified_total_cost_savings"]}')
    print(f'reason: {t["comparison_blocked_reason"]}')
    print()
    print(report.get('qualification_note', ''))
    print()


def write_report(report: dict, output_path: Path) -> None:
    Path(output_path).write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding='utf-8'
    )
