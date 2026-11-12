"""Tests for urace.runtime_cycle_cli — cycle settings constants."""
import unittest


class RuntimeCycleSettingsTests(unittest.TestCase):
    def test_schema_string(self):
        from urace.runtime_cycle_cli import SCHEMA
        self.assertEqual(SCHEMA, "runtime-cycle-v1")

    def test_defaults_has_required_keys(self):
        from urace.runtime_cycle_cli import DEFAULTS
        self.assertIn("enabled", DEFAULTS)
        self.assertIn("auto_deploy", DEFAULTS)
        self.assertIn("interval_seconds", DEFAULTS)

    def test_enabled_false_by_default(self):
        from urace.runtime_cycle_cli import DEFAULTS
        self.assertFalse(DEFAULTS["enabled"])

    def test_interval_seconds_positive(self):
        from urace.runtime_cycle_cli import DEFAULTS
        self.assertGreater(DEFAULTS["interval_seconds"], 0)

    def test_schema_is_string(self):
        from urace.runtime_cycle_cli import SCHEMA
        self.assertIsInstance(SCHEMA, str)
