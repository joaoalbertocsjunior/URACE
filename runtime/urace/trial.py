"""Bridge to the isolated specification trial without importing its module globals."""
from pathlib import Path
import subprocess
import os
import sys


def main(arguments: list[str]) -> int:
    entrypoint = Path(__file__).resolve().parents[2] / "trial" / "urace"
    if not entrypoint.is_file():
        print("urace: specification trial is not installed", file=sys.stderr)
        return 1
    result = subprocess.run([sys.executable, str(entrypoint), *arguments], check=False, capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def workflow_root() -> Path:
    return Path(__file__).resolve().parents[2] / 'trial'


def run_workflow(cycles: int, *, dry_run: bool = False, interval: float = 5,
                 json_mode: bool = False, quiet: bool = False) -> int:
    """Run the selected product workflow under the canonical auto entrypoint."""
    import json
    import time
    root = workflow_root()
    if dry_run:
        clock = json.loads((root/'trial-clock.json').read_text())
        pointer = json.loads((root/'active-version.json').read_text())
        print(json.dumps({'mode':'dry-run','workflow':'specification-trial',
                          'trial_id':clock['trial_id'],'active_version':pointer['version'],
                          'cycles_run':0,'executor_calls':0,'writes':0}))
        return 0
    owner=None
    try:
        candidate=json.loads((root/'trial-supervisor.json').read_text());pid=candidate['pid']
        if type(pid) is int and pid>0 and pid!=os.getpid() and Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]==candidate.get('start_ticks'):owner=candidate
    except (OSError,ValueError,TypeError,KeyError,IndexError):pass
    if owner:
        print(json.dumps({'state':'ALREADY_RUNNING','supervisor_pid':owner['pid'],'duplicate_controller_started':False}));return 0
    count = 0
    while cycles == 0 or count < cycles:
        clock = json.loads((root/'trial-clock.json').read_text())
        if time.time() >= clock['ends_unix']:
            print(json.dumps({'state':'TRIAL_ENDED','trial_id':clock['trial_id'],
                              'cycles_run':count,'history_preserved':True}))
            return 0
        result = subprocess.run([sys.executable, str(root/'spec_trial.py')], check=False,
                                capture_output=True, text=True)
        if json_mode:
            sys.stdout.write(result.stdout)
        elif not quiet and result.stdout.strip():
            try:
                status = json.loads(result.stdout.splitlines()[-1])
                print(f"{status['state']}: {status['jobs']} completed tasks; "
                      f"{status['accepted_improvements']} accepted versions; "
                      f"{status['native_calls']} executor calls")
            except (ValueError, KeyError):
                sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode:
            return result.returncode
        count += 1
        if cycles == 0 or count < cycles:
            time.sleep(interval)
    return 0
