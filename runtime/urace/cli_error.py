"""Unified CLI error output — consistent JSON or text error format.

All user-facing errors should go through cli_error() so they produce
consistent output regardless of which handler raised them.
"""
from __future__ import annotations

import json
import sys

_EXIT_USAGE = 2      # argparse-style: bad arguments
_EXIT_ERROR = 1      # runtime error
_EXIT_NOTFOUND = 3   # resource not found


def cli_error(
    message: str,
    *,
    hint: str = '',
    code: str = '',
    as_json: bool = False,
    exit_code: int = _EXIT_ERROR,
) -> int:
    """Print a structured error and return exit_code.

    Usage:
        return cli_error('thing not found', hint='run: urace init', as_json=args.json)

    JSON output:  {"status": "error", "error": "...", "hint": "...", "code": "..."}
    Text output:  error: ...\n  hint: ...\n
    """
    if as_json:
        payload: dict = {'status': 'error', 'error': message}
        if hint:
            payload['hint'] = hint
        if code:
            payload['code'] = code
        print(json.dumps(payload, indent=2))
    else:
        print(f'error: {message}', file=sys.stderr)
        if hint:
            print(f'  hint: {hint}', file=sys.stderr)
    return exit_code
