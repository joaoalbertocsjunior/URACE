"""
Lightweight STUN client (RFC 5389) for NAT traversal / public address discovery.
No external dependencies — pure Python UDP socket only.
Used by `urace exchange network public-address` to probe public IP:port
for intranet→internet bridge configuration.
"""
from __future__ import annotations

import socket
import struct
import os


def get_public_address(
    stun_host: str = "stun.l.google.com",
    stun_port: int = 19302,
    timeout: float = 5.0,
) -> dict | None:
    """
    Probe a STUN server to discover this node's public IP:port.

    Returns {"ip": str, "port": int} on success, None on failure.
    Uses XOR-MAPPED-ADDRESS (RFC 5389) with fallback to MAPPED-ADDRESS (RFC 3489).
    """
    # STUN Binding Request (RFC 5389)
    # Type=0x0001, Length=0, Magic=0x2112A442, Transaction ID=12 random bytes
    magic = b"\x21\x12\xa4\x42"
    transaction_id = os.urandom(12)
    request = struct.pack("!HH", 0x0001, 0) + magic + transaction_id

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(request, (stun_host, stun_port))
        data, _ = sock.recvfrom(2048)
    except (OSError, socket.timeout):
        return None
    finally:
        sock.close()

    if len(data) < 20:
        return None
    msg_type = struct.unpack("!H", data[:2])[0]
    if msg_type != 0x0101:  # Binding Success Response
        return None

    # Parse TLV attributes
    i = 20
    result = None
    fallback = None
    while i + 4 <= len(data):
        attr_type = struct.unpack("!H", data[i : i + 2])[0]
        attr_len = struct.unpack("!H", data[i + 2 : i + 4])[0]
        attr_val = data[i + 4 : i + 4 + attr_len]
        if attr_type == 0x0020 and attr_len >= 8:  # XOR-MAPPED-ADDRESS
            family = attr_val[1]
            if family == 0x01:  # IPv4
                port = struct.unpack("!H", attr_val[2:4])[0] ^ 0x2112
                ip_int = struct.unpack("!I", attr_val[4:8])[0] ^ 0x2112A442
                ip = socket.inet_ntoa(struct.pack("!I", ip_int))
                result = {"ip": ip, "port": port}
                break
        elif attr_type == 0x0001 and attr_len >= 8 and fallback is None:  # MAPPED-ADDRESS
            family = attr_val[1]
            if family == 0x01:
                port = struct.unpack("!H", attr_val[2:4])[0]
                ip = socket.inet_ntoa(attr_val[4:8])
                fallback = {"ip": ip, "port": port}
        padded = attr_len + (4 - attr_len % 4) % 4
        i += 4 + padded

    return result or fallback
