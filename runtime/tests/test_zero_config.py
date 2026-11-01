"""Tests for zero-config P2P: BEP 44, TOFU auto-pin, anonymization, auto-pin integration."""
from __future__ import annotations

import hashlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_exchange(tmp, name="node"):
    from urace import peer_exchange as pe
    e = pe.Exchange(Path(tmp) / name)
    e.configure(enabled=True, network=True)
    e.feature("feat", [])
    return e


# ── BEP 44 Tests ──────────────────────────────────────────────────────────────

class BEP44Tests(unittest.TestCase):

    def _gen_keypair(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        priv = Ed25519PrivateKey.generate()
        priv_bytes = priv.private_bytes_raw()
        pub_bytes = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return priv_bytes, pub_bytes

    def test_bep44_sign_verify_roundtrip(self):
        from urace.peer_discovery import _bep44_sign, _bep44_verify, _be
        priv, pub = self._gen_keypair()
        value = _be({b"k": b"v"})
        sig = _bep44_sign(priv, 42, value)
        self.assertEqual(len(sig), 64)
        self.assertTrue(_bep44_verify(pub, 42, value, sig))

    def test_bep44_sign_bad_sig_fails(self):
        from urace.peer_discovery import _bep44_sign, _bep44_verify, _be
        priv, pub = self._gen_keypair()
        value = _be({b"k": b"v"})
        sig = _bep44_sign(priv, 1, value)
        bad_sig = bytes([sig[0] ^ 0xFF]) + sig[1:]
        self.assertFalse(_bep44_verify(pub, 1, value, bad_sig))

    def test_dht_cert_publish_returns_dht_key(self):
        from urace.peer_discovery import dht_cert_publish
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            with patch("urace.peer_discovery._DHTClient") as MockClient:
                inst = MockClient.return_value
                inst.bootstrap.return_value = 1
                inst._tokens = {}
                inst.get_peers.return_value = []
                result = dht_cert_publish(e, 8443, ephemeral=False)
            self.assertEqual(result["status"], "PUBLISHED")
            self.assertIn("dht_key", result)
            self.assertEqual(len(bytes.fromhex(result["dht_key"])), 32)
            self.assertFalse(result["ephemeral"])
            self.assertEqual(result["port"], 8443)

    def test_dht_cert_lookup_returns_none_on_miss(self):
        from urace.peer_discovery import dht_cert_lookup
        priv_bytes = os.urandom(32)
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        pub = Ed25519PrivateKey.from_private_bytes(priv_bytes).public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        with patch("urace.peer_discovery._DHTClient") as MockClient:
            inst = MockClient.return_value
            inst.bootstrap.return_value = 0
            inst._tokens = {}
            inst._recv.return_value = (None, None)
            inst._send.return_value = None
            with patch("urace.peer_discovery.bep44_get", return_value=None):
                result = dht_cert_lookup(pub.hex(), timeout=0.1)
        self.assertIsNone(result)

    def test_derive_announce_key_stable(self):
        from urace.peer_discovery import _derive_announce_key
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            priv1, pub1 = _derive_announce_key(e)
            priv2, pub2 = _derive_announce_key(e)
            self.assertEqual(priv1, priv2)
            self.assertEqual(pub1, pub2)

    def test_derive_announce_key_differs_between_exchanges(self):
        from urace.peer_discovery import _derive_announce_key
        with tempfile.TemporaryDirectory() as tmp1:
            with tempfile.TemporaryDirectory() as tmp2:
                e1 = _make_exchange(tmp1, "nodeA")
                e2 = _make_exchange(tmp2, "nodeB")
                _, pub1 = _derive_announce_key(e1)
                _, pub2 = _derive_announce_key(e2)
                self.assertNotEqual(pub1, pub2)

    def test_derive_announce_key_differs_from_identity(self):
        from urace.peer_discovery import _derive_announce_key
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            _, pub_dht = _derive_announce_key(e)
            # Identity ED25519 pub key
            identity_pub_raw = e.crypto_identity().ed.public_key().public_bytes_raw()
            self.assertNotEqual(pub_dht, identity_pub_raw)


# ── TOFU Tests ────────────────────────────────────────────────────────────────

class TOFUTests(unittest.TestCase):

    def _make_pair(self, tmp):
        """Make two exchanges, pin them to each other."""
        from urace import peer_exchange as pe
        a = pe.Exchange(Path(tmp) / "alpha")
        a.configure(enabled=True, network=True)
        a.feature("feat", [])
        b = pe.Exchange(Path(tmp) / "beta")
        b.configure(enabled=True, network=True)
        b.feature("feat", [])
        return a, b

    def test_tofu_new_peer_returns_new_peer(self):
        from urace.peer_exchange import tofu_check
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self._make_pair(tmp)
            b_cert = b.identity()["certificate"]
            b_id   = b.identity()["peer_id"]
            result = tofu_check(a, b_id, b_cert)
            self.assertEqual(result, "NEW_PEER")

    def test_tofu_same_cert_returns_already_pinned(self):
        from urace.peer_exchange import tofu_check
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self._make_pair(tmp)
            b_cert = b.identity()["certificate"]
            b_id   = b.identity()["peer_id"]
            a.peer(b_cert, endpoint="https://localhost:9000")
            result = tofu_check(a, b_id, b_cert)
            self.assertEqual(result, "ALREADY_PINNED")

    def test_tofu_cert_change_raises(self):
        from urace.peer_exchange import tofu_check
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self._make_pair(tmp)
            b_cert = b.identity()["certificate"]
            b_id   = b.identity()["peer_id"]
            a.peer(b_cert, endpoint="https://localhost:9000")
            # Generate a fresh cert with the SAME peer_id key (simulated mismatch)
            c = _make_exchange(tmp, "charlie")
            fake_cert = c.identity()["certificate"]
            with self.assertRaises(ValueError) as ctx:
                tofu_check(a, b_id, fake_cert)
            self.assertIn("TOFU violation", str(ctx.exception))

    def test_auto_pin_pins_new_peer_and_applies_rules(self):
        from urace.peer_exchange import auto_pin
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self._make_pair(tmp)
            b_cert = b.identity()["certificate"]
            result = auto_pin(
                a, b_cert, "https://localhost:9001",
                default_rules={"feat": {"send": True, "receive": True}},
            )
            self.assertEqual(result["status"], "PINNED")
            p = a.load()
            peer_id = result["peer_id"]
            self.assertIn(peer_id, p["peers"])
            self.assertTrue(p["rules"].get(f"{peer_id}:send:feat"))
            self.assertTrue(p["rules"].get(f"{peer_id}:receive:feat"))

    def test_auto_pin_idempotent_same_cert(self):
        from urace.peer_exchange import auto_pin
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self._make_pair(tmp)
            b_cert = b.identity()["certificate"]
            r1 = auto_pin(a, b_cert, "https://localhost:9001")
            self.assertEqual(r1["status"], "PINNED")
            r2 = auto_pin(a, b_cert, "https://localhost:9001")
            self.assertEqual(r2["status"], "ALREADY_PINNED")

    def test_auto_pin_applies_default_rules_from_config(self):
        from urace.peer_exchange import auto_pin
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self._make_pair(tmp)
            a.configure(default_feature_rules={"feat": {"send": False, "receive": True}})
            b_cert = b.identity()["certificate"]
            result = auto_pin(a, b_cert, "https://localhost:9001")
            p = a.load()
            peer_id = result["peer_id"]
            self.assertFalse(p["rules"].get(f"{peer_id}:send:feat", True))
            self.assertTrue(p["rules"].get(f"{peer_id}:receive:feat"))


# ── Anonymization Tests ───────────────────────────────────────────────────────

class AnonymizationTests(unittest.TestCase):

    def test_relay_only_skips_dht_announce(self):
        from urace.peer_discovery import DiscoverySession
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            e.configure(relay_only=True)
            session = DiscoverySession(e, 8443, lan=False, wan=True)
            with patch("urace.peer_discovery.dht_announce") as mock_dht, \
                 patch("urace.peer_discovery.dht_cert_publish") as mock_publish:
                mock_publish.return_value = {"status": "PUBLISHED", "dht_key": "aa" * 32}
                session.start()
                session.stop()
            mock_dht.assert_not_called()

    def test_ephemeral_announce_uses_different_key_each_call(self):
        from urace.peer_discovery import dht_cert_publish
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            with patch("urace.peer_discovery._DHTClient") as MockClient:
                inst = MockClient.return_value
                inst.bootstrap.return_value = 0
                inst._tokens = {}
                inst.get_peers.return_value = []
                r1 = dht_cert_publish(e, 8443, ephemeral=True)
                r2 = dht_cert_publish(e, 8443, ephemeral=True)
            self.assertEqual(r1["status"], "PUBLISHED")
            self.assertEqual(r2["status"], "PUBLISHED")
            self.assertNotEqual(r1["dht_key"], r2["dht_key"])

    def test_stable_announce_key_same_across_calls(self):
        from urace.peer_discovery import dht_cert_publish
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            with patch("urace.peer_discovery._DHTClient") as MockClient:
                inst = MockClient.return_value
                inst.bootstrap.return_value = 0
                inst._tokens = {}
                inst.get_peers.return_value = []
                r1 = dht_cert_publish(e, 8443, ephemeral=False)
                r2 = dht_cert_publish(e, 8443, ephemeral=False)
            self.assertEqual(r1["dht_key"], r2["dht_key"])

    def test_dht_node_id_differs_from_peer_id(self):
        from urace.peer_discovery import _dht_node_id
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            peer_id = e.identity()["peer_id"]
            node_id = _dht_node_id(e)
            # SHA1(peer_id) != raw peer_id[:20]
            self.assertNotEqual(node_id, peer_id[:20].encode())
            # node_id is 20 bytes
            self.assertEqual(len(node_id), 20)

    def test_announce_key_differs_from_identity(self):
        from urace.peer_discovery import _derive_announce_key
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            _, pub_dht = _derive_announce_key(e)
            identity_pub = e.crypto_identity().ed.public_key().public_bytes_raw()
            self.assertNotEqual(pub_dht, identity_pub)

    def test_anonymize_cert_fields_no_pii(self):
        from urace.peer_exchange import anonymize_cert_fields
        with tempfile.TemporaryDirectory() as tmp:
            e = _make_exchange(tmp)
            cert_pem = e.identity()["certificate"]
            info = anonymize_cert_fields(cert_pem)
            self.assertIn("subject", info)
            self.assertIn("public_key_type", info)
            self.assertIn("not_valid_after", info)
            # Must not expose org / email
            self.assertNotIn("organization", info)
            self.assertNotIn("email", info)
            self.assertNotIn("san", info)


if __name__ == "__main__":
    unittest.main()
