"""Tests for measurement_corpus: freeze, load, arm-marker, and integrity checks."""
import json
import time
import pytest
from pathlib import Path

from measurement_corpus import (
    ARM_MARKER, CorpusFrozenError, freeze_corpus, load_corpus, mark_arm_started,
)

TASK = {
    'task_id': 'T001',
    'input': 'Add retry logic to the HTTP client.',
    'acceptance_criteria': 'Three retries on 5xx with exponential backoff.',
    'value_rubric': 'Score 1.0 if retries fire; 0.0 otherwise.',
}


def _make_tasks(n: int = 3) -> list[dict]:
    return [
        {
            'task_id': f'T{i:03d}',
            'input': f'Input for task {i}',
            'acceptance_criteria': f'Criteria {i}',
            'value_rubric': f'Rubric {i}',
        }
        for i in range(1, n + 1)
    ]


def test_freeze_writes_corpus_and_manifest(tmp_path):
    tasks = _make_tasks()
    manifest = freeze_corpus(tasks, tmp_path, product_id='p1', source_ref='git:abc123')
    assert manifest['task_count'] == 3
    assert (tmp_path / 'corpus.jsonl').exists()
    assert (tmp_path / 'corpus_manifest.json').exists()


def test_load_corpus_round_trips(tmp_path):
    tasks = _make_tasks()
    freeze_corpus(tasks, tmp_path, product_id='p1', source_ref='git:abc123')
    loaded = load_corpus(tmp_path)
    assert len(loaded) == 3
    assert loaded[0]['task_id'] == 'T001'


def test_task_sha256_is_stable(tmp_path):
    tasks = [TASK]
    freeze_corpus(tasks, tmp_path, product_id='p1', source_ref='git:abc123')
    loaded = load_corpus(tmp_path)
    sha = loaded[0]['task_sha256']
    # Second freeze of same task yields identical hash
    tmp2 = tmp_path / 'b'
    freeze_corpus(tasks, tmp2, product_id='p1', source_ref='git:abc123')
    loaded2 = load_corpus(tmp2)
    assert loaded2[0]['task_sha256'] == sha


def test_modified_corpus_raises(tmp_path):
    freeze_corpus(_make_tasks(), tmp_path, product_id='p1', source_ref='r')
    corpus_path = tmp_path / 'corpus.jsonl'
    corpus_path.write_text(corpus_path.read_text() + 'x', encoding='utf-8')
    with pytest.raises(ValueError, match='modified after freezing'):
        load_corpus(tmp_path)


def test_freeze_raises_after_arm_started(tmp_path):
    freeze_corpus(_make_tasks(), tmp_path, product_id='p1', source_ref='r')
    mark_arm_started(tmp_path, 'direct_executor')
    with pytest.raises(CorpusFrozenError):
        freeze_corpus(_make_tasks(1), tmp_path, product_id='p1', source_ref='r')


def test_mark_arm_started_idempotent(tmp_path):
    freeze_corpus(_make_tasks(), tmp_path, product_id='p1', source_ref='r')
    mark_arm_started(tmp_path, 'direct_executor')
    t1 = json.loads((tmp_path / ARM_MARKER).read_text())['started_at']
    time.sleep(0.01)
    mark_arm_started(tmp_path, 'direct_executor')
    t2 = json.loads((tmp_path / ARM_MARKER).read_text())['started_at']
    assert t1 == t2  # second call is a no-op


def test_duplicate_task_ids_rejected(tmp_path):
    tasks = _make_tasks(2)
    tasks[1]['task_id'] = tasks[0]['task_id']
    with pytest.raises(ValueError, match='Duplicate task_id'):
        freeze_corpus(tasks, tmp_path, product_id='p1', source_ref='r')


def test_missing_field_rejected(tmp_path):
    task = {**TASK}
    del task['value_rubric']
    with pytest.raises(ValueError, match='value_rubric'):
        freeze_corpus([task], tmp_path, product_id='p1', source_ref='r')


def test_empty_task_list_rejected(tmp_path):
    with pytest.raises(ValueError, match='non-empty'):
        freeze_corpus([], tmp_path, product_id='p1', source_ref='r')


def test_load_corpus_missing_files_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_corpus(tmp_path)
