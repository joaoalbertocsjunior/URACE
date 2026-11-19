import json, io, zipfile, unittest

from urace.tokenomics import (
    artifact_fingerprint, _statistical_fingerprint, _xml_fingerprint, _pdf_text_fingerprint, _office_open_xml_fingerprint,
)
from urace import mime_policy as mp


class StatisticalFingerprintTests(unittest.TestCase):

    def _make_csv(self, header, rows):
        lines = [header] + [','.join(str(v) for v in r) for r in rows]
        return '\n'.join(lines).encode()

    def test_same_data_same_fingerprint(self):
        csv = self._make_csv('a,b,c', [[1,2,3],[4,5,6],[7,8,9]])
        fp1 = _statistical_fingerprint(csv, 'text/csv')
        fp2 = _statistical_fingerprint(csv, 'text/csv')
        self.assertEqual(fp1, fp2)

    def test_changed_first_8_rows_still_detected(self):
        # Original dataset
        rows = [[i, i*2, i*3] for i in range(1, 20)]
        original = self._make_csv('a,b,c', rows)
        # Adversarial: change first 8 rows but keep rest (same distribution)
        # With statistical fingerprint, this changes the distribution → different hash
        # (This tests that the fingerprint is NOT fooled by first-8-row swap)
        changed_rows = [[99, 99, 99]] * 8 + rows[8:]
        changed = self._make_csv('a,b,c', changed_rows)
        fp_orig = _statistical_fingerprint(original, 'text/csv')
        fp_changed = _statistical_fingerprint(changed, 'text/csv')
        self.assertNotEqual(fp_orig, fp_changed)

    def test_reordered_rows_same_fingerprint(self):
        rows = [[1,2,3],[4,5,6],[7,8,9]]
        original = self._make_csv('a,b,c', rows)
        reordered = self._make_csv('a,b,c', list(reversed(rows)))
        fp_orig = _statistical_fingerprint(original, 'text/csv')
        fp_reorder = _statistical_fingerprint(reordered, 'text/csv')
        self.assertEqual(fp_orig, fp_reorder)

    def test_json_array_fingerprint(self):
        data = json.dumps([{'x': i, 'y': i*2} for i in range(10)]).encode()
        fp = artifact_fingerprint('application/json', data)
        self.assertIsInstance(fp, str)
        self.assertEqual(len(fp), 64)

    def test_json_changed_first_8_still_detected(self):
        rows = [{'a': i, 'b': i*2} for i in range(1, 20)]
        original = json.dumps(rows).encode()
        changed = json.dumps([{'a': 99, 'b': 99}]*8 + rows[8:]).encode()
        fp_orig = artifact_fingerprint('application/json', original)
        fp_changed = artifact_fingerprint('application/json', changed)
        self.assertNotEqual(fp_orig, fp_changed)

    def test_ndjson_fingerprint(self):
        lines = '\n'.join(json.dumps({'k': i, 'v': str(i)}) for i in range(10))
        fp = artifact_fingerprint('application/x-ndjson', lines.encode())
        self.assertIsInstance(fp, str)


class XmlFingerprintTests(unittest.TestCase):

    def test_xml_same_structure_same_fingerprint(self):
        xml = b'<root><item id="1">hello</item><item id="2">world</item></root>'
        fp1 = _xml_fingerprint(xml)
        fp2 = _xml_fingerprint(xml)
        self.assertEqual(fp1, fp2)

    def test_xml_different_structure_different_fingerprint(self):
        xml1 = b'<root><item>hello</item></root>'
        xml2 = b'<root><entry>hello</entry></root>'
        fp1 = _xml_fingerprint(xml1)
        fp2 = _xml_fingerprint(xml2)
        self.assertNotEqual(fp1, fp2)

    def test_artifact_fingerprint_routes_xml(self):
        xml = b'<root><a>1</a></root>'
        fp = artifact_fingerprint('application/xml', xml)
        self.assertEqual(fp, _xml_fingerprint(xml))

    def test_artifact_fingerprint_routes_text_xml(self):
        xml = b'<data><row>x</row></data>'
        fp = artifact_fingerprint('text/xml', xml)
        self.assertEqual(fp, _xml_fingerprint(xml))


class PdfFingerprintTests(unittest.TestCase):

    def _make_pdf_with_text(self, text: str) -> bytes:
        # Minimal PDF with a text stream
        escaped = text.replace('(', r'\(').replace(')', r'\)')
        return f'%PDF-1.4\nBT /F1 12 Tf ({escaped}) Tj ET'.encode()

    def test_pdf_with_text_gives_fingerprint(self):
        pdf = self._make_pdf_with_text('hello world this is a test document')
        fp = _pdf_text_fingerprint(pdf)
        self.assertIsInstance(fp, str)
        self.assertEqual(len(fp), 64)

    def test_pdf_same_text_same_fingerprint(self):
        pdf = self._make_pdf_with_text('same content here repeated many times')
        self.assertEqual(_pdf_text_fingerprint(pdf), _pdf_text_fingerprint(pdf))

    def test_pdf_different_text_different_fingerprint(self):
        pdf1 = self._make_pdf_with_text('content alpha beta gamma delta epsilon zeta eta')
        pdf2 = self._make_pdf_with_text('completely different words here foo bar baz qux')
        self.assertNotEqual(_pdf_text_fingerprint(pdf1), _pdf_text_fingerprint(pdf2))

    def test_artifact_fingerprint_routes_pdf(self):
        pdf = self._make_pdf_with_text('test content for routing check')
        fp = artifact_fingerprint('application/pdf', pdf)
        self.assertEqual(fp, _pdf_text_fingerprint(pdf))


class OfficeFingerprintTests(unittest.TestCase):

    def _make_docx(self, text: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            xml = f'<w:document><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
            zf.writestr('word/document.xml', xml)
        return buf.getvalue()

    def _make_xlsx(self, values: list) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            cells = ''.join(f'<c><v>{v}</v></c>' for v in values)
            xml = f'<worksheet><sheetData><row>{cells}</row></sheetData></worksheet>'
            zf.writestr('xl/worksheets/sheet1.xml', xml)
        return buf.getvalue()

    def test_docx_fingerprint(self):
        docx = self._make_docx('The quick brown fox jumps over the lazy dog')
        fp = _office_open_xml_fingerprint(docx, 'docx')
        self.assertIsInstance(fp, str)
        self.assertEqual(len(fp), 64)

    def test_docx_same_content_same_fingerprint(self):
        text = 'identical text content in both documents for fingerprinting test'
        docx1 = self._make_docx(text)
        docx2 = self._make_docx(text)
        self.assertEqual(_office_open_xml_fingerprint(docx1, 'docx'),
                         _office_open_xml_fingerprint(docx2, 'docx'))

    def test_xlsx_fingerprint(self):
        xlsx = self._make_xlsx([1, 2, 3, 4, 5, 10, 20, 30])
        fp = _office_open_xml_fingerprint(xlsx, 'xlsx')
        self.assertIsInstance(fp, str)

    def test_artifact_fingerprint_routes_docx(self):
        docx = self._make_docx('some words here')
        ct = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        fp = artifact_fingerprint(ct, docx)
        self.assertEqual(fp, _office_open_xml_fingerprint(docx, 'docx'))


class MimePolicyTests(unittest.TestCase):

    # ── quality_gate_only (default) ───────────────────────────────────────────

    def test_default_allows_source_code(self):
        for ct in ('text/x-python', 'application/json', 'text/plain', 'text/csv', 'text/markdown'):
            allowed, reason = mp.is_allowed(ct, {})
            self.assertTrue(allowed, f'{ct}: {reason}')

    def test_default_allows_text_wildcard_subtypes(self):
        # text/* subtypes with MEDIUM ALE protection are accepted (e.g. text/x-go, text/x-rust)
        allowed, _ = mp.is_allowed('text/x-go', {})
        self.assertTrue(allowed)

    def test_default_blocks_html(self):
        # text/html has ALE protection but no reliable APS outcome delta
        allowed, reason = mp.is_allowed('text/html', {})
        self.assertFalse(allowed)
        self.assertIn('quality_gate_only', reason)

    def test_default_blocks_image(self):
        # Images cannot be objectively scored by APS
        allowed, reason = mp.is_allowed('image/jpeg', {})
        self.assertFalse(allowed)
        self.assertIn('quality_gate_only', reason)

    def test_default_blocks_pdf(self):
        allowed, reason = mp.is_allowed('application/pdf', {})
        self.assertFalse(allowed)
        self.assertIn('quality_gate_only', reason)

    def test_default_blocks_docx(self):
        ct = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        allowed, reason = mp.is_allowed(ct, {})
        self.assertFalse(allowed)

    def test_default_blocks_octet_stream(self):
        allowed, reason = mp.is_allowed('application/octet-stream', {})
        self.assertFalse(allowed)

    # ── hard_protected_only ───────────────────────────────────────────────────

    def test_hard_protected_allows_image(self):
        config = {'p2p': {'mime_policy': 'hard_protected_only'}}
        allowed, _ = mp.is_allowed('image/jpeg', config)
        self.assertTrue(allowed)

    def test_hard_protected_allows_csv(self):
        config = {'p2p': {'mime_policy': 'hard_protected_only'}}
        allowed, _ = mp.is_allowed('text/csv', config)
        self.assertTrue(allowed)

    def test_hard_protected_allows_json(self):
        config = {'p2p': {'mime_policy': 'hard_protected_only'}}
        allowed, _ = mp.is_allowed('application/json', config)
        self.assertTrue(allowed)

    def test_hard_protected_allows_pdf(self):
        config = {'p2p': {'mime_policy': 'hard_protected_only'}}
        allowed, _ = mp.is_allowed('application/pdf', config)
        self.assertTrue(allowed)

    def test_hard_protected_blocks_octet_stream(self):
        config = {'p2p': {'mime_policy': 'hard_protected_only'}}
        allowed, reason = mp.is_allowed('application/octet-stream', config)
        self.assertFalse(allowed)
        self.assertIn('weak', reason)

    def test_hard_protected_blocks_unknown(self):
        config = {'p2p': {'mime_policy': 'hard_protected_only'}}
        allowed, reason = mp.is_allowed('application/x-custom-binary', config)
        self.assertFalse(allowed)

    # ── all_allowed ───────────────────────────────────────────────────────────

    def test_all_allowed_permits_octet_stream(self):
        config = {'p2p': {'mime_policy': 'all_allowed'}}
        allowed, _ = mp.is_allowed('application/octet-stream', config)
        self.assertTrue(allowed)

    # ── custom ────────────────────────────────────────────────────────────────

    def test_custom_policy_explicit_allowlist(self):
        config = {'p2p': {'mime_policy': 'custom', 'allowed_asset_mime_types': ['application/octet-stream', 'image/*']}}
        self.assertTrue(mp.is_allowed('application/octet-stream', config)[0])
        self.assertTrue(mp.is_allowed('image/png', config)[0])
        self.assertFalse(mp.is_allowed('text/csv', config)[0])

    def test_custom_wildcard_match(self):
        config = {'p2p': {'mime_policy': 'custom', 'allowed_asset_mime_types': ['image/*']}}
        self.assertTrue(mp.is_allowed('image/jpeg', config)[0])
        self.assertTrue(mp.is_allowed('image/webp', config)[0])
        self.assertFalse(mp.is_allowed('application/json', config)[0])

    def test_custom_policy_empty_allowlist_blocks_all(self):
        config = {'p2p': {'mime_policy': 'custom', 'allowed_asset_mime_types': []}}
        allowed, _ = mp.is_allowed('image/jpeg', config)
        self.assertFalse(allowed)

    # ── protection level (ALE classification, independent of policy) ──────────

    def test_protection_level_image(self):
        self.assertEqual(mp.protection_level('image/png'), 'strong')

    def test_protection_level_csv(self):
        self.assertEqual(mp.protection_level('text/csv'), 'strong')

    def test_protection_level_octet_stream(self):
        self.assertEqual(mp.protection_level('application/octet-stream'), 'weak')

    def test_protection_level_unknown(self):
        self.assertEqual(mp.protection_level('application/x-mystery'), 'unknown')

    # ── is_network_allowed — network-enforced gate, ignores user config ───────

    def test_network_allowed_source_code(self):
        allowed, reason = mp.is_network_allowed('text/x-python')
        self.assertTrue(allowed)
        self.assertIn('quality_gate_only', reason)

    def test_network_allowed_structured_data(self):
        for ct in ('application/json', 'text/csv', 'text/plain'):
            allowed, _ = mp.is_network_allowed(ct)
            self.assertTrue(allowed, ct)

    def test_network_blocks_image_regardless_of_config(self):
        # Even if user set hard_protected_only, network gate rejects images
        allowed, reason = mp.is_network_allowed('image/jpeg')
        self.assertFalse(allowed)
        self.assertIn('quality_gate_only', reason)

    def test_network_blocks_pdf_regardless_of_config(self):
        allowed, _ = mp.is_network_allowed('application/pdf')
        self.assertFalse(allowed)

    def test_network_blocks_octet_stream(self):
        allowed, _ = mp.is_network_allowed('application/octet-stream')
        self.assertFalse(allowed)

    def test_network_policy_constant_is_quality_gate_only(self):
        self.assertEqual(mp.NETWORK_MIME_POLICY, 'quality_gate_only')


if __name__ == '__main__':
    unittest.main()
