"""Tests for peer_improvement.py — peer artifact pipeline."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch


def _write_bundle(qdir: Path, bundle_id: str, artifact: str = "urace runtime improvement", feature: str = "runtime-quality") -> Path:
    import hashlib, time
    payload = {
        "schema": "urace-peer-bundle-v1",
        "sender": "a" * 64,
        "recipient": "b" * 64,
        "feature": feature,
        "dependencies": [],
        "created_unix": time.time(),
        "artifact": artifact,
        "sha256": hashlib.sha256(artifact.encode()).hexdigest(),
        "distribution_terms": "research",
    }
    bundle = {"payload": payload, "signature": {"alg": "test"}}
    path = qdir / f"{bundle_id}.json"
    path.write_text(json.dumps(bundle))
    return path


class ListQuarantinedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.qdir = self.root / "quarantine"
        self.qdir.mkdir(parents=True)

    def _patch_qdir(self):
        from urace import peer_improvement as pi
        return patch.object(pi, "quarantine_dir", return_value=self.qdir)

    def test_empty_returns_empty(self):
        from urace import peer_improvement as pi
        with self._patch_qdir():
            result = pi.list_quarantined(self.root)
        self.assertEqual(result, [])

    def test_lists_bundles(self):
        _write_bundle(self.qdir, "bundle1")
        from urace import peer_improvement as pi
        with self._patch_qdir():
            result = pi.list_quarantined(self.root)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["bundle_id"], "bundle1")
        self.assertIn("feature", result[0])
        self.assertIn("artifact_bytes", result[0])

    def test_skips_symlinks(self):
        target = self.qdir / "real.json"
        target.write_text("{}")
        link = self.qdir / "link.json"
        link.symlink_to(target)
        from urace import peer_improvement as pi
        with self._patch_qdir():
            result = pi.list_quarantined(self.root)
        ids = [r["bundle_id"] for r in result]
        self.assertNotIn("link", ids)


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.qdir = self.root / "quarantine"
        self.qdir.mkdir(parents=True)

    def _patch_qdir(self):
        from urace import peer_improvement as pi
        return patch.object(pi, "quarantine_dir", return_value=self.qdir)

    def test_evaluate_clean_bundle(self):
        _write_bundle(self.qdir, "bnd1", artifact="urace runtime feature improvement candidate")
        from urace import peer_improvement as pi
        with self._patch_qdir():
            report = pi.evaluate(self.root, "bnd1")
        self.assertIn(report["verdict"], {"SAFE", "REVIEW"})
        self.assertEqual(report["bundle_id"], "bnd1")
        self.assertIn("urace", report["relevant_signals"])

    def test_evaluate_missing_bundle(self):
        from urace import peer_improvement as pi
        with self._patch_qdir():
            with self.assertRaises(FileNotFoundError):
                pi.evaluate(self.root, "nonexistent")

    def test_evaluate_tampered_sha256(self):
        import hashlib
        path = _write_bundle(self.qdir, "tampered")
        bundle = json.loads(path.read_text())
        bundle["payload"]["sha256"] = "0" * 64
        path.write_text(json.dumps(bundle))
        from urace import peer_improvement as pi
        with self._patch_qdir():
            report = pi.evaluate(self.root, "tampered")
        self.assertIn("sha256 mismatch", " ".join(report["issues"]))
        self.assertEqual(report["verdict"], "UNSAFE")

    def test_evaluate_empty_artifact(self):
        _write_bundle(self.qdir, "empty", artifact="")
        from urace import peer_improvement as pi
        with self._patch_qdir():
            report = pi.evaluate(self.root, "empty")
        self.assertIn("empty", " ".join(report["issues"]))

    def test_invalid_bundle_id_rejected(self):
        from urace import peer_improvement as pi
        with self._patch_qdir():
            with self.assertRaises(ValueError):
                pi.evaluate(self.root, "../etc/passwd")


class MarkQualifiedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _make_exchange_pair(self):
        from urace import peer_exchange as pe
        a = pe.Exchange(self.root / "a")
        b = pe.Exchange(self.root / "b")
        for e in (a, b):
            e.configure(enabled=True)
            e.feature("feat", [])
        aid = a.identity()["peer_id"]
        bid = b.identity()["peer_id"]
        a.peer(b.identity()["certificate"], post_quantum=b.identity()["post_quantum"])
        b.peer(a.identity()["certificate"], post_quantum=a.identity()["post_quantum"])
        a.rule(bid, "feat", "send", True)
        b.rule(aid, "feat", "receive", True)
        return a, b, aid, bid

    def test_mark_qualified_emits_audit_event(self):
        import hashlib, time
        from urace import peer_improvement as pi
        a, b, aid, bid = self._make_exchange_pair()
        artifact = "urace runtime improvement patch"
        result = a.prepare(bid, "feat", artifact, True)
        bundle = a.inspect(result["bundle_id"])["bundle"]
        recv = b.receive(bundle)
        bundle_id = recv["bundle_id"]

        mark_result = pi.mark_qualified(
            b, bundle_id,
            score_delta=7.5,
            affected_files={"urace/executor.py": "def run(): pass"},
            baseline_sha256="a" * 64,
        )
        self.assertEqual(mark_result["status"], "QUALIFIED")
        self.assertEqual(mark_result["bundle_id"], bundle_id)
        self.assertIn("canonical_fingerprint", mark_result)
        self.assertIn("outcome_fingerprint", mark_result)

        rows = b.audit_rows()
        kinds = [r["kind"] for r in rows]
        self.assertIn("APPLIED_AFTER_LOCAL_QUALIFICATION", kinds)
        qualified = next(r for r in rows if r["kind"] == "APPLIED_AFTER_LOCAL_QUALIFICATION")
        self.assertEqual(qualified["peer"], aid)
        self.assertEqual(qualified["feature"], "feat")
        self.assertEqual(qualified["score_delta"], 7.5)
        self.assertEqual(qualified["canonical_fingerprint"], mark_result["canonical_fingerprint"])

    def test_mark_qualified_unknown_bundle_raises(self):
        from urace import peer_improvement as pi
        a, b, aid, bid = self._make_exchange_pair()
        with self.assertRaises(ValueError):
            pi.mark_qualified(b, "a" * 64, 5.0, {}, "b" * 64)

    def test_mark_qualified_duplicate_raises(self):
        """A bundle may only be qualified once — second call must raise ValueError."""
        import hashlib, time
        from urace import peer_improvement as pi
        a, b, aid, bid = self._make_exchange_pair()
        artifact = "urace runtime improvement patch duplicate check"
        result = a.prepare(bid, "feat", artifact, True)
        bundle = a.inspect(result["bundle_id"])["bundle"]
        recv = b.receive(bundle)
        bundle_id = recv["bundle_id"]
        # First qualification succeeds
        pi.mark_qualified(b, bundle_id, score_delta=3.0, affected_files={}, baseline_sha256="a" * 64)
        # Second qualification on same bundle must be rejected
        with self.assertRaises(ValueError):
            pi.mark_qualified(b, bundle_id, score_delta=3.0, affected_files={}, baseline_sha256="a" * 64)


class PromoteRateLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.qdir = self.root / "quarantine"
        self.qdir.mkdir(parents=True)

    def _patch_qdir(self):
        from urace import peer_improvement as pi
        return patch.object(pi, "quarantine_dir", return_value=self.qdir)

    def test_promote_rate_limit_exceeded_raises(self):
        """Exceed 10 promotions per peer per 24h — 11th call must raise ValueError."""
        import time as _t
        from urace import peer_improvement as pi
        config = {}
        state = {}
        sender = "a" * 64
        # Pre-fill rollback_records with 10 recent promotions from same sender
        state["rollback_records"] = [
            {
                "kind": "peer-artifact-promoted",
                "peer_sender": sender,
                "promoted_at_unix": _t.time() - 60 * i,  # within last 24h
            }
            for i in range(10)
        ]
        # Write a valid bundle for the promote call
        _write_bundle(self.qdir, "rate-test-bundle", artifact="urace runtime improvement")
        # Patch sender in bundle to match our sender
        bundle_path = self.qdir / "rate-test-bundle.json"
        bundle = json.loads(bundle_path.read_text())
        bundle["payload"]["sender"] = sender
        bundle_path.write_text(json.dumps(bundle))
        with self._patch_qdir():
            with self.assertRaises(ValueError) as ctx:
                pi.promote(self.root, "rate-test-bundle", config, state)
        self.assertIn("daily promotion limit", str(ctx.exception))


class MultiPeerAmplificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _make_exchange(self, name="node"):
        from urace import peer_exchange as pe
        e = pe.Exchange(self.root / name)
        e.configure(enabled=True)
        e.feature("feat", [])
        return e

    def _inject_qualified_event(self, exchange, peer_id, canon_fp):
        with exchange.lock():
            exchange.event(
                "APPLIED_AFTER_LOCAL_QUALIFICATION",
                peer=peer_id,
                feature="feat",
                bundle="b" * 64,
                score_delta=5.0,
                canonical_fingerprint=canon_fp,
                outcome_fingerprint="o" * 64,
                affected_files=[],
            )

    def test_no_prior_qualifications_returns_zero(self):
        from urace import peer_improvement as pi
        e = self._make_exchange()
        boost = pi.multi_peer_amplification(e, "urace runtime patch")
        self.assertEqual(boost, 0)

    def test_one_peer_qualification_returns_fifteen(self):
        from urace import peer_improvement as pi
        e = self._make_exchange()
        artifact = "urace runtime patch"
        canon_fp = pi._artifact_canonical_fp(artifact)
        self._inject_qualified_event(e, "p" * 64, canon_fp)
        boost = pi.multi_peer_amplification(e, artifact)
        self.assertEqual(boost, 15)

    def test_same_peer_twice_does_not_double_count(self):
        from urace import peer_improvement as pi
        e = self._make_exchange()
        artifact = "urace runtime patch"
        canon_fp = pi._artifact_canonical_fp(artifact)
        self._inject_qualified_event(e, "p" * 64, canon_fp)
        self._inject_qualified_event(e, "p" * 64, canon_fp)
        boost = pi.multi_peer_amplification(e, artifact)
        self.assertEqual(boost, 15)

    def test_two_distinct_peers_boosts_higher(self):
        from urace import peer_improvement as pi
        e = self._make_exchange()
        artifact = "urace runtime patch"
        canon_fp = pi._artifact_canonical_fp(artifact)
        self._inject_qualified_event(e, "p1" + "a" * 62, canon_fp)
        self._inject_qualified_event(e, "p2" + "b" * 62, canon_fp)
        boost = pi.multi_peer_amplification(e, artifact)
        self.assertGreater(boost, 15)
        self.assertLessEqual(boost, 30)

    def test_different_artifact_no_boost(self):
        from urace import peer_improvement as pi
        e = self._make_exchange()
        artifact_a = "urace runtime patch A"
        artifact_b = "urace runtime patch B"
        canon_fp_a = pi._artifact_canonical_fp(artifact_a)
        self._inject_qualified_event(e, "p" * 64, canon_fp_a)
        boost = pi.multi_peer_amplification(e, artifact_b)
        self.assertEqual(boost, 0)

    def test_boost_capped_at_max(self):
        from urace import peer_improvement as pi
        e = self._make_exchange()
        artifact = "urace runtime patch"
        canon_fp = pi._artifact_canonical_fp(artifact)
        for i in range(20):
            self._inject_qualified_event(e, f"peer{i:04d}" + "x" * 58, canon_fp)
        boost = pi.multi_peer_amplification(e, artifact, max_boost=30)
        self.assertLessEqual(boost, 30)


class NetworkConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_network_disabled_returns_early(self):
        from urace import peer_exchange as pe, peer_improvement as pi
        e = pe.Exchange(self.root / "node")
        e.configure(enabled=True)
        result = pi.network_convergence(e, "a" * 64)
        self.assertEqual(result["status"], "NETWORK_DISABLED")
        self.assertIsNone(result["ratio"])

    def test_invalid_fingerprint_raises(self):
        from urace import peer_exchange as pe, peer_improvement as pi
        e = pe.Exchange(self.root / "node")
        e.configure(enabled=True)
        with self.assertRaises(ValueError):
            pi.network_convergence(e, "not-a-hex-fingerprint")

    def test_no_available_peers_returns_no_reachable(self):
        from urace import peer_exchange as pe, peer_improvement as pi
        e = pe.Exchange(self.root / "node")
        e.configure(enabled=True, network=True)
        result = pi.network_convergence(e, "a" * 64)
        self.assertEqual(result["status"], "NO_REACHABLE_PEERS")
        self.assertEqual(result["queried"], 0)

    def test_convergence_rpc_via_live_server(self):
        import threading
        from urace import peer_exchange as pe, peer_improvement as pi
        a = pe.Exchange(self.root / "a")
        b = pe.Exchange(self.root / "b")
        for e in (a, b):
            e.configure(enabled=True, network=True)
            e.feature("feat", [])
        aid = a.identity()["peer_id"]
        bid = b.identity()["peer_id"]
        a.peer(b.identity()["certificate"], post_quantum=b.identity()["post_quantum"])
        b.peer(a.identity()["certificate"], post_quantum=a.identity()["post_quantum"])
        a.rule(bid, "feat", "send", True)
        b.rule(aid, "feat", "receive", True)

        canon_fp = "c" * 64
        with b.lock():
            b.event("APPLIED_AFTER_LOCAL_QUALIFICATION", peer=aid, feature="feat",
                    bundle="d" * 64, score_delta=5.0, canonical_fingerprint=canon_fp,
                    outcome_fingerprint="e" * 64, affected_files=[])

        with pe.server(b) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                a.peer(b.identity()["certificate"], "https://127.0.0.1:" + str(server.server_port))
                from urace import peer_selection as ps
                # Manually set peer as AVAILABLE in cache
                import json as _json
                cache = ps.cache(a)
                cache["peers"][bid] = {"status": "AVAILABLE", "checked_unix": 1e10, "next_probe_unix": 1e10}
                pe.atomic(a.root / "selection.json", cache)

                result = pi.network_convergence(a, canon_fp)
                self.assertEqual(result["queried"], 1)
                self.assertEqual(result["confirmed"], 1)
                self.assertEqual(result["ratio"], 1.0)
                self.assertEqual(result["status"], "OK")
            finally:
                server.shutdown()
                thread.join(timeout=5)


class SanitizeArtifactTests(unittest.TestCase):
    def test_clean_text_passes(self):
        from urace.peer_improvement import sanitize_quarantine_artifact
        result = sanitize_quarantine_artifact("urace runtime feature improvement candidate")
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["issues"], [])

    def test_shell_metachar_injection_fails(self):
        from urace.peer_improvement import sanitize_quarantine_artifact
        result = sanitize_quarantine_artifact("do $(rm -rf /) please")
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("shell_metachar_injection", result["issues"])

    def test_elf_magic_bytes_fails(self):
        from urace.peer_improvement import sanitize_quarantine_artifact
        result = sanitize_quarantine_artifact("", artifact_bytes_raw=b'\x7fELF' + b'\x00' * 100)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("elf_binary", result["issues"])

    def test_pe_magic_bytes_fails(self):
        from urace.peer_improvement import sanitize_quarantine_artifact
        result = sanitize_quarantine_artifact("", artifact_bytes_raw=b'MZ' + b'\x00' * 100)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("pe_binary", result["issues"])

    def test_dangerous_import_subprocess_fails(self):
        from urace.peer_improvement import sanitize_quarantine_artifact
        result = sanitize_quarantine_artifact("import subprocess")
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("dangerous_import", result["issues"])

    def test_high_entropy_bytes_fails(self):
        import os
        from urace.peer_improvement import sanitize_quarantine_artifact
        artifact_bytes_raw = os.urandom(500)
        result = sanitize_quarantine_artifact("", artifact_bytes_raw=artifact_bytes_raw)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("high_entropy", result["issues"])

    def test_promote_refuses_unsafe_artifact(self):
        import hashlib, json, tempfile, time
        from pathlib import Path
        from unittest.mock import patch
        from urace import peer_improvement as pi

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        qdir = root / "quarantine"
        qdir.mkdir(parents=True)

        malicious = "urace runtime $(rm -rf /)"
        payload = {
            "schema": "urace-peer-bundle-v1",
            "sender": "a" * 64,
            "recipient": "b" * 64,
            "feature": "runtime-quality",
            "dependencies": [],
            "created_unix": time.time(),
            "artifact": malicious,
            "sha256": hashlib.sha256(malicious.encode()).hexdigest(),
            "distribution_terms": "research",
        }
        bundle = {"payload": payload, "signature": {"alg": "test"}}
        (qdir / "malicious-bundle.json").write_text(json.dumps(bundle))

        with patch.object(pi, "quarantine_dir", return_value=qdir):
            with self.assertRaises(ValueError) as ctx:
                pi.promote(root, "malicious-bundle", {}, {})
        self.assertIn("sanitization", str(ctx.exception).lower())

    def test_sanitization_recorded_in_audit(self):
        import hashlib, json, tempfile, time
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from urace import peer_improvement as pi

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        qdir = root / "quarantine"
        qdir.mkdir(parents=True)

        clean = "urace runtime improvement candidate"
        payload = {
            "schema": "urace-peer-bundle-v1",
            "sender": "a" * 64,
            "recipient": "b" * 64,
            "feature": "runtime-quality",
            "dependencies": [],
            "created_unix": time.time(),
            "artifact": clean,
            "sha256": hashlib.sha256(clean.encode()).hexdigest(),
            "distribution_terms": "research",
        }
        bundle = {"payload": payload, "signature": {"alg": "test"}}
        (qdir / "clean-bundle.json").write_text(json.dumps(bundle))

        fake_entry = {"id": "input-abc123"}
        state = {}

        with patch.object(pi, "quarantine_dir", return_value=qdir), \
             patch("urace._common.queue_input", return_value=fake_entry):
            result = pi.promote(root, "clean-bundle", {}, state)

        self.assertEqual(result["status"], "PROMOTED")
        audit_rows = state.get("rollback_records", [])
        self.assertEqual(len(audit_rows), 1)
        row = audit_rows[0]
        self.assertIn("sanitization", row)
        self.assertEqual(row["sanitization"]["verdict"], "PASS")


import sys
