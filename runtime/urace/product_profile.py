"""Product profile — observed capability and baseline metrics for a managed product.

The profile is stored under state['product_profile'] and updated by source adapters
(codebase, test_suite) during sync.  It is the canonical input to feature_matcher.py
and the repricing hookup (Phase 5D).

No authority — observations only; profile data never grants permissions.
"""
from __future__ import annotations

from typing import Any

_REQUIRED_FOR_MATCHING = ('capability',)
_NUMERIC_FIELDS = ('codebase_loc', 'test_pass_count', 'test_fail_count')


def load(state: dict) -> dict:
    """Return a copy of the product profile from state (never mutates state)."""
    return dict(state.get('product_profile') or {})


def update(state: dict, **kwargs: Any) -> dict:
    """Merge *kwargs* into state['product_profile'] and return the updated profile."""
    pp = state.setdefault('product_profile', {})
    for k, v in kwargs.items():
        if v is not None:
            pp[k] = v
    return dict(pp)


def validate(profile: dict) -> list[str]:
    """Return a list of validation warnings; empty list means ready for matching."""
    warnings: list[str] = []
    for field in _REQUIRED_FOR_MATCHING:
        if not profile.get(field):
            warnings.append(f'product_profile missing required field for matching: {field!r}')
    for field in _NUMERIC_FIELDS:
        val = profile.get(field)
        if val is not None and not isinstance(val, (int, float)):
            warnings.append(f'product_profile.{field} must be numeric, got {type(val).__name__}')
    return warnings


def snapshot(state: dict) -> dict:
    """Return a serialisable snapshot suitable for embedding in audit events."""
    pp = load(state)
    return {
        'capability': pp.get('capability', ''),
        'codebase_loc': pp.get('codebase_loc'),
        'codebase_languages': pp.get('codebase_languages', []),
        'test_pass_count': pp.get('test_pass_count'),
        'test_fail_count': pp.get('test_fail_count'),
        'ready_for_matching': not validate(pp),
    }


def set_capability(state: dict, capability: str) -> None:
    """Set the product capability string (required for feature matching)."""
    if not isinstance(capability, str) or not capability.strip():
        raise ValueError('capability must be a non-empty string')
    state.setdefault('product_profile', {})['capability'] = capability.strip()


def maybe_reprice(state: dict, exchange: Any, atom_id: str, outcome_delta: float) -> dict | None:
    """Phase 5D — trigger REPRICE_OBSERVED when product has ≥5 verified borrows for atom_id.

    Reads borrow counts from the exchange audit chain; writes the anchor when threshold met.
    Returns the REPRICE_OBSERVED record or None.
    """
    try:
        from .credit_ledger import write_reprice_observed
        rows = exchange.audit_rows()
        verified_borrows = [
            r for r in rows
            if r.get('kind') == 'FEATURE_BORROWED'
            and r.get('atom') == atom_id
            and r.get('receipt_verified') is True
        ]
        borrow_count = len(verified_borrows)
        if borrow_count < 5:
            return None
        deltas = [float(r.get('outcome_delta', 0.0)) for r in verified_borrows]
        median_delta = sorted(deltas)[len(deltas) // 2]
        return write_reprice_observed(exchange, atom_id, median_delta, borrow_count)
    except Exception:
        return None
