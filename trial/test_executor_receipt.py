"""Tests for executor_receipt: USD calculation, capture, load, and edge cases."""
import json
import hashlib
import pytest
from pathlib import Path

from executor_receipt import (
    PROVIDER_RATES, SCHEMA, capture_receipt, load_receipts, usd_from_tokens,
)

KNOWN_SHA = 'a' * 64
TASK_ID = 'T001'


def test_usd_from_tokens_known_model():
    usd, snap = usd_from_tokens('claude-sonnet-4-6', 1_000_000, 1_000_000)
    assert usd == pytest.approx(18.00, rel=1e-6)
    assert snap['model'] == 'claude-sonnet-4-6'
    assert snap['rate_source'] == 'anthropic.com/pricing'


def test_usd_from_tokens_cache_included():
    usd, _ = usd_from_tokens(
        'claude-sonnet-4-6', 0, 0,
        cache_write_tokens=1_000_000,
        cache_read_tokens=1_000_000,
    )
    expected = 3.75 + 0.30
    assert usd == pytest.approx(expected, rel=1e-6)


def test_usd_from_tokens_unknown_model_raises():
    with pytest.raises(ValueError, match='No published rate'):
        usd_from_tokens('unknown-model-x', 100, 100)


def test_usd_from_tokens_negative_tokens_raise():
    with pytest.raises(ValueError, match='non-negative'):
        usd_from_tokens('claude-sonnet-4-6', -1, 0)


def test_all_provider_rates_have_required_fields():
    required = {'input_usd_per_mtok', 'output_usd_per_mtok', 'provider', 'rate_source', 'rate_effective'}
    for model, rates in PROVIDER_RATES.items():
        missing = required - rates.keys()
        assert not missing, f'{model} missing fields: {missing}'


def test_capture_receipt_writes_file(tmp_path):
    result = capture_receipt(
        TASK_ID, KNOWN_SHA, 'claude-sonnet-4-6', 500, 200, output_dir=tmp_path
    )
    path = Path(result['receipt_path'])
    assert path.exists()
    assert result['schema'] == SCHEMA
    assert result['arm'] == 'direct_executor'
    assert result['usd_source'] == 'provider_published_rate'


def test_capture_receipt_sha256_matches_file(tmp_path):
    result = capture_receipt(
        TASK_ID, KNOWN_SHA, 'claude-sonnet-4-6', 100, 50, output_dir=tmp_path
    )
    path = Path(result['receipt_path'])
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual_sha == result['receipt_sha256']


def test_capture_receipt_usd_nonzero(tmp_path):
    result = capture_receipt(
        TASK_ID, KNOWN_SHA, 'claude-sonnet-4-6', 1000, 500, output_dir=tmp_path
    )
    assert result['usd_observed'] > 0


def test_load_receipts_round_trips(tmp_path):
    for i in range(3):
        capture_receipt(
            f'T{i:03d}', KNOWN_SHA, 'claude-sonnet-4-6', 100 * i, 50 * i,
            output_dir=tmp_path,
        )
    receipts = load_receipts(tmp_path)
    assert len(receipts) == 3
    assert all(r['schema'] == SCHEMA for r in receipts)


def test_load_receipts_empty_dir_returns_empty(tmp_path):
    assert load_receipts(tmp_path) == []


def test_capture_bad_task_id_raises(tmp_path):
    with pytest.raises(ValueError, match='task_id'):
        capture_receipt('', KNOWN_SHA, 'claude-sonnet-4-6', 100, 50, output_dir=tmp_path)


def test_capture_bad_sha_raises(tmp_path):
    with pytest.raises(ValueError, match='task_sha256'):
        capture_receipt(TASK_ID, 'tooshort', 'claude-sonnet-4-6', 100, 50, output_dir=tmp_path)


def test_gpt4o_rates_present():
    usd, snap = usd_from_tokens('gpt-4o', 1_000_000, 1_000_000)
    assert snap['provider'] == 'openai'
    assert usd == pytest.approx(12.50, rel=1e-6)
