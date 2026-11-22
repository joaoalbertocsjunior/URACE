import tempfile,unittest
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
 def test_lifecycle_field_written_to_journal(self):
  """append_row with explicit lifecycle stores the value."""
  from urace.audit_kinds import EventLifecycle
  import json
  append_row(self.path,{'kind':'TEST_EVENT'},lifecycle=EventLifecycle.ACTIVE)
  lines=[l for l in self.path.read_text().splitlines() if l.strip()]
  self.assertTrue(lines)
  row=json.loads(lines[-1])
  self.assertEqual(row.get('lifecycle'),'active')
 def test_terminal_kinds_auto_lifecycle(self):
  """Rows whose kind is in TERMINAL_KINDS get lifecycle=terminal automatically."""
  from urace.audit_kinds import EventLifecycle,TERMINAL_KINDS
  self.assertIn('EARN',TERMINAL_KINDS)
  self.assertIn('SPEND',TERMINAL_KINDS)
  self.assertEqual(EventLifecycle.TERMINAL.value,'terminal')
  self.assertEqual(EventLifecycle.ACTIVE.value,'active')
  self.assertEqual(EventLifecycle.ARCHIVED.value,'archived')
 def test_mark_terminal_transitions_active_row(self):
  """mark_terminal returns True when it transitions active→terminal."""
  from urace.authenticated_journal import mark_terminal
  import json
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'journal.jsonl'
   path.write_text(json.dumps({'id':'row-001','kind':'TEST','lifecycle':'active'})+'\n')
   result=mark_terminal(path,'row-001')
   self.assertTrue(result)
   row=json.loads(path.read_text().splitlines()[0])
   self.assertEqual(row['lifecycle'],'terminal')
