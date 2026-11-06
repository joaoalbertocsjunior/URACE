"""Tests for mime_priority.py — 8+ cases."""
import time
import pytest

from urace import mime_priority as mp


class MockExchange:
    def __init__(self, peer_id='node-1'):
        self._rows = []
        self._peer_id = peer_id

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)

    def local_peer_id(self):
        return self._peer_id


def _grant(fid, ct):
    return {'kind': 'EQUITY_GRANT', 'feature_id': fid, 'content_type': ct}


def _borrow(fid, peer='node-1'):
    return {'kind': 'FEATURE_BORROWED', 'feature_id': fid, 'peer_id': peer}


# ── calibrate_mime_priority ───────────────────────────────────────────────────

def test_empty_history_returns_empty():
    ex = MockExchange()
    result = mp.calibrate_mime_priority(ex)
    assert result == {}


def test_single_type_full_weight():
    ex = MockExchange()
    ex.append_audit_row(_grant('f1', 'text/x-python'))
    ex.append_audit_row(_borrow('f1'))
    ex.append_audit_row(_borrow('f1'))
    result = mp.calibrate_mime_priority(ex)
    assert result == {'text/x-python': 1.0}


def test_frequency_counting_two_types():
    ex = MockExchange()
    ex.append_audit_row(_grant('f1', 'text/csv'))
    ex.append_audit_row(_grant('f2', 'application/json'))
    ex.append_audit_row(_borrow('f1'))
    ex.append_audit_row(_borrow('f1'))
    ex.append_audit_row(_borrow('f1'))
    ex.append_audit_row(_borrow('f2'))
    result = mp.calibrate_mime_priority(ex)
    assert abs(result['text/csv'] - 0.75) < 1e-4
    assert abs(result['application/json'] - 0.25) < 1e-4


def test_weights_sum_to_one():
    ex = MockExchange()
    types = ['text/csv', 'application/json', 'image/png', 'application/pdf', 'application/zip']
    for i, ct in enumerate(types):
        ex.append_audit_row(_grant(f'f{i}', ct))
        ex.append_audit_row(_borrow(f'f{i}'))
    result = mp.calibrate_mime_priority(ex)
    assert abs(sum(result.values()) - 1.0) < 1e-4


# ── should_replicate ──────────────────────────────────────────────────────────

def test_should_replicate_bootstrap_fewer_than_5_types():
    # Only 2 unique types seen → bootstrap mode → replicate everything
    ex = MockExchange()
    ex.append_audit_row(_grant('f1', 'text/csv'))
    ex.append_audit_row(_grant('f2', 'application/json'))
    ex.append_audit_row(_borrow('f1'))
    ex.append_audit_row(_borrow('f2'))
    # Even a type never seen should replicate
    assert mp.should_replicate('application/pdf', ex) is True


def test_should_replicate_above_threshold():
    ex = MockExchange()
    # 5 unique types to bypass bootstrap
    for i, ct in enumerate(['text/csv', 'application/json', 'image/png', 'application/pdf', 'application/zip']):
        ex.append_audit_row(_grant(f'f{i}', ct))
        # CSV gets 6/10, others get 1/10 each
    for _ in range(6):
        ex.append_audit_row(_borrow('f0'))  # text/csv
    for i in range(1, 5):
        ex.append_audit_row(_borrow(f'f{i}'))
    assert mp.should_replicate('text/csv', ex, threshold=0.05) is True


def test_should_replicate_below_threshold():
    # Need 5 unique types in priorities to escape bootstrap
    # text/csv: 90, json: 5, image/png: 1, pdf: 1, zip: 1 → zip weight = 1/98 ≈ 0.01 < 0.05
    ex = MockExchange()
    types = ['text/csv', 'application/json', 'image/png', 'application/pdf', 'application/zip']
    for i, ct in enumerate(types):
        ex.append_audit_row(_grant(f'f{i}', ct))
    for _ in range(90):
        ex.append_audit_row(_borrow('f0'))  # text/csv
    for _ in range(5):
        ex.append_audit_row(_borrow('f1'))  # json
    ex.append_audit_row(_borrow('f2'))   # image/png
    ex.append_audit_row(_borrow('f3'))   # pdf
    ex.append_audit_row(_borrow('f4'))   # zip — weight = 1/97 ≈ 0.01
    result = mp.should_replicate('application/zip', ex, threshold=0.05)
    assert result is False  # ~0.01 < 0.05


# ── get_priority_rank ─────────────────────────────────────────────────────────

def test_get_priority_rank_known_type():
    ex = MockExchange()
    ex.append_audit_row(_grant('f1', 'text/x-python'))
    ex.append_audit_row(_borrow('f1'))
    rank = mp.get_priority_rank('text/x-python', ex)
    assert rank == 1.0


def test_get_priority_rank_unknown_type():
    ex = MockExchange()
    ex.append_audit_row(_grant('f1', 'text/x-python'))
    ex.append_audit_row(_borrow('f1'))
    rank = mp.get_priority_rank('application/pdf', ex)
    assert rank == 0.0


# ── emit_mime_calibration_event ───────────────────────────────────────────────

def test_emit_writes_audit_row():
    # Reset cache
    mp._CALIBRATION_CACHE.clear()
    ex = MockExchange('peer-test-emit')
    ex.append_audit_row(_grant('f1', 'text/csv'))
    ex.append_audit_row(_borrow('f1'))
    result = mp.emit_mime_calibration_event(ex)
    assert result.get('kind') == 'MIME_PRIORITY_CALIBRATED'
    assert result.get('peer_id') == 'peer-test-emit'
    rows = [r for r in ex.audit_rows() if r.get('kind') == 'MIME_PRIORITY_CALIBRATED']
    assert len(rows) == 1


def test_emit_idempotent_within_24h():
    mp._CALIBRATION_CACHE.clear()
    ex = MockExchange('peer-idem')
    ex.append_audit_row(_grant('f1', 'text/csv'))
    ex.append_audit_row(_borrow('f1'))
    r1 = mp.emit_mime_calibration_event(ex)
    r2 = mp.emit_mime_calibration_event(ex)
    assert r1.get('kind') == 'MIME_PRIORITY_CALIBRATED'
    assert r2.get('status') == 'skipped'
    rows = [r for r in ex.audit_rows() if r.get('kind') == 'MIME_PRIORITY_CALIBRATED']
    assert len(rows) == 1  # only one written
