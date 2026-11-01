"""Local, source-bound skill selection and requirement clarification. No model calls or host setup."""
import hashlib,json,re

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

BUILTINS=[
 {'id':'urace-receipt-review','version':'1','providers':['codex','claude'],'families':['receipts'],'terms':['receipt','accounting'],'expected_benefit':'Avoid duplicate usage accounting and false known-cost claims','instructions':'Trace each receipt identity to its producing attempt. Count failed attempts and retries. Deduplicate identical receipt identities; conflicting duplicates invalidate exact cost. Preserve unknown usage as unknown. Cached/reasoning subtotals are nested unless the native contract says otherwise. Keep product/provider scopes separate. Use public development checks; never change acceptance or quota guards.'},
 {'id':'urace-continuity-review','version':'1','providers':['codex','claude'],'families':['recovery','interruption'],'terms':['recovery','interruption'],'expected_benefit':'Find checkpoint, replay and rollback mistakes before delivery','instructions':'Identify the durable commit boundary and interrupted states. Preserve unrelated edits and immutable history. Check replay/idempotence, partial writes, cancellation and exact preimages. Use bounded retries and record failure. Never infer success from a transport acknowledgement. Exercise public checks without modifying them.'},
 {'id':'urace-requirement-trace','version':'1','providers':['codex','claude'],'families':['requirements_change'],'terms':['requirements change'],'expected_benefit':'Keep changed requirements and earlier constraints visible together','instructions':'Read the requirement index and source passages relevant to the change. Preserve retained requirements; distinguish superseded requirements from still-active constraints. Ask a precise clarification when meanings conflict. Map the planned change to the current public success measure and run development checks. An acknowledgement is not proof of correctness.'},
]

def settings(config):
 raw=config.get('executor_skills',{});allowed={'enabled','mode','max_selected','max_instruction_bytes','catalog'}
 if not isinstance(raw,dict) or set(raw)-allowed:raise ValueError('Invalid executor skill settings')
 cfg={'enabled':raw.get('enabled',True),'mode':raw.get('mode','auto'),'max_selected':raw.get('max_selected',2),'max_instruction_bytes':raw.get('max_instruction_bytes',4096),'catalog':raw.get('catalog',[])}
 if type(cfg['enabled']) is not bool or cfg['mode'] not in ('auto','off') or type(cfg['max_selected']) is not int or not 1<=cfg['max_selected']<=4 or type(cfg['max_instruction_bytes']) is not int or not 256<=cfg['max_instruction_bytes']<=16384:raise ValueError('Invalid bounded skill controls')
 if not isinstance(cfg['catalog'],list) or len(cfg['catalog'])>16:raise ValueError('Bounded owner-approved skill catalog required')
 seen={s['id'] for s in BUILTINS}
 for skill in cfg['catalog']:
  if not isinstance(skill,dict) or set(skill)!={'id','version','providers','families','terms','expected_benefit','instructions','sha256'}:raise ValueError('Instruction-only skill contract required; setup scripts are not permitted')
  if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}',skill['id']) or skill['id'] in seen:raise ValueError('Unique bounded skill identity required')
  seen.add(skill['id'])
  for k in ('version','expected_benefit','instructions'):
   if not isinstance(skill[k],str) or not skill[k] or len(skill[k].encode())>16384:raise ValueError('Bounded skill text required')
  if not isinstance(skill['providers'],list) or not skill['providers'] or set(skill['providers'])-{'codex','claude'}:raise ValueError('Explicit corresponding executor required')
  for k in ('families','terms'):
   if not isinstance(skill[k],list) or len(skill[k])>20 or any(not isinstance(v,str) or not v or len(v)>80 for v in skill[k]):raise ValueError('Bounded relevance declarations required')
  if hashlib.sha256(skill['instructions'].encode()).hexdigest()!=skill['sha256']:raise ValueError('Skill instruction pin differs')
 return cfg

def context_settings(config):
 raw=config.get('context_guard',{})
 if not isinstance(raw,dict) or set(raw)-{'enabled'} or type(raw.get('enabled',True)) is not bool:raise ValueError('Invalid context-guard controls')
 return {'enabled':raw.get('enabled',True)}

def contract(config):return {'schema':'executor-capabilities-v1','skills':settings(config),'builtin_sha256':digest(BUILTINS),'context_guard':context_settings(config),'scope':'Owner-approved instruction packets through existing scoped tools; no native plugin injection, network install, extra inference or authority expansion'}

def prepare(config,provider,task):
 cfg=settings(config);guard=context_settings(config);requirements=task.get('requirements',[])
 if not isinstance(requirements,list) or len(requirements)>1000:raise ValueError('Bounded requirement ledger required')
 passages={}
 for index,row in enumerate(requirements):
  if not isinstance(row,dict):raise ValueError('Structured requirement required')
  identifier=row.get('id','requirement-'+str(index+1))
  if not isinstance(identifier,str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}',identifier) or identifier in passages:raise ValueError('Unique requirement identifiers required')
  if len(json.dumps(row).encode())>32768:raise ValueError('Large requirement passage needs an explicit scoped partition; no silent truncation')
  passages[identifier]=row
 if len(json.dumps(passages).encode())>1048576:raise ValueError('Requirement ledger too large; explicit scoped partition required')
 family=task.get('family');intent=str(task.get('intent','')).lower();selected=[];skipped=[];remaining=cfg['max_instruction_bytes']
 for skill in [*BUILTINS,*cfg['catalog']]:
  reason=None
  if not cfg['enabled'] or cfg['mode']=='off':reason='DISABLED'
  elif provider not in skill['providers']:reason='EXECUTOR_MISMATCH'
  elif not (family in skill['families'] or any(term.lower() in intent for term in skill['terms'])):reason='NO_CONCRETE_TASK_MATCH'
  elif len(selected)>=cfg['max_selected'] or len(skill['instructions'].encode())>remaining:reason='CONTEXT_ALLOWANCE'
  if reason:skipped.append({'id':skill['id'],'reason':reason});continue
  item={**skill,'sha256':hashlib.sha256(skill['instructions'].encode()).hexdigest(),'status':'AVAILABLE_ON_DEMAND','setup':'instruction packet only; no host installation','benefit_verified':False};selected.append(item);remaining-=len(skill['instructions'].encode())
 from .context_relations import build
 graph=build(passages)
 return {'context_relations':graph,'schema':'job-capabilities-v1','contract_sha256':digest(contract(config)),'skills':selected,'skipped_skills':skipped,'requirements':passages if guard['enabled'] else {},'context_guard_enabled':guard['enabled'],'requirement_source_sha256':digest(requirements),'clarifications':task.get('clarifications',{}),'native_plugin_injection_verified':False,'model_calls':0}

def read(packet,path,start=1,end=None):
 if type(start) is not int or start<1 or end is not None and (type(end) is not int or end<start):raise ValueError('Invalid bounded index range')
 if path=='@attention':
  from .context_relations import attention
  data=attention(packet['context_relations']);rows=data.pop('ordered_nodes');stop=min(end if end is not None else start+7,start+49);return {**data,'ordered_nodes':rows[start-1:stop],'total':len(rows),'next_start':stop+1 if stop<len(rows) else None}
 if path.startswith('@related/'):
  from .context_relations import related
  return related(packet['context_relations'],path[len('@related/'):])
 if path=='@skills':return {'skills':[{k:s[k] for k in ('id','version','sha256','expected_benefit','status')} for s in packet['skills']],'authority':'Advisory instructions only; task authority and tools remain unchanged'}
 if path.startswith('@skill/'):
  key=path[len('@skill/'):];skill=next((s for s in packet['skills'] if s['id']==key),None)
  if skill is None:raise ValueError('Skill not selected/available for this executor and task')
  return skill
 if path=='@requirements':
  rows=list(packet['requirements'].items());stop=min(end if end is not None else start+49,start+49);return {'source_sha256':packet['requirement_source_sha256'],'total':len(rows),'entries':[{'id':k,'title':str(v.get('title',''))[:120],'success_measure':str(v.get('success_measure',''))[:160],'full_passage':'@requirement/'+k} for k,v in rows[start-1:stop]],'next_start':stop+1 if stop<len(rows) else None,'index_only':True,'comprehension_proven':False}
 if path.startswith('@requirement/'):
  key=path[len('@requirement/'):]
  if key not in packet['requirements']:raise ValueError('Unknown requirement; do not invent missing context')
  return {'id':key,'source_sha256':packet['requirement_source_sha256'],'passage':packet['requirements'][key],'owner_clarification':packet['clarifications'].get(key),'authority':'Frozen source; no change to independent acceptance'}
 raise ValueError('Unknown virtual context resource')

def clarify(packet,identifier,content):
 if not packet.get('context_guard_enabled'):raise ValueError('Context clarification disabled')
 if identifier not in packet['requirements']:raise ValueError('Unknown requirement identifier')
 try:question=json.loads(content)
 except ValueError:raise ValueError('Clarification content must be JSON')
 if not isinstance(question,dict) or set(question)-{'question','needs_owner'} or not isinstance(question.get('question'),str) or not 1<=len(question['question'].encode())<=1024 or type(question.get('needs_owner',False)) is not bool:raise ValueError('A bounded precise clarification question is required')
 answer=packet['clarifications'].get(identifier)
 return {'id':identifier,'question':question['question'],'question_sha256':digest(question),'status':'ANSWERED_FROM_OWNER_CONTEXT' if answer is not None else 'NEEDS_OWNER_CLARIFICATION' if question.get('needs_owner') else 'SOURCE_PASSAGE_RETURNED','passage':packet['requirements'][identifier],'answer':answer,'understanding_proven':False,'next_action':'Check the source and independent public contract; ask needs_owner=true if ambiguity remains'}

def feedback(packet,events):
 reads=[e.get('path') for e in events if e.get('tool')=='read_file' and not e.get('error')];questions=[e['clarification'] for e in events if e.get('clarification') and not e.get('error')];required={k for k,v in packet['requirements'].items() if v.get('requires_explicit_context_read') is True};read_ids={p[len('@requirement/'):] for p in reads if isinstance(p,str) and p.startswith('@requirement/')}
 unresolved=[q for q in questions if q['status']=='NEEDS_OWNER_CLARIFICATION'];missing=sorted(required-read_ids)
 return {'schema':'job-context-feedback-v1','status':'AWAITING_OWNER_CLARIFICATION' if unresolved else 'MISSING_REQUIRED_CONTEXT' if missing else 'PROTOCOL_SATISFIED','unresolved_questions':unresolved,'missing_required_context':missing,'requirement_source_sha256':packet['requirement_source_sha256'],'context_response_bytes':sum(e.get('response_bytes') or 0 for e in events if isinstance(e.get('path'),str) and e['path'].startswith('@')),'requirements_total':len(packet['requirements']),'explicit_requirement_reads':sorted(read_ids),'skill_instruction_reads':sorted(set(p[len('@skill/'):] for p in reads if isinstance(p,str) and p.startswith('@skill/'))),'understanding_proven':False,'meaning':'Provided source, retrieval and clarification receipts are distinct from semantic comprehension; independent acceptance still required'}
