"""Independent, model-free runtime contracts; expected outputs never enter candidate containers."""
from pathlib import Path
from datetime import datetime, timezone
import ast, copy, hashlib, json, math, os, shutil, subprocess, sys, time, uuid, tempfile
from common import BASE, atomic
from executable_sandbox import IMAGE

SCHEMA='runtime-evaluation-v1'
SUITE='runtime-helper-contracts-v1'
ALLOWED={'milestone_suggestions.py':{'suggestions','refresh'},'milestone_feedback.py':{'assess'}}

FORBIDDEN={'open','exec','eval','compile','__import__','globals','locals','vars','getattr','setattr','delattr','input','print','os','sys','subprocess','socket','builtins','atomic','atomic_write_json','atomic_write_text','save_config','save_state','reserve','Transport','Path','state_path'}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def inventory(package):
 package=Path(package);result={}
 if package.is_symlink():raise ValueError('Runtime package symlink prohibited')
 for p in sorted(package.glob('*.py')):
  if p.is_symlink() or not p.is_file():raise ValueError('Regular runtime source required')
  result[p.name]=sha(p)
 if not result:raise ValueError('Runtime package is empty')
 return result

def engine(package):return digest(inventory(package))
def snapshot(package,destination):
 package=Path(package);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
 for name in inventory(package):shutil.copyfile(package/name,destination/name)
 return inventory(destination)

def validate_sources(before,after,declared=None):
 """Automatic changes affect selected function bodies, never policy/controllers/imports."""
 before=Path(before);after=Path(after);a=inventory(before);b=inventory(after)
 if set(a)!=set(b):raise ValueError('Automatic file creation/deletion is outside current declared scope')
 changed=[n for n in a if a[n]!=b[n]]
 if not changed:raise ValueError('No material source change')
 if declared is not None and set(changed)!=set(declared):raise ValueError('Declared files do not match source delta')
 for name in changed:
  if name not in ALLOWED:raise ValueError('Protected runtime module: '+name)
  old=ast.parse((before/name).read_text());new=ast.parse((after/name).read_text())
  if len((after/name).read_bytes())>65536:raise ValueError('Bounded runtime source required')
  def protected(tree):
   values=[]
   for node in tree.body:
    node=copy.deepcopy(node)
    if isinstance(node,ast.FunctionDef) and node.name in ALLOWED[name]:node.body=[ast.Pass()]
    values.append(ast.dump(node,include_attributes=False))
   return values
  if protected(old)!=protected(new):raise ValueError('Change outside declared function bodies')
  old_functions={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)}
  for node in new.body:
   if not isinstance(node,ast.FunctionDef) or node.name not in ALLOWED[name]:continue
   previous=old_functions[node.name]
   if ast.dump(node,include_attributes=False)==ast.dump(previous,include_attributes=False):continue
   imports=lambda n:[ast.dump(v,include_attributes=False) for v in ast.walk(n) if isinstance(v,(ast.Import,ast.ImportFrom))]
   if imports(node)!=imports(previous):raise ValueError('Function imports are frozen')
   old_calls={ast.dump(v.func,include_attributes=False) for v in ast.walk(previous) if isinstance(v,ast.Call)}
   safe_calls={'str','int','float','bool','dict','list','set','tuple','len','sorted','enumerate','range','min','max','sum','any','all','isinstance','type','abs','round','zip','ValueError'}
   safe_methods={'upper','lower','casefold','strip','get','items','values','keys','copy','count','index'}
   old_targets={ast.dump(t,include_attributes=False) for v in ast.walk(previous) if isinstance(v,(ast.Assign,ast.AnnAssign,ast.AugAssign)) for t in (v.targets if isinstance(v,ast.Assign) else [v.target])}
   for v in ast.walk(node):
    if isinstance(v,ast.Call) and ast.dump(v.func,include_attributes=False) not in old_calls:
     if not (isinstance(v.func,ast.Name) and v.func.id in safe_calls or isinstance(v.func,ast.Attribute) and v.func.attr in safe_methods):raise ValueError('New privileged/unknown call outside fixed automatic contract')
    if isinstance(v,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
     if any(ast.dump(t,include_attributes=False) not in old_targets for t in (v.targets if isinstance(v,ast.Assign) else [v.target])):raise ValueError('New mutation target outside fixed automatic contract')
    if isinstance(v,(ast.Global,ast.Nonlocal,ast.ClassDef)):raise ValueError('Global mutation or nested class prohibited')
    if isinstance(v,ast.FunctionDef) and v is not node and v.name.startswith('_'):raise ValueError('Nested private callable prohibited')
    if isinstance(v,ast.Name) and (v.id in FORBIDDEN or v.id.startswith('__')):raise ValueError('Privileged operation prohibited')
    if isinstance(v,ast.Attribute) and (v.attr.startswith('_') or v.attr in {'write_text','write_bytes','unlink','rmdir','remove','rename','read_text','read_bytes','system','popen','open'}):raise ValueError('Filesystem/process/introspection operation prohibited')
 return changed

def cases(public=False):
 def c(identifier,module,function,args,expect,kwargs=None):return {'id':identifier,'module':module,'function':function,'args':args,'kwargs':kwargs or {},'expect':expect}
 ms='milestone_suggestions';mf='milestone_feedback';wp='work_policy'
 if public:
  return [c('completed-objective-planning',ms,'suggestions',[{}, {'objectives':[{'id':'documented-complete','title':'Finished owner work','success_measure':'Owner completion criterion','status':'completed'}]}],{'suggestions':[]}),c('default-local-planning',ms,'settings',[{}],{'enabled':True})]
 fixture={'id':'milestone-owner','name':'Declared target','status':'ACTIVE','capability_gates':['cap-owner']}
 choose={'provider':'codex','family':'navigation','model':'declared','contract':'owner-contract','engine':'engine','now':100,'enabled':True}
 return [
 c('settings-default',ms,'settings',[{}],{'enabled':True}),
 c('settings-disabled',ms,'settings',[{'auto_milestones':{'enabled':False}}],{'enabled':False}),
 c('settings-type',ms,'settings',[{'auto_milestones':{'enabled':'false'}}],{'$error':'ValueError'}),
 c('settings-key',ms,'settings',[{'auto_milestones':{'unapproved':True}}],{'$error':'ValueError'}),
 c('empty-planning',ms,'suggestions',[{},{}],{'suggestions':[],'additional_model_calls':0}),
 c('disabled-planning',ms,'suggestions',[{'auto_milestones':{'enabled':False},'capability_envelope':{'capabilities':[{'id':'cap'}]}},{}],{'suggestions':[]}),
 c('unknown-evidence',ms,'suggestions',[{'capability_envelope':{'capabilities':[{'id':'cap-hidden'}]}},{}],{'suggestions.0.bottleneck.status':'UNKNOWN','suggestions.0.status':'DRAFT','suggestions.0.automatically_activated':False}),
 c('complete-capability',ms,'suggestions',[{'capability_envelope':{'capabilities':[{'id':'cap'}]}},{'capability_states':[{'capability_id':'cap','status':'CAPABLE'}]}],{'suggestions':[]}),
 c('covered-milestone',ms,'suggestions',[{'capability_envelope':{'capabilities':[{'id':'cap'}],'milestones':[{'id':'existing','status':'ACTIVE','capability_gates':['cap']}]}},{}],{'suggestions':[]}),
 c('finished-owner-objective',ms,'suggestions',[{}, {'objectives':[{'id':'g-private','title':'Previously completed work','success_measure':'Recorded completion','status':'completed'}]}],{'suggestions':[]}),
 c('finished-upper-objective',ms,'suggestions',[{}, {'objectives':[{'id':'g-upper','title':'Completed goal','success_measure':'Recorded completion','status':'COMPLETED'}]}],{'suggestions':[]}),
 c('duplicate-capability',ms,'suggestions',[{'capability_envelope':{'capabilities':[{'id':'same'},{'id':'same'}]}},{}],{'suggestions.0.source_refs':['capability:same'],'suggestions.1':{'$absent':True}}),
 c('native-low',wp,'choose',[{}],{'native_effort':'low','adaptive':False},{**choose,'default_effort':'low'}),
 c('native-high',wp,'choose',[{}],{'native_effort':'high','adaptive':False},{**choose,'default_effort':'high'}),
 c('native-invalid',wp,'choose',[{}],{'native_effort':'medium'},{**choose,'default_effort':'invalid'}),
 c('milestone-unknown',mf,'assess',[{}, {}, fixture],{'phase':'IMPLEMENTATION','canonical_status':'ACTIVE','additional_model_calls':0}),
 c('historical-achievement',mf,'assess',[{}, {}, {**fixture,'status':'ACHIEVED'}],{'canonical_status':'ACHIEVED','operational_status':'NEEDS_REASSESSMENT'}),
 c('zero-quality-contract',mf,'assess',[{}, {'capability_states':[{'capability_id':'cap-owner','status':'CAPABLE'}]}, {**fixture,'quality_gates':[{'scope':'owner','min_streak':0}]}],{'operational_status':'READY_FOR_GATE_EVALUATION'}),
 c('missing-quality',mf,'assess',[{}, {'capability_states':[{'capability_id':'cap-owner','status':'CAPABLE'}]}, {**fixture,'quality_gates':[{'scope':'owner','min_streak':3}]}],{'phase':'VALIDATION','quality_gates.0.satisfied':False}),
 c('pending-authority',mf,'assess',[{}, {}, {**fixture,'status':'PENDING'}],{'canonical_status':'PENDING','phase':'PLANNING','operational_status':'PENDING'}),
 ]

def contract():
 return {'schema':SCHEMA,'suite':SUITE,'cases':cases(),'repeats':2,'sandbox_image':IMAGE,'evaluator_sha256':sha(__file__),'regression_rule':'All candidate private cases pass; no baseline pass may be lost; immutable full core regression must also pass','scope':'Bounded runtime helper behavior; not overall worth, user benefit or complete system correctness'}

RUNNER=r'''
import sys,json,importlib,copy
sys.path.insert(0,'/package')
requests=json.load(sys.stdin);results=[]
for request in requests:
 args=copy.deepcopy(request['args']);kwargs=copy.deepcopy(request['kwargs']);before=copy.deepcopy([args,kwargs])
 try:
  value=getattr(importlib.import_module('urace.'+request['module']),request['function'])(*args,**kwargs)
  result={'value':json.loads(json.dumps(value,allow_nan=False))}
 except Exception as error:result={'error':type(error).__name__}
 result['inputs_unchanged']=before==[args,kwargs];result['id']=request['id'];results.append(result)
print(json.dumps(results,allow_nan=False))
'''

def container_run(package,requests):
 package=Path(package).resolve();name='urace-runtime-eval-'+uuid.uuid4().hex
 command=['docker','run','-i','--rm','--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user',f'{os.getuid()}:{os.getgid()}','--pids-limit','32','--memory','256m','--memory-swap','256m','--cpus','1','--tmpfs','/tmp:rw,nosuid,noexec,size=32m','--mount',f'type=bind,src={package},dst=/package/urace,readonly',IMAGE,'python3','-I','-c',RUNNER]
 process=None
 try:
  with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
   process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=output,stderr=errors)
   process.stdin.write(json.dumps(requests).encode());process.stdin.close();deadline=time.monotonic()+60
   while process.poll() is None:
    if output.tell()>262144 or errors.tell()>65536:raise ValueError('Runtime observation limit exceeded')
    if time.monotonic()>deadline:raise TimeoutError('Runtime sandbox wall limit')
    time.sleep(.05)
   output.seek(0);errors.seek(0);raw=output.read(262145);error=errors.read(65537)
   if len(raw)>262144 or len(error)>65536:raise ValueError('Runtime observation limit exceeded')
   if process.returncode:raise RuntimeError('Runtime sandbox failed: '+error[-300:].decode(errors='replace'))
   rows=json.loads(raw)
   if not isinstance(rows,list) or [r.get('id') for r in rows]!=[r['id'] for r in requests]:raise ValueError('Incomplete runtime observations')
   return rows
 except BaseException:
  if process is not None and process.poll() is None:
   subprocess.run(['docker','kill',name],capture_output=True,timeout=10)
   process.kill();process.wait(timeout=10)
  raise

def matches(observed,expected):
 if '$error' in expected:return observed.get('error')==expected['$error']
 if 'value' not in observed:return False
 for key,value in expected.items():
  found=observed['value'];absent=False
  try:
   for part in key.split('.'):found=found[int(part)] if isinstance(found,list) else found[part]
  except (KeyError,IndexError,TypeError,ValueError):absent=True
  if isinstance(value,dict) and value=={'$absent':True}:
   if not absent:return False
  elif absent or found!=value:return False
 return True

def measure(base,package,role,*,runner=None,public=False):
 base=Path(base);package=Path(package);suite=contract();source=inventory(package);requests=[{k:v for k,v in case.items() if k!='expect'} for case in cases(public)];start=time.monotonic();runs=[]
 for _ in range(2):runs.append((runner or container_run)(package,requests))
 if inventory(package)!=source:raise ValueError('Source changed during runtime measurement')
 outcomes={}
 for i,case in enumerate(cases(public)):
  outcomes[case['id']]=all(matches(run[i],case['expect']) and run[i].get('inputs_unchanged') is True for run in runs) and runs[0][i]==runs[1][i]
 receipt={'schema':SCHEMA,'id':'evaluation-'+uuid.uuid4().hex,'at':now(),'role':role,'suite_sha256':digest(suite),'sources':source,'engine_sha256':digest(source),'complete':True,'case_results':outcomes,'observations':runs,'score':100*sum(outcomes.values())/len(outcomes),'all_pass':all(outcomes.values()),'deterministic':runs[0]==runs[1],'wall_seconds':time.monotonic()-start,'model_calls':0,'tokens':0,'credit_decrement':None,'public':public}
 path=base/'runtime-evaluations'/receipt['id']/'receipt.json';atomic(path,receipt);return receipt

def load_receipt(base,identifier,*,public=False):
 if not isinstance(identifier,str) or not identifier.startswith('evaluation-') or not identifier.replace('-','').isalnum():raise ValueError('Invalid runtime evaluation id')
 path=Path(base)/'runtime-evaluations'/identifier/'receipt.json'
 if path.is_symlink() or path.parent.is_symlink():raise ValueError('Evaluation symlink prohibited')
 receipt=json.loads(path.read_text())
 if receipt.get('schema')!=SCHEMA or receipt.get('id')!=identifier or receipt.get('suite_sha256')!=digest(contract()) or receipt.get('public') is not public or receipt.get('complete') is not True:raise ValueError('Runtime evidence is stale, public or incomplete')
 if not isinstance(receipt.get('case_results'),dict) or set(receipt['case_results'])!={c['id'] for c in cases(public)}:raise ValueError('Runtime case observations incomplete')
 if any(type(v) is not bool for v in receipt['case_results'].values()):raise ValueError('Invalid runtime verdict')
 # Verdicts and scores are derived again from retained observations, not trusted scalars.
 runs=receipt.get('observations');expected=cases(public)
 if not isinstance(runs,list) or len(runs)!=2 or any(not isinstance(run,list) or len(run)!=len(expected) for run in runs):raise ValueError('Runtime observation transcript incomplete')
 derived={case['id']:all(run[i].get('id')==case['id'] and matches(run[i],case['expect']) and run[i].get('inputs_unchanged') is True for run in runs) and runs[0][i]==runs[1][i] for i,case in enumerate(expected)}
 if derived!=receipt['case_results'] or receipt.get('score')!=100*sum(derived.values())/len(derived) or receipt.get('all_pass')!=all(derived.values()) or receipt.get('deterministic')!=(runs[0]==runs[1]) or receipt.get('engine_sha256')!=digest(receipt.get('sources')):raise ValueError('Runtime observation integrity mismatch')
 return receipt
