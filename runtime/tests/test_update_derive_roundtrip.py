"""Actual local update/derive round trips; no remote downloads or executor calls."""
import contextlib,copy,hashlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli,_common,updater,derived_artifacts,api_interface

class Commands(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.product=self.root/'product';self.product.mkdir();self.state_path=self.root/'state/state.json';self.cfg=copy.deepcopy(cli.load_config());self.cfg.pop('active_product',None);self.cfg['state_path']=str(self.state_path);self.cfg['executor']['enabled']=False;self.cfg['self_evolution_policy']={'mode':'NECESSARY_ONLY'}
  self.text='# URACE\n# Normative Language\n# Bootstrap Execution Requirements\n'+''.join('# Section '+str(i)+'\n'+'Runtime MUST preserve owner intent.\n'*30 for i in range(20));(self.product/'URACE.md').write_text(self.text);self.source=self.root/'candidate.md';self.source.write_text(self.text+'\nUpdates SHOULD be staged.\n');_common.atomic_write_json(self.state_path,cli.initial_state(self.cfg))
 def call(self,args):
  with patch.object(cli,'load_config',return_value=self.cfg),patch.object(cli,'ROOT',self.product),patch.object(cli,'CONFIG_PATH',self.root/'config.json'),contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()) as err:
   try:code=cli.main(args)
   except SystemExit as e:code=e.code
  return code,out.getvalue(),err.getvalue()
 def state(self):return json.loads(self.state_path.read_text())
 def test_download_hash_pin_success_and_wrong_pin_preserves_pointer(self):
  h=hashlib.sha256(self.source.read_bytes()).hexdigest();code,text,error=self.call(['update','download',str(self.source),'--hash',h,'--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['sha256'],h);pointer=updater._updates_root(self.state_path.parent)/'latest.json';before=pointer.read_bytes();bad=self.root/'other.md';bad.write_text(self.text+'different');code,_,_=self.call(['update','download',str(bad),'--hash','0'*64,'--json']);self.assertNotEqual(code,0);self.assertEqual(pointer.read_bytes(),before);self.assertEqual((self.product/'URACE.md').read_text(),self.text)
 def test_download_explain_apply_and_expected_hash(self):
  self.assertEqual(self.call(['update','download',str(self.source)])[0],0);code,text,error=self.call(['update','explain','--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['status'],'REVIEW_REQUIRED')
  with patch.object(cli,'queue_input',return_value={'id':'queued'}) as queue:
   self.assertNotEqual(self.call(['update','apply','--hash','0'*64,'--json'])[0],0);queue.assert_not_called();code,text,error=self.call(['update','apply','--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['status'],'QUEUED');self.assertEqual(queue.call_args.args[1],'goal')
 def test_orchestrated_json_update_requires_no_stdin_and_reviews_first(self):
  with patch('builtins.input',side_effect=AssertionError('Machine update must not prompt')),patch.object(cli,'queue_input') as queue:
   code,text,error=self.call(['update','--source',str(self.source),'--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['status'],'REVIEW_REQUIRED');queue.assert_not_called()
 def test_orchestrated_update_yes_queues_same_candidate_without_applying(self):
  with patch('builtins.input',side_effect=AssertionError('Already authorized')),patch.object(cli,'queue_input',return_value={'id':'queued'}) as queue:
   code,text,error=self.call(['update','--source',str(self.source),'--yes','--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['status'],'QUEUED');self.assertEqual(queue.call_args.args[2]['update_candidate']['sha256'],hashlib.sha256(self.source.read_bytes()).hexdigest());self.assertEqual((self.product/'URACE.md').read_text(),self.text)
 def test_missing_source_bad_spec_and_bad_reference_are_actionable_failures(self):
  self.assertNotEqual(self.call(['update','--json'])[0],0);bad=self.root/'bad.md';bad.write_text('not URACE');self.assertNotEqual(self.call(['update','download',str(bad),'--json'])[0],0)
  with self.assertRaises(ValueError):updater.resolve_candidate(self.state_path.parent,'../escape*')
 def test_tampered_candidate_cannot_be_queued(self):
  _,text,_=self.call(['update','download',str(self.source),'--json']);m=json.loads(text);Path(m['candidate']).write_text(self.text+'tampered')
  with patch.object(cli,'queue_input') as queue:self.assertNotEqual(self.call(['update','apply','--json'])[0],0);queue.assert_not_called()
 def test_derive_save_verify_and_export_agree(self):
  out=self.root/'export.json';code,text,error=self.call(['derive','--constructs','AP0','--save','--out',str(out),'--json']);self.assertEqual(code,0,error);manifest=json.loads(text);self.assertEqual(json.loads(out.read_text()),manifest);h=manifest['content_hash'];self.assertEqual(h,derived_artifacts.content_hash(manifest));code,text,error=self.call(['derive','--hash',h,'--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['verification'][0]['status'],'VERIFIED');self.assertEqual(self.call(['derive','--verify','--json'])[0],0)
 def test_saved_construct_set_is_also_verifiable(self):
  out=self.root/'saved-constructs.json';code,text,error=self.call(['derive','--constructs','GoalRecord','--kind','schema','--save','--out',str(out),'--json']);self.assertEqual(code,0,error);data=json.loads(text);self.assertIn('content_hash',data);self.assertEqual(json.loads(out.read_text()),data);self.assertEqual(data['content_hash'],derived_artifacts.content_hash(data));code,text,error=self.call(['derive','--verify','--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['verification'][0]['status'],'VERIFIED')
 def test_artifact_tamper_is_detected_and_not_resealed(self):
  # --kind pattern uses DerivedManifestRef (derivation_refs) for artifact verification
  self.assertEqual(self.call(['derive','--constructs','AP0','--kind','pattern','--save','--json'])[0],0);ref=self.state()['derivation_refs'][0];p=self.state_path.parent/ref['artifact'];body=json.loads(p.read_text());body['intent']='tampered';p.write_text(json.dumps(body));code,text,error=self.call(['derive','--verify','--json']);self.assertEqual(code,1,error);self.assertEqual(json.loads(text)['verification'][0]['status'],'MISMATCH');self.assertEqual(json.loads(p.read_text())['intent'],'tampered')
 def test_reference_tamper_is_detected(self):
  self.call(['derive','--constructs','AP0','--kind','pattern','--save','--json']);state=self.state();state['derivation_refs'][0]['intent']='tampered';_common.atomic_write_json(self.state_path,state);self.assertEqual(self.call(['derive','--verify','--json'])[0],1)
 def test_legacy_missing_artifact_is_unknown_not_false_mismatch(self):
  state=self.state();state['derived_manifest_refs']=[{'manifest_id':'old','content_hash':'a'*64}];_common.atomic_write_json(self.state_path,state);code,text,error=self.call(['derive','--verify','--json']);self.assertEqual(code,1,error);self.assertEqual(json.loads(text)['verification'][0]['status'],'UNVERIFIABLE')
 def test_refresh_without_new_intent_rebuilds_and_retains_verifiable_artifact(self):
  # --kind pattern uses DerivedManifestRef for manifest_id-based refresh
  self.call(['derive','--constructs','AP0','--kind','pattern','--save','--json']);before=self.state()['derivation_refs'][0]['manifest_id'];code,text,error=self.call(['derive','--refresh','--manifest-id',before,'--show-delta','--json']);self.assertEqual(code,0,error);data=json.loads(text);self.assertEqual(data['results'][0]['status'],'refreshed');self.assertEqual(self.call(['derive','--verify','--json'])[0],0)
 def test_construct_refresh_and_missing_filter_report_correctly(self):
  self.call(['derive','--constructs','GoalRecord','--kind','schema','--save','--json']);code,text,error=self.call(['derive','--kind','schema','--refresh','--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['results'][0]['status'],'refreshed');self.assertEqual(self.call(['derive','--verify','--json'])[0],0);self.assertNotEqual(self.call(['derive','--refresh','--manifest-id','missing','--json'])[0],0)
 def test_from_goals_uses_canonical_objectives(self):
  state=self.state();state['objectives']=[{'id':'g','title':'Recover transactions and validate checkpoints','description':'resilience'}];state['goals']=[];_common.atomic_write_json(self.state_path,state);code,text,error=self.call(['derive','--from-goals','--json']);self.assertEqual(code,0,error);self.assertTrue(json.loads(text)['suggestions'])
 def test_invalid_kind_and_conflicting_verification_fail(self):
  self.assertNotEqual(self.call(['derive','--kind','not-a-kind','--json'])[0],0);self.assertNotEqual(self.call(['derive','--verify','--no-verify'])[0],0)
 def test_api_roundtrip_for_derive_and_update(self):
  parser=cli.build_parser()
  with patch.object(cli,'load_config',return_value=self.cfg),patch.object(cli,'ROOT',self.product):
   result=api_interface.execute(parser,cli.main,command='derive',params={'constructs':'AP0','save':True});self.assertEqual(result['status'],'ok');h=result['output']['content_hash'];result=api_interface.execute(parser,cli.main,command='derive',params={'derive_expected_hash':h});self.assertEqual(result['status'],'ok');result=api_interface.execute(parser,cli.main,command='update download',params={'reference':str(self.source)});self.assertEqual(result['status'],'ok')

 def test_derivation_record_save_preserves_an_intervening_state_update(self):
  # --kind pattern path uses two state_lock calls; inject concurrent update at the 2nd
  original=_common.state_lock;calls=[0]
  @contextlib.contextmanager
  def lock(path):
   calls[0]+=1
   if calls[0]==2:
    current=self.state();current['unrelated_concurrent_marker']='preserved';_common.atomic_write_json(self.state_path,current)
   with original(path):yield
  with patch.object(cli,'state_lock',lock):self.assertEqual(self.call(['derive','--constructs','AP0','--kind','pattern','--save','--json'])[0],0)
  self.assertEqual(self.state()['unrelated_concurrent_marker'],'preserved')
 def test_resolve_conflict_and_missing_decision(self):
  state=self.state();state['objectives']=[{'id':'conflict','status':'awaiting_operator_decision','update_candidate':{'sha256':'a'*64}}];_common.atomic_write_json(self.state_path,state)
  with patch.object(cli,'queue_input',return_value={'id':'queued'}) as queue:
   self.assertNotEqual(self.call(['update','resolve','--json'])[0],0);queue.assert_not_called();code,text,error=self.call(['update','resolve','conflict','--decision','Preserve local behavior','--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['status'],'QUEUED');self.assertEqual(queue.call_args.args[1],'goal_control')

 def test_catalog_and_empty_suggestions_honor_json(self):
  # --kind all (default): JSON output has 'constructs'; --kind pattern has 'patterns'
  code,text,error=self.call(['derive','--no-verify','--json']);self.assertEqual(code,0,error);data=json.loads(text);self.assertTrue(data.get('constructs') or data.get('patterns'));code,text,error=self.call(['derive','--kind','schema','--no-verify','--json']);self.assertEqual(code,0,error);self.assertTrue(json.loads(text)['constructs']);code,text,error=self.call(['derive','xyzxyzxyzxyz','--suggest','--no-verify','--json']);self.assertEqual(code,0,error);self.assertEqual(json.loads(text)['suggestions'],[])

 def test_non_object_artifact_returns_mismatch_without_crashing(self):
  # --kind pattern uses DerivedManifestRef (derivation_refs) for artifact path
  self.call(['derive','--constructs','AP0','--kind','pattern','--save','--json']);ref=self.state()['derivation_refs'][0];(self.state_path.parent/ref['artifact']).write_text('[]');code,text,error=self.call(['derive','--verify','--json']);self.assertEqual(code,1,error);self.assertEqual(json.loads(text)['verification'][0]['status'],'MISMATCH')
 def test_corrupt_candidate_pointer_cannot_escape_storage(self):
  self.call(['update','download',str(self.source),'--json']);pointer=updater._updates_root(self.state_path.parent)/'latest.json'
  for body in [{'sha256':'../../outside'},[],{'sha256':True}]:
   pointer.write_text(json.dumps(body))
   with self.assertRaises(ValueError):updater.resolve_candidate(self.state_path.parent)
 def test_managed_candidate_manifest_cannot_redirect_to_another_file(self):
  _,text,_=self.call(['update','download',str(self.source),'--json']);m=json.loads(text);path=Path(m['candidate']).parent/'manifest.json';m['candidate']=str(self.source);path.write_text(json.dumps(m))
  with self.assertRaises(ValueError):updater.resolve_candidate(self.state_path.parent)
