"""Event-driven evidence follow-ups. Uncertainty is never an instruction to spin native calls."""
import hashlib,json

def plan(claims):
 rows=[]
 for index,claim in enumerate(claims):
  kind=claim.get('kind','bounded_behavior');evidence=claim.get('evidence_refs',[]);source=claim.get('source_sha256');identifier=claim.get('id','claim-'+str(index));status=claim.get('status','UNPROVEN')
  if status=='VERIFIED' and claim.get('independently_verified') is True and source and evidence:
   state='VERIFIED_WITHIN_DECLARED_SCOPE';why='Controller supplied independent source-bound evidence; claim remains bounded by that evidence';action='Revalidate if source, evaluator, execution conditions or owner requirements change';resume='SOURCE_OR_CONTRACT_CHANGED'
  elif kind in ('universal_optimality','universal_perfection','indefinite_reliability'):
   state='NOT_PROVABLE_AS_STATED';why='No finite test set proves an unbounded universal claim; optimality also needs a defined objective and calibrated weights';action='Replace with a bounded, falsifiable claim, explicit utility and reference population';resume='OWNER_BOUNDS_CLAIM'
  elif kind in ('statistical_estimate','comparative_gain'):
   state='WAITING_MATCHED_EVIDENCE';why='Compatible profile/family samples and complete resources are required; elapsed time is not qualification';action='Collect balanced independent accepted/failed outcomes using the frozen comparison protocol';resume='SAMPLE_AND_COVERAGE_THRESHOLDS_MET'
  elif kind in ('external_approval','external_availability'):
   state='WAITING_EXTERNAL_CONDITION';why='External decisions or capabilities are not controlled by local inference';action='Check authoritative metadata on schedule; avoid repeated speculative model requests';resume='AUTHORITATIVE_EXTERNAL_STATE_CHANGED'
  elif not source:
   state='WAITING_SOURCE_OR_CLARIFICATION';why='No current source/version binding or precise claim supplied';action='Preserve the original request and obtain the missing source or owner clarification';resume='SOURCE_OR_OWNER_ANSWER_AVAILABLE'
  else:
   state='READY_FOR_BOUNDED_VALIDATION';why='Independent acceptance evidence is missing or incomplete';action=claim.get('validation_plan','Run relevant deterministic/held-out checks; use an executor only for a concrete implementation or expert-review gap');resume='VALIDATION_READY_OR_IMPLEMENTATION_CHANGED'
  rows.append({'id':identifier,'claim':claim.get('text',claim.get('title')),'status':state,'unproven_reason':why,'next_action':action,'resume_when':resume,'resource_policy':'Local first; reuse valid evidence; no inference on unchanged blockers','estimated_additional_native_cost':None,'expected_benefit':claim.get('expected_benefit','Resolve a specific evidence/implementation gap without inventing success'),'scope':claim.get('scope'),'source_sha256':source})
 return {'schema':'uncertainty-followups-v1','items':rows,'native_model_calls':0,'trigger_sha256':hashlib.sha256(json.dumps(claims,sort_keys=True,default=str).encode()).hexdigest(),'mechanism':'Recompute on changed evidence/requirements/source; scheduled local metadata checks. Not an endless inference loop.'}
