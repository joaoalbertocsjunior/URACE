import pytest
pytestmark = pytest.mark.slow
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from urace import ledger_sync as ls


# ── chain-building helpers ────────────────────────────────────────────────────

def _sha256_row(signed: dict) -> str:
    return hashlib.sha256(json.dumps(signed, sort_keys=True).encode()).hexdigest()


def _make_row(kind: str, previous: str, **fields) -> dict:
    """Build a valid audit chain row."""
    row = {'kind': kind, 'previous': previous, 'at_unix': time.time(), **fields}
    row['sha256'] = _sha256_row(row)
    return row


def _make_chain(events: list) -> list:
    """Build a chain of rows: events = [(kind, extra_fields), ...]"""
    rows = []
    prev = '0' * 64
    for kind, fields in events:
        row = _make_row(kind, prev, **fields)
        rows.append(row)
        prev = row['sha256']
    return rows


def _make_seal_row(previous: str, sequence: int = 1, snapshot: dict = None) -> dict:
    """Build a LEDGER_BLOCK_SEAL row."""
    row = {
        'kind': 'LEDGER_BLOCK_SEAL',
        'previous': previous,
        'sequence': sequence,
        'at_unix': time.time(),
        'credit_balance_snapshot': snapshot or {},
    }
    row['sha256'] = _sha256_row(row)
    return row


# ── LatestSealTests ───────────────────────────────────────────────────────────

class LatestSealTests(unittest.TestCase):

    def test_no_seal_returns_none(self):
        rows = _make_chain([('SOME_EVENT', {}), ('OTHER_EVENT', {})])
        self.assertIsNone(ls.latest_seal(rows))

    def test_single_seal_returned(self):
        rows = _make_chain([('SOME_EVENT', {})])
        seal = _make_seal_row(rows[-1]['sha256'], sequence=1)
        rows.append(seal)
        result = ls.latest_seal(rows)
        self.assertEqual(result['kind'], 'LEDGER_BLOCK_SEAL')
        self.assertEqual(result['sequence'], 1)

    def test_latest_of_multiple_seals_returned(self):
        rows = _make_chain([('EVT', {}), ('EVT', {})])
        seal1 = _make_seal_row(rows[-1]['sha256'], sequence=1)
        seal1['at_unix'] = time.time() - 100  # older
        seal1['sha256'] = _sha256_row({k: v for k, v in seal1.items() if k != 'sha256'})
        rows.append(seal1)
        seal2 = _make_seal_row(seal1['sha256'], sequence=2)
        seal2['at_unix'] = time.time()  # newer
        seal2['sha256'] = _sha256_row({k: v for k, v in seal2.items() if k != 'sha256'})
        rows.append(seal2)
        result = ls.latest_seal(rows)
        self.assertEqual(result['sequence'], 2)

    def test_non_seal_rows_ignored(self):
        rows = _make_chain([
            ('CREDIT_DELTA', {'peer': 'p1', 'amount_units': 100}),
            ('WORK_REQUEST', {'request_id': 'r1'}),
        ])
        self.assertIsNone(ls.latest_seal(rows))


# ── TailSinceTests ────────────────────────────────────────────────────────────

class TailSinceTests(unittest.TestCase):

    def test_tail_all_when_no_seal(self):
        rows = _make_chain([('EVT', {}), ('EVT', {}), ('EVT', {})])
        tail = ls.tail_since_seal(rows, seal=None)
        self.assertEqual(len(tail), 3)

    def test_tail_empty_when_seal_is_last(self):
        rows = _make_chain([('EVT', {})])
        seal = _make_seal_row(rows[-1]['sha256'])
        rows.append(seal)
        tail = ls.tail_since_seal(rows, seal=seal)
        self.assertEqual(tail, [])

    def test_tail_rows_after_seal(self):
        rows = _make_chain([('EVT', {})])
        seal = _make_seal_row(rows[-1]['sha256'])
        rows.append(seal)
        after1 = _make_row('CREDIT_DELTA', seal['sha256'], peer='p1', amount_units=50)
        after2 = _make_row('CREDIT_DELTA', after1['sha256'], peer='p2', amount_units=30)
        rows.extend([after1, after2])
        tail = ls.tail_since_seal(rows, seal=seal)
        self.assertEqual(len(tail), 2)
        self.assertEqual(tail[0]['sha256'], after1['sha256'])

    def test_seal_not_included_in_tail(self):
        rows = _make_chain([('EVT', {})])
        seal = _make_seal_row(rows[-1]['sha256'])
        rows.append(seal)
        after = _make_row('EVT', seal['sha256'])
        rows.append(after)
        tail = ls.tail_since_seal(rows, seal=seal)
        for r in tail:
            self.assertNotEqual(r['kind'], 'LEDGER_BLOCK_SEAL')


# ── PruneWindowTests ──────────────────────────────────────────────────────────

class PruneWindowTests(unittest.TestCase):

    def test_prune_no_seal_returns_last_n(self):
        rows = _make_chain([('EVT', {}) for _ in range(20)])
        pruned = ls.prune_to_window(rows, tail_rows=5)
        self.assertEqual(len(pruned), 5)
        # should be the last 5 rows
        self.assertEqual(pruned, rows[-5:])

    def test_prune_keeps_seal_plus_tail(self):
        base = _make_chain([('EVT', {})])
        seal = _make_seal_row(base[-1]['sha256'], sequence=1)
        rows = base + [seal]
        after = _make_row('EVT', seal['sha256'])
        rows.append(after)
        pruned = ls.prune_to_window(rows, tail_rows=10)
        self.assertIn(seal, pruned)
        self.assertIn(after, pruned)

    def test_prune_window_too_small_still_includes_seal(self):
        base = _make_chain([('EVT', {})])
        seal = _make_seal_row(base[-1]['sha256'])
        rows = base + [seal]
        # Add 10 tail rows
        prev = seal['sha256']
        for _ in range(10):
            r = _make_row('EVT', prev)
            rows.append(r)
            prev = r['sha256']
        pruned = ls.prune_to_window(rows, tail_rows=0)
        # Even with tail_rows=0, seal should be first element
        self.assertEqual(pruned[0]['kind'], 'LEDGER_BLOCK_SEAL')

    def test_prune_full_tail_when_small_enough(self):
        base = _make_chain([('EVT', {})])
        seal = _make_seal_row(base[-1]['sha256'])
        rows = base + [seal]
        prev = seal['sha256']
        for _ in range(3):
            r = _make_row('EVT', prev)
            rows.append(r)
            prev = r['sha256']
        pruned = ls.prune_to_window(rows, tail_rows=100)
        # seal + 3 tail rows
        self.assertEqual(len(pruned), 4)


# ── VerifyTailTests ───────────────────────────────────────────────────────────

class VerifyTailTests(unittest.TestCase):

    def _make_seal_and_tail(self, n=3):
        base = _make_chain([('EVT', {})])
        seal = _make_seal_row(base[-1]['sha256'])
        tail = []
        prev = seal['sha256']
        for i in range(n):
            r = _make_row('EVT', prev, idx=i)
            tail.append(r)
            prev = r['sha256']
        return seal, tail

    def test_valid_chain_passes(self):
        seal, tail = self._make_seal_and_tail(3)
        ls.verify_tail(seal, tail)  # should not raise

    def test_empty_tail_passes(self):
        base = _make_chain([('EVT', {})])
        seal = _make_seal_row(base[-1]['sha256'])
        ls.verify_tail(seal, [])  # should not raise

    def test_broken_previous_raises(self):
        seal, tail = self._make_seal_and_tail(3)
        # corrupt previous on second row
        tail[1] = dict(tail[1])
        tail[1]['previous'] = '0' * 64
        # recompute sha256 so hash is internally valid but chain is broken
        signed = {k: v for k, v in tail[1].items() if k != 'sha256'}
        tail[1]['sha256'] = _sha256_row(signed)
        with self.assertRaises(ValueError):
            ls.verify_tail(seal, tail)

    def test_hash_mismatch_raises(self):
        seal, tail = self._make_seal_and_tail(2)
        # tamper with a field without updating sha256
        bad = dict(tail[0])
        bad['tampered'] = True
        # leave sha256 as original — hash mismatch
        tail[0] = bad
        with self.assertRaises(ValueError):
            ls.verify_tail(seal, tail)


# ── BalanceFromSealTests ──────────────────────────────────────────────────────

class BalanceFromSealTests(unittest.TestCase):

    def _seal_with_snapshot(self, snapshot):
        base = _make_chain([('EVT', {})])
        return _make_seal_row(base[-1]['sha256'], snapshot=snapshot)

    def test_peer_in_snapshot_no_tail(self):
        seal = self._seal_with_snapshot({'alice': 500})
        self.assertEqual(ls.balance_from_seal(seal, [], 'alice'), 500)

    def test_peer_not_in_snapshot(self):
        seal = self._seal_with_snapshot({'alice': 500})
        self.assertEqual(ls.balance_from_seal(seal, [], 'bob'), 0)

    def test_tail_credit_delta_added(self):
        seal = self._seal_with_snapshot({'alice': 100})
        tail = [
            _make_row('CREDIT_DELTA', seal['sha256'], peer='alice', amount_units=50),
        ]
        self.assertEqual(ls.balance_from_seal(seal, tail, 'alice'), 150)

    def test_tail_credit_delta_negative(self):
        seal = self._seal_with_snapshot({'alice': 200})
        tail = [
            _make_row('CREDIT_DELTA', seal['sha256'], peer='alice', amount_units=-80),
        ]
        self.assertEqual(ls.balance_from_seal(seal, tail, 'alice'), 120)

    def test_multiple_deltas_accumulated(self):
        seal = self._seal_with_snapshot({'alice': 100})
        prev = seal['sha256']
        tail = []
        for amt in [10, -5, 20, -3]:
            r = _make_row('CREDIT_DELTA', prev, peer='alice', amount_units=amt)
            tail.append(r)
            prev = r['sha256']
        # 100 + 10 - 5 + 20 - 3 = 122
        self.assertEqual(ls.balance_from_seal(seal, tail, 'alice'), 122)

    def test_other_peer_deltas_ignored(self):
        seal = self._seal_with_snapshot({'alice': 100, 'bob': 200})
        tail = [
            _make_row('CREDIT_DELTA', seal['sha256'], peer='bob', amount_units=999),
        ]
        self.assertEqual(ls.balance_from_seal(seal, tail, 'alice'), 100)


# ── SyncSummaryTests ──────────────────────────────────────────────────────────

class SyncSummaryTests(unittest.TestCase):

    def test_no_rows_summary(self):
        result = ls.sync_summary([])
        self.assertEqual(result['schema'], ls.SCHEMA)
        self.assertEqual(result['total_rows'], 0)
        self.assertIsNone(result['seal_at_unix'])
        self.assertIsNone(result['seal_sequence'])
        self.assertEqual(result['tail_rows_since_seal'], 0)
        self.assertFalse(result['is_light_peer_sufficient'])
        self.assertEqual(result['pruned_row_count'], 0)

    def test_with_seal_summary(self):
        base = _make_chain([('EVT', {}), ('EVT', {})])
        seal = _make_seal_row(base[-1]['sha256'], sequence=7)
        rows = base + [seal]
        # add 3 tail rows
        prev = seal['sha256']
        for _ in range(3):
            r = _make_row('EVT', prev)
            rows.append(r)
            prev = r['sha256']
        result = ls.sync_summary(rows)
        self.assertEqual(result['total_rows'], 6)
        self.assertEqual(result['tail_rows_since_seal'], 3)
        self.assertEqual(result['seal_sequence'], 7)
        # pruned: 2 base rows before seal
        self.assertEqual(result['pruned_row_count'], 2)

    def test_is_light_peer_sufficient_true_with_seal(self):
        base = _make_chain([('EVT', {})])
        seal = _make_seal_row(base[-1]['sha256'])
        rows = base + [seal]
        result = ls.sync_summary(rows)
        self.assertTrue(result['is_light_peer_sufficient'])


# ── RequestTailPayloadTests ───────────────────────────────────────────────────

class RequestTailPayloadTests(unittest.TestCase):

    def _make_exchange(self):
        from urace import peer_exchange as pe
        tmp = tempfile.mkdtemp()
        e = pe.Exchange(Path(tmp) / 'node')
        e.configure(enabled=True, network=False)
        e.feature('feat', [])
        return e

    def test_no_seal_returns_empty_payload(self):
        e = self._make_exchange()
        result = ls.request_tail_payload(e)
        self.assertIsNone(result['seal'])
        self.assertEqual(result['tail'], [])

    def test_with_seal_returns_seal_and_tail(self):
        from urace import ledger_compaction as lc
        e = self._make_exchange()
        tmp = tempfile.mkdtemp()
        lc.seal_ledger_block(e, tmp)
        # Add a row after the seal by appending an audit event
        e.event('POST_SEAL_EVENT', note='tail_row')
        result = ls.request_tail_payload(e)
        self.assertIsNotNone(result['seal'])
        self.assertEqual(result['seal']['kind'], 'LEDGER_BLOCK_SEAL')
        # tail should contain at least the POST_SEAL_EVENT
        tail_kinds = [r.get('kind') for r in result['tail']]
        self.assertIn('POST_SEAL_EVENT', tail_kinds)


# ── FetchTailFromPeerTests ────────────────────────────────────────────────────

class FetchTailFromPeerTests(unittest.TestCase):

    def _fake_urlopen_response(self, payload: bytes):
        resp = MagicMock()
        resp.read = MagicMock(return_value=payload)
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_fetch_tail_calls_correct_url(self):
        from unittest.mock import MagicMock, patch
        payload = json.dumps({'seal': None, 'tail': []}).encode()
        resp_mock = self._fake_urlopen_response(payload)
        with patch('urllib.request.urlopen', return_value=resp_mock) as mock_open:
            ls.fetch_tail_from_peer('https://peer.example.com')
            call_req = mock_open.call_args[0][0]
            self.assertTrue(call_req.full_url.endswith('/urace/rpc/v1/ledger-tail'))

    def test_fetch_tail_returns_parsed_payload(self):
        from unittest.mock import patch
        payload = b'{"seal": null, "tail": []}'
        resp_mock = self._fake_urlopen_response(payload)
        with patch('urllib.request.urlopen', return_value=resp_mock):
            result = ls.fetch_tail_from_peer('https://peer.example.com')
            self.assertIn('tail', result)
            self.assertIsNone(result['seal'])
            self.assertEqual(result['tail'], [])

    def test_fetch_tail_on_error_propagates(self):
        import urllib.error
        from unittest.mock import patch
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('test')):
            with self.assertRaises(urllib.error.URLError):
                ls.fetch_tail_from_peer('https://peer.example.com')


if __name__ == '__main__':
    unittest.main()
