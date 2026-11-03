import json
import tempfile
import unittest
from pathlib import Path
from controls import effective


class ControlsTests(unittest.TestCase):
    def test_trial_high_is_separate_from_native_reasoning_default(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)/'trial';base.mkdir()
            (base/'settings.json').write_text(json.dumps({'resource_effort':'high'}))
            result=effective(base)
            self.assertTrue(result['auto_goals']);self.assertTrue(result['replenish_backlog'])
            self.assertEqual(result['executors']['codex']['resource_effort'],'high')
            self.assertEqual(result['executors']['codex']['native_effort'],'medium')

    def test_canonical_controls_propagate_without_copying_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'trial';base.mkdir()
            path=root/'runtime/urace/config.json';path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'auto_goals':{'enabled':False,'replenish_backlog':True},'resources':{'effort':'high','executor_effort':{'claude':'low'}},'executor':{'native_options':{'codex':{'model':'chosen-model','native_effort':'low'}},'secret':'never-return'}}))
            result=effective(base)
            self.assertFalse(result['replenish_backlog']);self.assertNotIn('never-return',json.dumps(result))
            self.assertEqual(result['executors']['codex']['model'],'chosen-model')
            self.assertEqual(result['executors']['codex']['native_effort'],'low')
            self.assertEqual(result['executors']['claude']['resource_effort'],'low')

    def test_invalid_model_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'trial';base.mkdir();path=root/'runtime/urace/config.json';path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'executor':{'native_options':{'codex':{'model':'--bad-option'}}}}))
            with self.assertRaises(ValueError):effective(base)

    def test_provider_allocation_waits_are_independent_and_effort_controls_idle(self):
        from controls import task_eligibility
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as directory:
            controls=effective(Path(directory))
        controls['executors']['codex']['resource_effort']='high'
        controls['executors']['claude']['resource_effort']='low'
        rows=[{'kind':'finished','provider':p,'at':datetime.fromtimestamp(100,timezone.utc).isoformat(),'wall_seconds':10} for p in ('codex','claude')]
        ready,waits=task_eligibility(['codex','claude'],controls,rows,120)
        self.assertEqual(ready,['codex']);self.assertIn('claude',waits)
        self.assertEqual(task_eligibility(['codex'],controls,rows,114)[0],[])

    def test_detached_executor_stops_before_availability_or_model_calls(self):
        import sys
        import spec_trial as worker
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'trial';base.mkdir()
            config=root/'runtime/urace/config.json';config.parent.mkdir(parents=True)
            config.write_text(json.dumps({'executor':{'enabled':False}}))
            for name,value in [('harness-manifest.json',{}),('settings.json',{'enabled':True}),('trial-clock.json',{'ends_unix':9999999999}),('state.json',{'jobs':[]})]:
                (base/name).write_text(json.dumps(value))
            with patch.object(worker,'BASE',base),patch.object(worker.sys,'argv',['spec_trial.py']),patch.object(worker,'eligible',side_effect=AssertionError('Detached: no provider launch')),patch.object(worker,'status',return_value=0):
                self.assertEqual(worker.main(),0)
            self.assertIn('disabled',json.loads((base/'state.json').read_text())['waits']['operator'])

    def test_registered_provider_disable_is_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'trial';base.mkdir();p=root/'runtime/urace/config.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'executor':{'providers':[{'id':'codex','adapter':'codex-cli','enabled':False},{'id':'claude','adapter':'claude-cli','enabled':True}]}}))
            result=effective(base)
            self.assertFalse(result['executors']['codex']['enabled']);self.assertTrue(result['executors']['claude']['enabled'])
