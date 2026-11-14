"""NAT type detection, UPnP probing, and node capability assessment for internet-wide P2P."""
from __future__ import annotations
import os
import socket
import struct
import time


STUN_SERVERS = [
    ("stun.l.google.com", 19302),
    ("stun1.l.google.com", 19302),
    ("stun.cloudflare.com", 3478),
    ("stun.stunprotocol.org", 3478),
]

DEFAULT_LISTEN_PORT = 7301


def _stun_probe(stun_host: str, stun_port: int, local_sock: socket.socket, timeout: float = 5.0) -> dict | None:
    """Send a single STUN binding request on existing socket. Returns {ip, port} or None."""
    magic = b"\x21\x12\xa4\x42"
    tid = os.urandom(12)
    req = struct.pack("!HH", 0x0001, 0) + magic + tid
    local_sock.settimeout(timeout)
    try:
        local_sock.sendto(req, (stun_host, stun_port))
        data, _ = local_sock.recvfrom(2048)
    except (OSError, socket.timeout):
        return None
    if len(data) < 20 or struct.unpack("!H", data[:2])[0] != 0x0101:
        return None
    i = 20
    result = fallback = None
    while i + 4 <= len(data):
        at = struct.unpack("!H", data[i:i+2])[0]
        al = struct.unpack("!H", data[i+2:i+4])[0]
        av = data[i+4:i+4+al]
        if at == 0x0020 and al >= 8 and av[1] == 0x01:
            p = struct.unpack("!H", av[2:4])[0] ^ 0x2112
            ip_int = struct.unpack("!I", av[4:8])[0] ^ 0x2112A442
            ip = socket.inet_ntoa(struct.pack("!I", ip_int))
            result = {"ip": ip, "port": p}
            break
        elif at == 0x0001 and al >= 8 and fallback is None and av[1] == 0x01:
            p = struct.unpack("!H", av[2:4])[0]
            ip = socket.inet_ntoa(av[4:8])
            fallback = {"ip": ip, "port": p}
        pad = al + (4 - al % 4) % 4
        i += 4 + pad
    return result or fallback


def detect_nat_type(timeout: float = 5.0) -> dict:
    """Double-STUN probe to classify NAT type.

    Returns:
        {nat_type: 'direct'|'cone'|'symmetric'|'unknown',
         public_ip: str|None, public_port: int|None, stun_server: str|None}

    'direct'   — public IP matches local IP (VPS/server, no NAT)
    'cone'     — same external port across multiple STUN servers (UPnP/port-forward can open inbound)
    'symmetric' — different external port per STUN server (relay required for inbound)
    'unknown'  — STUN failed
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 0))
    results = []
    stun_used = None
    for host, port in STUN_SERVERS[:3]:
        r = _stun_probe(host, port, sock, timeout)
        if r:
            results.append(r)
            if stun_used is None:
                stun_used = f"{host}:{port}"
        time.sleep(0.1)
    sock.close()

    if not results:
        return {"nat_type": "unknown", "public_ip": None, "public_port": None, "stun_server": None}

    public_ip = results[0]["ip"]
    public_port = results[0]["port"]

    # Check if direct (no NAT): local IP == public IP
    try:
        local_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_sock.connect(("8.8.8.8", 80))
        local_ip = local_sock.getsockname()[0]
        local_sock.close()
    except OSError:
        local_ip = None

    if local_ip and local_ip == public_ip:
        return {"nat_type": "direct", "public_ip": public_ip, "public_port": public_port, "stun_server": stun_used}

    if len(results) >= 2:
        ports = {r["port"] for r in results}
        if len(ports) == 1:
            return {"nat_type": "cone", "public_ip": public_ip, "public_port": public_port, "stun_server": stun_used}
        return {"nat_type": "symmetric", "public_ip": public_ip, "public_port": public_port, "stun_server": stun_used}

    return {"nat_type": "unknown", "public_ip": public_ip, "public_port": public_port, "stun_server": stun_used}


def detect_upnp(port: int = DEFAULT_LISTEN_PORT, timeout_ms: int = 2000) -> dict:
    """Probe router for UPnP IGD. Returns {available, external_ip, mapped_port, error}.

    Requires miniupnpc (now in base install). Never raises.
    """
    try:
        import miniupnpc
        u = miniupnpc.UPnP()
        u.discoverdelay = timeout_ms
        n = u.discover()
        if n == 0:
            return {"available": False, "external_ip": None, "mapped_port": None, "error": "no_upnp_devices"}
        u.selectigd()
        ext_ip = u.externalipaddress()
        return {"available": True, "external_ip": ext_ip, "mapped_port": port, "error": None}
    except ImportError:
        return {"available": False, "external_ip": None, "mapped_port": None, "error": "miniupnpc_not_installed"}
    except Exception as e:
        # miniupnpc raises Exception("Success") when discover() finds 0 devices in some versions
        msg = str(e)
        if msg == "Success":
            return {"available": False, "external_ip": None, "mapped_port": None, "error": "no_upnp_devices"}
        return {"available": False, "external_ip": None, "mapped_port": None, "error": msg}


def check_node_capability(timeout: float = 5.0, upnp_timeout_ms: int = 2000) -> dict:
    """Full capability check: STUN + UPnP → determine feasible node roles.

    Returns:
        {
          public_ip: str|None,
          nat_type: str,
          upnp_available: bool,
          upnp_external_ip: str|None,
          can_bootstrap: bool,
          can_relay: bool,
          relay_required: bool,
          recommended_roles: list[str],
          recommended_network_mode: str,
          reasons: dict,
        }
    """
    nat = detect_nat_type(timeout=timeout)
    upnp = detect_upnp(timeout_ms=upnp_timeout_ms)

    nat_type = nat["nat_type"]
    public_ip = nat["public_ip"]
    upnp_ok = upnp["available"]

    # Bootstrap requires stable long-lived inbound reachability
    # Only 'direct' (no NAT) or cone NAT + UPnP qualifies automatically
    can_bootstrap = nat_type == "direct"
    can_relay = nat_type in ("direct", "cone") and (nat_type == "direct" or upnp_ok)
    relay_required = nat_type == "symmetric"

    # Consumers/creators only need outbound — always works
    roles = ["consumer", "creator"]
    if can_relay:
        roles.insert(0, "relay")
    if can_bootstrap:
        roles.insert(0, "bootstrap")

    if nat_type == "unknown" or public_ip is None:
        network_mode = "intranet"
    else:
        network_mode = "internet" if nat_type == "direct" else "hybrid"

    reasons: dict = {}
    if not can_bootstrap and nat_type != "direct":
        reasons["bootstrap"] = f"NAT type '{nat_type}' — needs manual port-forward or direct public IP for stable inbound"
    if not can_relay and nat_type == "cone" and not upnp_ok:
        reasons["relay"] = "Cone NAT detected but UPnP unavailable — enable UPnP on router or set manual port-forward"
    if relay_required:
        reasons["relay_required"] = "Symmetric NAT — this node cannot receive inbound connections; LAN-only or use existing relay"

    return {
        "public_ip": public_ip,
        "nat_type": nat_type,
        "upnp_available": upnp_ok,
        "upnp_external_ip": upnp.get("external_ip"),
        "can_bootstrap": can_bootstrap,
        "can_relay": can_relay,
        "relay_required": relay_required,
        "recommended_roles": roles,
        "recommended_network_mode": network_mode,
        "reasons": reasons,
    }


def auto_open_upnp_port(port: int = DEFAULT_LISTEN_PORT, description: str = "URACE P2P") -> dict:
    """Attempt to open an inbound port via UPnP IGD. Returns {status, mapped_port, error}."""
    try:
        import miniupnpc
        u = miniupnpc.UPnP()
        u.discoverdelay = 2000
        if u.discover() == 0:
            return {"status": "no_upnp", "mapped_port": None, "error": "no_upnp_devices"}
        u.selectigd()
        result = u.addportmapping(port, "TCP", u.lanaddr, port, description, "")
        if result:
            return {"status": "ok", "mapped_port": port, "error": None}
        return {"status": "failed", "mapped_port": None, "error": "addportmapping returned False"}
    except ImportError:
        return {"status": "no_upnp", "mapped_port": None, "error": "miniupnpc_not_installed"}
    except Exception as e:
        msg = str(e)
        if msg == "Success":
            return {"status": "no_upnp", "mapped_port": None, "error": "no_upnp_devices"}
        return {"status": "failed", "mapped_port": None, "error": msg}
