"""Tests for urace.local_feature_sources — ledger binding verifier."""
import tempfile
import unittest
from pathlib import Path


def _feature(tags=None, files=None, manifest=None, license_id="Apache-2.0"):
    return {
        "tags": tags or [],
        "artifact_discovery": {
            "local_source_files": files,
            "source_license_id": license_id,
            "source_manifest_sha256": manifest or "a" * 64,
        },
    }


class NoBindingTests(unittest.TestCase):
    def test_no_artifact_discovery_key(self):
        from urace.local_feature_sources import resolve_local_source_binding
        result = resolve_local_source_binding({})
        self.assertEqual(result["status"], "NO_LOCAL_SOURCE_BINDING")

    def test_empty_files_list(self):
        from urace.local_feature_sources import resolve_local_source_binding
        result = resolve_local_source_binding(_feature(files=[]))
        self.assertEqual(result["status"], "NO_LOCAL_SOURCE_BINDING")

    def test_none_files(self):
        from urace.local_feature_sources import resolve_local_source_binding
        result = resolve_local_source_binding(_feature(files=None))
        self.assertEqual(result["status"], "NO_LOCAL_SOURCE_BINDING")


class InvalidBindingTests(unittest.TestCase):
    def test_wrong_license_id(self):
        from urace.local_feature_sources import resolve_local_source_binding
        feature = _feature(files=[{"path": "runtime/urace/cli.py"}], license_id="MIT")
        result = resolve_local_source_binding(feature)
        self.assertEqual(result["status"], "INVALID_LOCAL_SOURCE_BINDING")

    def test_missing_manifest_sha256(self):
        from urace.local_feature_sources import resolve_local_source_binding
        feature = {
            "tags": [],
            "artifact_discovery": {
                "local_source_files": [{"path": "runtime/urace/cli.py"}],
                "source_license_id": "Apache-2.0",
                "source_manifest_sha256": None,
            },
        }
        result = resolve_local_source_binding(feature)
        self.assertEqual(result["status"], "INVALID_LOCAL_SOURCE_BINDING")


class ResolveTests(unittest.TestCase):
    def _repo_root(self):
        import urace
        return Path(urace.__file__).resolve().parents[2]

    def test_non_dict_feature_returns_no_binding(self):
        from urace.local_feature_sources import resolve_local_source_binding
        result = resolve_local_source_binding("not_a_dict")
        self.assertEqual(result["status"], "NO_LOCAL_SOURCE_BINDING")

    def test_source_files_key_in_result(self):
        from urace.local_feature_sources import resolve_local_source_binding
        result = resolve_local_source_binding({})
        self.assertIn("source_files", result)

    def test_path_not_matching_tags_no_verified_files(self):
        from urace.local_feature_sources import resolve_local_source_binding
        feature = _feature(
            tags=["nonexistent_module_xyz"],
            files=[{"path": "runtime/urace/nonexistent_module_xyz.py",
                    "sha256": "b" * 64, "size": 100}],
        )
        repo = self._repo_root()
        result = resolve_local_source_binding(feature, repo_root=repo)
        self.assertIn(result["status"], ("NO_MATCHING_LOCAL_FILES", "NO_LOCAL_SOURCE_BINDING",
                                         "PARTIAL_MATCH", "MANIFEST_MISMATCH", "INVALID_LOCAL_SOURCE_BINDING"))
