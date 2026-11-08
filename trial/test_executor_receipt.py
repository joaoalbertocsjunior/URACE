"""Tests for executor_receipt: USD calculation, capture, load, and edge cases."""
import json
import hashlib
import pytest
from pathlib import Path

from executor_receipt import (
    P2P_SCHEMA, P2P_STEPS, PROVIDER_RATES, SCHEMA,
    capture_p2p_receipt, capture_receipt, load_p2p_receipts, load_receipts,
    usd_from_tokens,
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


# --- P2P integration receipt tests ---

def test_capture_p2p_receipt_writes_file(tmp_path):
    result = capture_p2p_receipt(
        TASK_ID, KNOWN_SHA, 'context_adaptation', 'claude-sonnet-4-6',
        800, 300, output_dir=tmp_path, asset_id='rt-freeform-route',
    )
    path = Path(result['receipt_path'])
    assert path.exists()
    assert result['schema'] == P2P_SCHEMA
    assert result['arm'] == 'p2p_integration'
    assert result['p2p_step'] == 'context_adaptation'
    assert result['asset_id'] == 'rt-freeform-route'
    assert result['usd_source'] == 'provider_published_rate'


def test_capture_p2p_receipt_sha256_matches_file(tmp_path):
    result = capture_p2p_receipt(
        TASK_ID, KNOWN_SHA, 'asset_analysis', 'claude-sonnet-4-6',
        400, 150, output_dir=tmp_path,
    )
    actual = hashlib.sha256(Path(result['receipt_path']).read_bytes()).hexdigest()
    assert actual == result['receipt_sha256']


def test_capture_p2p_receipt_usd_less_than_executor(tmp_path):
    exec_result = capture_receipt(
        TASK_ID, KNOWN_SHA, 'claude-sonnet-4-6', 5000, 1500, output_dir=tmp_path
    )
    p2p_result = capture_p2p_receipt(
        TASK_ID, KNOWN_SHA, 'context_adaptation', 'claude-sonnet-4-6',
        800, 200, output_dir=tmp_path,
    )
    assert p2p_result['usd_observed'] < exec_result['usd_observed']


def test_capture_p2p_multiple_steps_per_task(tmp_path):
    for step in ('asset_analysis', 'context_adaptation', 'validation'):
        capture_p2p_receipt(
            TASK_ID, KNOWN_SHA, step, 'claude-sonnet-4-6', 400, 100, output_dir=tmp_path
        )
    grouped = load_p2p_receipts(tmp_path)
    assert len(grouped[TASK_ID]) == 3
    assert {r['p2p_step'] for r in grouped[TASK_ID]} == {
        'asset_analysis', 'context_adaptation', 'validation'
    }


def test_capture_p2p_invalid_step_raises(tmp_path):
    with pytest.raises(ValueError, match='p2p_step'):
        capture_p2p_receipt(
            TASK_ID, KNOWN_SHA, 'unknown_step', 'claude-sonnet-4-6',
            100, 50, output_dir=tmp_path,
        )


def test_all_p2p_steps_valid():
    assert P2P_STEPS == {'asset_analysis', 'context_adaptation', 'validation', 'gap_fill'}


def test_load_p2p_receipts_empty_dir(tmp_path):
    assert load_p2p_receipts(tmp_path) == {}


def test_load_p2p_receipts_groups_by_task(tmp_path):
    for tid in ('T001', 'T002'):
        capture_p2p_receipt(
            tid, KNOWN_SHA, 'asset_analysis', 'claude-sonnet-4-6',
            300, 100, output_dir=tmp_path,
        )
    grouped = load_p2p_receipts(tmp_path)
    assert set(grouped.keys()) == {'T001', 'T002'}
    assert all(r['schema'] == P2P_SCHEMA for rs in grouped.values() for r in rs)


def test_gap_fill_step_accepted():
    # gap_fill is the most expensive step — should still be a valid P2P step
    usd, _ = usd_from_tokens('claude-sonnet-4-6', 3000, 1000)
    assert usd > 0
    assert 'gap_fill' in P2P_STEPS
