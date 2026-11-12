"""Tests for urace.stun_client — RFC 5389 STUN public address discovery."""
import os
import socket
import struct
import unittest
from unittest.mock import MagicMock, patch


def _xor_mapped_response(ip: str, port: int) -> bytes:
    """Build a minimal STUN Binding Success Response with XOR-MAPPED-ADDRESS."""
    magic = 0x2112A442
    xor_port = port ^ 0x2112
    xor_ip = struct.unpack("!I", socket.inet_aton(ip))[0] ^ magic
    attr_val = bytes([0x00, 0x01]) + struct.pack("!H", xor_port) + struct.pack("!I", xor_ip)
    attr = struct.pack("!HH", 0x0020, len(attr_val)) + attr_val
    # pad to 4-byte boundary
    padded = attr + b"\x00" * ((4 - len(attr_val) % 4) % 4)
    header = struct.pack("!HH", 0x0101, len(padded)) + b"\x21\x12\xa4\x42" + b"\x00" * 12
    return header + padded


def _mapped_address_response(ip: str, port: int) -> bytes:
    """Build a minimal STUN response with MAPPED-ADDRESS (RFC 3489 fallback)."""
    attr_val = bytes([0x00, 0x01]) + struct.pack("!H", port) + socket.inet_aton(ip)
    attr = struct.pack("!HH", 0x0001, len(attr_val)) + attr_val
    padded = attr + b"\x00" * ((4 - len(attr_val) % 4) % 4)
    header = struct.pack("!HH", 0x0101, len(padded)) + b"\x21\x12\xa4\x42" + b"\x00" * 12
    return header + padded


def _mock_sock(response_bytes: bytes):
    sock = MagicMock()
    sock.recvfrom.return_value = (response_bytes, ("stun.l.google.com", 19302))
    return sock


class XorMappedAddressTests(unittest.TestCase):
    def test_returns_ip_and_port(self):
        from urace.stun_client import get_public_address
        resp = _xor_mapped_response("1.2.3.4", 54321)
        with patch("socket.socket", return_value=_mock_sock(resp)):
            result = get_public_address()
        self.assertIsNotNone(result)
        self.assertEqual(result["ip"], "1.2.3.4")
        self.assertEqual(result["port"], 54321)

    def test_prefers_xor_over_mapped(self):
        from urace.stun_client import get_public_address
        magic = 0x2112A442
        xor_port = 9000 ^ 0x2112
        xor_ip = struct.unpack("!I", socket.inet_aton("10.0.0.1"))[0] ^ magic
        xor_val = bytes([0x00, 0x01]) + struct.pack("!H", xor_port) + struct.pack("!I", xor_ip)
        xor_attr = struct.pack("!HH", 0x0020, len(xor_val)) + xor_val
        mapped_val = bytes([0x00, 0x01]) + struct.pack("!H", 8000) + socket.inet_aton("9.9.9.9")
        mapped_attr = struct.pack("!HH", 0x0001, len(mapped_val)) + mapped_val
        body = mapped_attr + xor_attr
        header = struct.pack("!HH", 0x0101, len(body)) + b"\x21\x12\xa4\x42" + b"\x00" * 12
        with patch("socket.socket", return_value=_mock_sock(header + body)):
            result = get_public_address()
        self.assertEqual(result["ip"], "10.0.0.1")
        self.assertEqual(result["port"], 9000)


class MappedAddressFallbackTests(unittest.TestCase):
    def test_fallback_to_mapped_address(self):
        from urace.stun_client import get_public_address
        resp = _mapped_address_response("5.6.7.8", 12345)
        with patch("socket.socket", return_value=_mock_sock(resp)):
            result = get_public_address()
        self.assertIsNotNone(result)
        self.assertEqual(result["ip"], "5.6.7.8")
        self.assertEqual(result["port"], 12345)


class ErrorHandlingTests(unittest.TestCase):
    def test_returns_none_on_timeout(self):
        from urace.stun_client import get_public_address
        sock = MagicMock()
        sock.recvfrom.side_effect = socket.timeout("timed out")
        with patch("socket.socket", return_value=sock):
            result = get_public_address()
        self.assertIsNone(result)

    def test_returns_none_on_oserror(self):
        from urace.stun_client import get_public_address
        sock = MagicMock()
        sock.sendto.side_effect = OSError("network unreachable")
        with patch("socket.socket", return_value=sock):
            result = get_public_address()
        self.assertIsNone(result)

    def test_returns_none_on_too_short_response(self):
        from urace.stun_client import get_public_address
        sock = _mock_sock(b"\x01\x01\x00")
        with patch("socket.socket", return_value=sock):
            result = get_public_address()
        self.assertIsNone(result)

    def test_returns_none_on_wrong_msg_type(self):
        from urace.stun_client import get_public_address
        resp = struct.pack("!HH", 0x0111, 0) + b"\x21\x12\xa4\x42" + b"\x00" * 12
        with patch("socket.socket", return_value=_mock_sock(resp)):
            result = get_public_address()
        self.assertIsNone(result)

    def test_returns_none_when_no_address_attributes(self):
        from urace.stun_client import get_public_address
        header = struct.pack("!HH", 0x0101, 0) + b"\x21\x12\xa4\x42" + b"\x00" * 12
        with patch("socket.socket", return_value=_mock_sock(header)):
            result = get_public_address()
        self.assertIsNone(result)

    def test_socket_always_closed(self):
        from urace.stun_client import get_public_address
        sock = MagicMock()
        sock.recvfrom.side_effect = socket.timeout
        with patch("socket.socket", return_value=sock):
            get_public_address()
        sock.close.assert_called_once()

    def test_socket_closed_on_success_too(self):
        from urace.stun_client import get_public_address
        resp = _xor_mapped_response("192.168.1.1", 50000)
        sock = _mock_sock(resp)
        with patch("socket.socket", return_value=sock):
            get_public_address()
        sock.close.assert_called_once()
