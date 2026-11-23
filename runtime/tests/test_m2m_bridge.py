"""Unit tests for runtime.urace.m2m_bridge (U3)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sources.m2m.interface import RpcError

from urace.integration_bridge import BridgeError
from urace.m2m_bridge import make_dispatch_fn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_jobs(*, submit_row=None, status_row=None):
    jobs = MagicMock()
    jobs.submit.return_value = submit_row or {"job_id": "job-abc", "status": "PENDING"}
    jobs.status.return_value = status_row or {"job_id": "job-abc", "status": "COMPLETED"}
    return jobs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_submit_dispatches():
    jobs = _mock_jobs()
    dispatch = make_dispatch_fn(jobs)
    result = dispatch("urace.submit", {"command": "help", "params": {}})
    assert "job_id" in result
    assert result["job_id"] == "job-abc"
    jobs.submit.assert_called_once()
    call_kwargs = jobs.submit.call_args
    assert call_kwargs.args[0] == "help" or call_kwargs.kwargs.get("command") == "help"


def test_status_dispatches():
    jobs = _mock_jobs()
    dispatch = make_dispatch_fn(jobs)
    result = dispatch("urace.status", {"job_id": "job-abc"})
    jobs.status.assert_called_once_with("job-abc")
    assert result["job_id"] == "job-abc"


def test_cancel_dispatches():
    jobs = _mock_jobs()
    dispatch = make_dispatch_fn(jobs)
    result = dispatch("urace.cancel", {"job_id": "job-xyz"})
    jobs.cancel.assert_called_once_with("job-xyz")
    assert result == {"job_id": "job-xyz", "cancelled": True}


def test_unknown_method_raises_rpc_error():
    jobs = _mock_jobs()
    dispatch = make_dispatch_fn(jobs)
    with pytest.raises(RpcError) as exc_info:
        dispatch("urace.nonexistent", {})
    assert exc_info.value.code == -32601


def test_bridge_error_maps_to_rpc_error():
    jobs = _mock_jobs()
    jobs.status.side_effect = BridgeError("nope")
    dispatch = make_dispatch_fn(jobs)
    with pytest.raises(RpcError) as exc_info:
        dispatch("urace.status", {"job_id": "bad-id"})
    assert exc_info.value.code == -32602
    assert "nope" in str(exc_info.value)
