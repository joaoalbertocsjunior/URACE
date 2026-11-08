"""Tests for the executor receipt contract in cost_model.py."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from urace import cost_model as cm


# ---------------------------------------------------------------------------
# usd_from_tokens
# ---------------------------------------------------------------------------

class UsdFromTokensTests(unittest.TestCase):

    def test_known_model_sonnet(self):
        usd, snap = cm.usd_from_tokens('claude-sonnet-4-6', 1_000_000, 1_000_000)
        self.assertAlmostEqual(usd, 18.00, places=4)
        self.assertEqual(snap['model'], 'claude-sonnet-4-6')
        self.assertEqual(snap['provider'], 'anthropic')

    def test_cache_read_included(self):
        usd, _ = cm.usd_from_tokens(
            'claude-sonnet-4-6', 0, 0, cache_read_tokens=1_000_000
        )
        self.assertAlmostEqual(usd, 0.30, places=6)

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError, msg='No published rate'):
            cm.usd_from_tokens('no-such-model', 100, 100)

    def test_negative_tokens_raise(self):
        with self.assertRaises(ValueError):
            cm.usd_from_tokens('claude-sonnet-4-6', -1, 0)

    def test_all_provider_rates_have_required_fields(self):
        required = {'input_usd_per_mtok', 'output_usd_per_mtok', 'provider',
                    'rate_source', 'rate_effective'}
        for model, rates in cm.PROVIDER_RATES.items():
            missing = required - rates.keys()
            self.assertFalse(missing, f'{model} missing: {missing}')

    def test_gpt4o_openai_provider(self):
        usd, snap = cm.usd_from_tokens('gpt-4o', 1_000_000, 1_000_000)
        self.assertEqual(snap['provider'], 'openai')
        self.assertAlmostEqual(usd, 12.50, places=4)


# ---------------------------------------------------------------------------
# receipt_from_operation
# ---------------------------------------------------------------------------

def _make_operation(input_tokens=1000, output_tokens=500, cache_read=0,
                    model='claude-sonnet-4-6', reported_cost=None):
    transport = []
    if model:
        transport = [{'provider_id': 'anthropic',
                      'usage': {'models': {model: {'uncached_input_tokens': input_tokens,
                                                   'output_tokens': output_tokens}}}}]
    usage = {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cached_input_tokens': cache_read,
        'reported_cost_usd': reported_cost,
        'transport_usage': transport,
    }
    return {'id': 'op-test-001', 'usage': usage}


class ReceiptFromOperationTests(unittest.TestCase):

    def test_known_model_produces_receipt(self):
        op = _make_operation()
        r = cm.receipt_from_operation(op)
        self.assertIsNotNone(r)
        self.assertEqual(r['schema'], cm.RECEIPT_SCHEMA)
        self.assertEqual(r['arm'], 'direct_executor')
        self.assertEqual(r['input_tokens'], 1000)
        self.assertEqual(r['output_tokens'], 500)
        self.assertEqual(r['usd_source'], 'provider_published_rate')
        self.assertIsInstance(r['usd_observed'], float)
        self.assertGreater(r['usd_observed'], 0)

    def test_unknown_model_falls_back_to_reported_cost(self):
        op = _make_operation(model=None, reported_cost=0.042)
        r = cm.receipt_from_operation(op)
        self.assertIsNotNone(r)
        self.assertEqual(r['usd_source'], 'executor_reported')
        self.assertAlmostEqual(r['usd_observed'], 0.042)

    def test_no_usage_returns_none(self):
        self.assertIsNone(cm.receipt_from_operation({'id': 'x'}))

    def test_missing_tokens_returns_none(self):
        op = {'id': 'x', 'usage': {'input_tokens': None, 'output_tokens': 500}}
        self.assertIsNone(cm.receipt_from_operation(op))

    def test_negative_tokens_returns_none(self):
        op = {'id': 'x', 'usage': {'input_tokens': -1, 'output_tokens': 500}}
        self.assertIsNone(cm.receipt_from_operation(op))

    def test_no_model_no_reported_cost_usd_source_unavailable(self):
        op = _make_operation(model=None, reported_cost=None)
        r = cm.receipt_from_operation(op)
        self.assertIsNotNone(r)
        self.assertEqual(r['usd_source'], 'unavailable')
        self.assertIsNone(r['usd_observed'])

    def test_operation_id_propagated(self):
        op = _make_operation()
        op['id'] = 'op-abc-123'
        r = cm.receipt_from_operation(op)
        self.assertEqual(r['operation_id'], 'op-abc-123')

    def test_cache_read_tokens_propagated(self):
        op = _make_operation(cache_read=200)
        r = cm.receipt_from_operation(op)
        self.assertEqual(r['cache_read_tokens'], 200)


# ---------------------------------------------------------------------------
# store_receipt / load_receipts / summarize_receipts
# ---------------------------------------------------------------------------

class ReceiptStorageTests(unittest.TestCase):

    def _make_config(self, tmp_dir: Path) -> dict:
        state_file = tmp_dir / 'state.json'
        state_file.write_text('{}')
        with patch('urace._common.state_path', return_value=state_file):
            return {}

    def test_store_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            state_file = tmp / 'state.json'
            state_file.write_text('{}')
            with patch('urace._common.state_path', return_value=state_file):
                receipt = cm.receipt_from_operation(_make_operation())
                cm.store_receipt({}, receipt)
                loaded = cm.load_receipts({})
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]['schema'], cm.RECEIPT_SCHEMA)

    def test_load_empty_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            state_file = tmp / 'state.json'
            state_file.write_text('{}')
            with patch('urace._common.state_path', return_value=state_file):
                result = cm.load_receipts({})
        self.assertEqual(result, [])

    def test_load_with_limit(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            state_file = tmp / 'state.json'
            state_file.write_text('{}')
            with patch('urace._common.state_path', return_value=state_file):
                for i in range(5):
                    op = _make_operation()
                    op['id'] = f'op-{i:03d}'
                    cm.store_receipt({}, cm.receipt_from_operation(op))
                loaded = cm.load_receipts({}, limit=3)
        self.assertEqual(len(loaded), 3)

    def test_load_with_since_filters(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            state_file = tmp / 'state.json'
            state_file.write_text('{}')
            with patch('urace._common.state_path', return_value=state_file):
                # Write a receipt with an old timestamp
                receipt = cm.receipt_from_operation(_make_operation())
                receipt['captured_at'] = int(time.time()) - 86400 * 10  # 10 days ago
                cm.store_receipt({}, receipt)
                # since=tomorrow should return nothing
                future = '2099-01-01'
                loaded = cm.load_receipts({}, since=future)
        self.assertEqual(len(loaded), 0)


class SummarizeReceiptsTests(unittest.TestCase):

    def _receipt(self, input_tok=1000, output_tok=500, model='claude-sonnet-4-6'):
        op = _make_operation(input_tokens=input_tok, output_tokens=output_tok, model=model)
        return cm.receipt_from_operation(op)

    def test_empty_list_returns_zeros(self):
        s = cm.summarize_receipts([])
        self.assertEqual(s['receipt_count'], 0)
        self.assertIsNone(s['usd_total'])

    def test_aggregates_tokens(self):
        receipts = [self._receipt(1000, 500), self._receipt(2000, 800)]
        s = cm.summarize_receipts(receipts)
        self.assertEqual(s['receipt_count'], 2)
        self.assertEqual(s['total_input_tokens'], 3000)
        self.assertEqual(s['total_output_tokens'], 1300)

    def test_aggregates_usd(self):
        receipts = [self._receipt(), self._receipt()]
        s = cm.summarize_receipts(receipts)
        self.assertIsNotNone(s['usd_total'])
        self.assertGreater(s['usd_total'], 0)

    def test_model_counts(self):
        receipts = [
            self._receipt(model='claude-sonnet-4-6'),
            self._receipt(model='claude-sonnet-4-6'),
            self._receipt(model='gpt-4o'),
        ]
        s = cm.summarize_receipts(receipts)
        self.assertEqual(s['models']['claude-sonnet-4-6'], 2)
        self.assertEqual(s['models']['gpt-4o'], 1)

    def test_usd_source_note_present(self):
        s = cm.summarize_receipts([])
        self.assertIn('provider_published_rate', s['usd_source_note'])


if __name__ == '__main__':
    unittest.main()
