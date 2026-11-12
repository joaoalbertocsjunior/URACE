"""Shared test utilities — single import, structural enforcement of dual-namespace patches."""
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def patch_config_path(path):
    from urace import cli as _cli, _common as _cm
    with patch.object(_cli, 'CONFIG_PATH', path), patch.object(_cm, 'CONFIG_PATH', path):
        yield
