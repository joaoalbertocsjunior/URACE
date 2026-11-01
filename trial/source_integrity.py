"""Freeze authority/configuration while allowing narrowly validated operator controls."""
import copy,hashlib,json

def projected(path):
 c=json.loads(path.read_text());out=copy.deepcopy(c)
 from urace.executor_capabilities import contract as capability_contract
 capability_contract(out)
 out.pop('executor_skills',None);out.pop('context_guard',None)
 from urace.product_creation import validate_entry
 registry=out.get('product_registry',[])
 for entry in registry:
  if entry.get('kind')=='bootstrapped':validate_entry(entry,path.parents[3])
 if registry:out['product_registry']=[e for e in registry if e.get('kind')!='bootstrapped']
 milestones=out.pop('auto_milestones',{})
 from urace.milestone_suggestions import settings as milestone_settings
 milestone_settings({'auto_milestones':milestones})
 runtime=out.get('runtime_workflow',{})
 from runtime_cycle import settings as runtime_settings
 runtime_settings({'runtime_workflow':runtime})
 for key in ('enabled','auto_deploy','interval_seconds'):runtime.pop(key,None)
 if not runtime:out.pop('runtime_workflow',None)
 feedback=out.pop('decision_feedback',{})
 from urace.decision_feedback import settings as feedback_settings
 feedback_settings({'decision_feedback':feedback})
 value=out.pop('value_discovery',{})
 if not isinstance(value,dict) or set(value)-{'enabled','external_research','ranking','freshness_seconds','research_seconds','research_sources'}:raise ValueError('Invalid value-discovery controls')
 for key in ('enabled','external_research','ranking'):
  if key in value and type(value[key]) is not bool:raise ValueError('Invalid value-discovery boolean')
 for key,lo,hi in [('freshness_seconds',60,31536000),('research_seconds',1,300),('research_sources',1,50)]:
  if key in value and (type(value[key]) is not int or not lo<=value[key]<=hi):raise ValueError('Invalid value-discovery allowance')
 goals=out.get('auto_goals',{})
 for k in ('enabled','replenish_backlog'):
  if k in goals and type(goals[k]) is not bool:raise ValueError('Invalid automatic goal control')
  goals.pop(k,None)
 if not goals:out.pop('auto_goals',None)
 resources=out.get('resources',{})
 if resources.get('effort','medium') not in ('low','medium','high'):raise ValueError('Invalid URACE resource effort')
 overrides=resources.get('executor_effort',{})
 if not isinstance(overrides,dict) or any(v not in ('low','medium','high') for v in overrides.values()):raise ValueError('Invalid per-executor resource effort')
 resources.pop('effort',None);resources.pop('executor_effort',None)
 if not resources:out.pop('resources',None)
 executor=out.get('executor',{});native=executor.get('native_options',{})
 for key in ('max_executor_calls_per_24h','max_executor_calls_per_30d'):
  value=executor.pop(key,None)
  if value is not None and (type(value) is not int or value<2):raise ValueError('Invalid executor budget')
 if 'enabled' in executor:
  if type(executor['enabled']) is not bool:raise ValueError('Invalid executor enabled control')
  executor.pop('enabled')
 for provider in executor.get('providers',[]):
  for key in ('max_calls_per_24h','max_calls_per_30d'):
   value=provider.pop(key,None)
   if value is not None and (type(value) is not int or value<1):raise ValueError('Invalid provider budget')
  if 'enabled' in provider:
   if type(provider['enabled']) is not bool:raise ValueError('Invalid provider enabled control')
   provider.pop('enabled')
 known={'codex','claude'}|{p.get('id') for p in executor.get('providers',[])}
 if not isinstance(native,dict):raise ValueError('Invalid native options')
 for provider,options in native.items():
  if provider not in known or not isinstance(options,dict) or set(options)-{'model','native_effort'}:raise ValueError('Unsupported native override')
  if options.get('native_effort','medium') not in ('low','medium','high'):raise ValueError('Invalid native effort')
  if 'model' in options:
   m=options['model']
   if not isinstance(m,str) or not m.strip() or m.startswith('-') or any(ord(x)<32 for x in m):raise ValueError('Invalid model')
 executor.pop('native_options',None)
 return hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def descriptor(path):return {'projection':'operator-controls-v1','sha256':projected(path)}
def matches(path,expected):
 try:
  if isinstance(expected,str):return hashlib.sha256(path.read_bytes()).hexdigest()==expected
  return expected.get('projection')=='operator-controls-v1' and projected(path)==expected['sha256']
 except (OSError,ValueError,TypeError,KeyError,AttributeError):return False
