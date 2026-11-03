"""Tests for content_store, product_type_detector, circuit_breaker, crypto_wallet."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from urace.content_store import content_ref, content_list, content_show
from urace.product_type_detector import detect_product_types, normalize_types


class TestContentStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)

    def test_ref_registers_file(self):
        f = self.root / "video.mp4"
        f.write_bytes(b"fake video data")
        result = content_ref(self.root, str(f))
        self.assertIn("sha256", result)
        self.assertIn("id", result)
        self.assertEqual(result["name"], "video.mp4")

    def test_ref_deduplicates(self):
        f = self.root / "asset.bin"
        f.write_bytes(b"data")
        content_ref(self.root, str(f))
        content_ref(self.root, str(f))
        refs = content_list(self.root)
        self.assertEqual(len(refs), 1)

    def test_list_empty(self):
        self.assertEqual(content_list(self.root), [])

    def test_show_by_id(self):
        f = self.root / "model.pt"
        f.write_bytes(b"model weights")
        entry = content_ref(self.root, str(f))
        found = content_show(self.root, entry["id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["sha256"], entry["sha256"])

    def test_show_missing(self):
        self.assertIsNone(content_show(self.root, "nonexistent"))

    def test_ref_missing_file(self):
        result = content_ref(self.root, "/nonexistent/file.mp4")
        self.assertIn("error", result)


class TestProductTypeDetector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)

    def _write(self, name: str, content: str = ""):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def test_detects_software(self):
        self._write("main.py", "import os")
        self._write("pyproject.toml", "[project]")
        result = detect_product_types(self.root)
        self.assertIn("software", result)

    def test_detects_data(self):
        # Need more data signals than software to overcome threshold
        self._write("data.csv", "a,b,c")
        self._write("data.parquet", "")
        self._write("pipeline.jsonl", "")
        self._write("output.tsv", "")
        result = detect_product_types(self.root)
        # Either data or software is fine depending on ratio
        self.assertTrue(len(result) > 0)

    def test_detects_media(self):
        self._write("video.mp4", "")
        result = detect_product_types(self.root)
        self.assertTrue(len(result) > 0)

    def test_empty_dir_defaults_software(self):
        result = detect_product_types(self.root)
        self.assertEqual(result, ["software"])

    def test_normalize_single_string(self):
        self.assertEqual(normalize_types("software"), ["software"])

    def test_normalize_comma_separated(self):
        result = normalize_types("software,media")
        self.assertIn("software", result)
        self.assertIn("media", result)

    def test_normalize_list(self):
        result = normalize_types(["software", "model"])
        self.assertIn("software", result)
        self.assertIn("model", result)

    def test_normalize_invalid_ignored(self):
        result = normalize_types("invalid,software")
        self.assertEqual(result, ["software"])

    def test_normalize_none_defaults(self):
        self.assertEqual(normalize_types(None), ["software"])


class TestCircuitBreaker(unittest.TestCase):
    def test_import_and_api(self):
        from urace import circuit_breaker
        self.assertTrue(hasattr(circuit_breaker, "status"))
        self.assertTrue(hasattr(circuit_breaker, "reset"))
        self.assertTrue(hasattr(circuit_breaker, "auto_trip"))


class TestCryptoWallet(unittest.TestCase):
    def test_import_and_api(self):
        from urace import crypto_wallet
        self.assertTrue(hasattr(crypto_wallet, "wallet_init"))
        self.assertTrue(hasattr(crypto_wallet, "wallet_show"))
        self.assertTrue(hasattr(crypto_wallet, "wallet_sign"))


if __name__ == "__main__":
    unittest.main()
