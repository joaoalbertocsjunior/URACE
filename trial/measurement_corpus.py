"""Freeze a measurement task corpus before either arm runs.

Tasks are immutable once an arm-started marker exists. Add tasks only before
the first arm executes; calling freeze_corpus after raises CorpusFrozenError.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Sequence

SCHEMA = 'urace-measurement-corpus-v1'
MANIFEST_SCHEMA = 'urace-corpus-manifest-v1'
ARM_MARKER = 'arm_started.marker'


class CorpusFrozenError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def freeze_corpus(
    tasks: Sequence[dict],
    output_dir: Path,
    *,
    product_id: str,
    source_ref: str,
) -> dict:
    """Write corpus.jsonl + corpus_manifest.json to output_dir.

    Raises CorpusFrozenError if any arm has already been marked as started.
    Each task requires: task_id (str), input (str), acceptance_criteria (str),
    value_rubric (str).
    """
    output_dir = Path(output_dir)
    if (output_dir / ARM_MARKER).exists():
        raise CorpusFrozenError('An arm has already started; corpus is immutable')
    if not tasks:
        raise ValueError('Task list must be non-empty')
    frozen_at = int(time.time())
    records: list[dict] = []
    seen: set[str] = set()
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f'Task {i} must be a dict')
        task_id = task.get('task_id')
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError(f'Task {i} missing non-empty task_id')
        if task_id in seen:
            raise ValueError(f'Duplicate task_id: {task_id!r}')
        seen.add(task_id)
        for field in ('input', 'acceptance_criteria', 'value_rubric'):
            if not isinstance(task.get(field), str) or not task[field].strip():
                raise ValueError(f'Task {task_id!r} missing non-empty {field!r}')
        task_sha256 = _canonical_sha256({
            'task_id': task_id,
            'input': task['input'],
            'acceptance_criteria': task['acceptance_criteria'],
            'value_rubric': task['value_rubric'],
        })
        records.append({
            'schema': SCHEMA,
            'task_id': task_id,
            'task_sha256': task_sha256,
            'input': task['input'],
            'acceptance_criteria': task['acceptance_criteria'],
            'value_rubric': task['value_rubric'],
            'product_id': product_id,
            'source_ref': source_ref,
            'frozen_at': frozen_at,
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = output_dir / 'corpus.jsonl'
    lines = [json.dumps(r, separators=(',', ':'), allow_nan=False) for r in records]
    corpus_bytes = ('\n'.join(lines) + '\n').encode()
    corpus_path.write_bytes(corpus_bytes)
    manifest = {
        'schema': MANIFEST_SCHEMA,
        'task_count': len(records),
        'corpus_sha256': _sha256(corpus_bytes),
        'product_id': product_id,
        'source_ref': source_ref,
        'frozen_at': frozen_at,
    }
    (output_dir / 'corpus_manifest.json').write_text(
        json.dumps(manifest, indent=2, allow_nan=False), encoding='utf-8'
    )
    return manifest


def load_corpus(corpus_dir: Path) -> list[dict]:
    """Load and integrity-verify the frozen corpus. Raises if modified."""
    corpus_dir = Path(corpus_dir)
    manifest_path = corpus_dir / 'corpus_manifest.json'
    corpus_path = corpus_dir / 'corpus.jsonl'
    if not manifest_path.exists() or not corpus_path.exists():
        raise FileNotFoundError('Corpus not found; call freeze_corpus first')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    actual_sha = _sha256(corpus_path.read_bytes())
    if actual_sha != manifest['corpus_sha256']:
        raise ValueError('Corpus file modified after freezing')
    records = [
        json.loads(line)
        for line in corpus_path.read_text(encoding='utf-8').splitlines()
        if line.strip()
    ]
    if len(records) != manifest['task_count']:
        raise ValueError('Corpus record count does not match manifest')
    return records


def mark_arm_started(corpus_dir: Path, arm: str) -> None:
    """Write arm_started.marker so freeze_corpus refuses further modifications."""
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.exists():
        raise FileNotFoundError('corpus_dir does not exist; freeze_corpus first')
    marker = corpus_dir / ARM_MARKER
    if not marker.exists():
        marker.write_text(
            json.dumps({'arm': arm, 'started_at': int(time.time())}, allow_nan=False),
            encoding='utf-8',
        )
