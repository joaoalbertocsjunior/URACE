import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import auto_goals,data_transport,resource_usage,workflow_state

class ProjectDependencyIsolation(unittest.TestCase):
 def config(self):
  return {'authority':{'delegated':['objectives']},'project':{'id':'new','intent':'New owner project','requirements':[{'id':'ship','title':'Ship','success_measure':'Validated','dependencies':['build']}]}}
 def test_old_project_completion_does_not_satisfy_dependency(self):
  old={'id':'old-build','status':'completed','source':'auto_goals','project_id':'old','project_requirement':'build'}
  self.assertIsNone(auto_goals.select(self.config(),{'objectives':[old]}))
 def test_dependency_links_only_current_project_objectives(self):
  old={'id':'old-build','status':'completed','source':'auto_goals','project_id':'old','project_requirement':'build'}
  current={**old,'id':'new-build','project_id':'new'}
  result=auto_goals.select(self.config(),{'objectives':[old,current]});self.assertEqual(result['dependencies'],['new-build'])

class AutomaticDataRecovery(unittest.TestCase):
 def test_transient_failure_retries_without_source_edit(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);src=root/'input.json';src.write_text('[{"n":1}]')
   record={'id':'source','adapter_kind':'json','auto':True,'direction':'READ','connection_metadata':{'dsn':str(src)}};state={'data_source_records':[record]};config={'data_limits':{'auto_poll_seconds':0}}
   real=data_transport.perform
   with patch.object(data_transport,'read',side_effect=OSError('transient busy')):
    first=data_transport.auto_sync(state,config,root)
   self.assertEqual(first[0]['status'],'DISCONNECTED')
   second=data_transport.auto_sync(state,config,root);self.assertEqual(len(second),1);self.assertEqual(second[0]['status'],'CONNECTED');self.assertEqual(data_transport.auto_sync(state,config,root),[])
 def test_disconnected_source_retries_even_after_previous_success(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);src=root/'input.json';src.write_text('[]')
   record={'id':'source','adapter_kind':'json','auto':True,'direction':'READ','connection_metadata':{'dsn':str(src)}};state={'data_source_records':[record]};config={'data_limits':{'auto_poll_seconds':0}}
   data_transport.auto_sync(state,config,root);record['status']='DISCONNECTED'
   self.assertEqual(len(data_transport.auto_sync(state,config,root)),1)

class ProductReceiptIsolation(unittest.TestCase):
 def test_foreign_receipt_does_not_overwrite_same_id_current_archive(self):
  with tempfile.TemporaryDirectory() as directory:
   config={'state_path':str(Path(directory)/'state.json'),'resource_product_id':'current'}
   local={'id':'call','product_id':'current','usage':{'total_tokens':7}}
   resource_usage.archive_calls(config,{'executor_state':{'executor_calls':[local]}})
   foreign={**local,'product_id':'other','usage':{'total_tokens':99}}
   result=resource_usage.summary(config,{'executor_state':{'executor_calls':[foreign]}})
   self.assertEqual(result['known_tokens'],7);self.assertEqual(result['logical_calls'],1)
 def test_archive_retains_declared_product_instead_of_relabeling(self):
  with tempfile.TemporaryDirectory() as directory:
   config={'state_path':str(Path(directory)/'state.json'),'resource_product_id':'current'}
   foreign={'id':'call','product_id':'other','usage':{'total_tokens':99}}
   resource_usage.archive_calls(config,{'executor_state':{'executor_calls':[foreign]}})
   self.assertEqual(resource_usage.summary(config,{})['known_tokens'],0)
   self.assertEqual(resource_usage.summary({**config,'resource_product_id':'other'}, {})['known_tokens'],99)

class WithdrawnQualityClaims(unittest.TestCase):
 def test_known_imported_operation_withdraws_current_claim_without_rewriting_history(self):
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);job={'id':'spec-old','trial_id':'t','outcome':'ACCEPTED_EDITORIAL_IMPROVEMENT','accepted_version':7}
   for name,value in [('trial-clock.json',{'trial_id':'t'}),('state.json',{'jobs':[job]}),('withdrawn-acceptances.json',{'trial_id':'t','versions':[7]})]:
    (base/name).write_text(json.dumps(value))
   operation={'id':'spec-old','trial_id':'t','status':'ACCEPTED','quality_improvement_claimed':True,'independent_validation':{'verdict':'ACCEPTED'}};state={'operations':[operation]}
   workflow_state._import_observations({},state,base)
   self.assertFalse(operation['quality_improvement_claimed']);self.assertTrue(operation['editorial_acceptance_withdrawn']);self.assertEqual(operation['status'],'ACCEPTED');self.assertEqual(operation['independent_validation']['verdict'],'ACCEPTED')
   before=len(state.get('trace_records',[]));workflow_state._import_observations({},state,base);self.assertEqual(len(state.get('trace_records',[])),before)
 def test_other_trial_withdrawal_does_not_affect_current_claim(self):
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory)
   for name,value in [('trial-clock.json',{'trial_id':'t'}),('state.json',{'jobs':[{'id':'spec-old','trial_id':'t','accepted_version':7}]}),('withdrawn-acceptances.json',{'trial_id':'older','versions':[7]})]:
    (base/name).write_text(json.dumps(value))
   operation={'id':'spec-old','trial_id':'t','quality_improvement_claimed':True};state={'operations':[operation]};workflow_state._import_observations({},state,base);self.assertTrue(operation['quality_improvement_claimed'])

class SQLiteResourceBounds(unittest.TestCase):
 def test_transfer_stops_at_byte_budget_before_fetching_remainder(self):
  from contextlib import nullcontext
  class Connection:
   row_factory=None
   def setlimit(self,*args):pass
   def execute(self,*args):
    yield {'payload':'a'*100}
    yield {'payload':'b'*100}
    raise AssertionError('Fetched beyond exhausted aggregate byte budget')
  record={'adapter_kind':'sqlite','schema_hint':'items','connection_metadata':{'dsn':'unused.db'}}
  with patch.object(data_transport.sqlite3,'connect',return_value=nullcontext(Connection())):
   with self.assertRaises(data_transport.TransportError):data_transport.read(record,{'data_limits':{'max_bytes':200}})
 def test_blob_fails_as_transport_error_without_success_evidence(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);path=root/'input.db'
   with sqlite3.connect(path) as db:db.execute('CREATE TABLE items (payload BLOB)');db.execute('INSERT INTO items VALUES (?)',(b'\x00binary',))
   record={'id':'blob','adapter_kind':'sqlite','schema_hint':'items','connection_metadata':{'dsn':str(path)}};state={}
   code,result=data_transport.perform('sync',record,state,{},root)
   self.assertEqual(code,1);self.assertEqual(result['error'],'TRANSPORT_FAILED');self.assertEqual(state.get('evidence',[]),[])
