"""Phase 4.5 — Web Phase 4 tests: products, fleet, portfolio + regressions."""
from __future__ import annotations

import importlib.util
import json
import unittest
from unittest.mock import patch

_MISSING = [n for n in ("fastapi", "uvicorn", "jinja2", "httpx") if importlib.util.find_spec(n) is None]
_SKIP = bool(_MISSING)
_SKIP_REASON = f"web deps not installed: {', '.join(_MISSING)}" if _MISSING else ""

AUTH = {"Authorization": "Bearer test-token"}

_PRODUCTS_LIST = [
    {"name": "alpha", "active": True,  "generation": 3, "aps_score": 0.82, "created_at": "2026-11-01T00:00:00"},
    {"name": "beta",  "active": False, "generation": 1, "aps_score": 0.61, "created_at": "2026-11-10T00:00:00"},
]

_PRODUCTS_STATUS = {
    "active_product": "alpha",
    "total": 2,
    "products": _PRODUCTS_LIST,
}

_PRODUCTS_IMPROVEMENTS = {
    "products": [
        {
            "name": "alpha",
            "improvements": [
                {"id": "imp-1", "title": "Cache warm-up", "status": "pending", "priority": 80},
                {"id": "imp-2", "title": "Auth refactor",  "status": "done",    "priority": 60},
            ],
        },
    ],
}

_FLEET_STATUS = [
    {"peer_id": "p-1", "address": "127.0.0.1", "port": 7501, "product": "alpha", "version": "0.9.0", "healthy": True},
    {"peer_id": "p-2", "address": "127.0.0.2", "port": 7501, "product": "beta",  "version": "0.9.0", "healthy": False},
]

_FLEET_CAPACITY = {
    "fleet_size": 2,
    "healthy": 1,
    "total_capacity_units": 200,
    "used_capacity_units": 120,
    "members": _FLEET_STATUS,
}

_FLEET_RUN_RESULT = {
    "dry_run": True,
    "cycles_scheduled": 2,
    "members_targeted": ["p-1", "p-2"],
    "errors": [],
}

_FLEET_BROADCAST_RESULT = {
    "command": "status",
    "targets": 2,
    "acknowledged": 2,
    "errors": [],
}

_FLEET_CONFIG_PUSH_RESULT = {
    "key": "aps_threshold",
    "value": "0.75",
    "applied_to": 2,
    "errors": [],
}

_PORTFOLIO_FEEDBACK = {
    "phase": "SELECTION",
    "generation": 3,
    "variants": [
        {"name": "alpha", "aps_score": 0.82, "wins": 5, "losses": 2, "evidence_items": 12},
        {"name": "beta",  "aps_score": 0.61, "wins": 2, "losses": 5, "evidence_items": 7},
    ],
}

_PORTFOLIO_STATUS = {
    "phase": "SELECTION",
    "generation": 3,
    "active_product": "alpha",
    "cycle_count": 42,
    "last_evaluated_at": "2026-11-18T10:00:00",
}


def _client(token: str = "test-token"):
    from fastapi.testclient import TestClient
    from urace.web.app import create_app
    return TestClient(create_app({}, token), raise_server_exceptions=True)


def _mock_dispatch(payload):
    def _fake(*args, **kwargs):
        return {"output": json.dumps(payload)}
    return _fake


# ── Phase 1-3 regression ──────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPhase123Regression(unittest.TestCase):

    def test_shell_still_loads(self):
        self.assertEqual(_client().get("/shell").status_code, 200)

    def test_daemon_status_still_requires_auth(self):
        self.assertEqual(_client().get("/api/daemon/status").status_code, 401)

    def test_compliance_page_still_loads(self):
        self.assertEqual(_client().get("/compliance").status_code, 200)

    def test_exchange_page_still_loads(self):
        self.assertEqual(_client().get("/exchange").status_code, 200)

    def test_audit_page_still_loads(self):
        self.assertEqual(_client().get("/audit").status_code, 200)


# ── Products ──────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestProductsList(unittest.TestCase):

    def _get(self, payload=None):
        c = _client()
        with patch("urace.web.routes.products._dispatch",
                   side_effect=_mock_dispatch(payload or _PRODUCTS_LIST)):
            return c.get("/api/products/", headers=AUTH)

    def test_returns_list(self):
        body = self._get()
        self.assertEqual(body.status_code, 200)
        self.assertIsInstance(body.json(), list)

    def test_has_two_products(self):
        self.assertEqual(len(self._get().json()), 2)

    def test_active_product_flagged(self):
        products = self._get().json()
        active = [p for p in products if p["active"]]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["name"], "alpha")

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/products/").status_code, 401)

    def test_parse_error_returns_empty(self):
        c = _client()
        with patch("urace.web.routes.products._dispatch",
                   return_value={"output": "not json"}):
            r = c.get("/api/products/", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestProductsStatus(unittest.TestCase):

    def _get(self, payload=None):
        c = _client()
        with patch("urace.web.routes.products._dispatch",
                   side_effect=_mock_dispatch(payload or _PRODUCTS_STATUS)):
            return c.get("/api/products/status", headers=AUTH)

    def test_active_product_name(self):
        self.assertEqual(self._get().json()["active_product"], "alpha")

    def test_total_count(self):
        self.assertEqual(self._get().json()["total"], 2)

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/products/status").status_code, 401)

    def test_parse_error_returns_safe_default(self):
        c = _client()
        with patch("urace.web.routes.products._dispatch",
                   return_value={"output": "bad json {{"}):
            r = c.get("/api/products/status", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("active_product", r.json())
        self.assertIsNone(r.json()["active_product"])


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestProductsSwitch(unittest.TestCase):

    def test_dispatches_switch_argv(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({"status": "ok", "switched_to": "beta"})}

        c = _client()
        with patch("urace.web.routes.products._dispatch", side_effect=_fake):
            r = c.post("/api/products/beta/switch", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("beta", captured["argv"])
        self.assertIn("switch", captured["argv"])

    def test_requires_auth(self):
        self.assertEqual(_client().post("/api/products/beta/switch").status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestProductsActivateDeactivate(unittest.TestCase):

    def test_activate_dispatches_activate_argv(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({"status": "ok"})}

        c = _client()
        with patch("urace.web.routes.products._dispatch", side_effect=_fake):
            r = c.post("/api/products/alpha/activate", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("activate", captured["argv"])
        self.assertIn("alpha", captured["argv"])

    def test_deactivate_dispatches_deactivate_argv(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({"status": "ok"})}

        c = _client()
        with patch("urace.web.routes.products._dispatch", side_effect=_fake):
            r = c.post("/api/products/alpha/deactivate", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("deactivate", captured["argv"])

    def test_activate_requires_auth(self):
        self.assertEqual(_client().post("/api/products/alpha/activate").status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestProductsImprovements(unittest.TestCase):

    def _get(self):
        c = _client()
        with patch("urace.web.routes.products._dispatch",
                   side_effect=_mock_dispatch(_PRODUCTS_IMPROVEMENTS)):
            return c.get("/api/products/improvements", headers=AUTH)

    def test_returns_products_key(self):
        body = self._get().json()
        self.assertIn("products", body)

    def test_has_improvement_entries(self):
        body = self._get().json()
        self.assertEqual(len(body["products"][0]["improvements"]), 2)

    def test_parse_error_returns_safe_default(self):
        c = _client()
        with patch("urace.web.routes.products._dispatch",
                   return_value={"output": ""}):
            r = c.get("/api/products/improvements", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("products", r.json())

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/products/improvements").status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestProductsPage(unittest.TestCase):

    def test_page_loads(self):
        self.assertEqual(_client().get("/products").status_code, 200)

    def test_page_has_product_references(self):
        html = _client().get("/products").text.lower()
        self.assertIn("product", html)


# ── Fleet ─────────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestFleetStatus(unittest.TestCase):

    def _get(self, payload=None):
        c = _client()
        with patch("urace.web.routes.fleet._dispatch",
                   side_effect=_mock_dispatch(payload or _FLEET_STATUS)):
            return c.get("/api/fleet/status", headers=AUTH)

    def test_returns_list(self):
        self.assertIsInstance(self._get().json(), list)

    def test_has_two_members(self):
        self.assertEqual(len(self._get().json()), 2)

    def test_healthy_flag_present(self):
        members = self._get().json()
        self.assertIn("healthy", members[0])

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/fleet/status").status_code, 401)

    def test_parse_error_returns_empty_list(self):
        c = _client()
        with patch("urace.web.routes.fleet._dispatch",
                   return_value={"output": "bad json"}):
            r = c.get("/api/fleet/status", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestFleetCapacity(unittest.TestCase):

    def _get(self, payload=None):
        c = _client()
        with patch("urace.web.routes.fleet._dispatch",
                   side_effect=_mock_dispatch(payload or _FLEET_CAPACITY)):
            return c.get("/api/fleet/capacity", headers=AUTH)

    def test_fleet_size_present(self):
        self.assertEqual(self._get().json()["fleet_size"], 2)

    def test_members_list_present(self):
        body = self._get().json()
        self.assertIn("members", body)
        self.assertEqual(len(body["members"]), 2)

    def test_parse_error_returns_safe_default(self):
        c = _client()
        with patch("urace.web.routes.fleet._dispatch",
                   return_value={"output": ""}):
            r = c.get("/api/fleet/capacity", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("fleet_size", body)
        self.assertEqual(body["fleet_size"], 0)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestFleetRun(unittest.TestCase):

    def test_dry_run_flag_passed(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps(_FLEET_RUN_RESULT)}

        c = _client()
        with patch("urace.web.routes.fleet._dispatch", side_effect=_fake):
            r = c.post("/api/fleet/run", json={"dry_run": True}, headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("--dry-run", captured["argv"])

    def test_live_run_omits_dry_run_flag(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps({**_FLEET_RUN_RESULT, "dry_run": False})}

        c = _client()
        with patch("urace.web.routes.fleet._dispatch", side_effect=_fake):
            c.post("/api/fleet/run", json={"dry_run": False}, headers=AUTH)
        self.assertNotIn("--dry-run", captured.get("argv", []))

    def test_requires_auth(self):
        self.assertEqual(_client().post("/api/fleet/run", json={"dry_run": True}).status_code, 401)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestFleetBroadcast(unittest.TestCase):

    def test_dispatches_broadcast_argv(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps(_FLEET_BROADCAST_RESULT)}

        c = _client()
        with patch("urace.web.routes.fleet._dispatch", side_effect=_fake):
            r = c.post("/api/fleet/broadcast", json={"command": "status"}, headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("broadcast", captured["argv"])

    def test_requires_auth(self):
        self.assertEqual(_client().post("/api/fleet/broadcast", json={"command": "x"}).status_code, 401)

    def test_missing_command_returns_422(self):
        self.assertEqual(_client().post("/api/fleet/broadcast", json={}, headers=AUTH).status_code, 422)


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestFleetConfigPush(unittest.TestCase):

    def test_dispatches_config_push_argv(self):
        captured = {}
        def _fake(argv):
            captured["argv"] = argv
            return {"output": json.dumps(_FLEET_CONFIG_PUSH_RESULT)}

        c = _client()
        with patch("urace.web.routes.fleet._dispatch", side_effect=_fake):
            r = c.post("/api/fleet/config-push",
                       json={"key": "aps_threshold", "value": "0.75"},
                       headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("config-push", captured["argv"])
        self.assertIn("aps_threshold", captured["argv"])
        self.assertIn("0.75", captured["argv"])

    def test_missing_key_returns_422(self):
        c = _client()
        r = c.post("/api/fleet/config-push", json={"value": "0.75"}, headers=AUTH)
        self.assertEqual(r.status_code, 422)

    def test_missing_value_returns_422(self):
        c = _client()
        r = c.post("/api/fleet/config-push", json={"key": "aps_threshold"}, headers=AUTH)
        self.assertEqual(r.status_code, 422)

    def test_requires_auth(self):
        self.assertEqual(
            _client().post("/api/fleet/config-push",
                           json={"key": "k", "value": "v"}).status_code,
            401,
        )


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestFleetPage(unittest.TestCase):

    def test_page_loads(self):
        self.assertEqual(_client().get("/fleet").status_code, 200)

    def test_page_has_fleet_references(self):
        html = _client().get("/fleet").text.lower()
        self.assertIn("fleet", html)


# ── Portfolio ─────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPortfolioFeedback(unittest.TestCase):

    def _get(self, payload=None):
        c = _client()
        with patch("urace.web.routes.portfolio._dispatch",
                   side_effect=_mock_dispatch(payload or _PORTFOLIO_FEEDBACK)):
            return c.get("/api/portfolio/feedback", headers=AUTH)

    def test_phase_present(self):
        self.assertEqual(self._get().json()["phase"], "SELECTION")

    def test_variants_list_present(self):
        body = self._get().json()
        self.assertIn("variants", body)
        self.assertEqual(len(body["variants"]), 2)

    def test_variant_has_aps_score(self):
        variants = self._get().json()["variants"]
        self.assertIn("aps_score", variants[0])

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/portfolio/feedback").status_code, 401)

    def test_parse_error_returns_safe_default(self):
        c = _client()
        with patch("urace.web.routes.portfolio._dispatch",
                   return_value={"output": "not json"}):
            r = c.get("/api/portfolio/feedback", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("phase", body)
        self.assertEqual(body["phase"], "UNKNOWN")


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPortfolioStatus(unittest.TestCase):

    def _get(self, payload=None):
        c = _client()
        with patch("urace.web.routes.portfolio._dispatch",
                   side_effect=_mock_dispatch(payload or _PORTFOLIO_STATUS)):
            return c.get("/api/portfolio/status", headers=AUTH)

    def test_active_product_present(self):
        self.assertEqual(self._get().json()["active_product"], "alpha")

    def test_cycle_count_present(self):
        self.assertEqual(self._get().json()["cycle_count"], 42)

    def test_requires_auth(self):
        self.assertEqual(_client().get("/api/portfolio/status").status_code, 401)

    def test_parse_error_returns_error_dict(self):
        c = _client()
        with patch("urace.web.routes.portfolio._dispatch",
                   return_value={"output": ""}):
            r = c.get("/api/portfolio/status", headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertIn("error", r.json())


@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPortfolioPage(unittest.TestCase):

    def test_page_loads(self):
        self.assertEqual(_client().get("/portfolio").status_code, 200)

    def test_page_has_portfolio_references(self):
        html = _client().get("/portfolio").text.lower()
        self.assertIn("portfolio", html)


# ── Navigation ────────────────────────────────────────────────────────────────

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestPhase4Navigation(unittest.TestCase):

    def test_nav_has_products(self):
        self.assertIn("/products", _client().get("/shell").text)

    def test_nav_has_fleet(self):
        self.assertIn("/fleet", _client().get("/shell").text)

    def test_nav_has_portfolio(self):
        self.assertIn("/portfolio", _client().get("/shell").text)

    def test_phase3_nav_links_still_present(self):
        html = _client().get("/shell").text
        self.assertIn("/compliance", html)
        self.assertIn("/github", html)
        self.assertIn("/exchange", html)


if __name__ == "__main__":
    unittest.main()
