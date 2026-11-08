"""Traceable bounded assessment; missing evidence never becomes success.

No inference, scheduling, policy changes or acceptance-gate changes here.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from period_feedback import percentiles

SOURCES = {
    'standalone_comparison': 'repository-study-latest.json',
    'context_ablation': 'downstream-context-latest.json',
    'specification_comparison': 'downstream-specification-latest.json',
    'executable_versions': 'executable-benchmark-latest.json',
}


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z*z/total
    center = (p + z*z/(2*total))/denominator
    half = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))/denominator
    return {'lower': max(0, center-half), 'upper': min(1, center+half),
            'nominal_confidence': .95,
            'assumption': 'Independent representative Bernoulli trials. Repeated tasks/provider calls may be dependent; this interval is descriptive and cannot establish field reliability.'}


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def recorded_time(row):
    value = row.get('at_unix')
    if numeric(value):
        return value
    try:
        value = datetime.fromisoformat(row['at'].replace('Z', '+00:00'))
        return value.timestamp() if value.tzinfo else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def assess(base, rows, now, *, engine_sha256, execution_sha256=None, window_seconds=10800):
    base = Path(base)
    clock = json.loads((base/'trial-clock.json').read_text())
    epoch_path = base/'assessment-epoch.json'
    epoch = json.loads(epoch_path.read_text()) if epoch_path.exists() else {}
    if epoch.get('trial_id') != clock['trial_id']:
        epoch = {}
    epoch_start = epoch.get('started_unix')
    if not numeric(epoch_start):
        epoch_start = clock.get('started_unix') if numeric(clock.get('started_unix')) else now
    start = max(now-window_seconds, epoch_start)
    scoped = [r for r in rows if r.get('trial_id') == clock['trial_id']]
    missing_time = sum(recorded_time(r) is None for r in scoped)
    selected = [r for r in scoped if recorded_time(r) is not None and start <= recorded_time(r) <= now]
    # A receipt identity is one attempt, regardless of projected duplicate rows.
    finished = {r['id']: r for r in selected if r.get('kind') == 'finished' and isinstance(r.get('id'), str)}
    providers = {}
    for provider in sorted({'codex', 'claude'} | {r['provider'] for r in finished.values() if isinstance(r.get('provider'), str)}):
        done = [r for r in finished.values() if r.get('provider') == provider]
        failures = sum(bool(r.get('failure')) for r in done)
        tokens = [r['tokens'] for r in done if type(r.get('tokens')) is int and r['tokens'] >= 0]
        elapsed = [r['wall_seconds'] for r in done if numeric(r.get('wall_seconds'))]
        providers[provider] = {
            'finished_attempts': len(done), 'failed_attempts': failures,
            'transport_success_rate_pct': 100*(len(done)-failures)/len(done) if done else None,
            'transport_success_wilson_interval': wilson(len(done)-failures, len(done)),
            'known_tokens_including_failures': sum(tokens), 'unknown_usage_attempts': len(done)-len(tokens),
            'total_tokens': sum(tokens) if done and len(tokens) == len(done) else None,
            'tokens': percentiles(tokens), 'executor_seconds': percentiles(elapsed),
            'known_executor_seconds_including_failures': sum(elapsed),
            'missing_timing_attempts': len(done)-len(elapsed),
            'transport_success_is_output_quality': False,
        }
    evidence = {}
    for name, relative in SOURCES.items():
        path = base/relative
        if not path.exists():
            evidence[name] = {'status': 'MISSING', 'eligible_for_current_engine_claim': False}
            continue
        try:
            raw = path.read_bytes()
            data = json.loads(raw)
            plan = data.get('plan', {})
            trial = data.get('trial_id', plan.get('trial_id'))
            engine = plan.get('engine_sha256', data.get('engine'))
            # Some legacy executable reports use a structured engine descriptor.
            if isinstance(engine, dict):
                engine = engine.get('code_fingerprint')
            expected_engine = execution_sha256 if name == 'executable_versions' else engine_sha256
            current = expected_engine is not None and trial == clock['trial_id'] and engine == expected_engine and path.stat().st_mtime >= epoch_start
            evidence[name] = {
                'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
                'trial_id': trial, 'engine_sha256': engine, 'expected_engine_sha256': expected_engine,
                'epoch_scope': 'Cohort-level comparison may include earlier runs of the matching engine; do not interpret file refresh time as fresh executor work',
                'eligible_for_current_engine_claim': current,
                'status': data.get('status', 'RECORDED'),
                'completed_workflows': data.get('completed_workflows'),
                'quality': data.get('output_quality', data.get('scorecard')),
                'comparisons': data.get('assessment', data.get('comparisons_by_provider_and_family')),
                'benefit': data.get('benefit'), 'forecast': data.get('forecast'),
                'scope': 'Current matching engine/trial; inspect paired coverage and quality' if current else 'Historical, stale or incompatible; retained for context, excluded from current-engine conclusions',
            }
        except (OSError, ValueError, TypeError, AttributeError) as error:
            evidence[name] = {'status': 'INVALID', 'eligible_for_current_engine_claim': False, 'error': type(error).__name__}
    from coverage_assessment import product_context, features, comparative_readiness
    coverage={}
    for name,callback in [('product_context',lambda:product_context(base)),('runtime_features',lambda:features(base)),('comparative_value',lambda:comparative_readiness(base,engine_sha256))]:
        try:coverage[name]=callback()
        except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:coverage[name]={'status':'UNAVAILABLE','reason':type(error).__name__+': '+str(error)[:300]}
    from refinement_targets import report as refinement_report
    return {
        'core_refinement_targets':refinement_report(),
        'assessment_axes': {
            'performance_and_resource_efficiency':'Per compatible profile; complete failed-attempt/native receipts and paired uncertainty required',
            'reliability_and_attrition':'Include failed, timed-out, unmatched and pending arms; do not assess survivors alone',
            'functional_robustness_determinism_regression':'Independent sealed executable gates; inspect each quality dimension and failure, not transport success',
            'fairness_and_reproducibility':'Frozen tasks, profile, runtime/client/evaluator/tool identities, active budgets, order and disclosed treatment differences',
            'context_and_comprehension':'Context selection history and scoped source availability are measured separately from semantic comprehension, which remains unproven',
            'interfaces_and_recovery':'Use source-matching core qualification and transport-specific evidence; static inventories do not prove every path live',
            'accounting_and_observation_boundaries':'Separate products/providers/efforts, unknown usage and credits; distinguish nested timing, reporting windows and historical cohorts',
            'usability_maintainability_external_validity':'Unmeasured; require independent human review, representative external tasks and actual use before claims',
            'universal_complete_assessment_established':False,
            'scope':'Expanded evidence checklist, not newly weakened acceptance or a claim all axes are measured. Enough synthetic pairs can support a bounded engineering comparison only.'},
        'coverage_and_value_readiness':coverage,
        'schema': 'comprehensive-assessment-v1', 'trial_id': clock['trial_id'],
        'engine_sha256': engine_sha256,
        'at': datetime.fromtimestamp(now, timezone.utc).isoformat(),
        'window': {'started_unix': start, 'ended_unix': now, 'seconds_observed': max(0, now-start),
                   'assessment_epoch': epoch, 'trial_start_time_known':numeric(clock.get('started_unix')), 'timestamp_scope': 'Native attempts by recorded start timestamp; boundary-spanning attempts may complete later'},
        'performance_and_transport_reliability_by_executor': providers,
        'unattributable_timestamp_rows': missing_time,
        'quality_effectiveness_and_comparative_evidence': evidence,
        'required_advantage_criteria': {
            'comparison': 'Same task contract, actual provider/model/native effort, tools, budget and matched repetitions; compare URACE with standalone AI',
            'quality': 'Independent held-out acceptance, robustness, determinism and regression checks; no quality regression hidden by a composite score',
            'resources': 'Count failed attempts, repairs, queue/availability delay and orchestration overhead; native credits are unknown unless directly reported',
            'minimum_coverage': 'At least 30 matched ordinary pairs per provider/native-effort profile and at least six pairs in each of five ordinary families; repeated fixed tasks are not independent user samples',
            'material_gain': 'Existing paired qualification requires >=20% time/token improvement with <=5% degradation on the other dimension, or additional validated deliveries under its declared constraints',
            'claim_limit': 'Engineering advantage is bounded to covered tasks and conditions. No guarantee of market fit, actual-user benefit, all-feature superiority or maintenance-free indefinite operation',
        },
        'evidence_ladder': {
            'without_users': 'Can establish bounded correctness, recovery behavior and comparative engineering utility on representative independently checked scenarios',
            'without_real_use_cases': 'Cannot establish external relevance. Synthetic benchmarks alone do not establish real-world value; require documented real-world task provenance and independent acceptance',
            'actual_user_value_or_market_fit_established': False,
            'actual_user_value_status': 'Not measured by this trial; requires observed use/adoption or independent external validation',
        },
        'assessment_schedule': {'automatic_review_interval_seconds': 10800,
                                'first_operational_check_hours': 3, 'comparative_reassessment_hours': [12, 24],
                                'long_run_checkpoints_days': [7, 30],
                                'readiness_rule': 'Time estimates are conditional; report observed eligible pairs/coverage and withhold advantage when insufficient'},
    }
