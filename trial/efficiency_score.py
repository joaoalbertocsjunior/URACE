"""Inspectable declarative scores. No eval, plugins, executable formulas or hidden weights."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,math,re,time
from common import BASE,atomic

def read(path,default):
    return json.loads(path.read_text()) if path.exists() else default

def product_id(name):
    matches=[p for p in read(BASE/'products.json',{}).get('products',[]) if name in (p['id'],p['name'])]
    if len(matches)!=1:raise ValueError('Unknown or ambiguous product: '+name)
    return matches[0]['id']

def validate(config):
    if not isinstance(config,dict) or set(config)!={'enabled','metrics'} or type(config['enabled']) is not bool:raise ValueError('Expected enabled boolean and metrics list')
    if not isinstance(config['metrics'],list) or len(config['metrics'])>20:raise ValueError('At most20 scoring metrics')
    if config['enabled'] and not config['metrics']:raise ValueError('Enabled score needs metrics')
    names=[]
    for m in config['metrics']:
        if not isinstance(m,dict) or set(m)!={'name','weight','direction','target'}:raise ValueError('Each metric needs name,weight,direction,target')
        if not isinstance(m['name'],str) or not re.fullmatch(r'(?:custom\.)?[a-z][a-z0-9_]{0,79}',m['name']):raise ValueError('Invalid metric name')
        if m['direction'] not in ('higher','lower'):raise ValueError('Metric direction must be higher or lower')
        for k in ('weight','target'):
            if type(m[k]) not in (int,float) or not math.isfinite(m[k]) or m[k]<=0:raise ValueError(k+' must be finite and positive')
        names.append(m['name'])
    if len(set(names))!=len(names):raise ValueError('Duplicate scoring metric')
    if config['metrics'] and not math.isfinite(sum(m['weight'] for m in config['metrics'])):raise ValueError('Nonfinite weight sum')
    return config

def configure(config,product='*',executor='all'):
    validate(config);key=('*' if product=='*' else product_id(product))+'|'+executor
    with (BASE/'efficiency-config.guard').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);path=BASE/'efficiency-config.json';data=read(path,{'profiles':{}})
        if path.exists():atomic(BASE/'history'/('efficiency-config-'+str(time.time_ns())+'.json'),data)
        data['profiles'][key]=config;atomic(path,data)
    return {'profile':key,'configuration':config}

def inspect(product='*',executor='all'):
    key=('*' if product=='*' else product_id(product))+'|'+executor
    return {'profile':key,'configuration':read(BASE/'efficiency-config.json',{'profiles':{}})['profiles'].get(key,{'enabled':False,'metrics':[]})}

def record(product,executor,name,value,unit,source):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}',name):raise ValueError('Invalid custom metric name')
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Custom metric must be finite and nonnegative')
    if not source.strip() or len(source)>2000 or len(unit)>80:raise ValueError('Bounded nonempty provenance source required')
    epoch=read(BASE/'accounting-epoch.json',{});row={'at':datetime.now(timezone.utc).isoformat(),'product_id':product_id(product),'executor':executor,'name':name,'value':value,'unit':unit,'source':source,'accounting_epoch_id':epoch.get('id'),'verification':'user_supplied_unverified'}
    with (BASE/'custom-metrics.guard').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        from urace.authenticated_journal import append_row
        append_row(BASE/'custom-metrics.jsonl',row)
    return row

def score(report):
    profiles=read(BASE/'efficiency-config.json',{'profiles':{}})['profiles'];product=report.get('product_id','*');executor=report['executor'];profile=next((k for k in (product+'|'+executor,product+'|all','*|'+executor,'*|all') if k in profiles),None)
    config=validate(profiles[profile]) if profile else {'enabled':False,'metrics':[]}
    if not config['enabled']:return {'enabled':False,'score':None,'reason':'Configure weights, targets and metrics through config efficiency','methodology_review':methodology(report,config,[],[])}
    observations=read_custom();epoch=report.get('accounting_epoch');values={**report,**report['efficiency']};components=[];missing=[]
    for metric in config['metrics']:
        name=metric['name'];provenance='Measured native resources / explicitly scoped engineering output quality or editorial acceptance'
        if name.startswith('custom.'):
            eligible=[r for r in observations if r['product_id']==product and r['executor'] in ('all',executor) and r['name']==name[7:] and (report['scope']=='lifetime' or (epoch and r.get('accounting_epoch_id')==epoch['id']))]
            observation=eligible[-1] if eligible else None;value=observation['value'] if observation else None;provenance=observation
        else:value=values.get(name)
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:missing.append(name);continue
        normalized=min(1,value/metric['target']) if metric['direction']=='higher' else (1 if value==0 else min(1,metric['target']/value))
        components.append({**metric,'observed':value,'normalized':normalized,'provenance':provenance})
    result=None if missing else 100*sum(c['weight']*c['normalized'] for c in components)/sum(c['weight'] for c in components)
    return {'enabled':True,'profile':profile,'score':result,'range':[0,100],'missing_metrics':missing,'components':components,'configuration':config,'configuration_sha256':hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),'methodology_review':methodology(report,config,components,missing),'interpretation':'Provisional user-defined decision aid, not independent proof of efficiency, real-world value or acceptance. Required missing data withholds score. Formula revisions require matched held-out evaluation before superiority can be claimed.'}

def methodology(report,config,components,missing):
    issues=[];suggestions=[];names={m['name'] for m in config['metrics']}
    if report.get('missing_usage',0):issues.append('Incomplete native usage: full cost efficiency cannot be established')
    if missing:issues.append('Required metrics missing: '+', '.join(missing))
    completed=report.get('completed_tasks',0);accepted=report.get('accepted_improvements',0)
    if completed<20 or accepted<5:issues.append('Sparse accepted-outcome sample: descriptive results only')
    if 'acceptance_rate_pct' not in names:suggestions.append('Include outcome quality/acceptance with fixed independent validation criteria')
    if not names&{'tokens_per_accepted_improvement','elapsed_seconds_per_accepted_improvement'}:suggestions.append('Include total resource/time cost per accepted outcome, retaining rejected work')
    if 'accepted_improvements_per_elapsed_hour' not in names:suggestions.append('Include accepted outcomes per elapsed hour to detect underuse and slow throughput')
    if any(c['name'].startswith('custom.') for c in components):issues.append('Custom observations are user-supplied and unverified; independently validate their provenance')
    if any(m['name'] in ('known_tokens','native_calls','known_executor_seconds','completed_tasks') for m in config['metrics']):issues.append('Raw activity/spending volume is not validated productive efficiency')
    if config['metrics']:
        total=sum(m['weight'] for m in config['metrics'])
        if max(m['weight']/total for m in config['metrics'])>.8:issues.append('One metric dominates the score; check sensitivity and gaming risk')
    if components and all(c['normalized']==1 for c in components):suggestions.append('All targets saturated: test discrimination against held-out outcome examples before recalibrating')
    suggestions.append('Compare candidate formulas on matched held-out tasks with fixed quality gates; retain formula hashes and raw measurements')
    return {'reviewed_at':datetime.now(timezone.utc).isoformat(),'review_version':'screening-v1','issues':issues,'recommended_checks':suggestions,'formula_optimality_established':False,'held_out_calibration':'Not established','score_reliability':'Unvalidated operational/editorial proxy','validated_value_score':None,'sample_screen':{'completed_tasks':completed,'accepted_improvements':accepted,'descriptive_min_completed':20,'descriptive_min_accepted':5,'thresholds_are_screening_not_statistical_guarantees':True},'automatic_formula_mutation':False,'revision_policy':'Each configuration change is archived and hash-identified; change calculations only with disclosed rationale and validated comparison, never to make results look better'}

def read_custom():
    p=BASE/'custom-metrics.jsonl'
    return [json.loads(line) for line in p.read_text().splitlines() if line] if p.exists() else []
