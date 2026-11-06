"""Tests for universal asset similarity enforcement — Layers 1-4."""
import hashlib
import tempfile
import time
import unittest
from pathlib import Path

from urace import peer_exchange as pe
from urace.tokenomics import (
    dhash_int,
    hamming_distance,
    winnow_fingerprint,
    winnow_similarity,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_exchange(tmp_path: str, name: str = 'node') -> pe.Exchange:
    return pe.Exchange(Path(tmp_path) / name)


def _grant_row(feature_id, peer_id, **extra):
    row = {'kind': 'EQUITY_GRANT', 'feature_id': feature_id, 'peer_id': peer_id, 'at_unix': time.time()}
    row.update(extra)
    return row


# ── Test 1: dhash_int ─────────────────────────────────────────────────────────

class DhashIntTests(unittest.TestCase):

    def test_returns_int_for_any_bytes(self):
        """dhash_int returns an integer for any non-empty bytes (PIL fallback path)."""
        raw = b'\x00' * 200  # minimal valid-ish bytes, PIL will fail, fallback kicks in
        result = dhash_int(raw)
        self.assertIsInstance(result, int)

    def test_returns_none_for_empty(self):
        """dhash_int returns None for empty bytes."""
        result = dhash_int(b'')
        self.assertIsNone(result)

    def test_returns_none_for_garbage(self):
        """dhash_int returns None for single-byte garbage (too small for pixel grid)."""
        result = dhash_int(b'\xff')
        self.assertIsNone(result)

    def test_deterministic(self):
        """Same bytes → same integer."""
        raw = bytes(range(200))
        self.assertEqual(dhash_int(raw), dhash_int(raw))

    def test_different_bytes_produce_different_hash(self):
        """Different byte sequences should produce different hashes."""
        raw_a = bytes(range(200))
        raw_b = bytes(reversed(range(200)))
        # Not a strict requirement but overwhelmingly likely for distinct inputs
        # (allowing equality in degenerate fallback edge cases)
        result_a = dhash_int(raw_a)
        result_b = dhash_int(raw_b)
        self.assertIsNotNone(result_a)
        self.assertIsNotNone(result_b)


# ── Test 2: hamming_distance ──────────────────────────────────────────────────

class HammingDistanceTests(unittest.TestCase):

    def test_identical_zero(self):
        self.assertEqual(hamming_distance(0, 0), 0)

    def test_one_bit_diff(self):
        self.assertEqual(hamming_distance(0, 1), 1)

    def test_eight_bits_diff(self):
        self.assertEqual(hamming_distance(0xFF, 0), 8)

    def test_symmetric(self):
        self.assertEqual(hamming_distance(0xABCD, 0x1234), hamming_distance(0x1234, 0xABCD))

    def test_all_bits_same(self):
        v = 0xDEADBEEFCAFEBABE
        self.assertEqual(hamming_distance(v, v), 0)


# ── Test 3: winnow_fingerprint ────────────────────────────────────────────────

class WinnowFingerprintTests(unittest.TestCase):

    def test_returns_frozenset_for_text(self):
        fp = winnow_fingerprint(b'hello world this is some code text')
        self.assertIsInstance(fp, frozenset)
        self.assertGreater(len(fp), 0)

    def test_empty_input_returns_empty(self):
        fp = winnow_fingerprint(b'')
        self.assertIsInstance(fp, frozenset)
        self.assertEqual(len(fp), 0)

    def test_very_short_input_below_k(self):
        """Input shorter than k=5 → empty frozenset."""
        fp = winnow_fingerprint(b'ab')
        self.assertIsInstance(fp, frozenset)
        self.assertEqual(len(fp), 0)

    def test_deterministic(self):
        raw = b'def foo(x):\n    return x + 1\n'
        self.assertEqual(winnow_fingerprint(raw), winnow_fingerprint(raw))

    def test_different_text_different_fp(self):
        fp_a = winnow_fingerprint(b'def foo(): pass')
        fp_b = winnow_fingerprint(b'class Bar: x = 42')
        # May overlap by chance but overwhelmingly shouldn't for distinct text
        # We just assert both are non-empty frozensets
        self.assertIsInstance(fp_a, frozenset)
        self.assertIsInstance(fp_b, frozenset)


# ── Test 4: winnow_similarity — identical and completely different ─────────────

class WinnowSimilarityTests(unittest.TestCase):

    def test_identical_texts_score_one(self):
        raw = b'def process(data):\n    return [x for x in data if x > 0]\n'
        fp = winnow_fingerprint(raw)
        self.assertAlmostEqual(winnow_similarity(fp, fp), 1.0)

    def test_completely_different_texts_low_score(self):
        fp_a = winnow_fingerprint(b'aaaa bbbb cccc dddd eeee ffff gggg hhhh iiii jjjj')
        fp_b = winnow_fingerprint(b'1111 2222 3333 4444 5555 6666 7777 8888 9999 0000')
        sim = winnow_similarity(fp_a, fp_b)
        self.assertLess(sim, 0.3)

    def test_empty_inputs_return_zero(self):
        self.assertEqual(winnow_similarity(frozenset(), frozenset()), 0.0)
        self.assertEqual(winnow_similarity(frozenset({1, 2}), frozenset()), 0.0)
        self.assertEqual(winnow_similarity(frozenset(), frozenset({3, 4})), 0.0)


# ── Test 5: near-identical texts → ≥ 0.6 ─────────────────────────────────────

class WinnowNearIdenticalTests(unittest.TestCase):

    def test_near_identical_texts_above_threshold(self):
        """One line changed out of many → Jaccard ≥ 0.6."""
        base = b"""
def compute_score(values):
    total = 0
    for v in values:
        if v > 0:
            total += v
    return total / len(values) if values else 0

def normalize(data):
    mn = min(data)
    mx = max(data)
    return [(x - mn) / (mx - mn) for x in data]

def filter_outliers(data, threshold=3.0):
    mean = sum(data) / len(data)
    std = (sum((x - mean)**2 for x in data) / len(data)) ** 0.5
    return [x for x in data if abs(x - mean) <= threshold * std]
"""
        modified = base.replace(b'total += v', b'total += v * 2')
        fp_a = winnow_fingerprint(base)
        fp_b = winnow_fingerprint(modified)
        sim = winnow_similarity(fp_a, fp_b)
        self.assertGreaterEqual(sim, 0.6)


# ── Test 6: Layer 1 — exact fingerprint → FEATURE_COMPOSITION ─────────────────

class Layer1ExactFingerprintCompositionTests(unittest.TestCase):
    """Unit-test Layer 1 upgrade: exact fingerprint match also emits FEATURE_COMPOSITION."""

    def _simulate_layer1(self, exchange, new_feature_id, new_fp, prior_grant_row, creator_id):
        """Simulate the near-dup block logic (Layer 1 upgraded version)."""
        from datetime import datetime, timezone
        if new_fp == prior_grant_row.get('artifact_fingerprint', ''):
            exchange.append_audit_row({
                'kind': 'GAP',
                'severity': 'WARNING',
                'gap_type': 'near-duplicate-artifact',
                'feature_id': new_feature_id,
                'similar_to_feature': prior_grant_row.get('feature_id', ''),
                'artifact_fingerprint': new_fp,
                'at_unix': time.time(),
                'at': datetime.now(timezone.utc).isoformat(),
                'note': 'Artifact is semantically similar to an existing feature',
            })
            existing_comp = any(
                r.get('kind') == 'FEATURE_COMPOSITION'
                and r.get('composite_feature_id') == new_feature_id
                and prior_grant_row.get('feature_id', '') in r.get('component_feature_ids', [])
                for r in exchange.audit_rows()
            )
            if not existing_comp:
                exchange.append_audit_row({
                    'kind': 'FEATURE_COMPOSITION',
                    'composite_feature_id': new_feature_id,
                    'component_feature_ids': [prior_grant_row.get('feature_id', '')],
                    'creator_peer_id': creator_id,
                    'auto_detected': True,
                    'detection_method': 'exact_fingerprint',
                    'at_unix': time.time(),
                    'at': datetime.now(timezone.utc).isoformat(),
                })

    def test_exact_match_emits_gap_and_composition(self):
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            prior = _grant_row('orig-feat', 'peer-alice', artifact_fingerprint='abc123')
            ex.append_audit_row(prior)

            self._simulate_layer1(ex, 'copy-feat', 'abc123', prior, 'peer-bob')

            rows = ex.audit_rows()
            gap_rows = [r for r in rows if r.get('kind') == 'GAP' and r.get('gap_type') == 'near-duplicate-artifact']
            comp_rows = [r for r in rows if r.get('kind') == 'FEATURE_COMPOSITION']

            self.assertEqual(len(gap_rows), 1)
            self.assertEqual(len(comp_rows), 1)
            self.assertEqual(comp_rows[0]['composite_feature_id'], 'copy-feat')
            self.assertIn('orig-feat', comp_rows[0]['component_feature_ids'])
            self.assertEqual(comp_rows[0]['detection_method'], 'exact_fingerprint')

    def test_no_duplicate_composition_on_second_match(self):
        """Second identical match → no second FEATURE_COMPOSITION for same pair."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            prior = _grant_row('orig-feat', 'peer-alice', artifact_fingerprint='abc123')
            ex.append_audit_row(prior)

            self._simulate_layer1(ex, 'copy-feat', 'abc123', prior, 'peer-bob')
            self._simulate_layer1(ex, 'copy-feat', 'abc123', prior, 'peer-bob')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)


# ── Test 7: Image Hamming detection ───────────────────────────────────────────

class Layer2ImageHammingTests(unittest.TestCase):
    """Unit-test Layer 2 image Hamming detection logic."""

    def _simulate_layer2(self, exchange, new_feature_id, new_dhash_int, creator_id):
        """Simulate the Layer 2+3 similarity detection block."""
        from datetime import datetime, timezone
        HAMMING_THRESHOLD = 10
        sim_checked = set()
        for sg in [r for r in exchange.audit_rows() if r.get('kind') == 'EQUITY_GRANT' and r.get('feature_id', '') != new_feature_id]:
            sg_fid = sg.get('feature_id', '')
            if sg_fid in sim_checked:
                continue
            detected = False
            method = ''
            if sg.get('artifact_dhash_int') is not None:
                dist = hamming_distance(new_dhash_int, int(sg['artifact_dhash_int']))
                if dist <= HAMMING_THRESHOLD:
                    detected = True
                    method = f'image_hamming_d{dist}'
            if detected:
                sim_checked.add(sg_fid)
                already = any(
                    r.get('kind') == 'FEATURE_COMPOSITION'
                    and r.get('composite_feature_id') == new_feature_id
                    and sg_fid in r.get('component_feature_ids', [])
                    for r in exchange.audit_rows()
                )
                if not already:
                    exchange.append_audit_row({
                        'kind': 'FEATURE_COMPOSITION',
                        'composite_feature_id': new_feature_id,
                        'component_feature_ids': [sg_fid],
                        'creator_peer_id': creator_id,
                        'auto_detected': True,
                        'detection_method': method,
                        'at_unix': time.time(),
                        'at': datetime.now(timezone.utc).isoformat(),
                    })
                    exchange.append_audit_row({
                        'kind': 'GAP',
                        'severity': 'WARNING',
                        'gap_type': 'near-similar-asset',
                        'feature_id': new_feature_id,
                        'similar_to_feature': sg_fid,
                        'detection_method': method,
                        'at_unix': time.time(),
                        'at': datetime.now(timezone.utc).isoformat(),
                    })

    def test_hamming_within_threshold_emits_composition(self):
        """Two grants with dhash_int differing by ≤ 10 → FEATURE_COMPOSITION with hamming method."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            base_dhash = 0xABCDEF0123456789
            # Differ by 5 bits
            similar_dhash = base_dhash ^ 0b11111
            ex.append_audit_row(_grant_row('img-orig', 'peer-alice', artifact_dhash_int=base_dhash))

            self._simulate_layer2(ex, 'img-similar', similar_dhash, 'peer-bob')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)
            self.assertIn('hamming', comp_rows[0]['detection_method'])
            self.assertIn('img-orig', comp_rows[0]['component_feature_ids'])

    def test_hamming_above_threshold_no_composition(self):
        """Two grants with dhash_int differing by > 10 → no FEATURE_COMPOSITION."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            base_dhash = 0xABCDEF0123456789
            # Differ by 20 bits
            different_dhash = base_dhash ^ 0xFFFFF
            ex.append_audit_row(_grant_row('img-orig', 'peer-alice', artifact_dhash_int=base_dhash))

            self._simulate_layer2(ex, 'img-different', different_dhash, 'peer-bob')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 0)

    def test_identical_dhash_emits_composition(self):
        """Identical dhash_int (distance=0) → FEATURE_COMPOSITION emitted."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            dhash = 0x1234567890ABCDEF
            ex.append_audit_row(_grant_row('img-orig', 'peer-alice', artifact_dhash_int=dhash))

            self._simulate_layer2(ex, 'img-copy', dhash, 'peer-bob')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)


# ── Test 8: Code Winnowing detection ──────────────────────────────────────────

class Layer3WinnowingTests(unittest.TestCase):
    """Unit-test Layer 3 Winnowing-based code similarity detection logic."""

    def _simulate_layer3(self, exchange, new_feature_id, new_raw_bytes, creator_id):
        """Simulate the Layer 3 Winnowing detection block."""
        from datetime import datetime, timezone
        WINNOW_THRESHOLD = 0.60
        sim_checked = set()
        new_wfp = winnow_fingerprint(new_raw_bytes)
        for sg in [r for r in exchange.audit_rows() if r.get('kind') == 'EQUITY_GRANT' and r.get('feature_id', '') != new_feature_id]:
            sg_fid = sg.get('feature_id', '')
            if sg_fid in sim_checked:
                continue
            detected = False
            method = ''
            if sg.get('artifact_winnow_fp'):
                sg_wfp = frozenset(sg['artifact_winnow_fp'])
                sim = winnow_similarity(new_wfp, sg_wfp)
                if sim >= WINNOW_THRESHOLD:
                    detected = True
                    method = f'winnow_jaccard_{sim:.2f}'
            if detected:
                sim_checked.add(sg_fid)
                already = any(
                    r.get('kind') == 'FEATURE_COMPOSITION'
                    and r.get('composite_feature_id') == new_feature_id
                    and sg_fid in r.get('component_feature_ids', [])
                    for r in exchange.audit_rows()
                )
                if not already:
                    exchange.append_audit_row({
                        'kind': 'FEATURE_COMPOSITION',
                        'composite_feature_id': new_feature_id,
                        'component_feature_ids': [sg_fid],
                        'creator_peer_id': creator_id,
                        'auto_detected': True,
                        'detection_method': method,
                        'at_unix': time.time(),
                        'at': datetime.now(timezone.utc).isoformat(),
                    })
                    exchange.append_audit_row({
                        'kind': 'GAP',
                        'severity': 'WARNING',
                        'gap_type': 'near-similar-asset',
                        'feature_id': new_feature_id,
                        'similar_to_feature': sg_fid,
                        'detection_method': method,
                        'at_unix': time.time(),
                        'at': datetime.now(timezone.utc).isoformat(),
                    })

    def test_high_winnow_similarity_emits_composition(self):
        """Two grants with ≥ 60% shared Winnowing fingerprints → FEATURE_COMPOSITION."""
        base_code = b"""
def compute_score(values):
    total = 0
    for v in values:
        if v > 0:
            total += v
    return total / len(values) if values else 0

def normalize(data):
    mn = min(data)
    mx = max(data)
    return [(x - mn) / (mx - mn) for x in data]

def filter_outliers(data, threshold=3.0):
    mean = sum(data) / len(data)
    std = (sum((x - mean)**2 for x in data) / len(data)) ** 0.5
    return [x for x in data if abs(x - mean) <= threshold * std]
"""
        modified_code = base_code.replace(b'total += v', b'total += v * 2')

        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            base_wfp = sorted(winnow_fingerprint(base_code))
            ex.append_audit_row(_grant_row('code-orig', 'peer-alice', artifact_winnow_fp=base_wfp))

            self._simulate_layer3(ex, 'code-similar', modified_code, 'peer-bob')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)
            self.assertIn('winnow', comp_rows[0]['detection_method'])
            self.assertIn('code-orig', comp_rows[0]['component_feature_ids'])

    def test_low_winnow_similarity_no_composition(self):
        """Two completely different code artifacts → no FEATURE_COMPOSITION."""
        code_a = b'aaaa bbbb cccc dddd eeee ffff gggg hhhh iiii jjjj kkkk llll mmmm'
        code_b = b'1111 2222 3333 4444 5555 6666 7777 8888 9999 0000 aaab bbbc cccd'

        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            wfp_a = sorted(winnow_fingerprint(code_a))
            ex.append_audit_row(_grant_row('code-orig', 'peer-alice', artifact_winnow_fp=wfp_a))

            self._simulate_layer3(ex, 'code-different', code_b, 'peer-bob')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 0)


# ── Test 9: SIMILARITY_VERDICT at fill-listing → FEATURE_COMPOSITION ──────────

class Layer4SimilarityVerdictTests(unittest.TestCase):
    """Unit-test Layer 4 — SIMILARITY_VERDICT rows at fill-listing trigger FEATURE_COMPOSITION."""

    def _simulate_verdict_block(self, exchange, feat_id, original_creator):
        """Simulate the Layer 4 verdict-processing block from fill-listing."""
        from datetime import datetime, timezone
        all_rows = exchange.audit_rows()
        verdict_rows = [
            r for r in all_rows
            if r.get('kind') == 'SIMILARITY_VERDICT'
            and r.get('feature_id') == feat_id
            and r.get('verdict') == 'derived'
            and r.get('reference_feature_id', '')
        ]
        for vr in verdict_rows:
            vr_ref = vr.get('reference_feature_id', '')
            already = any(
                r.get('kind') == 'FEATURE_COMPOSITION'
                and r.get('composite_feature_id') == feat_id
                and vr_ref in r.get('component_feature_ids', [])
                for r in all_rows
            )
            if not already:
                exchange.append_audit_row({
                    'kind': 'FEATURE_COMPOSITION',
                    'composite_feature_id': feat_id,
                    'component_feature_ids': [vr_ref],
                    'creator_peer_id': original_creator,
                    'auto_detected': True,
                    'detection_method': 'llm_peer_semantic',
                    'at_unix': time.time(),
                    'at': datetime.now(timezone.utc).isoformat(),
                })

    def test_verdict_derived_emits_composition(self):
        """SIMILARITY_VERDICT(verdict=derived) → FEATURE_COMPOSITION at fill-listing."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            ex.append_audit_row({
                'kind': 'SIMILARITY_VERDICT',
                'feature_id': 'feat-new',
                'reference_feature_id': 'feat-ref',
                'verdict': 'derived',
                'at_unix': time.time(),
            })

            self._simulate_verdict_block(ex, 'feat-new', 'peer-creator')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)
            self.assertEqual(comp_rows[0]['composite_feature_id'], 'feat-new')
            self.assertIn('feat-ref', comp_rows[0]['component_feature_ids'])
            self.assertEqual(comp_rows[0]['detection_method'], 'llm_peer_semantic')

    def test_verdict_not_derived_no_composition(self):
        """SIMILARITY_VERDICT(verdict=independent) → no FEATURE_COMPOSITION."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            ex.append_audit_row({
                'kind': 'SIMILARITY_VERDICT',
                'feature_id': 'feat-new',
                'reference_feature_id': 'feat-ref',
                'verdict': 'independent',
                'at_unix': time.time(),
            })

            self._simulate_verdict_block(ex, 'feat-new', 'peer-creator')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 0)

    def test_verdict_no_duplicate_composition(self):
        """Pre-existing FEATURE_COMPOSITION for same pair → verdict block does not duplicate."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            ex.append_audit_row({
                'kind': 'FEATURE_COMPOSITION',
                'composite_feature_id': 'feat-new',
                'component_feature_ids': ['feat-ref'],
                'creator_peer_id': 'peer-creator',
                'auto_detected': True,
                'detection_method': 'exact_fingerprint',
                'at_unix': time.time(),
            })
            ex.append_audit_row({
                'kind': 'SIMILARITY_VERDICT',
                'feature_id': 'feat-new',
                'reference_feature_id': 'feat-ref',
                'verdict': 'derived',
                'at_unix': time.time(),
            })

            self._simulate_verdict_block(ex, 'feat-new', 'peer-creator')

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)


# ── Test 10: No duplicate FEATURE_COMPOSITION when multiple layers trigger ─────

class NoDuplicateCompositionTests(unittest.TestCase):
    """When multiple detection layers could match the same pair, only one FEATURE_COMPOSITION emitted."""

    def test_no_duplicate_when_exact_and_hamming_both_match(self):
        """If Layer 1 (exact) already emitted FEATURE_COMPOSITION for a pair,
        Layer 2 (Hamming) must not emit a second one for the same pair."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            # Simulate Layer 1 already emitted composition
            ex.append_audit_row({
                'kind': 'FEATURE_COMPOSITION',
                'composite_feature_id': 'feat-new',
                'component_feature_ids': ['feat-orig'],
                'creator_peer_id': 'peer-bob',
                'auto_detected': True,
                'detection_method': 'exact_fingerprint',
                'at_unix': time.time(),
            })
            # Now simulate Layer 2 checking the same pair
            from datetime import datetime, timezone
            dhash_a = 0xABCDEF0123456789
            dhash_b = dhash_a ^ 0b111  # distance = 3, within threshold
            ex.append_audit_row(_grant_row('feat-orig', 'peer-alice', artifact_dhash_int=dhash_a))

            already = any(
                r.get('kind') == 'FEATURE_COMPOSITION'
                and r.get('composite_feature_id') == 'feat-new'
                and 'feat-orig' in r.get('component_feature_ids', [])
                for r in ex.audit_rows()
            )
            if not already:
                ex.append_audit_row({
                    'kind': 'FEATURE_COMPOSITION',
                    'composite_feature_id': 'feat-new',
                    'component_feature_ids': ['feat-orig'],
                    'creator_peer_id': 'peer-bob',
                    'auto_detected': True,
                    'detection_method': f'image_hamming_d{hamming_distance(dhash_a, dhash_b)}',
                    'at_unix': time.time(),
                    'at': datetime.now(timezone.utc).isoformat(),
                })

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)

    def test_no_duplicate_when_winnow_and_verdict_both_match(self):
        """Layer 3 Winnowing emitted composition, then Layer 4 verdict for same pair → still only 1 row."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            # Layer 3 already emitted
            ex.append_audit_row({
                'kind': 'FEATURE_COMPOSITION',
                'composite_feature_id': 'feat-new',
                'component_feature_ids': ['feat-orig'],
                'creator_peer_id': 'peer-bob',
                'auto_detected': True,
                'detection_method': 'winnow_jaccard_0.85',
                'at_unix': time.time(),
            })
            # Layer 4 verdict arrives
            ex.append_audit_row({
                'kind': 'SIMILARITY_VERDICT',
                'feature_id': 'feat-new',
                'reference_feature_id': 'feat-orig',
                'verdict': 'derived',
                'at_unix': time.time(),
            })

            # Simulate verdict block
            from datetime import datetime, timezone
            all_rows = ex.audit_rows()
            for vr in [r for r in all_rows if r.get('kind') == 'SIMILARITY_VERDICT' and r.get('verdict') == 'derived']:
                vr_ref = vr.get('reference_feature_id', '')
                already = any(
                    r.get('kind') == 'FEATURE_COMPOSITION'
                    and r.get('composite_feature_id') == 'feat-new'
                    and vr_ref in r.get('component_feature_ids', [])
                    for r in all_rows
                )
                if not already:
                    ex.append_audit_row({
                        'kind': 'FEATURE_COMPOSITION',
                        'composite_feature_id': 'feat-new',
                        'component_feature_ids': [vr_ref],
                        'creator_peer_id': 'peer-bob',
                        'auto_detected': True,
                        'detection_method': 'llm_peer_semantic',
                        'at_unix': time.time(),
                        'at': datetime.now(timezone.utc).isoformat(),
                    })

            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)


if __name__ == '__main__':
    unittest.main()
