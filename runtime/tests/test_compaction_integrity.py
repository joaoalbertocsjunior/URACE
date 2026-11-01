import copy,json,tempfile,unittest
from pathlib import Path
from urace import compaction
class CompactionIntegrity(unittest.TestCase):
 def fixture(self,root):
  records=[{'id':f'rec-{i:010x}','at':f'2020-01-01T00:{i:02d}:00+00:00','detail':'Measured observation '+('value '*120)} for i in range(30)]
  state={'executor_state':{'failures':copy.deepcopy(records)}};engine=compaction.CompactionEngine(root);policy={'id':'rtp-a1b2c3d4e5','target_field':'executor_state.failures','compaction_mode':'ARCHIVE','max_entries':2,'archive_subpath':'archives/failures'}
  before=len(json.dumps(state));summary,event=engine.compact_field(state,'executor_state.failures',policy,'explicit-test-operator');return records,state,engine,event,before
 def test_lossless_round_trip_reduces_working_state(self):
  with tempfile.TemporaryDirectory() as root:
   records,state,engine,event,before=self.fixture(root);after=len(json.dumps(state));self.assertLess(after,before*.25)
   engine.decompact_field(state,'executor_state.failures',event['id'],'operator');self.assertEqual(state['executor_state']['failures'],records)
 def test_index_does_not_bypass_digest_verification(self):
  with tempfile.TemporaryDirectory() as root:
   records,state,engine,event,before=self.fixture(root);archive=Path(root)/event['archive_path'];items=json.loads(archive.read_text());items[0]['detail']='tampered';archive.write_text(json.dumps(items))
   with self.assertRaisesRegex(ValueError,'digest mismatch'):engine.decompact_record(event['id'],items[0]['id'])
   with self.assertRaisesRegex(ValueError,'digest mismatch'):engine.amend_archived_record(event['id'],items[0]['id'],'CUSTOM','tamper rejected','operator',lambda r:r)
 def test_archive_escape_is_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   with self.assertRaises(ValueError):compaction._archive_path(root,'../outside.json')
   with self.assertRaises(ValueError):compaction._archive_path(root,'/tmp/outside.json')
