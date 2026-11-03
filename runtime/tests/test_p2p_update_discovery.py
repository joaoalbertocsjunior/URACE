"""Tests for p2p_update_publish and p2p_update_check in peer_discovery."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_exchange(tmp, name="node"):
    from urace import peer_exchange as pe
    e = pe.Exchange(Path(tmp) / name)
    e.configure(enabled=True, network=True)
    e.feature("feat", [])
    return e


def _sign(data: bytes) -> str:
    return hashlib.sha256(b"secret" + data).hexdigest()


def _verify(data: bytes, sig: bytes) -> bool:
    return sig == bytes.fromhex(_sign(data))


class P2PUpdatePublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        from urace.evolution_guard import P2P_SECURITY_FILES
        for rel in P2P_SECURITY_FILES:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"dummy content for " + rel.encode())

    def _make_bundle(self):
        from urace.evolution_guard import build_p2p_update_bundle
        return build_p2p_update_bundle(self.root, _sign)

    def test_publish_returns_published_status(self):
        from urace import peer_discovery as pd
        bundle = self._make_bundle()
        priv = b"\x42" * 32
        with patch.object(pd._DHTClient, "bootstrap", return_value=2), \
             patch("urace.peer_discovery.bep44_put", return_value=3):
            result = pd.p2p_update_publish(bundle, priv)
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertIn("dht_key", result)
        self.assertEqual(len(result["dht_key"]), 64)   # 32 bytes hex
        self.assertEqual(result["announced_to"], 3)
        self.assertEqual(result["corpus_fingerprint"], bundle["corpus_fingerprint"])

    def test_publish_derives_pubkey_from_priv(self):
        from urace import peer_discovery as pd
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        bundle = self._make_bundle()
        priv = b"\x99" * 32
        expected_pub = Ed25519PrivateKey.from_private_bytes(priv).public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        ).hex()
        with patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch("urace.peer_discovery.bep44_put", return_value=0):
            result = pd.p2p_update_publish(bundle, priv)
        self.assertEqual(result["dht_key"], expected_pub)

    def test_publish_returns_error_on_exception(self):
        from urace import peer_discovery as pd
        bundle = self._make_bundle()
        priv = b"\x00" * 32
        with patch.object(pd._DHTClient, "__init__", side_effect=OSError("net")):
            result = pd.p2p_update_publish(bundle, priv)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("error", result)


class P2PUpdateCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        from urace.evolution_guard import P2P_SECURITY_FILES
        for rel in P2P_SECURITY_FILES:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"dummy content for " + rel.encode())

    def _fake_pub_key_hex(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        return Ed25519PrivateKey.from_private_bytes(b"\xab" * 32).public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        ).hex()

    def test_check_no_item_returns_not_available(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        pub_hex = self._fake_pub_key_hex()
        with patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch("urace.peer_discovery.bep44_get", return_value=None):
            result = pd.p2p_update_check(e, pub_hex, _verify)
        self.assertFalse(result["available"])
        self.assertIn("local_fingerprint", result)

    def test_check_same_fingerprint_no_event(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        pub_hex = self._fake_pub_key_hex()
        local_fp = pd._local_corpus_fingerprint_from_root()
        sig = _sign(local_fp.encode())
        fake_value = {
            b"corpus_fingerprint": local_fp.encode(),
            b"author_signature":   sig.encode(),
            b"announced_at":       1000,
        }
        with patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch("urace.peer_discovery.bep44_get", return_value=fake_value):
            result = pd.p2p_update_check(e, pub_hex, _verify)
        self.assertFalse(result["available"])
        rows = [r for r in e.audit_rows() if r.get("kind") == "P2P_UPDATE_AVAILABLE"]
        self.assertEqual(len(rows), 0)

    def test_check_different_fp_emits_event(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        pub_hex   = self._fake_pub_key_hex()
        remote_fp = "bb" * 32
        sig       = _sign(remote_fp.encode())
        fake_value = {
            b"corpus_fingerprint": remote_fp.encode(),
            b"author_signature":   sig.encode(),
            b"announced_at":       9999,
        }
        with patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch("urace.peer_discovery.bep44_get", return_value=fake_value):
            result = pd.p2p_update_check(e, pub_hex, _verify)
        self.assertTrue(result["available"])
        self.assertEqual(result["corpus_fingerprint"], remote_fp)
        self.assertEqual(result["announced_at"], 9999)
        self.assertEqual(result["dht_key"], pub_hex)
        rows = [r for r in e.audit_rows() if r.get("kind") == "P2P_UPDATE_AVAILABLE"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["remote_fingerprint"], remote_fp)

    def test_check_invalid_signature_no_event(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        pub_hex   = self._fake_pub_key_hex()
        remote_fp = "cc" * 32
        fake_value = {
            b"corpus_fingerprint": remote_fp.encode(),
            b"author_signature":   b"00" * 32,   # wrong sig
            b"announced_at":       1,
        }
        with patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch("urace.peer_discovery.bep44_get", return_value=fake_value):
            result = pd.p2p_update_check(e, pub_hex, _verify)
        self.assertFalse(result["available"])
        self.assertIn("error", result)
        rows = [r for r in e.audit_rows() if r.get("kind") == "P2P_UPDATE_AVAILABLE"]
        self.assertEqual(len(rows), 0)

    def test_check_error_returns_not_available(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        pub_hex = self._fake_pub_key_hex()
        with patch.object(pd._DHTClient, "__init__", side_effect=OSError("net")):
            result = pd.p2p_update_check(e, pub_hex, _verify)
        self.assertFalse(result["available"])

    def test_check_incorporates_existing_mismatch_count(self):
        """peer_count reflects prior P2P_CORPUS_MISMATCH events for the same fingerprint."""
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        remote_fp = "dd" * 32
        # Plant two prior mismatch events from distinct peers.
        with e.lock():
            e.event("P2P_CORPUS_MISMATCH", peer="peer-A", local_fingerprint="x"*64, remote_fingerprint=remote_fp)
            e.event("P2P_CORPUS_MISMATCH", peer="peer-B", local_fingerprint="x"*64, remote_fingerprint=remote_fp)
        pub_hex  = self._fake_pub_key_hex()
        sig      = _sign(remote_fp.encode())
        fake_val = {
            b"corpus_fingerprint": remote_fp.encode(),
            b"author_signature":   sig.encode(),
            b"announced_at":       1,
        }
        with patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch("urace.peer_discovery.bep44_get", return_value=fake_val):
            result = pd.p2p_update_check(e, pub_hex, _verify)
        self.assertTrue(result["available"])
        self.assertEqual(result["peer_count"], 2)


class ReleaseAuthorityKeyTests(unittest.TestCase):
    """Pinned release authority key in evolution_guard — cannot be swapped at call-site."""

    def test_verify_returns_false_when_key_not_configured(self):
        from urace import evolution_guard as eg
        with patch.object(eg, "RELEASE_AUTHORITY_KEYS", ()):
            self.assertFalse(eg.verify_release_signature(b"data", b"sig"))

    def test_verify_accepts_valid_signature(self):
        from urace import evolution_guard as eg
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        priv    = Ed25519PrivateKey.from_private_bytes(b"\x11" * 32)
        pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        data    = b"corpus-fp-abc123"
        sig     = priv.sign(data)
        with patch.object(eg, "RELEASE_AUTHORITY_KEYS", (pub_hex,)):
            self.assertTrue(eg.verify_release_signature(data, sig))

    def test_verify_rejects_wrong_signature(self):
        from urace import evolution_guard as eg
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        priv    = Ed25519PrivateKey.from_private_bytes(b"\x22" * 32)
        pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        with patch.object(eg, "RELEASE_AUTHORITY_KEYS", (pub_hex,)):
            self.assertFalse(eg.verify_release_signature(b"data", b"\x00" * 64))

    def test_verify_rejects_garbage_sig(self):
        from urace import evolution_guard as eg
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        priv    = Ed25519PrivateKey.from_private_bytes(b"\x33" * 32)
        pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        with patch.object(eg, "RELEASE_AUTHORITY_KEYS", (pub_hex,)):
            self.assertFalse(eg.verify_release_signature(b"data", b"tooshort"))

    def test_p2p_update_check_defaults_to_pinned_key(self):
        """When no verify_fn is passed, p2p_update_check uses the pinned release key."""
        import tempfile
        from urace import peer_discovery as pd, evolution_guard as eg
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        priv     = Ed25519PrivateKey.from_private_bytes(b"\x44" * 32)
        pub_hex  = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        priv_raw = b"\x44" * 32

        remote_fp = "ee" * 32
        sig       = priv.sign(remote_fp.encode()).hex()
        fake_val  = {
            b"corpus_fingerprint": remote_fp.encode(),
            b"author_signature":   sig.encode(),
            b"announced_at":       1,
        }

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        e = _make_exchange(tmp.name)

        with patch.object(eg, "RELEASE_AUTHORITY_KEYS", (pub_hex,)), \
             patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch("urace.peer_discovery.bep44_get", return_value=fake_val):
            # No author_verify_fn passed — should pick up pinned key automatically.
            result = pd.p2p_update_check(e, pub_hex)

        self.assertTrue(result["available"])
        rows = [r for r in e.audit_rows() if r.get("kind") == "P2P_UPDATE_AVAILABLE"]
        self.assertEqual(len(rows), 1)

    def test_p2p_update_check_rejects_when_key_not_configured(self):
        """If RELEASE_AUTHORITY_PUB_KEY_HEX is empty, update check fails gracefully."""
        import tempfile
        from urace import peer_discovery as pd, evolution_guard as eg

        remote_fp = "ff" * 32
        fake_sig  = "00" * 64
        fake_val  = {
            b"corpus_fingerprint": remote_fp.encode(),
            b"author_signature":   fake_sig.encode(),
            b"announced_at":       1,
        }
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        e = _make_exchange(tmp.name)

        with patch.object(eg, "RELEASE_AUTHORITY_KEYS", ()), \
             patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch("urace.peer_discovery.bep44_get", return_value=fake_val):
            result = pd.p2p_update_check(e, "aa" * 32)

        self.assertFalse(result["available"])
        self.assertIn("error", result)
        rows = [r for r in e.audit_rows() if r.get("kind") == "P2P_UPDATE_AVAILABLE"]
        self.assertEqual(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
