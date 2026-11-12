"""Tests for relay rewards: issue_relay_credit and track_relay_hop."""
import time
import unittest


class TestTrackRelayHop(unittest.TestCase):
    def test_adds_hop(self):
        from urace.freeform_routing import track_relay_hop
        record = {}
        track_relay_hop(record, "peer-1", hop_latency_ms=42)
        self.assertEqual(len(record['relay_hops']), 1)
        self.assertEqual(record['relay_hops'][0]['relay_peer_id'], "peer-1")
        self.assertEqual(record['relay_hops'][0]['hop_latency_ms'], 42)

    def test_multiple_hops(self):
        from urace.freeform_routing import track_relay_hop
        record = {}
        track_relay_hop(record, "peer-a")
        track_relay_hop(record, "peer-b")
        self.assertEqual(len(record['relay_hops']), 2)

    def test_no_latency(self):
        from urace.freeform_routing import track_relay_hop
        record = {}
        track_relay_hop(record, "peer-x")
        self.assertIsNone(record['relay_hops'][0]['hop_latency_ms'])

    def test_at_timestamp(self):
        from urace.freeform_routing import track_relay_hop
        before = time.time()
        record = {}
        track_relay_hop(record, "peer-t")
        after = time.time()
        self.assertGreaterEqual(record['relay_hops'][0]['at'], before)
        self.assertLessEqual(record['relay_hops'][0]['at'], after)

    def test_returns_record(self):
        from urace.freeform_routing import track_relay_hop
        record = {'existing': True}
        result = track_relay_hop(record, "peer-r")
        self.assertIs(result, record)


class TestIssueRelayCredit(unittest.TestCase):
    def test_basic(self):
        from urace.peer_exchange import issue_relay_credit, RELAY_CREDIT_ISSUED
        exchange = []
        row = issue_relay_credit(exchange, "req-1", "peer-1", 10)
        self.assertEqual(len(exchange), 1)
        self.assertEqual(row['kind'], RELAY_CREDIT_ISSUED)
        self.assertEqual(row['relay_peer_id'], "peer-1")
        self.assertEqual(row['credit_units'], 10)

    def test_appends_to_exchange(self):
        from urace.peer_exchange import issue_relay_credit
        exchange = [{'existing': True}]
        issue_relay_credit(exchange, "req-2", "peer-2", 5)
        self.assertEqual(len(exchange), 2)

    def test_at_field(self):
        from urace.peer_exchange import issue_relay_credit
        exchange = []
        before = time.time()
        issue_relay_credit(exchange, "req-3", "peer-3", 1)
        after = time.time()
        self.assertGreaterEqual(exchange[0]['at'], before)
        self.assertLessEqual(exchange[0]['at'], after)


if __name__ == '__main__':
    unittest.main()
