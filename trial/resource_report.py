"""Observed managed executor use, deduplicating preserved mirrored native receipts."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,tempfile
from common import operations_root
ROOT=operations_root()

def main():
    order=['productive-native-30d-v1','autonomous-maintenance-v1','accelerated-productivity-v1','productive-native-30d-v2','productive-native-30d-v3','pretrial-calibration-v3','productive-native-30d-v4','productive-native-30d-v5','adaptive-effort-study-v1','productive-native-30d-v6','adaptive-effort-study-v2','cli-native-qualification-v1','productive-native-30d-v7','adaptive-effort-study-v3','productive-native-30d-v8','adaptive-effort-study-v4','urace-self-improvement-v1']
    from resource_governor import registered_roots,external_roots
    order+=registered_roots()+[str(p) for p in external_roots(ROOT)]
    reservations={};finished={};copies=0
    for name in order:
        path=ROOT.parent/name/'ledger.jsonl'
        if not path.exists():continue
        for line in path.read_text().splitlines():
            if not line:continue
            row=json.loads(line);table=reservations if row['kind']=='reserved' else finished
            if row['kind'] not in ('reserved','finished'):continue
            if row['id'] in table:copies+=1
            table[row['id']]={**row,'attributed_root':name}
    providers={}
    for provider in ('codex','claude'):
        rows=[r for r in reservations.values() if r['provider']==provider]
        done=[finished.get(r['id'],{}) for r in rows]
        providers[provider]={'unique_native_calls':len(rows),'known_tokens':sum(r.get('tokens') or 0 for r in done),'missing_usage':sum(r.get('tokens') is None for r in done),'known_native_wall_seconds':sum(r.get('wall_seconds') or 0 for r in done),'api_equivalent_usd':sum(r.get('provider_reported_total_cost_usd') or 0 for r in done) if provider=='claude' and len(done)==len(rows) and all(v.get('provider_reported_total_cost_usd') is not None for v in done) else None,'actual_subscription_credit_charge':None,'inflight_calls':sum(r['id'] not in finished for r in rows),'completed_missing_usage':sum(r['id'] in finished and finished[r['id']].get('tokens') is None for r in rows),'reserved_tokens_for_unmeasured_usage':sum(r.get('token_reservation',50000) for r in rows if finished.get(r['id'],{}).get('tokens') is None)}
    report={'at':datetime.now(timezone.utc).isoformat(),'providers':providers,'unique_native_calls':len(reservations),'known_tokens':sum(p['known_tokens'] for p in providers.values()),'duplicate_preserved_event_copies_excluded':copies,'scope':'These managed study/maintenance ledgers only; earlier preparation, this chat and operator labor are not included','billing_attribution':'Tokens are measured native usage, not evidence of monetary subscription-credit decrements','native_failure_and_product_acceptance_differ':'See per-job receipts: a successful native transport can still produce a rejected artifact','cohort_breakdown':{name:{'calls':sum(r['attributed_root']==name for r in reservations.values()),'known_tokens':sum(finished.get(r['id'],{}).get('tokens') or 0 for r in reservations.values() if r['attributed_root']==name)} for name in order}}
    payload=json.dumps(report,indent=2)+'\n'
    with tempfile.NamedTemporaryFile('w',dir=ROOT,prefix='resources-',delete=False) as stream:
        stream.write(payload);stream.flush();os.fsync(stream.fileno());temporary=Path(stream.name)
    temporary.replace(ROOT/'resources-latest.json');print(payload)
if __name__=='__main__':main()
