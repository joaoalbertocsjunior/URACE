import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import product_resources as p
from common import atomic

class ProductResources(unittest.TestCase):
    def test_lifetime_reads_legacy_archive_names_without_json_suffix(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'BASE',Path(d)):
            b=Path(d);atomic(b/'products.json',dict(products=[dict(id='a',name='Alpha')],state_product_id='a'))
            atomic(b/'state.json',{'jobs':[]})
            atomic(b/'history/state.json.before-old-trial',{'jobs':[dict(id='old',product_id='a',outcome='ACCEPTED_EDITORIAL_IMPROVEMENT')]})
            with patch.object(p,'events',return_value=[]):
                r=p.report('a','lifetime');self.assertEqual(r['completed_tasks'],1);self.assertEqual(r['accepted_improvements'],1)
    def test_trial_report_excludes_all_older_tokens_and_outcomes(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'BASE',Path(d)):
            b=Path(d);atomic(b/'products.json',dict(products=[dict(id='a',name='Alpha')],state_product_id='a'));atomic(b/'trial-clock.json',dict(trial_id='new'));atomic(b/'state.json',dict(jobs=[dict(id='old',trial_id='old',outcome='ACCEPTED_EDITORIAL_IMPROVEMENT'),dict(id='new',trial_id='new',outcome='REJECTED_OR_DEFERRED')]))
            rows=[]
            for trial,tokens in [('old',900),('new',100)]:rows.extend([dict(kind='reserved',id=trial,provider='codex',product_id='a',trial_id=trial,at_unix=1),dict(kind='finished',id=trial,product_id='a',trial_id=trial,tokens=tokens,wall_seconds=1)])
            with patch.object(p,'events',return_value=rows):
                r=p.report('a','trial');self.assertEqual(r['known_tokens'],100);self.assertEqual(r['completed_tasks'],1);self.assertEqual(r['accepted_improvements'],0);self.assertEqual(p.report('a','lifetime')['known_tokens'],1000)
    def test_efficiency_does_not_hide_failure_or_unknown_usage(self):
        e=p.efficiency(dict(known_tokens=1000,missing_usage=0),1,4,3600)
        self.assertEqual(e['acceptance_rate_pct'],25);self.assertEqual(e['tokens_per_accepted_improvement'],1000);self.assertEqual(e['accepted_improvements_per_elapsed_hour'],1)
        e=p.efficiency(dict(known_tokens=1000,missing_usage=0),0,4,3600);self.assertIsNone(e['tokens_per_accepted_improvement']);self.assertEqual(e['accepted_improvements_per_million_tokens'],0)
        e=p.efficiency(dict(known_tokens=1000,missing_usage=1),1,4,3600);self.assertIsNone(e['tokens_per_accepted_improvement']);self.assertFalse(e['usage_complete'])
    def test_products_are_separate_and_reading_does_not_spend(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'BASE',Path(d)):
            b=Path(d);atomic(b/'products.json',dict(products=[dict(id='a',name='Alpha'),dict(id='b',name='Beta')]))
            rows=[]
            for product,tokens in [('a',100),('b',900)]:
                rows.extend([dict(kind='reserved',id=product,provider='codex',product_id=product,at_unix=1),dict(kind='finished',id=product,product_id=product,tokens=tokens,wall_seconds=2)])
            with patch.object(p,'events',return_value=rows):
                self.assertEqual(p.report('Alpha','lifetime')['known_tokens'],100);self.assertEqual(p.report('b','lifetime')['known_tokens'],900)
                with self.assertRaises(ValueError):p.report('Unknown')
    def test_epoch_reset_does_not_change_product_lifetime(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'BASE',Path(d)):
            b=Path(d);atomic(b/'products.json',dict(products=[dict(id='a',name='Alpha')]))
            atomic(b/'accounting-epoch.json',dict(product_id='a',started_unix=10,started_at='2026',excluded_jobs=[]))
            rows=[dict(kind='reserved',id='r',provider='codex',product_id='a',at_unix=1),dict(kind='finished',id='r',product_id='a',tokens=100,wall_seconds=2)]
            with patch.object(p,'events',return_value=rows):
                self.assertEqual(p.report('a')['known_tokens'],0);self.assertEqual(p.report('a','lifetime')['known_tokens'],100)
    def test_product_executor_and_global_totals_agree(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'BASE',Path(d)):
            b=Path(d);atomic(b/'products.json',dict(products=[dict(id='a',name='Alpha'),dict(id='b',name='Beta')]))
            rows=[]
            for i,(product,executor,tokens) in enumerate([('a','codex',100),('a','claude',200),('b','codex',900)]):
                rows.extend([dict(kind='reserved',id=str(i),provider=executor,product_id=product,at_unix=1),dict(kind='finished',id=str(i),product_id=product,tokens=tokens,wall_seconds=2)])
            with patch.object(p,'events',return_value=rows):
                self.assertEqual(p.overall('lifetime')['known_tokens'],1200);self.assertEqual(p.overall('lifetime','codex')['known_tokens'],1000);self.assertEqual(p.report('a','lifetime','claude')['known_tokens'],200);self.assertEqual(p.overall('lifetime')['providers']['codex']['known_tokens'],1000)
    def test_overall_rejects_ambiguous_legacy_binding(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'BASE',Path(d)):
            atomic(Path(d)/'products.json',dict(products=[dict(id='a',name='Alpha',legacy_ledger_binding=True),dict(id='b',name='Beta',legacy_ledger_binding=True)]))
            with self.assertRaises(ValueError):p.overall()
    def test_legacy_attribution_requires_explicit_binding(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'BASE',Path(d)):
            b=Path(d);rows=[dict(kind='reserved',id='r',provider='codex',at_unix=1),dict(kind='finished',id='r',tokens=100,wall_seconds=2)]
            with patch.object(p,'events',return_value=rows):
                atomic(b/'products.json',dict(products=[dict(id='a',name='Alpha')]))
                self.assertEqual(p.report('a')['known_tokens'],0)
                atomic(b/'products.json',dict(products=[dict(id='a',name='Alpha',legacy_ledger_binding=True)]))
                self.assertEqual(p.report('a')['known_tokens'],100);self.assertEqual(p.report('a')['legacy_events_attributed_by_explicit_ledger_binding'],2)

if __name__=='__main__':unittest.main()
