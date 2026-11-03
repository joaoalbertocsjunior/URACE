import argparse,copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from urace import validation,api_interface,auto_goals,resource_usage,external_metrics

class EvidenceQuality(unittest.TestCase):
 def verdict(self,before,after,direction='nondecreasing'):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'doc.txt').write_text('Document')
   op={'scope':'documentation','changed_files':['doc.txt'],'authority_basis':'delegated'}
   cfg={'executor':{'allowed_files_by_scope':{'documentation':['doc.txt']}}};state={'progress_profiles':[{'measures':{'quality':{'direction':direction}}}]}
   return validation.validate_operation(root,op,before,after,cfg,state)['verdict']
 def test_valid_finite_pair_remains_validated(self):self.assertEqual(self.verdict({'quality':1},{'quality':2}),'VALIDATED')
 def test_invalid_measurements_cannot_pass_guardrail(self):
  for invalid in [float('nan'),float('inf'),True,'invalid']:
   with self.subTest(invalid=invalid):self.assertEqual(self.verdict({'quality':1},{'quality':invalid}),'REJECTED')
 def test_dropped_metric_cannot_hide_regression(self):self.assertEqual(self.verdict({'quality':1,'reliability':1},{'quality':2}),'REJECTED')
 def test_new_metric_needs_matching_baseline(self):self.assertEqual(self.verdict({'quality':1},{'quality':2,'new':5}),'REJECTED')
 def test_unknown_direction_cannot_disable_guard(self):self.assertEqual(self.verdict({'quality':1},{'quality':0},'sideways'),'REJECTED')
 def test_nonfinite_external_measure_keeps_last_good_evidence(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'data.json').write_text('{"quality":NaN}')
   prior={'source':{'value':{'quality':1},'at':'prior'}}
   r=external_metrics.collect(root,{'mode':'LIVE','sources':[{'id':'source','kind':'json_file','location':'data.json','values':{'quality':'quality'}}]},prior)
   self.assertEqual(r['observations'],[]);self.assertEqual(r['last_known_good'],prior);self.assertEqual(len(r['errors']),1)

class PersistentAPIBounds(unittest.TestCase):
 def test_all_cli_infinite_aliases_require_stream(self):
  p=argparse.ArgumentParser();a=p.add_subparsers(dest='command').add_parser('auto');a.add_argument('--cycles');a.add_argument('--dry-run',action='store_true')
  for value in ['00','+0','-0',' 0 ','inf','infinite','forever','INFINITY']:
   for tokens in [['auto','--cycles',value],['auto','--cycles='+value]]:
    calls=[];r=api_interface.execute(p,lambda argv:calls.append(argv),argv=tokens);self.assertEqual(r['exit_code'],2,(tokens,r));self.assertEqual(calls,[])
 def test_finite_cycles_stay_nonpersistent(self):self.assertFalse(api_interface.persistent(['auto','--cycles','2']))

class ChangedPrerequisiteAcceptance(unittest.TestCase):
 def config(self):return {'authority':{'delegated':['objectives']},'project':{'id':'p','intent':'Ship safely','requirements':[{'id':'build','title':'Build','success_measure':'Old tests pass','priority':90},{'id':'ship','title':'Ship','success_measure':'Release passes','dependencies':['build'],'priority':80}]}}
 def test_changed_predecessor_criteria_require_new_completion(self):
  c=self.config();s={};parent=auto_goals.select(c,s);parent['status']='completed';c['project']['requirements'][0].update(success_measure='New independently verified criteria',priority=1)
  self.assertEqual(auto_goals.select(c,s)['project_requirement'],'build')
 def test_unchanged_predecessor_still_satisfies_dependency(self):
  c=self.config();s={};parent=auto_goals.select(c,s);parent['status']='completed';self.assertEqual(auto_goals.select(c,s)['project_requirement'],'ship')

class ArchivedProductAttribution(unittest.TestCase):
 def test_mismatched_legacy_archive_cannot_be_current_cost(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);cfg={'state_path':str(root/'state.json'),'resource_product_id':'current'}
   with sqlite3.connect(root/'resource-usage.sqlite3') as db:
    db.execute('CREATE TABLE native_calls (product_id TEXT,id TEXT,record TEXT)');db.execute('INSERT INTO native_calls VALUES (?,?,?)',('current','foreign',json.dumps({'id':'foreign','product_id':'other','usage':{'total_tokens':99}})))
   self.assertEqual(resource_usage.summary(cfg,{})['known_tokens'],0)
