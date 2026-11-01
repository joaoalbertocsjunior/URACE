"""Non-blocking startup hints: state format compatibility and pending improvement signals."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def hints(config: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    """Return [{level, code, message, action}]. Never raises; empty list on any error."""
    result: list[dict[str, Any]] = []
    _format_hints(config, result)
    _improvement_hints(root, result)
    return result


def _format_hints(config: dict[str, Any], result: list[dict[str, Any]]) -> None:
    try:
        from .version import FORMAT_VERSION, MIN_FORMAT_VERSION
        from ._common import state_path
        path = state_path(config)
        if not path.exists():
            return
        sv = json.loads(path.read_text(encoding='utf-8')).get('schema_version', 1)
        if sv < MIN_FORMAT_VERSION:
            result.append({'level': 'WARNING', 'code': 'FORMAT_TOO_OLD',
                           'message': f'State format {sv} predates minimum {MIN_FORMAT_VERSION}; migration required',
                           'action': 'urace check --migration-dry-run'})
        elif sv > FORMAT_VERSION:
            result.append({'level': 'WARNING', 'code': 'FORMAT_NEWER',
                           'message': f'State was written by a newer runtime (format {sv}); this runtime may misread it',
                           'action': 'upgrade urace to match the state format version'})
    except Exception:
        pass


def _improvement_hints(root: Path, result: list[dict[str, Any]]) -> None:
    try:
        trial = root / 'trial'
        if (trial / 'runtime-deployment-pending.json').exists():
            result.append({'level': 'INFO', 'code': 'IMPROVEMENT_READY',
                           'message': 'Runtime improvement qualified and pending deployment',
                           'action': 'urace watch report'})
            return
        cycle_file = trial / 'runtime-cycle-latest.json'
        if cycle_file.exists():
            stage = json.loads(cycle_file.read_text(encoding='utf-8')).get('stage', '')
            if stage == 'AWAITING_APPROVAL':
                result.append({'level': 'INFO', 'code': 'IMPROVEMENT_AWAITING_APPROVAL',
                               'message': 'Runtime improvement awaiting owner approval',
                               'action': 'urace watch report'})
    except Exception:
        pass
