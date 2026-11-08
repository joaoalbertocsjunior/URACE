import json,tempfile,unittest
from pathlib import Path
from common import atomic
from assessment_evidence import assess,wilson

class AssessmentEvidenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);atomic(self.base/'trial-clock.json',{'trial_id':'t','started_unix':0});atomic(self.base/'assessment-epoch.json',{'trial_id':'t','started_unix':100})
 def test_empty_evidence_does_not_become_success(self):
  r=assess(self.base,[],200,engine_sha256='e');self.assertIsNone(r['performance_and_transport_reliability_by_executor']['codex']['transport_success_rate_pct']);self.assertFalse(r['evidence_ladder']['actual_user_value_or_market_fit_established']);self.assertTrue(all(not s['eligible_for_current_engine_claim'] for s in r['quality_effectiveness_and_comparative_evidence'].values()))
 def test_epoch_trial_and_duplicate_receipt_filtering(self):
  row={'trial_id':'t','kind':'finished','provider':'codex','id':'a','at_unix':150,'tokens':20,'wall_seconds':3};r=assess(self.base,[row,row,{**row,'id':'old','at_unix':90},{**row,'id':'other','trial_id':'different'}],200,engine_sha256='e');v=r['performance_and_transport_reliability_by_executor']['codex'];self.assertEqual(v['finished_attempts'],1);self.assertEqual(v['total_tokens'],20);self.assertEqual(r['window']['seconds_observed'],100)
 def test_failed_costs_unknown_usage_and_missing_timing_retained(self):
  rows=[{'trial_id':'t','kind':'finished','provider':'codex','id':'a','at_unix':150,'tokens':20,'wall_seconds':3,'failure':'timeout'},{'trial_id':'t','kind':'finished','provider':'codex','id':'b','at_unix':151,'tokens':None}];v=assess(self.base,rows,200,engine_sha256='e')['performance_and_transport_reliability_by_executor']['codex'];self.assertEqual(v['transport_success_rate_pct'],50);self.assertEqual(v['known_tokens_including_failures'],20);self.assertIsNone(v['total_tokens']);self.assertEqual(v['missing_timing_attempts'],1)
 def test_stale_engine_or_other_trial_excluded_even_when_scores_perfect(self):
  p=self.base/'repository-study-latest.json';atomic(p,{'plan':{'trial_id':'t','engine_sha256':'old'},'output_quality':{'score':100}});r=assess(self.base,[],200,engine_sha256='e');self.assertFalse(r['quality_effectiveness_and_comparative_evidence']['standalone_comparison']['eligible_for_current_engine_claim']);atomic(p,{'plan':{'trial_id':'t','engine_sha256':'e'}});r=assess(self.base,[],200,engine_sha256='e');self.assertTrue(r['quality_effectiveness_and_comparative_evidence']['standalone_comparison']['eligible_for_current_engine_claim'])
 def test_executable_report_uses_its_execution_fingerprint(self):
  atomic(self.base/'executable-benchmark-latest.json',{'trial_id':'t','engine':{'code_fingerprint':'exec'}});r=assess(self.base,[],200,engine_sha256='repository',execution_sha256='exec');self.assertTrue(r['quality_effectiveness_and_comparative_evidence']['executable_versions']['eligible_for_current_engine_claim'])
 def test_invalid_report_is_explicit(self):
  (self.base/'repository-study-latest.json').write_text('[]');r=assess(self.base,[],200,engine_sha256='e');self.assertEqual(r['quality_effectiveness_and_comparative_evidence']['standalone_comparison']['status'],'INVALID')
 def test_perfect_small_sample_still_has_uncertainty(self):
  self.assertIsNone(wilson(0,0));one=wilson(1,1);hundred=wilson(100,100);self.assertLess(one['lower'],.3);self.assertGreater(hundred['lower'],.96);self.assertLess(hundred['lower'],1)

if __name__=='__main__':unittest.main()
