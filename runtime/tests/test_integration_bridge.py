"""Tests for integration_bridge.py adapter pattern and on-chain attestation stubs."""
import unittest


class MockExchange:
    def __init__(self):
        self._rows = []

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)


class TestChainAdapterInterface(unittest.TestCase):
    """ChainAdapter base class raises NotImplementedError — documents the interface contract."""

    def setUp(self):
        from urace._chain_adapter_base import ChainAdapter
        self.adapter = ChainAdapter()

    def test_mint_nft_raises(self):
        with self.assertRaises(NotImplementedError):
            self.adapter.mint_nft('f', 'p', {})

    def test_on_ramp_raises(self):
        with self.assertRaises(NotImplementedError):
            self.adapter.on_ramp('p', 1, '0x1')

    def test_off_ramp_raises(self):
        with self.assertRaises(NotImplementedError):
            self.adapter.off_ramp('p', 1, '0x1')

    def test_verify_raises(self):
        with self.assertRaises(NotImplementedError):
            self.adapter.verify('f')


class TestNullAdapter(unittest.TestCase):
    def setUp(self):
        from urace.integration_bridge import NullAdapter, ChainAdapter
        self.adapter = NullAdapter()
        self.ChainAdapter = ChainAdapter

    def test_null_adapter_is_chain_adapter_subclass(self):
        self.assertIsInstance(self.adapter, self.ChainAdapter)

    def test_mint_nft_returns_expected_shape(self):
        result = self.adapter.mint_nft('feat-1', 'alice', {})
        self.assertIn('tx_hash', result)
        self.assertIn('token_id', result)
        self.assertIn('chain_id', result)
        self.assertIn('status', result)
        self.assertIsNone(result['tx_hash'])
        self.assertIsNone(result['token_id'])
        self.assertIsNone(result['chain_id'])

    def test_on_ramp_returns_expected_shape(self):
        result = self.adapter.on_ramp('alice', 1000, '0xABC')
        self.assertIn('tx_hash', result)
        self.assertIn('amount_crypto', result)
        self.assertIn('crypto_symbol', result)
        self.assertIn('status', result)
        self.assertIsNone(result['tx_hash'])

    def test_off_ramp_returns_expected_shape(self):
        result = self.adapter.off_ramp('bob', 500, '0xDEF')
        self.assertIn('tx_hash', result)
        self.assertIn('amount_crypto', result)
        self.assertIn('crypto_symbol', result)
        self.assertIn('status', result)

    def test_verify_returns_expected_shape(self):
        result = self.adapter.verify('feat-2')
        self.assertIn('verified', result)
        self.assertIn('tx_hash', result)
        self.assertIn('block_number', result)
        self.assertIn('chain_id', result)
        self.assertIn('status', result)
        self.assertIsNone(result['verified'])

    def test_null_adapter_does_not_raise(self):
        # NullAdapter must be safe to call without network/config
        self.adapter.mint_nft('x', 'y', {})
        self.adapter.on_ramp('p', 100, '0x0')
        self.adapter.off_ramp('p', 100, '0x0')
        self.adapter.verify('feat')


class TestGetChainAdapter(unittest.TestCase):
    def test_empty_config_returns_null_adapter(self):
        from urace.integration_bridge import get_chain_adapter, NullAdapter
        adapter = get_chain_adapter({})
        self.assertIsInstance(adapter, NullAdapter)

    def test_missing_p2p_key_returns_null_adapter(self):
        from urace.integration_bridge import get_chain_adapter, NullAdapter
        adapter = get_chain_adapter({'executor': {}})
        self.assertIsInstance(adapter, NullAdapter)

    def test_bad_dotted_path_returns_null_adapter_gracefully(self):
        from urace.integration_bridge import get_chain_adapter, NullAdapter
        adapter = get_chain_adapter({'p2p': {'chain_adapter': 'nonexistent.module.FakeAdapter'}})
        self.assertIsInstance(adapter, NullAdapter)

    def test_non_subclass_path_returns_null_adapter(self):
        from urace.integration_bridge import get_chain_adapter, NullAdapter
        # os.path is a valid module but not a ChainAdapter subclass
        adapter = get_chain_adapter({'p2p': {'chain_adapter': 'os.path'}})
        self.assertIsInstance(adapter, NullAdapter)

    def test_explicit_null_adapter_path_loads_correctly(self):
        from urace.integration_bridge import get_chain_adapter, NullAdapter
        adapter = get_chain_adapter({'p2p': {'chain_adapter': 'urace.integration_bridge.NullAdapter'}})
        self.assertIsInstance(adapter, NullAdapter)


class TestStubNftMint(unittest.TestCase):
    def setUp(self):
        from urace import integration_bridge as ib
        self.ib = ib
        self.ex = MockExchange()

    def test_returns_stub_status(self):
        result = self.ib.stub_nft_mint(self.ex, 'feat-1', 'alice')
        self.assertEqual(result['status'], 'stub')

    def test_emits_nft_mint_requested_row(self):
        self.ib.stub_nft_mint(self.ex, 'feat-1', 'alice')
        kinds = [r['kind'] for r in self.ex.audit_rows()]
        self.assertIn('NFT_MINT_REQUESTED', kinds)

    def test_row_has_feature_id_and_creator(self):
        self.ib.stub_nft_mint(self.ex, 'feat-2', 'bob')
        row = next(r for r in self.ex.audit_rows() if r['kind'] == 'NFT_MINT_REQUESTED')
        self.assertEqual(row['feature_id'], 'feat-2')
        self.assertEqual(row['creator_peer_id'], 'bob')

    def test_audit_row_has_chain_aware_fields(self):
        self.ib.stub_nft_mint(self.ex, 'feat-3', 'carol')
        row = next(r for r in self.ex.audit_rows() if r['kind'] == 'NFT_MINT_REQUESTED')
        self.assertIn('tx_hash', row)
        self.assertIn('token_id', row)
        self.assertIn('chain_id', row)
        self.assertIn('adapter_status', row)
        self.assertIsNone(row['tx_hash'])
        self.assertIsNone(row['chain_id'])

    def test_backward_compat_no_config_uses_null_adapter(self):
        # config defaults to None — must not raise
        result = self.ib.stub_nft_mint(self.ex, 'feat-x', 'dave')
        self.assertEqual(result['status'], 'stub')


class TestStubCryptoOnRamp(unittest.TestCase):
    def setUp(self):
        from urace import integration_bridge as ib
        self.ib = ib
        self.ex = MockExchange()

    def test_returns_stub_status(self):
        result = self.ib.stub_crypto_on_ramp(self.ex, 'alice', 1000, '0xABC')
        self.assertEqual(result['status'], 'stub')

    def test_emits_crypto_on_ramp_requested_row(self):
        self.ib.stub_crypto_on_ramp(self.ex, 'alice', 1000, '0xABC')
        kinds = [r['kind'] for r in self.ex.audit_rows()]
        self.assertIn('CRYPTO_ON_RAMP_REQUESTED', kinds)

    def test_audit_row_has_chain_aware_fields(self):
        self.ib.stub_crypto_on_ramp(self.ex, 'alice', 500, '0xABC')
        row = next(r for r in self.ex.audit_rows() if r['kind'] == 'CRYPTO_ON_RAMP_REQUESTED')
        self.assertIn('tx_hash', row)
        self.assertIn('amount_crypto', row)
        self.assertIn('crypto_symbol', row)
        self.assertIn('adapter_status', row)
        self.assertIsNone(row['tx_hash'])


class TestStubCryptoOffRamp(unittest.TestCase):
    def setUp(self):
        from urace import integration_bridge as ib
        self.ib = ib
        self.ex = MockExchange()

    def test_returns_stub_status(self):
        result = self.ib.stub_crypto_off_ramp(self.ex, 'bob', 500, '0xDEF')
        self.assertEqual(result['status'], 'stub')

    def test_emits_crypto_off_ramp_requested_row(self):
        self.ib.stub_crypto_off_ramp(self.ex, 'bob', 500, '0xDEF')
        kinds = [r['kind'] for r in self.ex.audit_rows()]
        self.assertIn('CRYPTO_OFF_RAMP_REQUESTED', kinds)

    def test_audit_row_has_chain_aware_fields(self):
        self.ib.stub_crypto_off_ramp(self.ex, 'bob', 250, '0xDEF')
        row = next(r for r in self.ex.audit_rows() if r['kind'] == 'CRYPTO_OFF_RAMP_REQUESTED')
        self.assertIn('tx_hash', row)
        self.assertIn('amount_crypto', row)
        self.assertIn('crypto_symbol', row)
        self.assertIn('adapter_status', row)
        self.assertIsNone(row['tx_hash'])


class TestStubOnChainVerify(unittest.TestCase):
    def setUp(self):
        from urace import integration_bridge as ib
        self.ib = ib
        self.ex = MockExchange()

    def test_returns_stub_status(self):
        result = self.ib.stub_on_chain_verify(self.ex, 'feat-3')
        self.assertEqual(result['status'], 'stub')

    def test_emits_on_chain_verify_requested_row(self):
        self.ib.stub_on_chain_verify(self.ex, 'feat-3')
        kinds = [r['kind'] for r in self.ex.audit_rows()]
        self.assertIn('ON_CHAIN_VERIFY_REQUESTED', kinds)

    def test_row_has_feature_id(self):
        self.ib.stub_on_chain_verify(self.ex, 'feat-4')
        row = next(r for r in self.ex.audit_rows() if r['kind'] == 'ON_CHAIN_VERIFY_REQUESTED')
        self.assertEqual(row['feature_id'], 'feat-4')

    def test_audit_row_has_chain_aware_fields(self):
        self.ib.stub_on_chain_verify(self.ex, 'feat-5')
        row = next(r for r in self.ex.audit_rows() if r['kind'] == 'ON_CHAIN_VERIFY_REQUESTED')
        self.assertIn('tx_hash', row)
        self.assertIn('block_number', row)
        self.assertIn('chain_id', row)
        self.assertIn('verified', row)
        self.assertIn('adapter_status', row)
        self.assertIsNone(row['tx_hash'])
        self.assertIsNone(row['chain_id'])


class TestReceiptRecord(unittest.TestCase):
    def test_receipt_record_has_expected_fields(self):
        from urace.integration_bridge import ReceiptRecord
        r = ReceiptRecord(feature_id='f1', status='ok', tx_hash='0xabc')
        self.assertEqual(r.feature_id, 'f1')
        self.assertEqual(r.status, 'ok')
        self.assertEqual(r.tx_hash, '0xabc')
        self.assertIsNone(r.block_number)

    def test_receipt_record_default_status_is_stub(self):
        from urace.integration_bridge import ReceiptRecord
        r = ReceiptRecord()
        self.assertEqual(r.status, 'stub')


class TestEthSettlementAdapterIsChainAdapter(unittest.TestCase):
    def test_eth_settlement_adapter_is_chain_adapter_subclass(self):
        from urace.eth_settlement_adapter import EthSettlementAdapter
        from urace._chain_adapter_base import ChainAdapter
        self.assertTrue(issubclass(EthSettlementAdapter, ChainAdapter))

    def test_eth_settlement_adapter_loads_via_get_chain_adapter(self):
        from urace.integration_bridge import get_chain_adapter, NullAdapter
        # Without rpc_provider_url, should still return NullAdapter
        adapter = get_chain_adapter({'p2p': {'token_settlement': True}})
        self.assertIsInstance(adapter, NullAdapter)


if __name__ == '__main__':
    unittest.main()
