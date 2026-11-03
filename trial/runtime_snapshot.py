"""Per-snapshot summary artifacts for accepted runtime improvements."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os

SCHEMA = 'runtime-snapshot-v1'
SNAPSHOTS_DIR = 'runtime-snapshots'


def _sha(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(path)


def _load(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def create(base, change_spec, quality_evidence, *, snapshot_id=None):
    """
    Generate summary artifacts for an accepted runtime improvement.

    change_spec keys:
      rationale (str): why this change was proposed and accepted
      files_changed (list[str]): list of changed file paths
      diff (str): unified diff of the change
      engine_sha256_before (str): runtime identity before the change
      engine_sha256_after (str): runtime identity after the change
      proposer_provider (str): which provider proposed the change

    quality_evidence keys:
      baseline_score (float|None): executable benchmark score before change
      candidate_score (float|None): executable benchmark score after change
      gate_decision (dict): result from runtime_quality_gate.gate_decision()

    Returns the snapshot ID.
    """
    base = Path(base)
    if not isinstance(change_spec, dict):
        raise ValueError('change_spec must be a dict')
    if not isinstance(quality_evidence, dict):
        raise ValueError('quality_evidence must be a dict')

    required_change = ('rationale', 'files_changed', 'engine_sha256_before', 'engine_sha256_after')
    for key in required_change:
        if key not in change_spec:
            raise ValueError(f'change_spec missing required key: {key}')

    diff = change_spec.get('diff', '')
    change_type = change_spec.get('change_type', 'improvement')
    files_removed = list(change_spec.get('files_removed', []))
    if snapshot_id is None:
        snapshot_id = 'runtime-' + _sha((change_spec['engine_sha256_after'] + _now()).encode())[:24]

    snapshots_root = base / SNAPSHOTS_DIR / snapshot_id
    snapshots_root.mkdir(parents=True, exist_ok=True)

    baseline = quality_evidence.get('baseline_score')
    candidate = quality_evidence.get('candidate_score')
    delta = (candidate - baseline) if (
        type(baseline) in (int, float) and type(candidate) in (int, float)
    ) else None

    summary = {
        'schema': SCHEMA,
        'snapshot_id': snapshot_id,
        'recorded_at': _now(),
        'engine_sha256_before': change_spec['engine_sha256_before'],
        'engine_sha256_after': change_spec['engine_sha256_after'],
        'change_type': change_type,
        'files_changed': list(change_spec['files_changed']),
        'files_removed': files_removed,
        'proposer_provider': change_spec.get('proposer_provider'),
        'rationale': change_spec['rationale'],
        'quality': {
            'baseline_score': baseline,
            'candidate_score': candidate,
            'delta': delta,
            'gate_decision': quality_evidence.get('gate_decision', {}),
        },
        'diff_sha256': _sha(diff) if diff else None,
        'diff_bytes': len(diff.encode()) if diff else 0,
        'scope': 'Runtime codebase change; spec (URACE.md) must be updated to match if behaviour changed',
        'real_user_value_verified': False,
        'real_user_value_note': 'Executable benchmark score improvement is not user-value proof',
    }

    _atomic(snapshots_root / 'summary.json', summary)

    # Write the diff as a separate artifact for review
    if diff:
        diff_path = snapshots_root / 'change.diff'
        diff_path.write_text(diff)

    # Write comprehensive change log (human-readable)
    change_log_lines = [
        f'# Runtime Snapshot {snapshot_id}',
        f'Recorded: {summary["recorded_at"]}',
        f'Change type: {change_type}',
        '',
        '## Rationale',
        change_spec['rationale'],
        '',
        '## Files Changed',
    ]
    for f in change_spec['files_changed']:
        change_log_lines.append(f'- {f}')
    if files_removed:
        change_log_lines += ['', '## Files Removed']
        for f in files_removed:
            change_log_lines.append(f'- {f}')
    change_log_lines += [
        '',
        '## Quality Evidence',
        f'Baseline score: {baseline}',
        f'Candidate score: {candidate}',
        f'Delta: {delta}',
        f'Gate decision: {quality_evidence.get("gate_decision", {}).get("decision", "UNKNOWN")}',
        '',
        '## Engine Identity',
        f'Before: {change_spec["engine_sha256_before"]}',
        f'After:  {change_spec["engine_sha256_after"]}',
        '',
        '## Scope',
        summary['scope'],
    ]
    (snapshots_root / 'change_log.md').write_text('\n'.join(change_log_lines))

    # Write quality evidence separately for machine consumption
    _atomic(snapshots_root / 'quality_evidence.json', {
        'schema': SCHEMA,
        'snapshot_id': snapshot_id,
        **quality_evidence,
        'recorded_at': summary['recorded_at'],
    })

    # Update the snapshots index
    index_path = base / SNAPSHOTS_DIR / 'index.json'
    index = _load(index_path, {'schema': SCHEMA, 'snapshots': []})
    if not any(s['snapshot_id'] == snapshot_id for s in index['snapshots']):
        index['snapshots'].append({
            'snapshot_id': snapshot_id,
            'recorded_at': summary['recorded_at'],
            'engine_sha256_after': change_spec['engine_sha256_after'],
            'delta': delta,
            'files_changed_count': len(change_spec['files_changed']),
        })
        index['updated_at'] = _now()
        _atomic(index_path, index)

    return snapshot_id


def list_snapshots(base):
    """Return all recorded runtime snapshots in chronological order."""
    base = Path(base)
    index = _load(base / SNAPSHOTS_DIR / 'index.json', {'snapshots': []})
    return index['snapshots']


def load_snapshot(base, snapshot_id):
    """Load a specific runtime snapshot's summary."""
    base = Path(base)
    path = base / SNAPSHOTS_DIR / snapshot_id / 'summary.json'
    if not path.exists():
        raise FileNotFoundError(f'Runtime snapshot not found: {snapshot_id}')
    return _load(path)


def stream_summaries(base, *, limit=None):
    """
    Yield one summary dict per accepted snapshot in chronological order.

    Each entry is the full summary.json for the snapshot, enriched with
    'change_log_path' pointing to the human-readable change_log.md artifact.
    Skips snapshots whose summary.json is missing or corrupt.
    """
    base = Path(base)
    snapshots = list_snapshots(base)
    if limit is not None:
        snapshots = snapshots[-limit:]
    for entry in snapshots:
        snap_id = entry['snapshot_id']
        try:
            summary = load_snapshot(base, snap_id)
        except (FileNotFoundError, ValueError):
            continue
        log_path = base / SNAPSHOTS_DIR / snap_id / 'change_log.md'
        summary['change_log_path'] = str(log_path) if log_path.exists() else None
        yield summary


def planning_context(base, *, limit=5, extra_bases=None):
    """
    Return a compact planning context from recent accepted runtime snapshots.

    This is suitable for injection into the bootstrap/planning context (P1-4).

    extra_bases: optional list of Path/str pointing to additional trial dirs.
    When supplied, snapshots from all bases are merged (sorted by recorded_at
    descending) and the top ``limit`` entries are returned.  Every entry gains
    a ``product_base`` field (str) identifying the source base directory.
    """
    all_bases = [Path(base)]
    if extra_bases:
        for eb in extra_bases:
            p = Path(eb)
            if p not in all_bases:
                all_bases.append(p)

    raw_entries = []
    for b in all_bases:
        b_str = str(b)
        try:
            snapshots = list_snapshots(b)
        except Exception:
            snapshots = []
        for s in snapshots:
            snap_id = s['snapshot_id']
            try:
                summary = load_snapshot(b, snap_id)
            except (FileNotFoundError, ValueError):
                continue
            raw_entries.append({
                'snapshot_id': snap_id,
                'recorded_at': summary['recorded_at'],
                'change_type': summary.get('change_type', 'improvement'),
                'rationale': summary['rationale'],
                'files_changed': summary['files_changed'],
                'files_removed': summary.get('files_removed', []),
                'quality_delta': summary['quality']['delta'],
                'engine_sha256_after': summary['engine_sha256_after'],
                'product_base': b_str,
            })

    # Sort all entries by recorded_at descending, then take the last ``limit``
    # (most recent).  Using ascending sort then slicing from the tail matches
    # the existing single-base behaviour which returns snapshots[-limit:].
    raw_entries.sort(key=lambda e: e['recorded_at'])
    entries = raw_entries[-limit:]

    return {
        'schema': SCHEMA,
        'runtime_improvement_history': entries,
        'count': len(entries),
        'product_bases': [str(b) for b in all_bases],
        'scope': f'Last {limit} accepted runtime snapshots; not all changes or user outcomes',
    }
