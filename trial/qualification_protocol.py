"""Frozen qualification rules and lossless cohort progress; no inference."""
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ORDINARY = ('navigation', 'recovery', 'interruption', 'receipts', 'requirements_change')
SCHEMA = 'qualified-paired-engineering-v3'
MINIMUM_PAIRS = 30
MINIMUM_PER_FAMILY = 6

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def native_clients(controls):
    import subprocess
    result={}
    for provider,options in controls['executors'].items():
        if not options['enabled']:continue
        try:
            p=subprocess.run([provider,'--version'],capture_output=True,text=True,timeout=10)
            result[provider]={'version':p.stdout.strip()[:100] if p.returncode==0 else None,'verified':p.returncode==0 and bool(p.stdout.strip())}
        except (OSError,subprocess.TimeoutExpired):result[provider]={'version':None,'verified':False}
    return result

def protocol(base=None):
    from executable_sandbox import IMAGE
    from project_tools import TOOLS
    from output_quality import contract as quality_contract
    from common import BASE
    from urace.executor_capabilities import contract as capabilities_contract
    base=Path(base or BASE);path=base.parent/'runtime/urace/config.json';capabilities_sha=digest(capabilities_contract(json.loads(path.read_text()) if path.exists() else {}))
    return {'schema': SCHEMA, 'skills_and_context_contract_sha256':capabilities_sha, 'ordinary_families': list(ORDINARY), 'minimum_pairs_per_profile': MINIMUM_PAIRS,
            'minimum_pairs_per_family': MINIMUM_PER_FAMILY, 'failover_separate': True,
            'runtime': {'sandbox_image': IMAGE, 'controller_python': list(sys.version_info[:3]), 'tools_sha256': digest(TOOLS)},
            'quality_contracts': {f: {str(p): quality_contract(f,p) for p in (1,2)} for f in ORDINARY},
            'active_wall_budget_seconds': 480, 'counterbalance': 'repeat + family index parity',
            'arms': {'standalone': {'outer_attempts': 1, 'urace_goal_packet': False, 'publication': 'sealed delivery'},
                     'urace': {'outer_attempts': 3, 'urace_goal_packet': True, 'publication': 'authority + atomic publication'}},
            'ordinary_provider_policy': 'fixed provider for both arms including repairs; failover is separate',
            'timing': 'end-to-end includes admission/queue and controller gaps; active allowance accumulates admitted invocation intervals across resumes and phases; inactive controller gaps excluded from active allowance but retained in elapsed',
            'resources': 'all attempts, failures, repairs and native auxiliary usage; unknown stays unknown; no nested timing addition',
            'acceptance': 'functional, robustness, determinism and regression sealed before generation; no private repair feedback',
            'inference': 'conditional descriptive paired bootstrap; repeated synthetic tasks may be dependent',
            'percentile_minimums': {'p50': 5, 'p90': 20, 'p95': 40},
            'value_claim': 'no universal worth percentile, real-user benefit or market-fit claim'}

def cells(root, identity, eligible=None):
    """Unfinished pairs first, then least represented profiles/families. No cap."""
    root=Path(root); candidates=[]; counts=Counter(); profile=Counter()
    for provider in identity['models']:
        for effort in identity['settings']['efforts']:
            for family in ORDINARY + ('failover',):
                for repeat in range(identity['settings']['repetitions']):
                    cell=root/(provider+'-'+effort+'-'+family+'-'+str(repeat))
                    done=[(cell/a/'study-result.json').exists() for a in ('standalone','urace')]
                    if all(done):
                        counts[provider,effort,family]+=1
                        if family in ORDINARY: profile[provider,effort]+=1
                    else: candidates.append((provider,effort,family,repeat,cell,sum(done)))
    if eligible is not None:
        candidates=[v for v in candidates if v[0] in eligible and v[2]!='failover'] + [v for v in candidates if v[2]=='failover' and any(p!=v[0] for p in eligible)]
    return sorted(candidates, key=lambda v: (v[2]=='failover', -v[5], profile[v[0],v[1]], counts[v[0],v[1],v[2]], v[3], ORDINARY.index(v[2]) if v[2] in ORDINARY else 5, v[0], v[1]))

def reconcile(row, base=None):
    """Receipt totals are authoritative; conflicting duplicate IDs invalidate cost."""
    receipts={}; conflicts=[]
    for receipt in row.get('native_receipts', []):
        identifier=receipt.get('id')
        if not isinstance(identifier,str) or not identifier: conflicts.append('missing_receipt_id');continue
        if identifier in receipts and receipts[identifier]!=receipt: conflicts.append(identifier)
        receipts[identifier]=receipt
    authoritative=True
    if base is not None:
        for identifier,receipt in receipts.items():
            if not identifier.isalnum():authoritative=False;continue
            path=Path(base)/'transport'/(identifier+'.json')
            if path.is_symlink() or not path.is_file():authoritative=False;continue
            try:
                if json.loads(path.read_text())!=receipt:authoritative=False
            except (OSError,ValueError):authoritative=False
    known=authoritative and bool(receipts) and not conflicts and all(type(r.get('tokens')) is int and r['tokens']>=0 for r in receipts.values())
    for r in receipts.values():
        details=r.get('accounting_details') or {}
        if details.get('known') is True and 'tokens' in details and details['tokens']!=r.get('tokens'):known=False
    tokens=sum(r['tokens'] for r in receipts.values()) if known else None
    walls=[r.get('wall_seconds') for r in receipts.values()]
    timing=bool(walls) and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in walls)
    elapsed=row.get('elapsed_seconds')
    timing=timing and type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>0 and sum(walls)<=elapsed+1
    products={r.get('product_id') for r in receipts.values() if r.get('product_id')}
    product_ok=not products or products=={row.get('product_id')}
    providers={r.get('provider') for r in receipts.values() if r.get('provider')}
    provider_ok=providers==set(row.get('actual_providers',[]))
    return {'authoritative_receipts_match':authoritative if base is not None else None,'product_scope_consistent':product_ok,'provider_scope_consistent':provider_ok,'tokens':tokens,'cached_tokens_match':known and row.get('tokens')==tokens,
            'receipt_ids':sorted(receipts),'conflicting_receipt_ids':conflicts,
            'native_seconds':sum(walls) if timing else None,
            'failed_attempts':sum(bool(r.get('failure')) for r in receipts.values()),
            'unknown_usage_attempts':sum(type(r.get('tokens')) is not int for r in receipts.values()),
            'credit_decrement':None,'all_cost_known':known and timing and product_ok and provider_ok,
            'scope':'Native session is nested inside workflow elapsed time, not additive'}

def compatible(row, identity):
    expected=identity.get('qualification_protocol')
    conditions=row.get('execution_conditions',{})
    receipts=row.get('native_receipts',[])
    receipt_profiles=bool(receipts) and all(r.get('requested_model')==identity['models'].get(row.get('provider')) and r.get('effort')==row.get('effort') for r in receipts)
    capability_match=all(r.get('skills_and_context_contract_sha256')==expected.get('skills_and_context_contract_sha256') and r.get('owner_clarification_sha256')==digest({}) for r in receipts) if expected and expected.get('skills_and_context_contract_sha256') else True
    client=identity.get('native_clients',{}).get(row.get('provider'),{})
    client_matches=client.get('verified') is True and all(r.get('client_version')==client.get('version') for r in receipts)
    return bool(row.get('active_budget',{}).get('closed',True) and row.get('active_budget',{}).get('measurement_complete',True) and receipt_profiles and client_matches and capability_match and expected and row.get('protocol_sha256')==digest(expected) and
                row.get('cohort_identity_sha256')==digest(identity) and
                conditions.get('requested_model')==identity['models'].get(row.get('provider')) and
                conditions.get('requested_effort')==row.get('effort') and
                conditions.get('active_wall_budget_seconds')==480 and
                row.get('actual_providers')==[row.get('provider')])

def progress(root, identity):
    root=Path(root);base=root.parent.parent if root.parent.name=='repository-studies' else root;profiles={};all_rows=[]
    for p in root.glob('*/*/study-result.json'):
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):raise ValueError('Study evidence escapes cohort')
        all_rows.append(json.loads(p.read_text()))
    for provider in identity['models']:
        for effort in identity['settings']['efforts']:
            rows=[r for r in all_rows if r.get('provider')==provider and r.get('effort')==effort and r.get('family') in ORDINARY]
            paired={};family=Counter();eligible_family=Counter();incompatible=unknown=quality_missing=0
            for r in rows:paired.setdefault((r['family'],r['repeat']),{})[r['arm']]=r
            for (f,_), arms in paired.items():
                if set(arms)!= {'standalone','urace'}:continue
                family[f]+=1;pair=list(arms.values())
                ok=all(compatible(r,identity) for r in pair)
                cost=all(reconcile(r,base)['all_cost_known'] and reconcile(r,base)['cached_tokens_match'] for r in pair)
                quality=all(r.get('acceptance',{}).get('quality',{}).get('measurement_complete') is True for r in pair)
                incompatible+=not ok;unknown+=not cost;quality_missing+=not quality
                if ok and cost and quality:eligible_family[f]+=1
            pending=sum(1 for v in cells(root,identity) if v[0]==provider and v[1]==effort and v[2] in ORDINARY and (v[4]/'pair-launch.json').exists())
            deficits={f:max(0,MINIMUM_PER_FAMILY-eligible_family[f]) for f in ORDINARY}
            ready=sum(eligible_family.values())>=MINIMUM_PAIRS and not any(deficits.values()) and not pending and not incompatible and not unknown and not quality_missing
            profiles[provider+':'+effort]={'status':'READY' if ready else 'INSUFFICIENT','matched_pairs':sum(family.values()),'eligible_pairs':sum(eligible_family.values()),'family_pairs':dict(family),'eligible_family_pairs':dict(eligible_family),'family_deficits':deficits,'pair_deficit':max(0,MINIMUM_PAIRS-sum(eligible_family.values())),'launched_incomplete_pairs':pending,'unmatched_completed_arms':sum(len(a)==1 for a in paired.values()),'incompatible_pairs':incompatible,'unknown_resource_pairs':unknown,'unmeasured_quality_pairs':quality_missing}
    return {'all_completed_resources_by_profile':{provider+':'+effort:{'workflows':len(rs),'failed_workflows':sum(r.get('validated') is not True for r in rs),'known_native_tokens':sum(reconcile(r,base)['tokens'] or 0 for r in rs),'unknown_resource_workflows':sum(not reconcile(r,base)['all_cost_known'] for r in rs),'scope':'All completed ordinary arms, including unmatched and failed; pending project-work attempts are additionally retained in product resources'} for provider in identity['models'] for effort in identity['settings']['efforts'] for rs in [[r for r in all_rows if r.get('provider')==provider and r.get('effort')==effort and r.get('family') in ORDINARY]]},'schema':SCHEMA,'status':'READY' if profiles and all(p['status']=='READY' for p in profiles.values()) else 'INSUFFICIENT','profiles':profiles,'completed_workflows_including_failover':len(all_rows),'failover_workflows':sum(r.get('family')=='failover' for r in all_rows),'legacy_plan_qualified':bool(identity.get('qualification_protocol')),'sample_readiness_time':None,'limitations':'Time alone never qualifies. All launched incomplete pairs remain visible and block a complete assessment; historical incompatible evidence retained separately.'}
