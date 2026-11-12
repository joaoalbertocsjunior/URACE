"""Abstract base for on-chain settlement adapters.

Extracted from integration_bridge.py to break the circular import between
integration_bridge (which imports EthSettlementAdapter) and
eth_settlement_adapter (which needs to inherit ChainAdapter).
"""
from __future__ import annotations


class ChainAdapter:
    """Protocol for optional on-chain attestation. Implement a subclass and set
    config p2p.chain_adapter to its dotted import path to go live on-chain.
    NullAdapter (default) emits audit rows only — no network calls.
    """

    def mint_nft(self, feature_id: str, creator_peer_id: str, metadata: dict) -> dict:
        """Mint NFT attestation. Returns {tx_hash, token_id, chain_id, status}."""
        raise NotImplementedError

    def on_ramp(self, peer_id: str, amount_units: int, crypto_address: str) -> dict:
        """Convert crypto to URACE units. Returns {tx_hash, amount_crypto, crypto_symbol, status}."""
        raise NotImplementedError

    def off_ramp(self, peer_id: str, amount_units: int, crypto_address: str) -> dict:
        """Convert URACE units to crypto. Returns {tx_hash, amount_crypto, crypto_symbol, status}."""
        raise NotImplementedError

    def verify(self, feature_id: str) -> dict:
        """Verify on-chain attestation. Returns {verified, tx_hash, block_number, chain_id}."""
        raise NotImplementedError
