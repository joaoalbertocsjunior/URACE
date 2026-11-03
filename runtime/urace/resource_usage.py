"""Normalize retained native receipts without inventing token or credit observations."""
from __future__ import annotations
import json
import math
import sqlite3
from pathlib import Path


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def token_count(value):
    return value if type(value) is int and value >= 0 else None


def json_safe(value):
    if type(value) is float and not math.isfinite(value):return None
    if isinstance(value,dict):return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,list):return [json_safe(v) for v in value]
    return value


def usage_totals(usage):
    if not isinstance(usage, dict):
        return {'known_tokens': 0, 'missing_usage': 1, 'reported_cost_usd': None}
    receipts = usage.get('transport_usage')
    if isinstance(receipts, list) and receipts:
        parts = [usage_totals(r.get('usage')) for r in receipts]
        costs = [p['reported_cost_usd'] for p in parts]
        return {'known_tokens': sum(p['known_tokens'] for p in parts),
                'missing_usage': sum(p['missing_usage'] for p in parts),
                'reported_cost_usd': sum(costs) if all(c is not None for c in costs) else None}
    tokens = next((token_count(usage[k]) for k in ('resource_total_tokens', 'total_tokens', 'tokens')
                   if token_count(usage.get(k)) is not None), None)
    if tokens is None and 'model_usage' not in usage:
        incoming, outgoing = token_count(usage.get('input_tokens')), token_count(usage.get('output_tokens'))
        if incoming is not None and outgoing is not None:
            tokens = incoming + outgoing
            # Claude's cache counters are extra inputs; Codex cached_input_tokens
            # is already included in input_tokens and must not be added again.
            extended = usage.get('extended', {})
            for key in ('cache_creation_input_tokens', 'cache_read_input_tokens'):
                if key in extended:
                    cache = token_count(extended[key])
                    if cache is None:
                        tokens = None
                        break
                    tokens += cache
    cost = number(usage.get('reported_cost_usd', usage.get('cost')))
    return {'known_tokens': tokens if tokens is not None else 0,
            'missing_usage': int(tokens is None), 'reported_cost_usd': cost}


def observed_calls(config, state):
    """Merge core and freeform receipts by stable identity; adapter mirrors dedupe."""
    calls = {}
    if config.get('state_path'):
        from ._common import state_path
        database = state_path(config).parent/'resource-usage.sqlite3'
        if database.exists():
            with sqlite3.connect(database.resolve().as_uri()+'?mode=ro', uri=True, timeout=2) as db:
                for row, in db.execute('SELECT record FROM native_calls WHERE product_id=?', (product_identity(config),)):
                    receipt = json.loads(row)
                    if receipt.get('product_id') in (None,product_identity(config),config.get('product')):
                        calls[receipt['id']] = receipt
    calls.update({r.get('id', 'legacy-'+str(i)): r for i, r in enumerate(
        state.get('executor_state', {}).get('executor_calls', []))
        if r.get('product_id') in (None,product_identity(config),config.get('product'))})
    if config.get('state_path'):
        from ._common import state_path
        path = state_path(config).parent/'freeform-routing-resources.jsonl'
        if path.exists():
            for i, line in enumerate(path.read_text().splitlines()):
                row = json.loads(line)
                if row.get('product_id') not in (None, product_identity(config), config.get('product')):
                    continue
                key = row.get('id', 'legacy-freeform-'+str(i))
                calls.setdefault(key, {'id': key, 'at': row.get('at'),
                    'stage': 'freeform-routing', 'usage': row.get('reported_usage'),
                    'elapsed_seconds': row.get('wall_seconds'),
                    'trial_id': row.get('trial_id'), 'product_id': row.get('product_id')})
    return list(calls.values())


def product_identity(config):
    active=config.get('active_product')
    if active:
        entry=next((p for p in config.get('product_registry',[]) if p.get('name')==active and p.get('status','ACTIVE')=='ACTIVE'),{})
        return str(entry.get('resource_product_id') or entry.get('id') or active)
    return str(config.get('resource_product_id') or config.get('product') or 'unattributed')


def archive_calls(config, state):
    """Retain stable native identities beyond the controller's state retention window."""
    calls = [c for c in state.get('executor_state', {}).get('executor_calls', [])
             if c.get('id') and c.get('stage') != 'specification_adapter']
    if not calls:
        return
    from ._common import state_path
    path = state_path(config).parent/'resource-usage.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=2) as db:
        db.execute('CREATE TABLE IF NOT EXISTS native_calls (product_id TEXT, id TEXT, record TEXT NOT NULL, PRIMARY KEY(product_id,id))')
        for call in calls:
            # Prompts, credentials, full state and operator intent are never copied.
            record = {k: call[k] for k in ('id','at','stage','usage','elapsed_seconds','trial_id','product_id','executor_attribution','outcome','integration_context') if k in call}
            encoded = json.dumps(json_safe(record), sort_keys=True, allow_nan=False)
            db.execute('INSERT INTO native_calls VALUES (?,?,?) ON CONFLICT(product_id,id) DO UPDATE SET record=excluded.record WHERE native_calls.record<>excluded.record',
                       ((product_identity(config) if call.get('product_id') in (None,config.get('product')) else call['product_id']), call['id'], encoded))


def summary(config, state):
    calls = observed_calls(config, state)
    parts = [usage_totals(r.get('usage')) for r in calls]
    costs = [r['reported_cost_usd'] for r in parts]
    return {'logical_calls': len(calls), 'known_tokens': sum(r['known_tokens'] for r in parts),
            'missing_usage': sum(r['missing_usage'] for r in parts),
            'known_reported_cost_usd':sum(c for c in costs if c is not None),
            'missing_reported_cost_calls':sum(c is None for c in costs),
            'reported_cost_usd': sum(costs) if costs and all(c is not None for c in costs) else None,
            'known_executor_seconds': sum(number(r.get('elapsed_seconds')) or 0 for r in calls),
            'missing_elapsed_seconds': sum(number(r.get('elapsed_seconds')) is None for r in calls),
            'subscription_credit_decrement': None,
            'interpretation': 'Retained logical reservations plus durable freeform receipts; transport retries may contain multiple native calls. Unknown usage is not zero.'}


def write_projection(config,state):
    """Small receipt read model; stale/corrupt projections fall back to full state."""
    import hashlib
    from ._common import state_path,atomic_write_json
    source=state_path(config).resolve();info=source.stat()
    calls=[]
    for call in state.get('executor_state',{}).get('executor_calls',[]):
        if call.get('stage')=='specification_adapter':continue
        calls.append({k:call[k] for k in ('id','at','stage','usage','elapsed_seconds','trial_id','product_id','executor_attribution','outcome','integration_context') if k in call})
    calls=json_safe(calls);digest=hashlib.sha256(json.dumps(calls,sort_keys=True,allow_nan=False).encode()).hexdigest()
    atomic_write_json(source.parent/'resource-projection.json',{'schema':'receipt-projection-v1','state_path':str(source),'state_identity':[info.st_dev,info.st_ino,info.st_mtime_ns,info.st_ctime_ns,info.st_size],'executor_calls':calls,'calls_sha256':digest})
