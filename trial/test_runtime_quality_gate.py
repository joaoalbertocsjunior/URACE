"""Tests for runtime quality gate evaluation."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import runtime_quality_gate as rqg


class TestQualify(unittest.TestCase):
    def test_passes_when_delta_meets_minimum(self):
        self.assertTrue(rqg.qualify(60.0, 65.0, 5.0))
        self.assertTrue(rqg.qualify(60.0, 65.0))  # default minimum_delta

    def test_passes_at_exact_minimum(self):
        self.assertTrue(rqg.qualify(60.0, 65.0, 5.0))

    def test_rejects_below_minimum(self):
        self.assertFalse(rqg.qualify(60.0, 64.9, 5.0))

    def test_rejects_regression(self):
        self.assertFalse(rqg.qualify(60.0, 55.0, 5.0))

    def test_rejects_no_change(self):
        self.assertFalse(rqg.qualify(60.0, 60.0, 5.0))

    def test_rejects_non_finite_baseline(self):
        self.assertFalse(rqg.qualify(None, 65.0, 5.0))
        self.assertFalse(rqg.qualify(float('nan'), 65.0, 5.0))

    def test_rejects_non_finite_candidate(self):
        self.assertFalse(rqg.qualify(60.0, None, 5.0))

    def test_negative_delta_raises(self):
        with self.assertRaises(ValueError):
            rqg.qualify(60.0, 65.0, -1.0)


class RuntimeOnlyGateTests(unittest.TestCase):
 def test_legacy_specification_score_is_unavailable_for_runtime(self):
  with tempfile.TemporaryDirectory() as d:
   (Path(d)/'executable-benchmark-latest.json').write_text(json.dumps({'scorecard':{'overall_quality_score':99}}));self.assertIsNone(rqg.read_latest_score(d));self.assertEqual(rqg.gate_decision(d,{},100)['decision'],'GATE_UNAVAILABLE')
 def test_threshold_validation(self):
  for value in (True,float('nan'),-1):
   with self.assertRaises(ValueError):rqg.gate_config({'runtime_workflow':{'quality_gate_minimum_score_delta':value}})
 def test_custom_metric_is_not_silently_reinterpreted(self):
  self.assertEqual(rqg.gate_decision('.',{'runtime_workflow':{'quality_gate_metric':'custom'}},100)['decision'],'GATE_UNAVAILABLE')
