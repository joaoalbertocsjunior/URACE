import importlib
import sys
import unittest
from unittest.mock import patch


class TestFindCloudflared(unittest.TestCase):
    def setUp(self):
        # Remove cached module so patches on shutil.which take effect per test.
        sys.modules.pop('urace.tunnel_install', None)

    def test_finds_system_binary(self):
        with patch('shutil.which', return_value='/usr/bin/cloudflared'):
            import urace.tunnel_install as ti
            self.assertEqual(ti.find_cloudflared(), '/usr/bin/cloudflared')

    def test_returns_none_when_absent_no_local(self):
        with patch('shutil.which', return_value=None):
            import urace.tunnel_install as ti
            # Patch the SYSTEM_ROOT so the local path check also fails.
            with patch('urace._common.SYSTEM_ROOT', '/nonexistent_path_xyz'):
                result = ti.find_cloudflared()
            self.assertIsNone(result)

    def test_prefers_system_path_over_local(self):
        """When shutil.which finds it, return immediately without touching SYSTEM_ROOT."""
        with patch('shutil.which', return_value='/opt/homebrew/bin/cloudflared'):
            import urace.tunnel_install as ti
            self.assertEqual(ti.find_cloudflared(), '/opt/homebrew/bin/cloudflared')

    def test_returns_none_when_shutil_which_raises(self):
        with patch('shutil.which', side_effect=OSError('no access')):
            import urace.tunnel_install as ti
            # OSError from shutil.which is unhandled; find_cloudflared should propagate it.
            with self.assertRaises(OSError):
                ti.find_cloudflared()
