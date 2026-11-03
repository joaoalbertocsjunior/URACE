"""Read-only milestone phase/status projection; existing achievement gates stay authoritative."""
from __future__ import annotations
import math

SCHEMA='milestone-phase-feedback-v1'

def number(value):return type(value) in (int,float) and math.isfinite(value)

def assess(config,state,milestone):
    canonical=milestone.get('status','UNKNOWN')
    raw_capabilities=state.get('capability_states',[])
    capabilities={v.get('capability_id'):v for v in (raw_capabilities if isinstance(raw_capabilities,list) else []) if isinstance(v,dict)}
    raw_assessments=state.get('sweet_spot_assessments')
    assessment=(raw_assessments[-1] if isinstance(raw_assessments,list) and raw_assessments else {})
    if not isinstance(assessment,dict):assessment={}
    envelope=config.get('capability_envelope',{}) if isinstance(config,dict) else {}
    capability_gates=[{'id':key,'status':capabilities.get(key,{}).get('status','UNKNOWN'),'satisfied':capabilities.get(key,{}).get('status') in ('CAPABLE','OVER_ENGINEERED')} for key in milestone.get('capability_gates',[])]
    quality=[]
    quality_state=state.get('quality_state',{})
    if not isinstance(quality_state,dict):quality_state={}
    for gate in milestone.get('quality_gates',[]):
        scope=gate.get('scope','*');observed=quality_state.get(scope,{}).get('current_streak');minimum=gate.get('min_streak',0)
        quality.append({'scope':scope,'observed_streak':observed,'minimum_streak':minimum,'measurement_known':number(observed),'satisfied':number(minimum) and (minimum==0 or number(observed) and observed>=minimum)})
    constraints=[]
    for name,metric,direction in [('complexity_ceiling','product_surface_measure','lower'),('value_density_floor','value_density','higher')]:
        bound=milestone.get(name)
        if bound is None:bound=envelope.get(name)
        if bound is None:continue
        observed=assessment.get(metric);known=number(observed) and number(bound)
        constraints.append({'name':name,'observed':observed,'bound':bound,'measurement_known':known,'satisfied':known and (observed<=bound if direction=='lower' else observed>=bound)})
    cap_ok=all(g['satisfied'] for g in capability_gates);quality_ok=all(g['satisfied'] for g in quality);limits_ok=all(g['satisfied'] for g in constraints)
    bottlenecks=[{'kind':'capability_gate','reference':g['id'],'status':g['status'],'action_recommendation':'Complete or independently verify capability '+g['id']} for g in capability_gates if not g['satisfied']]
    bottlenecks += [{'kind':'quality_gate','reference':g['scope'],'status':'AWAITING_EVIDENCE','action_recommendation':'Collect the required quality streak for '+g['scope']+' without weakening the gate'} for g in quality if not g['satisfied']]
    bottlenecks += [{'kind':'configured_constraint','reference':g['name'],'status':'BLOCKED' if g['measurement_known'] else 'AWAITING_EVIDENCE','action_recommendation':'Reassess '+g['name']+' against current evidence; retain the configured boundary'} for g in constraints if not g['satisfied']]
    raw_blockers=state.get('blockers',[])
    linked_blockers=[v for v in (raw_blockers if isinstance(raw_blockers,list) else []) if milestone.get('id') and v.get('milestone_id')==milestone.get('id') and not v.get('resolved_at')]
    bottlenecks += [{'kind':'blocker','reference':v.get('id'),'status':'BLOCKED','action_recommendation':v.get('reason')} for v in linked_blockers]
    decision_refs=milestone.get('decision_refs',[])
    if not isinstance(decision_refs,list):decision_refs=[]
    decisions=[r for r in state.get('decision_records',[]) if r.get('id') in decision_refs or milestone.get('id') and r.get('milestone_ref')==milestone.get('id')]
    from .decision_feedback import view,indexes
    indexed=indexes(state);decision_feedback=[view(config,state,r,indexed) for r in decisions]
    approval='BLOCKED' if any(r['authority_outcome']=='DENIED' for r in decision_feedback) else 'AWAITING_APPROVAL' if any(r['authority_outcome'] in ('REQUIRES_AUTHORITATIVE_DECISION','UNRESOLVED') for r in decision_feedback) else 'APPROVED' if decision_feedback and all(r['authority_outcome']=='AUTONOMOUSLY_AUTHORIZED' for r in decision_feedback) else 'UNKNOWN'
    if canonical=='SUPERSEDED':phase='SUPERSEDED';operational='SUPERSEDED'
    elif canonical=='PENDING':phase='PLANNING';operational='PENDING'
    elif canonical=='ACHIEVED':
        phase='COMPLETE' if cap_ok and quality_ok and limits_ok else 'REASSESSMENT'
        operational='ACHIEVED' if phase=='COMPLETE' else 'NEEDS_REASSESSMENT'
    elif canonical=='ACTIVE':
        phase='IMPLEMENTATION' if not cap_ok else 'VALIDATION'
        operational='READY_FOR_GATE_EVALUATION' if cap_ok and quality_ok and limits_ok else 'ACTIVE'
    else:phase='UNKNOWN';operational='UNKNOWN'
    if canonical not in ('SUPERSEDED','ACHIEVED'):
        if linked_blockers or approval=='BLOCKED' or any(g['measurement_known'] and not g['satisfied'] for g in constraints):operational='BLOCKED'
        elif approval=='AWAITING_APPROVAL':operational='AWAITING_APPROVAL'
    phases=[{'id':'planning','status':'PENDING' if canonical=='PENDING' else 'COMPLETE','required_by_existing_contract':True},
            {'id':'implementation','status':'COMPLETE' if cap_ok else 'PENDING' if canonical=='PENDING' else 'IN_PROGRESS','required_by_existing_contract':True},
            {'id':'validation','status':'COMPLETE' if cap_ok and quality_ok and limits_ok else 'PENDING' if not cap_ok else 'IN_PROGRESS','required_by_existing_contract':True},
            {'id':'outcome_observation','status':'UNMEASURED','required_by_existing_contract':False,'scope':'Informational axis; achievement of capability gates is not observed user benefit'}]
    if canonical=='SUPERSEDED':
        for item in phases:item['status']='SUPERSEDED'
    return {'schema':SCHEMA,'id':milestone.get('id'),'name':milestone.get('name'),'canonical_status':canonical,'phase':phase,'operational_status':operational,'approval_status':approval,'phases':phases,
            'capability_gates':capability_gates,'quality_gates':quality,'constraints':constraints,'bottlenecks':bottlenecks,
            'decision_refs':[r['decision_id'] for r in decision_feedback],'additional_model_calls':0,'mutates_achievement_contract':False,
            'achievement_scope':'Existing configured capability/quality/complexity/density gates only. Not full live-feature, comparative, real-user or market-fit proof. Historical achievement is retained if current evidence regresses.'}
