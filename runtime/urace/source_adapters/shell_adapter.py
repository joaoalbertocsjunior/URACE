"""Shell source adapter — runs a command and captures its output as an observation."""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

_MAX_OUTPUT_BYTES = 65_536


class ShellAdapter(NullSourceAdapter):
    kind = 'shell'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--command', default=None, help='Command to run (no shell expansion)')
        subparser.add_argument('--cwd', default=None, help='Absolute working directory')
        subparser.add_argument('--timeout', type=int, default=30, help='Timeout in seconds')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        command = getattr(args, 'command', None) or ''
        if not name:
            raise ValueError('source add --kind shell requires a name')
        if not command:
            raise ValueError('source add --kind shell requires --command')
        # Reject shell metacharacters to prevent injection
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
            'timeout': int(getattr(args, 'timeout', None) or 30),
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
                'timeout': kwargs.get('timeout', 30),
                'last_exit_code': None,
                'last_run_at': None,
                'output_bytes': None,
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
        timeout = astate.get('timeout', 30)
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
            astate['last_exit_code'] = -1
            astate['last_run_at'] = now()
            _set_source(state, source_id, record)
            return {'synced': False, 'reason': 'timeout'}
        output = result.stdout[:_MAX_OUTPUT_BYTES]
        astate['last_exit_code'] = result.returncode
        astate['last_run_at'] = now()
        astate['output_bytes'] = len(output)
        _set_source(state, source_id, record)
        return {
            'synced': result.returncode == 0,
            'exit_code': result.returncode,
            'output_bytes': len(output),
        }


    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        if action != 'run':
            return {'acted': False, 'reason': f'unknown action: {action}'}
        return self._sync(config, state, source_id) | {'acted': True}


SOURCE_REGISTRY.register(ShellAdapter())
