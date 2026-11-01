"""Self-measurement metrics for URACE runtime as its own product.

Collects real, numeric metrics via subprocess and filesystem — no external users required.
When the product IS the software, test quality, import health, and spec compliance
are valid outcome metrics from day zero.
"""
from __future__ import annotations
import json as _json
import re as _re
import subprocess
import time
from pathlib import Path
from typing import Any

SELF_METRICS_SCHEMA = 'urace-self-metrics-v1'

# ── collection ────────────────────────────────────────────────────────────────

def collect(root: Path, timeout: int = 120) -> dict[str, Any]:
    """Collect self-measurement metrics snapshot. Never raises; partial results on error."""
    results: dict[str, Any] = {
        'schema': SELF_METRICS_SCHEMA,
        'collected_at': time.time(),
        'metrics': {},
        'errors': [],
    }

    runtime = root / 'runtime'
    if not runtime.exists():
        runtime = root

    _collect_test_pass_rate(runtime, timeout, results)
    _collect_import_health(runtime, results)
    _collect_spec_quality(results)

    return results


def _collect_test_pass_rate(runtime: Path, timeout: int,
                             out: dict[str, Any]) -> None:
    try:
        proc = subprocess.run(
            ['python3', '-m', 'pytest', 'tests/', '-q', '--tb=no', '--no-header'],
            capture_output=True, text=True, cwd=str(runtime), timeout=timeout,
        )
        last = (proc.stdout.strip().split('\n') or [''])[-1]
        passed = int(m.group(1)) if (m := _re.search(r'(\d+) passed', last)) else 0
        failed = int(m.group(1)) if (m := _re.search(r'(\d+) failed', last)) else 0
        errors = int(m.group(1)) if (m := _re.search(r'(\d+) error', last)) else 0
        total = passed + failed + errors
        out['metrics']['test_pass_rate'] = {
            'value': passed / total if total else None,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'total': total,
            'unit': 'ratio',
            'direction': 'nondecreasing',
        }
    except subprocess.TimeoutExpired:
        out['errors'].append({'metric': 'test_pass_rate', 'error': 'timeout'})
    except Exception as exc:
        out['errors'].append({'metric': 'test_pass_rate', 'error': str(exc)})


def _collect_import_health(runtime: Path, out: dict[str, Any]) -> None:
    check = (
        'from urace import cli, inspection, executor, '
        'integration_bridge, peer_exchange, tui, runtime_features; '
        'print("ok")'
    )
    try:
        proc = subprocess.run(
            ['python3', '-c', check],
            capture_output=True, text=True, cwd=str(runtime), timeout=30,
        )
        ok = proc.returncode == 0 and 'ok' in proc.stdout
        out['metrics']['import_health'] = {
            'value': 1.0 if ok else 0.0,
            'unit': 'binary',
            'direction': 'nondecreasing',
            'detail': proc.stderr[:400] if not ok else '',
        }
    except Exception as exc:
        out['errors'].append({'metric': 'import_health', 'error': str(exc)})


def _collect_spec_quality(out: dict[str, Any]) -> None:
    try:
        from .inspection import document_metrics
        from ._common import load_config
        config = load_config()
        m = document_metrics(config)
        out['metrics']['spec_normative_rules'] = {
            'value': m.get('normative_rules', 0),
            'unit': 'count',
            'direction': 'nondecreasing',
        }
        out['metrics']['spec_behavioral_tests'] = {
            'value': m.get('behavioral_tests', 0),
            'unit': 'count',
            'direction': 'nondecreasing',
        }
        out['metrics']['spec_unresolved_markers'] = {
            'value': m.get('unresolved_markers', 0),
            'unit': 'count',
            'direction': 'nonincreasing',
        }
    except Exception as exc:
        out['errors'].append({'metric': 'spec_quality', 'error': str(exc)})


# ── persistence ───────────────────────────────────────────────────────────────

def latest(root: Path) -> dict[str, Any] | None:
    """Return the last collected self-metrics snapshot, or None."""
    path = root / 'trial' / 'self-metrics-latest.json'
    if not path.exists():
        return None
    try:
        return _json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def save(root: Path, metrics: dict[str, Any]) -> None:
    """Persist self-metrics snapshot alongside trial artifacts."""
    from ._common import atomic_write_json
    trial = root / 'trial'
    trial.mkdir(parents=True, exist_ok=True)
    atomic_write_json(trial / 'self-metrics-latest.json', metrics)


# ── integration: feed into external_metric_state ─────────────────────────────

def as_external_source(root: Path) -> dict[str, Any] | None:
    """Return self-metrics formatted as an external_metric_state source entry.

    Use this to inject self-measurement into URACE's normal metric pipeline so
    that test_pass_rate and import_health appear as observable progress metrics
    without requiring external infrastructure.
    """
    snapshot = latest(root)
    if snapshot is None:
        return None
    values: dict[str, float] = {}
    for name, entry in snapshot.get('metrics', {}).items():
        v = entry.get('value')
        if v is not None:
            values[name] = float(v)
    if not values:
        return None
    return {
        'id': 'urace-self-measurement',
        'source': 'urace-self-measurement',
        'kind': 'self_metrics',
        'collected_at': snapshot.get('collected_at', 0.0),
        'values': values,
        'attribution': 'SELF_MEASURED_NO_EXTERNAL_USERS_REQUIRED',
    }
