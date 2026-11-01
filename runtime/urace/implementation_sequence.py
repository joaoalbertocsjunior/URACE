"""Explainable dependency planning and local-first executor routing; no native model calls."""
import copy,hashlib,json,math,time

LOCAL_ACTIONS={'plan_sequence','draft_milestones','rank_peers','status','assessment_index','reconcile_receipts','refresh_metadata'}
DONE={'completed','achieved','superseded','cancelled'}

def local_only(task):return task.get('execution_kind')=='local_orchestration' or task.get('controller_action') in LOCAL_ACTIONS

def finite(value):return type(value) in (int,float) and math.isfinite(value)

def plan(tasks,*,scores=None,eligible=None):
 if not isinstance(tasks,list) or len(tasks)>2000:raise ValueError('Bounded implementation task list required')
 by_id={}
 for task in tasks:
  key=task.get('id')
  if not isinstance(key,str) or not key or key in by_id:raise ValueError('Unique task identity required')
  deps=task.get('dependencies',[])
  if not isinstance(deps,list) or any(not isinstance(d,str) for d in deps):raise ValueError('Task dependencies must be identifiers')
  by_id[key]=task
 positions={key:i for i,key in enumerate(by_id)}
 active={k:v for k,v in by_id.items() if str(v.get('status','planned')).lower() not in DONE};pending=set(active);resolved={k for k,v in by_id.items() if str(v.get('status','')).lower() in ('completed','achieved','superseded')};rows=[];groups=[]
 blocked={k:['Unknown dependency '+d for d in v.get('dependencies',[]) if d not in by_id] for k,v in active.items()};scores=scores or {}
 def ordering(k):
  task=active[k];score=scores.get(k,task.get('priority',50));score=score if finite(score) else 0
  # Keep declared/ranked owner priorities primary. Prefer cheap uncertainty-reducing checks only at equal priority.
  estimate=task.get('estimate') or {};cost=estimate.get('max_hours');known=finite(cost) and cost>0
  return (-score,not bool(task.get('uncertainty_reduction')),not local_only(task),not known,cost if known else float('inf'),positions[k])
 while pending:
  ready=[k for k in pending if not blocked[k] and all(d in resolved for d in active[k].get('dependencies',[])) and str(active[k].get('status','planned')).lower() not in ('blocked','policy_blocked','disabled','awaiting_operator_decision','deferred')]
  if not ready:break
  ready.sort(key=ordering);groups.append(ready)
  for key in ready:
   task=active[key];actual_ready=eligible.get(key,False) if eligible is not None else not task.get('dependencies');route='LOCAL_CONTROLLER' if local_only(task) else 'EXECUTOR_CANDIDATE';estimate=task.get('estimate') or {}
   reasons=['Dependency predecessors precede this task','Owner priority/score retained before resource tie-breaks']
   if local_only(task):reasons.append('Orchestration belongs to a deterministic local handler; no executor token spend')
   if task.get('uncertainty_reduction'):reasons.append('At equal priority, resolves uncertainty before more expensive implementation')
   if not finite(estimate.get('max_hours')):reasons.append('Cost unknown; not treated as free')
   rows.append({'id':key,'rank':len(rows)+1,'phase':len(groups),'status':'READY' if actual_ready else 'PLANNED_AFTER_PREDECESSORS','route':route,'dependencies':task.get('dependencies',[]),'bottleneck':task.get('bottleneck_id'),'expected_benefit':task.get('expected_benefit'),'expected_benefit_score':task.get('expected_benefit_score'),'benefit_score_verified':task.get('benefit_score_verified') is True,'action_recommendation':task.get('action_recommendation',task.get('title')),'why':reasons,'estimated_cost':estimate or None,'authority':'Recheck existing authority and acceptance before dispatch'})
   pending.remove(key);resolved.add(key)
 for key in sorted(pending):
  deps=active[key].get('dependencies',[]);reasons=blocked[key] or ['Blocked/cyclic or unresolved predecessor chain; explicit owner/action review required']
  rows.append({'id':key,'rank':None,'phase':None,'status':'BLOCKED','route':'LOCAL_CONTROLLER' if local_only(active[key]) else 'EXECUTOR_CANDIDATE','dependencies':deps,'why':reasons,'action_recommendation':'Resolve the dependency or authority blocker; do not dispatch speculative work'})
 source=hashlib.sha256(json.dumps(tasks,sort_keys=True,default=str).encode()).hexdigest()
 return {'schema':'implementation-sequence-v1','source_sha256':source,'tasks':rows,'dependency_phases':groups,'dispatch_order':[r['id'] for r in rows if r['rank'] is not None and (eligible is None or eligible.get(r['id']))],'native_model_calls':0,'absolute_optimum_proven':False,'uncertainty':'Scores and cost estimates are provisional. Independent outcomes and calibrated owner utility are needed to compare alternative sequences. Dependency phases do not promise safe parallel writes or available executor capacity.'}

def execute_local(config,state,objective):
 """Only explicit controller actions; never interpret a task title as authority to run code."""
 action=objective.get('controller_action');started=time.monotonic()
 if action=='plan_sequence':
  from .inspection import objective_score,goal_is_schedulable
  output=plan(copy.deepcopy(state.get('objectives',[])),scores={t['id']:objective_score(t) for t in state.get('objectives',[])},eligible={t['id']:goal_is_schedulable(state,t) for t in state.get('objectives',[])})
 elif action=='draft_milestones':
  from .milestone_suggestions import refresh
  output=refresh(config,state)
 elif action=='rank_peers':
  from .peer_exchange import Exchange,directory
  from .peer_selection import rank
  output=rank(Exchange(directory(config)))
 elif action=='reconcile_receipts':
  from .inspection import resource_accounting
  output=resource_accounting(config,state)
 elif action=='assessment_index':
  from ._common import SYSTEM_ROOT
  import sys
  sys.path.insert(0,str(SYSTEM_ROOT/'trial'))
  from assessment_packet import packet
  output=packet(SYSTEM_ROOT/'trial')
 elif action=='status':output={'objectives':len(state.get('objectives',[])),'lifecycle_state':state.get('lifecycle_state')}
 else:raise RuntimeError('Local-only task requires a registered local handler; no executor fallback')
 result={'status':'COMPLETED','execution_route':'LOCAL_CONTROLLER','native_calls':0,'tokens':0,'controller_seconds':time.monotonic()-started,'implementation_change':False,'product_improvement_claim':False,'output':output}
 objective.update(status='completed',outcome_status='LOCAL_CONTROLLER_ACTION_COMPLETE',local_execution=result);return result
