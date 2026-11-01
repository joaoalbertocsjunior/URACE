"""Schema export module — programmatic access to all URACE registered schemas (§62t)."""
from __future__ import annotations

from urace.primitives import OUTPUT_SCHEMA_REGISTRY, FEATURE_BUNDLE_REGISTRY


def export_output_schemas(format: str = "json") -> dict:
    """Return all registered OutputSchemas as a structured dict."""
    schemas = [
        {
            "command": cmd,
            "schema_version": info["version"],
            "stable_since": info["stable_since"],
            "fields": info["fields"],
        }
        for cmd, info in sorted(OUTPUT_SCHEMA_REGISTRY.items())
    ]
    return {"schema_version": "1.0", "schemas": schemas, "total": len(schemas)}


def export_feature_bundles(format: str = "json") -> dict:
    """Return all registered FeatureBundles as a structured dict."""
    bundles = [
        {
            "name": name,
            "construct_ids": entry["construct_ids"],
            "description": entry.get("description", ""),
            "spec_version": entry["spec_version"],
            "source": entry["source"],
        }
        for name, entry in sorted(FEATURE_BUNDLE_REGISTRY.items())
    ]
    return {"schema_version": "1.0", "bundles": bundles, "total": len(bundles)}


def export_all(format: str = "json") -> dict:
    """Export all schema registries."""
    return {
        "schema_version": "1.0",
        "output_schemas": export_output_schemas()["schemas"],
        "feature_bundles": export_feature_bundles()["bundles"],
    }
