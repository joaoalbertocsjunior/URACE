import unittest
from urace.freeform_routing import (
    log_request_ingress, log_request_start, log_request_end,
    get_request_log, _REQUEST_LOG, _REQUEST_LOG_LOCK, _REQUEST_LOG_MAX,
)


class RequestLogTests(unittest.TestCase):

    def setUp(self):
        with _REQUEST_LOG_LOCK:
            _REQUEST_LOG.clear()

    def test_ingress_returns_request_id(self):
        rid = log_request_ingress(target_id='peer-1')
        self.assertIsInstance(rid, str)
        self.assertEqual(len(rid), 32)

    def test_three_phase_lifecycle(self):
        rid = log_request_ingress(target_id='peer-1', affinity_applied=True)
        log_request_start(rid, target_id='peer-1', tokens_in=100)
        log_request_end(rid, tokens_out=200, latency_ms=42.5)
        entries = get_request_log()
        phases = [e.phase for e in entries]
        self.assertEqual(phases, ['ingress', 'start', 'end'])

    def test_get_request_log_respects_limit(self):
        for _ in range(10):
            log_request_ingress()
        entries = get_request_log(limit=3)
        self.assertEqual(len(entries), 3)

    def test_ring_buffer_cap(self):
        for _ in range(_REQUEST_LOG_MAX + 50):
            log_request_ingress()
        with _REQUEST_LOG_LOCK:
            self.assertLessEqual(len(_REQUEST_LOG), _REQUEST_LOG_MAX)

    def test_error_captured_in_end_phase(self):
        rid = log_request_ingress()
        log_request_end(rid, error='timeout')
        entries = get_request_log(limit=1)
        self.assertEqual(entries[-1].error, 'timeout')
