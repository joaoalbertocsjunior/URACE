"""External regression detector: compares current benchmark score to last accepted deployment score."""
from pathlib import Path
from datetime import datetime, timezone
import json

SCHEMA = 'runtime-regression-guard-v1'
_STATUS_FILE = 'runtime-regression-status.json'
_ALERT_FILE = 'runtime-regression-alerts.jsonl'


def _utc_iso():
    return datetime.now(timezone.utc).isoformat()


def _load(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def last_accepted_score(base):
    """Return the candidate_score from the most recent DEPLOYED event, or None."""
    import runtime_trial as _rt
    import runtime_snapshot as _rs
    base = Path(base)
    events = _rt.deployment_log(base)
    # Iterate latest-first
    for event in reversed(events):
        if event.get('event') != 'DEPLOYED':
            continue
        snap_id = event.get('snapshot_id')
        if not snap_id:
            continue
        try:
            summary = _rs.load_snapshot(base, snap_id)
            import runtime_evaluation as _evaluation
            quality=summary.get('quality',{})
            if quality.get('gate_decision',{}).get('suite_sha256')!=_evaluation.digest(_evaluation.contract()):continue
            score = quality.get('candidate_score')
            if score is not None:
                return float(score)
        except (FileNotFoundError, ValueError, KeyError):
            continue
    return None


def check(base, config=None):
    """Compare current benchmark score to last accepted deployment score."""
    import runtime_quality_gate as _rqg
    base = Path(base)
    current_score = _rqg.read_latest_score(base)
    accepted_score = last_accepted_score(base)

    checked_at = _utc_iso()

    if current_score is None and accepted_score is None:
        return {
            'schema': SCHEMA,
            'status': 'UNKNOWN',
            'current_score': None,
            'accepted_score': None,
            'delta': None,
            'checked_at': checked_at,
            'reason': 'Runtime baseline has not been measured for current source; no accepted runtime deployment reference exists',
        }
    if current_score is None:
        return {
            'schema': SCHEMA,
            'status': 'UNKNOWN',
            'current_score': None,
            'accepted_score': accepted_score,
            'delta': None,
            'checked_at': checked_at,
            'reason': 'No current benchmark score; cannot compare against accepted baseline',
        }
    if accepted_score is None:
        return {
            'schema': SCHEMA,
            'status': 'BASELINE_ONLY',
            'current_score': current_score,
            'accepted_score': None,
            'delta': None,
            'checked_at': checked_at,
            'reason': 'No accepted deployment score recorded yet; regression check unavailable',
        }

    delta = current_score - accepted_score
    if current_score < accepted_score:
        return {
            'schema': SCHEMA,
            'status': 'REGRESSION',
            'current_score': current_score,
            'accepted_score': accepted_score,
            'delta': delta,
            'checked_at': checked_at,
            'reason': f'Current score {current_score:.2f} is below accepted score {accepted_score:.2f} (delta={delta:.2f})',
        }
    return {
        'schema': SCHEMA,
        'status': 'OK',
        'current_score': current_score,
        'accepted_score': accepted_score,
        'delta': delta,
        'checked_at': checked_at,
        'reason': f'Current score {current_score:.2f} meets or exceeds accepted score {accepted_score:.2f}',
    }


def run_guard(base, config=None):
    """Run regression check, persist results, and return the check result."""
    base = Path(base)
    result = check(base, config)

    if result['status'] == 'REGRESSION':
        alert_path = base / _ALERT_FILE
        with open(alert_path, 'a') as fh:
            fh.write(json.dumps(result, sort_keys=True) + '\n')

    # Atomic write of status file
    status_path = base / _STATUS_FILE
    tmp_path = status_path.with_suffix('.tmp')
    tmp_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    tmp_path.replace(status_path)

    return result


def report(base):
    """Return summary of current regression guard status and recent alerts."""
    base = Path(base)
    status_path = base / _STATUS_FILE
    alert_path = base / _ALERT_FILE

    current_status = _load(status_path, {}).get('status', 'UNKNOWN')

    alerts = []
    if alert_path.exists():
        for line in alert_path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    alerts.append(json.loads(line))
                except ValueError:
                    pass

    return {
        'schema': SCHEMA,
        'current_status': current_status,
        'alert_count': len(alerts),
        'alerts': alerts[-5:],
    }
