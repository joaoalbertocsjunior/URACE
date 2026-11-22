import time
import unittest
from urace.freeform_routing import (
    CacheEvidence,
    record_cache_evidence,
    evict_stale_cache_evidence,
    select_cache_target,
    select_target,
    _CACHE_EVIDENCE,
    _CACHE_LOCK,
)


class CacheAwareRoutingTests(unittest.TestCase):

    def _make_evidence(self, target_id='peer-1', prefix_hash='abc123',
                       matched_tokens=512, queue_delay_ms=10, restore_ms=5,
                       prefill_micros_per_token=50, age_seconds=0):
        return CacheEvidence(
            target_id=target_id,
            prefix_hash=prefix_hash,
            matched_tokens=matched_tokens,
            queue_delay_ms=queue_delay_ms,
            restore_ms=restore_ms,
            observed_at=time.time() - age_seconds,
            prefill_micros_per_token=prefill_micros_per_token,
        )

    def setUp(self):
        with _CACHE_LOCK:
            _CACHE_EVIDENCE.clear()

    def test_eviction_removes_expired_entries(self):
        e = self._make_evidence(age_seconds=1000)
        record_cache_evidence(e)
        count = evict_stale_cache_evidence(ttl_seconds=60)
        self.assertEqual(count, 1)
        with _CACHE_LOCK:
            self.assertEqual(len(_CACHE_EVIDENCE), 0)

    def test_recent_entry_survives_eviction(self):
        e = self._make_evidence(age_seconds=10)
        record_cache_evidence(e)
        count = evict_stale_cache_evidence(ttl_seconds=900)
        self.assertEqual(count, 0)

    def test_select_cache_target_returns_none_below_min_tokens(self):
        e = self._make_evidence(matched_tokens=50)
        record_cache_evidence(e)
        result = select_cache_target(['peer-1'], e.prefix_hash, min_saved_tokens=256)
        self.assertIsNone(result)

    def test_select_cache_target_returns_none_when_target_not_in_candidates(self):
        e = self._make_evidence(target_id='peer-1', matched_tokens=512)
        record_cache_evidence(e)
        result = select_cache_target(['peer-2', 'peer-3'], e.prefix_hash)
        self.assertIsNone(result)

    def test_queue_delay_can_make_cache_hit_uneconomical(self):
        # cold prefill = 10 tokens * 50 µs = 500 µs
        # cache cost = queue_delay_ms=10000 * 1000 = 10_000_000 µs >> 500 µs
        e = self._make_evidence(
            matched_tokens=10,
            queue_delay_ms=10000,
            restore_ms=0,
            prefill_micros_per_token=50,
        )
        record_cache_evidence(e)
        result = select_cache_target(['peer-1'], e.prefix_hash)
        self.assertIsNone(result)

    def test_economical_cache_hit_is_returned(self):
        # cold prefill = 1024 * 50 = 51200 µs
        # cache cost = 1ms queue + 1ms restore = 2000 µs << 51200 µs
        e = self._make_evidence(
            matched_tokens=1024, queue_delay_ms=1, restore_ms=1,
            prefill_micros_per_token=50,
        )
        record_cache_evidence(e)
        result = select_cache_target(['peer-1'], e.prefix_hash)
        self.assertIsNotNone(result)
        self.assertEqual(result.target_id, 'peer-1')

    def test_affinity_applied_when_cache_hit_chosen(self):
        e = self._make_evidence(
            matched_tokens=1024, queue_delay_ms=1, restore_ms=1,
            prefill_micros_per_token=50,
        )
        record_cache_evidence(e)
        target, applied = select_target(
            ['peer-1', 'peer-2'], e.prefix_hash, None,
            ttl_seconds=900, min_saved_tokens=256,
        )
        self.assertEqual(target, 'peer-1')
        self.assertTrue(applied)

    def test_no_cache_evidence_returns_first_candidate(self):
        target, applied = select_target(['peer-A', 'peer-B'], None, None)
        self.assertEqual(target, 'peer-A')
        self.assertFalse(applied)
