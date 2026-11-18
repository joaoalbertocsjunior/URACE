"""Multi-node chunk concentration guard.

Detects when a cluster of closely-registered nodes collectively hold
too many chunks of the same feature (potential cartel reconstruction).
"""
from __future__ import annotations
import datetime
import time
from .p2p_constants import UNIT as _UNIT

# Threshold: fraction of n_total chunks above which a cluster can deny reconstruction.
# RS(n_data=4, n_parity=2): reconstruction needs 4/6 chunks.
# A cluster holding > n_parity/n_total = 2/6 ≈ 0.334 of slots can block availability
# if they also meet the slot-count condition (>= n_parity+1 slots).
_N_DATA_DEFAULT = 4
_N_PARITY_DEFAULT = 2
_N_TOTAL_DEFAULT = 6
DEFAULT_MAX_CHUNK_CONCENTRATION = (_N_TOTAL_DEFAULT - _N_DATA_DEFAULT) / _N_TOTAL_DEFAULT  # 2/6 ≈ 0.334
DEFAULT_MAX_CLUSTER_SLOTS = _N_PARITY_DEFAULT + 1  # 3 — controlling >= 3 slots blocks reconstruction
DEFAULT_REGISTRATION_WINDOW_SECS = 300


def check_chunk_concentration(
    feature_id: str,
    rows: list[dict],
    n_total: int = _N_TOTAL_DEFAULT,
    n_data: int = _N_DATA_DEFAULT,
    threshold: float = DEFAULT_MAX_CHUNK_CONCENTRATION,
    registration_window_secs: float = DEFAULT_REGISTRATION_WINDOW_SECS,
) -> dict:
    """Check if any cluster of co-registered peers can deny reconstruction.

    Two independent conditions — either alone is sufficient to flag:
    1. Coverage: cluster holds > threshold fraction of distinct chunk indices
    2. Slot count: cluster controls >= n_parity+1 replica slots (enough to block RS reconstruction)

    Returns {'flagged': True, 'cluster': [...], 'concentration': float,
             'slot_count': int, 'flag_reason': str, 'feature_id': str}
    or {'flagged': False}.
    """
    # Gather BUNDLE_REPLICA_REGISTERED rows for this feature
    replica_rows = [
        r for r in rows
        if r.get('kind') == 'BUNDLE_REPLICA_REGISTERED'
        and r.get('feature_id') == feature_id
    ]
    if not replica_rows:
        return {'flagged': False}

    # Build {peer_id: set(chunk_indices)}
    peer_chunks: dict[str, set] = {}
    peer_time: dict[str, float] = {}
    for r in replica_rows:
        pid = r.get('replica_peer_id', '')
        if not pid:
            continue
        raw_indices = r.get('chunk_indices')
        if raw_indices is not None:
            if isinstance(raw_indices, str):
                indices = set(int(x.strip()) for x in raw_indices.split(',') if x.strip().isdigit())
            else:
                indices = set(int(x) for x in raw_indices)
        else:
            # No chunk_indices specified — holds all chunks
            indices = set(range(n_total))
        peer_chunks[pid] = peer_chunks.get(pid, set()) | indices
        at_unix = float(r.get('at_unix', 0))
        # Use earliest registration time per peer
        if pid not in peer_time or at_unix < peer_time[pid]:
            peer_time[pid] = at_unix

    peers = list(peer_chunks.keys())
    if not peers:
        return {'flagged': False}

    # Find clusters: groups of peers that all registered within registration_window_secs
    # of each other (pairwise within-window → connected component)
    # Build adjacency: two peers are "co-registered" if |t_a - t_b| <= window
    n = len(peers)
    adj: dict[str, set] = {p: set() for p in peers}
    for i in range(n):
        for j in range(i + 1, n):
            pa, pb = peers[i], peers[j]
            ta = peer_time.get(pa, 0)
            tb = peer_time.get(pb, 0)
            if abs(ta - tb) <= registration_window_secs:
                adj[pa].add(pb)
                adj[pb].add(pa)

    # Connected components (clusters)
    visited: set = set()
    clusters: list[list[str]] = []
    for p in peers:
        if p in visited:
            continue
        # BFS
        cluster = []
        queue = [p]
        while queue:
            cur = queue.pop()
            if cur in visited:
                continue
            visited.add(cur)
            cluster.append(cur)
            queue.extend(adj[cur] - visited)
        clusters.append(cluster)

    # Check each cluster — two independent conditions
    n_parity = n_total - n_data
    max_safe_slots = n_parity  # cluster with > n_parity slots can block reconstruction
    best_flagged = None
    best_concentration = 0.0
    best_slot_count = 0
    best_reason = ''
    for cluster in clusters:
        union_chunks: set = set()
        for pid in cluster:
            union_chunks |= peer_chunks.get(pid, set())
        concentration = len(union_chunks) / max(1, n_total)
        slot_count = len(cluster)
        # Condition 1: chunk coverage exceeds reconstruction threshold
        coverage_flagged = concentration > threshold
        # Condition 2: slot count >= n_parity+1 — enough nodes to deny n_parity chunks
        slot_flagged = slot_count > max_safe_slots
        if (coverage_flagged or slot_flagged) and concentration >= best_concentration:
            best_concentration = concentration
            best_slot_count = slot_count
            best_flagged = cluster
            if coverage_flagged and slot_flagged:
                best_reason = 'coverage_and_slot_count'
            elif coverage_flagged:
                best_reason = 'coverage'
            else:
                best_reason = 'slot_count'

    if best_flagged is not None:
        return {
            'flagged': True,
            'cluster': sorted(best_flagged),
            'concentration': best_concentration,
            'slot_count': best_slot_count,
            'flag_reason': best_reason,
            'feature_id': feature_id,
        }
    return {'flagged': False}


def apply_chunk_concentration_penalty(
    exchange,
    feature_id: str,
    n_total: int = _N_TOTAL_DEFAULT,
    n_data: int = _N_DATA_DEFAULT,
    threshold: float = DEFAULT_MAX_CHUNK_CONCENTRATION,
    registration_window_secs: float = DEFAULT_REGISTRATION_WINDOW_SECS,
) -> dict:
    """Check and apply cartel chunk concentration penalty.

    Idempotent: skips if CARTEL_CHUNK_CONCENTRATION already exists for this
    feature_id + cluster within 24h.
    Returns {'applied': bool, 'cluster': [...], 'concentration': float}.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return {'applied': False, 'cluster': [], 'concentration': 0.0}

    result = check_chunk_concentration(
        feature_id, rows, n_total=n_total, n_data=n_data,
        threshold=threshold, registration_window_secs=registration_window_secs,
    )
    if not result.get('flagged'):
        return {'applied': False, 'cluster': [], 'concentration': 0.0}

    cluster = result['cluster']
    concentration = result['concentration']
    now = time.time()
    window_24h = now - 86400

    # Idempotency: skip if same feature_id + cluster penalized within 24h
    cluster_set = frozenset(cluster)
    for r in rows:
        if (
            r.get('kind') == 'CARTEL_CHUNK_CONCENTRATION'
            and r.get('feature_id') == feature_id
            and float(r.get('at_unix', 0)) > window_24h
        ):
            existing_cluster = frozenset(r.get('cluster_peers', []))
            if existing_cluster == cluster_set:
                return {'applied': False, 'cluster': cluster, 'concentration': concentration}

    at_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Emit CARTEL_CHUNK_CONCENTRATION row
    exchange.append_audit_row({
        'kind': 'CARTEL_CHUNK_CONCENTRATION',
        'feature_id': feature_id,
        'cluster_peers': cluster,
        'concentration': concentration,
        'slot_count': result.get('slot_count', len(cluster)),
        'flag_reason': result.get('flag_reason', ''),
        'at_unix': now,
        'at': at_iso,
    })

    # Emit CREDIT_DELTA penalty for each cluster peer
    # penalty: 1-10 tokens per cluster peer, proportional to excess concentration above threshold
    _excess_conc = max(0.0, concentration - threshold)
    _penalty_units = max(_UNIT, int(_excess_conc * 10 * _UNIT))  # 1-10 tokens
    for p in cluster:
        exchange.append_audit_row({
            'kind': 'CREDIT_DELTA',
            'direction': 'cartel_chunk_penalty',
            'peer': p,
            'amount_units': -_penalty_units,
            'feature_id': feature_id,
            'concentration': round(concentration, 4),
            'at_unix': now,
            'at': at_iso,
        })

    return {'applied': True, 'cluster': cluster, 'concentration': concentration}


def register_replica_guard(
    exchange,
    feature_id: str,
    replica_peer_id: str,
    n_total: int = _N_TOTAL_DEFAULT,
    n_data: int = _N_DATA_DEFAULT,
    threshold: float = DEFAULT_MAX_CHUNK_CONCENTRATION,
    registration_window_secs: float = DEFAULT_REGISTRATION_WINDOW_SECS,
    chunk_indices=None,
) -> None:
    """Pre-registration guard: raises ValueError if adding this peer would push
    any existing cluster above threshold.

    Call before emitting BUNDLE_REPLICA_REGISTERED.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return  # can't check — allow

    # Build a synthetic future row for this peer
    now = time.time()
    if chunk_indices is not None:
        if isinstance(chunk_indices, str):
            indices_list = [int(x.strip()) for x in chunk_indices.split(',') if x.strip().isdigit()]
        else:
            indices_list = list(chunk_indices)
        ci_value = ','.join(str(x) for x in indices_list)
    else:
        ci_value = None  # will default to all chunks in check_chunk_concentration

    synthetic_row = {
        'kind': 'BUNDLE_REPLICA_REGISTERED',
        'feature_id': feature_id,
        'replica_peer_id': replica_peer_id,
        'at_unix': now,
    }
    if ci_value is not None:
        synthetic_row['chunk_indices'] = ci_value

    future_rows = list(rows) + [synthetic_row]
    result = check_chunk_concentration(
        feature_id, future_rows, n_total=n_total, n_data=n_data,
        threshold=threshold, registration_window_secs=registration_window_secs,
    )
    if result.get('flagged') and replica_peer_id in result.get('cluster', []):
        reason = result.get('flag_reason', '')
        raise ValueError(
            f'Registering {replica_peer_id!r} as replica for {feature_id!r} would push '
            f'cluster {result["cluster"]} to concentration {result["concentration"]:.2f} '
            f'({result.get("slot_count",0)} slots, reason={reason!r}, threshold={threshold:.2f}) '
            f'— registration blocked to prevent availability hijack'
        )


# ---------------------------------------------------------------------------
# Mutual-approval quality cartel detection (III.2)
# ---------------------------------------------------------------------------

def detect_mutual_approval_cartel(
    rows: list[dict],
    min_scc_size: int = 3,
    min_mutual_density: float = 0.70,
) -> list[dict]:
    """Detect mutual-approval cartel rings via strongly-connected components (SCCs).

    Builds a directed graph from QUALITY_VERIFICATION rows (issuer → subject).
    SCCs with ≥ min_scc_size nodes and bidirectional density ≥ min_mutual_density
    are flagged as suspected cartels. Confidence = (density - 0.70) / 0.30 → [0, 1].

    Returns list of flagged cartel groups:
      [{'members': [...], 'density': float, 'confidence': float, 'scc_size': int}, ...]
    """
    from collections import defaultdict

    # Build adjacency: who verified whom
    out_edges: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r.get('kind') == 'QUALITY_VERIFICATION':
            issuer = r.get('peer') or r.get('issuer')
            subject = r.get('subject_peer_id') or r.get('subject_peer')
            if issuer and subject and issuer != subject:
                out_edges[issuer].add(subject)

    all_peers = set(out_edges.keys()) | {v for vs in out_edges.values() for v in vs}
    if len(all_peers) < min_scc_size:
        return []

    # Kosaraju's SCC algorithm
    peer_list = list(all_peers)
    idx = {p: i for i, p in enumerate(peer_list)}
    n = len(peer_list)
    adj = [[] for _ in range(n)]
    radj = [[] for _ in range(n)]
    for src, dsts in out_edges.items():
        s = idx.get(src)
        if s is None:
            continue
        for dst in dsts:
            d = idx.get(dst)
            if d is None:
                continue
            adj[s].append(d)
            radj[d].append(s)

    visited = [False] * n
    order: list[int] = []

    def _dfs1(v: int) -> None:
        stack = [(v, 0)]
        while stack:
            u, state = stack.pop()
            if state == 0:
                if visited[u]:
                    continue
                visited[u] = True
                stack.append((u, 1))
                for w in adj[u]:
                    if not visited[w]:
                        stack.append((w, 0))
            else:
                order.append(u)

    for i in range(n):
        if not visited[i]:
            _dfs1(i)

    comp = [-1] * n
    c = 0

    def _dfs2(v: int, label: int) -> None:
        stack = [v]
        while stack:
            u = stack.pop()
            if comp[u] != -1:
                continue
            comp[u] = label
            for w in radj[u]:
                if comp[w] == -1:
                    stack.append(w)

    for v in reversed(order):
        if comp[v] == -1:
            _dfs2(v, c)
            c += 1

    # Group by SCC
    scc_groups: dict[int, list[str]] = defaultdict(list)
    for i, label in enumerate(comp):
        scc_groups[label].append(peer_list[i])

    flagged = []
    for label, members in scc_groups.items():
        if len(members) < min_scc_size:
            continue
        member_set = set(members)
        # Count actual bidirectional edges within the SCC
        possible_edges = len(members) * (len(members) - 1)
        actual_edges = sum(
            1 for src in members for dst in out_edges.get(src, set())
            if dst in member_set and dst != src
        )
        density = actual_edges / possible_edges if possible_edges > 0 else 0.0
        if density >= min_mutual_density:
            confidence = min(1.0, (density - min_mutual_density) / (1.0 - min_mutual_density))
            flagged.append({
                'members': sorted(members),
                'scc_size': len(members),
                'density': round(density, 3),
                'confidence': round(confidence, 3),
            })

    return flagged
