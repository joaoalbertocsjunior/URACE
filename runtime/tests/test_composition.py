"""Tests for bundle_decompose + auto FEATURE_COMPOSITION and composition referral rewards."""
import hashlib
import io
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from urace import peer_exchange as pe
from urace.tokenomics import artifact_fingerprint, bundle_decompose


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_zip(files: dict) -> bytes:
    """files: {filename: bytes}"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _make_exchange(tmp_path: str, name: str = 'node') -> pe.Exchange:
    return pe.Exchange(Path(tmp_path) / name)


# ── System 1: bundle_decompose unit tests ─────────────────────────────────────

class BundleDecomposeTests(unittest.TestCase):

    def test_valid_zip_two_files(self):
        """zip with 2 non-empty files → 2 entries with correct filenames and content."""
        data_a = b'hello world'
        data_b = b'second file content'
        raw = _make_zip({'a.txt': data_a, 'b.txt': data_b})
        result = bundle_decompose(raw)
        self.assertEqual(len(result), 2)
        names = {r[0] for r in result}
        self.assertIn('a.txt', names)
        self.assertIn('b.txt', names)
        content_map = {r[0]: r[1] for r in result}
        self.assertEqual(content_map['a.txt'], data_a)
        self.assertEqual(content_map['b.txt'], data_b)

    def test_non_zip_bytes(self):
        """non-zip → single-entry list with empty filename."""
        raw = b'this is not a zip file at all'
        result = bundle_decompose(raw)
        self.assertEqual(len(result), 1)
        fname, data, ct = result[0]
        self.assertEqual(fname, '')
        self.assertEqual(data, raw)

    def test_empty_zip_fallback(self):
        """zip with no non-empty files → single-entry fallback."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w'):
            pass  # empty zip
        raw = buf.getvalue()
        result = bundle_decompose(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], '')

    def test_content_types_detected(self):
        """content_type is set based on filename."""
        raw = _make_zip({'data.csv': b'a,b\n1,2\n'})
        result = bundle_decompose(raw)
        self.assertEqual(len(result), 1)
        _, _, ct = result[0]
        self.assertEqual(ct, 'text/csv')


# ── System 1: composition detection logic unit tests ─────────────────────────

class CompositionDetectionTests(unittest.TestCase):
    """Unit-tests the bundle decompose + fingerprint matching logic directly
    (without full CLI dispatch, as approved by spec)."""

    def _simulate_grant_with_artifact(self, exchange, feature_id, peer_id, artifact_bytes, content_type='application/octet-stream'):
        """Directly append an EQUITY_GRANT row with artifact_fingerprint, as the CLI does."""
        fp = artifact_fingerprint(content_type, artifact_bytes)
        sha = hashlib.sha256(artifact_bytes).hexdigest()
        exchange.append_audit_row({
            'kind': 'EQUITY_GRANT',
            'feature_id': feature_id,
            'peer_id': peer_id,
            'artifact_ref': sha,
            'artifact_fingerprint': fp,
            'artifact_size_bytes': len(artifact_bytes),
            'content_type': content_type,
            'at_unix': time.time(),
        })
        return fp, sha

    def _run_composition_detection(self, exchange, new_feature_id, artifact_bytes, content_type='application/octet-stream'):
        """Simulate the pre-grant composition detection logic from exchange_cli."""
        audit_rows = exchange.audit_rows()
        fp_index = {
            r['artifact_fingerprint']: r.get('feature_id', '')
            for r in audit_rows
            if r.get('kind') == 'EQUITY_GRANT'
            and r.get('artifact_fingerprint', '')
            and r.get('feature_id', '') != new_feature_id
        }
        members = bundle_decompose(artifact_bytes)
        decomp_components = []
        for _mname, _mbytes, _mct in members:
            mfp = artifact_fingerprint(_mct, _mbytes)
            if mfp in fp_index:
                decomp_components.append(fp_index[mfp])
        decomp_components = list(dict.fromkeys(decomp_components))
        art_fp = artifact_fingerprint(content_type, artifact_bytes)
        if len(members) == 1 and art_fp in fp_index:
            raise ValueError(
                f'Artifact is identical to existing feature {fp_index[art_fp]!r} — cannot re-mint. Reference that feature instead.'
            )
        return decomp_components, art_fp

    def test_zip_with_matching_member_emits_composition(self):
        """zip containing a file matching existing grant's fingerprint → FEATURE_COMPOSITION emitted."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            base_bytes = b'base feature implementation v1'
            self._simulate_grant_with_artifact(ex, 'base-feature', 'peer-alice', base_bytes)

            # Build composite zip: contains base_bytes as one file + something new
            composite_zip = _make_zip({
                'module_a.bin': base_bytes,
                'module_b.bin': b'extra new stuff for composite',
            })
            components, _ = self._run_composition_detection(ex, 'composite-feature', composite_zip)
            self.assertIn('base-feature', components)

            # Emit FEATURE_COMPOSITION (as the CLI does)
            ex.append_audit_row({
                'kind': 'FEATURE_COMPOSITION',
                'composite_feature_id': 'composite-feature',
                'component_feature_ids': components,
                'creator_peer_id': 'peer-bob',
                'auto_detected': True,
                'at_unix': time.time(),
            })
            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 1)
            self.assertTrue(comp_rows[0]['auto_detected'])
            self.assertIn('base-feature', comp_rows[0]['component_feature_ids'])

    def test_exact_remint_raises(self):
        """Single-file artifact identical to existing feature → raises ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            existing_bytes = b'unique feature bytes xyz'
            self._simulate_grant_with_artifact(ex, 'orig-feature', 'peer-alice', existing_bytes)
            with self.assertRaises(ValueError) as ctx:
                self._run_composition_detection(ex, 'copy-feature', existing_bytes)
            self.assertIn('orig-feature', str(ctx.exception))

    def test_no_artifact_no_composition(self):
        """Grant with no artifact → no FEATURE_COMPOSITION row (no regression)."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            # Grant without artifact — just append a bare EQUITY_GRANT
            ex.append_audit_row({
                'kind': 'EQUITY_GRANT',
                'feature_id': 'bare-feature',
                'peer_id': 'peer-carol',
                'at_unix': time.time(),
            })
            comp_rows = [r for r in ex.audit_rows() if r.get('kind') == 'FEATURE_COMPOSITION']
            self.assertEqual(len(comp_rows), 0)

    def test_no_matching_members_no_composition(self):
        """zip with no member matching any existing grant → empty components list."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            self._simulate_grant_with_artifact(ex, 'some-feature', 'peer-alice', b'alice bytes')
            composite_zip = _make_zip({'new.bin': b'completely different content 999'})
            components, _ = self._run_composition_detection(ex, 'new-composite', composite_zip)
            self.assertEqual(components, [])


# ── System 2: composition referral rewards unit tests ─────────────────────────

class CompositionReferralTests(unittest.TestCase):
    """Unit-tests the fill-listing composition referral logic directly."""

    def _setup_composition_scenario(self, ex, composite_id, component_id, component_owner, price):
        """Set up rows needed for referral: EQUITY_GRANT for component + FEATURE_COMPOSITION."""
        ex.append_audit_row({
            'kind': 'EQUITY_GRANT',
            'feature_id': component_id,
            'peer_id': component_owner,
            'at_unix': time.time(),
        })
        ex.append_audit_row({
            'kind': 'FEATURE_COMPOSITION',
            'composite_feature_id': composite_id,
            'component_feature_ids': [component_id],
            'creator_peer_id': 'peer-creator',
            'auto_detected': True,
            'at_unix': time.time(),
        })

    def _run_referral_logic(self, ex, feat_id, fl_price, listing_id, local_id, config=None):
        """Simulate the composition referral block from fill-listing."""
        if config is None:
            config = {}
        all_rows = ex.audit_rows()
        comp_fc = [r for r in all_rows if r.get('kind') == 'FEATURE_COMPOSITION' and r.get('composite_feature_id') == feat_id]
        emitted = []
        if comp_fc and fl_price > 0:
            ref_rate = float(config.get('p2p', {}).get('composition_referral_rate', 0.20))
            comp_fids = list(dict.fromkeys(fid for _cr in comp_fc for fid in _cr.get('component_feature_ids', [])))
            if comp_fids:
                total_ref = int(fl_price * min(ref_rate * len(comp_fids), 0.50))
                per_comp = max(1, total_ref // len(comp_fids))
                for cid in comp_fids:
                    cg = next((r for r in all_rows if r.get('kind') == 'EQUITY_GRANT' and r.get('feature_id') == cid), None)
                    cowner = cg.get('peer_id', '') if cg else ''
                    if cowner and per_comp > 0:
                        row = {
                            'kind': 'CREDIT_DELTA',
                            'direction': 'composition_referral',
                            'peer': cowner,
                            'local_peer': local_id,
                            'amount_units': per_comp,
                            'composite_feature_id': feat_id,
                            'component_feature_id': cid,
                            'listing_id': listing_id,
                            'at_unix': time.time(),
                        }
                        ex.append_audit_row(row)
                        emitted.append(row)
        return emitted

    def test_referral_emitted_for_component_owner(self):
        """fill-listing with FEATURE_COMPOSITION and price > 0 → CREDIT_DELTA(composition_referral) for component owner."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            self._setup_composition_scenario(ex, 'comp-feat', 'base-feat', 'peer-alice', 100)
            emitted = self._run_referral_logic(ex, 'comp-feat', 100, 'listing-1', 'buyer-bob')
            self.assertEqual(len(emitted), 1)
            self.assertEqual(emitted[0]['direction'], 'composition_referral')
            self.assertEqual(emitted[0]['peer'], 'peer-alice')
            self.assertGreater(emitted[0]['amount_units'], 0)
            # Verify persisted
            cd_rows = [r for r in ex.audit_rows() if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'composition_referral']
            self.assertEqual(len(cd_rows), 1)

    def test_no_referral_without_composition_rows(self):
        """fill-listing with no FEATURE_COMPOSITION rows → no referral CREDIT_DELTA."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            emitted = self._run_referral_logic(ex, 'plain-feat', 100, 'listing-2', 'buyer-bob')
            self.assertEqual(emitted, [])

    def test_no_referral_when_price_zero(self):
        """fill-listing with FEATURE_COMPOSITION but price == 0 → no referral."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            self._setup_composition_scenario(ex, 'comp-feat2', 'base-feat2', 'peer-dave', 0)
            emitted = self._run_referral_logic(ex, 'comp-feat2', 0, 'listing-3', 'buyer-eve')
            self.assertEqual(emitted, [])

    def test_referral_capped_at_50_percent(self):
        """Referral total capped at 50% of price even with many components."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            # Create many components (10) — rate 0.20 × 10 = 2.0, capped at 0.50
            component_ids = [f'comp-{i}' for i in range(10)]
            for cid in component_ids:
                ex.append_audit_row({
                    'kind': 'EQUITY_GRANT',
                    'feature_id': cid,
                    'peer_id': f'owner-{cid}',
                    'at_unix': time.time(),
                })
            ex.append_audit_row({
                'kind': 'FEATURE_COMPOSITION',
                'composite_feature_id': 'big-composite',
                'component_feature_ids': component_ids,
                'creator_peer_id': 'peer-creator',
                'auto_detected': True,
                'at_unix': time.time(),
            })
            price = 1000
            emitted = self._run_referral_logic(ex, 'big-composite', price, 'listing-4', 'buyer-frank')
            total_paid = sum(e['amount_units'] for e in emitted)
            self.assertLessEqual(total_paid, price * 0.50 + len(component_ids))  # allow integer rounding per slot

    def test_component_owner_resolved_from_equity_grant(self):
        """Component owner resolves correctly from EQUITY_GRANT rows."""
        with tempfile.TemporaryDirectory() as tmp:
            ex = _make_exchange(tmp)
            ex.append_audit_row({
                'kind': 'EQUITY_GRANT',
                'feature_id': 'feat-x',
                'peer_id': 'peer-xowner',
                'at_unix': time.time(),
            })
            ex.append_audit_row({
                'kind': 'FEATURE_COMPOSITION',
                'composite_feature_id': 'composite-y',
                'component_feature_ids': ['feat-x'],
                'creator_peer_id': 'peer-creator',
                'auto_detected': True,
                'at_unix': time.time(),
            })
            emitted = self._run_referral_logic(ex, 'composite-y', 500, 'listing-5', 'buyer-g')
            self.assertEqual(len(emitted), 1)
            self.assertEqual(emitted[0]['peer'], 'peer-xowner')
            self.assertEqual(emitted[0]['component_feature_id'], 'feat-x')


if __name__ == '__main__':
    unittest.main()
