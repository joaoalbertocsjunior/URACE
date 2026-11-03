import argparse,contextlib,io,json,unittest
from unittest.mock import patch
from urace import cli,command_surface
class Captured(BaseException):pass
class JsonFlags(unittest.TestCase):
 def test_nested_data_json_alias_and_complete_format_discovery(self):
  parsers=[]
  def intercept(parser,*args,**kwargs):parsers.append(parser);raise Captured()
  with patch.object(argparse.ArgumentParser,'parse_known_args',intercept):
   try:cli.main(['commands'])
   except Captured:pass
  parser=parsers[0];args=parser.parse_args(['data','add','sample','--type','json','--connect','input.json','--json']);self.assertEqual(args.format,'json')
  def visit(p):
   if '--format' in p._option_string_actions:self.assertIn('--json',p._option_string_actions)
   for child in command_surface.child_parsers(p).values():visit(child)
  visit(parser)

 def test_quoted_nested_json_command_does_not_use_inference(self):
  with patch.object(cli.freeform_routing,'route',side_effect=AssertionError('unnecessary inference')),patch.object(cli,'load_state_for_read',return_value={'data_source_records':[]}),contextlib.redirect_stdout(io.StringIO()) as out:
   self.assertEqual(cli.main(['data status --json']),0)
  self.assertEqual(json.loads(out.getvalue())['action'],'data-status')
