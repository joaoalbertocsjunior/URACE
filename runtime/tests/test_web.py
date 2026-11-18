"""Phase 1.5 — Web interface tests: auth, daemon controls, shell SSE, config, vitals."""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import queue
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

_MISSING = [
    name
    for name in ("fastapi", "uvicorn", "jinja2", "httpx")
    if importlib.util.find_spec(name) is None
]
_SKIP = bool(_MISSING)
_SKIP_REASON = f"web deps not installed: {', '.join(_MISSING)}" if _MISSING else ""


def _make_app(token: str = "test-token"):
    from urace.web.app import create_app
    return create_app({}, token)


def _client(token: str = "test-token"):
    from fastapi.testclient import TestClient
    return TestClient(_make_app(token), raise_server_exceptions=True)


AUTH = {"Authorization": "Bearer test-token"}


# ── Capabilities ──────────────────────────────────────────────────────────────

class TestWebCapabilities(unittest.TestCase):
    """capabilities() must work regardless of whether web deps are installed."""

    def test_returns_dict_with_status_key(self):
        from urace.web.server import capabilities
        result = capabilities()
        self.assertIn("status", result)
        self.assertIn(result["status"], ("READY", "ADAPTER_REQUIRED"))

    def test_ready_when_deps_present(self):
        from urace.web.server import capabilities
        if not _SKIP:
            self.assertEqual(capabilities()["status"], "READY")

    def test_adapter_required_when_fastapi_missing(self):
        from urace.web import server as web_server
        original = importlib.util.find_spec

        def _mock(name, *a, **kw):
            return None if name == "fastapi" else original(name, *a, **kw)

        with patch("urace.web.server.importlib.util.find_spec", side_effect=_mock):
            result = web_server.capabilities()
        self.assertEqual(result["status"], "ADAPTER_REQUIRED")
        self.assertIn("fastapi", result["missing"])


# ── Auth ─────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestAuth(unittest.TestCase):

    def _status(self, headers=None):
        c = _client()
        with patch("urace._common.load_config", return_value={}), \
             patch("urace._common.load_state_for_read", return_value={}), \
             patch("urace.web.routes.daemon.os.kill"):
            return c.get("/api/daemon/status", headers=headers or {})

    def test_no_token_returns_401(self):
        self.assertEqual(self._status().status_code, 401)

    def test_wrong_token_returns_401(self):
        self.assertEqual(
            self._status({"Authorization": "Bearer wrong"}).status_code, 401
        )

    def test_correct_token_returns_200(self):
        c = _client("tok")
        with patch("urace._common.load_config", return_value={}), \
             patch("urace._common.load_state_for_read", return_value={}):
            r = c.get("/api/daemon/status", headers={"Authorization": "Bearer tok"})
        self.assertNotEqual(r.status_code, 401)

    def test_token_is_case_sensitive(self):
        c = _client("Tok")
        with patch("urace._common.load_config", return_value={}), \
             patch("urace._common.load_state_for_read", return_value={}):
            r = c.get("/api/daemon/status", headers={"Authorization": "Bearer tok"})
        self.assertEqual(r.status_code, 401)


# ── Daemon status ─────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestDaemonStatus(unittest.TestCase):

    def _get(self, pid_exists: bool = False, pid: int = 0,
             process_alive: bool = False, lifecycle: str = "DORMANT",
             htmx: bool = False):
        c = _client()
        headers = dict(AUTH)
        if htmx:
            headers["HX-Request"] = "true"

        with tempfile.TemporaryDirectory() as d:
            state_dir = Path(d) / "state"
            state_dir.mkdir()
            pid_path = state_dir / "daemon.pid"
            if pid_exists:
                pid_path.write_text(str(pid))

            def _fake_state_path(config):
                return state_dir / "state.json"

            def _fake_kill(p, sig):
                if not process_alive:
                    raise ProcessLookupError
                # sig 0 = existence check; alive so don't raise

            with patch("urace._common.state_path", side_effect=_fake_state_path), \
                 patch("urace._common.load_config", return_value={}), \
                 patch("urace._common.load_state_for_read",
                       return_value={"lifecycle_state": lifecycle}), \
                 patch("urace.web.routes.daemon.os.kill", side_effect=_fake_kill):
                return c.get("/api/daemon/status", headers=headers)

    def test_stopped_reports_stopped(self):
        r = self._get(pid_exists=False)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "stopped")
        self.assertIsNone(body["pid"])
        self.assertFalse(body["cycle_active"])

    def test_running_reports_running(self):
        r = self._get(pid_exists=True, pid=1234, process_alive=True)
        body = r.json()
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["pid"], 1234)

    def test_cycle_active_when_lifecycle_active(self):
        r = self._get(pid_exists=True, pid=99, process_alive=True, lifecycle="ACTIVE")
        self.assertTrue(r.json()["cycle_active"])

    def test_cycle_inactive_when_stopped(self):
        r = self._get(pid_exists=False)
        self.assertFalse(r.json()["cycle_active"])

    def test_htmx_returns_html(self):
        r = self._get(htmx=True)
        self.assertIn("text/html", r.headers.get("content-type", ""))


# ── Daemon stop ───────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestDaemonStop(unittest.TestCase):

    def _stop(self, pid_exists: bool = True, pid: int = 5555,
              kill_raises: Exception | None = None):
        c = _client()
        with tempfile.TemporaryDirectory() as d:
            state_dir = Path(d) / "state"
            state_dir.mkdir()
            pid_path = state_dir / "daemon.pid"
            if pid_exists:
                pid_path.write_text(str(pid))

            def _fake_state_path(config):
                return state_dir / "state.json"

            kill_calls = []

            def _fake_kill(p, sig):
                kill_calls.append((p, sig))
                if sig == 0:
                    return  # process exists check
                if kill_raises:
                    raise kill_raises

            with patch("urace._common.state_path", side_effect=_fake_state_path), \
                 patch("urace._common.load_config", return_value={}), \
                 patch("urace._common.load_state_for_read", return_value={}), \
                 patch("urace.web.routes.daemon.os.kill", side_effect=_fake_kill):
                r = c.post("/api/daemon/stop", headers=AUTH)

        return r, kill_calls

    def test_sends_sigterm_to_running_daemon(self):
        r, kills = self._stop(pid_exists=True, pid=5555)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "stopped")
        sigterm_calls = [(p, s) for p, s in kills if s == signal.SIGTERM]
        self.assertEqual(len(sigterm_calls), 1)
        self.assertEqual(sigterm_calls[0][0], 5555)

    def test_not_running_returns_not_running(self):
        r, _ = self._stop(pid_exists=False)
        self.assertEqual(r.json()["status"], "not_running")

    def test_oserror_returns_error(self):
        r, _ = self._stop(kill_raises=OSError("denied"))
        self.assertEqual(r.json()["status"], "error")


# ── Daemon start ──────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestDaemonStart(unittest.TestCase):

    def test_spawns_urace_start_subprocess(self):
        c = _client()
        with patch("urace.web.routes.daemon.subprocess.Popen") as mock_popen:
            r = c.post("/api/daemon/start", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "starting")
        mock_popen.assert_called_once()
        argv = mock_popen.call_args[0][0]
        self.assertIn("urace", argv)
        self.assertIn("start", argv)

    def test_start_uses_new_session(self):
        c = _client()
        with patch("urace.web.routes.daemon.subprocess.Popen") as mock_popen:
            c.post("/api/daemon/start", headers=AUTH)
        kwargs = mock_popen.call_args[1]
        self.assertTrue(kwargs.get("start_new_session"))


# ── Shell / SSE ───────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestShell(unittest.TestCase):

    def _run(self, text: str, rpc_return=None, rpc_raises=None):
        c = _client()

        def _fake_rpc(method, **kwargs):
            if rpc_raises:
                raise rpc_raises
            return rpc_return or {"output": "ok"}

        with patch("urace.web.routes.shell._rpc_call", side_effect=_fake_rpc):
            return c.post("/api/shell/run", json={"input": text}, headers=AUTH)

    def test_returns_sse_content_type(self):
        r = self._run("status", rpc_return={"output": "running"})
        self.assertIn("text/event-stream", r.headers.get("content-type", ""))

    def test_streams_output_lines(self):
        r = self._run("status", rpc_return={"output": "line1\nline2"})
        self.assertIn("data: line1", r.text)
        self.assertIn("data: line2", r.text)

    def test_done_sentinel_always_present(self):
        r = self._run("status", rpc_return={"output": ""})
        self.assertIn("data: [DONE]", r.text)

    def test_nl_input_sent_as_single_argv_element(self):
        """Multi-word NL input must arrive at the CLI as one element (freeform path)."""
        captured = {}

        def _fake_rpc(method, **kwargs):
            captured["argv"] = kwargs.get("argv", [])
            return {"output": "routed"}

        c = _client()
        with patch("urace.web.routes.shell._rpc_call", side_effect=_fake_rpc):
            c.post("/api/shell/run",
                   json={"input": "what is my aps score"}, headers=AUTH)
        self.assertEqual(len(captured["argv"]), 1)
        self.assertEqual(captured["argv"][0], "what is my aps score")

    def test_single_token_command_sent_as_single_element(self):
        captured = {}

        def _fake_rpc(method, **kwargs):
            captured["argv"] = kwargs.get("argv", [])
            return {"output": "ok"}

        c = _client()
        with patch("urace.web.routes.shell._rpc_call", side_effect=_fake_rpc):
            c.post("/api/shell/run", json={"input": "status"}, headers=AUTH)
        self.assertEqual(captured["argv"], ["status"])

    def test_fallback_to_cli_when_daemon_offline(self):
        q: queue.Queue = queue.Queue()
        q.put("fallback output")
        q.put(None)

        c = _client()
        with patch("urace.web.routes.shell._rpc_call",
                   side_effect=ConnectionRefusedError()), \
             patch("urace.web.routes.shell._run_cli_streaming", return_value=q) as mock_stream:
            r = c.post("/api/shell/run", json={"input": "status"}, headers=AUTH)
        mock_stream.assert_called_once()
        self.assertIn("data: [DONE]", r.text)

    def test_error_field_streamed_when_no_output(self):
        r = self._run("bad", rpc_return={"error": "unknown command", "output": ""})
        self.assertIn("data: [DONE]", r.text)


# ── Config ────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestConfig(unittest.TestCase):

    def test_fields_returns_list_with_path_and_type(self):
        c = _client()
        r = c.get("/api/config/fields", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsInstance(body, list)
        self.assertGreater(len(body), 0)
        for f in body:
            self.assertIn("path", f)
            self.assertIn("type", f)

    def _set(self, key: str, value: str, existing: dict | None = None):
        c = _client()
        saved = {}

        def _fake_save(cfg):
            saved.update(cfg)

        with patch("urace._common.load_config", return_value=dict(existing or {})), \
             patch("urace._common.save_config", side_effect=_fake_save):
            r = c.post("/api/config/set",
                       json={"key": key, "value": value}, headers=AUTH)
        return r, saved

    def test_set_bool_true(self):
        r, saved = self._set("executor.enabled", "true")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(saved.get("executor", {}).get("enabled"))

    def test_set_bool_false(self):
        r, saved = self._set("executor.enabled", "false")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(saved.get("executor", {}).get("enabled"))

    def test_set_int(self):
        r, saved = self._set("network.port", "9090")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(saved.get("network", {}).get("port"), 9090)

    def test_set_enum_valid(self):
        r, _ = self._set("network.mode", "intranet")
        self.assertEqual(r.status_code, 200)

    def test_set_enum_invalid_returns_422(self):
        c = _client()
        with patch("urace._common.load_config", return_value={}), \
             patch("urace._common.save_config"):
            r = c.post("/api/config/set",
                       json={"key": "network.mode", "value": "badvalue"}, headers=AUTH)
        self.assertEqual(r.status_code, 422)

    def test_set_list_json_array(self):
        r, saved = self._set("network.bootstrap_peers", '["a", "b"]')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(saved.get("network", {}).get("bootstrap_peers"), ["a", "b"])

    def test_set_list_comma_separated(self):
        r, saved = self._set("network.bootstrap_peers", "a, b, c")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(saved.get("network", {}).get("bootstrap_peers"), ["a", "b", "c"])

    def test_set_invalid_int_returns_422(self):
        c = _client()
        with patch("urace._common.load_config", return_value={}), \
             patch("urace._common.save_config"):
            r = c.post("/api/config/set",
                       json={"key": "network.port", "value": "not-a-number"}, headers=AUTH)
        self.assertEqual(r.status_code, 422)

    def test_set_saves_to_config(self):
        r, saved = self._set("network.enabled", "true")
        self.assertEqual(r.json()["status"], "ok")
        self.assertTrue(saved.get("network", {}).get("enabled"))


# ── Vitals ────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestVitals(unittest.TestCase):

    def _get(self, state: dict | None):
        c = _client()
        with patch("urace._common.load_state_for_read", return_value=state), \
             patch("urace._common.load_config", return_value={}):
            return c.get("/api/vitals/", headers=AUTH)

    def test_required_fields_present(self):
        r = self._get({"lifecycle_state": "ACTIVE"})
        self.assertEqual(r.status_code, 200)
        for key in ("lifecycle_state", "last_cycle_at", "aps_score",
                    "cycle_count", "objectives_count", "evidence_count"):
            self.assertIn(key, r.json())

    def test_lifecycle_state_propagates(self):
        self.assertEqual(self._get({"lifecycle_state": "DORMANT"}).json()["lifecycle_state"], "DORMANT")

    def test_unknown_when_no_state(self):
        self.assertEqual(self._get(None).json()["lifecycle_state"], "UNKNOWN")

    def test_counts_objectives_and_evidence(self):
        body = self._get({
            "objectives": [{"id": "o1"}, {"id": "o2"}],
            "evidence": [{"id": "e1"}],
        }).json()
        self.assertEqual(body["objectives_count"], 2)
        self.assertEqual(body["evidence_count"], 1)

    def test_aps_score_from_state(self):
        self.assertAlmostEqual(self._get({"aps_score": 0.87}).json()["aps_score"], 0.87)

    def test_last_cycle_at_picks_latest_checkpoint(self):
        state = {
            "checkpoints": [
                {"completed_at": "2026-11-18T10:00:00"},
                {"completed_at": "2026-11-18T12:00:00"},
            ]
        }
        self.assertEqual(
            self._get(state).json()["last_cycle_at"], "2026-11-18T12:00:00"
        )

    def test_cycle_count_matches_checkpoints(self):
        state = {"checkpoints": [{}, {}, {}]}
        self.assertEqual(self._get(state).json()["cycle_count"], 3)


# ── Page routes ───────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPageRoutes(unittest.TestCase):

    def test_root_redirects_to_shell(self):
        c = _client()
        r = c.get("/", follow_redirects=False)
        self.assertIn(r.status_code, (301, 302, 307, 308))
        self.assertIn("/shell", r.headers["location"])

    def test_shell_page_200(self):
        self.assertEqual(_client().get("/shell").status_code, 200)

    def test_config_page_200(self):
        with patch("urace.web.routes.config_router._get_fields_and_values",
                   return_value=([], {})):
            self.assertEqual(_client().get("/config").status_code, 200)

    def test_vitals_page_200(self):
        self.assertEqual(_client().get("/vitals").status_code, 200)

    def test_wallet_page_200(self):
        self.assertEqual(_client().get("/wallet").status_code, 200)

    def test_wallet_page_contains_polygon_placeholder(self):
        self.assertIn("Polygon", _client().get("/wallet").text)

    def test_shell_page_embeds_token(self):
        self.assertIn("my-secret", _client("my-secret").get("/shell").text)

    def test_shell_page_has_input_element(self):
        html = _client().get("/shell").text
        self.assertIn("<input", html)

    def test_config_page_has_save_function(self):
        with patch("urace.web.routes.config_router._get_fields_and_values",
                   return_value=([], {})):
            html = _client().get("/config").text
        self.assertIn("saveField", html)


if __name__ == "__main__":
    unittest.main()
