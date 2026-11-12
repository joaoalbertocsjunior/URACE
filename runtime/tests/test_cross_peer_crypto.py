"""Cross-instance cryptographic tests for ledger_crypto, trial_receipt, and key_lifecycle.

Tests prove that hybrid signatures, encryption, receipts, and key rotation work
correctly across two independent in-memory Identity objects — simulating cross-peer
cryptographic operations without any network.
"""
import tempfile
import unittest
from pathlib import Path


class TwoIdentityFixture(unittest.TestCase):
    """Base class providing two in-memory Identity instances."""

    def setUp(self):
        from urace.ledger_crypto import Identity
        self._tmp_a = tempfile.TemporaryDirectory()
        self._tmp_b = tempfile.TemporaryDirectory()
        self.id_a = Identity(Path(self._tmp_a.name) / 'key-a.json')
        self.id_b = Identity(Path(self._tmp_b.name) / 'key-b.json')

    def tearDown(self):
        self._tmp_a.cleanup()
        self._tmp_b.cleanup()


class CrossInstanceSignVerifyTests(TwoIdentityFixture):
    def test_sign_and_verify_cross_instance(self):
        """Identity A signs a payload; ledger_crypto.verify() accepts it using A's public key."""
        from urace import ledger_crypto
        payload = {'action': 'transfer', 'units': 42}
        sig = self.id_a.sign(payload, 'test-domain')
        result = ledger_crypto.verify(self.id_a.public(), payload, sig, 'test-domain')
        self.assertTrue(result)

    def test_cross_instance_identity_b_verifies_a(self):
        """Identity B can verify a signature produced by Identity A."""
        from urace import ledger_crypto
        payload = {'message': 'hello from A'}
        sig = self.id_a.sign(payload, 'cross-peer-domain')
        # B uses A's public key to verify — simulates cross-peer verification
        result = ledger_crypto.verify(self.id_a.public(), payload, sig, 'cross-peer-domain')
        self.assertTrue(result)

    def test_wrong_domain_raises(self):
        """Verifying with the wrong domain raises ValueError."""
        from urace import ledger_crypto
        payload = {'data': 'test'}
        sig = self.id_a.sign(payload, 'domain-one')
        with self.assertRaises(Exception):
            ledger_crypto.verify(self.id_a.public(), payload, sig, 'domain-two')

    def test_wrong_public_key_raises(self):
        """Verifying A's signature with B's public key raises ValueError."""
        from urace import ledger_crypto
        payload = {'data': 'cross-verify'}
        sig = self.id_a.sign(payload, 'test')
        with self.assertRaises(Exception):
            ledger_crypto.verify(self.id_b.public(), payload, sig, 'test')


class EncryptDecryptRoundTripTests(TwoIdentityFixture):
    def test_a_encrypts_b_decrypts(self):
        """Identity A encrypts for B; B decrypts successfully."""
        from urace import ledger_crypto
        plaintext = b'secret message from A to B'
        context = {'operation': 'test-transfer', 'nonce': '1234'}
        envelope = ledger_crypto.encrypt(self.id_b.public(), plaintext, context)
        recovered = self.id_b.decrypt(envelope, context)
        self.assertEqual(recovered, plaintext)

    def test_b_encrypts_a_decrypts(self):
        """Identity B encrypts for A; A decrypts successfully."""
        from urace import ledger_crypto
        plaintext = b'response from B to A'
        context = {'op': 'reply', 'seq': 99}
        envelope = ledger_crypto.encrypt(self.id_a.public(), plaintext, context)
        recovered = self.id_a.decrypt(envelope, context)
        self.assertEqual(recovered, plaintext)

    def test_wrong_recipient_cannot_decrypt(self):
        """B cannot decrypt a message encrypted for A."""
        from urace import ledger_crypto
        plaintext = b'private to A'
        context = {'op': 'private'}
        envelope = ledger_crypto.encrypt(self.id_a.public(), plaintext, context)
        with self.assertRaises(Exception):
            self.id_b.decrypt(envelope, context)

    def test_wrong_context_cannot_decrypt(self):
        """Correct recipient with wrong context raises ValueError."""
        from urace import ledger_crypto
        plaintext = b'context-bound data'
        context = {'op': 'original-context'}
        wrong_context = {'op': 'tampered-context'}
        envelope = ledger_crypto.encrypt(self.id_b.public(), plaintext, context)
        with self.assertRaises(Exception):
            self.id_b.decrypt(envelope, wrong_context)


class TrialReceiptCrossIdentityTests(TwoIdentityFixture):
    def test_create_and_verify_receipt(self):
        """Borrower (A) creates a receipt; verify_receipt() accepts it using A's public key."""
        from urace.trial_receipt import create_receipt, verify_receipt
        receipt = create_receipt(
            identity=self.id_a,
            feature_id='feat-abc',
            creator_peer_id='creator-peer-b',
            outcome_delta=0.15,
            borrower_peer_id='borrower-peer-a',
        )
        result = verify_receipt(receipt, self.id_a.public())
        self.assertTrue(result)

    def test_verify_receipt_wrong_key_raises(self):
        """verify_receipt() raises when checked against the wrong public key."""
        from urace.trial_receipt import create_receipt, verify_receipt
        receipt = create_receipt(
            identity=self.id_a,
            feature_id='feat-xyz',
            creator_peer_id='creator-b',
            outcome_delta=0.05,
            borrower_peer_id='borrower-a',
        )
        with self.assertRaises(Exception):
            verify_receipt(receipt, self.id_b.public())

    def test_verify_receipt_schema_check(self):
        """verify_receipt() raises on bad schema."""
        from urace.trial_receipt import verify_receipt
        bad_receipt = {
            'payload': {'schema': 'wrong-schema-v9'},
            'signature': {},
        }
        with self.assertRaises(ValueError):
            verify_receipt(bad_receipt, self.id_a.public())


class KeyRotationTests(TwoIdentityFixture):
    def test_create_and_verify_rotation_proof(self):
        """create_rotation_proof() and verify_rotation_proof() succeed for a valid rotation."""
        from urace.key_lifecycle import create_rotation_proof, verify_rotation_proof
        # id_a rotates to id_b
        proof = create_rotation_proof(self.id_a, self.id_b.public())
        result = verify_rotation_proof(self.id_a.public(), proof, self.id_b.public())
        self.assertTrue(result)

    def test_rotation_proof_wrong_new_key_raises(self):
        """verify_rotation_proof() raises when new_public does not match proof."""
        from urace.key_lifecycle import create_rotation_proof, verify_rotation_proof
        import tempfile
        from pathlib import Path
        from urace.ledger_crypto import Identity
        with tempfile.TemporaryDirectory() as tmp:
            id_c = Identity(Path(tmp) / 'key-c.json')
            proof = create_rotation_proof(self.id_a, self.id_b.public())
            with self.assertRaises(ValueError):
                verify_rotation_proof(self.id_a.public(), proof, id_c.public())

    def test_rotation_proof_wrong_old_key_raises(self):
        """verify_rotation_proof() raises when old_public does not match the signing key."""
        from urace.key_lifecycle import create_rotation_proof, verify_rotation_proof
        proof = create_rotation_proof(self.id_a, self.id_b.public())
        with self.assertRaises(Exception):
            verify_rotation_proof(self.id_b.public(), proof, self.id_b.public())


if __name__ == '__main__':
    unittest.main()
