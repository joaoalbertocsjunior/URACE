"""Tests for measurement_report: table structure, qualification labels, P2P NOT_AVAILABLE."""
import json
import pytest
from pathlib import Path

from measurement_corpus import freeze_corpus
from executor_receipt import capture_receipt
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


def _make_receipts(tmp_path: Path, task_ids: list[str]) -> Path:
    receipts_dir = tmp_path / 'receipts'
    for tid in task_ids:
        # sha256 must be loaded from corpus; use fixture sha for tests
        capture_receipt(
            tid, KNOWN_SHA, 'claude-sonnet-4-6', 1000, 500, output_dir=receipts_dir
        )
    return receipts_dir


def _make_evaluations(tmp_path: Path, task_ids: list[str], *, accepted: bool = True) -> Path:
    evals_dir = tmp_path / 'evals'
    evals_dir.mkdir()
    for tid in task_ids:
        ev = {
            'task_id': tid,
            'executor_accepted': accepted,
            'executor_value_score': 0.80,
        }
        (evals_dir / f'eval_{tid}.json').write_text(json.dumps(ev), encoding='utf-8')
    return evals_dir


def test_report_schema_present(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    report = build_report(corpus_dir)
    assert report['schema'] == REPORT_SCHEMA
    assert report['task_count'] == 3


def test_p2p_always_not_available(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    report = build_report(corpus_dir)
    for row in report['per_task']:
        assert row['p2p']['status'] == 'NOT_AVAILABLE'
    for key, cell in report['summary_table'].items():
        if isinstance(cell, dict) and 'p2p' in cell:
            assert cell['p2p'] == 'NOT_AVAILABLE'


def test_no_receipts_produces_not_run(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    report = build_report(corpus_dir)
    usd_cell = report['summary_table']['usd_total']
    assert usd_cell['executor'] == 'NOT_RUN'
    assert usd_cell['qualification'] == 'NOT_RUN'


def test_receipts_produce_provider_rate_qualification(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_receipts(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir)
    usd_cell = report['summary_table']['usd_total']
    assert usd_cell['qualification'] == 'PROVIDER_RATE'
    assert usd_cell['usd_source'] == 'provider_published_rate'
    assert isinstance(usd_cell['executor'], float)
    assert usd_cell['executor'] > 0


def test_evaluations_produce_real_qualification(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_receipts(tmp_path, ['T001', 'T002', 'T003'])
    evals_dir = _make_evaluations(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, evals_dir)
    acc = report['summary_table']['acceptance']
    assert acc['qualification'] == 'REAL'
    assert acc['executor'] == '3/3'
    score = report['summary_table']['mean_value_score']
    assert score['qualification'] == 'REAL'
    assert score['executor'] == pytest.approx(0.80)


def test_qualified_total_cost_savings_always_false(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_receipts(tmp_path, ['T001', 'T002', 'T003'])
    evals_dir = _make_evaluations(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir, evals_dir)
    assert report['summary_table']['qualified_total_cost_savings'] is False
    assert report['summary_table']['comparison_valid'] is False


def test_partial_evaluations_accepted_count(tmp_path):
    corpus_dir = _make_corpus(tmp_path, n=4)
    receipts_dir = _make_receipts(tmp_path, ['T001', 'T002', 'T003', 'T004'])
    evals_dir = _make_evaluations(tmp_path, ['T001', 'T002'], accepted=True)
    # T003, T004 have no eval
    report = build_report(corpus_dir, receipts_dir, evals_dir)
    acc = report['summary_table']['acceptance']
    # Only T001 and T002 have accepted=True; T003/T004 have NOT_RUN
    assert acc['executor'] == '2/4'


def test_urace_ledger_entries_aggregated(tmp_path):
    corpus_dir = _make_corpus(tmp_path, n=2)
    ledger = [
        {'task_id': 'T001', 'executor_urace_units': 150},
        {'task_id': 'T002', 'executor_urace_units': 100},
    ]
    report = build_report(corpus_dir, urace_ledger_entries=ledger)
    units = report['summary_table']['urace_units_total']
    assert units['executor'] == 250
    assert units['qualification'] == 'REAL'


def test_print_table_runs_without_error(tmp_path, capsys):
    corpus_dir = _make_corpus(tmp_path)
    receipts_dir = _make_receipts(tmp_path, ['T001', 'T002', 'T003'])
    report = build_report(corpus_dir, receipts_dir)
    print_table(report)
    out = capsys.readouterr().out
    assert 'NOT_AVAILABLE' in out
    assert 'qualified_total_cost_savings' in out


def test_write_report_produces_valid_json(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    report = build_report(corpus_dir)
    out_path = tmp_path / 'report.json'
    write_report(report, out_path)
    loaded = json.loads(out_path.read_text())
    assert loaded['schema'] == REPORT_SCHEMA


def test_qualification_note_present(tmp_path):
    corpus_dir = _make_corpus(tmp_path)
    report = build_report(corpus_dir)
    assert 'qualification_note' in report
    assert 'PROVIDER_RATE' in report['qualification_note']
    assert 'NOT_AVAILABLE' in report['qualification_note']
