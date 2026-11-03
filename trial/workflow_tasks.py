"""Prespecified core-use scenarios, public examples, and separate sealed hold-outs."""
import hashlib,json,random
FAMILIES=('project_navigation','executor_failover','transaction_recovery')
BRIEFS={
 'project_navigation':"Implement next_goal(requirements, completed, project_id). Requirements have id, project_id, priority, dependencies, criteria. Completed records have id, project_id, criteria. Return the ID of the unfinished requirement with the LARGEST numeric priority (larger numbers mean higher priority) whose dependencies have a matching current-project completion with exactly matching current criteria; tie-break lexicographically. A completion from another project or older criteria never satisfies it. Unknown dependencies block. Return None if no eligible work. Input IDs are unique within each list.",
 'executor_failover':"Implement executor_route(providers, now, remaining_tokens). Providers have id, enabled, available (True/False/None), retry_at (epoch), estimated_tokens, quality (0..1), seconds (>0). Return enabled, explicitly available provider with retry_at <= now and estimated_tokens <= remaining_tokens (None means unbounded). Maximize quality/seconds, then minimize estimated_tokens, then lexicographic id. If none are eligible return None. Availability of one provider is independent of another.",
 'transaction_recovery':"Implement recover_change(transaction, accepted, current). transaction has before and after mappings of relative paths to strings; current maps paths to current strings. Return {action:ROLL_FORWARD|ROLL_BACK|CONFLICT, writes:dict}. Accepted chooses after; otherwise before. Key sets must match. Absolute paths, empty paths and paths containing .. components are conflicts. Every current path must match either its before or after bytes; unrelated edits cause conflict. On conflict return empty writes. Otherwise return only chosen values different from current; preserve unrelated current files. Never perform I/O."}

def expected(family,args):
 if family=='project_navigation':
  requirements,completed,project=args;req={r['id']:r for r in requirements if r['project_id']==project}
  done={r['id'] for r in completed if r['project_id']==project and r['id'] in req and r['criteria']==req[r['id']]['criteria']}
  eligible=[r for r in req.values() if r['id'] not in done and set(r['dependencies'])<=done]
  return min(eligible,key=lambda r:(-r['priority'],r['id']))['id'] if eligible else None
 if family=='executor_failover':
  providers,now,budget=args
  ready=[p for p in providers if p['enabled'] is True and p['available'] is True and p['retry_at']<=now and (budget is None or p['estimated_tokens']<=budget)]
  return min(ready,key=lambda p:(-p['quality']/p['seconds'],p['estimated_tokens'],p['id']))['id'] if ready else None
 transaction,accepted,current=args;before,after=transaction['before'],transaction['after']
 valid=set(before)==set(after) and all(path and not path.startswith('/') and '..' not in path.split('/') and current.get(path) in (before[path],after[path]) for path in before)
 if not valid:return {'action':'CONFLICT','writes':{}}
 target=after if accepted else before
 return {'action':'ROLL_FORWARD' if accepted else 'ROLL_BACK','writes':{p:v for p,v in target.items() if current.get(p)!=v}}

def cases(family,public=False):
 if public:
  if family=='project_navigation':
   req=[{'id':'contract','project_id':'p','priority':10,'dependencies':[],'criteria':'v1'},{'id':'deliver','project_id':'p','priority':20,'dependencies':['contract'],'criteria':'v1'}]
   inputs=[[req,[{'id':'contract','project_id':'p','criteria':'v1'}],'p'],[req,[{'id':'contract','project_id':'other','criteria':'v1'}],'p'],[req,[{'id':'contract','project_id':'p','criteria':'old'}],'p'],[[],[],'p']];fn='next_goal'
  elif family=='executor_failover':
   a={'id':'codex','enabled':True,'available':False,'retry_at':0,'estimated_tokens':10,'quality':1,'seconds':2};b={'id':'claude','enabled':True,'available':True,'retry_at':0,'estimated_tokens':10,'quality':1,'seconds':3}
   inputs=[[[a,b],100,20],[[dict(a,available=True),dict(b,available=False)],100,20],[[dict(a,available=None),dict(b,available=False)],100,None],[[dict(a,available=True),b],100,5]];fn='executor_route'
  else:
   transaction={'before':{'product.txt':'base'},'after':{'product.txt':'next'}};bad={'before':{'../escape':'base'},'after':{'../escape':'next'}}
   inputs=[[transaction,True,{'product.txt':'base','unrelated.txt':'keep'}],[transaction,False,{'product.txt':'next'}],[transaction,True,{'product.txt':'external'}],[bad,False,{'../escape':'base'}]];fn='recover_change'
  if family=='project_navigation':
   independent=[{'id':'alpha','project_id':'p','priority':10,'dependencies':[],'criteria':'current'},{'id':'beta','project_id':'p','priority':20,'dependencies':[],'criteria':'current'}]
   inputs.extend([[independent,[],'p'],[[dict(r,priority=20) for r in independent],[],'p']])
  return [{'id':'public-'+str(i),'workflow':family,'function':fn,'args':args,'expected':expected(family,args),'error':None} for i,args in enumerate(inputs)]
 rng=random.Random(2381+(FAMILIES.index(family)*173)+10000);rows=[]
 for i in range(4 if public else 64):
  if family=='project_navigation':
   req=[{'id':str(j),'project_id':'p','priority':rng.randint(1,100),'dependencies':[str(k) for k in range(j) if rng.random()<.3],'criteria':'v'+str(rng.randrange(2))} for j in range(1+rng.randrange(6))]
   done=[{'id':r['id'],'project_id':rng.choice(['p','other']),'criteria':rng.choice(['v0','v1','old'])} for r in req if rng.random()<.7];args=[req,done,'p'];fn='next_goal'
  elif family=='executor_failover':
   providers=[{'id':p,'enabled':rng.choice([True,True,False]),'available':rng.choice([True,False,None]),'retry_at':rng.choice([0,50,200]),'estimated_tokens':rng.choice([5,20,80]),'quality':rng.choice([.5,.75,1]),'seconds':rng.choice([1,2,10])} for p in ['codex','claude']];args=[providers,100,rng.choice([None,10,50,100])];fn='executor_route'
  else:
   before={'product.txt':'base','policy.txt':'old'};after={'product.txt':'candidate','policy.txt':'new'}
   if i%7==0:before['../escape']='a';after['../escape']='b'
   current={p:rng.choice([before[p],after[p],'external']) for p in before};current['unrelated.txt']='keep';args=[{'before':before,'after':after},bool(i%2),current];fn='recover_change'
  rows.append({'id':('public-' if public else 'hidden-')+str(i),'workflow':family,'function':fn,'args':args,'expected':expected(family,args),'error':None})
 return rows

def manifest(family):
 from execution_contract import fingerprint
 public,hidden=cases(family,True),cases(family)
 return {'family':family,'brief_sha256':hashlib.sha256(BRIEFS[family].encode()).hexdigest(),'public_sha256':hashlib.sha256(json.dumps(public,sort_keys=True).encode()).hexdigest(),'held_out_sha256':hashlib.sha256(json.dumps(hidden,sort_keys=True).encode()).hexdigest(),'execution_sha256':fingerprint(),'case_count':len(public)+len(hidden),'public_cases':len(public),'held_out_cases':len(hidden)}
