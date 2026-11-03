"""Read-only runtime status presentation. Missing measurements are never zero scores."""
from pathlib import Path
import json
import runtime_cycle as cycle,runtime_quality_gate as gate,runtime_regression_guard as guard,runtime_trial as trial

def data(base,config=None):
 base=Path(base);config=config or {};state=cycle.status(base);events=trial.deployment_log(base);deployed=[e for e in events if e.get('event')=='DEPLOYED'];score=gate.read_latest_score(base);g=guard.check(base,config)
 return {'schema':'runtime-dashboard-v2','current_score':score,'accepted_score':g.get('accepted_score'),'guard_status':g['status'],'guard_reason':g['reason'],'stage':state.get('stage','NOT_STARTED'),'reason':state.get('reason'),'completed_cycles':state.get('completed_cycles',0),'next_due_unix':state.get('next_due_unix'),'deployments_total':len(deployed),'regressions_detected':sum(bool(e.get('regression') or e.get('regression_detected')) for e in deployed),'deployments':deployed,'minimum_delta':gate.gate_config(config)['minimum_delta'],'score_scope':'Bounded runtime contracts; not universal worth or user benefit','policy':{'owner_purpose_frozen':True,'self_modification_of_guards':False,'absolute_optimum_established':False,'scope':'Declared helper functions only','uncertainty':'Finite tests and provisional owner thresholds cannot prove perfect permission balance, all behavior, field safety or market fit'}}

def render(base,config=None):
 d=data(base,config);score='unavailable' if d['current_score'] is None else f"{d['current_score']:.1f} / 100"
 lines=['Runtime Improvement Dashboard','═'*42,f"Stage:           {d['stage']}",f"Reason:          {d['reason']}",f"Current score:   {score} (gate: +{d['minimum_delta']:.1f} required)",f"Guard:           {d['guard_status']}",f"Guard reason:    {d['guard_reason']}",f"Completed cycles: {d['completed_cycles']}",f"Deployments:     {d['deployments_total']} accepted",'Scope: bounded runtime behavior; no user-value or perfect-balance claim']
 if not d['deployments']:lines.append('No runtime deployment accepted yet; rejected/no-change cycles are still recorded.')
 for event in d['deployments'][-10:]:lines.append(f"{event.get('at','')} DEPLOYED {event.get('snapshot_id','')} delta={event.get('delta')}")
 return '\n'.join(lines)
