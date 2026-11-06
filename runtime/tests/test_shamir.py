"""Tests for Shamir's Secret Sharing over GF(256) — urace.shamir"""
import hashlib
import itertools
import os
import unittest

from urace.shamir import MAX_SHARES, SCHEMA, reconstruct, share_commitment, split


class ShamirSplitReconstructTests(unittest.TestCase):

    def test_split_produces_n_shares(self):
        secret = b'hello world sss!'
        shares = split(secret, k=3, n=5)
        self.assertEqual(len(shares), 5)
        # each share has correct length
        for x, sb in shares:
            self.assertEqual(len(sb), len(secret))

    def test_reconstruct_from_exactly_k(self):
        secret = b'threshold test!!'
        shares = split(secret, k=3, n=5)
        # first k=3 shares
        result = reconstruct(shares[:3])
        self.assertEqual(result, secret)

    def test_reconstruct_any_k_subset(self):
        secret = b'any subset works'
        shares = split(secret, k=3, n=5)
        # test all C(5,3) = 10 subsets
        for combo in itertools.combinations(shares, 3):
            result = reconstruct(list(combo))
            self.assertEqual(result, secret, f'failed for combo {[c[0] for c in combo]}')

    def test_reconstruct_all_shares_works(self):
        secret = b'all shares ok!!!'
        shares = split(secret, k=3, n=5)
        result = reconstruct(shares)
        self.assertEqual(result, secret)

    def test_different_splits_differ(self):
        secret = b'random poly test'
        shares1 = split(secret, k=3, n=5)
        shares2 = split(secret, k=3, n=5)
        # Extremely unlikely (1/256^16 per share) that two random splits match
        share_bytes1 = [sb for _, sb in shares1]
        share_bytes2 = [sb for _, sb in shares2]
        self.assertNotEqual(share_bytes1, share_bytes2)

    def test_various_secret_sizes(self):
        for size in [1, 16, 32, 64, 100]:
            secret = os.urandom(size)
            shares = split(secret, k=3, n=5)
            result = reconstruct(shares[:3])
            self.assertEqual(result, secret, f'failed for size {size}')

    def test_binary_secret(self):
        secret = bytes(range(256))
        shares = split(secret, k=3, n=5)
        result = reconstruct(shares[:3])
        self.assertEqual(result, secret)

    def test_k_equals_1_always_reconstructible(self):
        secret = b'k=1 means any share works'
        shares = split(secret, k=1, n=5)
        for single_share in shares:
            result = reconstruct([single_share])
            self.assertEqual(result, secret)

    def test_k_equals_n_all_required(self):
        secret = b'k=n requires all!'
        shares = split(secret, k=5, n=5)
        # Using all 5 works
        result = reconstruct(shares)
        self.assertEqual(result, secret)
        # Using k-1=4 should NOT reconstruct correctly (wrong polynomial eval)
        # (not guaranteed to raise, but result must differ from secret)
        result_partial = reconstruct(shares[:4])
        self.assertNotEqual(result_partial, secret)


class ShamirEdgeCasesTests(unittest.TestCase):

    def test_invalid_k_greater_than_n(self):
        with self.assertRaises(ValueError):
            split(b'secret', k=5, n=3)

    def test_invalid_n_exceeds_max(self):
        with self.assertRaises(ValueError):
            split(b'secret', k=1, n=255)

    def test_invalid_k_zero(self):
        with self.assertRaises(ValueError):
            split(b'secret', k=0, n=5)

    def test_empty_secret_raises(self):
        with self.assertRaises(ValueError):
            split(b'', k=2, n=3)

    def test_duplicate_share_index_raises(self):
        secret = b'dup index test!!'
        shares = split(secret, k=2, n=3)
        # Inject a duplicate x
        dup_shares = [shares[0], shares[0]]
        with self.assertRaises(ValueError):
            reconstruct(dup_shares)

    def test_share_index_zero_raises(self):
        secret = b'zero index test!'
        shares = split(secret, k=2, n=3)
        # Replace first share's x with 0
        bad_shares = [(0, shares[0][1]), shares[1]]
        with self.assertRaises(ValueError):
            reconstruct(bad_shares)

    def test_share_commitment_is_sha256(self):
        data = b'\x01' * 32
        expected = hashlib.sha256(data).hexdigest()
        self.assertEqual(share_commitment(data), expected)


class ShamirDEKTests(unittest.TestCase):
    """Realistic 32-byte DEK usage scenarios."""

    def test_32_byte_dek_roundtrip(self):
        dek = os.urandom(32)
        shares = split(dek, k=3, n=5)
        result = reconstruct(shares[:3])
        self.assertEqual(result, dek)

    def test_k3_n5_dek_distribution(self):
        """k=3, n=5 — realistic replica distribution (any 3 of 5 replicas suffice)."""
        dek = os.urandom(32)
        shares = split(dek, k=3, n=5)
        self.assertEqual(len(shares), 5)
        # Verify x coords are 1..5
        self.assertEqual([x for x, _ in shares], [1, 2, 3, 4, 5])
        # Every combination of 3 must reconstruct
        for combo in itertools.combinations(shares, 3):
            self.assertEqual(reconstruct(list(combo)), dek)

    def test_commitments_match_shares(self):
        dek = os.urandom(32)
        shares = split(dek, k=3, n=5)
        for x, sb in shares:
            committed = share_commitment(sb)
            # Commitment is a 64-char hex string
            self.assertEqual(len(committed), 64)
            # Recomputing gives the same value
            self.assertEqual(share_commitment(sb), committed)
            # Different share → different commitment (practically certain)
        commitments = [share_commitment(sb) for _, sb in shares]
        self.assertEqual(len(set(commitments)), 5)

    def test_schema_constant(self):
        self.assertEqual(SCHEMA, 'urace-shamir-v1')

    def test_max_shares_constant(self):
        self.assertEqual(MAX_SHARES, 254)
