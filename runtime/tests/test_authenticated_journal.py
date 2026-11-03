import json,tempfile,unittest
from pathlib import Path
from urace.authenticated_journal import append_row,coverage
class JournalTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'ledger.jsonl'
 def test_legacy_history_and_new_rows_have_distinct_origin_claims(self):
  self.path.write_text('{"legacy":true}\n');append_row(self.path,{'new':True});report=coverage(self.path);self.assertEqual(report['status'],'AUTHENTICATED_OBSERVED_BYTES');self.assertGreater(report['historically_observed_bytes'],0);self.assertGreater(report['instrumented_writer_bytes'],0);self.assertFalse(report['historical_authorship_proven']);self.assertEqual(len(self.path.read_text().splitlines()),2)
 def test_changed_original_rows_are_detected(self):
  append_row(self.path,{'a':1});self.path.write_text('{"a":2}\n')
  with self.assertRaises(ValueError):coverage(self.path)
 def test_unsealed_tail_is_not_silently_authenticated(self):
  append_row(self.path,{'a':1})
  with self.path.open('a') as f:f.write('{"external":2}\n')
  self.assertEqual(coverage(self.path)['status'],'UNCOVERED_TAIL');append_row(self.path,{'b':2});self.assertGreater(coverage(self.path)['historically_observed_bytes'],0)
 def test_incomplete_tail_and_truncation_block_append(self):
  append_row(self.path,{'a':1});self.path.write_text('')
  with self.assertRaises(ValueError):append_row(self.path,{'b':2})
 def test_empty_inspection_creates_nothing(self):
  self.assertEqual(coverage(self.path)['status'],'NOT_AUTHENTICATED');self.assertFalse(self.path.exists());self.assertFalse(self.path.with_name(self.path.name+'.pq').exists())
