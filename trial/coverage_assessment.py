"""Evidence inventory and sample-gated value metrics; no inference or authority."""
from pathlib import Path
from datetime import datetime
import ast
import hashlib
import json
import math
import random

from period_feedback import percentiles


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def product_context(base):
    from spec_trial import sections, digest
    base = Path(base)
    pointer = load(base/'active-version.json', {})
    if not pointer:
        return {'status': 'NOT_CONFIGURED', 'global_semantic_consistency_proven': False}
    folder = Path(pointer.get('snapshot', '/nonexistent')).resolve()
    if not folder.is_relative_to((base/'versions').resolve()):
        raise ValueError('Product snapshot outside version storage')
    manifest = load(folder/'manifest.json')
    text = (folder/'URACE.md').read_text()
    if digest(text) != manifest['sha256'] or digest(text) != pointer['sha256']:
        raise ValueError('Product source integrity mismatch')
    trial = load(base/'trial-clock.json')['trial_id']
    jobs = [j for j in load(base/'state.json', {'jobs': []})['jobs'] if j.get('trial_id') == trial]
    seen = {}
    for job in jobs:
        if job.get('context_sha256'):
            seen.setdefault(job['context_sha256'], []).append(job)
    contexts = []
    parts = sections(text)
    if ''.join(parts) != text:
        raise ValueError('Context inventory is not a lossless product partition')
    for index, part in enumerate(parts):
        matching = seen.get(digest(part), [])
        contexts.append({'index': index, 'sha256': digest(part), 'bytes': len(part.encode()),
                         'heading': part.splitlines()[0] if part.splitlines() else '',
                         'selected_tasks': len(matching),
                         'accepted_tasks': sum(j.get('outcome') == 'ACCEPTED_EDITORIAL_IMPROVEMENT' for j in matching),
                         'semantic_coverage_proven': False})
    return {'status': 'INVENTORIED', 'active_version': manifest['version'], 'source_sha256': digest(text),
            'contexts': contexts, 'context_count': len(contexts),
            'contexts_with_selection_history': sum(c['selected_tasks'] > 0 for c in contexts),
            'editorial_context': {'section_bytes': 22000, 'supporting_contract_bytes': 2000,
                                  'full_document_sent_to_model': False,
                                  'full_document_static_preservation_guards': True},
            'downstream_full_document_tool_available': True,
            'global_semantic_consistency_proven': False,
            'interpretation': 'Selection history is not accepted improvement or comprehension. Tool availability is not proof every source part was read. Static preservation is distinct from cross-part semantic validation.'}


def features(base, parser=None):
    from urace import cli, command_surface
    base = Path(base)
    core = base.parent/'runtime/urace'
    core_tests = base.parent/'runtime/tests'
    tests = sorted(core_tests.glob('test*.py')) + sorted(base.glob('test*.py'))
    links = {}
    declared = 0
    for test in tests:
        tree = ast.parse(test.read_text())
        declared += sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in ast.walk(tree))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module == 'urace':
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('urace.'):
                names = [node.module.split('.')[1]]
            elif isinstance(node, ast.Import):
                names = [a.name.split('.')[1] for a in node.names if a.name.startswith('urace.')]
            for name in names:
                links.setdefault(name, set()).add(str(test.relative_to(base.parent)))
    receipt = load(base/'verification-latest.json', {})
    expected = receipt.get('source_sha256', {})
    allowed={str(p.relative_to(base.parent)) for directory in (core,core_tests,base) for p in directory.glob('*.py') if not p.is_symlink() and p.resolve()==p.absolute()}
    qualified = isinstance(expected,dict) and bool(expected) and set(expected)==allowed and all(sha(base.parent/name)==value for name,value in expected.items())
    return {'status': 'INVENTORIED', 'operation_paths': sorted(command_surface.operation_parsers(parser or cli.build_parser())),
            'modules': [{'path': str(p.relative_to(base.parent)), 'static_test_links': sorted(links.get(p.stem, set())),
                         'all_behavior_live_verified': False} for p in sorted(core.glob('*.py'))],
            'trial_modules': [p.name for p in sorted(base.glob('*.py')) if not p.name.startswith('test')],
            'test_files': [str(p.relative_to(base.parent)) for p in tests], 'declared_test_methods': declared,
            'qualification': {'source_matches': qualified, 'results': receipt.get('results', []) if qualified else [],
                              'reason': None if qualified else 'No matching complete owner qualification receipt; do not reuse old passing results'},
            'all_features_live_verified': False,
            'interpretation': 'Operation parents and aliases are not independent features. Static imports are links, not execution/branch coverage. A passing regression suite does not establish every deployed behavior.'}


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def paired_metrics(pairs, *, required_families, minimum=30, minimum_per_family=6):
    """One provider/profile only. Hold outputs until sample/quality gates pass."""
    pairs = sorted(pairs, key=lambda pair: json.dumps([(r.get('family'),r.get('repeat'),r.get('id')) for r in pair],sort_keys=True))
    from collections import Counter
    family_counts=Counter(a.get('family') for a,b in pairs)
    families = set(family_counts)
    complete = bool(pairs) and all(a.get('provider') == b.get('provider') and
        a.get('family') == b.get('family') and a.get('effort') == b.get('effort') and
        a.get('repeat') == b.get('repeat') and
        a.get('actual_providers') == b.get('actual_providers') == [a.get('provider')] and
        all(r.get('acceptance', {}).get('quality', {}).get('measurement_complete') is True and
            type(r.get('acceptance', {}).get('quality', {}).get('gate_passed')) is bool and
            r.get('complete') is True and type(r.get('validated')) is bool and
            type(r.get('tokens')) is int and r['tokens'] >= 0 and _positive(r.get('elapsed_seconds'))
            for r in (a, b)) for a, b in pairs)
    profile = {(r.get('provider'), r.get('effort')) for pair in pairs for r in pair}
    ready = all(type(a.get('tokens')) is int and a['tokens']>0 for a,b in pairs) and len(pairs) >= minimum and all(family_counts[f]>=minimum_per_family for f in required_families) and complete and len(profile) == 1
    result = {'status': 'READY_FOR_BOUNDED_DESCRIPTIVE_COMPARISON' if ready else 'INSUFFICIENT_OR_INCOMPATIBLE_EVIDENCE',
              'pairs': len(pairs), 'minimum_pairs': minimum, 'families': sorted(f for f in families if isinstance(f, str)),
              'required_families': sorted(required_families), 'family_counts':dict(family_counts), 'family_deficits':{f:max(0,minimum_per_family-family_counts[f]) for f in required_families}, 'quality_and_cost_complete': complete,
              'profile_count': len(profile), 'ready': ready, 'metrics': None,
              'overall_worth_percentage': None, 'overall_worth_percentile': None,
              'worth_reason': 'No validated overall utility weights or reference population. Resource percentiles are not overall product worth.'}
    if not ready:
        return result
    def improvements(sample, key):
        before = sum(a[key] for a, b in sample)
        after = sum(b[key] for a, b in sample)
        return 100*(before-after)/before
    metrics = {}
    seed = hashlib.sha256(json.dumps([(a.get('id'), b.get('id')) for a, b in pairs]).encode()).hexdigest()
    rng = random.Random(seed)
    for key in ('tokens', 'elapsed_seconds'):
        changes = [100*(a[key]-b[key])/a[key] for a, b in pairs]
        draws = sorted(improvements([pairs[rng.randrange(len(pairs))] for _ in pairs], key) for _ in range(1000))
        metrics[key] = {'observed_reduction_pct': improvements(pairs, key),
                        'paired_reduction_percentiles': percentiles(changes),
                        'bootstrap_interval_95_pct': [draws[24], draws[974]],
                        'resamples': 1000, 'method': 'Deterministic paired percentile bootstrap; repeated fixed tasks may be dependent. Conditional descriptive uncertainty, not a field-reliability guarantee.'}
    for arm,index in [('standalone',0),('urace',1)]:
        rs=[pair[index] for pair in pairs]
        metrics[arm]={'validated_delivery_pct':100*sum(r['validated'] for r in rs)/len(rs),'quality_gate_pass_pct':100*sum(r['acceptance']['quality']['gate_passed'] for r in rs)/len(rs),'failed_or_rejected_workflows':sum(not r['validated'] for r in rs)}
    for name,key in [('delivery','validated'),('quality_gate','quality_gate')]:
        def score(row):
            return int(row['validated']) if key=='validated' else int(row['acceptance']['quality']['gate_passed'])
        diffs=[score(b)-score(a) for a,b in pairs]
        draws=sorted(100*sum(diffs[rng.randrange(len(diffs))] for _ in diffs)/len(diffs) for _ in range(1000))
        metrics[name+'_uncertainty']={'paired_delta_percentage_points':100*sum(diffs)/len(diffs),'bootstrap_interval_95_percentage_points':[draws[24],draws[974]],'resamples':1000,'scope':'Conditional descriptive paired interval; dependence and representativeness are not established'}
    for arm,index in [('standalone',0),('urace',1)]:
        rows=[pair[index] for pair in pairs];deliveries=sum(r['validated'] for r in rows)
        metrics[arm]['tokens_per_validated_delivery']=sum(r['tokens'] for r in rows)/deliveries if deliveries else None
        metrics[arm]['validated_deliveries_per_workflow_hour']=3600*deliveries/sum(r['elapsed_seconds'] for r in rows)
        metrics[arm]['throughput_scope']='Summed workflow hours include waits; not calendar throughput when work overlaps'
        metrics[arm]['intervention_rate_pct']=100*sum(bool(r.get('interventions')) for r in rows)/len(rows) if all('interventions' in r for r in rows) else None
        metrics[arm]['recovery_delivery_pct']=100*sum(r['validated'] for r in rows if r['family'] in ('recovery','interruption'))/sum(r['family'] in ('recovery','interruption') for r in rows) if any(r['family'] in ('recovery','interruption') for r in rows) else None
    metrics['quality_dimension_delta_percentage_points']={}
    for dimension in ('primary_correctness_pct','robustness_pct','determinism_pct'):
        values=[[r.get('acceptance',{}).get('quality',{}).get(dimension) for r in pair] for pair in pairs]
        metrics['quality_dimension_delta_percentage_points'][dimension]=sum(b-a for a,b in values)/len(values) if all(type(v) in (int,float) and math.isfinite(v) for row in values for v in row) else None
    metrics['delivery_delta_percentage_points']=metrics['urace']['validated_delivery_pct']-metrics['standalone']['validated_delivery_pct']
    metrics['quality_gate_delta_percentage_points']=metrics['urace']['quality_gate_pass_pct']-metrics['standalone']['quality_gate_pass_pct']
    result['metrics'] = metrics
    result['scope'] = 'This matched provider/requested-effort profile and covered contracts only; actual served identity may be unverified. No market-fit or universal superiority claim.'
    return result


def comparative_readiness(base, engine_sha256):
    base = Path(base)
    summary = load(base/'repository-study-latest.json', {})
    plan = summary.get('plan', {})
    clock = load(base/'trial-clock.json', {})
    cohort = summary.get('cohort')
    if not isinstance(cohort, str) or not cohort.isalnum() or plan.get('trial_id') != clock.get('trial_id') or plan.get('engine_sha256') != engine_sha256:
        return {'status': 'NO_CURRENT_MATCHING_COHORT', 'profiles': {}, 'overall_worth_percentile': None}
    root = base/'repository-studies'/cohort
    rows = []
    for path in root.glob('*/*/study-result.json'):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Study result escapes cohort')
        rows.append(load(path))
    key = lambda r: (r.get('provider'), r.get('family'), r.get('effort'), r.get('repeat'))
    direct = {key(r): r for r in rows if r.get('arm') == 'standalone'}
    groups = {}
    from repository_tasks import FAMILIES
    required = set(FAMILIES)-{'failover'}
    for row in rows:
        if row.get('arm') != 'urace' or key(row) not in direct or row.get('family') == 'failover':
            continue
        group = str(row.get('provider'))+':'+str(row.get('effort'))
        groups.setdefault(group, []).append((direct[key(row)], row))
    from qualification_protocol import progress,compatible,reconcile
    qualification=progress(root,plan)
    for name,pairs in groups.items():
        if qualification['profiles'].get(name,{}).get('status')!='READY' or any(not compatible(r,plan) or not reconcile(r,base)['all_cost_known'] or not reconcile(r,base)['cached_tokens_match'] for pair in pairs for r in pair):
            groups[name]=[]
    return {'qualification_progress':qualification,'status': 'SAMPLE_GATED', 'cohort': cohort, 'profiles': {name: paired_metrics(pairs, required_families=required) for name, pairs in groups.items()},
            'declared_models': plan.get('models'), 'overall_worth_percentile': None,
            'interpretation': 'No cross-provider or cross-effort pooling; all fields stay unavailable until matched sample, coverage, quality and resource gates pass. Failed/rejected workflows remain visible and prevent a clean gated comparison.'}
