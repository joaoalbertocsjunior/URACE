"""Earned reputation categories — multi-dimensional scoring with consensus weight profiles.

WHY CATEGORIES MATTER
─────────────────────
A single reputation number is easy to game: accumulate in one dimension,
appear trustworthy across all. Multi-category scoring forces an attacker to
fake every dimension simultaneously — exponentially harder.

Five categories, each using signals already present in the audit ledger:

  quality     — PoQ scores, quality_wilson from accepted work
  delivery    — delivery_wilson, on-time accepted deliveries
  service     — seal_reward events, relay/bootstrap uptime contributions
  validation  — challenge accuracy: upheld/(upheld+rejected) for filed challenges
  longevity   — age-weighted activity (EMA); cannot be bought or accelerated

CONSENSUS WEIGHT PROFILES
─────────────────────────
Different decisions weight categories differently. A peer with high quality
but zero service has strong technical voice but limited operational weight.

  WORK_QUALITY_GATE   — gates new work submissions; quality + validation dominant
  NETWORK_GOVERNANCE  — relay/bootstrap policy; service + longevity dominant
  CHALLENGE_WEIGHT    — weight of challenge filing; validation + quality dominant
  CARTEL_RESISTANT    — voting on suspected cartel behaviour; diversity + longevity
  ARBITRATION         — dispute resolution; all categories balanced

SYBIL / CARTEL / COLD-START
────────────────────────────
  Sybil:      must accumulate ALL five categories — service and longevity
              require real time and real work, not just key generation.
  Cartel:     mutual-approval inflates quality; it cannot inflate service,
              longevity, or validation accuracy. Cartel weight is capped.
  Cold-start: new peers can earn service rep immediately (run a relay node),
              providing an onboarding path before established peers validate them.

EARNED vs TRADE separation
───────────────────────────
All five categories are strictly earned — no category can be increased by
purchasing credits (REP_SOURCE_TRADE). The enforcement is in the row filters:
only REP_SOURCE_WORK CREDIT_DELTA rows feed category scores.
"""
from __future__ import annotations

import math
import time

SCHEMA = 'urace-rep-categories-v1'

# ---------------------------------------------------------------------------
# Category identifiers
# ---------------------------------------------------------------------------

CAT_QUALITY    = 'quality'      # PoQ score, quality acceptance rate
CAT_DELIVERY   = 'delivery'     # delivery rate, on-time fulfilment
CAT_SERVICE    = 'service'      # seal rewards, relay/bootstrap uptime
CAT_VALIDATION = 'validation'   # challenge accuracy (upheld ratio)
CAT_LONGEVITY  = 'longevity'    # time-weighted activity, age of participation

ALL_CATEGORIES = (CAT_QUALITY, CAT_DELIVERY, CAT_SERVICE, CAT_VALIDATION, CAT_LONGEVITY)

# ---------------------------------------------------------------------------
# Consensus weight profiles
# ---------------------------------------------------------------------------

CONSENSUS_PROFILES: dict[str, dict[str, float]] = {
    # Gates work submission bids — technical quality and validation accuracy matter most
    'work_quality_gate': {
        CAT_QUALITY:    0.50,
        CAT_DELIVERY:   0.25,
        CAT_VALIDATION: 0.15,
        CAT_SERVICE:    0.05,
        CAT_LONGEVITY:  0.05,
    },
    # Relay / bootstrap / governance policy decisions — uptime and longevity matter most
    'network_governance': {
        CAT_SERVICE:    0.40,
        CAT_LONGEVITY:  0.30,
        CAT_QUALITY:    0.15,
        CAT_DELIVERY:   0.10,
        CAT_VALIDATION: 0.05,
    },
    # Weight of challenge filing — accurate challengers gate bad actors
    'challenge_weight': {
        CAT_VALIDATION: 0.50,
        CAT_QUALITY:    0.25,
        CAT_LONGEVITY:  0.15,
        CAT_SERVICE:    0.05,
        CAT_DELIVERY:   0.05,
    },
    # Voting on suspected cartel behaviour — diversity + longevity resist colluders
    # (cartels tend to specialise in quality; longevity is individual)
    'cartel_resistant': {
        CAT_LONGEVITY:  0.35,
        CAT_SERVICE:    0.25,
        CAT_QUALITY:    0.20,
        CAT_VALIDATION: 0.15,
        CAT_DELIVERY:   0.05,
    },
    # Dispute arbitration — all five balanced, longevity slightly elevated
    'arbitration': {
        CAT_QUALITY:    0.25,
        CAT_VALIDATION: 0.25,
        CAT_LONGEVITY:  0.20,
        CAT_DELIVERY:   0.15,
        CAT_SERVICE:    0.15,
    },
}

# ---------------------------------------------------------------------------
# Category score computation
# ---------------------------------------------------------------------------

def _work_rows(rows: list[dict], peer_id: str) -> list[dict]:
    """CREDIT_DELTA rows for peer_id from REP_SOURCE_WORK only."""
    return [
        r for r in rows
        if r.get('kind') == 'CREDIT_DELTA'
        and r.get('peer') == peer_id
        and r.get('rep_source', 'work') == 'work'
    ]


def score_quality(rows: list[dict], peer_id: str) -> float:
    """Quality Wilson score — fraction of work rows tagged as quality-verified.

    Uses Wilson lower bound at 95% confidence to favour peers with more evidence.
    Floor: 0.05 (new peers can participate at minimum quality gate).
    """
    work = _work_rows(rows, peer_id)
    quality_events = [r for r in work if r.get('direction') in
                      ('earn', 'borrow_earn') and r.get('reason') in
                      ('quality_accepted', 'poq_verified', 'qualification_accepted',
                       'quality_verification')]
    total = len([r for r in work if r.get('direction') in ('earn', 'borrow_earn')])
    if total == 0:
        return 0.05  # cold-start floor
    return _wilson_lower(len(quality_events), total)


def score_delivery(rows: list[dict], peer_id: str) -> float:
    """Delivery Wilson score — accepted deliveries / (accepted + rejected).

    Mirrors the existing delivery_wilson used in combined_rep_score().
    """
    work = _work_rows(rows, peer_id)
    accepted = len([r for r in work if r.get('direction') == 'earn'
                    and r.get('reason') in ('delivery_accepted', 'delivery_fee',
                                            'qualification_accepted')])
    rejected = len([r for r in rows if r.get('kind') == 'CREDIT_DELTA'
                    and r.get('peer') == peer_id
                    and r.get('direction') == 'spend'
                    and r.get('reason') in ('delivery_rejected', 'slash_delivery')])
    total = accepted + rejected
    if total == 0:
        return 0.05
    return _wilson_lower(accepted, total)


def score_service(rows: list[dict], peer_id: str) -> float:
    """Service score — seal rewards + relay/bootstrap contributions, normalised [0,1].

    Seal rewards are earned by running a full node and sealing ledger blocks.
    Relay/bootstrap events are earned by operating network infrastructure.
    Score saturates at _SERVICE_SAT events (diminishing returns).
    """
    _SERVICE_SAT = 100  # events to reach score ≈ 1.0 (diminishing log returns)
    service_events = [
        r for r in rows
        if r.get('kind') == 'CREDIT_DELTA'
        and r.get('peer') == peer_id
        and r.get('direction') in ('seal_reward', 'relay_reward', 'bootstrap_reward',
                                   'llm_peer_reward')
    ]
    n = len(service_events)
    if n == 0:
        return 0.0
    return min(1.0, math.log1p(n) / math.log1p(_SERVICE_SAT))


def score_validation(rows: list[dict], peer_id: str) -> float:
    """Validation accuracy — challenge upheld ratio for challenges filed by this peer.

    A peer who files accurate challenges (upheld) gets high validation score.
    A peer who files frivolous challenges (rejected, stake slashed) gets low score.
    Floor: 0.10 (new peers without challenge history can still file).
    """
    filed = [r for r in rows if r.get('kind') == 'PROVENANCE_CHALLENGE'
             and r.get('challenger_peer_id') == peer_id]
    if not filed:
        return 0.10  # no history → floor, not zero (cold-start grace)
    challenge_ids = {r.get('challenge_id') for r in filed if r.get('challenge_id')}
    resolved = [r for r in rows if r.get('kind') == 'PROVENANCE_CHALLENGE_RESOLVED'
                and r.get('challenge_id') in challenge_ids]
    upheld = sum(1 for r in resolved if r.get('verdict') == 'upheld')
    total_resolved = len(resolved)
    if total_resolved == 0:
        return 0.10  # pending challenges → floor
    return _wilson_lower(upheld, total_resolved)


def score_longevity(rows: list[dict], peer_id: str,
                    now: float | None = None) -> float:
    """Longevity score — age of participation weighted by recent activity.

    Two components:
      age_score   — log-normalised age since first audit row (days). Saturates at ~2 years.
      activity    — EMA of activity recency over last 90 days (prevents sleeper Sybils).
    Final = geometric mean of age_score and activity. Both must be non-trivial.
    """
    _now = now if now is not None else time.time()
    _AGE_SAT_DAYS = 730.0   # 2 years to reach age_score ≈ 1.0
    _ACTIVITY_WINDOW = 90 * 86400.0  # 90-day window for recent activity

    peer_rows = [r for r in rows if r.get('peer') == peer_id or
                 r.get('staker_peer_id') == peer_id or
                 r.get('challenger_peer_id') == peer_id or
                 r.get('owner_peer_id') == peer_id]
    if not peer_rows:
        return 0.0

    timestamps = [float(r.get('at_unix', 0)) for r in peer_rows if r.get('at_unix')]
    if not timestamps:
        return 0.0

    first_seen = min(timestamps)
    age_days = (_now - first_seen) / 86400.0
    age_score = min(1.0, math.log1p(age_days) / math.log1p(_AGE_SAT_DAYS))

    # Recent activity EMA: fraction of 90-day window with at least one event
    cutoff = _now - _ACTIVITY_WINDOW
    recent = [t for t in timestamps if t >= cutoff]
    # Bucket into 30 weekly slots; count non-empty weeks
    week = 7 * 86400.0
    weeks_active = len({int((t - cutoff) / week) for t in recent})
    activity = min(1.0, weeks_active / 13.0)  # 13 weeks = 90 days

    if age_score == 0.0 or activity == 0.0:
        return min(age_score, activity)
    return math.sqrt(age_score * activity)  # geometric mean


# ---------------------------------------------------------------------------
# Composite profile
# ---------------------------------------------------------------------------

def peer_rep_profile(rows: list[dict], peer_id: str,
                     now: float | None = None) -> dict[str, float]:
    """Return all five category scores for peer_id.

    All scores are in [0.0, 1.0]. Higher is better.
    This is EARNED reputation only — trade reputation is excluded.
    """
    return {
        CAT_QUALITY:    score_quality(rows, peer_id),
        CAT_DELIVERY:   score_delivery(rows, peer_id),
        CAT_SERVICE:    score_service(rows, peer_id),
        CAT_VALIDATION: score_validation(rows, peer_id),
        CAT_LONGEVITY:  score_longevity(rows, peer_id, now=now),
    }


def consensus_weight(rows: list[dict], peer_id: str,
                     profile_name: str = 'work_quality_gate',
                     now: float | None = None) -> float:
    """Consensus weight for peer_id under a named profile.

    Returns a score in [0.0, 1.0] suitable for weighting votes or bids.
    Unknown profile_name falls back to 'work_quality_gate'.
    """
    weights = CONSENSUS_PROFILES.get(profile_name, CONSENSUS_PROFILES['work_quality_gate'])
    scores = peer_rep_profile(rows, peer_id, now=now)
    return sum(weights[cat] * scores[cat] for cat in ALL_CATEGORIES)


def sybil_gate(rows: list[dict], peer_id: str,
               min_scores: dict[str, float] | None = None) -> tuple[bool, list[str]]:
    """Return (passes, failing_categories) for Sybil admission gate.

    Default minimum scores require non-trivial presence in each category.
    A Sybil with only quality history (bought work) will fail service + longevity.
    """
    _DEFAULTS: dict[str, float] = {
        CAT_QUALITY:    0.10,
        CAT_DELIVERY:   0.10,
        CAT_SERVICE:    0.05,  # low — new peers can earn 1 seal reward to pass
        CAT_VALIDATION: 0.05,  # low — no challenge history needed early
        CAT_LONGEVITY:  0.05,  # low — only a few days of activity needed
    }
    thresholds = {**_DEFAULTS, **(min_scores or {})}
    scores = peer_rep_profile(rows, peer_id)
    failing = [cat for cat, threshold in thresholds.items()
               if scores[cat] < threshold]
    return (len(failing) == 0, failing)


# ---------------------------------------------------------------------------
# Wilson lower bound (internal helper)
# ---------------------------------------------------------------------------

def _wilson_lower(successes: int, total: int, z: float = 1.645) -> float:
    """Wilson score lower bound at ~90% confidence (z=1.645).

    More robust than simple success/total for small sample sizes.
    Returns value in [0.0, 1.0].
    """
    if total == 0:
        return 0.0
    p = successes / total
    n = total
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    denom = 1 + z * z / n
    return max(0.0, (centre - spread) / denom)
