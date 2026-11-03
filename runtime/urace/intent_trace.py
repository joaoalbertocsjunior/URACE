"""Source/claim coverage is explicit; text coverage never proves semantic understanding."""
import hashlib,re

def source_coverage(text,sections):
 covered=bytearray(len(text))
 for section in sections:
  part=section.get('raw_text','')
  if not isinstance(part,str) or not part:continue
  start=0
  while True:
   index=text.find(part,start)
   if index<0:break
   covered[index:index+len(part)]=b'1'*len(part);start=index+len(part)
 missing=[]
 for match in re.finditer(r'\S+',text):
  token=match.group();word=token.strip('.,;:!?()[]{}').lower()
  if any(not covered[i] and text[i].isalnum() for i in range(match.start(),match.end())) and word not in {'and','or','also','please','then','e','ou'} and word:
   missing.append({'start':match.start(),'end':match.end(),'text':token})
 return {'schema':'intent-source-coverage-v1','source_sha256':hashlib.sha256(text.encode()).hexdigest(),'status':'SOURCE_COVERED' if not missing else 'UNASSIGNED_SOURCE','unassigned':missing,'semantic_completeness_proven':False,'meaning':'Every source section must be accounted for; interpretation and outcome still require validation'}

def assessment(requirements,claims):
 by_id={r['id']:r for r in requirements};mapped={k:[] for k in by_id};unsupported=[]
 for claim in claims:
  targets=claim.get('requirement_ids',[])
  if not targets or any(k not in by_id for k in targets):unsupported.append({**claim,'reason':'Unknown or absent request linkage'});continue
  for key in targets:mapped[key].append(claim)
 rows=[]
 for key,requirement in by_id.items():
  linked=mapped[key];verified=[c for c in linked if c.get('status')=='VERIFIED' and c.get('evidence_refs')];pending=[c for c in linked if c not in verified]
  rows.append({'id':key,'request':requirement,'claims':linked,'status':'LINKED_EVIDENCE_REQUIRES_AUTHENTICATION' if verified and not pending else 'UNVERIFIED_OR_INCOMPLETE','unproven_reason':None if verified and not pending else 'Missing implementation/evidence, unresolved claims, or incomplete validation scope','next_action':requirement.get('validation_plan','Provide independent source-bound acceptance evidence and state its limits'),'resume_when':requirement.get('resume_when','New evidence, clarified requirement or changed implementation'),'native_model_calls':0})
 return {'schema':'request-claim-evidence-trace-v1','requirements':rows,'unsupported_claims':unsupported,'linkage_complete':bool(rows) and all(r['status']=='LINKED_EVIDENCE_REQUIRES_AUTHENTICATION' for r in rows) and not unsupported,'complete_assessment_proven':False,'evidence_truth_independently_verified':False,'meaning':'This is linkage/coverage validation; cited evidence must itself be authenticated and relevant. No universal success or comprehension claim.'}
