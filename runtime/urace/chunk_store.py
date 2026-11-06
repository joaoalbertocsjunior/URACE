"""Erasure-coded artifact chunk store with per-chunk encryption.

Architecture (two separate systems):
  Economy ledger  (audit.jsonl)      — small, fully replicated to all peers, governs payments
  Artifact chunk DHT (bundle-chunks) — k-of-n encrypted shards, no single node holds a full feature

Security properties:
  - Each chunk is AES-256-GCM ciphertext; useless without the per-chunk key
  - Per-chunk keys derived from local artifact-seed.bin (creator's private material)
  - Replica holder nodes store ciphertext only — cannot read artifact content
  - DEK (master key) released to buyer only after EQUITY_LISTING_FILLED in economy ledger
  - Any k of (k+p) chunks reconstruct the artifact; up to p nodes can be offline

Reed-Solomon GF(256) arithmetic — pure Python, zero external dependencies.
Primitive polynomial: x^8 + x^4 + x^3 + x^2 + 1  (0x11D)
"""
import hashlib, hmac, json, os
from pathlib import Path

# ---------------------------------------------------------------------------
# GF(256) arithmetic
# ---------------------------------------------------------------------------

_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _gf_inv(x):
    if x == 0:
        raise ZeroDivisionError('GF(256) inverse of zero')
    return _EXP[255 - _LOG[x]]


def _gf_pow(x, p):
    return _EXP[(_LOG[x] * p) % 255] if x else 0


# ---------------------------------------------------------------------------
# Systematic Reed-Solomon encode/decode (column-per-byte approach)
# ---------------------------------------------------------------------------

def _rs_encode_block(data: bytes, n_data: int, n_parity: int) -> list:
    """Split data into n_data chunks, compute n_parity parity chunks.

    Returns list of (n_data + n_parity) bytes objects of equal chunk_size.
    Original length prepended as 8-byte big-endian header before RS encoding.
    """
    # Prepend 8-byte length header so reconstruction is self-describing
    payload = len(data).to_bytes(8, 'big') + data
    pad = (-len(payload)) % n_data
    padded = payload + bytes(pad)
    chunk_size = len(padded) // n_data
    chunks = [bytearray(padded[i * chunk_size:(i + 1) * chunk_size]) for i in range(n_data)]
    parity = [bytearray(chunk_size) for _ in range(n_parity)]

    # Vandermonde evaluation: parity[p][pos] = sum_j( alpha^((p+1)*j) * data[j][pos] )
    for pos in range(chunk_size):
        for p in range(n_parity):
            s = 0
            for j in range(n_data):
                s ^= _gf_mul(_gf_pow(2, (p + 1) * j), chunks[j][pos])
            parity[p][pos] = s

    return [bytes(c) for c in chunks] + [bytes(c) for c in parity]


def _rs_reconstruct_block(available: dict, n_data: int, n_parity: int) -> bytes:
    """Reconstruct original data from any n_data of (n_data+n_parity) chunks.

    available: {chunk_index: chunk_bytes}  — must have len >= n_data
    """
    if len(available) < n_data:
        raise ValueError(f'Need at least {n_data} chunks, got {len(available)}')

    indices = sorted(available.keys())[:n_data]

    # Fast path: all n_data data chunks present
    if set(indices) == set(range(n_data)):
        raw = b''.join(available[i] for i in range(n_data))
    else:
        # Gaussian elimination in GF(256) to solve for missing data chunks
        matrix = []
        for idx in indices:
            if idx < n_data:
                row = [1 if j == idx else 0 for j in range(n_data)]
            else:
                p = idx - n_data + 1
                row = [_gf_pow(2, p * j) for j in range(n_data)]
            matrix.append(row)

        rhs = [bytearray(available[i]) for i in indices]

        # RREF in GF(256): each rhs entry is a full chunk (chunk_size bytes)
        for col in range(n_data):
            pivot = None
            for row in range(col, n_data):
                if matrix[row][col] != 0:
                    pivot = row
                    break
            if pivot is None:
                raise ValueError('Singular matrix — insufficient independent chunks')
            if pivot != col:
                matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
                rhs[col], rhs[pivot] = rhs[pivot], rhs[col]
            inv = _gf_inv(matrix[col][col])
            matrix[col] = [_gf_mul(v, inv) for v in matrix[col]]
            rhs[col] = bytearray(_gf_mul(b, inv) for b in rhs[col])
            for row in range(n_data):
                if row != col and matrix[row][col] != 0:
                    factor = matrix[row][col]
                    matrix[row] = [matrix[row][j] ^ _gf_mul(factor, matrix[col][j])
                                   for j in range(n_data)]
                    # iterate all bytes in the chunk, not just n_data bytes
                    rhs[row] = bytearray(rhs[row][j] ^ _gf_mul(factor, rhs[col][j])
                                         for j in range(len(rhs[col])))

        raw = b''.join(bytes(rhs[i]) for i in range(n_data))

    # Recover original length from prepended 8-byte header
    orig_len = int.from_bytes(raw[:8], 'big')
    if 0 <= orig_len <= len(raw) - 8:
        return raw[8:8 + orig_len]
    return raw[8:]


# ---------------------------------------------------------------------------
# Per-chunk encryption
# ---------------------------------------------------------------------------

def _chunk_dek(exchange_root: Path, artifact_sha256: str) -> bytes:
    """Derive artifact-level master key from local private seed. Creator only."""
    seed_path = Path(exchange_root) / 'artifact-seed.bin'
    if not seed_path.exists():
        seed = os.urandom(32)
        fd = os.open(seed_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(seed)
            f.flush()
            os.fsync(f.fileno())
    else:
        seed = seed_path.read_bytes()
    # HKDF-SHA256: derive artifact-specific master key
    prk = hmac.new(b'URACE-ARTIFACT-SEED-v1', seed, 'sha256').digest()
    okm = hmac.new(prk, artifact_sha256.encode() + b'\x01', 'sha256').digest()
    return okm


def _chunk_key(master_dek: bytes, artifact_sha256: str, chunk_idx: int) -> bytes:
    """Derive per-chunk AES-256 key from master DEK."""
    info = f'{artifact_sha256}:chunk:{chunk_idx}'.encode()
    return hmac.new(master_dek, info + b'\x01', 'sha256').digest()


def _encrypt_chunk(key: bytes, plaintext: bytes, chunk_idx: int) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, f'urace-chunk-{chunk_idx}'.encode())
    return nonce + ct


def _decrypt_chunk(key: bytes, ciphertext: bytes, chunk_idx: int) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(ciphertext) < 13:
        raise ValueError('Ciphertext too short')
    nonce, ct = ciphertext[:12], ciphertext[12:]
    return AESGCM(key).decrypt(nonce, ct, f'urace-chunk-{chunk_idx}'.encode())


# ---------------------------------------------------------------------------
# ChunkStore
# ---------------------------------------------------------------------------

DEFAULT_N_DATA = 4
DEFAULT_N_PARITY = 2


def get_artifact_dek(exchange_root, artifact_sha256: str) -> bytes:
    """Return the master DEK for an artifact. Creator only (requires artifact-seed.bin)."""
    return _chunk_dek(exchange_root, artifact_sha256)


class ChunkStore:
    """Erasure-coded encrypted artifact storage.

    Each artifact is split into n_data + n_parity encrypted chunks.
    Any n_data chunks reconstruct the original — up to n_parity nodes can be offline.
    Chunk bytes are ciphertext: replica holders cannot read content without the DEK.

    Storage layout:
        <exchange_root>/bundle-chunks/<sha256[:2]>/<sha256>/chunk-NNN.bin
        <exchange_root>/bundle-chunks/<sha256[:2]>/<sha256>/manifest.json
    """

    def __init__(self, exchange_root):
        self.root = Path(exchange_root)

    def _chunk_dir(self, artifact_sha256: str) -> Path:
        return self.root / 'bundle-chunks' / artifact_sha256[:2] / artifact_sha256

    def _manifest_path(self, artifact_sha256: str) -> Path:
        return self._chunk_dir(artifact_sha256) / 'manifest.json'

    def store(self, artifact_sha256: str, raw_bytes: bytes,
              n_data: int = DEFAULT_N_DATA, n_parity: int = DEFAULT_N_PARITY) -> dict:
        """Encrypt-then-erasure-code artifact. Idempotent."""
        if self._manifest_path(artifact_sha256).exists():
            return json.loads(self._manifest_path(artifact_sha256).read_text())

        chunk_dir = self._chunk_dir(artifact_sha256)
        chunk_dir.mkdir(parents=True, exist_ok=True)

        dek = _chunk_dek(self.root, artifact_sha256)
        chunks = _rs_encode_block(raw_bytes, n_data, n_parity)
        chunk_hashes = []

        for i, chunk_data in enumerate(chunks):
            key = _chunk_key(dek, artifact_sha256, i)
            enc = _encrypt_chunk(key, chunk_data, i)
            cpath = chunk_dir / f'chunk-{i:03d}.bin'
            cpath.write_bytes(enc)
            os.chmod(cpath, 0o600)
            chunk_hashes.append(hashlib.sha256(enc).hexdigest())

        manifest = {
            'schema': 'urace-chunk-manifest-v1',
            'artifact_sha256': artifact_sha256,
            'artifact_size_bytes': len(raw_bytes),
            'n_data': n_data,
            'n_parity': n_parity,
            'n_total': n_data + n_parity,
            'chunk_hashes': chunk_hashes,
            'chunk_size_bytes': len(chunks[0]),
        }
        self._manifest_path(artifact_sha256).write_text(json.dumps(manifest, indent=2))
        return manifest

    def load(self, artifact_sha256: str) -> bytes | None:
        """Reconstruct artifact from locally held chunks. Returns None if insufficient."""
        mp = self._manifest_path(artifact_sha256)
        if not mp.exists():
            return None
        manifest = json.loads(mp.read_text())
        n_data = manifest['n_data']
        n_parity = manifest['n_parity']
        dek = _chunk_dek(self.root, artifact_sha256)
        chunk_dir = self._chunk_dir(artifact_sha256)

        available = {}
        for i in range(manifest['n_total']):
            cpath = chunk_dir / f'chunk-{i:03d}.bin'
            if cpath.exists():
                try:
                    key = _chunk_key(dek, artifact_sha256, i)
                    available[i] = _decrypt_chunk(key, cpath.read_bytes(), i)
                except Exception:
                    pass  # corrupt or wrong key — skip

        if len(available) < n_data:
            return None
        try:
            return _rs_reconstruct_block(available, n_data, n_parity)
        except Exception:
            return None

    def has_chunks(self, artifact_sha256: str) -> list:
        """Return list of locally held chunk indices."""
        mp = self._manifest_path(artifact_sha256)
        if not mp.exists():
            return []
        manifest = json.loads(mp.read_text())
        chunk_dir = self._chunk_dir(artifact_sha256)
        return [i for i in range(manifest['n_total'])
                if (chunk_dir / f'chunk-{i:03d}.bin').exists()]

    def get_chunk_bytes(self, artifact_sha256: str, chunk_idx: int) -> bytes | None:
        """Return raw encrypted chunk bytes for P2P distribution.
        Replica holder receives these — ciphertext only, cannot decrypt without creator DEK.
        """
        mp = self._manifest_path(artifact_sha256)
        if not mp.exists():
            return None
        cpath = self._chunk_dir(artifact_sha256) / f'chunk-{chunk_idx:03d}.bin'
        return cpath.read_bytes() if cpath.exists() else None

    def store_chunk(self, artifact_sha256: str, chunk_idx: int,
                    encrypted_chunk: bytes, manifest: dict) -> None:
        """Store a received encrypted chunk from another peer. Verifies integrity hash."""
        expected = manifest['chunk_hashes'][chunk_idx]
        actual = hashlib.sha256(encrypted_chunk).hexdigest()
        if actual != expected:
            raise ValueError(f'Chunk {chunk_idx} hash mismatch: expected {expected}, got {actual}')
        chunk_dir = self._chunk_dir(artifact_sha256)
        chunk_dir.mkdir(parents=True, exist_ok=True)
        if not self._manifest_path(artifact_sha256).exists():
            self._manifest_path(artifact_sha256).write_text(json.dumps(manifest, indent=2))
        cpath = chunk_dir / f'chunk-{chunk_idx:03d}.bin'
        if not cpath.exists():
            cpath.write_bytes(encrypted_chunk)
            os.chmod(cpath, 0o600)

    def manifest(self, artifact_sha256: str) -> dict | None:
        mp = self._manifest_path(artifact_sha256)
        return json.loads(mp.read_text()) if mp.exists() else None

    def is_reconstructable(self, artifact_sha256: str) -> bool:
        mp = self._manifest_path(artifact_sha256)
        if not mp.exists():
            return False
        m = json.loads(mp.read_text())
        return len(self.has_chunks(artifact_sha256)) >= m['n_data']
