"""Prespecified executable URACE companion projects; separate development/acceptance data."""
import json,hashlib,random
from workflow_tasks import expected as reference,BRIEFS
FAMILIES=('navigation','failover','recovery','receipts','requirements_change','interruption')
MAP={'navigation':'project_navigation','failover':'executor_failover','recovery':'transaction_recovery','requirements_change':'project_navigation','interruption':'transaction_recovery'}

def brief(family,phase=1):
 if family=='receipts':return "Implement logic.compute(request) and app.handle(request), plus JSON stdin/stdout CLI python3 app.py. request has product and records. Records have id, product, provider, stage and usage. Filter exact product, ignore specification_adapter mirror records; deduplicate non-mirrored IDs, first record wins. A valid token count is an integer >=0, excluding booleans. Use valid usage.total_tokens; else valid input_tokens + output_tokens; else usage is missing. Cached input is already included in input_tokens, never add it again. Return {known_tokens:int, missing_usage:int, calls:int, providers:{provider:{known_tokens:int,missing_usage:int,calls:int}}}. Unknown usage is not zero-cost. Empty result has empty providers. Standard library only."
 text=BRIEFS[MAP[family]].replace('Implement next_goal(requirements, completed, project_id).','Request is [requirements, completed, project_id].').replace('Implement executor_route(providers, now, remaining_tokens).','Request is [providers, now, remaining_tokens].').replace('Implement recover_change(transaction, accepted, current).','Request is [transaction, accepted, current].')
 if MAP[family]=='project_navigation':text+=' Dependency definitions MUST belong to the requested project. Filter requirement definitions to that project before resolving dependencies. A completion record cannot import a requirement from another project; missing current-project dependency definitions block even when a completion with that ID exists.'
 text=text.replace('exactly matching current criteria',"exactly matching the DEPENDENCY requirement's own current criteria (not the dependent requirement's criteria)")
 if family=='requirements_change' and phase==2:text+=' NEW OWNER REQUIREMENT v2: among eligible unfinished goals, minimize estimated_tokens first, then prefer largest numeric priority, then lexicographic ID. All requirement estimated_tokens values are nonnegative integers. This supersedes the previous priority-first selection.'
 return 'Implement logic.compute(request) and app.handle(request) delegating to logic.compute; python3 app.py reads one JSON request from stdin and prints one JSON result. Standard library only. '+text

def answer(family,request,phase=1):
 if family=='receipts':
  seen=set();out={'known_tokens':0,'missing_usage':0,'calls':0,'providers':{}}
  valid=lambda x:type(x) is int and x>=0
  for r in request['records']:
   if r['product']!=request['product'] or r.get('stage')=='specification_adapter' or r['id'] in seen:continue
   seen.add(r['id']);u=r.get('usage') or {};n=u.get('total_tokens')
   if not valid(n):n=u.get('input_tokens',-1)+u.get('output_tokens',-1) if valid(u.get('input_tokens')) and valid(u.get('output_tokens')) else None
   target=out['providers'].setdefault(r['provider'],{'known_tokens':0,'missing_usage':0,'calls':0})
   for d in [out,target]:d['calls']+=1;d['missing_usage']+=n is None;d['known_tokens']+=n or 0
  return out
 if family=='requirements_change' and phase==2:
  req,done,project=request;current={r['id']:r for r in req if r['project_id']==project};complete={r['id'] for r in done if r['project_id']==project and r['id'] in current and r['criteria']==current[r['id']]['criteria']};eligible=[r for r in current.values() if r['id'] not in complete and set(r['dependencies'])<=complete]
  return min(eligible,key=lambda r:(r['estimated_tokens'],-r['priority'],r['id']))['id'] if eligible else None
 return reference(MAP[family],request)

def cases(family,public=False,phase=1):
 if family not in FAMILIES:raise ValueError('Unknown executable project')
 rng=random.Random((12491 if public else 978121)+FAMILIES.index(family)*139+phase*43);requests=[]
 if family=='receipts':
  for i in range(8 if public else 96):
   rows=[]
   for j in range(1+rng.randrange(12)):
    usage=rng.choice([{'total_tokens':12},{'input_tokens':7,'output_tokens':3,'cached_input_tokens':6},{'total_tokens':True},{},{'total_tokens':-1},None])
    rows.append({'id':str(rng.randrange(7)),'product':rng.choice(['p','p','other']),'provider':rng.choice(['codex','claude']),'stage':rng.choice(['native','native','specification_adapter']),'usage':usage})
   requests.append({'product':'p','records':rows})
 elif MAP[family]=='project_navigation':
  for i in range(8 if public else 96):
   req=[{'id':str(j),'project_id':rng.choice(['p','p','other']),'priority':rng.randrange(100),'estimated_tokens':rng.randrange(100),'dependencies':[str(k) for k in range(j) if rng.random()<.35],'criteria':'rev'+str(rng.randrange(4))} for j in range(1+rng.randrange(7))]
   done=[{'id':r['id'],'project_id':rng.choice(['p','p','other']),'criteria':rng.choice([r['criteria'],'stale','rev0'])} for r in req if rng.random()<.65];requests.append([req,done,'p'])
 elif MAP[family]=='executor_failover':
  for i in range(8 if public else 96):requests.append([[{'id':p,'enabled':rng.choice([True,True,False]),'available':rng.choice([True,False,None]),'retry_at':rng.choice([0,50,201]),'estimated_tokens':rng.choice([0,10,100]),'quality':rng.choice([.5,.8,1]),'seconds':rng.choice([1,2,5])} for p in ['codex','claude']],100,rng.choice([None,0,50,100])])
 else:
  for i in range(8 if public else 96):
   before={'a.txt':'base','b.txt':'old'};after={'a.txt':'new','b.txt':'next'}
   if i%9==0:before['../escape']='base';after['../escape']='new'
   current={p:rng.choice([before[p],after[p],'owner edit']) for p in before};current['keep.txt']='untouched';requests.append([{'before':before,'after':after},bool(i%2),current])
 if public and MAP.get(family)=='project_navigation':
  foreign={'id':'foreign-dependency','project_id':'other','priority':1,'estimated_tokens':2,'dependencies':[],'criteria':'foreign-v1'}
  target={'id':'deliver-current','project_id':'p','priority':9,'estimated_tokens':1,'dependencies':['foreign-dependency'],'criteria':'local-v1'}
  requests.append([[foreign,target],[{'id':'foreign-dependency','project_id':'p','criteria':'foreign-v1'}],'p'])
  requests.append([[dict(foreign,project_id='p'),target],[{'id':'foreign-dependency','project_id':'p','criteria':'foreign-v1'}],'p'])
 return [{'id':('development-' if public else 'acceptance-')+str(i),'request':r,'expected':answer(family,r,phase)} for i,r in enumerate(requests)]

def public_script(rows):
 return 'import sys,json,subprocess\nsys.path.insert(0,"/workspace")\nimport app,logic\nCASES='+repr(rows)+'\nfor case in CASES:\n actual=app.handle(case["request"]);other=logic.compute(case["request"])\n assert actual==case["expected"], str({"id":case["id"],"request":case["request"],"expected":case["expected"],"actual":actual})\n assert other==actual,"app/logic disagree"\nprobe=subprocess.run([sys.executable,"app.py"],input=json.dumps(CASES[0]["request"]),text=True,capture_output=True,timeout=5)\nassert probe.returncode==0,probe.stderr\nassert json.loads(probe.stdout)==CASES[0]["expected"],"CLI result mismatch"\nprint(json.dumps({"development_checks_passed":len(CASES)+1}))\n'

ACCEPTANCE_RUNNER="""import sys,json
sys.path.insert(0,'/workspace')
import app,logic
rows=[]
for c in json.load(sys.stdin):
 try:
  actual=app.handle(c['request']);other=logic.compute(c['request'])
  rows.append({'id':c['id'],'value':actual,'modules_agree':actual==other})
 except Exception as e:rows.append({'id':c['id'],'error':type(e).__name__})
print(json.dumps(rows,allow_nan=False))
"""

def contract(family,phase=1):
 value={'schema':'repository-work-v1','family':family,'phase':phase,'brief':brief(family,phase),'development':cases(family,True,phase),'acceptance':cases(family,False,phase),'runner':ACCEPTANCE_RUNNER,'public_runner':public_script(cases(family,True,phase))}
 return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
