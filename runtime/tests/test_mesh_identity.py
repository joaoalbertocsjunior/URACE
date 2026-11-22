import pathlib
import tempfile
import unittest
from urace.mesh_identity import generate_mesh_id, get_or_create_mesh_id


class MeshIdentityTests(unittest.TestCase):

    def test_generate_has_correct_format(self):
        mid = generate_mesh_id()
        self.assertTrue(mid.startswith('mesh-'))
        self.assertEqual(len(mid), 37)

    def test_generate_is_unique(self):
        self.assertNotEqual(generate_mesh_id(), generate_mesh_id())

    def test_get_or_create_stable(self):
        with tempfile.TemporaryDirectory() as d:
            m1 = get_or_create_mesh_id(d)
            m2 = get_or_create_mesh_id(d)
            self.assertEqual(m1, m2)

    def test_get_or_create_persists_file(self):
        with tempfile.TemporaryDirectory() as d:
            get_or_create_mesh_id(d)
            self.assertTrue((pathlib.Path(d) / 'mesh_id.txt').exists())

    def test_get_or_create_valid_format(self):
        with tempfile.TemporaryDirectory() as d:
            mid = get_or_create_mesh_id(d)
            self.assertTrue(mid.startswith('mesh-'))
            self.assertEqual(len(mid), 37)
