from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from urace import cli


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config


class CapabilityGateEnforcementTests(unittest.TestCase):

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_cycle_blocked_when_capability_breach_gap_present(self):
        self.state.setdefault("integrity_gaps", []).append({
            "id": "g1",
            "kind": "capability-envelope-breach",
            "resolved": False,
            "severity": "WARNING",
            "detail": "test breach",
        })
        result = cli.cycle(self.config, self.state)
        self.assertEqual(result["outcome"], "blocked")
        self.assertIn("capability-envelope-breach", result["reason"])
        self.assertIn("AUTHORITY_GRANT", result["reason"])
        self.assertEqual(self.state["lifecycle_state"], "BLOCKED")

    def test_cycle_not_blocked_when_gap_resolved(self):
        self.state.setdefault("integrity_gaps", []).append({
            "id": "g2",
            "kind": "capability-envelope-breach",
            "resolved": True,
            "severity": "WARNING",
            "detail": "resolved breach",
        })
        with patch.object(cli, "document_metrics", return_value={"normative_rules": 1.0, "behavioral_tests": 1.0, "unresolved_markers": 0.0}):
            result = cli.cycle(self.config, self.state)
        self.assertNotEqual(result["outcome"], "blocked")

    def test_cycle_not_blocked_when_no_capability_gaps(self):
        self.state["integrity_gaps"] = []
        with patch.object(cli, "document_metrics", return_value={"normative_rules": 1.0, "behavioral_tests": 1.0, "unresolved_markers": 0.0}):
            result = cli.cycle(self.config, self.state)
        self.assertNotEqual(result["outcome"], "blocked")
        self.assertNotEqual(self.state["lifecycle_state"], "BLOCKED")
