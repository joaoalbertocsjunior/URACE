"""Measure raw-request vs classified-intent P2P retrieval on labeled JSONL cases.

No built-in cases or labels are supplied: the benchmark refuses to invent an
empirical retrieval score. Dataset review metadata is self-reported and shown
as such; this tool measures ranking only, not accepted work or cost.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent / 'runtime'
sys.path.insert(0, str(RUNTIME))

from urace.p2p_matching import benchmark


def run(path: str | Path) -> dict:
    dataset = Path(path).expanduser().absolute()
    if dataset.is_symlink() or not dataset.is_file():
        raise ValueError('Dataset must be a regular file')
    dataset = dataset.resolve(strict=True)
    raw = dataset.read_bytes()
    lines = raw.decode('utf-8').splitlines()
    if len(lines) < 2:
        raise ValueError('Dataset needs a metadata header and at least one labeled case')
    header = json.loads(lines[0])
    cases = [json.loads(line) for line in lines[1:] if line.strip()]
    if header.get('schema') != 'urace-p2p-retrieval-dataset-v1':
        raise ValueError('Unknown dataset schema')
    if type(header.get('case_count')) is not int or header.get('case_count') != len(cases):
        raise ValueError('Dataset header case_count does not match the rows')
    ids = [case.get('case_id') for case in cases]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('Every case needs a unique case_id')
    result = benchmark(cases)
    reviewed = (header.get('split') == 'held_out'
                and header.get('dataset_kind') == 'reviewed_real_work'
                and type(header.get('independent_reviewers')) is int
                and header['independent_reviewers'] >= 2
                and header.get('disagreements_adjudicated') is True
                and isinstance(header.get('source_description'), str)
                and bool(header['source_description'].strip()))
    return {**result,
            'status': 'HELD_OUT_RETRIEVAL_DIAGNOSTIC' if reviewed else 'NONQUALIFYING_DATASET_DIAGNOSTIC',
            'dataset_sha256': hashlib.sha256(raw).hexdigest(),
            'dataset_metadata': {key: header.get(key) for key in
                                 ('dataset_kind', 'split', 'independent_reviewers',
                                  'disagreements_adjudicated', 'source_description')},
            'review_provenance_self_reported': True,
            'qualified_real_task_value_or_cost_claim': False}


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({'status': 'error', 'error': 'usage: p2p_retrieval_benchmark.py DATASET.jsonl'}))
        return 2
    try:
        print(json.dumps(run(sys.argv[1]), sort_keys=True, separators=(',', ':')))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
