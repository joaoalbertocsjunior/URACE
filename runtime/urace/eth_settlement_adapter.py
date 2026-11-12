"""eth_settlement_adapter.py — EVM settlement adapter for URACE token bridge.

Broadcasts signed ERC-20 transfer transactions to a configured JSON-RPC endpoint.
Only active when token_settlement=True and rpc_provider_url is set in exchange config.
All methods return {status: 'rpc_error', error: str} on failure — never raise.
"""
from __future__ import annotations
import hashlib as _hashlib
import json as _json
import struct as _struct
import urllib.request as _ur
from pathlib import Path

from ._chain_adapter_base import ChainAdapter


# ---------------------------------------------------------------------------
# Minimal RLP encoder (no external dependencies)
# ---------------------------------------------------------------------------

def _rlp_encode(value) -> bytes:
    """Minimal RLP encoder supporting bytes, int, and list."""
    if isinstance(value, int):
        if value == 0:
            value = b''
        else:
            byte_len = (value.bit_length() + 7) // 8
            value = value.to_bytes(byte_len, 'big')
    if isinstance(value, (bytes, bytearray)):
        if len(value) == 1 and value[0] < 0x80:
            return bytes(value)
        length_bytes = _rlp_length_prefix(len(value), 0x80)
        return length_bytes + bytes(value)
    if isinstance(value, list):
        encoded_items = b''.join(_rlp_encode(item) for item in value)
        length_bytes = _rlp_length_prefix(len(encoded_items), 0xc0)
        return length_bytes + encoded_items
    raise TypeError(f"_rlp_encode: unsupported type {type(value)}")


def _rlp_length_prefix(length: int, offset: int) -> bytes:
    if length < 56:
        return bytes([offset + length])
    length_of_length = (length.bit_length() + 7) // 8
    return bytes([offset + 55 + length_of_length]) + length.to_bytes(length_of_length, 'big')


# ---------------------------------------------------------------------------
# keccak256 approximation
# NOTE: Python's hashlib.sha3_256 is FIPS SHA-3, NOT Ethereum's Keccak-256.
# For production use, install pysha3: pip install pysha3
# ---------------------------------------------------------------------------

def _keccak256(data: bytes) -> bytes:
    """Keccak-256 approximation. Install pysha3 for production correctness."""
    try:
        import sha3 as _sha3  # pysha3
        return _sha3.keccak_256(data).digest()
    except ImportError:
        # Fallback: SHA3-256 — NOT Keccak-256. Selector computation will be wrong
        # unless selectors are hardcoded (which they are below).
        return _hashlib.sha3_256(data).digest()


# ---------------------------------------------------------------------------
# ABI calldata helpers — selectors are hardcoded ERC-20/ERC-721 standards
# ---------------------------------------------------------------------------

_SELECTOR_TRANSFER  = bytes.fromhex('a9059cbb')  # transfer(address,uint256)
_SELECTOR_SAFE_MINT = bytes.fromhex('d204c45e')  # safeMint(address,uint256)


def _encode_erc20_transfer(to_address: str, amount: int) -> str:
    """ABI-encode ERC-20 transfer(address,uint256) calldata."""
    addr_bytes = bytes.fromhex(to_address.lstrip('0x').lower().zfill(40))
    calldata = (
        _SELECTOR_TRANSFER
        + addr_bytes.rjust(32, b'\x00')
        + amount.to_bytes(32, 'big')
    )
    return '0x' + calldata.hex()


def _encode_safe_mint(to_address: str, token_id: int) -> str:
    """ABI-encode safeMint(address,uint256) calldata."""
    addr_bytes = bytes.fromhex(to_address.lstrip('0x').lower().zfill(40))
    calldata = (
        _SELECTOR_SAFE_MINT
        + addr_bytes.rjust(32, b'\x00')
        + token_id.to_bytes(32, 'big')
    )
    return '0x' + calldata.hex()


# ---------------------------------------------------------------------------
# EIP-155 transaction signing (pure Python)
# ---------------------------------------------------------------------------

def _sign_transaction(
    nonce: int,
    gas_price: int,
    gas_limit: int,
    to: str,
    value: int,
    data: str,
    private_key_hex: str,
    chain_id: int = 1,
    wallet_dir=None,
) -> str:
    """Sign an EIP-155 transaction and return hex-encoded RLP bytes.

    Uses crypto_wallet.wallet_sign() for ECDSA signing. The recovery_id is
    approximated as 0 (even y parity) since wallet_sign returns DER encoding
    without exposing the recovery bit. For production use eth_account instead.
    """
    to_bytes = bytes.fromhex(to.lstrip('0x').zfill(40))
    data_bytes = bytes.fromhex(data.lstrip('0x')) if data and data != '0x' else b''

    # EIP-155 pre-sign payload: [nonce, gasPrice, gasLimit, to, value, data, chainId, 0, 0]
    unsigned_rlp = _rlp_encode([
        nonce, gas_price, gas_limit, to_bytes, value, data_bytes, chain_id, 0, 0
    ])
    tx_hash = _keccak256(unsigned_rlp)

    # Sign using crypto_wallet — returns DER-encoded signature
    from . import crypto_wallet as _cw
    sign_result = _cw.wallet_sign(tx_hash, wallet_dir=wallet_dir)
    der_sig = bytes.fromhex(sign_result['signature_der'])

    # Decode DER signature to r, s integers
    r, s = _der_to_rs(der_sig)

    # EIP-155: v = 35 + 2*chain_id + recovery_id
    # recovery_id approximated as 0 (wallet_sign does not expose it)
    recovery_id = 0
    v = 35 + 2 * chain_id + recovery_id

    signed_rlp = _rlp_encode([
        nonce, gas_price, gas_limit, to_bytes, value, data_bytes, v, r, s
    ])
    return '0x' + signed_rlp.hex()


def _der_to_rs(der: bytes) -> tuple[int, int]:
    """Parse DER-encoded ECDSA signature to (r, s) integers."""
    # DER: 0x30 [total-len] 0x02 [r-len] [r] 0x02 [s-len] [s]
    assert der[0] == 0x30
    offset = 2
    assert der[offset] == 0x02
    r_len = der[offset + 1]
    r = int.from_bytes(der[offset + 2: offset + 2 + r_len], 'big')
    offset += 2 + r_len
    assert der[offset] == 0x02
    s_len = der[offset + 1]
    s = int.from_bytes(der[offset + 2: offset + 2 + s_len], 'big')
    return r, s


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class EthSettlementAdapter(ChainAdapter):
    """Live EVM adapter. Replaces NullAdapter when rpc_provider_url is configured.

    chain_id controls EIP-155 signing:
      1       = Ethereum mainnet   (~$4-7/tx at 20 Gwei, uneconomical per-borrow)
      137     = Polygon PoS        (~$0.001/tx — recommended for per-borrow settlement)
      8453    = Base               (~$0.001/tx)
      42161   = Arbitrum One      (~$0.001/tx)
    """

    def __init__(
        self,
        rpc_url: str,
        wallet_dir: 'str | Path | None' = None,
        erc20_contract: 'str | None' = None,
        nft_contract: 'str | None' = None,
        chain_id: int = 1,
    ):
        self._rpc_url      = rpc_url.rstrip('/')
        self._wallet_dir   = Path(wallet_dir) if wallet_dir else None
        self._erc20_contract = erc20_contract or ''
        self._nft_contract   = nft_contract   or ''
        self._chain_id       = chain_id

    # ------------------------------------------------------------------
    # JSON-RPC
    # ------------------------------------------------------------------

    def _rpc_call(self, method: str, params: list) -> dict:
        """Issue a JSON-RPC 2.0 call. Returns parsed response or error dict."""
        payload = _json.dumps({
            "jsonrpc": "2.0", "method": method, "params": params, "id": 1
        }).encode()
        req = _ur.Request(
            self._rpc_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with _ur.urlopen(req, timeout=15) as resp:
                return _json.loads(resp.read(65536))
        except Exception as e:
            return {"error": {"message": str(e)}}

    def _fetch_nonce(self, address: str) -> int:
        """Fetch pending tx count for address. Returns 0 on any failure (tx will fail on-chain if wrong)."""
        resp = self._rpc_call("eth_getTransactionCount", [address, "pending"])
        if "error" in resp:
            return 0
        try:
            return int(resp["result"], 16)
        except (ValueError, TypeError):
            return 0

    def _fetch_gas_price(self) -> int:
        """Fetch current gas price. Returns 20 Gwei fallback on any failure."""
        resp = self._rpc_call("eth_gasPrice", [])
        if "error" in resp:
            return 20_000_000_000
        try:
            return int(resp["result"], 16)
        except (ValueError, TypeError):
            return 20_000_000_000

    def _get_wallet(self) -> dict:
        from . import crypto_wallet as _cw
        return _cw.wallet_show(self._wallet_dir)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def on_ramp(self, peer_id: str, amount_units: int, crypto_address: str) -> dict:
        try:
            from . import credit_ledger as _cl
            chain_amount = _cl.to_chain_units(amount_units)
            wallet = self._get_wallet()
            address = wallet['address']
            nonce = self._fetch_nonce(address)
            gas_price = self._fetch_gas_price()
            if self._erc20_contract:
                calldata = _encode_erc20_transfer(crypto_address, chain_amount)
                to_addr  = self._erc20_contract
                value    = 0
            else:
                calldata = '0x'
                to_addr  = crypto_address
                value    = chain_amount
            signed_tx = _sign_transaction(
                nonce, gas_price, 100000, to_addr, value, calldata,
                private_key_hex='', wallet_dir=self._wallet_dir,
                chain_id=self._chain_id,
            )
            resp = self._rpc_call("eth_sendRawTransaction", [signed_tx])
            if "error" in resp:
                return {"status": "rpc_error", "error": resp["error"].get("message", str(resp["error"]))}
            return {"status": "ok", "tx_hash": resp.get("result", ""), "amount_crypto": chain_amount}
        except Exception as e:
            return {"status": "rpc_error", "error": str(e)}

    def off_ramp(self, peer_id: str, amount_units: int, crypto_address: str) -> dict:
        try:
            from . import credit_ledger as _cl
            chain_amount = _cl.to_chain_units(amount_units)
            wallet = self._get_wallet()
            address = wallet['address']
            nonce = self._fetch_nonce(address)
            gas_price = self._fetch_gas_price()
            if self._erc20_contract:
                calldata = _encode_erc20_transfer(crypto_address, chain_amount)
                to_addr  = self._erc20_contract
                value    = 0
            else:
                calldata = '0x'
                to_addr  = crypto_address
                value    = chain_amount
            signed_tx = _sign_transaction(
                nonce, gas_price, 100000, to_addr, value, calldata,
                private_key_hex='', wallet_dir=self._wallet_dir,
                chain_id=self._chain_id,
            )
            resp = self._rpc_call("eth_sendRawTransaction", [signed_tx])
            if "error" in resp:
                return {"status": "rpc_error", "error": resp["error"].get("message", str(resp["error"]))}
            return {"status": "ok", "tx_hash": resp.get("result", ""), "amount_crypto": chain_amount}
        except Exception as e:
            return {"status": "rpc_error", "error": str(e)}

    def mint_nft(self, feature_id: str, creator_peer_id: str, metadata: dict) -> dict:
        try:
            wallet    = self._get_wallet()
            address   = wallet['address']
            nonce     = self._fetch_nonce(address)
            gas_price = self._fetch_gas_price()
            token_id  = int(_hashlib.sha256(feature_id.encode()).hexdigest()[:8], 16)
            to_addr   = self._nft_contract if self._nft_contract else '0x' + '00' * 20
            calldata  = _encode_safe_mint(address, token_id) if self._nft_contract else '0x'
            signed_tx = _sign_transaction(
                nonce, gas_price, 100000, to_addr, 0, calldata,
                private_key_hex='', wallet_dir=self._wallet_dir,
                chain_id=self._chain_id,
            )
            resp = self._rpc_call("eth_sendRawTransaction", [signed_tx])
            if "error" in resp:
                return {"status": "rpc_error", "error": resp["error"].get("message", str(resp["error"]))}
            return {"status": "ok", "tx_hash": resp.get("result", ""), "token_id": token_id}
        except Exception as e:
            return {"status": "rpc_error", "error": str(e)}

    def verify(self, feature_id: str) -> dict:  # feature_id treated as tx_hash for receipt lookup
        try:
            resp = self._rpc_call("eth_getTransactionReceipt", [feature_id])
            if "error" in resp:
                return {"status": "rpc_error", "error": resp["error"].get("message", str(resp["error"]))}
            result = resp.get("result")
            if result is None:
                return {"status": "pending", "verified": False}
            if result.get("status") == "0x1":
                return {
                    "status": "ok",
                    "verified": True,
                    "block_number": int(result["blockNumber"], 16),
                    "chain_id": None,
                }
            return {"status": "ok", "verified": False, "block_number": None, "chain_id": None}
        except Exception as e:
            return {"status": "rpc_error", "error": str(e)}
