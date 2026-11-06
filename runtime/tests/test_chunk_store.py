"""Tests for RS erasure-coded chunk store."""
import hashlib, os, tempfile, unittest
import pytest
from pathlib import Path


def _root():
    return Path(tempfile.mkdtemp())


class RSErasureCodingTests(unittest.TestCase):
    def test_encode_decode_all_chunks(self):
        from urace.chunk_store import _rs_encode_block, _rs_reconstruct_block
        data = b'hello world erasure coding test payload' * 20
        chunks = _rs_encode_block(data, 4, 2)
        assert len(chunks) == 6
        available = {i: chunks[i] for i in range(6)}
        assert _rs_reconstruct_block(available, 4, 2) == data

    def test_reconstruct_minimum_data_chunks(self):
        from urace.chunk_store import _rs_encode_block, _rs_reconstruct_block
        data = bytes(range(256)) * 8
        chunks = _rs_encode_block(data, 4, 2)
        available = {i: chunks[i] for i in range(4)}
        assert _rs_reconstruct_block(available, 4, 2) == data

    def test_reconstruct_missing_one_data_chunk(self):
        from urace.chunk_store import _rs_encode_block, _rs_reconstruct_block
        data = b'artifact data for erasure test ' * 30
        chunks = _rs_encode_block(data, 4, 2)
        available = {i: chunks[i] for i in [1, 2, 3, 4]}  # drop chunk 0, use 1 parity
        assert _rs_reconstruct_block(available, 4, 2) == data

    def test_reconstruct_missing_two_data_chunks(self):
        from urace.chunk_store import _rs_encode_block, _rs_reconstruct_block
        data = b'test payload ' * 60
        chunks = _rs_encode_block(data, 4, 2)
        available = {i: chunks[i] for i in [2, 3, 4, 5]}  # 2 data + 2 parity
        assert _rs_reconstruct_block(available, 4, 2) == data

    def test_insufficient_chunks_raises(self):
        from urace.chunk_store import _rs_encode_block, _rs_reconstruct_block
        data = b'short ' * 50
        chunks = _rs_encode_block(data, 4, 2)
        available = {i: chunks[i] for i in range(3)}
        with pytest.raises((AssertionError, ValueError)):
            _rs_reconstruct_block(available, 4, 2)

    def test_various_data_sizes(self):
        from urace.chunk_store import _rs_encode_block, _rs_reconstruct_block
        for size in [1, 7, 16, 100, 1023, 4096, 10000]:
            data = os.urandom(size)
            chunks = _rs_encode_block(data, 4, 2)
            available = {i: chunks[i] for i in range(4)}
            assert _rs_reconstruct_block(available, 4, 2) == data, f'failed for size={size}'

    def test_binary_data(self):
        from urace.chunk_store import _rs_encode_block, _rs_reconstruct_block
        data = bytes(range(256)) * 100
        chunks = _rs_encode_block(data, 4, 2)
        available = {i: chunks[i] for i in [0, 1, 3, 4]}  # skip chunk 2
        assert _rs_reconstruct_block(available, 4, 2) == data


class ChunkStoreTests(unittest.TestCase):
    def test_store_and_load(self):
        from urace.chunk_store import ChunkStore
        cs = ChunkStore(_root())
        data = b'chunk store integration test' * 100
        sha = hashlib.sha256(data).hexdigest()
        mf = cs.store(sha, data)
        assert mf['n_data'] == 4
        assert mf['n_total'] == 6
        assert cs.load(sha) == data

    def test_store_idempotent(self):
        from urace.chunk_store import ChunkStore
        cs = ChunkStore(_root())
        data = b'idempotent test data' * 50
        sha = hashlib.sha256(data).hexdigest()
        cs.store(sha, data)
        cs.store(sha, data)
        assert cs.load(sha) == data

    def test_has_chunks(self):
        from urace.chunk_store import ChunkStore
        cs = ChunkStore(_root())
        data = b'chunk presence test' * 80
        sha = hashlib.sha256(data).hexdigest()
        cs.store(sha, data)
        held = cs.has_chunks(sha)
        assert len(held) == 6
        assert set(held) == {0, 1, 2, 3, 4, 5}

    def test_chunk_bytes_are_ciphertext(self):
        from urace.chunk_store import ChunkStore
        cs = ChunkStore(_root())
        data = b'secret artifact content that must not be readable by holder' * 100
        sha = hashlib.sha256(data).hexdigest()
        cs.store(sha, data)
        enc = cs.get_chunk_bytes(sha, 0)
        assert enc is not None
        assert data[:20] not in enc  # ciphertext — not plaintext

    def test_load_returns_none_when_missing(self):
        from urace.chunk_store import ChunkStore
        cs = ChunkStore(_root())
        assert cs.load('a' * 64) is None

    def test_cross_node_chunk_transfer(self):
        from urace.chunk_store import ChunkStore
        root1, root2 = _root(), _root()
        cs1, cs2 = ChunkStore(root1), ChunkStore(root2)
        data = b'cross-node chunk transfer ' * 100
        sha = hashlib.sha256(data).hexdigest()
        mf = cs1.store(sha, data)
        # Transfer chunk 0 from cs1 to cs2
        enc = cs1.get_chunk_bytes(sha, 0)
        cs2.store_chunk(sha, 0, enc, mf)
        assert 0 in cs2.has_chunks(sha)

    def test_tampered_chunk_rejected(self):
        from urace.chunk_store import ChunkStore
        root1, root2 = _root(), _root()
        cs1, cs2 = ChunkStore(root1), ChunkStore(root2)
        data = b'tamper detection test' * 200
        sha = hashlib.sha256(data).hexdigest()
        mf = cs1.store(sha, data)
        enc = bytearray(cs1.get_chunk_bytes(sha, 0))
        enc[20] ^= 0xFF
        with pytest.raises(ValueError, match='hash mismatch'):
            cs2.store_chunk(sha, 0, bytes(enc), mf)

    def test_large_artifact(self):
        from urace.chunk_store import ChunkStore
        cs = ChunkStore(_root())
        data = os.urandom(1024 * 512)  # 512 KB
        sha = hashlib.sha256(data).hexdigest()
        cs.store(sha, data)
        assert cs.load(sha) == data

    def test_is_reconstructable(self):
        from urace.chunk_store import ChunkStore
        cs = ChunkStore(_root())
        data = b'reconstructable test' * 100
        sha = hashlib.sha256(data).hexdigest()
        assert not cs.is_reconstructable(sha)
        cs.store(sha, data)
        assert cs.is_reconstructable(sha)

    def test_manifest_fields(self):
        from urace.chunk_store import ChunkStore
        cs = ChunkStore(_root())
        data = b'manifest test' * 100
        sha = hashlib.sha256(data).hexdigest()
        mf = cs.store(sha, data)
        assert mf['schema'] == 'urace-chunk-manifest-v1'
        assert mf['artifact_sha256'] == sha
        assert mf['artifact_size_bytes'] == len(data)
        assert len(mf['chunk_hashes']) == 6
