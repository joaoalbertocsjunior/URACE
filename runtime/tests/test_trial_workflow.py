import io
import json
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urace import cli, trial


class TrialWorkflowTests(unittest.TestCase):
    def test_plain_status_uses_same_active_workflow_as_json_status(self):
        self.assertEqual(cli._preprocess_args(['status']),['status'])
        with patch.object(cli,'load_config',return_value={'execution_workflow':'specification-trial'}), patch.object(trial,'main',return_value=0) as run:
            self.assertEqual(cli.main(['status']),0)
            run.assert_called_once_with(['status','runtime'])

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        (self.root/'trial-clock.json').write_text(json.dumps({'trial_id':'fixture','ends_unix':time.time()+60}))
        (self.root/'active-version.json').write_text(json.dumps({'version':0}))

    def test_dry_run_never_calls_a_worker_or_changes_files(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        with patch.object(trial,'workflow_root',return_value=self.root), patch.object(trial.subprocess,'run',side_effect=AssertionError('No worker')), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(trial.run_workflow(1,dry_run=True),0)
        self.assertEqual(json.loads(output.getvalue())['executor_calls'],0)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_auto_selects_workflow_without_loading_legacy_state(self):
        config={'state_path':str(self.root/'legacy-state.json'),'execution_workflow':'specification-trial'}
        with patch.object(cli,'load_config',return_value=config),patch.object(cli,'load_state',side_effect=AssertionError('Legacy state')),patch.object(trial,'run_workflow',return_value=0) as run:
            self.assertEqual(cli.main(['auto','--cycles','1','--json']),0)
            run.assert_called_once_with(1,dry_run=False,interval=5,json_mode=True,quiet=False)

    def test_finite_cycles_preserve_worker_failure_and_do_not_replay(self):
        with patch.object(trial,'workflow_root',return_value=self.root),patch.object(trial.subprocess,'run') as run,redirect_stdout(io.StringIO()):
            run.return_value.returncode=2;run.return_value.stdout='';run.return_value.stderr=''
            self.assertEqual(trial.run_workflow(3,json_mode=True),2);self.assertEqual(run.call_count,1)

    def test_trial_expiry_does_not_reset_clock_or_invoke_executor(self):
        p=self.root/'trial-clock.json';p.write_text(json.dumps({'trial_id':'fixture','ends_unix':0}));before=p.read_bytes()
        with patch.object(trial,'workflow_root',return_value=self.root),patch.object(trial.subprocess,'run',side_effect=AssertionError('Expired')),redirect_stdout(io.StringIO()) as output:
            self.assertEqual(trial.run_workflow(0),0)
        self.assertEqual(json.loads(output.getvalue())['state'],'TRIAL_ENDED');self.assertEqual(before,p.read_bytes())

    def test_status_uses_active_workflow_counters_and_typed_filters(self):
        config={'execution_workflow':'specification-trial'}
        with patch.object(cli,'load_config',return_value=config),patch.object(trial,'main',return_value=0) as run:
            self.assertEqual(cli.main(['status','resources','--product','URACE.md','--executor','claude','--scope','trial','--json']),0)
            run.assert_called_once_with(['status','resources','--product','URACE.md','--executor','claude','--scope','trial','--json'])
        with patch.object(cli,'load_config',return_value=config),patch.object(trial,'main',return_value=0) as run:
            self.assertEqual(cli.main(['status','--json']),0)
            run.assert_called_once_with(['status','runtime','--json'])
