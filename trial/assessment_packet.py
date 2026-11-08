"""Small, read-only evidence index. Full evidence remains authoritative and expandable."""
import hashlib,json,time
from pathlib import Path
from qualification_protocol import progress

FILES=('trial-clock.json','active-version.json','supervisor-health.json','review-schedule.json',
       'repository-study-latest.json','operational-review-latest.json','verification-latest.json',
       'claude-preflight-latest.json','harness-manifest.json')

def packet(base):
    base=Path(base).resolve();started=time.time();data={};evidence={}
    for name in FILES:
        p=base/name
        if p.is_symlink():raise ValueError('Evidence symlink prohibited')
        if not p.exists():evidence[name]={'status':'MISSING'};continue
        raw=p.read_bytes();data[name]=json.loads(raw)
        evidence[name]={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    summary=data.get('repository-study-latest.json',{});identity=summary.get('plan',{});cohort=summary.get('cohort')
    current={'status':'NO_CURRENT_COHORT'}
    from project_work import engine_hash
    current_engine=engine_hash()
    if isinstance(cohort,str) and cohort.isalnum() and identity.get('trial_id')==data.get('trial-clock.json',{}).get('trial_id'):
        root=base/'repository-studies'/cohort
        if root.is_symlink():raise ValueError('Cohort symlink prohibited')
        current=progress(root,identity)
        current['current_engine_matches']=identity.get('engine_sha256')==current_engine
        if not current['current_engine_matches']:current['status']='INSUFFICIENT_STALE_ENGINE'
    health=data.get('supervisor-health.json',{});review=data.get('operational-review-latest.json',{})
    return {'schema':'assessment-evidence-packet-v1','observation':{'started_unix':started,'ended_unix':time.time(),'atomic_snapshot':False},
            'trial':data.get('trial-clock.json'),'product':data.get('active-version.json'),'current_engine_sha256':current_engine,
            'health':health,'review_schedule':data.get('review-schedule.json'),'cohort':cohort,'qualification':current,
            'last_review':{k:review.get(k) for k in ('at','trial_id','runtime_integrity_pass','accounting_complete','evidence_warnings','issues')},
            'preflight':data.get('claude-preflight-latest.json',{'status':'UNMEASURED'}),
            'evidence_index':evidence,'unsupported_value_claims':False,
            'assessment_complete':False,
            'drilldown_required':['Read full linked receipt/source/test evidence for correctness, failure diagnosis, treatment fairness, quality dimensions and per-version/resource assertions','Verify current source qualification and freshness before reusing passing tests','Compare compatible profiles and inspect every incomplete/failed arm; do not infer missing evidence from this index'],
            'quality_contract':'Index only: preserves qualification gates and exact progress facts; does not replace a complete assessment or code review. No prompt truncation, summary-based acceptance or inferred success.'}
