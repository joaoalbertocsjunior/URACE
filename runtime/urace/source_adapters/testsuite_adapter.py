"""Test suite source adapter — runs tests and reports pass/fail counts."""
from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

_MAX_OUTPUT_BYTES = 131_072


class TestSuiteAdapter(NullSourceAdapter):
    kind = 'test_suite'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--command', default=None, help='Test command (e.g. pytest --tb=no -q)')
        subparser.add_argument('--cwd', default=None, help='Absolute working directory')
        subparser.add_argument('--timeout', type=int, default=120)
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        command = getattr(args, 'command', None) or ''
        if not name:
            raise ValueError('source add --kind test_suite requires a name')
        if not command:
            raise ValueError('source add --kind test_suite requires --command')
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            raise ValueError(f'invalid command syntax: {exc}') from exc
        if not parts:
            raise ValueError('--command must not be empty')
        cwd = getattr(args, 'cwd', None)
        if cwd and not Path(cwd).is_absolute():
            raise ValueError('--cwd must be an absolute path')
        return {
            'kind': self.kind,
            'command': command,
            'cwd': cwd,
            'timeout': int(getattr(args, 'timeout', None) or 120),
        }

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'command': kwargs.get('command', ''),
                'cwd': kwargs.get('cwd'),
                'timeout': kwargs.get('timeout', 120),
                'last_run_at': None,
                'passed': None,
                'failed': None,
                'exit_code': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        command = astate.get('command', '')
        cwd = astate.get('cwd')
        timeout = astate.get('timeout', 120)
        if not command:
            return {'synced': False, 'reason': 'no command configured'}
        try:
            parts = shlex.split(command)
            result = subprocess.run(
                parts,
                capture_output=True,
                cwd=cwd,
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            astate['last_run_at'] = now()
            astate['exit_code'] = -1
            _set_source(state, source_id, record)
            return {'synced': False, 'reason': 'timeout'}
        astate['last_run_at'] = now()
        astate['exit_code'] = result.returncode
        # Try to parse pytest-style summary line: "X passed, Y failed"
        output = result.stdout.decode('utf-8', errors='replace')
        passed, failed = _parse_pytest_summary(output)
        astate['passed'] = passed
        astate['failed'] = failed
        _set_source(state, source_id, record)
        # Update product_profile test baseline
        pp = state.setdefault('product_profile', {})
        pp['test_pass_count'] = passed
        pp['test_fail_count'] = failed
        pp['test_source_id'] = source_id
        return {
            'synced': result.returncode == 0,
            'exit_code': result.returncode,
            'passed': passed,
            'failed': failed,
        }

    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        if action != 'run':
            return {'acted': False, 'reason': f'unknown action: {action}'}
        return self._sync(config, state, source_id) | {'acted': True}


def _parse_pytest_summary(output: str) -> tuple[int | None, int | None]:
    import re
    passed = failed = None
    m = re.search(r'(\d+) passed', output)
    if m:
        passed = int(m.group(1))
    m = re.search(r'(\d+) failed', output)
    if m:
        failed = int(m.group(1))
    return passed, failed


SOURCE_REGISTRY.register(TestSuiteAdapter())
