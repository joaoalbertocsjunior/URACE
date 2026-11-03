"""Tests for tui.py — model, routing, and collect logic (no curses terminal needed)."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from urace import tui,version

class FormatScoreTests(unittest.TestCase):
 def test_none_returns_na(self):self.assertEqual(tui.format_score(None),'n/a')
 def test_float_two_decimal(self):self.assertEqual(tui.format_score(0.742),'0.74')
 def test_zero(self):self.assertEqual(tui.format_score(0.0),'0.00')
 def test_one(self):self.assertEqual(tui.format_score(1.0),'1.00')

class TruncateTests(unittest.TestCase):
 def test_short_string_unchanged(self):self.assertEqual(tui._truncate('hi',10),'hi')
 def test_exact_width_unchanged(self):self.assertEqual(tui._truncate('hello',5),'hello')
 def test_long_string_truncated(self):r=tui._truncate('hello world',6);self.assertEqual(len(r),6);self.assertTrue(r.endswith('…'))
 def test_zero_width(self):self.assertEqual(tui._truncate('abc',0),'')

class RouteInputTests(unittest.TestCase):
 def test_empty_returns_none(self):argv,_=tui.route_input('');self.assertIsNone(argv)
 def test_slash_help(self):argv,lbl=tui.route_input('/help');self.assertEqual(argv,['help'])
 def test_slash_check(self):argv,_=tui.route_input('/check');self.assertEqual(argv,['check'])
 def test_slash_pause(self):argv,_=tui.route_input('/pause');self.assertEqual(argv,['pause'])
 def test_slash_resume(self):argv,_=tui.route_input('/resume');self.assertEqual(argv,['resume'])
 def test_slash_auto(self):argv,_=tui.route_input('/auto');self.assertIn('auto',argv)
 def test_slash_status(self):argv,_=tui.route_input('/status');self.assertEqual(argv,['status'])
 def test_slash_vitals(self):argv,_=tui.route_input('/vitals');self.assertEqual(argv,['vitals'])
 def test_slash_goals(self):argv,_=tui.route_input('/goals');self.assertEqual(argv,['goal','list'])
 def test_slash_inbox(self):argv,_=tui.route_input('/inbox');self.assertEqual(argv,['inbox','list'])
 def test_slash_unknown_strips_slash(self):argv,_=tui.route_input('/custom-cmd arg');self.assertEqual(argv,['custom-cmd','arg'])
 def test_direct_goal_command(self):argv,_=tui.route_input('goal list');self.assertEqual(argv,['goal','list'])
 def test_direct_pause(self):argv,_=tui.route_input('pause');self.assertEqual(argv,['pause'])
 def test_nlp_fallthrough(self):argv,lbl=tui.route_input('improve auth flow');self.assertEqual(argv,['classify','improve auth flow'])
 def test_whitespace_only_returns_none(self):argv,_=tui.route_input('   ');self.assertIsNone(argv)
 def test_label_contains_cmd(self):_,lbl=tui.route_input('/check');self.assertIn('check',lbl)
 def test_nlp_label_contains_classify(self):_,lbl=tui.route_input('some nlp intent');self.assertIn('classif',lbl)

class DashboardDataTests(unittest.TestCase):
 def test_defaults(self):
  d=tui.DashboardData()
  self.assertEqual(d.lifecycle,'UNKNOWN');self.assertIsNone(d.score);self.assertEqual(d.events,[]);self.assertEqual(d.hints,[])
 def test_error_field(self):
  d=tui.DashboardData();d.error='oops'
  self.assertEqual(d.error,'oops')

class CollectTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def test_no_state_sets_error(self):
  with patch('urace._common.load_state_for_read',return_value=None):
   d=tui.collect({},self.root)
  self.assertIsNotNone(d.error);self.assertIn('urace init',d.error)
 def test_state_populates_lifecycle(self):
  state={'lifecycle_state':'ACTIVE','executor_state':{},'progress_profiles':[{'measures':{},'next_follow_up':None}]}
  with patch('urace._common.load_state_for_read',return_value=state),patch('urace.inspection.vitals_snapshot',side_effect=Exception('skip')):
   d=tui.collect({'product':'myapp'},self.root)
  self.assertEqual(d.lifecycle,'ACTIVE');self.assertEqual(d.product,'myapp')
 def test_pending_deploy_sets_status(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-deployment-pending.json').write_text('{}')
  state={'lifecycle_state':'ACTIVE','executor_state':{},'progress_profiles':[{'measures':{},'next_follow_up':None}]}
  with patch('urace._common.load_state_for_read',return_value=state):
   d=tui.collect({},self.root)
  self.assertEqual(d.improvement_status,'PENDING_DEPLOY')
 def test_awaiting_approval_sets_status(self):
  trial=self.root/'trial';trial.mkdir()
  (trial/'runtime-cycle-latest.json').write_text(json.dumps({'stage':'AWAITING_APPROVAL'}))
  state={'lifecycle_state':'ACTIVE','executor_state':{},'progress_profiles':[{'measures':{},'next_follow_up':None}]}
  with patch('urace._common.load_state_for_read',return_value=state):
   d=tui.collect({},self.root)
  self.assertEqual(d.improvement_status,'AWAITING_APPROVAL')
 def test_exception_sets_error(self):
  with patch('urace._common.load_state_for_read',side_effect=RuntimeError('boom')):
   d=tui.collect({},self.root)
  self.assertIsNotNone(d.error);self.assertIn('boom',d.error)
 def test_events_from_executor_calls(self):
  calls=[{'at':'2024-01-01T10:00:00Z','stage':'execution','reason':'test-goal','outcome':'accepted'}]
  state={'lifecycle_state':'ACTIVE','executor_state':{'executor_calls':calls},'progress_profiles':[{'measures':{},'next_follow_up':None}]}
  with patch('urace._common.load_state_for_read',return_value=state):
   d=tui.collect({},self.root)
  self.assertEqual(len(d.events),1);self.assertEqual(d.events[0]['kind'],'EXECUTION');self.assertEqual(d.events[0]['status'],'accepted')

class DispatchTests(unittest.TestCase):
 def test_dispatch_success(self):
  with patch('urace.cli.main',return_value=0) as m:
   r=tui._dispatch(['check'])
  self.assertEqual(r,0)
 def test_dispatch_systemexit_code(self):
  with patch('urace.cli.main',side_effect=SystemExit(1)):
   r=tui._dispatch(['check'])
  self.assertEqual(r,1)
 def test_dispatch_exception_returns_1(self):
  with patch('urace.cli.main',side_effect=ValueError('bad')):
   r=tui._dispatch(['check'])
  self.assertEqual(r,1)

class LaunchNoTtyTests(unittest.TestCase):
 def test_no_tty_calls_fallback(self):
  with patch('sys.stdout') as mock_stdout:
   mock_stdout.isatty.return_value=False
   with patch.object(tui,'_no_tty_fallback',return_value=0) as fb:
    tui.launch({},Path('/tmp'))
  fb.assert_called_once()

import sys
