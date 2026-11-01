"""Multi-executor parallel plan selection.

Agora pattern applied to the discovery/planning stage:
  1. Each available executor generates a proposal (discover()).
  2. Each proposal is scored on quality dimensions.
  3. The highest-scoring proposal is selected for execution.

This closes the 'multi-executor-planning' stub gap. Configuration:
  config["executor"]["multi_plan_selection"] = {"enabled": True, "max_candidates": 3}

When disabled (default) or only one provider is available, falls through
transparently to the existing single-executor path.
"""
from __future__ import annotations
from typing import Any

SCHEMA = 'urace-multi-plan-v1'
DEFAULT_SETTINGS: dict[str, Any] = {
    'enabled': False,
    'max_candidates': 3,
    'score_weights': {
        'constraint_compliance': 0.4,
        'goal_alignment': 0.3,
        'cost_estimate': 0.2,
        'novelty': 0.1,
    },
}


def settings(config: dict[str, Any]) -> dict[str, Any]:
    """Return validated multi-plan settings. Never raises."""
    raw = config.get('executor', {}).get('multi_plan_selection', {})
    enabled = raw.get('enabled', DEFAULT_SETTINGS['enabled'])
    if type(enabled) is not bool:
        enabled = False
    max_cand = int(raw.get('max_candidates', DEFAULT_SETTINGS['max_candidates']))
    max_cand = max(1, min(max_cand, 5))
    return {'enabled': enabled, 'max_candidates': max_cand,
            'score_weights': DEFAULT_SETTINGS['score_weights']}


def score_proposal(proposal: dict[str, Any], config: dict[str, Any],
                   state: dict[str, Any]) -> dict[str, float]:
    """Score a discovery proposal on four dimensions. Returns {dimension: 0.0–1.0}."""
    weights = DEFAULT_SETTINGS['score_weights']

    # 1. Constraint compliance: does the proposal mention violating any constraint?
    constraints = [c.get('text', '') for c in (state.get('constraints') or [])]
    proposal_text = str(proposal.get('message', '')) + str(proposal.get('plan', ''))
    violations = sum(1 for c in constraints if c and c.lower() in proposal_text.lower())
    constraint_score = max(0.0, 1.0 - 0.25 * violations)

    # 2. Goal alignment: does the proposal reference the current objective?
    cur = state.get('current_objective', '')
    goal_score = 0.5
    if cur and cur in proposal_text:
        goal_score = 1.0
    elif proposal.get('objective_id') == cur:
        goal_score = 1.0
    elif proposal.get('has_actionable_plan'):
        goal_score = 0.75

    # 3. Cost estimate: shorter plans score higher (proxy for lower cost)
    plan_len = len(str(proposal.get('plan', '') or ''))
    cost_score = max(0.0, 1.0 - plan_len / 10000)

    # 4. Novelty: does the proposal differ from recent accepted operations?
    recent_ops = [op.get('executor_source_summary', '') for op in state.get('operations', [])[-10:]]
    proposal_summary = str(proposal.get('message', ''))[:200]
    matches = sum(1 for op in recent_ops if op and proposal_summary and proposal_summary[:50] in op)
    novelty_score = max(0.0, 1.0 - 0.3 * matches)

    scores = {
        'constraint_compliance': constraint_score,
        'goal_alignment': goal_score,
        'cost_estimate': cost_score,
        'novelty': novelty_score,
    }
    total = sum(weights[k] * scores[k] for k in weights)
    return {**scores, 'total': total}


def select_best(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the highest-total-score candidate."""
    if not candidates:
        raise ValueError('No candidates to select from')
    return max(candidates, key=lambda c: c['score']['total'])


def generate_and_select(config: dict[str, Any], state: dict[str, Any],
                        discover_fn: Any) -> dict[str, Any] | None:
    """Generate proposals from multiple providers and select the best.

    Returns the winning proposal or None if multi-plan selection is disabled
    / has only one provider (caller should fall through to normal path).

    discover_fn must match the signature of intelligent_executor.discover().
    """
    cfg = settings(config)
    if not cfg['enabled']:
        return None

    from . import executor as _ex
    providers = _ex.provider_definitions(config.get('executor', {}))
    available = [
        p for p in providers
        if not state.get('executor_state', {}).get('provider_pool', {}).get(
            p.get('id', ''), {}
        ).get('retry_at')
    ]

    if len(available) < 2:
        return None

    candidates: list[dict[str, Any]] = []
    max_cand = min(cfg['max_candidates'], len(available))

    for provider in available[:max_cand]:
        # Temporarily pin the config to use only this provider.
        single_config = {**config, 'executor': {**config.get('executor', {}),
                                                  '_override_provider': provider.get('id')}}
        try:
            proposal = discover_fn(None, single_config, state)
            score = score_proposal(proposal, config, state)
            candidates.append({
                'schema': SCHEMA,
                'provider_id': provider.get('id'),
                'proposal': proposal,
                'score': score,
            })
        except Exception:
            continue

    if not candidates:
        return None

    winner = select_best(candidates)
    winner['_multi_plan_candidates'] = len(candidates)
    return winner['proposal']
