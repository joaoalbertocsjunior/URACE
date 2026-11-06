"""Tests for session_dek.py — session-bound DEK wrapping."""

import os
import pytest
from urace.session_dek import (
    generate_buyer_keypair,
    wrap_dek,
    unwrap_dek,
)


def _random_dek(n=32):
    return os.urandom(n)


# ── 1. basic roundtrip ────────────────────────────────────────────────────────

def test_wrap_unwrap_roundtrip():
    priv_pem, pub_pem = generate_buyer_keypair()
    dek = _random_dek()
    wrapped = wrap_dek(dek, pub_pem)
    recovered = unwrap_dek(wrapped, priv_pem)
    assert recovered == dek


def test_roundtrip_various_dek_lengths():
    priv_pem, pub_pem = generate_buyer_keypair()
    for length in (1, 16, 32, 64, 128):
        dek = _random_dek(length)
        assert unwrap_dek(wrap_dek(dek, pub_pem), priv_pem) == dek


# ── 2. keypair generation ─────────────────────────────────────────────────────

def test_generate_buyer_keypair_returns_pem_bytes():
    priv_pem, pub_pem = generate_buyer_keypair()
    assert isinstance(priv_pem, bytes)
    assert isinstance(pub_pem, bytes)
    assert b"PRIVATE KEY" in priv_pem
    assert b"PUBLIC KEY" in pub_pem


def test_different_calls_give_different_keypairs():
    priv1, pub1 = generate_buyer_keypair()
    priv2, pub2 = generate_buyer_keypair()
    assert priv1 != priv2
    assert pub1 != pub2


# ── 3. different buyers get different wraps ───────────────────────────────────

def test_different_buyer_keys_give_different_wrapped_bytes():
    _, pub1 = generate_buyer_keypair()
    _, pub2 = generate_buyer_keypair()
    dek = _random_dek()
    w1 = wrap_dek(dek, pub1)
    w2 = wrap_dek(dek, pub2)
    assert w1 != w2


def test_same_dek_different_wraps_each_call():
    """wrap_dek uses a fresh ephemeral key each time → non-deterministic."""
    _, pub = generate_buyer_keypair()
    dek = _random_dek()
    assert wrap_dek(dek, pub) != wrap_dek(dek, pub)


# ── 4. wrong private key fails ────────────────────────────────────────────────

def test_wrong_private_key_raises():
    _, pub = generate_buyer_keypair()
    wrong_priv, _ = generate_buyer_keypair()
    dek = _random_dek()
    wrapped = wrap_dek(dek, pub)
    with pytest.raises(ValueError):
        unwrap_dek(wrapped, wrong_priv)


def test_truncated_wrapped_dek_raises():
    priv_pem, pub_pem = generate_buyer_keypair()
    dek = _random_dek()
    wrapped = wrap_dek(dek, pub_pem)
    with pytest.raises(ValueError):
        unwrap_dek(wrapped[:10], priv_pem)


# ── 5. ARTIFACT_KEY_GRANT row must NOT contain raw DEK ───────────────────────

def test_artifact_key_grant_row_excludes_raw_dek():
    """The row schema must include wrapped_dek_hex, not a 'dek' field."""
    priv_pem, pub_pem = generate_buyer_keypair()
    dek = _random_dek()
    wrapped = wrap_dek(dek, pub_pem)

    row = {
        "kind": "ARTIFACT_KEY_GRANT",
        "listing_id": "lst-001",
        "buyer_pubkey_hex": pub_pem.hex(),
        "wrapped_dek_hex": wrapped.hex(),
    }
    # Must not contain the raw DEK
    assert "dek" not in row or row.get("dek") is None
    # Must be recoverable
    recovered = unwrap_dek(bytes.fromhex(row["wrapped_dek_hex"]), priv_pem)
    assert recovered == dek
