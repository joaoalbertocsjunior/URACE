"""Security tests for remote_assets.py.

remote_assets.py is a CRITICAL security surface: it handles P2P artifact
discovery and bounded delivery from untrusted peers over the network.

These tests verify the security-critical invariants WITHOUT real network calls:
  1. validate_catalog rejects malformed, expired, and oversized catalogs
  2. OPEN_ASSET_LIMIT is enforced — oversized artifacts are rejected
  3. CATALOG_LIMIT is enforced — oversized catalogs are rejected
  4. Asset identity hashes must match contents (tamper detection)
  5. Only open/free assets are accepted (payment_enabled=False, usage_price=0)
  6. SHA-256 artifact digest format is validated (64 hex chars)
"""
import hashlib
import json
import time
import unittest


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _minimal_open_asset(peer_id: str, feature_id: str = "feature-test-001") -> dict:
    artifact_sha = "a" * 64
    item = {
        "seller_peer_id": peer_id,
        "feature_id": feature_id,
        "description": "test feature",
        "spec_context": "",
        "tags": [],
        "dependencies": [],
        "artifact_sha256": artifact_sha,
        "artifact_size_bytes": 100,
        "content_type": "application/octet-stream",
        "license_id": "Apache-2.0",
        "usage_price_units": 0,
        "payment_enabled": False,
    }
    item["asset_id"] = _sha(_canonical(item))
    return item


def _minimal_valid_catalog(peer_id: str) -> dict:
    now = time.time()
    return {
        "schema": "urace-public-asset-catalog-v1",
        "seller_peer_id": peer_id,
        "created_unix": now,
        "expires_unix": now + 300,
        "open_assets": [_minimal_open_asset(peer_id)],
        "paid_listings": [],
        "settlement_supported": False,
        "price_interpretation": "test",
    }


class ValidateCatalogSchemaTests(unittest.TestCase):
    """validate_catalog must reject catalogs with wrong schema."""

    def test_valid_catalog_passes(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        result = validate_catalog(catalog, peer_id)
        self.assertIsNotNone(result)

    def test_wrong_schema_rejected(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        catalog["schema"] = "wrong-schema-v99"
        with self.assertRaises(ValueError):
            validate_catalog(catalog, peer_id)

    def test_peer_id_mismatch_rejected(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        with self.assertRaises(ValueError):
            validate_catalog(catalog, "different-peer")

    def test_expired_catalog_rejected(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        catalog["created_unix"] = time.time() - 400
        catalog["expires_unix"] = time.time() - 100
        with self.assertRaises(ValueError):
            validate_catalog(catalog, peer_id)

    def test_missing_created_unix_rejected(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        del catalog["created_unix"]
        with self.assertRaises((ValueError, TypeError, KeyError)):
            validate_catalog(catalog, peer_id)

    def test_non_dict_rejected(self):
        from urace.remote_assets import validate_catalog
        with self.assertRaises((ValueError, AttributeError, TypeError)):
            validate_catalog("not a dict", "peer-aaaaaa")


class CatalogLimitTests(unittest.TestCase):
    """CATALOG_LIMIT must be enforced — oversized catalogs are rejected."""

    def test_catalog_limit_constant_exists(self):
        from urace.remote_assets import CATALOG_LIMIT
        self.assertGreater(CATALOG_LIMIT, 0)
        self.assertLessEqual(CATALOG_LIMIT, 1000)

    def test_oversized_catalog_rejected(self):
        from urace.remote_assets import validate_catalog, CATALOG_LIMIT
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        catalog["open_assets"] = [_minimal_open_asset(peer_id, f"feat-{i}") for i in range(CATALOG_LIMIT + 1)]
        with self.assertRaises(ValueError):
            validate_catalog(catalog, peer_id)

    def test_catalog_at_limit_accepted(self):
        from urace.remote_assets import validate_catalog, CATALOG_LIMIT
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        catalog["open_assets"] = [_minimal_open_asset(peer_id, f"feat-{i}") for i in range(CATALOG_LIMIT)]
        result = validate_catalog(catalog, peer_id)
        self.assertIsNotNone(result)


class AssetSizeLimitTests(unittest.TestCase):
    """OPEN_ASSET_LIMIT must be enforced — oversized artifacts are rejected."""

    def test_open_asset_limit_constant_exists(self):
        from urace.remote_assets import OPEN_ASSET_LIMIT
        self.assertGreater(OPEN_ASSET_LIMIT, 0)

    def test_asset_exceeding_size_limit_rejected(self):
        from urace.remote_assets import validate_catalog, OPEN_ASSET_LIMIT
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        item = _minimal_open_asset(peer_id)
        item["artifact_size_bytes"] = OPEN_ASSET_LIMIT + 1
        item["asset_id"] = _sha(_canonical({k: v for k, v in item.items() if k != "asset_id"}))
        catalog["open_assets"] = [item]
        with self.assertRaises(ValueError):
            validate_catalog(catalog, peer_id)

    def test_asset_at_size_limit_accepted(self):
        from urace.remote_assets import validate_catalog, OPEN_ASSET_LIMIT
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        item = _minimal_open_asset(peer_id)
        item["artifact_size_bytes"] = OPEN_ASSET_LIMIT
        item["asset_id"] = _sha(_canonical({k: v for k, v in item.items() if k != "asset_id"}))
        catalog["open_assets"] = [item]
        result = validate_catalog(catalog, peer_id)
        self.assertIsNotNone(result)


class AssetIdentityTamperTests(unittest.TestCase):
    """asset_id must be a SHA-256 of the asset content — tamper detection."""

    def test_tampered_asset_id_rejected(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        catalog["open_assets"][0]["asset_id"] = "b" * 64
        with self.assertRaises(ValueError):
            validate_catalog(catalog, peer_id)

    def test_duplicate_asset_id_rejected(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        item = _minimal_open_asset(peer_id)
        catalog["open_assets"] = [item, item]
        with self.assertRaises(ValueError):
            validate_catalog(catalog, peer_id)

    def test_invalid_artifact_sha256_format_rejected(self):
        """artifact_sha256 must be 64 hex chars — rejects truncated or non-hex."""
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        for bad_sha in ["short", "z" * 64, "a" * 63, ""]:
            catalog = _minimal_valid_catalog(peer_id)
            item = _minimal_open_asset(peer_id)
            item["artifact_sha256"] = bad_sha
            item["asset_id"] = _sha(_canonical({k: v for k, v in item.items() if k != "asset_id"}))
            catalog["open_assets"] = [item]
            with self.assertRaises(ValueError, msg=f"Should reject sha256={bad_sha!r}"):
                validate_catalog(catalog, peer_id)


class AssetPaymentFreedomTests(unittest.TestCase):
    """Only open/free assets (usage_price=0, payment_enabled=False) may pass validate_catalog."""

    def test_paid_asset_in_open_assets_rejected(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        item = _minimal_open_asset(peer_id)
        item["usage_price_units"] = 100
        item["asset_id"] = _sha(_canonical({k: v for k, v in item.items() if k != "asset_id"}))
        catalog["open_assets"] = [item]
        with self.assertRaises(ValueError):
            validate_catalog(catalog, peer_id)

    def test_payment_enabled_asset_rejected(self):
        from urace.remote_assets import validate_catalog
        peer_id = "peer-aaaaaa"
        catalog = _minimal_valid_catalog(peer_id)
        item = _minimal_open_asset(peer_id)
        item["payment_enabled"] = True
        item["asset_id"] = _sha(_canonical({k: v for k, v in item.items() if k != "asset_id"}))
        catalog["open_assets"] = [item]
        with self.assertRaises(ValueError):
            validate_catalog(catalog, peer_id)
