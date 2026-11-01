"""Bidirectional declared context relations and explainable attention; no inferred authority or neural claims."""
import hashlib,json,math
RELATIONS={'depends_on','relates_to','supports','contradicts','clarifies','supersedes','derived_from'}

def build(passages):
 nodes={k:{'id':k,'source_sha256':hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest(),'type':v.get('type','requirement'),'priority':v.get('priority'),'critical':v.get('requires_explicit_context_read') is True,'changed':v.get('changed') is True,'bottleneck':v.get('bottleneck_id'),'status':v.get('status'),'unproven':v.get('unproven') is True or str(v.get('status','')).upper() in ('UNPROVEN','UNVERIFIED','MISSING_EVIDENCE'),'validation_plan':v.get('validation_plan'),'resume_when':v.get('resume_when'),'source':v.get('source')} for k,v in passages.items()};edges=[];unresolved=[]
 for key,row in passages.items():
  declarations={r:row.get(r,[]) for r in RELATIONS}
  declarations['depends_on']=row.get('dependencies',declarations['depends_on'])
  for relation,targets in declarations.items():
   if isinstance(targets,str):targets=[targets]
   if not isinstance(targets,list) or len(targets)>100:raise ValueError('Bounded declared graph relationships required')
   for target in targets:
    if not isinstance(target,str):raise ValueError('Relationship target must be an identity')
    edge={'from':key,'to':target,'relation':relation,'basis':'DECLARED_SOURCE','verified_semantic_truth':False,'authority_grant':False}
    (edges if target in nodes else unresolved).append(edge)
 edges.sort(key=lambda e:(e['from'],e['relation'],e['to']));identity=hashlib.sha256(json.dumps({'nodes':nodes,'edges':edges,'unresolved':unresolved},sort_keys=True).encode()).hexdigest()
 return {'schema':'context-relations-v1','sha256':identity,'nodes':nodes,'edges':edges,'unresolved_edges':unresolved,'scheduling':'Only explicit dependency relations feed dependency planning; semantic links may be cyclic','native_model_calls':0,'semantic_comprehension_proven':False}

def related(graph,identifier,depth=1,limit=32):
 if identifier not in graph['nodes'] or type(depth) is not int or not 0<=depth<=3 or type(limit) is not int or not 1<=limit<=100:raise ValueError('Known node, depth 0–3 and limit 1–100 required')
 seen={identifier};frontier={identifier};links=[]
 for _ in range(depth):
  next_nodes=set()
  for edge in graph['edges']:
   if edge['from'] in frontier or edge['to'] in frontier:
    links.append(edge);next_nodes.update((edge['from'],edge['to']))
  next_nodes-=seen;seen|=next_nodes;frontier=next_nodes
  if len(seen)>limit:break
 keys=sorted(seen,key=lambda k:(k!=identifier,k));selected=set(keys[:limit]);return {'graph_sha256':graph['sha256'],'nodes':[graph['nodes'][k] for k in keys[:limit]],'edges':[e for e in links if e['from'] in selected and e['to'] in selected],'more_available':len(seen)>limit,'query_again':'Use another node/depth to expand; full source remains available','authority_grant':False}

def attention(graph):
 def key(node):
  priority=node.get('priority');known=type(priority) in (int,float) and math.isfinite(priority)
  return (not node['critical'],not node['changed'],not bool(node['bottleneck']),not node['unproven'],-(priority if known else 0),node['id'])
 return {'graph_sha256':graph['sha256'],'ordered_nodes':[{'id':n['id'],'why':[reason for condition,reason in ((n['critical'],'Owner-declared critical context'),(n['changed'],'Declared change needs rechecking'),(bool(n['bottleneck']),'Addresses a declared bottleneck'),(n['unproven'],'Unproven claim needs evidence or a conditional follow-up; not automatic inference'),(n['priority'] is not None,'Owner priority'),(True,'Full original passage remains retrievable')) if condition],'source_sha256':n['source_sha256']} for n in sorted(graph['nodes'].values(),key=key)],'mechanism':'Deterministic, explainable retrieval priority; not transformer attention or proof of relevance','pruning_enabled':False,'native_model_calls':0}

def from_state(state):
 rows={}
 for kind,items in (('goal',state.get('objectives',[])),('context',state.get('context_inputs',[]))):
  for index,row in enumerate(items):
   key=str(row.get('id',kind+'-'+str(index)))
   if key in rows:raise ValueError('Context/goal identity collision; disambiguate source identities')
   rows[key]={**row,'type':kind}
 return build(rows)
