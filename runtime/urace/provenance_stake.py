"""Asset Provenance Staking (APS).

Mint stake: creator locks tokens at grant time.
Challenge window: any peer can challenge within N days.
Resolution: upheld → stake slashed to challenger+base owner, grant revoked.
            rejected → challenger stake slashed, creator stake returned.
Quorum resolution (cross-node): fetch_quorum_verdicts() polls bootstrap peers and
resolve_challenge() uses remote majority when bootstrap_peers is provided.
"""
import hashlib, time
from datetime import datetime, timezone

SCHEMA = 'urace-provenance-stake-v1'
MINT_STAKE_DEFAULT = 3        # matches bootstrap grant — configurable via policy
CHALLENGER_STAKE_DEFAULT = 2  # cheaper to challenge than to mint
CHALLENGE_WINDOW_DAYS_DEFAULT = 30
SLASH_BOUNTY_FRACTION = 0.50  # 50% of slashed stake to challenger, 50% to base owner


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _now():
    return time.time()


def _challenge_id(feature_id: str, challenger_peer_id: str, at_unix: float) -> str:
    return hashlib.sha256(f'{feature_id}:{challenger_peer_id}:{at_unix}'.encode()).hexdigest()


def get_mint_stake_units(config: dict) -> int:
    return int(config.get('p2p', {}).get('mint_stake_units', MINT_STAKE_DEFAULT))


def get_challenge_window_days(config: dict) -> int:
    return int(config.get('p2p', {}).get('challenge_window_days', CHALLENGE_WINDOW_DAYS_DEFAULT))


def _credit_balance(rows, peer_id: str) -> int:
    """Sum all CREDIT_DELTA amount_units for peer_id."""
    total = 0
    for r in rows:
        if r.get('kind') == 'CREDIT_DELTA':
            if r.get('peer') == peer_id or r.get('receiver_peer_id') == peer_id:
                total += int(r.get('amount_units', 0))
    return total


def lock_mint_stake(exchange, feature_id: str, staker_peer_id: str, stake_units: int, challenge_window_days: int) -> dict:
    """Lock creator's mint stake. Deducts from balance immediately.

    Returns the MINT_STAKE_LOCKED row or raises ValueError if insufficient balance.
    Idempotent: returns existing row if already locked.
    """
    rows = exchange.audit_rows()
    existing = next((r for r in rows if r.get('kind') == 'MINT_STAKE_LOCKED' and r.get('feature_id') == feature_id), None)
    if existing:
        return existing
    balance = _credit_balance(rows, staker_peer_id)
    if balance < stake_units:
        raise ValueError(f'Insufficient balance to lock mint stake: have {balance}, need {stake_units}. Earn tokens first or lower mint_stake_units in policy.')
    t = _now()
    deadline = t + challenge_window_days * 86400
    lock_row = {
        'kind': 'MINT_STAKE_LOCKED',
        'schema': SCHEMA,
        'feature_id': feature_id,
        'staker_peer_id': staker_peer_id,
        'stake_units': stake_units,
        'challenge_window_days': challenge_window_days,
        'challenge_deadline_unix': deadline,
        'at_unix': t,
        'at': _now_iso(),
    }
    exchange.append_audit_row(lock_row)
    exchange.append_audit_row({
        'kind': 'CREDIT_DELTA',
        'direction': 'mint_stake_locked',
        'peer': staker_peer_id,
        'amount_units': -stake_units,
        'feature_id': feature_id,
        'at_unix': t,
        'at': _now_iso(),
    })
    return lock_row


def release_mint_stake(exchange, feature_id: str) -> bool:
    """Return locked stake to creator after challenge window expires without upheld challenge.

    Returns True if released, False if already released, raises ValueError if window still open
    or if an upheld challenge exists.
    """
    rows = exchange.audit_rows()
    lock_row = next((r for r in rows if r.get('kind') == 'MINT_STAKE_LOCKED' and r.get('feature_id') == feature_id), None)
    if not lock_row:
        return False
    already_released = any(r.get('kind') == 'MINT_STAKE_RELEASED' and r.get('feature_id') == feature_id for r in rows)
    if already_released:
        return False
    already_slashed = any(r.get('kind') == 'MINT_STAKE_SLASHED' and r.get('feature_id') == feature_id for r in rows)
    if already_slashed:
        raise ValueError(f'Stake for {feature_id!r} was already slashed — cannot release.')
    deadline = float(lock_row.get('challenge_deadline_unix', 0))
    if _now() < deadline:
        days_left = (deadline - _now()) / 86400
        raise ValueError(f'Challenge window still open for {feature_id!r} ({days_left:.1f} days remaining).')
    upheld = any(r.get('kind') == 'PROVENANCE_CHALLENGE_RESOLVED' and r.get('feature_id') == feature_id and r.get('verdict') == 'upheld' for r in rows)
    if upheld:
        raise ValueError(f'Challenge was upheld for {feature_id!r} — stake already distributed.')
    t = _now()
    exchange.append_audit_row({'kind': 'MINT_STAKE_RELEASED', 'schema': SCHEMA, 'feature_id': feature_id, 'staker_peer_id': lock_row['staker_peer_id'], 'stake_units': lock_row['stake_units'], 'reason': 'challenge_window_expired', 'at_unix': t, 'at': _now_iso()})
    exchange.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'mint_stake_released', 'peer': lock_row['staker_peer_id'], 'amount_units': lock_row['stake_units'], 'feature_id': feature_id, 'at_unix': t, 'at': _now_iso()})
    return True


def file_challenge(exchange, feature_id: str, challenger_peer_id: str,
                   evidence: str = '', reference_feature_id: str = '',
                   challenger_stake_units: int = CHALLENGER_STAKE_DEFAULT) -> dict:
    """File a provenance challenge against a minted feature.

    Auto-upholds immediately if FEATURE_COMPOSITION(auto_detected=True) already exists
    for this feature (the system already detected the derivation).
    Returns the PROVENANCE_CHALLENGE row.
    """
    rows = exchange.audit_rows()
    lock_row = next((r for r in rows if r.get('kind') == 'MINT_STAKE_LOCKED' and r.get('feature_id') == feature_id), None)
    if not lock_row:
        raise ValueError(f'Feature {feature_id!r} has no mint stake — cannot challenge.')
    deadline = float(lock_row.get('challenge_deadline_unix', 0))
    if _now() > deadline:
        raise ValueError(f'Challenge window for {feature_id!r} has expired.')
    revoked = any(r.get('kind') == 'EQUITY_GRANT_REVOKED' and r.get('feature_id') == feature_id for r in rows)
    if revoked:
        raise ValueError(f'Feature {feature_id!r} is already revoked.')
    existing_challenge = next((r for r in rows if r.get('kind') == 'PROVENANCE_CHALLENGE' and r.get('feature_id') == feature_id and r.get('status') == 'pending'), None)
    if existing_challenge:
        raise ValueError(f'A pending challenge already exists for {feature_id!r}: {existing_challenge.get("challenge_id")}')
    balance = _credit_balance(rows, challenger_peer_id)
    if balance < challenger_stake_units:
        raise ValueError(f'Insufficient balance to file challenge: have {balance}, need {challenger_stake_units}.')
    t = _now()
    cid = _challenge_id(feature_id, challenger_peer_id, t)
    challenge_row = {
        'kind': 'PROVENANCE_CHALLENGE',
        'schema': SCHEMA,
        'challenge_id': cid,
        'feature_id': feature_id,
        'challenger_peer_id': challenger_peer_id,
        'challenger_stake_units': challenger_stake_units,
        'reference_feature_id': reference_feature_id,
        'evidence': evidence,
        'status': 'pending',
        'at_unix': t,
        'at': _now_iso(),
    }
    exchange.append_audit_row(challenge_row)
    exchange.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'challenge_stake_locked', 'peer': challenger_peer_id, 'amount_units': -challenger_stake_units, 'feature_id': feature_id, 'challenge_id': cid, 'at_unix': t, 'at': _now_iso()})
    # Auto-uphold if system already detected derivation
    auto_comp = next((r for r in rows if r.get('kind') == 'FEATURE_COMPOSITION' and r.get('composite_feature_id') == feature_id and r.get('auto_detected')), None)
    if auto_comp:
        ref_fid = reference_feature_id or (auto_comp.get('component_feature_ids') or [''])[0]
        _resolve(exchange, cid, feature_id, 'upheld', 'auto_detected_composition', ref_fid,
                 lock_row, challenger_peer_id, challenger_stake_units)
    return challenge_row


def fetch_quorum_verdicts(exchange, feature_id: str, challenge_id: str, bootstrap_peers: list) -> list:
    """Fetch APS_VERDICT rows for a challenge from bootstrap peers via HTTP GET."""
    import urllib.request as _ur, json as _j, urllib.parse as _up
    remote_verdicts = []
    for endpoint in bootstrap_peers[:3]:
        try:
            params = _up.urlencode({'feature_id': feature_id, 'challenge_id': challenge_id})
            url = f"{endpoint.rstrip('/')}/urace/rpc/v1/find-node?{params}"
            req = _ur.Request(url, headers={"Accept": "application/json"})
            with _ur.urlopen(req, timeout=10) as resp:
                data = _j.loads(resp.read(65536))
                # Expect {verdicts: [{verdict: "upheld"|"rejected", peer_id: ...}, ...]}
                remote_verdicts.extend(data.get('verdicts', []))
        except Exception:
            pass  # peer unreachable — continue with local resolution
    return remote_verdicts


def resolve_challenge(exchange, challenge_id: str, verdict: str,
                      resolver_peer_id: str = 'local',
                      resolver_type: str = 'local',
                      bootstrap_peers: list | None = None) -> dict:
    """Resolve a pending challenge. verdict = 'upheld' | 'rejected'.

    upheld: creator stake slashed, grant revoked, challenger stake returned + bounty.
    rejected: challenger stake slashed (stays deducted), creator stake released.

    When bootstrap_peers is non-empty, fetch remote quorum verdicts and use majority
    to override local verdict if remote majority disagrees.
    """
    rows = exchange.audit_rows()
    challenge_row = next((r for r in rows if r.get('kind') == 'PROVENANCE_CHALLENGE' and r.get('challenge_id') == challenge_id), None)
    if not challenge_row:
        raise ValueError(f'Challenge {challenge_id!r} not found.')
    already_resolved = any(r.get('kind') == 'PROVENANCE_CHALLENGE_RESOLVED' and r.get('challenge_id') == challenge_id for r in rows)
    if already_resolved:
        raise ValueError(f'Challenge {challenge_id!r} already resolved.')
    if verdict not in ('upheld', 'rejected'):
        raise ValueError(f'verdict must be upheld or rejected, got {verdict!r}')
    feature_id = challenge_row['feature_id']
    lock_row = next((r for r in rows if r.get('kind') == 'MINT_STAKE_LOCKED' and r.get('feature_id') == feature_id), None)
    if not lock_row:
        raise ValueError(f'No MINT_STAKE_LOCKED for feature {feature_id!r}.')

    final_verdict = verdict
    final_resolver_type = resolver_type
    if bootstrap_peers:
        remote_verdicts = fetch_quorum_verdicts(exchange, feature_id, challenge_id, bootstrap_peers)
        if remote_verdicts:
            upheld_count = sum(1 for v in remote_verdicts if v.get('verdict') == 'upheld')
            rejected_count = sum(1 for v in remote_verdicts if v.get('verdict') == 'rejected')
            if upheld_count != rejected_count:  # not a tie
                remote_majority = 'upheld' if upheld_count > rejected_count else 'rejected'
                if remote_majority != verdict:
                    final_verdict = remote_majority
                    final_resolver_type = 'remote_quorum'

    return _resolve(exchange, challenge_id, feature_id, final_verdict, final_resolver_type,
                    challenge_row.get('reference_feature_id', ''), lock_row,
                    challenge_row['challenger_peer_id'], challenge_row['challenger_stake_units'])


def _resolve(exchange, challenge_id, feature_id, verdict, resolver_type, reference_feature_id,
             lock_row, challenger_peer_id, challenger_stake_units):
    rows = exchange.audit_rows()
    t = _now()
    exchange.append_audit_row({'kind': 'PROVENANCE_CHALLENGE_RESOLVED', 'schema': SCHEMA, 'challenge_id': challenge_id, 'feature_id': feature_id, 'verdict': verdict, 'resolver_type': resolver_type, 'at_unix': t, 'at': _now_iso()})
    if verdict == 'upheld':
        stake_units = lock_row['stake_units']
        staker = lock_row['staker_peer_id']
        bounty = max(1, int(stake_units * SLASH_BOUNTY_FRACTION))
        compensation = stake_units - bounty
        exchange.append_audit_row({'kind': 'MINT_STAKE_SLASHED', 'schema': SCHEMA, 'feature_id': feature_id, 'staker_peer_id': staker, 'stake_units': stake_units, 'challenge_id': challenge_id, 'challenger_bounty': bounty, 'base_owner_compensation': compensation, 'at_unix': t, 'at': _now_iso()})
        # Distribute: challenger bounty
        exchange.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'challenge_bounty', 'peer': challenger_peer_id, 'amount_units': bounty, 'feature_id': feature_id, 'challenge_id': challenge_id, 'at_unix': t, 'at': _now_iso()})
        # Return challenger's locked stake
        exchange.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'challenge_stake_returned', 'peer': challenger_peer_id, 'amount_units': challenger_stake_units, 'feature_id': feature_id, 'challenge_id': challenge_id, 'at_unix': t, 'at': _now_iso()})
        # Base owner compensation (if reference known)
        if reference_feature_id and compensation > 0:
            base_grant = next((r for r in rows if r.get('kind') == 'EQUITY_GRANT' and r.get('feature_id') == reference_feature_id), None)
            base_owner = base_grant.get('peer_id', '') if base_grant else ''
            if base_owner:
                exchange.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'provenance_compensation', 'peer': base_owner, 'amount_units': compensation, 'feature_id': feature_id, 'reference_feature_id': reference_feature_id, 'challenge_id': challenge_id, 'at_unix': t, 'at': _now_iso()})
        # Revoke the grant
        exchange.append_audit_row({'kind': 'EQUITY_GRANT_REVOKED', 'feature_id': feature_id, 'revoked_by_challenge_id': challenge_id, 'reason': 'provenance_challenge_upheld', 'at_unix': t, 'at': _now_iso()})
    else:  # rejected
        # Challenger stake was already deducted — stays slashed (no return)
        # Release creator's locked stake
        exchange.append_audit_row({'kind': 'MINT_STAKE_RELEASED', 'schema': SCHEMA, 'feature_id': feature_id, 'staker_peer_id': lock_row['staker_peer_id'], 'stake_units': lock_row['stake_units'], 'reason': 'challenge_rejected', 'at_unix': t, 'at': _now_iso()})
        exchange.append_audit_row({'kind': 'CREDIT_DELTA', 'direction': 'mint_stake_released', 'peer': lock_row['staker_peer_id'], 'amount_units': lock_row['stake_units'], 'feature_id': feature_id, 'challenge_id': challenge_id, 'at_unix': t, 'at': _now_iso()})
    resolved_row = next((r for r in exchange.audit_rows() if r.get('kind') == 'PROVENANCE_CHALLENGE_RESOLVED' and r.get('challenge_id') == challenge_id), None)
    return resolved_row or {}


def challenge_status(exchange, feature_id: str) -> dict:
    """Return current staking and challenge status for a feature."""
    rows = exchange.audit_rows()
    lock = next((r for r in rows if r.get('kind') == 'MINT_STAKE_LOCKED' and r.get('feature_id') == feature_id), None)
    challenge = next((r for r in rows if r.get('kind') == 'PROVENANCE_CHALLENGE' and r.get('feature_id') == feature_id), None)
    resolved = next((r for r in rows if r.get('kind') == 'PROVENANCE_CHALLENGE_RESOLVED' and r.get('feature_id') == feature_id), None)
    revoked = any(r.get('kind') == 'EQUITY_GRANT_REVOKED' and r.get('feature_id') == feature_id for r in rows)
    slashed = next((r for r in rows if r.get('kind') == 'MINT_STAKE_SLASHED' and r.get('feature_id') == feature_id), None)
    released = next((r for r in rows if r.get('kind') == 'MINT_STAKE_RELEASED' and r.get('feature_id') == feature_id), None)
    window_open = False
    days_left = 0.0
    if lock and not resolved and not slashed and not released:
        deadline = float(lock.get('challenge_deadline_unix', 0))
        window_open = _now() < deadline
        days_left = max(0.0, (deadline - _now()) / 86400)
    return {
        'schema': SCHEMA,
        'feature_id': feature_id,
        'staked': lock is not None,
        'stake_units': lock.get('stake_units', 0) if lock else 0,
        'window_open': window_open,
        'days_remaining': round(days_left, 1),
        'challenge_pending': challenge is not None and resolved is None,
        'challenge_id': challenge.get('challenge_id') if challenge else None,
        'verdict': resolved.get('verdict') if resolved else None,
        'revoked': revoked,
        'slashed': slashed is not None,
        'released': released is not None,
    }
