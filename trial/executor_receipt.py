"""Capture executor API receipts and reconcile to USD at published provider rates.

usd_source is always 'provider_published_rate' — not a reconciled invoice.
Callers must reconcile against actual provider billing statements before making
a qualified cost claim. All token fields are actual observed values from API
usage objects, not estimates.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

SCHEMA = 'urace-executor-receipt-v1'

# Published rates as of 2025-11. Update rate_effective when provider changes pricing.
# source: anthropic.com/pricing, openai.com/pricing
PROVIDER_RATES: dict[str, dict[str, Any]] = {
    'claude-sonnet-4-6': {
        'input_usd_per_mtok': 3.00,
        'output_usd_per_mtok': 15.00,
        'cache_write_usd_per_mtok': 3.75,
        'cache_read_usd_per_mtok': 0.30,
        'provider': 'anthropic',
        'rate_source': 'anthropic.com/pricing',
        'rate_effective': '2025-11',
    },
    'claude-opus-4-7': {
        'input_usd_per_mtok': 15.00,
        'output_usd_per_mtok': 75.00,
        'cache_write_usd_per_mtok': 18.75,
        'cache_read_usd_per_mtok': 1.50,
        'provider': 'anthropic',
        'rate_source': 'anthropic.com/pricing',
        'rate_effective': '2025-11',
    },
    'claude-haiku-4-5-20251001': {
        'input_usd_per_mtok': 0.80,
        'output_usd_per_mtok': 4.00,
        'cache_write_usd_per_mtok': 1.00,
        'cache_read_usd_per_mtok': 0.08,
        'provider': 'anthropic',
        'rate_source': 'anthropic.com/pricing',
        'rate_effective': '2025-11',
    },
    'gpt-4o': {
        'input_usd_per_mtok': 2.50,
        'output_usd_per_mtok': 10.00,
        'cache_write_usd_per_mtok': 0.0,
        'cache_read_usd_per_mtok': 1.25,
        'provider': 'openai',
        'rate_source': 'openai.com/api/pricing',
        'rate_effective': '2025-11',
    },
    'gpt-4o-mini': {
        'input_usd_per_mtok': 0.15,
        'output_usd_per_mtok': 0.60,
        'cache_write_usd_per_mtok': 0.0,
        'cache_read_usd_per_mtok': 0.075,
        'provider': 'openai',
        'rate_source': 'openai.com/api/pricing',
        'rate_effective': '2025-11',
    },
}


def usd_from_tokens(
    model: str,
    input_tokens: int,
    output_tokens: int,
    *,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> tuple[float, dict]:
    """Return (usd_observed, rate_snapshot) using published provider rates.

    Raises ValueError for unknown models. Add unknown models to PROVIDER_RATES.
    """
    if not isinstance(input_tokens, int) or input_tokens < 0:
        raise ValueError('input_tokens must be a non-negative int')
    if not isinstance(output_tokens, int) or output_tokens < 0:
        raise ValueError('output_tokens must be a non-negative int')
    rates = PROVIDER_RATES.get(model)
    if rates is None:
        raise ValueError(
            f'No published rate for model {model!r}; add it to PROVIDER_RATES'
        )
    usd = (
        input_tokens * rates['input_usd_per_mtok'] / 1_000_000
        + output_tokens * rates['output_usd_per_mtok'] / 1_000_000
        + cache_write_tokens * rates['cache_write_usd_per_mtok'] / 1_000_000
        + cache_read_tokens * rates['cache_read_usd_per_mtok'] / 1_000_000
    )
    snapshot = {
        'model': model,
        'input_usd_per_mtok': rates['input_usd_per_mtok'],
        'output_usd_per_mtok': rates['output_usd_per_mtok'],
        'cache_write_usd_per_mtok': rates['cache_write_usd_per_mtok'],
        'cache_read_usd_per_mtok': rates['cache_read_usd_per_mtok'],
        'provider': rates['provider'],
        'rate_source': rates['rate_source'],
        'rate_effective': rates['rate_effective'],
    }
    return round(usd, 10), snapshot


def capture_receipt(
    task_id: str,
    task_sha256: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    *,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
    output_dir: Path,
    extra: dict | None = None,
) -> dict:
    """Write an executor receipt for one task run to output_dir.

    Returns the receipt dict augmented with receipt_sha256 and receipt_path.
    """
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError('task_id must be a non-empty string')
    if not isinstance(task_sha256, str) or len(task_sha256) != 64:
        raise ValueError('task_sha256 must be a 64-char hex string')
    usd, rate_snapshot = usd_from_tokens(
        model, input_tokens, output_tokens,
        cache_write_tokens=cache_write_tokens,
        cache_read_tokens=cache_read_tokens,
    )
    receipt: dict = {
        'schema': SCHEMA,
        'task_id': task_id,
        'task_sha256': task_sha256,
        'arm': 'direct_executor',
        'model': model,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cache_write_tokens': cache_write_tokens,
        'cache_read_tokens': cache_read_tokens,
        'usd_observed': usd,
        'usd_source': 'provider_published_rate',
        'rate_snapshot': rate_snapshot,
        'captured_at': int(time.time()),
    }
    if extra:
        receipt['extra'] = extra
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = output_dir / f'executor_receipt_{task_id}.json'
    receipt_bytes = json.dumps(receipt, indent=2, allow_nan=False).encode()
    receipt_path.write_bytes(receipt_bytes)
    sha = hashlib.sha256(receipt_bytes).hexdigest()
    return {**receipt, 'receipt_sha256': sha, 'receipt_path': str(receipt_path)}


def load_receipts(receipts_dir: Path) -> list[dict]:
    """Load all executor receipts from receipts_dir, verifying schema."""
    receipts_dir = Path(receipts_dir)
    out: list[dict] = []
    for path in sorted(receipts_dir.glob('executor_receipt_*.json')):
        raw = path.read_bytes()
        receipt = json.loads(raw)
        if receipt.get('schema') != SCHEMA:
            raise ValueError(f'Unknown receipt schema in {path.name}')
        receipt['receipt_sha256'] = hashlib.sha256(raw).hexdigest()
        receipt['receipt_path'] = str(path)
        out.append(receipt)
    return out
