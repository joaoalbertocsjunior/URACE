"""Tests for runtime/urace/control_server.py (phase U4)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from urace.control_server import build_control_server
from sources import HTTPControlServer


def test_build_control_server_no_token():
    """build_control_server with no token returns an HTTPControlServer with auth_fn=None."""
    server = build_control_server({}, {})
    assert isinstance(server, HTTPControlServer)
    assert server.auth_fn is None


def test_build_control_server_with_token():
    """build_control_server with token wires up an HMAC auth_fn."""
    server = build_control_server({}, {}, token="secret")
    assert server.auth_fn is not None
    assert server.auth_fn("secret") is True
    assert server.auth_fn("wrong") is False


def test_build_control_server_registry_has_local_data():
    """The returned server's registry exposes the 'local_data' kind."""
    server = build_control_server({}, {})
    assert "local_data" in server.registry.kinds()


def test_build_control_server_with_jobs_creates_m2m():
    """Providing a jobs object causes an M2MServer to be attached."""
    mock_jobs = MagicMock()
    # make_dispatch_fn calls jobs.submit/status/cancel; mock is fine here
    server = build_control_server({}, {}, jobs=mock_jobs)
    assert server.m2m is not None


def test_build_control_server_no_jobs_no_m2m():
    """When jobs is None no M2MServer is attached."""
    server = build_control_server({}, {})
    assert server.m2m is None
