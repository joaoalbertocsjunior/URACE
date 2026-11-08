"""Tests for measurement_report: table structure, qualification labels, P2P integration."""
import json
import pytest
from pathlib import Path

from measurement_corpus import freeze_corpus
from executor_receipt import capture_receipt, capture_p2p_receipt
from measurement_report import REPORT_SCHEMA, build_report, print_table, write_report

KNOWN_SHA = 'a' * 64


def _make_corpus(tmp_path: Path, n: int = 3) -> Path:
    corpus_dir = tmp_path / 'corpus'
    tasks = [
        {
            'task_id': f'T{i:03d}',
            'input': f'Task input {i}',
            'acceptance_criteria': f'Criteria {i}',
            'value_rubric': f'Rubric {i}',
        }
        for i in range(1, n + 1)
    ]
    freeze_corpus(tasks, corpus_dir, product_id='prod1', source_ref='git:abc')
    return corpus_dir


def _make_exec_receipts(tmp_path: Path, task_ids: list[str], *, tokens: tuple = (5000, 1500)) -> Path:
    receipts_dir = tmp_path / 'receipts'
    for tid in task_ids:
        capture_receipt(tid, KNOWN_SHA, 'claude-sonnet-4-6', tokens[0], tokens[1], output_dir=receipts_dir)
    return receipts_dir


# Realistic per-step token midpoints (from observed ranges):
#   asset_analysis:     300–800 in,  100–200 out
#   context_adaptation: 800–2000 in, 200–600 out
#   validation:         500–1500 in, 100–300 out
_P2P_STEP_TOKENS = {
    'asset_analysis':     (550, 150),
    'context_adaptation': (1200, 400),
    'validation':         (900, 200),
    'gap_fill':           (5000, 1500),  # fallback: same scale as executor
}


def _make_p2p_receipts(tmp_path: Path, task_ids: list[str], steps: list[str] | None = None) -> Path:
    """Realistic P2P distribution when steps is None:
      ~50% zero-call (dir present, no receipts — ZERO_CALLS)
      ~35% single-step context_adaptation
      ~15% full-adaptation (asset_analysis + context_adaptation + validation)
    When steps is given, use those steps for every task_id (for targeted tests).
    """
    p2p_dir = tmp_path / 'p2p_receipts'
    if steps is not None:
        for tid in task_ids:
            for step in steps:
                in_tok, out_tok = _P2P_STEP_TOKENS.get(step, (550, 150))
                capture_p2p_receipt(
                    tid, KNOWN_SHA, step, 'claude-sonnet-4-6', in_tok, out_tok, output_dir=p2p_dir
                )
        return p2p_dir

    n = len(task_ids)
    n_zero = round(n * 0.50)
    n_full = round(n * 0.15)
    n_single = n - n_zero - n_full

    single_ids = task_ids[n_zero: n_zero + n_single]
    full_ids = task_ids[n_zero + n_single:]

    for tid in single_ids:
        in_tok, out_tok = _P2P_STEP_TOKENS['context_adaptation']
        capture_p2p_receipt(
            tid, KNOWN_SHA, 'context_adaptation', 'claude-sonnet-4-6', in_tok, out_tok, output_dir=p2p_dir
        )
    for tid in full_ids:
        for step in ('asset_analysis', 'context_adaptation', 'validation'):
            in_tok, out_tok = _P2P_STEP_TOKENS[step]
            capture_p2p_receipt(
                tid, KNOWN_SHA, step, 'claude-sonnet-4-6', in_tok, out_tok, output_dir=p2p_dir
            )
    return p2p_dir


def _make_evaluations(
    tmp_path: Path, task_ids: list[str], *,
    exec_accepted: bool = True, p2p_accepted: bool = True,
) -> Path:
    evals_dir = tmp_path / 'evals'
    evals_dir.mkdir(exist_ok=True)
    for tid in task_ids:
        ev = {
            'task_id': tid,
            'executor_accepted': exec_accepted,
            'executor_value_score': 0.78,
            'p2p_accepted': p2p_accepted,
            'p2p_value_score': 0.82,
        }
        (evals_dir / f'eval_{tid}.json').write_text(json.dumps(ev), encoding='utf-8')
    return evals_dir


# --- schema and structure ---

def test_report_schema_present(tmp_path):
    report = build_report(_make_corpus(tmp_path))
    assert report['schema'] == REPORT_SCHEMA
    assert report['task_count'] == 3


def test_qualification_note_present(tmp_path):
    report = build_report(_make_corpus(tmp_path))
    assert 'PROVIDER_RATE' in report['qualification_note']
    assert 'NOT_AVAILABLE' in report['qualification_note']
    assert 'integration steps' in report['qualification_note']


# --- no data produces NOT_RUN / NOT_AVAILABLE ---

def test_no_receipts_produces_not_run(tmp_path):
    report = build_report(_make_corpus(tmp_path))
    cell = report['summary_table']['provider_usd_total']
    assert cell['executor'] == 'NOT_RUN'
    assert cell['qualification'] == 'NOT_RUN'


def test_no_p2p_receipts_p2p_status_not_available(tmp_path):
    report = build_report(_make_corpus(tmp_path))
    for row in report['per_task']:
        assert row['p2p']['status'] == 'NOT_AVAILABLE'
    for key, cell in report['summary_table'].items():
        if isinstance(cell, dict) and 'p2p' in cell:
            assert cell['p2p'] == 'NOT_AVAILABLE'


# --- executor arm with receipts ---

def test_executor_receipts_produce_provider_rate(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir)
    cell = report['summary_table']['provider_usd_total']
    assert cell['qualification'] == 'PROVIDER_RATE'
    assert cell['usd_source'] == 'provider_published_rate'
    assert isinstance(cell['executor'], float) and cell['executor'] > 0


def test_evaluations_produce_real_qualification(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003'])
    evals_dir = _make_evaluations(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, evals_dir)
    assert report['summary_table']['acceptance']['qualification'] == 'REAL'
    assert report['summary_table']['acceptance']['executor'] == '3/3'
    assert report['summary_table']['mean_value_score']['executor'] == pytest.approx(0.78)


def test_partial_evaluations_accepted_count(tmp_path):
    corpus_dir = _make_corpus(tmp_path, n=4)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003', 'T004'])
    evals_dir = _make_evaluations(tmp_path, ['T001', 'T002'])
    report = build_report(corpus_dir, receipts_dir, evals_dir)
    assert report['summary_table']['acceptance']['executor'] == '2/4'


# --- P2P integration receipts ---

def test_p2p_receipts_populate_provider_usd(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003'])
    p2p_dir = _make_p2p_receipts(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, None, p2p_dir)
    cell = report['summary_table']['provider_usd_total']
    assert isinstance(cell['p2p'], float)
    assert cell['p2p'] > 0


def test_p2p_provider_usd_less_than_executor(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003'], tokens=(5000, 1500))
    p2p_dir = _make_p2p_receipts(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, None, p2p_dir)
    cell = report['summary_table']['provider_usd_total']
    assert cell['p2p'] < cell['executor']


def test_usd_difference_negative_when_p2p_cheaper(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003'], tokens=(5000, 1500))
    p2p_dir = _make_p2p_receipts(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, None, p2p_dir)
    diff = report['summary_table']['usd_difference']
    assert isinstance(diff['value'], float)
    assert diff['value'] < 0
    assert diff['qualification'] == 'PROVIDER_RATE'


def test_multiple_p2p_steps_summed_per_task(tmp_path):
    corpus_dir = _make_corpus(tmp_path, n=1)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001'], tokens=(5000, 1500))
    p2p_dir = _make_p2p_receipts(
        tmp_path, ['T001'], steps=['asset_analysis', 'context_adaptation', 'validation']
    )
    report = build_report(corpus_dir, receipts_dir, None, p2p_dir)
    task_row = report['per_task'][0]
    assert task_row['p2p']['status'] == 'PARTIAL'
    assert len(task_row['p2p']['integration_steps']) == 3
    assert isinstance(task_row['p2p']['provider_usd'], float)


def test_p2p_zero_calls_scenario(tmp_path):
    # Clean P2P pair: no integration steps → provider_usd = NOT_AVAILABLE
    corpus_dir = _make_corpus(tmp_path, n=1)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001'])
    # No p2p_receipts_dir provided
    report = build_report(corpus_dir, receipts_dir)
    task_row = report['per_task'][0]
    assert task_row['p2p']['status'] == 'NOT_AVAILABLE'
    assert task_row['p2p']['provider_usd'] == 'NOT_AVAILABLE'


# --- comparison and savings flags ---

def test_qualified_total_cost_savings_always_false(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003'])
    p2p_dir = _make_p2p_receipts(tmp_path, ['T001', 'T002', 'T003'])
    evals_dir = _make_evaluations(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, evals_dir, p2p_dir)
    # Even with P2P cheaper, qualified_total_cost_savings is False
    # because URACE unit → USD conversion not established
    assert report['summary_table']['qualified_total_cost_savings'] is False


def test_comparison_valid_when_both_arms_complete_and_p2p_cheaper(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003'], tokens=(5000, 1500))
    p2p_dir = _make_p2p_receipts(tmp_path, ['T001', 'T002', 'T003'])
    evals_dir = _make_evaluations(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, evals_dir, p2p_dir)
    assert report['summary_table']['comparison_valid'] is True


# --- URACE ledger ---

def test_urace_ledger_both_arms(tmp_path):
    corpus_dir = _make_corpus(tmp_path, n=2)
    ledger = [
        {'task_id': 'T001', 'executor_urace_units': 100, 'p2p_urace_units': 40},
        {'task_id': 'T002', 'executor_urace_units': 100, 'p2p_urace_units': 40},
    ]
    report = build_report(corpus_dir, urace_ledger_entries=ledger)
    units = report['summary_table']['urace_units_total']
    assert units['executor'] == 200
    assert units['p2p'] == 80
    assert units['qualification'] == 'REAL'


# --- output ---

def test_print_table_runs_without_error(tmp_path, capsys):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_exec_receipts(tmp_path, ['T001', 'T002', 'T003'], tokens=(5000, 1500))
    p2p_dir = _make_p2p_receipts(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, None, p2p_dir)
    print_table(report)
    out = capsys.readouterr().out
    assert 'qualified_total_cost_savings' in out


def test_write_report_produces_valid_json(tmp_path):
    report = build_report(_make_corpus(tmp_path))
    out_path = tmp_path / 'report.json'
    write_report(report, out_path)
    assert json.loads(out_path.read_text())['schema'] == REPORT_SCHEMA


# --- realistic 30-task cohort bounds ---

def test_realistic_30_task_p2p_within_expected_bounds(tmp_path):
    """P2P $Y total must be 5–25% of executor $X for a 30-task cohort.

    Distribution: ~50% zero-call, ~35% single-step, ~15% full-adaptation.
    Executor: claude-sonnet-4-6 at 5000 input + 1500 output per task.
    """
    n = 30
    task_ids = [f'T{i:03d}' for i in range(1, n + 1)]
    corpus_dir = _make_corpus(tmp_path, n=n)
    receipts_dir = _make_exec_receipts(tmp_path, task_ids, tokens=(5000, 1500))
    p2p_dir = _make_p2p_receipts(tmp_path, task_ids)
    report = build_report(corpus_dir, receipts_dir, None, p2p_dir)

    cell = report['summary_table']['provider_usd_total']
    exec_usd = cell['executor']
    p2p_usd = cell['p2p']

    assert isinstance(exec_usd, float) and exec_usd > 0
    assert isinstance(p2p_usd, float) and p2p_usd >= 0

    ratio = p2p_usd / exec_usd
    assert 0.05 <= ratio <= 0.25, (
        f'P2P $Y ({p2p_usd:.4f}) is {ratio:.1%} of executor $X ({exec_usd:.4f}); '
        f'expected 5–25%'
    )
