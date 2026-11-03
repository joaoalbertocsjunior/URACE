"""Tests for NAT traversal: public endpoint discovery, rendezvous, hole punching,
relay forwarding, and relay_connect helper.
"""
import hashlib
import os
import socket
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


def _pin_pair(a, b):
    """Mutually pin two exchanges and allow feat send/receive."""
    aid = a.identity()["peer_id"]
    bid = b.identity()["peer_id"]
    a.peer(b.identity()["certificate"], post_quantum=b.identity()["post_quantum"])
    b.peer(a.identity()["certificate"], post_quantum=a.identity()["post_quantum"])
    a.rule(bid, "feat", "send", True)
    b.rule(aid, "feat", "receive", True)
    a.rule(bid, "feat", "receive", True)
    b.rule(aid, "feat", "send", True)
    return aid, bid


# ── PublicEndpointTests ───────────────────────────────────────────────────────

class PublicEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_discover_public_endpoint_parses_dht_echo(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        # Simulate a DHT pong with r["ip"] = 1.2.3.4
        fake_msg = {b"y": b"r", b"r": {b"ip": socket.inet_aton("1.2.3.4")}}
        with patch.object(pd._DHTClient, "_recv", return_value=(fake_msg, ("1.2.3.4", 6881))), \
             patch("socket.gethostbyname", return_value="1.2.3.4"):
            result = pd.discover_public_endpoint(e, timeout=2.0)
        self.assertEqual(result["public_ip"], "1.2.3.4")
        self.assertEqual(result["source"], "dht_echo")

    def test_discover_public_endpoint_raises_on_no_response(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.object(pd._DHTClient, "_recv", return_value=(None, None)), \
             patch("socket.gethostbyname", return_value="127.0.0.1"):
            with self.assertRaises(OSError):
                pd.discover_public_endpoint(e, timeout=0.2)


# ── RdvTests ──────────────────────────────────────────────────────────────────

class RdvTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_rdv_infohash_stable(self):
        from urace.peer_discovery import _rdv_infohash
        ih1 = _rdv_infohash("abc123")
        ih2 = _rdv_infohash("abc123")
        self.assertEqual(ih1, ih2)
        self.assertEqual(len(ih1), 20)

    def test_rdv_infohash_differs_per_peer(self):
        from urace.peer_discovery import _rdv_infohash
        ih_a = _rdv_infohash("peerA")
        ih_b = _rdv_infohash("peerB")
        self.assertNotEqual(ih_a, ih_b)

    def test_rdv_announce_returns_status(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.object(pd._DHTClient, "bootstrap", return_value=2), \
             patch.object(pd._DHTClient, "get_peers", return_value=[]), \
             patch.object(pd._DHTClient, "announce_peer", return_value=3):
            result = pd.rdv_announce(e, "target-peer-id-12345678", 8443)
        self.assertEqual(result["status"], "ANNOUNCED")
        self.assertIn("target_peer_id", result)
        self.assertEqual(result["announced_to"], 3)

    def test_rdv_poll_returns_empty_on_no_peers(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.object(pd._DHTClient, "bootstrap", return_value=1), \
             patch.object(pd._DHTClient, "get_peers", return_value=[]):
            result = pd.rdv_poll(e, 8443, timeout=0.5)
        self.assertEqual(result, [])

    def test_rdv_poll_returns_candidates(self):
        from urace import peer_discovery as pd
        e = _make_exchange(self.tmp.name)
        with patch.object(pd._DHTClient, "bootstrap", return_value=1), \
             patch.object(pd._DHTClient, "get_peers", return_value=[("1.2.3.4", 9000)]):
            result = pd.rdv_poll(e, 8443, timeout=0.5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ip"], "1.2.3.4")
        self.assertEqual(result[0]["port"], 9000)
        self.assertEqual(result[0]["source"], "rdv_poll")


# ── HolePunchTests ────────────────────────────────────────────────────────────

class HolePunchTests(unittest.TestCase):
    def test_hole_punch_succeeds_on_localhost(self):
        from urace.peer_discovery import hole_punch
        # Start a real TCP listener on an ephemeral port
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(5)
        port = listener.getsockname()[1]
        try:
            sock = hole_punch("127.0.0.1", port, timeout=3.0)
            self.assertIsNotNone(sock)
            sock.close()
        finally:
            listener.close()

    def test_hole_punch_returns_none_on_refused(self):
        from urace.peer_discovery import hole_punch
        # Port 1 is almost certainly refused
        result = hole_punch("127.0.0.1", 1, timeout=1.0)
        self.assertIsNone(result)

    def test_hole_punch_no_raise_on_failure(self):
        from urace.peer_discovery import hole_punch
        # Should not raise, just return None
        try:
            result = hole_punch("0.0.0.0", 9, timeout=0.5)
            self.assertIsNone(result)
        except Exception as exc:
            self.fail(f"hole_punch raised unexpectedly: {exc}")


# ── RelayTests ────────────────────────────────────────────────────────────────

class RelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _start_server(self, exchange):
        """Start exchange server in background thread, return (server, thread)."""
        from urace import peer_exchange as pe
        srv = pe.server(exchange)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        return srv, t

    def _setup_three_nodes(self, relay_enabled=True):
        """Create nodes a, relay, b with mutual pinning and servers."""
        from urace import peer_exchange as pe
        root = Path(self.tmp.name)
        a     = pe.Exchange(root / "a")
        relay = pe.Exchange(root / "relay")
        b     = pe.Exchange(root / "b")
        for e in (a, relay, b):
            e.configure(enabled=True, network=True)
            e.feature("feat", [])
        relay.configure(relay_enabled=relay_enabled)
        # Pin a ↔ relay
        a_id     = a.identity()["peer_id"]
        relay_id = relay.identity()["peer_id"]
        b_id     = b.identity()["peer_id"]
        a.peer(relay.identity()["certificate"], post_quantum=relay.identity()["post_quantum"])
        relay.peer(a.identity()["certificate"], post_quantum=a.identity()["post_quantum"])
        relay.peer(b.identity()["certificate"], post_quantum=b.identity()["post_quantum"])
        b.peer(relay.identity()["certificate"], post_quantum=relay.identity()["post_quantum"])
        # a ↔ relay rules
        a.rule(relay_id, "feat", "send", True)
        relay.rule(a_id, "feat", "receive", True)
        relay.rule(a_id, "feat", "send", True)
        a.rule(relay_id, "feat", "receive", True)
        # relay ↔ b rules
        relay.rule(b_id, "feat", "send", True)
        b.rule(relay_id, "feat", "receive", True)
        b.rule(relay_id, "feat", "send", True)
        relay.rule(b_id, "feat", "receive", True)
        return a, a_id, relay, relay_id, b, b_id

    def test_relay_forward_requires_relay_enabled(self):
        """relay_forward with relay_enabled=False raises ValueError (400 error)."""
        from urace import peer_exchange as pe
        a, a_id, relay, relay_id, b, b_id = self._setup_three_nodes(relay_enabled=False)
        srv_relay, t_relay = self._start_server(relay)
        srv_b, t_b = self._start_server(b)
        try:
            port_relay = srv_relay.server_port
            port_b     = srv_b.server_port
            a.peer(relay.identity()["certificate"],
                   "https://127.0.0.1:" + str(port_relay),
                   post_quantum=relay.identity()["post_quantum"])
            relay.peer(b.identity()["certificate"],
                       "https://127.0.0.1:" + str(port_b),
                       post_quantum=b.identity()["post_quantum"])
            with self.assertRaises((ValueError, OSError)):
                pe.request(a, relay_id, "exchange.relay_forward", {
                    "target_peer_id": b_id,
                    "method": "exchange.info",
                    "params": {},
                })
        finally:
            srv_relay.shutdown(); t_relay.join(timeout=5)
            srv_b.shutdown();     t_b.join(timeout=5)

    def test_relay_forward_works_when_enabled(self):
        """a → relay → b returns exchange.info result from b."""
        from urace import peer_exchange as pe
        a, a_id, relay, relay_id, b, b_id = self._setup_three_nodes(relay_enabled=True)
        srv_a,     t_a     = self._start_server(a)
        srv_relay, t_relay = self._start_server(relay)
        srv_b,     t_b     = self._start_server(b)
        try:
            port_a     = srv_a.server_port
            port_relay = srv_relay.server_port
            port_b     = srv_b.server_port
            # Set endpoints
            a.peer(relay.identity()["certificate"],
                   "https://127.0.0.1:" + str(port_relay),
                   post_quantum=relay.identity()["post_quantum"])
            relay.peer(a.identity()["certificate"],
                       "https://127.0.0.1:" + str(port_a),
                       post_quantum=a.identity()["post_quantum"])
            relay.peer(b.identity()["certificate"],
                       "https://127.0.0.1:" + str(port_b),
                       post_quantum=b.identity()["post_quantum"])
            b.peer(relay.identity()["certificate"],
                   "https://127.0.0.1:" + str(port_relay),
                   post_quantum=relay.identity()["post_quantum"])
            result = pe.relay_connect(a, relay_id, b_id)
            self.assertEqual(result["peer_id"], b_id)
            self.assertIn("protocol_version", result)
        finally:
            srv_a.shutdown();     t_a.join(timeout=5)
            srv_relay.shutdown(); t_relay.join(timeout=5)
            srv_b.shutdown();     t_b.join(timeout=5)

    def test_relay_connect_helper_wraps_request(self):
        """relay_connect calls request with exchange.relay_forward and correct params."""
        from urace import peer_exchange as pe
        tmp_root = Path(self.tmp.name)
        a = pe.Exchange(tmp_root / "a2")
        a.configure(enabled=True, network=True)
        fake_result = {"peer_id": "b-id-fake", "protocol_version": 2}
        with patch.object(pe, "request", return_value=fake_result) as mock_req:
            result = pe.relay_connect(a, "relay-id", "b-id",
                                      method="exchange.info", params={})
        mock_req.assert_called_once_with(
            a, "relay-id", "exchange.relay_forward",
            {"target_peer_id": "b-id", "method": "exchange.info", "params": {}},
        )
        self.assertEqual(result, fake_result)


if __name__ == "__main__":
    unittest.main()
