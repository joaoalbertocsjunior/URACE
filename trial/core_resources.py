"""Reconcile canonical native receipts into trial reports without duplicating mirrors."""
from datetime import datetime
import json
import hashlib
import sys
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def _resource_projection(path, signature):
    # Keep only receipt data. Owner context and the rest of the large state are
    # released after parsing. Authoritative validation never uses this cache.
    state=json.loads(Path(path).read_text())
    return {'executor_state':{'executor_calls':state.get('executor_state',{}).get('executor_calls',[])}}

def resource_state(path):
    path=Path(path)
    try:info=path.stat()
    except FileNotFoundError:return {}
    signature=(info.st_dev,info.st_ino,info.st_mtime_ns,info.st_ctime_ns,info.st_size)
    projection=path.parent/'resource-projection.json'
    try:
        with projection.open('rb') as stream:raw=stream.read(8388609)
        if len(raw)<=8388608:
            value=json.loads(raw);calls=value['executor_calls']
            if (value.get('schema')=='receipt-projection-v1' and value.get('state_path')==str(path.resolve())
                    and value.get('state_identity')==list(signature) and isinstance(calls,list)
                    and hashlib.sha256(json.dumps(calls,sort_keys=True,allow_nan=False).encode()).hexdigest()==value.get('calls_sha256')):
                return {'executor_state':{'executor_calls':calls}}
    except (OSError,ValueError,KeyError,TypeError):pass
    return _resource_projection(str(path.resolve()),signature)

def events(base, product_id, trial_id=None, started_unix=None):
    base = Path(base)
    path = base.parent/'runtime/urace/config.json'
    if not path.exists():
        return []
    config = json.loads(path.read_text())
    sys.path.insert(0, str(base.parent/'runtime'))
    from urace._common import state_path
    from urace.resource_usage import observed_calls, usage_totals, number, product_identity
    if product_identity(config) != product_id:
        return []
    path = state_path(config)
    state = resource_state(path)
    adapters = {p['id']: p.get('adapter', config.get('executor',{}).get('kind','codex-cli')).removesuffix('-cli')
                for p in config.get('executor', {}).get('providers', [])}
    rows = []
    for call in observed_calls(config, state):
        # Adapter calls are projections of the native trial ledger, not new work.
        if call.get('stage') == 'specification_adapter' or not call.get('at'):
            continue
        at = datetime.fromisoformat(call['at']).timestamp()
        if started_unix is not None and at < started_unix:
            continue
        if trial_id and call.get('trial_id') not in (None, trial_id):
            continue
        usage = call.get('usage') or {}
        receipts = usage.get('transport_usage') or [{'provider_id': call.get('executor_attribution', {}).get('executor_id'), 'usage': usage}]
        for index, receipt in enumerate(receipts):
            metrics = usage_totals(receipt.get('usage'))
            provider = receipt.get('provider_id')
            provider = adapters.get(provider, provider)
            provider = provider if provider in ('codex', 'claude') else 'unattributed'
            identity = 'core:'+str(call.get('id'))+':'+str(index)
            common = {'id': identity, 'provider': provider, 'product_id': product_id,
                      'trial_id': trial_id, 'source': 'canonical core/freeform native receipt',
                      'logical_call_id': call.get('id'), 'at': call['at'],
                      'receipt_source':str(path.parent/'freeform-routing-resources.jsonl' if call.get('stage')=='freeform-routing' else (path.parent/'resource-usage.sqlite3' if (path.parent/'resource-usage.sqlite3').exists() else path))}
            rows.append({**common, 'kind': 'reserved', 'at_unix': at})
            rows.append({**common, 'kind': 'finished',
                         'tokens': None if metrics['missing_usage'] else metrics['known_tokens'],
                         'reported_cost_usd': metrics['reported_cost_usd'],
                         'wall_seconds': number(call.get('elapsed_seconds')) if index == 0 else None,
                         'wall_scope': 'logical route elapsed; retained once across transports',
                         'usage_missing': bool(metrics['missing_usage'])})
    return rows
