import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import efficiency_score as s
from common import atomic

class EfficiencyScore(unittest.TestCase):
    def config(self):return {'enabled':True,'metrics':[dict(name='acceptance_rate_pct',weight=1,direction='higher',target=100),dict(name='tokens_per_accepted_improvement',weight=1,direction='lower',target=1000)]}
    def report(self):return dict(product_id='a',executor='codex',scope='epoch',accounting_epoch={'id':'e'},efficiency={'acceptance_rate_pct':50,'tokens_per_accepted_improvement':2000})
    def test_weighted_score_and_missing_data(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            atomic(Path(d)/'efficiency-config.json',{'profiles':{'*|all':self.config()}})
            self.assertEqual(s.score(self.report())['score'],50)
            r=self.report();r['efficiency']['tokens_per_accepted_improvement']=None
            self.assertIsNone(s.score(r)['score']);self.assertIn('tokens_per_accepted_improvement',s.score(r)['missing_metrics'])
    def test_configuration_rejects_code_and_invalid_numbers(self):
        c=self.config();c['metrics'][0]['name']='__import__("os")'
        with self.assertRaises(ValueError):s.validate(c)
        c=self.config();c['metrics'][0]['target']=float('nan')
        with self.assertRaises(ValueError):s.validate(c)
        c=self.config();c['metrics'][0]['weight']=-1
        with self.assertRaises(ValueError):s.validate(c)
    def test_custom_values_retain_unverified_provenance(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            b=Path(d);atomic(b/'products.json',{'products':[dict(id='a',name='Alpha')]});atomic(b/'accounting-epoch.json',{'id':'e'})
            s.configure({'enabled':True,'metrics':[dict(name='custom.quality',weight=1,direction='higher',target=10)]},'Alpha','codex')
            self.assertIsNone(s.score(self.report())['score'])
            s.record('Alpha','codex','quality',8,'points','unit-test fixture, not live evidence')
            score=s.score(self.report());self.assertEqual(score['score'],80);self.assertEqual(score['components'][0]['provenance']['verification'],'user_supplied_unverified')
            other=self.report();other['product_id']='b';self.assertFalse(s.score(other)['enabled'])
    def test_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            self.assertFalse(s.score(self.report())['enabled'])
    def test_methodology_review_never_claims_best_formula_or_validated_value(self):
        review=s.methodology({'completed_tasks':2,'accepted_improvements':0,'missing_usage':1},self.config(),[],['tokens_per_accepted_improvement'])
        self.assertFalse(review['formula_optimality_established']);self.assertIsNone(review['validated_value_score']);self.assertGreaterEqual(len(review['issues']),3);self.assertFalse(review['automatic_formula_mutation'])

if __name__=='__main__':unittest.main()
