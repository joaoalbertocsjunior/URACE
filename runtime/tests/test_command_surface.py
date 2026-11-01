import argparse,contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli,_common,api_interface,command_surface,freeform_routing
class Capture(BaseException):pass

def grammar():
 found=[]
 def grab(self,*args,**kwargs):found.append(self);raise Capture()
 with patch.object(argparse.ArgumentParser,'parse_known_args',grab):
  try:cli.main(['commands'])
  except Capture:pass
 return found[0]

class CommandSurfaceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.parser=grammar()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.config=copy.deepcopy(cli.load_config());self.config.pop('active_product',None);self.config['state_path']=str(Path(self.tmp.name)/'state.json');self.config['executor']['enabled']=False
  self.path=Path(self.config['state_path']);self.state=cli.initial_state(self.config);_common.atomic_write_json(self.path,self.state)
 def invoke(self,argv):
  with patch.object(cli,'load_config',return_value=self.config),contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()) as err:
   try:rc=cli.main(argv)
   except SystemExit as e:rc=e.code
  return rc,out.getvalue(),err.getvalue()
 def test_nested_help_all_parser_paths(self):
  def walk(p,path):
   for name,c in command_surface.child_parsers(p).items():
    yield [*path,name];yield from walk(c,[*path,name])
  for path in walk(self.parser,[]):
   with self.subTest(path=path),patch.object(cli,'load_config',side_effect=AssertionError('help reads config')):
    rc,out,err=self.invoke_help(['help',*path]);self.assertEqual(rc,0,err);self.assertIn('usage:',out)
 def invoke_help(self,argv):
  with contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()) as err:
   try:rc=cli.main(argv)
   except SystemExit as e:rc=e.code
  return rc,out.getvalue(),err.getvalue()
 def test_global_flags_and_slash_grouped_controls(self):
  for args in [['help','configuration','effort'],['/configuration','effort','--help'],['--json','configuration','effort','--help'],['--format','json','configuration','executor','--help']]:
   self.assertEqual(self.invoke(args)[0],0)
 def test_status_is_read_only_under_writer_lock(self):
  before=self.path.read_bytes()
  with _common.state_lock(self.path),patch.object(cli,'save_state',side_effect=AssertionError('status wrote state')),patch.object(cli,'queue_input',side_effect=AssertionError('status queued work')):
   for subject in command_surface.child_parsers(command_surface.child_parsers(self.parser)['status']):
    with self.subTest(subject=subject):
     rc,out,err=self.invoke(['status',subject,'--json']);self.assertIn(rc,(0,1),err)
  self.assertEqual(before,self.path.read_bytes())
 def test_status_cannot_mutate(self):
  with patch.object(cli,'queue_input',side_effect=AssertionError('mutation')):
   for args in [['status','executors','attach'],['status','configuration','effort','high'],['status','data','sync'],['status','onboarding','confirm']]:
    self.assertNotEqual(self.invoke(args)[0],0)
 def test_dry_run_aliases_do_not_call_cycle_or_write(self):
  before=self.path.read_bytes()
  for command in ('auto','autonomous'):
   with patch.object(cli,'cycle',side_effect=AssertionError('cycle called')),patch.object(cli,'save_state',side_effect=AssertionError('state write')),patch.object(cli,'queue_input',side_effect=AssertionError('queue write')):
    rc,out,err=self.invoke([command,'--dry-run','--cycles','1','--json']);self.assertEqual(rc,0,err);self.assertEqual(json.loads(out)['executor_calls'],0)
  self.assertEqual(self.path.read_bytes(),before)
 def test_malformed_command_does_not_classify(self):
  with patch.object(freeform_routing,'route',side_effect=AssertionError('classification')):
   for args in [['configuration','effort','high','extra'],['status','unknown'],['goal','list','--priority','20'],['trace','list','--offset','-1']]:self.assertNotEqual(self.invoke(args)[0],0)
 def test_boolean_typo_rejected(self):
  rc,out,err=self.invoke(['data','add','x','--type','csv','--connect','x.csv','--auto','garbage']);self.assertEqual(rc,2);self.assertIn('true or false',err)
 def test_budget_and_evaluation_validate_before_queuing(self):
  with patch.object(cli,'queue_input',side_effect=AssertionError('invalid work queued')):
   for args in [['configuration','executor-budget','--daily','0','--monthly','0'],['configuration','evaluation-minimum','1.5'],['configuration','evaluation-weight','nan','--component','quality'],['configuration','evaluation-weight','.5','--component','missing']]:self.assertNotEqual(self.invoke(args)[0],0)
 def test_freeform_flags_outside_quotes_preserve_exact_input(self):
  text='Improve "checkout" latency — without changing billing'
  self.assertEqual(cli._preprocess_args([text,'--json','--confirm']),['classify',text,'--json','--confirm'])
  self.assertEqual(cli._preprocess_args(['--json',text]),['--json','classify',text])
  self.assertEqual(cli._preprocess_args(['Explain the literal --json flag']),['classify','Explain the literal --json flag'])
 def test_quoted_command_with_outer_flags_is_deterministic(self):
  with patch.object(freeform_routing,'route',side_effect=AssertionError('unnecessary inference')):
   for args in [['status executors','--json'],['--json','status executors']]:
    rc,out,err=self.invoke(args);self.assertEqual(rc,0,err);json.loads(out)
 def test_quoted_command_match_and_freeform_fallback(self):
  self.assertEqual(command_surface.match_quoted_command(self.parser,'status executors'),['status','executors'])
  for text in ['improve retention by 20%','pause the task if the deploy fails','goal list and fix every failing test','He said "hello": what should we do?']:
   self.assertIsNone(command_surface.match_quoted_command(self.parser,text));self.assertEqual(cli._preprocess_args([text]),['classify',text])
 def test_api_named_positionals_arrays_and_false(self):
  self.assertEqual(api_interface.build_argv(self.parser,'product switch',{'name':'Product with spaces'}),['product','switch','Product with spaces'])
  argv=api_interface.build_argv(self.parser,'add goal',{'title':'Improve','success_measure':'Latency','reason':'user','depends_on':['a','b']});self.assertEqual(self.parser.parse_args(argv).depends_on,['a','b'])
  argv=api_interface.build_argv(self.parser,'data add',{'name':'sample','type':'csv','connect':'input.csv','auto':False});self.assertIn('false',argv);self.assertFalse(self.parser.parse_args(argv).auto)
 def test_api_all_registered_help_paths(self):
  for name in command_surface.child_parsers(self.parser):
   with self.subTest(command=name):
    result=api_interface.execute(self.parser,lambda argv: self.invoke_help(argv)[0],argv=[name,'--help'])
    self.assertEqual(result['exit_code'],0,result)
 def test_api_call_positionals_error_and_batch_continue(self):
  rc,out,err=self.invoke(['api','call','--command','status runtime']);self.assertEqual(rc,0,err);self.assertEqual(json.loads(out)['status'],'ok')
  rc,out,err=self.invoke(['api','call','--command','this is prose']);self.assertEqual(rc,2);self.assertEqual(json.loads(out)['status'],'error')
  rc,out,err=self.invoke(['api','call','--command','product switch','--params','[]']);self.assertEqual(rc,2);json.loads(out)
  file=Path(self.tmp.name)/'batch.json';file.write_text(json.dumps([{'command':'configuration effort','params':[]},{'command':'status runtime'}]))
  rc,out,err=self.invoke(['api','batch','--input-json',str(file),'--continue-on-error']);self.assertEqual(rc,2);result=json.loads(out);self.assertEqual(len(result['results']),2);self.assertEqual(result['results'][1]['exit_code'],0)
 def test_api_streaming_requires_explicit_transport(self):
  called=[];result=api_interface.execute(self.parser,lambda argv:called.append(argv),command='auto');self.assertEqual(result['exit_code'],2);self.assertEqual(called,[])
  def runner(argv):print('{"progress":1}');return 0
  with contextlib.redirect_stdout(io.StringIO()) as out:result=api_interface.execute(self.parser,runner,command='auto',stream=True)
  self.assertEqual(result['exit_code'],0);self.assertEqual(json.loads(out.getvalue())['event'],'output')
 def test_api_errors_captured_and_do_not_abort_process(self):
  result=api_interface.execute(self.parser,cli.main,argv=['goal','nonsense']);self.assertEqual(result['exit_code'],2);self.assertIn('invalid choice',result['stderr'])
 def test_api_discovery_includes_nested_and_delegated_commands(self):
  catalog=api_interface.metadata(self.parser);roots={e['command']:e for e in catalog['commands']};self.assertEqual(set(roots),set(command_surface.child_parsers(self.parser)));self.assertEqual(len(roots['portfolio']['children']),30)


class ExecutableScoreCommandTests(unittest.TestCase):
 def test_short_and_canonical_scores_share_route_and_api_grammar(self):
  for args in [['status','scores'],['/status','scores']]:self.assertEqual(cli._preprocess_args(args),['trial','status','scores'])
  parser=grammar();args=parser.parse_args(['status','scores','--compare','parent','--history','--executor','claude','--json']);self.assertEqual(args.compare,'parent');self.assertTrue(args.history)
 def test_score_command_dispatches_without_generic_state(self):
  with patch('urace.trial.main',return_value=0) as run,patch.object(cli,'load_state',side_effect=AssertionError('No core state needed')):
   self.assertEqual(cli.main(['status','scores','--json']),0);run.assert_called_once_with(['status','scores','--json'])

 def test_slash_score_phrase_stays_an_inspection(self):
  with patch('urace.trial.main',return_value=0) as run,patch.object(cli,'load_state',side_effect=AssertionError('No generic state')):
   self.assertEqual(cli.main(['/status scores','--json']),0);self.assertEqual(run.call_args.args[0][:2],['status','scores'])
