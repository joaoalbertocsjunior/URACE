import os
import pathlib
import tempfile
import unittest
from urace.signed_records import (
    SignedRecord, sign_node_record, verify_node_record, persist_node_identity,
)


class SignedRecordsTests(unittest.TestCase):

    def _key(self):
        return os.urandom(32)

    def test_sign_and_verify_roundtrip(self):
        key = self._key()
        rec = sign_node_record('peer-1', b'hello', seq=1, key=key)
        self.assertTrue(verify_node_record(rec, key))

    def test_wrong_key_fails_verification(self):
        rec = sign_node_record('peer-1', b'hello', seq=1, key=self._key())
        self.assertFalse(verify_node_record(rec, self._key()))

    def test_tampered_payload_fails_verification(self):
        key = self._key()
        rec = sign_node_record('peer-1', b'hello', seq=1, key=key)
        tampered = SignedRecord(
            peer_id=rec.peer_id, payload=b'tampered',
            seq=rec.seq, signature=rec.signature, signed_at=rec.signed_at,
        )
        self.assertFalse(verify_node_record(tampered, key))

    def test_different_seq_fails_verification(self):
        key = self._key()
        rec = sign_node_record('peer-1', b'hello', seq=1, key=key)
        tampered = SignedRecord(
            peer_id=rec.peer_id, payload=rec.payload,
            seq=2, signature=rec.signature, signed_at=rec.signed_at,
        )
        self.assertFalse(verify_node_record(tampered, key))

    def test_persist_returns_stable_key(self):
        with tempfile.TemporaryDirectory() as d:
            k1 = persist_node_identity(d, 'peer-1')
            k2 = persist_node_identity(d, 'peer-1')
            self.assertEqual(k1, k2)
            self.assertEqual(len(k1), 32)

    def test_persist_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            persist_node_identity(d, 'peer-1')
            self.assertTrue((pathlib.Path(d) / 'node_identity.key').exists())
