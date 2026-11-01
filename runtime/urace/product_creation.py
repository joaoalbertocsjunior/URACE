"""Explicit product creation from owner prose; preserves source intent and isolated lifecycle state."""
from pathlib import Path
import copy,hashlib,json,os,re,uuid,contextlib,io

SCHEMA='product-intent-bootstrap-v1'

def explicit_creation(text):
 return bool(re.match(r'^(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?(?:create|build|make|bootstrap|start)\b',text.strip(),re.I) and re.search(r'\b(?:new\s+(?:product|app|application|project|tool|service|website|system)|(?:a|an)\s+(?:\w+\s+){0,6}(?:app|application|product|website|tool|service|system))\b',text,re.I))

def interpret(text,registry,active=None):
 if not isinstance(text,str) or not text.strip() or len(text.encode())>65536:raise ValueError('Nonempty bounded owner text required; no truncation')
 # Split only on explicit independent action boundaries. Keep ordinary feature conjunctions intact.
 parts=re.split(r'(?<=[.;])\s+(?=(?:also\s+)?(?:create|build|make|bootstrap|start|add|change|update|improve|fix|remove)\b)|\s+(?:and\s+also|also|and)\s+(?=(?:create|build|make|bootstrap|start|add|change|update|improve|fix|remove)\b)',text,flags=re.I)
 result=[];uncertain=[]
 for part in parts:
  probe=re.sub(r'^(?:and\s+)?also\s+','',part,flags=re.I)
  names=[e['name'] for e in registry if isinstance(e.get('name'),str) and re.search(r'(?<!\w)'+re.escape(e['name'])+r'(?!\w)',part,re.I)]
  creation=explicit_creation(probe)
  if re.search(r'\b(?:if|unless|instead|either|otherwise|before|after)\b',part,re.I) or re.match(r'^(?:do not|don.t|never|how|why|what)\b',probe,re.I):uncertain.append({'text':part,'reason':'Condition, negation, alternative or discussion needs explicit interpretation'});continue
  if creation and re.search(r'\b(?:existing|current)\s+(?:product|app|project)\b',probe,re.I):uncertain.append({'text':part,'reason':'Creation and existing-product references overlap in the same section'});continue
  if creation:result.append({'kind':'new_product','text':part,'target':None,'evidence':'Explicit local creation request'})
  elif re.match(r'^(?:please\s+)?(?:add|change|update|improve|fix|remove)\b',probe,re.I):
   if len(names)==1:result.append({'kind':'existing_product_change','text':part,'target':names[0],'evidence':'Explicit registered product reference'})
   elif not names and len(parts)==1 and active:result.append({'kind':'existing_product_change','text':part,'target':active,'evidence':'Current product context; original text retained'})
   else:uncertain.append({'text':part,'reason':'Existing-product target is absent or ambiguous'})
  else:uncertain.append({'text':part,'reason':'No high-confidence local creation/change interpretation; preserve for bounded semantic routing'})
 return {'schema':SCHEMA,'raw_text':text,'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'intents':result,'unresolved':uncertain,'status':'INTERPRETATION_REQUIRED' if uncertain else 'INTERPRETED','native_calls':0,'intent_understanding_guaranteed':False}

def validate_entry(entry,root):
 root=Path(root).resolve();rel=Path(entry['root_relative'])
 if rel.is_absolute() or '..' in rel.parts or len(rel.parts)!=3 or rel.parts[:2]!=('urace','products'):raise ValueError('Invalid isolated product root')
 cfg=entry['configuration'];prefix=rel.as_posix()+'/'
 if Path(entry.get('state_path','')).resolve()!=Path(cfg.get('state_path','')).resolve() or not Path(entry.get('state_path','')).resolve().is_relative_to((root/rel).resolve()):raise ValueError('Isolated product state path required')
 if not isinstance(cfg,dict) or cfg.get('product')!=entry['name'] or any(not isinstance(p,str) or not p.startswith(prefix) or '..' in Path(p).parts for p in cfg.get('product_files',[])):raise ValueError('Isolated product configuration required')
 if cfg.get('runtime_workflow',{}).get('enabled') or cfg.get('execution_workflow')!='core':raise ValueError('A new product cannot take ownership of runtime or trial workflows')
 allowed=cfg.get('executor',{}).get('allowed_files_by_scope',{})
 if allowed.get('runtime') or any(not isinstance(p,str) or not p.startswith(prefix) or '..' in Path(p).parts for values in allowed.values() for p in values):raise ValueError('New product mutation scope must stay inside its own root')
 return True

def create(cli,description,name=None,activate=False):
 if not isinstance(description,str) or not description.strip() or len(description.encode())>65536:raise ValueError('A complete bounded product description is required')
 base=json.loads(cli.CONFIG_PATH.read_text());name=name or 'New product '+uuid.uuid4().hex[:8]
 if not isinstance(name,str) or not 1<=len(name.strip())<=100 or any(ord(c)<32 for c in name):raise ValueError('Bounded product name required')
 with cli.state_lock(cli.CONFIG_PATH):
  base=json.loads(cli.CONFIG_PATH.read_text());registry=base.setdefault('product_registry',[])
  if name.startswith('New product '):
   prior=next((e for e in registry if e.get('kind')=='bootstrapped' and e.get('intent_purpose')==description),None)
   if prior:return {'schema':SCHEMA,'status':'ALREADY_BOOTSTRAPPED','product_id':prior['id'],'name':prior['name'],'native_calls':0,'working_implementation_verified':False,'stage':prior.get('bootstrap_status')}
  if any(e.get('name')==name for e in registry):raise ValueError('Product name already registered; explicit existing-product targeting required')
  identity=uuid.uuid4().hex;rel=Path('urace/products')/identity;folder=cli.ROOT/rel
  parent=cli.ROOT/'urace/products'
  if parent.is_symlink() or parent.exists() and not parent.resolve().is_relative_to(cli.SYSTEM_ROOT.resolve()):raise ValueError('Product root path escape')
  folder.mkdir(parents=True,exist_ok=False)
  purpose=folder/'INTENT.md';product=folder/'PRODUCT.md';draft=folder/'ACCEPTANCE_DRAFT.md'
  purpose.write_text(description);product.write_text('# '+name+'\n\nStatus: draft product definition; implementation not yet validated.\n\nThe complete original owner description is preserved in INTENT.md. Derive explicit testable requirements and independently seal acceptance before evaluating implementation.\n');draft.write_text('# Acceptance design pending\n\nDerive testable criteria from INTENT.md, resolve ambiguities and independently seal acceptance before implementation is evaluated. No working product or passing tests are claimed.\n')
  cfg=copy.deepcopy(base);cfg.pop('active_product',None);cfg.pop('product_registry',None);cfg['product']=name;cfg['product_files']=[str(rel/'PRODUCT.md'),str(rel/'INTENT.md')];cfg['state_path']=str(folder/'state/state.json');cfg['intent']={'purpose':description};cfg['authority']={'delegated':['assessment','objectives','priority','plans','measurement','validation','local implementation changes'],'reserved':['change retained purpose','publish externally','spend money','credentials or private profiles','change URACE runtime or other products']};cfg['constraints']=['Retain the exact original owner intent','No working implementation or functional improvement claim without independent acceptance'];cfg['self_evolution_policy']={'mode':'DISABLED'};cfg['execution_workflow']='core';cfg['runtime_workflow']={'enabled':False};cfg['specification_workflow']={'enabled':False};cfg['auto_goals']={'enabled':True,'replenish_backlog':True};cfg['executor']['allowed_files_by_scope']={'implementation':[str(rel/'PRODUCT.md'),str(rel/'ACCEPTANCE_DRAFT.md')],'runtime':[]};cfg['external_metrics']={'enabled':False};cfg['analytics_export']={'enabled':False};cfg['community_inbox']={'enabled':False};cfg['product_bootstrap']={'stage':'NEEDS_ACCEPTANCE_DESIGN','intent_sha256':hashlib.sha256(description.encode()).hexdigest(),'original_intent_path':str(rel/'INTENT.md'),'working_implementation_verified':False,'no_existing_product_required':True}
  entry={'id':'prod-'+identity,'name':name,'kind':'bootstrapped','root_relative':rel.as_posix(),'state_path':cfg['state_path'],'product_files':cfg['product_files'],'intent_purpose':description,'configuration':cfg,'registered_at':cli.now(),'last_active_at':None,'status':'ACTIVE','improvement_enabled':True,'bootstrap_status':'NEEDS_ACCEPTANCE_DESIGN'};validate_entry(entry,cli.ROOT)
  state=cli.initial_state(cfg);state['lifecycle_state']='ONBOARDING';state.setdefault('bootstrap_requests',[]).append({'schema':SCHEMA,'description':description,'sha256':cfg['product_bootstrap']['intent_sha256'],'authority':'Explicit owner creation request; no deployment, purchases, credential changes or existing-product edits authorized'});state.setdefault('objectives',[]).append({'id':'define-'+identity[:12],'title':'Derive and independently review acceptance and implementation plan for '+name,'status':'planned','scope':'implementation','target':'product','priority':80,'expected_benefit':'Convert owner intent into testable requirements without fabricating a working product','bottleneck_id':'acceptance-not-yet-defined','success_measure':'Owner intent preserved and independent acceptance contract sealed before evaluated implementation','necessity_evidence':description,'dependencies':[]})
  cli.atomic_write_json(Path(cfg['state_path']),state);registry.append(entry);cli.atomic_write_json(cli.CONFIG_PATH,base)
 if activate:
  with cli.state_lock(cli.CONFIG_PATH):
   selected=json.loads(cli.CONFIG_PATH.read_text());selected['active_product']=name;cli.atomic_write_json(cli.CONFIG_PATH,selected)
 # The explicit creation request authorizes draft onboarding through the real existing operator path.
 previous=os.environ.get('URACE_ACTIVE_PRODUCT');os.environ['URACE_ACTIVE_PRODUCT']=name
 try:
  with contextlib.redirect_stdout(io.StringIO()):code=cli.main(['onboard','confirm','--note','Explicit owner product-creation request; local draft lifecycle only, implementation acceptance still required','--json'])
 finally:
  if previous is None:os.environ.pop('URACE_ACTIVE_PRODUCT',None)
  else:os.environ['URACE_ACTIVE_PRODUCT']=previous
 return {'schema':SCHEMA,'status':'BOOTSTRAPPED','onboarding_confirmed':code==0,'product_id':entry['id'],'name':name,'root':str(folder),'intent_sha256':cfg['product_bootstrap']['intent_sha256'],'improvement_enabled':True,'stage':'NEEDS_ACCEPTANCE_DESIGN','working_implementation_verified':False,'native_calls':0,'previous_active_product_preserved':not activate,'active_product_selected':activate,'next_actions':['product switch '+name,'auto --cycles 1 (after selecting this product; shared admission and acceptance apply)','Resolve and independently seal acceptance, then run normal authorized improvement cycles'],'limitations':'Bootstrap creates a registered draft and lifecycle, not an already working arbitrary application. Ambiguous intent and missing acceptance must be resolved before implementation success can be claimed.'}


def apply_interpreted(cli,interpretation):
 """Journal independent local intentions. Retry never repeats a completed section."""
 if interpretation['status']!='INTERPRETED':return {**interpretation,'actions_taken':[]}
 base=cli.load_config();root=cli.state_path(base).parent/'freeform-intents';root.mkdir(parents=True,exist_ok=True);path=root/(interpretation['source_sha256']+'.json')
 with cli.state_lock(path):
  record=json.loads(path.read_text()) if path.exists() else {'schema':SCHEMA,'source_sha256':interpretation['source_sha256'],'raw_text':interpretation['raw_text'],'sections':[],'status':'PENDING'}
  cli.atomic_write_json(path,record)
  for index,intent in enumerate(interpretation['intents']):
   if any(row['index']==index and row['status']=='COMPLETED' for row in record['sections']):continue
   try:
    if intent['kind']=='new_product':result=create(cli,intent['text'],activate=len(interpretation['intents'])==1)
    else:
     cfg=json.loads(cli.CONFIG_PATH.read_text());entry=next((e for e in cfg.get('product_registry',[]) if e.get('name')==intent['target'] and e.get('status','ACTIVE')=='ACTIVE'),None)
     if entry is None and intent['target']!=cfg.get('product'):raise ValueError('Target product no longer available')
     if entry:
      cfg={**cfg,**entry.get('configuration',{}),'product_registry':cfg.get('product_registry',[]),'active_product':entry['name'],'product':entry['name']}
     payload={'title':intent['text'],'success_measure':'Resolve the owner request into independently testable acceptance before claiming implementation success','reason':intent['text'],'target':'product','priority':70,'expected_value':.5,'estimated_cost':.5,'risk':.5,'urgency':.5,'dependencies':[],'source_text':interpretation['raw_text'],'semantic_section':intent['text'],'target_product_name':intent['target'],'intent_sha256':interpretation['source_sha256'],'acceptance_needs_design':True}
     entry=cli.queue_input(cfg,'goal',payload);result={'status':'QUEUED_EXISTING_PRODUCT_CHANGE','product':intent['target'],'input_id':entry['id'],'native_calls':0,'implementation_success_claimed':False}
    record['sections'].append({'index':index,'kind':intent['kind'],'target':intent['target'],'status':'COMPLETED','result':result});record['status']='PENDING';cli.atomic_write_json(path,record)
   except (ValueError,OSError) as error:
    record['status']='PARTIAL_OR_BLOCKED';record['blocked_index']=index;record['reason']=str(error);cli.atomic_write_json(path,record);return record
  record['status']='BOOTSTRAPPED_OR_QUEUED';record['native_calls']=0;cli.atomic_write_json(path,record);return record
