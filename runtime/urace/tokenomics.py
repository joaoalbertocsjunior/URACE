"""Token unit definition and attribution fingerprints for peer artifact exchange."""
import ast, hashlib, json

TOKEN_UNIT = {
    'schema': 'urace-tokenomics-v1',
    'definition': '1 token = 1 accepted quality improvement point, attributed to its origin peer',
    'earn': 'score_delta at quality gate pass; no other earn path',
    'spend': 'request improvements from peers',
    'baseline_grant_requests': 3,
    'deduplication': 'canonical_fingerprint for exact copies; outcome_fingerprint for near-copies',
    'settlement': 'not_yet_implemented',
    'mainnet_settlement_enabled': False,
}

def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def canonical_fingerprint(source_delta):
    """Exact-copy detection via AST-normalized source hash.

    source_delta: dict of {filename: source_text} for changed files only.
    Returns hex SHA-256 of the canonical normalized form.
    Two patches are exact copies iff their canonical_fingerprint is equal.
    """
    canonical = {}
    for name, text in sorted(source_delta.items()):
        try:
            canonical[name] = ast.dump(ast.parse(text))
        except SyntaxError:
            canonical[name] = ' '.join(text.split())
    return hashlib.sha256(_encoded(canonical)).hexdigest()

def outcome_fingerprint(baseline_engine_sha256, affected_files, score_delta):
    """Near-copy detection: same outcome regardless of surface form.

    baseline_engine_sha256: engine_sha256 of the evaluation baseline.
    affected_files: iterable of changed filenames.
    score_delta: float; bucketed to nearest int to absorb trivial variance.
    Two patches are near-copies iff they fix the same files for the same score gain from the same baseline.
    """
    return hashlib.sha256(_encoded({
        'baseline': baseline_engine_sha256,
        'files': sorted(affected_files),
        'delta_bucket': round(float(score_delta)),
    })).hexdigest()

def fingerprint_index(evaluations_dir):
    """Build outcome fingerprint index from stored qualification receipts.

    Returns dict mapping outcome_fingerprint -> list of {id, at, score, delta}.
    Used at deduplication check time; empty dict when no qualifications exist yet.
    """
    from pathlib import Path
    index = {}
    q_dir = Path(evaluations_dir)
    if not q_dir.exists():
        return index
    for receipt_path in sorted(q_dir.glob('*/receipt.json')):
        try:
            receipt = json.loads(receipt_path.read_text())
            ev_id = receipt.get('id')
            fp = receipt.get('outcome_fingerprint')
            if ev_id and fp:
                index.setdefault(fp, []).append({
                    'id': ev_id,
                    'at': receipt.get('at'),
                    'score': receipt.get('candidate_score'),
                    'delta': receipt.get('delta'),
                })
        except (OSError, ValueError):
            continue
    return index
