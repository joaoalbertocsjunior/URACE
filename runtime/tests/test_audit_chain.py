"""Tests for emit_audit_record and verify_audit_chain."""
import unittest


class TestEmitAuditRecord(unittest.TestCase):
    def test_basic(self):
        from urace.peer_exchange import emit_audit_record, AUDIT_CHAIN_RECORD
        exchange = []
        rec = emit_audit_record(exchange, "CREATE", "actor-1", "abc123")
        self.assertEqual(rec['kind'], AUDIT_CHAIN_RECORD)
        self.assertEqual(rec['operation'], "CREATE")
        self.assertIn('record_hash', rec)

    def test_hash_deterministic(self):
        from urace.peer_exchange import emit_audit_record
        import hashlib, json
        exchange = []
        rec = emit_audit_record(exchange, "READ", "actor-2", "def456", prior_hash="0"*64)
        check = {k: v for k, v in rec.items() if k != 'record_hash'}
        expected = hashlib.sha256(
            json.dumps(check, sort_keys=True, separators=(',', ':')).encode()
        ).hexdigest()
        self.assertEqual(rec['record_hash'], expected)

    def test_prior_hash_stored(self):
        from urace.peer_exchange import emit_audit_record
        exchange = []
        rec = emit_audit_record(exchange, "UPDATE", "a", "d", prior_hash="prev-hash")
        self.assertEqual(rec['prior_hash'], "prev-hash")

    def test_appends(self):
        from urace.peer_exchange import emit_audit_record
        exchange = []
        emit_audit_record(exchange, "A", "a", "x")
        emit_audit_record(exchange, "B", "b", "y")
        self.assertEqual(len(exchange), 2)


class TestVerifyAuditChain(unittest.TestCase):
    def test_empty(self):
        from urace.peer_exchange import verify_audit_chain
        ok, broken = verify_audit_chain([])
        self.assertTrue(ok)
        self.assertEqual(broken, -1)

    def test_valid_chain(self):
        from urace.peer_exchange import emit_audit_record, verify_audit_chain
        exchange = []
        emit_audit_record(exchange, "A", "actor", "digest1")
        emit_audit_record(exchange, "B", "actor", "digest2")
        ok, broken = verify_audit_chain(exchange)
        self.assertTrue(ok)

    def test_tampered_record(self):
        from urace.peer_exchange import emit_audit_record, verify_audit_chain
        exchange = []
        rec = emit_audit_record(exchange, "A", "actor", "digest1")
        exchange[0]['operation'] = "TAMPERED"
        ok, broken = verify_audit_chain(exchange)
        self.assertFalse(ok)
        self.assertEqual(broken, 0)

    def test_ignores_non_audit(self):
        from urace.peer_exchange import verify_audit_chain
        records = [{'kind': 'OTHER', 'data': 'stuff'}]
        ok, broken = verify_audit_chain(records)
        self.assertTrue(ok)


if __name__ == '__main__':
    unittest.main()
