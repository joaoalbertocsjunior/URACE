"""Tests for eth_settlement_adapter bug fixes."""
import pytest
from unittest.mock import patch, MagicMock


def _make_adapter(chain_id=137):
    from urace.eth_settlement_adapter import EthSettlementAdapter
    return EthSettlementAdapter(
        rpc_url="http://localhost:8545",
        chain_id=chain_id,
        erc20_contract="0x" + "aa" * 20,
    )


def test_default_chain_id_is_polygon():
    from urace.eth_settlement_adapter import EthSettlementAdapter
    a = EthSettlementAdapter(rpc_url="http://localhost:8545")
    assert a._chain_id == 137


def test_estimate_gas_uses_rpc():
    adapter = _make_adapter()
    with patch.object(adapter, "_rpc_call") as mock_rpc:
        mock_rpc.return_value = {"result": hex(50000)}
        gas = adapter._estimate_gas("0x" + "bb" * 20, 0, "0x", "0x" + "cc" * 20)
    assert gas == int(50000 * 1.2)
    mock_rpc.assert_called_once()
    assert mock_rpc.call_args[0][0] == "eth_estimateGas"


def test_estimate_gas_fallback_on_error():
    adapter = _make_adapter()
    with patch.object(adapter, "_rpc_call") as mock_rpc:
        mock_rpc.return_value = {"error": {"message": "execution reverted"}}
        gas = adapter._estimate_gas("0x" + "bb" * 20, 0, "0x", "0x" + "cc" * 20)
    assert gas == 100_000


def test_fetch_nonce_returns_none_on_error():
    adapter = _make_adapter()
    with patch.object(adapter, "_rpc_call") as mock_rpc:
        mock_rpc.return_value = {"error": {"message": "node not synced"}}
        nonce = adapter._fetch_nonce("0x" + "aa" * 20)
    assert nonce is None


def test_fetch_nonce_returns_int_on_success():
    adapter = _make_adapter()
    with patch.object(adapter, "_rpc_call") as mock_rpc:
        mock_rpc.return_value = {"result": "0x5"}
        nonce = adapter._fetch_nonce("0x" + "aa" * 20)
    assert nonce == 5


def test_on_ramp_surfaces_nonce_error():
    adapter = _make_adapter()
    with patch.object(adapter, "_fetch_nonce", return_value=None):
        with patch.object(adapter, "_get_wallet", return_value={"address": "0x" + "ff" * 20}):
            result = adapter.on_ramp("peer1", 100, "0x" + "ee" * 20)
    assert result["status"] == "rpc_error"
    assert "nonce" in result["error"]


def test_on_ramp_uses_estimate_gas(monkeypatch):
    adapter = _make_adapter()
    with patch.object(adapter, "_fetch_nonce", return_value=0), \
         patch.object(adapter, "_fetch_gas_price", return_value=30_000_000_000), \
         patch.object(adapter, "_estimate_gas", return_value=42_000) as mock_est, \
         patch.object(adapter, "_get_wallet", return_value={"address": "0x" + "ff" * 20}), \
         patch("urace.eth_settlement_adapter._sign_transaction", return_value="0xdeadbeef"), \
         patch.object(adapter, "_rpc_call", return_value={"result": "0xtxhash"}):
        from urace import credit_ledger as cl
        monkeypatch.setattr(cl, "to_chain_units", lambda x: x * 100)
        result = adapter.on_ramp("peer1", 1, "0x" + "ee" * 20)
    mock_est.assert_called_once()
    assert result["status"] == "ok"
