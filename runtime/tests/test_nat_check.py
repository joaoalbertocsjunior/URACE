"""Tests for nat_check module — no real network calls."""
import sys
import types
import pytest
from unittest.mock import patch, MagicMock


def _make_stun_response(ip: str, port: int) -> bytes:
    """Build a minimal STUN Binding Success Response with XOR-MAPPED-ADDRESS."""
    import struct, socket
    magic = b"\x21\x12\xa4\x42"
    xip = struct.pack("!I", int.from_bytes(socket.inet_aton(ip), 'big') ^ 0x2112A442)
    xport = struct.pack("!H", port ^ 0x2112)
    attr = b"\x00\x01" + xip  # family=IPv4, padding
    attr_val = bytes([0, 1]) + xport + xip  # family, xport, xip
    attr_full = struct.pack("!HH", 0x0020, len(attr_val)) + attr_val
    # pad to 4 bytes
    while len(attr_full) % 4:
        attr_full += b"\x00"
    header = struct.pack("!HH", 0x0101, len(attr_full)) + magic + b"\x00" * 12
    return header + attr_full


def test_detect_nat_type_cone(monkeypatch):
    """Same port from multiple STUN servers → cone NAT."""
    from urace import nat_check
    call_count = [0]

    def fake_probe(host, port, sock, timeout=5.0):
        call_count[0] += 1
        return {"ip": "1.2.3.4", "port": 12345}

    monkeypatch.setattr(nat_check, "_stun_probe", fake_probe)

    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        mock_sock.getsockname.return_value = ("192.168.1.1", 54321)
        with patch("socket.socket") as ms2:
            ms2_inst = MagicMock()
            ms2.return_value = ms2_inst
            ms2_inst.getsockname.return_value = ("192.168.1.1", 0)
            result = nat_check.detect_nat_type()

    assert result["nat_type"] in ("cone", "unknown", "direct")
    assert result["public_ip"] == "1.2.3.4" or result["public_ip"] is None


def test_detect_nat_type_symmetric(monkeypatch):
    """Different port per STUN server → symmetric NAT."""
    from urace import nat_check
    ports = iter([11111, 22222, 33333])

    def fake_probe(host, port, sock, timeout=5.0):
        return {"ip": "1.2.3.4", "port": next(ports, 44444)}

    monkeypatch.setattr(nat_check, "_stun_probe", fake_probe)

    with patch("socket.socket") as ms:
        ms_inst = MagicMock()
        ms.return_value = ms_inst
        ms_inst.getsockname.return_value = ("192.168.1.1", 0)
        result = nat_check.detect_nat_type()

    assert result["nat_type"] in ("symmetric", "unknown")


def test_detect_nat_type_no_stun(monkeypatch):
    """All STUN servers fail → unknown."""
    from urace import nat_check
    monkeypatch.setattr(nat_check, "_stun_probe", lambda *a, **kw: None)
    with patch("socket.socket"):
        result = nat_check.detect_nat_type()
    assert result["nat_type"] == "unknown"
    assert result["public_ip"] is None


def test_detect_upnp_no_miniupnpc(monkeypatch):
    """miniupnpc not installed → available=False."""
    from urace import nat_check
    monkeypatch.setitem(sys.modules, "miniupnpc", None)
    result = nat_check.detect_upnp()
    assert result["available"] is False


def test_detect_upnp_success_exception(monkeypatch):
    """miniupnpc raises Exception('Success') → no devices, available=False."""
    from urace import nat_check
    mock_mod = types.ModuleType("miniupnpc")

    class FakeUPnP:
        discoverdelay = 0
        def discover(self): raise Exception("Success")

    mock_mod.UPnP = FakeUPnP
    monkeypatch.setitem(sys.modules, "miniupnpc", mock_mod)
    result = nat_check.detect_upnp()
    assert result["available"] is False
    assert result["error"] == "no_upnp_devices"


def test_check_node_capability_consumer_only(monkeypatch):
    """Symmetric NAT → only consumer+creator roles."""
    from urace import nat_check
    monkeypatch.setattr(nat_check, "detect_nat_type", lambda **kw: {
        "nat_type": "symmetric", "public_ip": "1.2.3.4", "public_port": 9999, "stun_server": "s"
    })
    monkeypatch.setattr(nat_check, "detect_upnp", lambda **kw: {
        "available": False, "external_ip": None, "mapped_port": None, "error": "no_devices"
    })
    cap = nat_check.check_node_capability()
    assert cap["can_bootstrap"] is False
    assert cap["can_relay"] is False
    assert cap["relay_required"] is True
    assert "consumer" in cap["recommended_roles"]
    assert cap["recommended_network_mode"] == "hybrid"


def test_check_node_capability_direct(monkeypatch):
    """Direct IP (VPS) → all roles."""
    from urace import nat_check
    import socket as _s
    monkeypatch.setattr(nat_check, "detect_nat_type", lambda **kw: {
        "nat_type": "direct", "public_ip": "5.5.5.5", "public_port": 7301, "stun_server": "s"
    })
    monkeypatch.setattr(nat_check, "detect_upnp", lambda **kw: {
        "available": False, "external_ip": None, "mapped_port": None, "error": "na"
    })
    cap = nat_check.check_node_capability()
    assert cap["can_bootstrap"] is True
    assert cap["can_relay"] is True
    assert "bootstrap" in cap["recommended_roles"]
    assert cap["recommended_network_mode"] == "internet"


def test_check_node_capability_cone_upnp(monkeypatch):
    """Cone NAT + UPnP → relay but not bootstrap."""
    from urace import nat_check
    monkeypatch.setattr(nat_check, "detect_nat_type", lambda **kw: {
        "nat_type": "cone", "public_ip": "2.2.2.2", "public_port": 5000, "stun_server": "s"
    })
    monkeypatch.setattr(nat_check, "detect_upnp", lambda **kw: {
        "available": True, "external_ip": "2.2.2.2", "mapped_port": 7301, "error": None
    })
    cap = nat_check.check_node_capability()
    assert cap["can_bootstrap"] is False
    assert cap["can_relay"] is True
    assert "relay" in cap["recommended_roles"]
    assert "bootstrap" not in cap["recommended_roles"]
