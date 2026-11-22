"""Property-based tests using hypothesis for algorithmic invariants."""
import time
import unittest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# TPS routing weights always stay within declared bounds
# ---------------------------------------------------------------------------
from urace.p2p_matching import (
    ThroughputTracker, TPS_WEIGHT_MIN, TPS_WEIGHT_MAX, _TPS_MIN_SAMPLES,
)

class TpsWeightPropertyTests(unittest.TestCase):

    @given(st.floats(min_value=0.01, max_value=10_000.0, allow_nan=False))
    @settings(max_examples=500)
    def test_weight_always_in_bounds(self, mean_tps):
        tracker = ThroughputTracker()
        for _ in range(_TPS_MIN_SAMPLES):
            tracker.record_tps('e', 'm', tokens_generated=int(mean_tps * 10),
                                elapsed_seconds=10.0)
        w = tracker.get_routing_weight('e', 'm', reference_tps=mean_tps or 1.0)
        self.assertGreaterEqual(w, TPS_WEIGHT_MIN)
        self.assertLessEqual(w, TPS_WEIGHT_MAX)

    @given(st.floats(min_value=0.01, max_value=10_000.0, allow_nan=False),
           st.floats(min_value=0.001, max_value=1_000.0, allow_nan=False))
    @settings(max_examples=300)
    def test_weight_monotone_with_tps(self, slow_tps, fast_delta):
        assume(fast_delta > 0.1)
        fast_tps = slow_tps + fast_delta
        tracker_slow = ThroughputTracker()
        tracker_fast = ThroughputTracker()
        ref = slow_tps
        for _ in range(_TPS_MIN_SAMPLES):
            tracker_slow.record_tps('e', 'm', tokens_generated=int(slow_tps * 10),
                                    elapsed_seconds=10.0)
            tracker_fast.record_tps('e', 'm', tokens_generated=int(fast_tps * 10),
                                    elapsed_seconds=10.0)
        w_slow = tracker_slow.get_routing_weight('e', 'm', reference_tps=ref)
        w_fast = tracker_fast.get_routing_weight('e', 'm', reference_tps=ref)
        self.assertLessEqual(w_slow, w_fast + 1e-9)


# ---------------------------------------------------------------------------
# Cache cost formula: economical iff cache_cost < cold_prefill_cost
# ---------------------------------------------------------------------------
from urace.freeform_routing import (
    CacheEvidence, record_cache_evidence, select_cache_target,
    _CACHE_EVIDENCE, _CACHE_LOCK,
)

class CacheCostPropertyTests(unittest.TestCase):

    def _make(self, matched_tokens, queue_delay_ms, restore_ms, prefill_micros):
        return CacheEvidence(
            target_id='p', prefix_hash='h',
            matched_tokens=matched_tokens,
            queue_delay_ms=queue_delay_ms,
            restore_ms=restore_ms,
            observed_at=time.time(),
            prefill_micros_per_token=prefill_micros,
        )

    @given(
        st.integers(min_value=1, max_value=100_000),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.floats(min_value=1.0, max_value=1_000.0, allow_nan=False),
    )
    @settings(max_examples=500)
    def test_cache_selection_consistent_with_cost(
        self, tokens, q_ms, r_ms, ppmt
    ):
        with _CACHE_LOCK:
            _CACHE_EVIDENCE.clear()
        e = self._make(tokens, q_ms, r_ms, ppmt)
        record_cache_evidence(e)
        result = select_cache_target(['p'], 'h', min_saved_tokens=0)
        cache_cost = (q_ms + r_ms) * 1000
        cold_cost = tokens * ppmt
        if cache_cost < cold_cost:
            self.assertIsNotNone(result)
        else:
            # may or may not select; just check no exception raised
            pass


# ---------------------------------------------------------------------------
# LocalRouteReputation: score always in (0, 1]
# ---------------------------------------------------------------------------
from urace.freeform_routing import LocalRouteReputation

class ReputationPropertyTests(unittest.TestCase):

    @given(
        st.lists(st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
                 min_size=1, max_size=20),
    )
    @settings(max_examples=300)
    def test_score_always_in_range(self, penalties):
        rep = LocalRouteReputation()
        for p in penalties:
            rep.record_failure('peer', penalty=p)
        score = rep.get_score('peer')
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)
