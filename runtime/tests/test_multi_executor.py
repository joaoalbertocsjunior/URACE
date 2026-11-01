"""Tests for multi_executor.py — multi-plan selection."""
import unittest
from urace import multi_executor as me

class SettingsTests(unittest.TestCase):
 def test_disabled_by_default(self):s=me.settings({});self.assertFalse(s['enabled'])
 def test_enabled_via_config(self):
  cfg={'executor':{'multi_plan_selection':{'enabled':True,'max_candidates':2}}}
  s=me.settings(cfg);self.assertTrue(s['enabled']);self.assertEqual(s['max_candidates'],2)
 def test_non_bool_enabled_defaults_false(self):
  cfg={'executor':{'multi_plan_selection':{'enabled':'yes'}}}
  s=me.settings(cfg);self.assertFalse(s['enabled'])
 def test_max_candidates_clamped(self):
  cfg={'executor':{'multi_plan_selection':{'enabled':True,'max_candidates':99}}}
  s=me.settings(cfg);self.assertEqual(s['max_candidates'],5)

class ScoreProposalTests(unittest.TestCase):
 def _state(self):return {'constraints':[],'current_objective':'obj-1','operations':[]}
 def test_returns_total(self):s=me.score_proposal({},{},self._state());self.assertIn('total',s)
 def test_total_in_range(self):s=me.score_proposal({},{},self._state());self.assertGreaterEqual(s['total'],0.0);self.assertLessEqual(s['total'],1.0)
 def test_goal_alignment_bonus_when_objective_referenced(self):
  p={'message':'working on obj-1 improvement'}
  s=me.score_proposal(p,{},self._state())
  s2=me.score_proposal({'message':'unrelated'},{},self._state())
  self.assertGreaterEqual(s['goal_alignment'],s2['goal_alignment'])
 def test_constraint_violation_reduces_score(self):
  state={'constraints':[{'text':'do not modify auth'}],'current_objective':'','operations':[]}
  p={'message':'do not modify auth is mentioned in this proposal'}
  s=me.score_proposal(p,{},state)
  self.assertLess(s['constraint_compliance'],1.0)

class SelectBestTests(unittest.TestCase):
 def test_selects_highest_total(self):
  a={'provider_id':'a','proposal':{'a':1},'score':{'total':0.5}}
  b={'provider_id':'b','proposal':{'b':1},'score':{'total':0.9}}
  c={'provider_id':'c','proposal':{'c':1},'score':{'total':0.3}}
  winner=me.select_best([a,b,c]);self.assertEqual(winner['provider_id'],'b')
 def test_raises_on_empty(self):
  with self.assertRaises(ValueError):me.select_best([])

class GenerateAndSelectDisabledTest(unittest.TestCase):
 def test_returns_none_when_disabled(self):
  result=me.generate_and_select({},{},(lambda *a:{}))
  self.assertIsNone(result)

import sys
