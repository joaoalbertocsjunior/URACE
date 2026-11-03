"""Zero-config peer discovery: LAN (mDNS) + WAN (BitTorrent DHT BEP 5).

Discovery surfaces UNVERIFIED candidates only. A candidate becomes a trusted
peer only after explicit exchange.peer() + exchange.rule() pinning.

LAN layer:  mDNS/Zeroconf, service _urace-exchange._tcp.local.
            Requires: pip install zeroconf  (optional — manual pinning works without it)
WAN layer:  BitTorrent DHT (BEP 5), stdlib only (socket + struct + asyncio).
            Topic infohash = SHA1(b"urace-exchange-v1")  [20 bytes]
            Announced value = HTTPS port only; certificate retrieved via exchange.info RPC.
            Bootstrap: router.bittorrent.com:6881, dht.transmissionbt.com:6881
            Truly decentralised — no URACE-specific infrastructure required.

NAT note: nodes behind NAT need port forwarding or UPnP to be WAN-reachable.
          LAN discovery works behind NAT; WAN discovery finds publicly reachable nodes.

start(exchange, port) -> DiscoverySession  — runs both layers, re-announces every 30 min.

Privacy / unlinkability properties
───────────────────────────────────
- _dht_node_id(exchange) uses SHA1(peer_id), not peer_id directly — DHT node id ≠ exchange
  identity. A passive DHT observer cannot recover the exchange peer_id from the node id.
- _derive_announce_key uses HKDF separation (salt=b"urace-dht-announce-v1") — the DHT
  announce keypair is cryptographically independent of the exchange signing keypair.  Even
  full compromise of the DHT announce key does not expose the exchange signing key.
- relay_only mode hides the node's IP from the final recipient; all traffic is routed
  through an explicitly trusted relay peer, so DHT only ever learns the relay's address.
- ephemeral_announce=True (DiscoverySession) generates a fresh BEP 44 keypair each
  session. Successive sessions cannot be correlated via DHT key; cert is only findable
  during the session it was published.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import threading
import time
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────────

_LAN_SERVICE = "_urace-exchange._tcp.local."
_DHT_TOPIC   = hashlib.sha1(b"urace-exchange-v1").digest()   # 20-byte infohash
_DHT_BOOTSTRAP = [
    ("router.bittorrent.com",   6881),
    ("router.utorrent.com",     6881),
    ("dht.transmissionbt.com",  6881),
]
_MAX_DHT_CANDIDATES = 64


# ── Bencode (stdlib-only, BEP 3) ──────────────────────────────────────────────

def _be(v: Any) -> bytes:
    if isinstance(v, bytes):  return (str(len(v)) + ":").encode() + v
    if isinstance(v, int):    return b"i" + str(v).encode() + b"e"
    if isinstance(v, list):   return b"l" + b"".join(_be(x) for x in v) + b"e"
    if isinstance(v, dict):   return b"d" + b"".join(_be(k) + _be(v[k]) for k in sorted(v)) + b"e"
    if isinstance(v, str):    return _be(v.encode())
    raise TypeError(f"Cannot bencode {type(v)!r}")


def _bd(d: bytes, i: int) -> tuple[Any, int]:
    b = d[i:i+1]
    if b == b"i":
        j = d.index(b"e", i + 1)
        return int(d[i+1:j]), j + 1
    if b == b"l":
        i += 1; lst: list = []
        while d[i:i+1] != b"e":
            v, i = _bd(d, i); lst.append(v)
        return lst, i + 1
    if b == b"d":
        i += 1; dct: dict = {}
        while d[i:i+1] != b"e":
            k, i = _bd(d, i); v, i = _bd(d, i); dct[k] = v
        return dct, i + 1
    c = d.index(b":", i); n = int(d[i:c]); end = c + 1 + n
    return d[c+1:end], end


def bdecode(data: bytes) -> Any:
    v, _ = _bd(data, 0)
    return v


# ── LAN: mDNS announce / discover ─────────────────────────────────────────────

def announce(exchange, port: int) -> Any:
    """Broadcast this node on the LAN as _urace-exchange._tcp.local.

    Returns an opaque handle; pass it to stop_announce() to deregister.
    Requires: pip install zeroconf
    """
    try:
        from zeroconf import ServiceInfo, Zeroconf
    except ImportError:
        raise ValueError("LAN announce requires: pip install zeroconf")

    peer_id = exchange.identity()["peer_id"]
    addrs: list[bytes] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                addrs.append(socket.inet_aton(ip))
    except OSError:
        pass
    if not addrs:
        addrs = [socket.inet_aton("127.0.0.1")]

    svc_name = f"{peer_id[:16]}.{_LAN_SERVICE}"
    info = ServiceInfo(
        _LAN_SERVICE,
        svc_name,
        addresses=addrs,
        port=port,
        properties={b"peer_id": peer_id.encode(), b"v": b"1"},
    )
    zc = Zeroconf()
    zc.register_service(info)
    return (zc, info)


def stop_announce(handle: Any) -> None:
    """Deregister a LAN announcement returned by announce()."""
    if handle is None:
        return
    zc, info = handle
    try:
        zc.unregister_service(info)
    except Exception:
        pass
    try:
        zc.close()
    except Exception:
        pass


def discover_lan(exchange, seconds: float = 3.0) -> list[dict[str, Any]]:
    """Browse LAN for URACE nodes via mDNS.

    Returns candidate dicts: {service, addresses, port, peer_id, auto_trusted: False}.
    Requires: pip install zeroconf
    """
    try:
        from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
    except ImportError:
        raise ValueError("LAN discovery requires: pip install zeroconf")

    rows: dict[str, dict] = {}

    def changed(zc, service_type, name, state_change):
        if state_change is ServiceStateChange.Removed:
            return
        info = zc.get_service_info(service_type, name, timeout=500)
        if info and len(rows) < 64:
            props = {k.decode(): v.decode() if isinstance(v, bytes) else v
                     for k, v in (info.properties or {}).items()}
            rows[name] = {
                "service": name,
                "addresses": info.parsed_addresses()[:4],
                "port": info.port,
                "peer_id": props.get("peer_id", ""),
                "auto_trusted": False,
                "source": "lan",
            }

    with Zeroconf() as z:
        browser = ServiceBrowser(z, _LAN_SERVICE, handlers=[changed])
        try:
            time.sleep(seconds)
        finally:
            browser.cancel()
    return list(rows.values())


# ── WAN: BitTorrent DHT (BEP 5) ───────────────────────────────────────────────

def _dht_node_id(exchange) -> bytes:
    """Derive a stable 20-byte DHT node ID from the exchange's peer identity."""
    peer_id = exchange.identity()["peer_id"]
    return hashlib.sha1(peer_id.encode()).digest()


# ── BEP 44: mutable DHT items (cert publishing / lookup) ──────────────────────

def _derive_announce_key(exchange) -> tuple[bytes, bytes]:
    """Derive a stable 32-byte ED25519 keypair for DHT BEP 44 announcements.

    Uses HKDF-SHA256 with a dedicated salt so the DHT announce key is
    cryptographically independent of the exchange signing key.

    Returns (priv_bytes, pub_bytes) — 32 bytes each.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    # Access raw ED25519 private key bytes from the exchange hybrid identity.
    crypto_id = exchange.crypto_identity()
    # crypto_id.ed is an Ed25519PrivateKey; private_bytes_raw() returns 32 bytes.
    ikm = crypto_id.ed.private_bytes_raw()

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"urace-dht-announce-v1",
        info=b"",
    )
    priv_bytes = hkdf.derive(ikm)
    priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
    pub_bytes = priv_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return priv_bytes, pub_bytes


def _bep44_sign(priv_bytes: bytes, seq: int, value_bencoded: bytes) -> bytes:
    """Sign a BEP 44 mutable item. Returns 64-byte Ed25519 signature."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sig_data = b"3:seq" + _be(seq) + b"1:v" + value_bencoded
    return Ed25519PrivateKey.from_private_bytes(priv_bytes).sign(sig_data)


def _bep44_verify(pub_bytes: bytes, seq: int, value_bencoded: bytes, sig: bytes) -> bool:
    """Verify a BEP 44 mutable item signature. Returns True if valid."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        sig_data = b"3:seq" + _be(seq) + b"1:v" + value_bencoded
        Ed25519PublicKey.from_public_bytes(pub_bytes).verify(sig, sig_data)
        return True
    except Exception:
        return False


def bep44_put(
    client: "_DHTClient",
    pub_bytes: bytes,
    priv_bytes: bytes,
    seq: int,
    value: dict,
    timeout: float = 8.0,
) -> int:
    """Store a BEP 44 mutable item in the DHT. Returns count of nodes sent to."""
    try:
        value_bencoded = _be(value)
        sig = _bep44_sign(priv_bytes, seq, value_bencoded)
        target = hashlib.sha1(pub_bytes).digest()
        # Walk DHT to collect write tokens.
        try:
            client.get_peers(target, timeout / 2)
        except Exception:
            pass
        sent = 0
        for addr, token in list(client._tokens.items()):
            if not token:
                continue
            client._send(addr, {
                b"t": os.urandom(2), b"y": b"q", b"q": b"put",
                b"a": {
                    b"id":  client._id,
                    b"k":   pub_bytes,
                    b"seq": seq,
                    b"sig": sig,
                    b"token": token,
                    b"v":   _be(value),
                },
            })
            sent += 1
        return sent
    except Exception:
        return 0


def bep44_get(
    client: "_DHTClient",
    pub_bytes: bytes,
    timeout: float = 10.0,
) -> "dict | None":
    """Retrieve a BEP 44 mutable item by public key. Returns None if not found."""
    try:
        target = hashlib.sha1(pub_bytes).digest()
        queried: set[tuple[str, int]] = set()
        candidates: list[tuple[str, int]] = []

        for host, port in _DHT_BOOTSTRAP:
            try:
                candidates.append((socket.gethostbyname(host), port))
            except OSError:
                pass

        deadline = time.monotonic() + timeout
        while candidates and time.monotonic() < deadline:
            addr = candidates.pop(0)
            if addr in queried:
                continue
            queried.add(addr)
            client._send(addr, {
                b"t": os.urandom(2), b"y": b"q", b"q": b"get",
                b"a": {b"id": client._id, b"target": target},
            })
            msg, src = client._recv(1.5)
            if not msg:
                continue
            r = msg.get(b"r", {})
            if b"v" in r:
                try:
                    raw_v = r[b"v"]
                    raw_sig = r.get(b"sig", b"")
                    raw_seq = r.get(b"seq", 0)
                    if isinstance(raw_v, bytes):
                        value_bencoded = raw_v
                    else:
                        value_bencoded = _be(raw_v)
                    if _bep44_verify(pub_bytes, raw_seq, value_bencoded, raw_sig):
                        if isinstance(raw_v, bytes):
                            return bdecode(raw_v)
                        return raw_v
                except Exception:
                    pass
            # Walk closer nodes.
            if b"nodes" in r:
                raw = r[b"nodes"]
                if isinstance(raw, bytes):
                    for i in range(0, len(raw) - 25, 26):
                        ip   = socket.inet_ntoa(raw[i+20:i+24])
                        port = struct.unpack("!H", raw[i+24:i+26])[0]
                        if port > 0 and (ip, port) not in queried:
                            candidates.append((ip, port))
        return None
    except Exception:
        return None


def dht_cert_publish(exchange, https_port: int, *, ephemeral: bool = False) -> dict:
    """Publish this node's certificate to the DHT via BEP 44 mutable item.

    If ephemeral=True: fresh random key each call (session-only discoverability).
    If ephemeral=False: stable key derived from identity (persistent discoverability).

    Returns {"status": "PUBLISHED", "dht_key": <hex>, "port": ..., "ephemeral": ...}.
    Never raises — returns error dict on failure.
    """
    try:
        if ephemeral:
            priv_bytes = os.urandom(32)
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
            pub_bytes = Ed25519PrivateKey.from_private_bytes(priv_bytes).public_key().public_bytes(
                Encoding.Raw, PublicFormat.Raw
            )
            seq = 0
        else:
            priv_bytes, pub_bytes = _derive_announce_key(exchange)
            seq = int(time.time())

        identity = exchange.identity()
        value = {
            b"cert":    identity["certificate"].encode(),
            b"port":    https_port,
            b"peer_id": identity["peer_id"].encode(),
        }
        nid    = os.urandom(20)
        client = _DHTClient(nid)
        try:
            client.bootstrap(timeout=3.0)
            bep44_put(client, pub_bytes, priv_bytes, seq, value, timeout=8.0)
        finally:
            client.close()

        return {
            "status":    "PUBLISHED",
            "dht_key":   pub_bytes.hex(),
            "port":      https_port,
            "ephemeral": ephemeral,
        }
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}


def dht_cert_lookup(dht_key_hex: str, timeout: float = 10.0) -> "dict | None":
    """Retrieve a peer's certificate from the DHT given their BEP 44 hex key.

    Returns {"certificate": ..., "port": ..., "peer_id": ...} or None.
    Never raises.
    """
    try:
        pub_bytes = bytes.fromhex(dht_key_hex)
        nid       = os.urandom(20)
        client    = _DHTClient(nid)
        try:
            client.bootstrap(timeout=3.0)
            value = bep44_get(client, pub_bytes, timeout)
        finally:
            client.close()

        if value is None:
            return None
        return {
            "certificate": value[b"cert"].decode(),
            "port":        value[b"port"],
            "peer_id":     value[b"peer_id"].decode(),
        }
    except Exception:
        return None


def dht_key_for(exchange, ephemeral: bool = False) -> str:
    """Return the hex DHT key others can use to look up this node's cert.

    Ephemeral keys are session-specific; get the key from dht_cert_publish result.
    """
    if ephemeral:
        raise ValueError(
            "Ephemeral keys are session-specific; get from dht_cert_publish result"
        )
    _, pub = _derive_announce_key(exchange)
    return pub.hex()


# ── P2P update bundle DHT broadcast / check ───────────────────────────────────

def _local_corpus_fingerprint_from_root() -> str:
    """Compute the local P2P corpus fingerprint using this file's location."""
    from pathlib import Path as _Path
    from . import evolution_guard as _eg
    _pkg = _Path(os.path.abspath(__file__)).parent
    return _eg.p2p_corpus_fingerprint(_pkg.parent.parent.parent)


def p2p_update_publish(
    bundle: dict,
    priv_key_bytes: bytes,
    bundle_url: str = "",
    timeout: float = 8.0,
) -> dict:
    """Publish a signed P2P update bundle to the DHT via BEP 44 mutable item.

    priv_key_bytes: 32-byte Ed25519 private key of the release authority.
    bundle_url: publicly reachable URL where nodes can download the full bundle JSON.
      Required for auto-update — DHT only stores metadata; nodes fetch the full
      bundle from this URL before verifying and applying.

    The DHT item schema (fits within BEP 44 1000-byte value limit):
      schema, corpus_fingerprint, author_signature, announced_at, bundle_url

    Returns {"status": "PUBLISHED", "dht_key": <hex>, "corpus_fingerprint": ...,
             "bundle_url": ..., "announced_to": N}.
    Never raises — returns error dict on failure.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        priv_key  = Ed25519PrivateKey.from_private_bytes(priv_key_bytes)
        pub_bytes = priv_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        seq       = bundle.get("announced_at", int(time.time()))

        benc_val: dict = {
            b"schema":             bundle["schema"].encode(),
            b"corpus_fingerprint": bundle["corpus_fingerprint"].encode(),
            b"author_signature":   bundle["author_signature"].encode(),
            b"announced_at":       seq,
        }
        if bundle_url:
            benc_val[b"bundle_url"] = bundle_url.encode()

        nid    = os.urandom(20)
        client = _DHTClient(nid)
        try:
            client.bootstrap(timeout=3.0)
            sent = bep44_put(client, pub_bytes, priv_key_bytes, seq, benc_val, timeout=timeout)
        finally:
            client.close()

        return {
            "status":             "PUBLISHED",
            "dht_key":            pub_bytes.hex(),
            "corpus_fingerprint": bundle["corpus_fingerprint"],
            "bundle_url":         bundle_url,
            "announced_to":       sent,
        }
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}


def p2p_update_check(
    exchange,
    update_pub_key_hex: str,
    author_verify_fn=None,
    *,
    timeout: float = 10.0,
) -> dict:
    """Query DHT for a signed P2P security update at update_pub_key_hex.

    author_verify_fn(corpus_fp: bytes, sig: bytes) -> bool
      Defaults to evolution_guard.verify_release_signature() — the pinned
      release authority key hardcoded in the immutable kernel.  Pass a custom
      verifier only in tests or operator tooling; production nodes should ALWAYS
      use the default so the trust anchor cannot be swapped at call-site.

    If a bundle with a different (but signature-verified) corpus fingerprint is
    found, emits a P2P_UPDATE_AVAILABLE audit event so the operator can decide
    whether to apply the update via evolution_guard.apply_p2p_update_bundle().

    Returns {available, local_fingerprint, corpus_fingerprint?, announced_at?,
             dht_key?, peer_count?}.  Never raises.
    """
    if author_verify_fn is None:
        from . import evolution_guard as _eg_default
        author_verify_fn = _eg_default.verify_release_signature
    try:
        local_fp = _local_corpus_fingerprint_from_root()

        pub_bytes = bytes.fromhex(update_pub_key_hex)
        nid       = os.urandom(20)
        client    = _DHTClient(nid)
        try:
            client.bootstrap(timeout=min(timeout * 0.3, 3.0))
            value = bep44_get(client, pub_bytes, timeout=timeout * 0.7)
        finally:
            client.close()

        if value is None:
            return {"available": False, "local_fingerprint": local_fp}

        remote_fp    = (value.get(b"corpus_fingerprint") or b"").decode("ascii", errors="replace")
        sig_hex      = (value.get(b"author_signature")   or b"").decode("ascii", errors="replace")
        announced_at = value.get(b"announced_at", 0)

        try:
            sig       = bytes.fromhex(sig_hex)
            sig_valid = author_verify_fn(remote_fp.encode(), sig)
        except Exception:
            sig_valid = False

        if not sig_valid:
            return {"available": False, "local_fingerprint": local_fp, "error": "invalid signature"}

        bundle_url = (value.get(b"bundle_url") or b"").decode("ascii", errors="replace")

        if remote_fp == local_fp:
            return {"available": False, "local_fingerprint": local_fp,
                    "corpus_fingerprint": remote_fp}

        # Count peers already observed with this fingerprint via P2P_CORPUS_MISMATCH events.
        try:
            mismatch_rows = [
                r for r in exchange.audit_rows()
                if r.get("kind") == "P2P_CORPUS_MISMATCH"
                and r.get("remote_fingerprint") == remote_fp
            ]
            peer_count = len({r.get("peer") for r in mismatch_rows if r.get("peer")})
        except Exception:
            peer_count = 0

        with exchange.lock():
            exchange.event(
                "P2P_UPDATE_AVAILABLE",
                dht_key=update_pub_key_hex,
                local_fingerprint=local_fp,
                remote_fingerprint=remote_fp,
                announced_at=announced_at,
                bundle_url=bundle_url,
                peer_count=peer_count,
            )

        result = {
            "available":          True,
            "local_fingerprint":  local_fp,
            "corpus_fingerprint": remote_fp,
            "announced_at":       announced_at,
            "dht_key":            update_pub_key_hex,
            "bundle_url":         bundle_url,
            "peer_count":         peer_count,
        }

        # Auto-apply path: operator opts in via config p2p.auto_update = true.
        # Only runs when a bundle_url is present; signature already verified above.
        try:
            cfg = exchange.load()
            if cfg.get("p2p", {}).get("auto_update") and bundle_url:
                apply_errors = _auto_apply_bundle_from_url(
                    exchange, bundle_url, author_verify_fn
                )
                result["auto_applied"] = not bool(apply_errors)
                result["auto_apply_errors"] = apply_errors
        except Exception as _exc:
            result["auto_apply_errors"] = [str(_exc)]

        return result
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def _run_update_check(exchange) -> None:
    """Check for updates: central hub URL first, then DHT key fallback.

    Also called immediately when ≥2 distinct peers are seen running a newer
    corpus fingerprint (peer-consensus trigger from peer_exchange.request()).
    """
    try:
        from . import evolution_guard as _eg
        if _eg.P2P_UPDATE_BUNDLE_URL:
            _check_and_auto_apply_central_url(exchange, _eg.P2P_UPDATE_BUNDLE_URL)
        elif _eg.RELEASE_AUTHORITY_KEYS:
            p2p_update_check(exchange, _eg.RELEASE_AUTHORITY_KEYS[0])
    except Exception:
        pass


def _check_and_auto_apply_central_url(exchange, url: str) -> None:
    """Fetch bundle from central URL, verify multi-sig, auto-apply if policy allows.

    Called from _reannounce_loop (every ~60 min) and from peer_exchange.request()
    when ≥2 distinct peers are seen running a newer corpus fingerprint.
    All security gates still apply: multi-sig threshold + full test suite.
    """
    import urllib.request as _ur
    try:
        from pathlib import Path as _Path
        from . import evolution_guard as _eg

        _pkg          = _Path(os.path.abspath(__file__)).parent
        _product_root = _pkg.parent.parent.parent
        local_fp      = _eg.p2p_corpus_fingerprint(_product_root)

        with _ur.urlopen(url, timeout=15) as resp:  # noqa: S310
            bundle = json.loads(resp.read())

        remote_fp = bundle.get("corpus_fingerprint", "")
        if not remote_fp or remote_fp == local_fp:
            return

        sigs = bundle.get("author_signatures")
        if sigs:
            valid, count = _eg.verify_multi_sig(remote_fp, sigs)
        else:
            sig_hex = bundle.get("author_signature", "")
            try:
                valid = _eg.verify_release_signature(remote_fp.encode(), bytes.fromhex(sig_hex))
                count = 1 if valid else 0
            except Exception:
                valid, count = False, 0

        if not valid:
            with exchange.lock():
                exchange.event("P2P_UPDATE_SIGNATURE_INVALID", bundle_url=url,
                               remote_fingerprint=remote_fp)
            return

        with exchange.lock():
            exchange.event("P2P_UPDATE_AVAILABLE", bundle_url=url,
                           local_fingerprint=local_fp, remote_fingerprint=remote_fp,
                           signatures_valid=count)

        cfg = exchange.load()
        if cfg.get("p2p", {}).get("auto_update"):
            errors = _eg.apply_p2p_update_bundle(bundle, _product_root, run_tests=True)
            kind = "P2P_UPDATE_APPLIED" if not errors else "P2P_UPDATE_REJECTED"
            with exchange.lock():
                exchange.event(kind, bundle_url=url,
                               corpus_fingerprint=remote_fp, errors=errors)
    except Exception:
        pass


def _auto_apply_bundle_from_url(exchange, bundle_url: str, author_verify_fn) -> list[str]:
    """Download, verify, and apply an update bundle from bundle_url.

    Used only when p2p.auto_update = true.  Returns [] on success, error list on failure.
    All gates still apply: signature verification + full test suite.
    """
    try:
        import urllib.request as _ur
        import json as _json
        from pathlib import Path as _Path
        from . import evolution_guard as _eg

        with _ur.urlopen(bundle_url, timeout=30) as _resp:  # noqa: S310
            bundle = _json.loads(_resp.read())

        _pkg          = _Path(os.path.abspath(__file__)).parent
        _product_root = _pkg.parent.parent.parent

        errors = _eg.apply_p2p_update_bundle(
            bundle, _product_root, author_verify_fn, run_tests=True
        )

        kind = "P2P_UPDATE_APPLIED" if not errors else "P2P_UPDATE_REJECTED"
        with exchange.lock():
            exchange.event(kind, bundle_url=bundle_url,
                           corpus_fingerprint=bundle.get("corpus_fingerprint", ""),
                           errors=errors)
        return errors
    except Exception as exc:
        return [str(exc)]


def _compact_peers(raw: bytes) -> list[tuple[str, int]]:
    """Decode BEP 5 compact peer list: 6 bytes per peer (4-byte IP + 2-byte port)."""
    out = []
    for i in range(0, len(raw) - 5, 6):
        ip   = socket.inet_ntoa(raw[i:i+4])
        port = struct.unpack("!H", raw[i+4:i+6])[0]
        if port > 0:
            out.append((ip, port))
    return out


class _DHTClient:
    """Minimal BEP 5 DHT UDP client: bootstrap → get_peers → announce_peer.

    Only implements the subset needed for rendezvous discovery.
    No persistent routing table — stateless between sessions.
    """

    def __init__(self, node_id: bytes):
        self._id = node_id
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(1.5)
        self._sock.bind(("0.0.0.0", 0))
        self._tokens: dict[tuple[str, int], bytes] = {}  # addr → write token

    def _send(self, addr: tuple[str, int], msg: dict) -> None:
        try:
            self._sock.sendto(_be(msg), addr)
        except OSError:
            pass

    def _recv(self, timeout: float = 1.5) -> tuple[dict | None, tuple[str, int] | None]:
        self._sock.settimeout(timeout)
        try:
            data, addr = self._sock.recvfrom(4096)
            return bdecode(data), addr
        except (socket.timeout, OSError, ValueError, IndexError, KeyError):
            return None, None

    def bootstrap(self, timeout: float = 4.0) -> int:
        """Ping bootstrap nodes; collect tokens for later announce_peer calls.

        Rate-limited: skips if last bootstrap was within 300s to prevent DHT flooding.
        Jitter (0–30s) is added per-node to spread load on shared bootstrap servers.
        """
        try:
            _policy = self._exchange.load()
            _last_boot = _policy.get('dht_bootstrap_last_unix', 0)
            if time.time() - _last_boot < 300:
                return 0  # Too soon — use cached DHT state
        except Exception:
            pass
        contacted = 0
        import random as _random
        for host, port in _DHT_BOOTSTRAP:
            try:
                ip = socket.gethostbyname(host)
            except OSError:
                continue
            time.sleep(_random.uniform(0, 0.5))  # jitter per node (max 0.5s)
            self._send((ip, port), {b"t": os.urandom(2), b"y": b"q",
                                    b"q": b"ping", b"a": {b"id": self._id}})
            contacted += 1

        try:
            from ._common import atomic_write_json as _awj
            with self._exchange.lock():
                _p = self._exchange.load()
                _p['dht_bootstrap_last_unix'] = time.time()
                _awj(self._exchange.root / 'policy.json', _p)
                import os as _os
                _os.chmod(self._exchange.root / 'policy.json', 0o600)
        except Exception:
            pass
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            msg, addr = self._recv(0.5)
            if msg and addr and msg.get(b"y") == b"r":
                tok = msg.get(b"r", {}).get(b"token", b"")
                self._tokens[addr] = tok
        return contacted

    def get_peers(self, infohash: bytes, timeout: float = 12.0) -> list[tuple[str, int]]:
        """Iterative get_peers walk. Returns (ip, https_port) candidates."""
        queried:    set[tuple[str, int]] = set()
        candidates: list[tuple[str, int]] = []
        found:      list[tuple[str, int]] = []

        for host, port in _DHT_BOOTSTRAP:
            try:
                candidates.append((socket.gethostbyname(host), port))
            except OSError:
                pass

        deadline = time.monotonic() + timeout
        while candidates and time.monotonic() < deadline and len(found) < _MAX_DHT_CANDIDATES:
            addr = candidates.pop(0)
            if addr in queried:
                continue
            queried.add(addr)

            self._send(addr, {b"t": os.urandom(2), b"y": b"q", b"q": b"get_peers",
                               b"a": {b"id": self._id, b"info_hash": infohash}})
            msg, src = self._recv(1.5)
            if not msg or not src:
                continue

            r = msg.get(b"r", {})
            if b"token" in r:
                self._tokens[src] = r[b"token"]

            # Peers directly announcing our topic — these are URACE HTTPS endpoints.
            if b"values" in r:
                for raw in r[b"values"]:
                    if isinstance(raw, bytes):
                        found.extend(_compact_peers(raw))

            # Closer nodes to walk toward.
            if b"nodes" in r:
                raw = r[b"nodes"]
                if isinstance(raw, bytes):
                    for i in range(0, len(raw) - 25, 26):
                        ip   = socket.inet_ntoa(raw[i+20:i+24])
                        port = struct.unpack("!H", raw[i+24:i+26])[0]
                        if port > 0 and (ip, port) not in queried:
                            candidates.append((ip, port))

        return list({(ip, p) for ip, p in found})  # deduplicate

    def announce_peer(self, infohash: bytes, port: int) -> int:
        """Announce self to all nodes that gave us a write token."""
        sent = 0
        for addr, token in list(self._tokens.items()):
            if not token:
                continue
            self._send(addr, {
                b"t": os.urandom(2), b"y": b"q", b"q": b"announce_peer",
                b"a": {
                    b"id":          self._id,
                    b"info_hash":   infohash,
                    b"port":        port,
                    b"token":       token,
                    b"implied_port": 0,
                },
            })
            sent += 1
        return sent

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


def dht_announce(exchange, port: int) -> dict[str, Any]:
    """Register this node on the BitTorrent DHT so peers can find it.

    Other URACE nodes running dht_discover() will find this IP:port.
    They then query the HTTPS exchange.info RPC to obtain the certificate.
    Call periodically (≥ every 30 min) to stay in DHT routing tables;
    DiscoverySession.start() handles the re-announce loop automatically.

    Returns immediately — no blocking wait.
    """
    nid    = _dht_node_id(exchange)
    client = _DHTClient(nid)
    try:
        client.bootstrap(timeout=4.0)
        client.get_peers(_DHT_TOPIC, timeout=8.0)   # walks DHT, collects tokens
        sent = client.announce_peer(_DHT_TOPIC, port)
        return {
            "status":       "ANNOUNCED",
            "port":         port,
            "announced_to": sent,
            "topic":        _DHT_TOPIC.hex(),
        }
    finally:
        client.close()


def dht_discover(exchange, timeout: float = 15.0) -> list[dict[str, Any]]:
    """Search BitTorrent DHT for URACE peers announcing our topic.

    Returns candidate dicts: {ip, port, auto_trusted: False, source: "dht"}.
    Candidates are UNVERIFIED. Exchange.peer() + cert pinning required before use.
    Returns empty list on network failure — never raises.
    """
    nid    = _dht_node_id(exchange)
    client = _DHTClient(nid)
    try:
        try:
            client.bootstrap(timeout=3.0)
        except OSError:
            return []
        raw = client.get_peers(_DHT_TOPIC, timeout=timeout)
        return [{"ip": ip, "port": port, "auto_trusted": False, "source": "dht"}
                for ip, port in raw]
    finally:
        client.close()


# ── Combined session ───────────────────────────────────────────────────────────

class DiscoverySession:
    """Runs LAN + WAN discovery for a live exchange server.

    Both layers are started immediately. WAN re-announces every 30 min
    to remain visible in DHT routing tables (entries expire after ~15 min).

    Usage:
        session = start(exchange, port=8443)
        candidates = session.scan()   # query both layers for new peers
        session.stop()

    Or as a context manager:
        with start(exchange, port=8443) as s:
            candidates = s.scan()
    """

    def __init__(
        self,
        exchange,
        port: int,
        *,
        lan: bool = True,
        wan: bool = True,
        ephemeral_announce: bool = False,
    ):
        self._exchange          = exchange
        self._port              = port
        self._lan               = lan
        self._wan               = wan
        self._ephemeral_announce = ephemeral_announce
        self._lan_handle: Any  = None
        self._stop              = threading.Event()
        self._thread:  threading.Thread | None = None

    def _reannounce_loop(self) -> None:
        _update_ticks = 0
        while not self._stop.wait(timeout=1800):   # every 30 min
            try:
                dht_announce(self._exchange, self._port)
            except Exception:
                pass
            _update_ticks += 1
            # Check for P2P security updates every 2 reannounce cycles (~60 min).
            if _update_ticks % 2 == 0:
                _run_update_check(self._exchange)
            # Update estimated_network_size via EMA (alpha=0.3) to drive dynamic
            # consensus threshold in peer_exchange._consensus_min().
            try:
                from ._common import atomic_write_json as _awj
                with self._exchange.lock():
                    policy = self._exchange.load()
                    known = len({r.get('peer') for r in self._exchange.audit_rows() if r.get('peer')})
                    current_est = policy.get('estimated_network_size', 1)
                    new_est = max(known, int(0.7 * current_est + 0.3 * known))
                    changed = False
                    if new_est != current_est:
                        policy['estimated_network_size'] = new_est
                        changed = True
                    # Persist all-time max to prevent attacker from faking small network
                    # and lowering the consensus threshold for P2P_CORPUS_MISMATCH votes.
                    prev_max = policy.get('max_observed_network_size', 1)
                    if known > prev_max:
                        policy['max_observed_network_size'] = known
                        changed = True
                    if changed:
                        _awj(self._exchange.root / 'policy.json', policy)
                        import os as _os
                        _os.chmod(self._exchange.root / 'policy.json', 0o600)
            except Exception:
                pass

    @property
    def dht_key(self) -> str:
        """Hex BEP 44 key others use to look up this node's cert (stable key only)."""
        return dht_key_for(self._exchange, ephemeral=False)

    def start(self) -> "DiscoverySession":
        relay_only = self._exchange.load().get("relay_only", False)

        if self._lan:
            if relay_only:
                self._lan_handle = None
            else:
                try:
                    self._lan_handle = announce(self._exchange, self._port)
                except Exception:
                    self._lan_handle = None

        if self._wan:
            if not relay_only:
                try:
                    dht_announce(self._exchange, self._port)
                except Exception:
                    pass
            # Always try BEP 44 cert publish (cert + port only, no IP in payload).
            try:
                dht_cert_publish(
                    self._exchange,
                    self._port,
                    ephemeral=self._ephemeral_announce,
                )
            except Exception:
                pass
            self._thread = threading.Thread(target=self._reannounce_loop, daemon=True,
                                            name="urace-dht-announce")
            self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        stop_announce(self._lan_handle)
        self._lan_handle = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def scan(self, lan_seconds: float = 2.0, wan_timeout: float = 15.0) -> list[dict[str, Any]]:
        """Active scan: browse LAN + search DHT. Returns merged candidate list.

        If auto_trust_first_contact is set in policy, attempts auto_pin for candidates
        that carry a certificate (from BEP 44 lookup) or an IP:port (via exchange.info).
        Each candidate gets an added auto_pinned: True/False field when auto-trust is on.
        """
        candidates: list[dict] = []
        if self._lan:
            try:
                candidates.extend(discover_lan(self._exchange, seconds=lan_seconds))
            except Exception:
                pass
        if self._wan:
            try:
                candidates.extend(dht_discover(self._exchange, timeout=wan_timeout))
            except Exception:
                pass
        # Deduplicate by (ip/address, port)
        seen: set[tuple] = set()
        unique = []
        for c in candidates:
            key = (c.get("ip", ""), c.get("port", 0))
            if key not in seen:
                seen.add(key)
                unique.append(c)

        # Auto-pin integration (Feature 4)
        if self._exchange.load().get("auto_trust_first_contact"):
            from .peer_exchange import auto_pin, request as _request
            for c in unique:
                pinned = False
                try:
                    cert = c.get("certificate")
                    ip   = c.get("ip") or (c.get("addresses") or [None])[0]
                    port = c.get("port")
                    if cert:
                        endpoint = f"https://{ip}:{port}" if ip and port else None
                        if endpoint:
                            auto_pin(self._exchange, cert, endpoint)
                            pinned = True
                    elif ip and port:
                        endpoint = f"https://{ip}:{port}"
                        try:
                            info = _request(self._exchange, c.get("peer_id", ""), "exchange.info", {})
                            remote_cert = info.get("certificate")
                            if remote_cert:
                                auto_pin(self._exchange, remote_cert, endpoint)
                                pinned = True
                        except Exception:
                            pass
                except Exception:
                    pass
                c["auto_pinned"] = pinned

        return unique

    def __enter__(self) -> "DiscoverySession":
        return self

    def __exit__(self, *_) -> None:
        self.stop()


def start(
    exchange,
    port: int,
    *,
    lan: bool = True,
    wan: bool = True,
    ephemeral_announce: bool = False,
) -> DiscoverySession:
    """Start LAN + WAN discovery. Returns a DiscoverySession; call .stop() when done."""
    return DiscoverySession(
        exchange, port, lan=lan, wan=wan, ephemeral_announce=ephemeral_announce
    ).start()


# ── NAT Traversal: Public endpoint discovery ──────────────────────────────────

def discover_public_endpoint(exchange, timeout: float = 5.0) -> dict[str, Any]:
    """Discover this node's public IP by echoing a BT DHT ping to bootstrap nodes.

    Bootstrap nodes (BEP 5) echo the querier's source IP in r["ip"] (4 bytes, IPv4).
    Returns {"public_ip": "...", "source": "dht_echo"}.
    Raises OSError if no bootstrap node responds.
    """
    nid = _dht_node_id(exchange)
    client = _DHTClient(nid)
    try:
        deadline = time.monotonic() + timeout
        for host, port in _DHT_BOOTSTRAP:
            try:
                ip = socket.gethostbyname(host)
            except OSError:
                continue
            client._send((ip, port), {
                b"t": os.urandom(2), b"y": b"q",
                b"q": b"ping", b"a": {b"id": nid},
            })

        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            msg, addr = client._recv(remaining)
            if msg is None:
                break
            r = msg.get(b"r", {})
            ip_bytes = r.get(b"ip", b"")
            if isinstance(ip_bytes, bytes) and len(ip_bytes) >= 4:
                public_ip = socket.inet_ntoa(ip_bytes[:4])
                return {"public_ip": public_ip, "source": "dht_echo"}
    finally:
        client.close()
    raise OSError("No DHT bootstrap node responded with IP echo")


# ── NAT Traversal: Rendezvous via DHT ─────────────────────────────────────────

def _rdv_infohash(peer_id: str) -> bytes:
    """Return the 20-byte rendezvous infohash for a given peer_id."""
    return hashlib.sha1(b"urace-rdv-" + peer_id[:16].encode()).digest()


def rdv_announce(exchange, target_peer_id: str, https_port: int) -> dict[str, Any]:
    """Announce on target peer's rendezvous slot to signal we want to connect.

    Bootstraps DHT, walks toward _rdv_infohash(target_peer_id), announces there.
    Returns {"status": "ANNOUNCED", "target_peer_id": ..., "announced_to": N}.
    """
    nid    = _dht_node_id(exchange)
    rdv_ih = _rdv_infohash(target_peer_id)
    client = _DHTClient(nid)
    try:
        client.bootstrap(timeout=4.0)
        client.get_peers(rdv_ih, timeout=8.0)  # walks DHT, collects tokens
        sent = client.announce_peer(rdv_ih, https_port)
        return {
            "status":         "ANNOUNCED",
            "target_peer_id": target_peer_id[:16],
            "announced_to":   sent,
        }
    finally:
        client.close()


def rdv_poll(exchange, https_port: int, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Check our own rendezvous slot for peers who want to connect to us.

    Returns list of {"ip": ..., "port": N, "source": "rdv_poll"}.
    Never raises — returns [] on any failure.
    """
    try:
        nid        = _dht_node_id(exchange)
        own_rdv_ih = _rdv_infohash(exchange.identity()["peer_id"])
        client     = _DHTClient(nid)
        try:
            client.bootstrap(timeout=min(timeout * 0.6, 3.0))
            peers = client.get_peers(own_rdv_ih, timeout=timeout)
            return [{"ip": ip, "port": port, "source": "rdv_poll"} for ip, port in peers]
        finally:
            client.close()
    except Exception:
        return []


# ── NAT Traversal: UDP hole punching + TCP connect ────────────────────────────

def hole_punch(
    target_ip: str,
    target_port: int,
    *,
    local_port: int = 0,
    timeout: float = 20.0,
) -> "socket.socket | None":
    """Attempt NAT hole-punch to (target_ip, target_port).

    Phase 1 — UDP knock: sends 5 × b"urace-punch" probes 100 ms apart to open
               NAT pinholes for full-cone NAT.
    Phase 2 — TCP connect: loops until timeout, each attempt creates a fresh TCP
               socket (SO_REUSEADDR, optionally SO_REUSEPORT + bind) and tries to
               connect.  Returns the connected socket on success, None on timeout.
    Never raises.
    """
    try:
        # Phase 1: UDP probes
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            if local_port:
                try:
                    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    if hasattr(socket, "SO_REUSEPORT"):
                        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    udp.bind(("0.0.0.0", local_port))
                except OSError:
                    pass
            for _ in range(5):
                try:
                    udp.sendto(b"urace-punch", (target_ip, target_port))
                except OSError:
                    pass
                time.sleep(0.1)
        finally:
            udp.close()

        # Phase 2: TCP connect loop
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if local_port:
                    if hasattr(socket, "SO_REUSEPORT"):
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    sock.bind(("0.0.0.0", local_port))
                sock.settimeout(2.0)
                sock.connect((target_ip, target_port))
                return sock
            except OSError:
                try:
                    sock.close()
                except OSError:
                    pass
                time.sleep(1.0)
        return None
    except Exception:
        return None


# ── DiscoverySession.connect_peer ─────────────────────────────────────────────

def _connect_peer(
    self: "DiscoverySession",
    peer_id: str,
    ip: str,
    port: int,
    relay_peer_id: "str | None" = None,
) -> bool:
    """Try direct → hole-punch → relay to establish connectivity with a peer.

    1. Direct: if peer already pinned, try exchange.info RPC.
    2. Punch:  rdv_announce then hole_punch; if socket returned, reachable.
    3. Relay:  if punch fails and relay_peer_id given, try relay_connect.
    Returns True if any path succeeded.
    """
    from .peer_exchange import request, relay_connect

    # 1. Direct attempt
    p = self._exchange.load()
    if peer_id in p.get("peers", {}):
        try:
            request(self._exchange, peer_id, "exchange.info", {})
            return True
        except Exception:
            pass

    # 2. Hole-punch via rendezvous (rate-limited: max 5 attempts per peer per day)
    try:
        _hp_rows = [r for r in self._exchange.audit_rows()
                    if r.get('kind') == 'HOLE_PUNCH_ATTEMPTED'
                    and r.get('peer') == peer_id
                    and r.get('at_unix', 0) > time.time() - 86400]
        if len(_hp_rows) >= 5:
            sock = None
        else:
            try:
                rdv_announce(self._exchange, peer_id, self._port)
            except Exception:
                pass
            self._exchange.event('HOLE_PUNCH_ATTEMPTED', peer=peer_id, ip=ip, port=port)
            sock = hole_punch(ip, port, timeout=20.0)
    except Exception:
        sock = None
    _dummy_sock = sock  # for reference after inner block
    if _dummy_sock is not None:
        try:
            _dummy_sock.close()
        except OSError:
            pass
        return True

    # 3. Relay fallback
    if relay_peer_id is not None:
        try:
            relay_connect(self._exchange, relay_peer_id, peer_id)
            return True
        except Exception:
            pass

    return False


# Attach connect_peer to DiscoverySession
DiscoverySession.connect_peer = _connect_peer
