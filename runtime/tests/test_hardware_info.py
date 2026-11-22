import unittest
from urace.hardware_info import survey_hardware, get_hardware_info, hardware_gossip_payload, HardwareInfo

class HardwareInfoTests(unittest.TestCase):

    def test_survey_returns_hardware_info(self):
        hw = survey_hardware()
        self.assertIsInstance(hw, HardwareInfo)

    def test_cpu_count_non_negative(self):
        hw = survey_hardware()
        self.assertGreaterEqual(hw.cpu_count, 0)

    def test_ram_mb_non_negative(self):
        hw = survey_hardware()
        self.assertGreaterEqual(hw.ram_mb, 0)

    def test_gpu_vram_lists_parallel(self):
        hw = survey_hardware()
        self.assertEqual(len(hw.gpu_names), len(hw.vram_mb))

    def test_gossip_payload_has_expected_keys(self):
        payload = hardware_gossip_payload()
        for key in ('cpu_count', 'ram_mb', 'gpu_names', 'vram_mb'):
            self.assertIn(key, payload)

    def test_cache_returns_same_instance(self):
        a = get_hardware_info()
        b = get_hardware_info()
        self.assertIs(a, b)

    def test_refresh_returns_new_instance(self):
        get_hardware_info()
        b = get_hardware_info(refresh=True)
        self.assertIsInstance(b, HardwareInfo)
