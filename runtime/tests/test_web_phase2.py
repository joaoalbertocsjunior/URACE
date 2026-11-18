"""Phase 2.5 — Web Phase 2 tests: cycle, goals, inbox, audit, page routes."""
from __future__ import annotations

import importlib.util
import json
import queue
import unittest
from pathlib import Path
from unittest.mock import patch

_MISSING = [
    n for n in ("fastapi", "uvicorn", "jinja2", "httpx")
    if importlib.util.find_spec(n) is None
]
_SKIP = bool(_MISSING)
_SKIP_REASON = f"web deps not installed: {', '.join(_MISSING)}" if _MISSING else ""

AUTH = {"Authorization": "Bearer test-token"}


def _client(token: str = "test-token"):
    from fastapi.testclient import TestClient
    from urace.web.app import create_app
    return TestClient(create_app({}, token), raise_server_exceptions=True)


# ── Phase 1 regression ────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPhase1Regression(unittest.TestCase):
    """Core Phase 1 endpoints must still work after Phase 2 additions."""

    def test_shell_page_still_loads(self):
        self.assertEqual(_client().get("/shell").status_code, 200)

    def test_daemon_status_still_requires_auth(self):
        self.assertEqual(_client().get("/api/daemon/status").status_code, 401)

    def test_config_fields_still_returns_list(self):
        r = _client().get("/api/config/fields", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_vitals_still_works(self):
        with patch("urace._common.load_state_for_read", return_value={}), \
             patch("urace._common.load_config", return_value={}):
            r = _client().get("/api/vitals/", headers=AUTH)
        self.assertEqual(r.status_code, 200)


# ── Cycle ─────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestCycleState(unittest.TestCase):

    _STATE = {
        "lifecycle_state": "ACTIVE",
        "objectives": [{"id": "o1", "title": "T", "status": "active"}],
        "evidence": [{"id": "e1", "kind": "test-pass", "at": "2026-11-18T10:00:00"}],
        "decision_records": [{"id": "d1", "outcome": "ACCEPT", "at": "2026-11-18T10:01:00"}],
        "operations": [{"id": "op1", "status": "ACCEPTED"}],
        "checkpoints": [{"id": "cp1", "at": "2026-11-18T10:02:00", "kind": "accepted-product-change"}],
    }

    def _get(self, htmx: bool = False, state: dict | None = None):
        c = _client()
        headers = dict(AUTH)
        if htmx:
            headers["HX-Request"] = "true"
        effective = state if state is not None else self._STATE
        with patch("urace._common.load_state_for_read", return_value=effective), \
             patch("urace._common.load_config", return_value={}):
            return c.get("/api/cycle/state", headers=headers)

    def test_json_response_has_counts(self):
        r = self._get()
        body = r.json()
        for key in ("objectives_count", "evidence_count", "decisions_count",
                    "operations_count", "checkpoints_count", "lifecycle_state"):
            self.assertIn(key, body)

    def test_lifecycle_state_propagates(self):
        self.assertEqual(self._get().json()["lifecycle_state"], "ACTIVE")

    def test_htmx_returns_html(self):
        r = self._get(htmx=True)
        self.assertIn("text/html", r.headers.get("content-type", ""))

    def test_htmx_html_contains_pipeline_data(self):
        r = self._get(htmx=True)
        self.assertIn("ACTIVE", r.text)

    def test_empty_state_returns_zeros(self):
        r = self._get(state={})
        body = r.json()
        self.assertEqual(body["objectives_count"], 0)
        self.assertEqual(body["lifecycle_state"], "UNKNOWN")

    def test_active_objectives_prioritised(self):
        state = {
            "objectives": [
                {"id": "o1", "status": "active"},
                {"id": "o2", "status": "DONE"},
                {"id": "o3", "status": "active"},
            ]
        }
        r = self._get(state=state)
        # active objectives prioritised — count should reflect active ones
        self.assertGreaterEqual(r.json()["objectives_count"], 2)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestCyclePage(unittest.TestCase):

    def test_cycle_page_loads(self):
        self.assertEqual(_client().get("/cycle").status_code, 200)

    def test_cycle_page_has_polling_div(self):
        html = _client().get("/cycle").text
        self.assertIn("hx-get", html)
        self.assertIn("every 3s", html)


# ── Goals ─────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestGoalsList(unittest.TestCase):

    def test_returns_goals_list(self):
        state = {"objectives": [{"id": "g1", "title": "Goal 1", "status": "active"}]}
        with patch("urace._common.load_state_for_read", return_value=state), \
             patch("urace._common.load_config", return_value={}):
            r = _client().get("/api/goals/", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("goals", r.json())
        self.assertEqual(len(r.json()["goals"]), 1)

    def test_empty_state_returns_empty_list(self):
        with patch("urace._common.load_state_for_read", return_value={}), \
             patch("urace._common.load_config", return_value={}):
            r = _client().get("/api/goals/", headers=AUTH)
        self.assertEqual(r.json()["goals"], [])

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/goals/").status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestGoalsAdd(unittest.TestCase):

    def _add(self, title="Test goal", description="desc", priority=50):
        c = _client()
        with patch("urace.web.routes.goals._rpc_call",
                   return_value={"output": '{"status": "ok"}'}):
            return c.post("/api/goals/add",
                          json={"title": title, "description": description, "priority": priority},
                          headers=AUTH)

    def test_add_dispatches_rpc(self):
        captured = {}

        def _fake_rpc(method, **kwargs):
            captured.update(kwargs)
            return {"output": "{}"}

        c = _client()
        with patch("urace.web.routes.goals._rpc_call", side_effect=_fake_rpc):
            c.post("/api/goals/add",
                   json={"title": "My goal", "description": "desc", "priority": 70},
                   headers=AUTH)
        argv = captured.get("argv", [])
        self.assertIn("add-goal", argv)
        self.assertIn("My goal", argv)

    def test_add_fallback_when_rpc_offline(self):
        q: queue.Queue = queue.Queue()
        q.put('{"status": "ok"}')
        q.put(None)
        c = _client()
        with patch("urace.web.routes.goals._rpc_call",
                   side_effect=ConnectionRefusedError()), \
             patch("urace.web.routes.goals._dispatch",
                   return_value={"output": '{"status": "ok"}'}):
            r = c.post("/api/goals/add",
                       json={"title": "Goal", "description": "", "priority": 50},
                       headers=AUTH)
        self.assertEqual(r.status_code, 200)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestGoalActions(unittest.TestCase):

    def _action(self, path: str, rpc_return: dict | None = None):
        c = _client()
        with patch("urace.web.routes.goals._rpc_call",
                   return_value=rpc_return or {"output": "{}"}):
            return c.post(f"/api/goals/{path}", headers=AUTH)

    def test_pin(self):
        captured = {}

        def _fake_rpc(method, **kwargs):
            captured["argv"] = kwargs.get("argv")
            return {"output": "{}"}

        c = _client()
        with patch("urace.web.routes.goals._rpc_call", side_effect=_fake_rpc):
            r = c.post("/api/goals/goal-123/pin", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("goal-123", captured["argv"])
        self.assertIn("pin", captured["argv"])

    def test_unpin(self):
        r = self._action("goal-123/unpin")
        self.assertEqual(r.status_code, 200)

    def test_defer(self):
        captured = {}

        def _fake_rpc(method, **kwargs):
            captured["argv"] = kwargs.get("argv")
            return {"output": "{}"}

        c = _client()
        with patch("urace.web.routes.goals._rpc_call", side_effect=_fake_rpc):
            r = c.post("/api/goals/goal-456/defer", headers=AUTH)
        self.assertIn("defer", captured["argv"])
        self.assertIn("goal-456", captured["argv"])

    def test_cancel(self):
        r = self._action("goal-789/cancel")
        self.assertEqual(r.status_code, 200)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestGoalsPage(unittest.TestCase):

    def test_goals_page_loads(self):
        self.assertEqual(_client().get("/goals").status_code, 200)

    def test_goals_page_has_add_form(self):
        html = _client().get("/goals").text
        self.assertIn("title", html.lower())


# ── Inbox ─────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestInboxList(unittest.TestCase):

    def test_returns_items_list(self):
        c = _client()
        with patch("urace.web.routes.inbox._rpc_call",
                   return_value={"output": json.dumps([{"id": "i1", "kind": "change", "status": "PENDING"}])}):
            r = c.get("/api/inbox/", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("items", r.json())

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/inbox/").status_code, 401)

    def test_rpc_error_returns_empty(self):
        c = _client()
        with patch("urace.web.routes.inbox._rpc_call",
                   side_effect=ConnectionRefusedError()), \
             patch("urace._common.load_state_for_read", return_value={}), \
             patch("urace._common.load_config", return_value={}):
            r = c.get("/api/inbox/", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("items", r.json())


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestInboxCount(unittest.TestCase):

    def test_count_endpoint_returns_int(self):
        c = _client()
        with patch("urace.web.routes.inbox._rpc_call",
                   return_value={"output": json.dumps([
                       {"id": "i1", "status": "PENDING"},
                       {"id": "i2", "status": "PENDING"},
                   ])}):
            r = c.get("/api/inbox/count", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("count", r.json())
        self.assertIsInstance(r.json()["count"], int)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestInboxActions(unittest.TestCase):

    def test_apply_dispatches_correct_argv(self):
        captured = {}

        def _fake_rpc(method, **kwargs):
            captured["argv"] = kwargs.get("argv", [])
            return {"output": "{}"}

        c = _client()
        with patch("urace.web.routes.inbox._rpc_call", side_effect=_fake_rpc):
            r = c.post("/api/inbox/item-42/apply", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("inbox", captured["argv"])
        self.assertIn("apply", captured["argv"])
        self.assertIn("item-42", captured["argv"])

    def test_reject_dispatches_correct_argv(self):
        captured = {}

        def _fake_rpc(method, **kwargs):
            captured["argv"] = kwargs.get("argv", [])
            return {"output": "{}"}

        c = _client()
        with patch("urace.web.routes.inbox._rpc_call", side_effect=_fake_rpc):
            r = c.post("/api/inbox/item-42/reject", headers=AUTH)
        self.assertIn("reject", captured["argv"])
        self.assertIn("item-42", captured["argv"])


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestInboxPage(unittest.TestCase):

    def test_inbox_page_loads(self):
        self.assertEqual(_client().get("/inbox").status_code, 200)

    def test_inbox_page_has_apply_reference(self):
        html = _client().get("/inbox").text
        self.assertIn("apply", html.lower())


# ── Audit ─────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestAuditDecisions(unittest.TestCase):

    _DECISIONS = [
        {"id": "d1", "outcome": "ACCEPT", "at": "2026-11-18T09:00:00", "reasoning": "good"},
        {"id": "d2", "outcome": "REJECT", "at": "2026-11-18T10:00:00", "reasoning": "bad"},
        {"id": "d3", "outcome": "ACCEPT", "at": "2026-11-18T11:00:00", "reasoning": "great"},
    ]

    def _get_decisions(self, state: dict | None = None, params: dict | None = None):
        c = _client()
        effective = state if state is not None else {"decision_records": self._DECISIONS}
        with patch("urace._common.load_state_for_read", return_value=effective), \
             patch("urace._common.load_config", return_value={}):
            return c.get("/api/audit/decisions", headers=AUTH, params=params or {})

    def test_returns_decisions_list(self):
        r = self._get_decisions()
        self.assertEqual(r.status_code, 200)
        self.assertIn("decisions", r.json())

    def test_newest_first(self):
        r = self._get_decisions()
        decisions = r.json()["decisions"]
        self.assertEqual(decisions[0]["id"], "d3")

    def test_filter_by_outcome(self):
        r = self._get_decisions(params={"outcome": "ACCEPT"})
        outcomes = {d["outcome"] for d in r.json()["decisions"]}
        self.assertEqual(outcomes, {"ACCEPT"})

    def test_filter_by_outcome_reject(self):
        r = self._get_decisions(params={"outcome": "REJECT"})
        self.assertEqual(len(r.json()["decisions"]), 1)
        self.assertEqual(r.json()["decisions"][0]["id"], "d2")

    def test_limit_param(self):
        r = self._get_decisions(params={"limit": 1})
        self.assertLessEqual(len(r.json()["decisions"]), 1)

    def test_since_filter(self):
        r = self._get_decisions(params={"since": "2026-11-18T10:30:00"})
        decisions = r.json()["decisions"]
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["id"], "d3")

    def test_empty_state_returns_empty(self):
        r = self._get_decisions(state={})
        self.assertEqual(r.json()["decisions"], [])

    def test_requires_auth(self):
        c = _client()
        self.assertEqual(c.get("/api/audit/decisions").status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestAuditEvidence(unittest.TestCase):

    _EVIDENCE = [
        {"id": "e1", "kind": "test-pass", "at": "2026-11-18T09:00:00"},
        {"id": "e2", "kind": "metric-observation", "at": "2026-11-18T10:00:00"},
        {"id": "e3", "kind": "test-pass", "at": "2026-11-18T11:00:00"},
    ]

    def _get(self, params: dict | None = None):
        c = _client()
        with patch("urace._common.load_state_for_read",
                   return_value={"evidence": self._EVIDENCE}), \
             patch("urace._common.load_config", return_value={}):
            return c.get("/api/audit/evidence", headers=AUTH, params=params or {})

    def test_returns_evidence_list(self):
        r = self._get()
        self.assertIn("evidence", r.json())

    def test_newest_first(self):
        r = self._get()
        self.assertEqual(r.json()["evidence"][0]["id"], "e3")

    def test_filter_by_kind(self):
        r = self._get(params={"kind": "test-pass"})
        kinds = {e["kind"] for e in r.json()["evidence"]}
        self.assertEqual(kinds, {"test-pass"})

    def test_since_filter(self):
        r = self._get(params={"since": "2026-11-18T09:30:00"})
        self.assertEqual(len(r.json()["evidence"]), 2)

    def test_limit_param(self):
        r = self._get(params={"limit": 2})
        self.assertLessEqual(len(r.json()["evidence"]), 2)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestAuditPage(unittest.TestCase):

    def test_audit_page_loads(self):
        self.assertEqual(_client().get("/audit").status_code, 200)

    def test_audit_page_has_decisions_reference(self):
        self.assertIn("decision", _client().get("/audit").text.lower())

    def test_audit_page_has_evidence_reference(self):
        self.assertIn("evidence", _client().get("/audit").text.lower())


# ── Navigation ────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestNavigation(unittest.TestCase):
    """All Phase 2 pages linked from base nav."""

    def test_base_nav_has_cycle_link(self):
        self.assertIn("/cycle", _client().get("/shell").text)

    def test_base_nav_has_goals_link(self):
        self.assertIn("/goals", _client().get("/shell").text)

    def test_base_nav_has_inbox_link(self):
        self.assertIn("/inbox", _client().get("/shell").text)

    def test_base_nav_has_audit_link(self):
        self.assertIn("/audit", _client().get("/shell").text)


if __name__ == "__main__":
    unittest.main()
