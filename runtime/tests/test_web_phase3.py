"""Phase 3.5 — Web Phase 3 tests: compliance, rules, github, exchange + regressions."""
from __future__ import annotations

import importlib.util
import json
import unittest
from unittest.mock import patch

_MISSING = [n for n in ("fastapi", "uvicorn", "jinja2", "httpx") if importlib.util.find_spec(n) is None]
_SKIP = bool(_MISSING)
_SKIP_REASON = f"web deps not installed: {', '.join(_MISSING)}" if _MISSING else ""

AUTH = {"Authorization": "Bearer test-token"}

_COMPLIANCE_PAYLOAD = {
    "domains": [
        {"domain": "authority", "status": "COMPLIANT", "consecutive_clean": 5, "last_checked_at": "2026-11-18T10:00:00", "violation_refs": []},
        {"domain": "intent",    "status": "COMPLIANT", "consecutive_clean": 3, "last_checked_at": "2026-11-18T10:00:00", "violation_refs": []},
        {"domain": "schema",    "status": "NON_COMPLIANT", "consecutive_clean": 0, "last_checked_at": "2026-11-18T10:00:00", "violation_refs": ["cpl-1"]},
        {"domain": "constraint","status": "UNKNOWN",   "consecutive_clean": 0, "last_checked_at": None, "violation_refs": []},
        {"domain": "governance","status": "COMPLIANT", "consecutive_clean": 2, "last_checked_at": "2026-11-18T10:00:00", "violation_refs": []},
    ],
    "total_records": 10,
    "compliant": 8,
    "non_compliant": 2,
    "recent_records": [
        {"id": "cpl-1", "domain": "schema", "status": "NON_COMPLIANT", "evaluated_at": "2026-11-18T09:00:00", "violation_detail": "schema mismatch"},
    ],
    "strict_pass": False,
}

_RULES_LIST = [
    {"id": "r-1", "kind": "PURPOSE",     "statement": "Improve product quality", "scope": ["*"], "confidence": 0.95, "created_at": "2026-11-01T00:00:00"},
    {"id": "r-2", "kind": "PROHIBITION", "statement": "No external publishing",  "scope": ["*"], "confidence": 1.0,  "created_at": "2026-11-01T00:00:00"},
]

_RULES_GRAPH = {
    "rules": _RULES_LIST,
    "relationships": [{"from_id": "r-2", "to_id": "r-1", "type": "derived_from"}],
}

_RULES_CONFLICTS = [
    {"rule_a": "r-1", "rule_b": "r-2", "kind": "PERMISSION_PROHIBITION_OVERLAP", "overlap_terms": ["publish"]},
]

_GITHUB_STATUS_CONNECTED = {
    "github_token_set": True, "repo": "owner/repo", "connected": True,
    "default_branch": "main", "open_issues": 3, "url": "https://github.com/owner/repo", "error": None,
}

_GITHUB_STATUS_DISCONNECTED = {
    "github_token_set": False, "repo": None, "connected": False,
    "default_branch": None, "open_issues": 0, "url": None, "error": "URACE_GITHUB_TOKEN not set",
}


def _client(token: str = "test-token"):
    from fastapi.testclient import TestClient
    from urace.web.app import create_app
    return TestClient(create_app({}, token), raise_server_exceptions=True)


def _mock_dispatch(payload):
    """Return a _dispatch mock that yields the given payload as JSON output."""
    def _fake(*args, **kwargs):
        return {"output": json.dumps(payload)}
    return _fake


# ── Phase 1 + 2 regression ────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPhase12Regression(unittest.TestCase):

    def test_shell_still_loads(self):
        self.assertEqual(_client().get("/shell").status_code, 200)

    def test_daemon_status_still_requires_auth(self):
        self.assertEqual(_client().get("/api/daemon/status").status_code, 401)

    def test_cycle_page_still_loads(self):
        self.assertEqual(_client().get("/cycle").status_code, 200)

    def test_audit_page_still_loads(self):
        self.assertEqual(_client().get("/audit").status_code, 200)


# ── Compliance ────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestComplianceEndpoint(unittest.TestCase):

    def _get(self, path="/api/compliance/", payload=None):
        c = _client()
        with patch("urace.web.routes.compliance._dispatch",
                   side_effect=_mock_dispatch(payload or _COMPLIANCE_PAYLOAD)):
            return c.get(path, headers=AUTH)

    def test_returns_domains_list(self):
        body = self._get().json()
        self.assertIn("domains", body)
        self.assertEqual(len(body["domains"]), 5)

    def test_compliant_count(self):
        body = self._get().json()
        self.assertEqual(body["compliant"], 8)

    def test_non_compliant_count(self):
        body = self._get().json()
        self.assertEqual(body["non_compliant"], 2)

    def test_recent_records_present(self):
        body = self._get().json()
        self.assertIn("recent_records", body)
        self.assertEqual(body["recent_records"][0]["id"], "cpl-1")

    def test_domain_filter(self):
        c = _client()
        with patch("urace.web.routes.compliance._dispatch",
                   side_effect=_mock_dispatch(_COMPLIANCE_PAYLOAD)):
            r = c.get("/api/compliance/domain/authority", headers=AUTH)
        self.assertEqual(r.status_code, 200)

    def test_history_endpoint(self):
        c = _client()
        with patch("urace.web.routes.compliance._dispatch",
                   side_effect=_mock_dispatch(_COMPLIANCE_PAYLOAD)):
            r = c.get("/api/compliance/history?limit=10", headers=AUTH)
        self.assertEqual(r.status_code, 200)

    def test_parse_error_returns_safe_default(self):
        c = _client()
        with patch("urace.web.routes.compliance._dispatch",
                   return_value={"output": "not valid json {{"}):
            r = c.get("/api/compliance/", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("domains", body)
        self.assertEqual(body["domains"], [])

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/compliance/").status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestCompliancePage(unittest.TestCase):

    def test_page_loads(self):
        self.assertEqual(_client().get("/compliance").status_code, 200)

    def test_page_has_domain_references(self):
        html = _client().get("/compliance").text.lower()
        self.assertIn("authority", html)
        self.assertIn("intent", html)


# ── Rules ─────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestRulesEndpoints(unittest.TestCase):

    def _dispatch_mock(self, payload):
        return patch("urace.web.routes.rules._dispatch",
                     side_effect=_mock_dispatch(payload))

    def test_list_returns_rules(self):
        c = _client()
        with self._dispatch_mock(_RULES_LIST):
            r = c.get("/api/rules/list", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 2)

    def test_list_rule_has_kind(self):
        c = _client()
        with self._dispatch_mock(_RULES_LIST):
            r = c.get("/api/rules/list", headers=AUTH)
        kinds = {rule["kind"] for rule in r.json()}
        self.assertIn("PURPOSE", kinds)
        self.assertIn("PROHIBITION", kinds)

    def test_graph_returns_rules_and_relationships(self):
        c = _client()
        with self._dispatch_mock(_RULES_GRAPH):
            r = c.get("/api/rules/graph", headers=AUTH)
        body = r.json()
        self.assertIn("rules", body)
        self.assertIn("relationships", body)
        self.assertEqual(len(body["relationships"]), 1)

    def test_conflicts_returns_list(self):
        c = _client()
        with self._dispatch_mock(_RULES_CONFLICTS):
            r = c.get("/api/rules/conflicts", headers=AUTH)
        body = r.json()
        self.assertIsInstance(body, list)
        self.assertEqual(body[0]["kind"], "PERMISSION_PROHIBITION_OVERLAP")

    def test_list_parse_error_returns_empty(self):
        c = _client()
        with patch("urace.web.routes.rules._dispatch",
                   return_value={"output": "bad json"}):
            r = c.get("/api/rules/list", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_graph_parse_error_returns_safe_default(self):
        c = _client()
        with patch("urace.web.routes.rules._dispatch",
                   return_value={"output": ""}):
            r = c.get("/api/rules/graph", headers=AUTH)
        body = r.json()
        self.assertIn("rules", body)
        self.assertIn("relationships", body)

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/rules/list").status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestRulesPage(unittest.TestCase):

    def test_page_loads(self):
        self.assertEqual(_client().get("/rules").status_code, 200)

    def test_page_has_tab_references(self):
        html = _client().get("/rules").text.lower()
        self.assertIn("conflict", html)


# ── GitHub ────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestGitHubStatus(unittest.TestCase):

    def _get_status(self, payload):
        c = _client()
        with patch("urace.web.routes.github_router._dispatch",
                   side_effect=_mock_dispatch(payload)):
            return c.get("/api/github/status", headers=AUTH)

    def test_connected_status(self):
        body = self._get_status(_GITHUB_STATUS_CONNECTED).json()
        self.assertTrue(body["connected"])
        self.assertEqual(body["repo"], "owner/repo")

    def test_disconnected_status(self):
        body = self._get_status(_GITHUB_STATUS_DISCONNECTED).json()
        self.assertFalse(body["connected"])

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/github/status").status_code, 401)

    def test_parse_error_returns_error_dict(self):
        c = _client()
        with patch("urace.web.routes.github_router._dispatch",
                   return_value={"output": "not json"}):
            r = c.get("/api/github/status", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("status", r.json())


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestGitHubPushGoals(unittest.TestCase):

    def test_dry_run_dispatches_dry_run_flag(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({"status": "ok", "dry_run": True, "objectives_pushed": 2, "issues": []})}

        c = _client()
        with patch("urace.web.routes.github_router._dispatch", side_effect=_fake):
            r = c.post("/api/github/push-goals", json={"dry_run": True}, headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("--dry-run", captured["argv"])

    def test_live_run_omits_dry_run_flag(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({"status": "ok", "dry_run": False, "objectives_pushed": 1, "issues": []})}

        c = _client()
        with patch("urace.web.routes.github_router._dispatch", side_effect=_fake):
            r = c.post("/api/github/push-goals", json={"dry_run": False}, headers=AUTH)
        self.assertNotIn("--dry-run", captured.get("argv", []))


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestGitHubTriggerWorkflow(unittest.TestCase):

    def test_dispatches_correct_argv(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({"status": "triggered", "workflow": "deploy.yml", "ref": "main"})}

        c = _client()
        with patch("urace.web.routes.github_router._dispatch", side_effect=_fake):
            r = c.post("/api/github/trigger-workflow",
                       json={"workflow": "deploy.yml", "ref": "main"}, headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("deploy.yml", captured["argv"])
        self.assertIn("main", captured["argv"])

    def test_requires_workflow_field(self):
        c = _client()
        r = c.post("/api/github/trigger-workflow", json={"ref": "main"}, headers=AUTH)
        self.assertEqual(r.status_code, 422)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestGitHubPage(unittest.TestCase):

    def test_page_loads(self):
        self.assertEqual(_client().get("/github").status_code, 200)

    def test_page_has_push_goals_reference(self):
        self.assertIn("push", _client().get("/github").text.lower())


# ── Exchange ──────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestExchangePeers(unittest.TestCase):

    def test_returns_peer_count(self):
        c = _client()
        with patch("urace.web.routes.exchange._dispatch",
                   side_effect=_mock_dispatch({"peer_count": 3, "anonymized_peer_ids": ["a", "b", "c"]})):
            r = c.get("/api/exchange/peers", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["peer_count"], 3)

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/exchange/peers").status_code, 401)

    def test_parse_error_safe_default(self):
        c = _client()
        with patch("urace.web.routes.exchange._dispatch",
                   return_value={"output": "not json"}):
            r = c.get("/api/exchange/peers", headers=AUTH)
        self.assertEqual(r.status_code, 200)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestExchangeAssets(unittest.TestCase):

    _ASSETS = {
        "query": "auth",
        "open_assets": [
            {"feature_id": "f-1", "description": "OAuth helper", "tags": ["auth"], "match_score": 0.9},
        ],
        "paid_listings": [],
    }

    def test_returns_assets(self):
        c = _client()
        with patch("urace.web.routes.exchange._dispatch",
                   side_effect=_mock_dispatch(self._ASSETS)):
            r = c.get("/api/exchange/assets?query=auth", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("open_assets", r.json())
        self.assertEqual(len(r.json()["open_assets"]), 1)

    def test_query_param_included_in_argv(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps(self._ASSETS)}

        c = _client()
        with patch("urace.web.routes.exchange._dispatch", side_effect=_fake):
            c.get("/api/exchange/assets?query=myquery", headers=AUTH)
        self.assertIn("myquery", captured.get("argv", []))

    def test_empty_query_omits_query_flag(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({"open_assets": [], "paid_listings": []})}

        c = _client()
        with patch("urace.web.routes.exchange._dispatch", side_effect=_fake):
            c.get("/api/exchange/assets", headers=AUTH)
        self.assertNotIn("--query", captured.get("argv", []))

    def test_parse_error_returns_safe_default(self):
        c = _client()
        with patch("urace.web.routes.exchange._dispatch",
                   return_value={"output": "{bad"}):
            r = c.get("/api/exchange/assets", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("open_assets", body)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestExchangeSearch(unittest.TestCase):

    def test_search_dispatches_query(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({"entries": [], "count": 0})}

        c = _client()
        with patch("urace.web.routes.exchange._dispatch", side_effect=_fake):
            c.get("/api/exchange/search?q=hello&kind=objective", headers=AUTH)
        self.assertIn("hello", captured.get("argv", []))

    def test_search_requires_auth(self):
        self.assertEqual(_client().get("/api/exchange/search").status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestExchangePage(unittest.TestCase):

    def test_page_loads(self):
        self.assertEqual(_client().get("/exchange").status_code, 200)

    def test_page_has_search_reference(self):
        self.assertIn("search", _client().get("/exchange").text.lower())


# ── Navigation ────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPhase3Navigation(unittest.TestCase):

    def test_nav_has_compliance(self):
        self.assertIn("/compliance", _client().get("/shell").text)

    def test_nav_has_rules(self):
        self.assertIn("/rules", _client().get("/shell").text)

    def test_nav_has_github(self):
        self.assertIn("/github", _client().get("/shell").text)

    def test_nav_has_exchange(self):
        self.assertIn("/exchange", _client().get("/shell").text)


if __name__ == "__main__":
    unittest.main()
