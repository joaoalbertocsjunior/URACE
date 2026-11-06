"""Provenance graph resolution for dynamic composition referral.

Resolves a feature's full provenance tree and returns {peer_id: weight} for
proportional referral distribution at borrow time.

Multi-provenance example:
  Feature Y = Component A (60%) + Component B (40%)
  Component B = Sub-owner P (70%) + Sub-owner Q (30%)
  → Y's provenance: {A_owner: 0.60, P: 0.28, Q: 0.12}
"""
import hashlib
from typing import Any


def resolve_provenance_weights(feature_id: str, rows: list[dict],
                                _visited: set | None = None) -> dict[str, float]:
    """Return {peer_id: weight} for all provenance contributors of a feature.

    Weights sum to ≤ 1.0. The remainder (1 - sum) belongs to the composite creator
    (the novel portion they added beyond their components).

    Handles cycles via _visited guard (should not occur in a DAG, but defensive).
    """
    if _visited is None:
        _visited = set()
    if feature_id in _visited:
        return {}
    _visited = _visited | {feature_id}

    # Find FEATURE_COMPOSITION row for this feature (most recent if multiple)
    comp_rows = [r for r in rows
                 if r.get('kind') == 'FEATURE_COMPOSITION'
                 and r.get('composite_feature_id') == feature_id]
    if not comp_rows:
        # No composition — full provenance is the creator
        grant = next((r for r in rows
                      if r.get('kind') == 'EQUITY_GRANT'
                      and r.get('feature_id') == feature_id), None)
        creator = grant.get('peer_id', '') if grant else ''
        return {creator: 1.0} if creator else {}

    # Merge component_feature_ids and component_weights across all FEATURE_COMPOSITION rows
    # (multiple rows can exist from different detection methods — merge by component)
    component_weights: dict[str, float] = {}
    for cr in comp_rows:
        ids = cr.get('component_feature_ids', [])
        weights = cr.get('component_weights', {})
        for cid in ids:
            w = float(weights.get(cid, 0.0)) if weights else 0.0
            if cid not in component_weights or w > component_weights[cid]:
                component_weights[cid] = w

    # If no weights stored, distribute equally
    if not any(component_weights.values()):
        n = len(component_weights)
        if n > 0:
            for cid in component_weights:
                component_weights[cid] = 1.0 / n

    # Normalize so total component weight ≤ 1.0
    total_w = sum(component_weights.values())
    if total_w > 1.0:
        for cid in component_weights:
            component_weights[cid] /= total_w

    # Recursively resolve each component's provenance
    result: dict[str, float] = {}
    for cid, w in component_weights.items():
        sub = resolve_provenance_weights(cid, rows, _visited)
        for peer, sub_w in sub.items():
            result[peer] = result.get(peer, 0.0) + w * sub_w

    # Composite creator keeps the novel portion
    novel_fraction = max(0.0, 1.0 - sum(component_weights.values()))
    if novel_fraction > 0.001:
        grant = next((r for r in rows
                      if r.get('kind') == 'EQUITY_GRANT'
                      and r.get('feature_id') == feature_id), None)
        creator = grant.get('peer_id', '') if grant else ''
        if creator:
            result[creator] = result.get(creator, 0.0) + novel_fraction

    # Normalize final result
    total = sum(result.values())
    if total > 0:
        result = {k: v / total for k, v in result.items()}
    return result


def composition_referral_amounts(feature_id: str, rows: list[dict],
                                  pool_units: int) -> dict[str, int]:
    """Return {peer_id: credit_units} for distributing a referral pool.

    Returns empty dict when feature has no FEATURE_COMPOSITION rows (no referral owed).
    Uses resolve_provenance_weights — handles multi-level provenance.
    Integer rounding: remainder goes to the highest-weight peer.
    """
    # Only pay referral when there is an explicit composition link
    has_composition = any(
        r.get('kind') == 'FEATURE_COMPOSITION' and r.get('composite_feature_id') == feature_id
        for r in rows
    )
    if not has_composition or pool_units <= 0:
        return {}
    weights = resolve_provenance_weights(feature_id, rows)
    if not weights:
        return {}

    # Allocate integer units
    alloc: dict[str, int] = {}
    remainder = pool_units
    sorted_peers = sorted(weights.items(), key=lambda x: -x[1])
    for peer, w in sorted_peers:
        units = int(pool_units * w)
        alloc[peer] = units
        remainder -= units
    # Give remainder to highest-weight peer
    if remainder > 0 and sorted_peers:
        alloc[sorted_peers[0][0]] = alloc.get(sorted_peers[0][0], 0) + remainder
    return {p: u for p, u in alloc.items() if u > 0}
