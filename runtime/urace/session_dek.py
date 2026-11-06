"""session_dek.py — Session-bound DEK wrapping for blackmarket protection.

Each DEK is wrapped with the buyer's ephemeral X25519 public key so that
the wrapped_dek stored in ARTIFACT_KEY_GRANT is useless without the matching
private key.

Wire format (all concatenated, no framing):
  ephemeral_public_bytes (32 bytes)
  nonce                  (12 bytes)
  ciphertext             (len(dek) bytes)
  tag                    (16 bytes)
"""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
    load_pem_private_key,
    load_pem_public_key,
)
import os

_HKDF_INFO = b"URACE-DEK-WRAP-v1"
_EPHEMERAL_PUB_LEN = 32
_NONCE_LEN = 12
_TAG_LEN = 16


def generate_buyer_keypair() -> tuple[bytes, bytes]:
    """Return (private_key_pem, public_key_pem) as PEM bytes (X25519)."""
    priv = X25519PrivateKey.generate()
    priv_pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    pub_pem = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return priv_pem, pub_pem


def _derive_wrap_key(shared_secret: bytes) -> bytes:
    """HKDF-SHA256 over shared_secret → 32-byte AES-256 key."""
    return HKDF(
        algorithm=SHA256(),
        length=32,
        salt=None,
        info=_HKDF_INFO,
    ).derive(shared_secret)


def wrap_dek(dek_bytes: bytes, buyer_public_key_pem: bytes) -> bytes:
    """Wrap *dek_bytes* for *buyer_public_key_pem*.

    Returns: ephemeral_pub(32) || nonce(12) || ciphertext+tag (len(dek)+16)
    """
    buyer_pub = load_pem_public_key(buyer_public_key_pem)
    ephemeral_priv = X25519PrivateKey.generate()
    ephemeral_pub_raw = ephemeral_priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    shared_secret = ephemeral_priv.exchange(buyer_pub)
    wrap_key = _derive_wrap_key(shared_secret)

    nonce = os.urandom(_NONCE_LEN)
    aesgcm = AESGCM(wrap_key)
    ciphertext_tag = aesgcm.encrypt(nonce, dek_bytes, None)  # includes GCM tag

    return ephemeral_pub_raw + nonce + ciphertext_tag


def unwrap_dek(wrapped_dek: bytes, buyer_private_key_pem: bytes) -> bytes:
    """Reverse *wrap_dek*.  Raises ValueError on authentication failure."""
    if len(wrapped_dek) < _EPHEMERAL_PUB_LEN + _NONCE_LEN + _TAG_LEN:
        raise ValueError("wrapped_dek too short")

    ephemeral_pub_raw = wrapped_dek[:_EPHEMERAL_PUB_LEN]
    nonce = wrapped_dek[_EPHEMERAL_PUB_LEN:_EPHEMERAL_PUB_LEN + _NONCE_LEN]
    ciphertext_tag = wrapped_dek[_EPHEMERAL_PUB_LEN + _NONCE_LEN:]

    buyer_priv = load_pem_private_key(buyer_private_key_pem, password=None)

    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
    ephemeral_pub = X25519PublicKey.from_public_bytes(ephemeral_pub_raw)

    shared_secret = buyer_priv.exchange(ephemeral_pub)
    wrap_key = _derive_wrap_key(shared_secret)

    aesgcm = AESGCM(wrap_key)
    try:
        return aesgcm.decrypt(nonce, ciphertext_tag, None)
    except Exception as exc:
        raise ValueError(f"DEK unwrap failed (wrong key or corrupt data): {exc}") from exc
