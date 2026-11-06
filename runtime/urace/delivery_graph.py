"""Multi-deliverer proportional delivery fee distribution.

For large networks where artifact chunks are spread across many replica holders,
each contributor receives a micro-payment proportional to their chunk coverage.

At millions of peers this enables the BitTorrent-like delivery economy:
every seeder earns proportionally to what they seed.
"""

DEFAULT_N_TOTAL = 6  # n_data=4 + n_parity=2


def delivery_weights(feature_id: str, rows: list[dict],
                     original_creator: str, n_total: int = DEFAULT_N_TOTAL) -> dict[str, float]:
    """Return {peer_id: weight} for delivery fee distribution.

    Only includes non-creator replica holders. Weights sum to 1.0.
    If no replicas registered: returns {} (creator delivers, no delivery fee).

    Weight = chunks_held_by_peer / n_total (normalized across contributors).
    """
    replicas = [
        r for r in rows
        if r.get('kind') == 'BUNDLE_REPLICA_REGISTERED'
        and r.get('feature_id') == feature_id
        and r.get('replica_peer_id', '') != original_creator
        and r.get('replica_peer_id', '')
    ]
    if not replicas:
        return {}

    # Compute raw chunk coverage per peer (last registration wins per peer)
    peer_chunks: dict[str, set] = {}
    for r in replicas:
        pid = r['replica_peer_id']
        indices = r.get('chunk_indices')
        if isinstance(indices, list) and indices:
            peer_chunks[pid] = set(indices)
        else:
            # No chunk_indices declared → assume full coverage
            peer_chunks[pid] = set(range(n_total))

    if not peer_chunks:
        return {}

    # Raw weights: fraction of n_total covered
    raw = {pid: len(chunks) / n_total for pid, chunks in peer_chunks.items()}
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {pid: w / total for pid, w in raw.items()}


def delivery_fee_amounts(feature_id: str, rows: list[dict],
                         original_creator: str, price: int,
                         delivery_fee_fraction: float = 0.10,
                         n_total: int = DEFAULT_N_TOTAL) -> dict[str, int]:
    """Return {peer_id: fee_units} for delivery fee distribution.

    Returns {} if original creator delivers (no replicas needed).
    Integer rounding: remainder goes to highest-weight peer.
    """
    weights = delivery_weights(feature_id, rows, original_creator, n_total)
    if not weights or price <= 0:
        return {}

    pool = max(1, int(price * delivery_fee_fraction))
    alloc: dict[str, int] = {}
    remainder = pool
    for pid, w in sorted(weights.items(), key=lambda x: -x[1]):
        units = int(pool * w)
        alloc[pid] = units
        remainder -= units
    # Remainder to highest-weight peer
    top = max(weights, key=weights.get)
    alloc[top] = alloc.get(top, 0) + remainder
    return {p: u for p, u in alloc.items() if u > 0}
