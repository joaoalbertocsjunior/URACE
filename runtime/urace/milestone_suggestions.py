"""Deterministic milestone drafts; never activates milestones or supplies acceptance."""
import hashlib,json

def settings(config):
 raw=config.get('auto_milestones',{})
 if not isinstance(raw,dict) or set(raw)-{'enabled'} or 'enabled' in raw and type(raw['enabled']) is not bool:raise ValueError('Invalid auto-milestones settings')
 return {'enabled':raw.get('enabled',True)}

def suggestions(config,state):
 result={'schema':'local-milestone-suggestions-v1','enabled':settings(config)['enabled'],'additional_model_calls':0,'suggestions':[],
         'activation':'Drafts only. Review acceptance and use existing authority before configuring or activating a milestone.'}
 if not result['enabled']:return result
 envelope=config.get('capability_envelope',{});configured=[m for m in envelope.get('milestones',[]) if isinstance(m,dict) and m.get('status')!='SUPERSEDED']
 covered={g for m in configured for g in m.get('capability_gates',[])}
 observed={v.get('capability_id'):v.get('status') for v in state.get('capability_states',[]) if isinstance(v,dict)}
 drafts={}
 def add(kind,ref,name,criteria,bottleneck,gates):
  basis={'kind':kind,'reference':ref,'criteria':criteria,'gates':gates}
  key='mst-draft-'+hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]
  drafts[key]={'id':key,'name':name,'status':'DRAFT','phase':'PLANNING','approval_status':'NOT_EVALUATED','source_refs':[kind+':'+ref],
    'bottleneck':bottleneck,'action_recommendation':'Review independent acceptance and authority before adopting this draft',
    'declared_success':criteria,'proposed_capability_gates':gates,'acceptance_status':'REQUIRES_REVIEW','automatically_activated':False,
    'expected_benefit':'Make unfinished declared work and its validation target visible','expected_benefit_score':None}
 for cap in envelope.get('capabilities',[]):
  if not isinstance(cap,dict) or not isinstance(cap.get('id'),str) or not cap['id']:continue
  ref=cap['id'];status=observed.get(ref,'UNKNOWN')
  if ref in covered or status in ('CAPABLE','OVER_ENGINEERED'):continue
  add('capability',ref,'Complete declared capability '+ref,None,{'reference':ref,'status':status,'kind':'capability_gap' if status in ('ABSENT','PARTIAL') else 'missing_capability_evidence'},[ref])
 represented={m.get('objective_ref') for m in configured}
 for goal in state.get('objectives',[]):
  if not isinstance(goal,dict) or str(goal.get('status','')).upper() in ('ACHIEVED','COMPLETED','SUPERSEDED','CANCELLED'):continue
  if not all(isinstance(goal.get(k),str) and goal[k].strip() for k in ('id','title','success_measure')) or goal['id'] in represented:continue
  ref=goal['id'];add('objective',ref,goal['title'],goal['success_measure'],{'reference':ref,'kind':'unverified_objective','status':'OUTCOME_NOT_VERIFIED'},[])
 result['suggestions']=[drafts[k] for k in sorted(drafts)]
 result['status']='DRAFTS_AVAILABLE' if drafts else 'NO_UNCOVERED_DECLARED_TARGETS'
 return result

def refresh(config,state):
 packet=suggestions(config,state)
 return {k:v for k,v in packet.items() if k!='suggestions'}|{'draft_count':len(packet['suggestions'])}
