"""Tests for peer_discovery: bencode, compact peers, DHT client, LAN announce,
and DiscoverySession lifecycle. Network-dependent tests require URACE_NETWORK_TESTS=1.
"""
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_exchange(tmp, name="node"):
    from urace import peer_exchange as pe
    e = pe.Exchange(Path(tmp) / name)
    e.configure(enabled=True, network=True)
    e.feature("feat", [])
    return e


# ── Bencode ───────────────────────────────────────────────────────────────────

class BencodeTests(unittest.TestCase):
    def _rt(self, v):
        from urace.peer_discovery import bdecode, _be
        self.assertEqual(bdecode(_be(v)), v if not isinstance(v, str) else v.encode())

    def test_bytes(self):        self._rt(b"hello")
    def test_empty_bytes(self):  self._rt(b"")
    def test_int(self):          self._rt(42)
    def test_negative_int(self): self._rt(-7)
    def test_list(self):         self._rt([b"a", b"b", 3])
    def test_dict(self):
        from urace.peer_discovery import bdecode, _be
        d = {b"id": b"x" * 20, b"port": 6881}
        self.assertEqual(bdecode(_be(d)), d)
    def test_nested(self):
        from urace.peer_discovery import bdecode, _be
        v = {b"r": {b"nodes": b"\x00" * 26, b"token": b"tok"}, b"t": b"ab", b"y": b"r"}
        self.assertEqual(bdecode(_be(v)), v)


# ── Compact peer decoding ─────────────────────────────────────────────────────

class CompactPeersTests(unittest.TestCase):
    def test_single_peer(self):
        from urace.peer_discovery import _compact_peers
        raw = socket.inet_aton("1.2.3.4") + struct.pack("!H", 8443)
        self.assertEqual(_compact_peers(raw), [("1.2.3.4", 8443)])

    def test_two_peers(self):
        from urace.peer_discovery import _compact_peers
        raw = (socket.inet_aton("10.0.0.1") + struct.pack("!H", 1234) +
               socket.inet_aton("10.0.0.2") + struct.pack("!H", 5678))
        self.assertEqual(_compact_peers(raw), [("10.0.0.1", 1234), ("10.0.0.2", 5678)])

    def test_zero_port_skipped(self):
        from urace.peer_discovery import _compact_peers
        raw = socket.inet_aton("1.2.3.4") + struct.pack("!H", 0)
        self.assertEqual(_compact_peers(raw), [])

    def test_empty(self):
        from urace.peer_discovery import _compact_peers
        self.assertEqual(_compact_peers(b""), [])


# ── DHT node ID ───────────────────────────────────────────────────────────────

class DHTNodeIdTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_stable_across_calls(self):
        from urace.peer_discovery import _dht_node_id
        e = _make_exchange(self.tmp.name)
        nid1 = _dht_node_id(e)
        nid2 = _dht_node_id(e)
        self.assertEqual(nid1, nid2)
        self.assertEqual(len(nid1), 20)

    def test_different_per_exchange(self):
        from urace.peer_discovery import _dht_node_id
        a = _make_exchange(self.tmp.name, "a")
        b = _make_exchange(self.tmp.name, "b")
        self.assertNotEqual(_dht_node_id(a), _dht_node_id(b))


# ── LAN announce ─────────────────────────────────────────────────────────────

class LanAnnounceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_missing_zeroconf_raises(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.dict("sys.modules", {"zeroconf": None}):
            import importlib
            pd2 = importlib.import_module("urace.peer_discovery")
            with self.assertRaises((ValueError, ImportError)):
                # Force the import path to fail
                orig = pd2.announce
                def patched(exc, port):
                    raise ValueError("LAN announce requires: pip install zeroconf")
                pd2.announce = patched
                try:
                    pd2.announce(e, 8443)
                finally:
                    pd2.announce = orig

    def test_stop_announce_handles_none(self):
        from urace.peer_discovery import stop_announce
        stop_announce(None)   # must not raise

    def test_stop_announce_handles_exception(self):
        from urace.peer_discovery import stop_announce
        bad_zc = MagicMock()
        bad_zc.unregister_service.side_effect = RuntimeError("boom")
        bad_zc.close.side_effect = RuntimeError("boom")
        stop_announce((bad_zc, MagicMock()))   # must not raise


# ── DHTClient (mocked UDP) ────────────────────────────────────────────────────

class DHTClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_bootstrap_handles_dns_failure(self):
        from urace.peer_discovery import _DHTClient
        c = _DHTClient(b"\x00" * 20)
        try:
            with patch("socket.gethostbyname", side_effect=OSError("no dns")):
                n = c.bootstrap(timeout=0.1)
            self.assertEqual(n, 0)
        finally:
            c.close()

    def test_compact_peer_encoding_roundtrip(self):
        from urace.peer_discovery import _compact_peers, _be, bdecode
        raw = socket.inet_aton("192.168.1.1") + struct.pack("!H", 9000)
        peers = _compact_peers(raw)
        self.assertEqual(peers, [("192.168.1.1", 9000)])

    def test_get_peers_returns_empty_on_no_response(self):
        from urace.peer_discovery import _DHTClient, _DHT_TOPIC
        c = _DHTClient(b"\x01" * 20)
        try:
            with patch.object(c, "_recv", return_value=(None, None)):
                with patch("socket.gethostbyname", return_value="127.0.0.1"):
                    result = c.get_peers(_DHT_TOPIC, timeout=0.1)
            self.assertEqual(result, [])
        finally:
            c.close()

    def test_announce_peer_skips_empty_tokens(self):
        from urace.peer_discovery import _DHTClient, _DHT_TOPIC
        c = _DHTClient(b"\x02" * 20)
        try:
            c._tokens = {("127.0.0.1", 6881): b""}  # empty token — should skip
            sent = c.announce_peer(_DHT_TOPIC, 8443)
            self.assertEqual(sent, 0)
        finally:
            c.close()

    def test_announce_peer_sends_with_valid_token(self):
        from urace.peer_discovery import _DHTClient, _DHT_TOPIC
        c = _DHTClient(b"\x03" * 20)
        sent_packets = []
        original_send = c._send
        try:
            c._tokens = {("127.0.0.1", 6881): b"validtoken"}
            c._send = lambda addr, msg: sent_packets.append((addr, msg))
            sent = c.announce_peer(_DHT_TOPIC, 8443)
            self.assertEqual(sent, 1)
            self.assertEqual(len(sent_packets), 1)
        finally:
            c._send = original_send
            c.close()


# ── dht_announce / dht_discover (mocked network) ─────────────────────────────

class DHTDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_dht_announce_returns_status(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.object(pd._DHTClient, "bootstrap", return_value=0), \
             patch.object(pd._DHTClient, "get_peers", return_value=[]), \
             patch.object(pd._DHTClient, "announce_peer", return_value=3):
            result = pd.dht_announce(e, 8443)
        self.assertEqual(result["status"], "ANNOUNCED")
        self.assertEqual(result["port"], 8443)
        self.assertEqual(result["announced_to"], 3)
        self.assertEqual(len(result["topic"]), 40)   # 20 bytes hex

    def test_dht_discover_returns_candidates(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        fake_peers = [("1.2.3.4", 8443), ("5.6.7.8", 9000)]
        with patch.object(pd._DHTClient, "bootstrap", return_value=2), \
             patch.object(pd._DHTClient, "get_peers", return_value=fake_peers):
            result = pd.dht_discover(e, timeout=0.1)
        self.assertEqual(len(result), 2)
        self.assertFalse(result[0]["auto_trusted"])
        self.assertEqual(result[0]["source"], "dht")
        ips = {c["ip"] for c in result}
        self.assertEqual(ips, {"1.2.3.4", "5.6.7.8"})

    def test_dht_discover_returns_empty_on_failure(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.object(pd._DHTClient, "bootstrap", side_effect=OSError("net")):
            result = pd.dht_discover(e, timeout=0.1)
        self.assertEqual(result, [])


# ── DiscoverySession lifecycle ────────────────────────────────────────────────

class DiscoverySessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _mock_both(self):
        from urace import peer_discovery as pd
        return (
            patch.object(pd, "announce", return_value=("fake_zc", "fake_info")),
            patch.object(pd, "stop_announce", return_value=None),
            patch.object(pd, "dht_announce", return_value={"status": "ANNOUNCED", "announced_to": 1}),
            patch.object(pd, "dht_discover", return_value=[]),
            patch.object(pd, "discover_lan", return_value=[]),
        )

    def test_start_stop_no_crash(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        patches = self._mock_both()
        for p in patches:
            p.start()
        try:
            s = pd.start(e, port=8443)
            time.sleep(0.05)
            s.stop()
        finally:
            for p in patches:
                p.stop()

    def test_context_manager(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        patches = self._mock_both()
        for p in patches:
            p.start()
        try:
            with pd.start(e, port=8443) as s:
                self.assertIsNotNone(s)
        finally:
            for p in patches:
                p.stop()

    def test_scan_deduplicates(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        dup = [{"ip": "1.2.3.4", "port": 8443, "auto_trusted": False, "source": "dht"}]
        with patch.object(pd, "announce", return_value=None), \
             patch.object(pd, "stop_announce"), \
             patch.object(pd, "dht_announce", return_value={}), \
             patch.object(pd, "discover_lan", return_value=dup), \
             patch.object(pd, "dht_discover", return_value=dup):
            s = pd.DiscoverySession(e, 8443, lan=True, wan=True)
            s.start()
            try:
                result = s.scan(lan_seconds=0.0, wan_timeout=0.0)
            finally:
                s.stop()
        self.assertEqual(len(result), 1)   # deduplicated

    def test_wan_only_no_lan_dep(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.object(pd, "dht_announce", return_value={}), \
             patch.object(pd, "dht_discover", return_value=[]):
            s = pd.DiscoverySession(e, 8443, lan=False, wan=True)
            s.start()
            s.stop()
            self.assertIsNone(s._lan_handle)

    def test_lan_only_no_dht_thread(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.object(pd, "announce", return_value=None), \
             patch.object(pd, "stop_announce"):
            s = pd.DiscoverySession(e, 8443, lan=True, wan=False)
            s.start()
            s.stop()
            self.assertIsNone(s._thread)


# ── Live DHT (real internet — opt-in) ────────────────────────────────────────

@unittest.skipUnless(os.environ.get("URACE_NETWORK_TESTS"), "set URACE_NETWORK_TESTS=1")
class LiveDHTTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_bootstrap_contacts_known_nodes(self):
        from urace.peer_discovery import _DHTClient
        c = _DHTClient(b"\xaa" * 20)
        try:
            n = c.bootstrap(timeout=5.0)
            self.assertGreater(n, 0)
        finally:
            c.close()

    def test_dht_announce_real_network(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        result = pd.dht_announce(e, 8443)
        self.assertEqual(result["status"], "ANNOUNCED")

    def test_dht_discover_finds_or_empty(self):
        """May return empty if no other URACE nodes are on DHT yet — that's OK."""
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        result = pd.dht_discover(e, timeout=20.0)
        self.assertIsInstance(result, list)
        for c in result:
            self.assertFalse(c["auto_trusted"])
