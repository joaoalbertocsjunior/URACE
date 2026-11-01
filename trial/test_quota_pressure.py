"""Tests for quota_pressure module."""
import json
import tempfile
from pathlib import Path
import unittest
import quota_pressure


def _write_preflight(base, quota_events):
    path = Path(base) / 'claude-preflight-latest.json'
    path.write_text(json.dumps({'receipt': {'quota_events': quota_events}}))


class Tests(unittest.TestCase):
    def test_returns_none_when_no_file(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);tmp_path=Path(temporary.name)
        assert quota_pressure.claude_utilization(tmp_path) is None
    
    
    def test_reads_seven_day_utilization(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);tmp_path=Path(temporary.name)
        _write_preflight(tmp_path, [
            {'rateLimitType': 'hourly', 'utilization': 0.50},
            {'rateLimitType': 'seven_day', 'utilization': 0.96},
        ])
        assert quota_pressure.claude_utilization(tmp_path) == 0.96
    
    
    def test_high_pressure_true_above_threshold(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);tmp_path=Path(temporary.name)
        _write_preflight(tmp_path, [{'rateLimitType': 'seven_day', 'utilization': 0.90}])
        assert quota_pressure.is_high_pressure(tmp_path, threshold=0.85) is True
    
    
    def test_high_pressure_false_below_threshold(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);tmp_path=Path(temporary.name)
        _write_preflight(tmp_path, [{'rateLimitType': 'seven_day', 'utilization': 0.80}])
        assert quota_pressure.is_high_pressure(tmp_path, threshold=0.85) is False
    
    
    def test_high_pressure_false_when_unknown(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);tmp_path=Path(temporary.name)
        assert quota_pressure.is_high_pressure(tmp_path) is False
