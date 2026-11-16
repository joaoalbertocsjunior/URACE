"""Chain anchor — publishes ledger seals to Polygon PoS (or any EVM L2).

Architecture: thin adapter over the existing off-chain ledger.
Off-chain logic (ledger_compaction, provenance_stake) stays unchanged.
This module is the only file that needs to know anything about the chain.

Phase 1 (current): complete no-op. enabled=false in config.
Phase 2: publish_seal() submits block_hash + block_height to HashRegistry contract.
Phase 3: publish_stake_event() calls StakeLedger contract for mint/slash/resolve.

Requires web3.py (MIT) for Phase 2+:
    pip install web3
If not installed, all calls are silently no-ops (graceful degradation).
"""
from __future__ import annotations

import hashlib
import json
import logging

SCHEMA = 'urace-chain-anchor-v1'
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config schema (fields under config["ledger"]["chain_anchor"])
# ---------------------------------------------------------------------------
CONFIG_DEFAULTS: dict = {
    "enabled": False,               # Phase 2: set True to activate
    "network": "polygon-amoy",      # "polygon-amoy" (testnet) | "polygon-pos" (mainnet)
    "rpc_url": "",                  # Infura / Alchemy / public RPC endpoint
    "hash_registry_address": "",    # deployed HashRegistry contract (Phase 2)
    "stake_ledger_address": "",     # deployed StakeLedger contract (Phase 3)
    "asset_registry_address": "",   # deployed AssetRegistry contract (Phase 3.5)
    "wallet_key_env": "URACE_CHAIN_KEY",  # env var holding the hex private key
    "publish_every_n_seals": 1,     # batch: anchor every N seals (1 = every seal)
    "dry_run": True,                # log tx but don't broadcast — safe default
    "gas_limit": 60000,
}

# Public RPC fallbacks (no API key required, rate-limited)
_PUBLIC_RPC = {
    "polygon-pos":   "https://polygon-rpc.com",
    "polygon-amoy":  "https://rpc-amoy.polygon.technology",
    "base":          "https://mainnet.base.org",
    "base-sepolia":  "https://sepolia.base.org",
}


# ---------------------------------------------------------------------------
# Public API — called by ledger_compaction.seal_ledger_block()
# ---------------------------------------------------------------------------

def publish_seal(seal_row: dict, config: dict) -> dict | None:
    """Anchor a LEDGER_BLOCK_SEAL to the chain.

    seal_row keys used: block_hash, block_height, rows_hash, at_unix
    Returns tx receipt dict on success, None if disabled/dry-run/unavailable.
    """
    cfg = _anchor_config(config)
    if not cfg.get("enabled"):
        return None
    try:
        return _do_publish_seal(seal_row, cfg)
    except Exception as exc:
        logger.warning("chain_anchor.publish_seal failed (non-fatal): %s", exc)
        return None


def publish_stake_event(event: dict, config: dict) -> dict | None:
    """Anchor a stake event (mint/slash/resolve) to StakeLedger contract.

    event keys: kind (STAKE_MINT|STAKE_SLASH|STAKE_RESOLVE), feature_id,
                challenger_peer_id (optional), amount_units, at_unix
    Returns tx receipt dict on success, None if disabled/unavailable.
    """
    cfg = _anchor_config(config)
    if not cfg.get("enabled"):
        return None
    try:
        return _do_publish_stake(event, cfg)
    except Exception as exc:
        logger.warning("chain_anchor.publish_stake_event failed (non-fatal): %s", exc)
        return None


def publish_asset_earning(earning: dict, config: dict) -> dict | None:
    """Anchor an ASSET_EARN event to AssetRegistry contract (Phase 3.5).

    earning keys: feature_id, owner_peer_id, earn_units, cumulative_earn_units, at_unix
    Records auditable yield history — the basis for asset market valuation.
    Returns tx receipt on success, None if disabled/unavailable.
    """
    cfg = _anchor_config(config)
    if not cfg.get("enabled"):
        return None
    try:
        return _do_publish_asset_earning(earning, cfg)
    except Exception as exc:
        logger.warning("chain_anchor.publish_asset_earning failed (non-fatal): %s", exc)
        return None


def publish_asset_transfer(transfer: dict, config: dict) -> dict | None:
    """Anchor an ASSET_TRANSFERRED event to AssetRegistry contract (Phase 3.5).

    transfer keys: feature_id, from_peer_id, to_peer_id, cumulative_earn_at_transfer, at_unix
    On-chain transfer record separates trade reputation from earned reputation.
    Returns tx receipt on success, None if disabled/unavailable.
    """
    cfg = _anchor_config(config)
    if not cfg.get("enabled"):
        return None
    try:
        return _do_publish_asset_transfer(transfer, cfg)
    except Exception as exc:
        logger.warning("chain_anchor.publish_asset_transfer failed (non-fatal): %s", exc)
        return None


def status(config: dict) -> dict:
    """Return anchor status for inclusion in `urace status` output."""
    cfg = _anchor_config(config)
    if not cfg.get("enabled"):
        return {"enabled": False}
    w3 = _w3(cfg)
    connected = False
    block = None
    if w3 is not None:
        try:
            block = w3.eth.block_number
            connected = True
        except Exception:
            pass
    return {
        "enabled": True,
        "network": cfg.get("network"),
        "connected": connected,
        "latest_block": block,
        "dry_run": cfg.get("dry_run", True),
        "hash_registry": cfg.get("hash_registry_address") or "not configured",
        "stake_ledger": cfg.get("stake_ledger_address") or "not configured",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _anchor_config(config: dict) -> dict:
    base = dict(CONFIG_DEFAULTS)
    base.update(config.get("ledger", {}).get("chain_anchor", {}))
    return base


def _w3(cfg: dict):
    """Return a web3.Web3 instance, or None if web3 not installed."""
    try:
        from web3 import Web3  # type: ignore
    except ImportError:
        return None
    rpc = cfg.get("rpc_url") or _PUBLIC_RPC.get(cfg.get("network", ""), "")
    if not rpc:
        return None
    return Web3(Web3.HTTPProvider(rpc))


def _wallet(cfg: dict):
    """Return (web3, account) or (None, None)."""
    import os
    w3 = _w3(cfg)
    if w3 is None:
        return None, None
    key = os.environ.get(cfg.get("wallet_key_env", "URACE_CHAIN_KEY"), "")
    if not key:
        return w3, None
    try:
        account = w3.eth.account.from_key(key)
        return w3, account
    except Exception:
        return w3, None


# Minimal ABI for HashRegistry contract (Phase 2)
# store(bytes32 blockHash, uint64 blockHeight, bytes32 rowsHash)
_HASH_REGISTRY_ABI = json.loads('[{"inputs":[{"name":"blockHash","type":"bytes32"},{"name":"blockHeight","type":"uint64"},{"name":"rowsHash","type":"bytes32"}],"name":"store","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"blockHeight","type":"uint64"}],"name":"get","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"}]')

# Minimal ABI for StakeLedger contract (Phase 3)
_STAKE_LEDGER_ABI = json.loads('[{"inputs":[{"name":"featureId","type":"bytes32"},{"name":"peerId","type":"bytes32"},{"name":"amount","type":"uint64"},{"name":"kind","type":"uint8"}],"name":"record","outputs":[],"stateMutability":"nonpayable","type":"function"}]')


def _do_publish_seal(seal_row: dict, cfg: dict) -> dict | None:
    w3, account = _wallet(cfg)
    if w3 is None:
        return None
    contract_addr = cfg.get("hash_registry_address", "")
    if not contract_addr:
        logger.debug("chain_anchor: hash_registry_address not configured — skipping")
        return None

    block_hash_hex = seal_row.get("block_hash", "0" * 64)
    rows_hash_hex = seal_row.get("rows_hash", "0" * 64)
    block_height = int(seal_row.get("block_height", 0))

    bh_bytes = bytes.fromhex(block_hash_hex.ljust(64, "0")[:64])
    rh_bytes = bytes.fromhex(rows_hash_hex.ljust(64, "0")[:64])

    if cfg.get("dry_run"):
        logger.info("chain_anchor [dry_run] would store seal height=%d hash=%.8s... on %s",
                    block_height, block_hash_hex, cfg.get("network"))
        return {"dry_run": True, "block_height": block_height, "block_hash": block_hash_hex}

    if account is None:
        logger.warning("chain_anchor: no wallet key — cannot submit tx")
        return None

    contract = w3.eth.contract(address=w3.to_checksum_address(contract_addr),
                               abi=_HASH_REGISTRY_ABI)
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.store(bh_bytes, block_height, rh_bytes).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": cfg.get("gas_limit", 60000),
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    logger.info("chain_anchor: seal height=%d anchored tx=%s status=%s",
                block_height, receipt["transactionHash"].hex(), receipt["status"])
    return {"tx_hash": receipt["transactionHash"].hex(), "status": receipt["status"],
            "block_height": block_height}


def _do_publish_stake(event: dict, cfg: dict) -> dict | None:
    w3, account = _wallet(cfg)
    if w3 is None:
        return None
    contract_addr = cfg.get("stake_ledger_address", "")
    if not contract_addr:
        return None

    _KIND = {"STAKE_MINT": 0, "STAKE_SLASH": 1, "STAKE_RESOLVE": 2}
    kind_int = _KIND.get(event.get("kind", ""), 0)
    feature_id = event.get("feature_id", "")
    peer_id = event.get("peer_id", "")
    amount = int(event.get("amount_units", 0))

    fid_bytes = hashlib.sha256(feature_id.encode()).digest()
    pid_bytes = hashlib.sha256(peer_id.encode()).digest()

    if cfg.get("dry_run"):
        logger.info("chain_anchor [dry_run] would record stake kind=%s feature=%.12s on %s",
                    event.get("kind"), feature_id, cfg.get("network"))
        return {"dry_run": True, "kind": event.get("kind"), "feature_id": feature_id}

    if account is None:
        return None

    contract = w3.eth.contract(address=w3.to_checksum_address(contract_addr),
                               abi=_STAKE_LEDGER_ABI)
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.record(fid_bytes, pid_bytes, amount, kind_int).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": cfg.get("gas_limit", 60000),
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    return {"tx_hash": receipt["transactionHash"].hex(), "status": receipt["status"]}


# AssetRegistry ABI (Phase 3.5)
# recordEarning(bytes32 featureId, bytes32 ownerId, uint64 earnUnits, uint64 cumulative)
# transfer(bytes32 featureId, bytes32 newOwnerId, uint64 cumulativeAtTransfer)
_ASSET_REGISTRY_ABI = json.loads('[{"inputs":[{"name":"featureId","type":"bytes32"},{"name":"ownerId","type":"bytes32"},{"name":"earnUnits","type":"uint64"},{"name":"cumulative","type":"uint64"}],"name":"recordEarning","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"featureId","type":"bytes32"},{"name":"newOwnerId","type":"bytes32"},{"name":"cumulativeAtTransfer","type":"uint64"}],"name":"transfer","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"featureId","type":"bytes32"}],"name":"getOwner","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"featureId","type":"bytes32"}],"name":"getCumulative","outputs":[{"name":"","type":"uint64"}],"stateMutability":"view","type":"function"}]')


def _do_publish_asset_earning(earning: dict, cfg: dict) -> dict | None:
    w3, account = _wallet(cfg)
    if w3 is None:
        return None
    contract_addr = cfg.get("asset_registry_address", "")
    if not contract_addr:
        return None

    feature_id = earning.get("feature_id", "")
    owner_id = earning.get("owner_peer_id", "")
    earn_units = int(earning.get("earn_units", 0))
    cumulative = int(earning.get("cumulative_earn_units", 0))

    fid_bytes = hashlib.sha256(feature_id.encode()).digest()
    oid_bytes = hashlib.sha256(owner_id.encode()).digest()

    if cfg.get("dry_run"):
        logger.info("chain_anchor [dry_run] would record asset earn feature=%.12s +%d (cum=%d) on %s",
                    feature_id, earn_units, cumulative, cfg.get("network"))
        return {"dry_run": True, "feature_id": feature_id, "earn_units": earn_units,
                "cumulative": cumulative}

    if account is None:
        return None

    contract = w3.eth.contract(address=w3.to_checksum_address(contract_addr),
                               abi=_ASSET_REGISTRY_ABI)
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.recordEarning(fid_bytes, oid_bytes, earn_units, cumulative
                                          ).build_transaction({
        "from": account.address, "nonce": nonce, "gas": cfg.get("gas_limit", 60000),
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    return {"tx_hash": receipt["transactionHash"].hex(), "status": receipt["status"],
            "feature_id": feature_id, "cumulative": cumulative}


def _do_publish_asset_transfer(transfer: dict, cfg: dict) -> dict | None:
    w3, account = _wallet(cfg)
    if w3 is None:
        return None
    contract_addr = cfg.get("asset_registry_address", "")
    if not contract_addr:
        return None

    feature_id = transfer.get("feature_id", "")
    to_peer = transfer.get("to_peer_id", "")
    cumulative = int(transfer.get("cumulative_earn_at_transfer", 0))

    fid_bytes = hashlib.sha256(feature_id.encode()).digest()
    to_bytes = hashlib.sha256(to_peer.encode()).digest()

    if cfg.get("dry_run"):
        logger.info("chain_anchor [dry_run] would transfer asset feature=%.12s → %.12s on %s",
                    feature_id, to_peer, cfg.get("network"))
        return {"dry_run": True, "feature_id": feature_id, "to_peer_id": to_peer}

    if account is None:
        return None

    contract = w3.eth.contract(address=w3.to_checksum_address(contract_addr),
                               abi=_ASSET_REGISTRY_ABI)
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.transfer(fid_bytes, to_bytes, cumulative).build_transaction({
        "from": account.address, "nonce": nonce, "gas": cfg.get("gas_limit", 60000),
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    return {"tx_hash": receipt["transactionHash"].hex(), "status": receipt["status"],
            "feature_id": feature_id, "to_peer_id": to_peer}
