"""Shared test utilities — single import, structural enforcement of dual-namespace patches."""
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def patch_config_path(path):
    from urace import cli as _cli, _common as _cm
    with patch.object(_cli, 'CONFIG_PATH', path), patch.object(_cm, 'CONFIG_PATH', path):
        yield


@contextmanager
def patch_cli_config_state(config=None, state=None):
    """Patch both load_config and load_state_for_read on the cli module.

    Usage::

        with patch_cli_config_state(config=my_config, state=my_state):
            run_some_cli_command(args)
    """
    import urace.cli as _cli

    _sentinel = object()
    config_val = config if config is not None else _sentinel
    state_val = state if state is not None else _sentinel

    patches = []
    if config_val is not _sentinel:
        patches.append(patch.object(_cli, "load_config", return_value=config_val))
    if state_val is not _sentinel:
        patches.append(patch.object(_cli, "load_state_for_read", return_value=state_val))

    if not patches:
        yield
        return

    ctx = patches[0]
    for p in patches[1:]:
        ctx = _nested(ctx, p)

    with ctx:
        yield


class _nested:
    """Stack two context managers without nesting syntax."""

    def __init__(self, outer, inner):
        self._outer = outer
        self._inner = inner

    def __enter__(self):
        self._outer.__enter__()
        self._inner.__enter__()
        return self

    def __exit__(self, *exc):
        inner_exc = self._inner.__exit__(*exc)
        outer_exc = self._outer.__exit__(*exc)
        return inner_exc or outer_exc
