import contextlib,copy,io,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli,_common,data_transport
class LocalDataTransports(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.config=copy.deepcopy(cli.load_config());self.config.pop('active_product',None);self.config['state_path']=str(self.root/'state.json');self.config['executor']['enabled']=False;_common.atomic_write_json(Path(self.config['state_path']),cli.initial_state(self.config))
 def call(self,*argv):
  with patch.object(cli,'load_config',return_value=self.config),contextlib.redirect_stdout(io.StringIO()) as out:
   rc=cli.main(['data',*argv,'--format','json'])
  return rc,json.loads(out.getvalue())
 def state(self):return json.loads(Path(self.config['state_path']).read_text())
 def test_json_sync_push_round_trip_preserves_old_file(self):
  source=self.root/'source.json';source.write_text('[{"value":1}]');self.assertEqual(self.call('add','json','--type','json','--connect',str(source),'--direction','both')[0],0)
  self.assertEqual(self.call('verify','json')[1]['rows_transferred'],0)
  self.assertEqual(self.call('sync','json')[1]['rows_affected'],1)
  input=self.root/'new.json';input.write_text('[{"value":2}]');rc,result=self.call('push','json','--input-json',str(input));self.assertEqual(rc,0);self.assertEqual(json.loads(source.read_text()),[{'value':2}]);self.assertEqual(json.loads(Path(result['backup']).read_text()),[{'value':1}]);self.assertEqual(self.state()['data_sync_records'][-1]['status'],'SUCCESS')
 def test_csv_sync_and_sqlite_append(self):
  source=self.root/'data.csv';source.write_text('name,value\na,1\n');self.call('add','csv','--type','csv','--connect',str(source));self.assertEqual(self.call('sync','csv')[1]['rows_affected'],1)
  db=self.root/'data.db'
  with sqlite3.connect(db) as c:c.execute('CREATE TABLE values_table (name TEXT,value INTEGER)');c.execute("INSERT INTO values_table VALUES ('a',1)")
  self.call('add','sql','--type','sqlite','--connect',str(db),'--schema','values_table','--direction','both');self.assertEqual(self.call('sync','sql')[1]['rows_affected'],1)
  input=self.root/'input.json';input.write_text('[{"name":"b","value":2}]');self.assertEqual(self.call('push','sql','--input-json',str(input))[0],0)
  with sqlite3.connect(db) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM values_table').fetchone()[0],2)
 def test_bounded_reads_fail_without_success_evidence(self):
  source=self.root/'huge.json';source.write_text('[{"payload":"'+('a'*100)+'"}]');self.config['data_limits']={'max_bytes':20};self.call('add','huge','--type','json','--connect',str(source));self.assertEqual(self.call('sync','huge')[0],1);self.assertEqual(self.state()['data_sync_records'][-1]['rows_affected'],0)
 def test_read_only_direction_and_unsupported_database(self):
  source=self.root/'source.json';source.write_text('[]');self.call('add','read','--type','json','--connect',str(source));self.assertEqual(self.call('push','read')[0],1)
  self.call('add','remote','--type','postgres','--connect','postgres://user:SECRET@invalid/db');rc,result=self.call('verify','remote');self.assertEqual(rc,1);self.assertEqual(result['error'],'ADAPTER_REQUIRED');self.assertNotIn('SECRET',json.dumps(self.call('list')[1]))
 def test_duplicate_registry_and_missing_credential_are_errors(self):
  self.call('add','one','--type','json','--connect','missing');self.assertEqual(self.call('add','one','--type','json','--connect','different')[0],1);self.assertEqual(self.call('credential','inspect','missing')[0],1)
 def test_auto_sync_only_changed_readable_sources_and_never_pushes(self):
  source=self.root/'auto.json';source.write_text('[{"n":1}]');self.call('add','auto','--type','json','--connect',str(source));state=self.state();self.config['data_limits']={'auto_poll_seconds':0}
  self.assertEqual(len(data_transport.auto_sync(state,self.config,self.root)),1);self.assertEqual(data_transport.auto_sync(state,self.config,self.root),[])
  source.write_text('[{"n":200}]');self.assertEqual(len(data_transport.auto_sync(state,self.config,self.root)),1);self.assertEqual(len(state['data_sync_records']),2)

 def test_push_input_is_bounded_before_json_decode_and_preserves_target(self):
  target=self.root/'target.json';target.write_text('[]');self.call('add','bounded','--type','json','--connect',str(target),'--direction','both');self.config['data_limits']={'max_bytes':20}
  source=self.root/'input.json';source.write_text('[{"payload":"'+('a'*100)+'"}]');rc,result=self.call('push','bounded','--input-json',str(source));self.assertEqual(rc,1);self.assertIn('byte limit',result['detail']);self.assertEqual(target.read_text(),'[]');self.assertEqual(self.state()['data_sync_records'],[])
  class BoundedStream(io.StringIO):
   def read(self,size=-1):
    if size<0:raise AssertionError('unbounded read')
    return super().read(size)
  with self.assertRaises(data_transport.TransportError):data_transport.input_rows('-',self.config,BoundedStream('a'*100))
