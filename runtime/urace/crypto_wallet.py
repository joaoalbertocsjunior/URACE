"""
Crypto wallet scaffold — local keypair generation, address derivation, payload signing.
No gas fees, no RPC calls, no on-chain broadcast. Everything here is CPU-local.

Address derivation uses keccak256 (EVM-compatible) when pysha3 is installed;
falls back to sha3_256 otherwise — structure is identical, only the hash differs.
Install pysha3 for mainnet-compatible addresses: pip install pysha3
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDSA,
    SECP256K1,
    generate_private_key,
)
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)
from cryptography.hazmat.backends import default_backend

try:
    import sha3 as _sha3_module  # pysha3
    _HAS_KECCAK = True
except ImportError:
    _HAS_KECCAK = False


def _keccak256(data: bytes) -> bytes:
    if _HAS_KECCAK:
        h = hashlib.new("sha3_256")
        h.update(data)
        return h.digest()  # pysha3 patches sha3_256 → keccak
    return hashlib.sha3_256(data).digest()  # FIPS SHA3 fallback (non-EVM)


def _derive_address(pub_uncompressed: bytes) -> str:
    """Ethereum-style address: 0x + last 20 bytes of keccak256(pubkey[1:])."""
    digest = _keccak256(pub_uncompressed[1:])
    return "0x" + digest[12:].hex()


def _wallet_path(wallet_dir: str | Path | None = None) -> Path:
    if wallet_dir:
        return Path(wallet_dir)
    return Path(os.environ.get("URACE_WALLET_DIR", Path.home() / ".urace" / "wallet"))


def _key_file(wallet_dir: Path) -> Path:
    return wallet_dir / "key.json"


def wallet_init(wallet_dir: str | Path | None = None, *, overwrite: bool = False) -> dict:
    """
    Generate a new secp256k1 keypair and persist it locally.
    Returns wallet metadata (no private key in return value).
    Raises FileExistsError if wallet already exists and overwrite=False.
    """
    wdir = _wallet_path(wallet_dir)
    keyfile = _key_file(wdir)

    if keyfile.exists() and not overwrite:
        raise FileExistsError(f"Wallet already exists at {keyfile}. Use overwrite=True to replace.")

    priv = generate_private_key(SECP256K1(), default_backend())
    priv_int = priv.private_numbers().private_value
    priv_hex = priv_int.to_bytes(32, "big").hex()
    pub_bytes = priv.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_hex = pub_bytes.hex()
    address = _derive_address(pub_bytes)

    wdir.mkdir(parents=True, exist_ok=True)
    keyfile.write_text(json.dumps({
        "schema_version": 1,
        "curve": "secp256k1",
        "evm_compatible": _HAS_KECCAK,
        "address": address,
        "public_key": pub_hex,
        "private_key": priv_hex,
    }, indent=2))
    try:
        keyfile.chmod(0o600)
    except (AttributeError, NotImplementedError, OSError):
        pass  # Non-POSIX: skip permission hardening, file already written

    return {
        "status": "ok",
        "address": address,
        "public_key": pub_hex,
        "evm_compatible": _HAS_KECCAK,
        "path": str(keyfile),
    }


def wallet_show(wallet_dir: str | Path | None = None) -> dict:
    """Return public wallet info (address, public key). Never returns private key."""
    wdir = _wallet_path(wallet_dir)
    keyfile = _key_file(wdir)
    if not keyfile.exists():
        raise FileNotFoundError(f"No wallet at {keyfile}. Run: urace crypto wallet init")
    data = json.loads(keyfile.read_text())
    return {
        "status": "ok",
        "address": data["address"],
        "public_key": data["public_key"],
        "evm_compatible": data.get("evm_compatible", False),
        "path": str(keyfile),
    }


def wallet_sign(payload: str | bytes, wallet_dir: str | Path | None = None) -> dict:
    """
    Sign an arbitrary payload with the wallet's private key.
    Returns DER-encoded signature as hex + the sha256 digest that was signed.

    payload: str (UTF-8 encoded) or bytes.
    """
    wdir = _wallet_path(wallet_dir)
    keyfile = _key_file(wdir)
    if not keyfile.exists():
        raise FileNotFoundError(f"No wallet at {keyfile}. Run: urace crypto wallet init")

    data = json.loads(keyfile.read_text())
    priv_bytes = bytes.fromhex(data["private_key"])

    from cryptography.hazmat.primitives.asymmetric.ec import (
        EllipticCurvePrivateNumbers,
        EllipticCurvePublicNumbers,
        SECP256K1 as _SECP,
    )
    from cryptography.hazmat.primitives.asymmetric.ec import (
        generate_private_key as _gpk,
    )

    priv_int = int.from_bytes(priv_bytes, "big")
    pub_bytes_raw = bytes.fromhex(data["public_key"])
    x = int.from_bytes(pub_bytes_raw[1:33], "big")
    y = int.from_bytes(pub_bytes_raw[33:], "big")
    pub_numbers = EllipticCurvePublicNumbers(x, y, _SECP())
    priv_numbers = EllipticCurvePrivateNumbers(priv_int, pub_numbers)
    priv_key = priv_numbers.private_key(default_backend())

    raw = payload.encode() if isinstance(payload, str) else payload
    digest_hex = hashlib.sha256(raw).hexdigest()
    sig_der = priv_key.sign(raw, ECDSA(SHA256()))

    return {
        "status": "ok",
        "address": data["address"],
        "payload_sha256": digest_hex,
        "signature_der": sig_der.hex(),
        "algorithm": "ECDSA-secp256k1-SHA256",
    }


def wallet_rotate(wallet_dir: "str | Path | None" = None, backup_dir: "str | Path | None" = None) -> dict:
    """Generate a new keypair, back up the old one with chain-of-custody signature."""
    import time as _t
    _wdir = _wallet_path(wallet_dir)
    _key_path = _key_file(_wdir)
    if not _key_path.exists():
        raise FileNotFoundError("No wallet to rotate — run: urace crypto wallet init")

    old_data = json.loads(_key_path.read_text())
    old_address = old_data.get("address", "")

    # Back up old key
    _backup_dir = Path(backup_dir) if backup_dir else (_wdir / "archive")
    _backup_dir.mkdir(parents=True, exist_ok=True)
    ts = int(_t.time())
    backup_path = _backup_dir / f"key_retired_{ts}.json"
    backup_path.write_text(json.dumps({**old_data, "retired_at": ts}, indent=2), encoding="utf-8")
    try: backup_path.chmod(0o600)
    except (AttributeError, NotImplementedError, OSError): pass

    # Generate new keypair
    new_result = wallet_init(wallet_dir=_wdir, overwrite=True)

    # Sign new address with old key (chain of custody) — reload old key data for signing
    old_priv_bytes = bytes.fromhex(old_data["private_key"])
    custody_payload = json.dumps({"rotated_from": old_address, "rotated_to": new_result["address"], "at": ts}, sort_keys=True)

    from cryptography.hazmat.primitives.asymmetric.ec import (
        EllipticCurvePrivateNumbers,
        EllipticCurvePublicNumbers,
        SECP256K1 as _SECP2,
    )
    old_pub_bytes = bytes.fromhex(old_data["public_key"])
    ox = int.from_bytes(old_pub_bytes[1:33], "big")
    oy = int.from_bytes(old_pub_bytes[33:], "big")
    old_pub_numbers = EllipticCurvePublicNumbers(ox, oy, _SECP2())
    old_priv_numbers = EllipticCurvePrivateNumbers(int.from_bytes(old_priv_bytes, "big"), old_pub_numbers)
    old_priv_key = old_priv_numbers.private_key(default_backend())
    raw_payload = custody_payload.encode()
    custody_sig_der = old_priv_key.sign(raw_payload, ECDSA(SHA256()))

    return {
        "status": "ok",
        "old_address": old_address,
        "new_address": new_result["address"],
        "backup_path": str(backup_path),
        "custody_signature": custody_sig_der.hex(),
    }
