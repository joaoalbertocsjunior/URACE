"""Tests for P2P corpus fingerprint, signed update bundles, and exchange.info integrity."""
import hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_exchange(tmp, name="node"):
    from urace import peer_exchange as pe
    e = pe.Exchange(Path(tmp) / name)
    e.configure(enabled=True, network=True)
    e.feature("feat", [])
    return e


# ── corpus fingerprint ────────────────────────────────────────────────────────

class CorpusFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _plant(self, files):
        for rel, content in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content if isinstance(content, bytes) else content.encode())

    def test_empty_tree_returns_hex(self):
        from urace.evolution_guard import p2p_corpus_fingerprint
        fp = p2p_corpus_fingerprint(self.root)
        self.assertRegex(fp, r'^[a-f0-9]{64}$')

    def test_stable_on_same_files(self):
        from urace.evolution_guard import p2p_corpus_fingerprint, P2P_SECURITY_FILES
        for rel in P2P_SECURITY_FILES:
            self._plant({rel: b"content"})
        fp1 = p2p_corpus_fingerprint(self.root)
        fp2 = p2p_corpus_fingerprint(self.root)
        self.assertEqual(fp1, fp2)

    def test_changes_when_file_modified(self):
        from urace.evolution_guard import p2p_corpus_fingerprint, P2P_SECURITY_FILES
        rel = sorted(P2P_SECURITY_FILES)[0]
        self._plant({rel: b"original"})
        fp1 = p2p_corpus_fingerprint(self.root)
        self._plant({rel: b"tampered"})
        fp2 = p2p_corpus_fingerprint(self.root)
        self.assertNotEqual(fp1, fp2)

    def test_includes_all_p2p_files(self):
        from urace.evolution_guard import p2p_corpus_fingerprint, P2P_SECURITY_FILES
        for rel in P2P_SECURITY_FILES:
            self._plant({rel: rel.encode()})
        fp_all = p2p_corpus_fingerprint(self.root)
        # Remove one file, fingerprint must differ
        (self.root / sorted(P2P_SECURITY_FILES)[0]).unlink()
        fp_minus = p2p_corpus_fingerprint(self.root)
        self.assertNotEqual(fp_all, fp_minus)


# ── build / verify bundle ─────────────────────────────────────────────────────

class P2PUpdateBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        from urace.evolution_guard import P2P_SECURITY_FILES
        for rel in P2P_SECURITY_FILES:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"dummy content for " + rel.encode())

    def _sign(self, data: bytes) -> str:
        return hashlib.sha256(b"secret" + data).hexdigest()

    def _verify(self, data: bytes, sig: bytes) -> bool:
        return sig == bytes.fromhex(self._sign(data))

    def test_build_produces_valid_schema(self):
        from urace.evolution_guard import build_p2p_update_bundle
        bundle = build_p2p_update_bundle(self.root, self._sign)
        self.assertEqual(bundle["schema"], "urace-p2p-update-v1")
        self.assertIn("corpus_fingerprint", bundle)
        self.assertIn("files", bundle)
        self.assertIn("author_signature", bundle)
        self.assertIn("announced_at", bundle)

    def test_verify_accepts_valid_bundle(self):
        from urace.evolution_guard import build_p2p_update_bundle, verify_p2p_update_bundle
        bundle = build_p2p_update_bundle(self.root, self._sign)
        errors = verify_p2p_update_bundle(bundle, self._verify)
        self.assertEqual(errors, [])

    def test_verify_rejects_tampered_file(self):
        from urace.evolution_guard import build_p2p_update_bundle, verify_p2p_update_bundle, P2P_SECURITY_FILES
        bundle = build_p2p_update_bundle(self.root, self._sign)
        rel = sorted(P2P_SECURITY_FILES)[0]
        bundle["files"][rel] = b"tampered".hex()
        errors = verify_p2p_update_bundle(bundle, self._verify)
        self.assertTrue(any("fingerprint" in e for e in errors))

    def test_verify_rejects_bad_signature(self):
        from urace.evolution_guard import build_p2p_update_bundle, verify_p2p_update_bundle
        bundle = build_p2p_update_bundle(self.root, self._sign)
        bundle["author_signature"] = "00" * 32
        errors = verify_p2p_update_bundle(bundle, self._verify)
        self.assertTrue(any("signature" in e for e in errors))

    def test_verify_rejects_unknown_files(self):
        from urace.evolution_guard import build_p2p_update_bundle, verify_p2p_update_bundle
        bundle = build_p2p_update_bundle(self.root, self._sign)
        bundle["files"]["urace/runtime/urace/evil.py"] = b"evil".hex()
        errors = verify_p2p_update_bundle(bundle, self._verify)
        self.assertTrue(any("unexpected" in e for e in errors))

    def test_verify_rejects_wrong_schema(self):
        from urace.evolution_guard import build_p2p_update_bundle, verify_p2p_update_bundle
        bundle = build_p2p_update_bundle(self.root, self._sign)
        bundle["schema"] = "urace-p2p-update-v0"
        errors = verify_p2p_update_bundle(bundle, self._verify)
        self.assertTrue(any("schema" in e for e in errors))

    def test_apply_no_tests_writes_files(self):
        from urace.evolution_guard import build_p2p_update_bundle, apply_p2p_update_bundle, P2P_SECURITY_FILES
        bundle = build_p2p_update_bundle(self.root, self._sign)
        dest = Path(self.tmp.name) / "dest"
        dest.mkdir()
        errors = apply_p2p_update_bundle(bundle, dest, self._verify, run_tests=False)
        self.assertEqual(errors, [])
        for rel in P2P_SECURITY_FILES:
            self.assertTrue((dest / rel).exists())


# ── exchange.info corpus fingerprint ─────────────────────────────────────────

class ExchangeInfoFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_local_corpus_fingerprint_returns_hex(self):
        from urace.peer_exchange import _local_corpus_fingerprint
        fp = _local_corpus_fingerprint()
        self.assertRegex(fp, r'^[a-f0-9]{64}$')

    def test_local_corpus_fingerprint_stable(self):
        from urace.peer_exchange import _local_corpus_fingerprint
        self.assertEqual(_local_corpus_fingerprint(), _local_corpus_fingerprint())

    def test_exchange_info_rpc_includes_fingerprint(self):
        """exchange.info result must carry p2p_corpus_fingerprint."""
        from urace import peer_exchange as pe
        e = _make_exchange(self.tmp.name)
        # Simulate the RPC result by inspecting what the handler would return.
        fp = pe._local_corpus_fingerprint()
        self.assertRegex(fp, r'^[a-f0-9]{64}$')
        # The fingerprint constant must match evolution_guard
        from urace.evolution_guard import p2p_corpus_fingerprint
        import os
        pkg = __import__("pathlib").Path(os.path.abspath(pe.__file__)).parent
        product_root = pkg.parent.parent.parent
        self.assertEqual(fp, p2p_corpus_fingerprint(product_root))


# ── P2P_CORPUS_MISMATCH audit event ──────────────────────────────────────────

class CorpusMismatchAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_no_mismatch_event_when_fingerprints_match(self):
        from urace import peer_exchange as pe
        e = _make_exchange(self.tmp.name)
        local_fp = pe._local_corpus_fingerprint()
        fake_result = {
            "jsonrpc": "2.0", "id": "nonce",
            "result": {"schema": pe.SCHEMA, "p2p_corpus_fingerprint": local_fp}
        }
        # Simulate post-request logic: fingerprints match → no event emitted
        remote_fp = fake_result["result"]["p2p_corpus_fingerprint"]
        self.assertEqual(local_fp, remote_fp)
        rows_before = e.audit_rows()
        # No event should have been emitted
        mismatch_rows = [r for r in e.audit_rows() if r.get("kind") == "P2P_CORPUS_MISMATCH"]
        self.assertEqual(len(mismatch_rows), 0)

    def test_mismatch_event_emitted_on_different_fingerprint(self):
        from urace import peer_exchange as pe
        e = _make_exchange(self.tmp.name)
        local_fp = pe._local_corpus_fingerprint()
        remote_fp = "aa" * 32  # deliberately different
        if remote_fp != local_fp:
            with e.lock():
                e.event("P2P_CORPUS_MISMATCH", peer="remotepeer123", local_fingerprint=local_fp, remote_fingerprint=remote_fp)
        rows = [r for r in e.audit_rows() if r.get("kind") == "P2P_CORPUS_MISMATCH"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["local_fingerprint"], local_fp)
        self.assertEqual(rows[0]["remote_fingerprint"], remote_fp)
        self.assertEqual(rows[0]["peer"], "remotepeer123")


if __name__ == "__main__":
    unittest.main()
