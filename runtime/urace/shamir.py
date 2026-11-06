"""Shamir's Secret Sharing over GF(256) — URACE v3 DEK distribution protocol.

Each byte of the secret is shared independently via a degree-(k-1) polynomial
over GF(256) with constant term equal to the secret byte.

Primitive polynomial: x^8+x^4+x^3+x^2+1 (0x11D) — shared with chunk_store.
"""
import hashlib
import os

from .chunk_store import _gf_mul, _gf_inv

SCHEMA = 'urace-shamir-v1'
MAX_SHARES = 254  # GF(256) has 255 non-zero elements; use x in 1..254


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def split(secret: bytes, k: int, n: int) -> list:
    """Split *secret* into *n* shares; any *k* of them reconstruct the secret.

    Returns list of (x, share_bytes) for x in 1..n.
    k: threshold (minimum shares needed to reconstruct)
    n: total shares to generate  (1 <= k <= n <= MAX_SHARES)
    """
    if not secret:
        raise ValueError('secret must be non-empty')
    if k < 1:
        raise ValueError(f'k must be >= 1, got {k}')
    if n > MAX_SHARES:
        raise ValueError(f'n must be <= MAX_SHARES ({MAX_SHARES}), got {n}')
    if k > n:
        raise ValueError(f'k ({k}) must be <= n ({n})')

    length = len(secret)
    # For each byte position generate a random degree-(k-1) polynomial whose
    # constant term is the secret byte.  Store evaluations for x in 1..n.
    share_arrays = [bytearray(length) for _ in range(n)]

    random_pool = os.urandom(length * (k - 1)) if k > 1 else b''

    for pos in range(length):
        # Coefficients: coeffs[0] = secret byte, rest random
        coeffs = [secret[pos]]
        for d in range(1, k):
            coeffs.append(random_pool[(d - 1) * length + pos])

        for xi in range(1, n + 1):  # x values 1..n
            # Horner's method: f(x) = coeffs[0] + coeffs[1]*x + ... + coeffs[k-1]*x^(k-1)
            val = 0
            for coeff in reversed(coeffs):
                val = _gf_mul(val, xi) ^ coeff
            share_arrays[xi - 1][pos] = val

    return [(xi, bytes(share_arrays[xi - 1])) for xi in range(1, n + 1)]


def reconstruct(shares: list) -> bytes:
    """Reconstruct secret from *shares* using Lagrange interpolation at x=0.

    shares: [(x, share_bytes)] — must have len >= k
    Raises ValueError if x coords repeat or any x==0.
    """
    if not shares:
        raise ValueError('shares list must be non-empty')

    xs = [s[0] for s in shares]

    # Validate x coords
    for x in xs:
        if x == 0:
            raise ValueError('share x coordinate must not be 0')
    if len(xs) != len(set(xs)):
        raise ValueError('duplicate share x coordinates')

    share_len = len(shares[0][1])
    result = bytearray(share_len)

    for pos in range(share_len):
        ys = [s[1][pos] for s in shares]
        # Lagrange interpolation at x=0
        # f(0) = sum_i [ y_i * prod_{j!=i}( x_j / (x_i XOR x_j) ) ]
        secret_byte = 0
        for i, (xi, _) in enumerate(shares):
            yi = ys[i]
            if yi == 0:
                # term contributes 0 regardless of basis polynomial
                continue
            # Compute basis polynomial L_i(0)
            num = 1  # product of x_j  for j!=i  (since 0 - x_j = x_j in GF)
            den = 1  # product of (x_i XOR x_j) for j!=i
            for j, (xj, _) in enumerate(shares):
                if j == i:
                    continue
                num = _gf_mul(num, xj)
                den = _gf_mul(den, xi ^ xj)
            basis = _gf_mul(num, _gf_inv(den))
            secret_byte ^= _gf_mul(yi, basis)
        result[pos] = secret_byte

    return bytes(result)


def share_commitment(share_bytes: bytes) -> str:
    """SHA-256 hex digest of share_bytes — stored on audit chain as commitment."""
    return hashlib.sha256(share_bytes).hexdigest()
