"""Phase II-D — URACEConfig pydantic model tests."""
import unittest


class URACEConfigModelTests(unittest.TestCase):
    def setUp(self):
        try:
            from urace.config_schema import URACEConfig, model_validate_config, _PYDANTIC_AVAILABLE
            if not _PYDANTIC_AVAILABLE or URACEConfig is None:
                self.skipTest("pydantic not installed")
            self.URACEConfig = URACEConfig
            self.model_validate_config = model_validate_config
        except ImportError:
            self.skipTest("pydantic not installed")

    def test_empty_config_uses_defaults(self):
        cfg = self.URACEConfig.model_validate({})
        self.assertEqual(cfg.execution_workflow, "core")
        self.assertFalse(cfg.capability_flags.p2p_mint_enabled)
        self.assertFalse(cfg.network.enabled)

    def test_valid_config_passes(self):
        errors = self.model_validate_config({
            "capability_flags": {"executor_enabled": True},
            "network": {"enabled": False, "port": 7301},
            "executor": {"enabled": False},
        })
        self.assertEqual(errors, [])

    def test_invalid_port_returns_error(self):
        errors = self.model_validate_config({"network": {"port": 99999}})
        self.assertTrue(any("port" in e["path"] for e in errors))

    def test_invalid_enum_returns_error(self):
        errors = self.model_validate_config({"execution_workflow": "unknown"})
        self.assertTrue(len(errors) > 0)

    def test_invalid_bool_coerces_leniently(self):
        # pydantic v2 lax mode coerces "yes"/"true"/1 to bool — not an error
        errors = self.model_validate_config({"capability_flags": {"executor_enabled": "yes"}})
        self.assertEqual(errors, [])

    def test_invalid_effort_enum_returns_error(self):
        errors = self.model_validate_config({"resources": {"effort": "extreme"}})
        self.assertTrue(len(errors) > 0)

    def test_extra_keys_pass_through(self):
        errors = self.model_validate_config({"custom_product_key": "value"})
        self.assertEqual(errors, [])

    def test_roundtrip_serialization(self):
        cfg = self.URACEConfig.model_validate({
            "execution_workflow": "specification-trial",
            "network": {"port": 8000, "enabled": True},
        })
        d = cfg.model_dump(exclude_unset=False)
        self.assertEqual(d["execution_workflow"], "specification-trial")
        self.assertEqual(d["network"]["port"], 8000)

    def test_model_validate_config_returns_list(self):
        result = self.model_validate_config({})
        self.assertIsInstance(result, list)

    def test_nested_port_validation(self):
        errors = self.model_validate_config({"api": {"a2a": {"port": 0}}})
        self.assertTrue(len(errors) > 0)
