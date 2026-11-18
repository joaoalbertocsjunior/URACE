"""Shared numeric constants for the P2P token economy.

Import from here rather than duplicating in credit_ledger or token_ledger.
Changing a value here propagates to all P2P accounting without touching
any transport, ledger, or CLI code.
"""
from __future__ import annotations

# ── Token precision (satoshi model) ──────────────────────────────────────────
DECIMALS: int = 8
UNIT: int = 10 ** DECIMALS           # 1.00000000 token = 100_000_000 base units

# ── EVM on-chain representation ───────────────────────────────────────────────
CHAIN_DECIMALS: int = 18
CHAIN_UNIT: int = 10 ** CHAIN_DECIMALS
CHAIN_SCALE: int = CHAIN_UNIT // UNIT   # = 10^10: multiply internal units for 18-dec EVM
