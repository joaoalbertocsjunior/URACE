import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import common


class RelocationTests(unittest.TestCase):
    def test_relocates_only_original_tree_and_preserves_external_references(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(common, 'BASE', Path(directory)):
            base = Path(directory)
            (base/'path-relocations.json').write_text(json.dumps({'previous_roots': ['/previous/RUNTIME']}))
            self.assertEqual(common.evidence_path('/previous/RUNTIME/versions/v1'), base/'versions/v1')
            self.assertEqual(common.evidence_path('/external/manifest'), Path('/external/manifest'))
            with self.assertRaises(ValueError):
                common.evidence_path('/previous/RUNTIME/../../outside')

    def test_unmigrated_installation_has_unchanged_resolution(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(common, 'BASE', Path(directory)):
            self.assertEqual(common.evidence_path('/previous/RUNTIME/versions'), Path('/previous/RUNTIME/versions'))
