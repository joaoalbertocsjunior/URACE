import unittest
from urace.peer_discovery import (
    SelectedPathKind,
    RelayPathObservation,
    RelayHealthMonitor,
    heartbeat_failure_threshold,
)
import time


class RelayHealthTests(unittest.TestCase):

    def test_relay_threshold_is_five(self):
        self.assertEqual(heartbeat_failure_threshold(SelectedPathKind.RELAY), 5)

    def test_direct_threshold_is_two(self):
        self.assertEqual(heartbeat_failure_threshold(SelectedPathKind.DIRECT), 2)

    def test_unknown_threshold_is_two(self):
        self.assertEqual(heartbeat_failure_threshold(SelectedPathKind.UNKNOWN), 2)

    def test_should_not_remove_below_threshold(self):
        monitor = RelayHealthMonitor()
        obs = RelayPathObservation(peer_id='p1', kind=SelectedPathKind.RELAY, rtt_ms=50, at=time.time())
        monitor.observe('p1', obs)
        for _ in range(4):  # 4 < 5 relay threshold
            monitor.record_failure('p1')
        self.assertFalse(monitor.should_remove_peer('p1'))

    def test_should_remove_at_threshold(self):
        monitor = RelayHealthMonitor()
        obs = RelayPathObservation(peer_id='p2', kind=SelectedPathKind.DIRECT, rtt_ms=10, at=time.time())
        monitor.observe('p2', obs)
        monitor.record_failure('p2')
        monitor.record_failure('p2')  # 2 >= 2 direct threshold
        self.assertTrue(monitor.should_remove_peer('p2'))

    def test_success_resets_failure_count(self):
        monitor = RelayHealthMonitor()
        monitor.record_failure('p3')
        monitor.record_failure('p3')
        monitor.record_success('p3')
        self.assertEqual(monitor.consecutive_failures('p3'), 0)
        self.assertFalse(monitor.should_remove_peer('p3', SelectedPathKind.DIRECT))
