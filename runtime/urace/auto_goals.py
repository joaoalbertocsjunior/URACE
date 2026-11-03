"""Derive bounded objectives from declared user-project requirements.

This proposes/selects objectives; existing authority and validation still govern execution.
Project content is data, never a grant of authority. No filesystem/network discovery.
"""
from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from typing import Any

ACTIVE={'planned','active','awaiting_validation','awaiting_outcome','blocked','deferred','deferred_budget','awaiting_operator_decision'}

def select(config:dict[str,Any],state:dict[str,Any])->dict[str,Any]|None:
    settings=config.get('auto_goals',{})
    if settings.get('enabled',True) is not True:
        for goal in state.get('objectives',[]):
            if goal.get('source')=='auto_goals' and goal.get('status') in {'planned','policy_blocked'}:goal.update(status='deferred',auto_defer_reason='auto-goals disabled')
        state['auto_goal_status']={'enabled':False,'reason':'disabled by configuration'};return None
    authority=state.get('authority',config.get('authority',{}))
    if 'objectives' not in authority.get('delegated',[]):
        state['auto_goal_status']={'enabled':True,'reason':'objective selection not delegated'};return None
    objectives=state.setdefault('objectives',[])
    operator=next((o for o in objectives if o.get('source')!='auto_goals' and o.get('status') in ACTIVE),None)
    if operator:
        for automatic in objectives:
            if automatic.get('source')=='auto_goals' and automatic.get('status')=='planned':automatic.update(status='deferred',auto_defer_reason='explicit project objective')
        state['current_objective']=operator.get('id')
        state['auto_goal_status']={'enabled':True,'reason':'explicit/existing objective takes precedence','objective':operator.get('id')};return operator
    project=state.get('project') or config.get('project')
    if not isinstance(project,dict) or not isinstance(project.get('intent'),str) or not project['intent'].strip():
        state['auto_goal_status']={'enabled':True,'reason':'no declared user-project intent; never infer URACE as the target'};return None
    requirements=project.get('requirements',[])
    if not isinstance(requirements,list):raise ValueError('project.requirements must be a list')
    project_id=project.get('id',project.get('name')) or hashlib.sha256(project['intent'].encode()).hexdigest()[:20]
    by_requirement={r.get('id'):r for r in requirements if isinstance(r,dict)}
    for old in objectives:
        if old.get('source')!='auto_goals' or old.get('status') not in ACTIVE:continue
        requirement=by_requirement.get(old.get('project_requirement'))
        if old.get('project_id')!=project_id or requirement is None or requirement.get('status','pending') not in {'pending','failed','in_progress'}:
            old.update(status='superseded',superseded_reason='Declared project or requirement changed; history retained')
    completed_project_goals=[]
    for goal in objectives:
        if goal.get('status')!='completed' or goal.get('project_id')!=project_id:continue
        previous=goal.get('project_source_sha256')
        if previous:
            requirement=by_requirement.get(goal.get('project_requirement'))
            if requirement is None:continue
            basis={'project':project_id,'intent':project['intent'],'requirement':requirement}
            current=hashlib.sha256(json.dumps(basis,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            if previous!=current:continue
        completed_project_goals.append(goal)
    completed_requirements={r.get('id') for r in requirements if isinstance(r,dict) and r.get('status')=='completed'} | {g.get('project_requirement') for g in completed_project_goals}
    candidates=[]
    replenishment_allowed = settings.get('replenish_backlog', True) is True
    previous_automatic_work = any(o.get('source') == 'auto_goals' for o in objectives)
    for index,requirement in enumerate(requirements[:1000]):
        if not isinstance(requirement,dict) or requirement.get('status','pending') not in {'pending','failed','in_progress'}:continue
        if not all(isinstance(requirement.get(k),str) and requirement[k].strip() for k in ('id','title','success_measure')):continue
        dependencies=requirement.get('dependencies',[])
        completed=completed_requirements
        if not isinstance(dependencies,list) or any(d not in completed for d in dependencies):continue
        basis={'project':project_id,'intent':project['intent'],'requirement':requirement}
        digest=hashlib.sha256(json.dumps(basis,sort_keys=True,ensure_ascii=False).encode()).hexdigest();identifier='auto-goal-'+digest[:20]
        for old in objectives:
            if old.get('source')=='auto_goals' and old.get('status') in ACTIVE and old.get('project_id')==project_id and old.get('project_requirement')==requirement['id'] and old.get('id')!=identifier:old.update(status='superseded',superseded_reason='Project acceptance criteria changed')
        existing=next((o for o in objectives if o.get('id')==identifier),None)
        if existing and existing.get('status')=='superseded':
            existing.setdefault('reactivations',[]).append({'at':datetime.now(timezone.utc).isoformat(),'previous_superseded_reason':existing.pop('superseded_reason',None),'reason':'Exact declared project requirement restored'})
            existing['status']='planned'
        if existing and existing.get('status') in {'completed','cancelled','rejected'}:continue
        if existing:candidates.append(existing);continue
        if previous_automatic_work and not replenishment_allowed:
            continue
        priority=requirement.get('priority',50)
        if not isinstance(priority,(int,float)) or isinstance(priority,bool):priority=50
        stamp=datetime.now(timezone.utc).isoformat()
        goal={'id':identifier,'title':requirement['title'],'success_measure':requirement['success_measure'],'reason':'Derived from declared project intent: '+project['intent'],'priority':max(0,min(100,priority)),'status':'planned','created_at':stamp,'updated_at':stamp,'scope':requirement.get('scope','documentation'),'target':requirement.get('target','product'),'source':'auto_goals','project_id':project_id,'project_source':project.get('source','config.project'),'project_source_sha256':digest,'project_requirement':requirement['id'],'metadata':dict(requirement.get('metadata',{})),'dependencies':[o['id'] for o in completed_project_goals if o.get('project_requirement') in dependencies],'pinned':False,'expected_value':0.5,'estimated_cost':0.3,'risk':0.2,'urgency':0.5}
        # Declare intent/requirements, but never manufacture Authority or proof of completion.
        if requirement.get('necessity_evidence'):goal['necessity_evidence']=requirement['necessity_evidence'];goal['lower_impact_route_sufficient']=requirement.get('lower_impact_route_sufficient',True)
        candidates.append(goal)
    if not candidates:
        state['auto_goal_status']={'enabled':True,'reason':('backlog replenishment disabled' if previous_automatic_work and not replenishment_allowed else 'no unfinished declared project requirement')};return None
    scores={}
    if config.get('value_discovery',{}).get('ranking') is True:
        from .value_discovery import ranking_scores
        try:scores=ranking_scores(config,state)
        except (OSError,ValueError,KeyError):state['value_ranking_status']='Evidence unavailable; declared priority preserved'
    candidates.sort(key=lambda g:(-g['priority'],-scores.get(g['project_requirement'],0),g['project_requirement']))
    chosen=candidates[0]
    if chosen.get('auto_defer_reason') in {'explicit project objective','auto-goals disabled'}:chosen['status']='planned';chosen.pop('auto_defer_reason',None)
    if not any(o.get('id')==chosen['id'] for o in objectives):
        objectives.append(chosen);state.setdefault('auto_goal_records',[]).append({'at':chosen['created_at'],'objective':chosen['id'],'project_id':chosen['project_id'],'source':chosen['project_source'],'source_sha256':chosen['project_source_sha256']})
    current=next((o for o in objectives if o.get('id')==state.get('current_objective')),None)
    if current is None or current.get('source')=='auto_goals':state['current_objective']=chosen['id']
    state['auto_goal_status']={'enabled':True,'reason':'selected unfinished user-project requirement','objective':chosen['id'],'project_id':chosen['project_id']}
    # Advisory objective conflict detection: flag similar success_measure text among active objectives
    _chosen_sm = chosen.get('success_measure', '').lower()
    if _chosen_sm:
        for _other in objectives:
            if _other.get('id') == chosen['id'] or _other.get('status') not in ACTIVE:
                continue
            _other_sm = _other.get('success_measure', '').lower()
            if not _other_sm:
                continue
            # Heuristic: >50% word overlap suggests conflicting measures
            _chosen_words = set(_chosen_sm.split())
            _other_words = set(_other_sm.split())
            _overlap = _chosen_words & _other_words
            if len(_chosen_words) > 0 and len(_overlap) / len(_chosen_words) > 0.5:
                _gap_id = 'objective-conflict-' + hashlib.sha256((chosen['id'] + _other['id']).encode()).hexdigest()[:16]
                _existing_gap = next((g for g in state.get('integrity_gaps', []) if g.get('id') == _gap_id), None)
                if not _existing_gap:
                    state.setdefault('integrity_gaps', []).append({
                        'id': _gap_id,
                        'kind': 'objective-conflict',
                        'severity': 'INFO',
                        'active': True,
                        'at': datetime.now(timezone.utc).isoformat(),
                        'detail': f"Advisory: objectives '{chosen['id']}' and '{_other['id']}' have overlapping success measures — verify they are not contradictory.",
                        'objective_a': chosen['id'],
                        'objective_b': _other['id'],
                    })
                break
    return chosen
