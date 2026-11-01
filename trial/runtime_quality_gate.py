"""Runtime-only quality gate; numeric claims are not deployment evidence."""
from pathlib import Path
import json,math
from common import BASE
import runtime_evaluation as ev

SCHEMA='runtime-quality-gate-v2'
DEFAULT_MINIMUM_DELTA=5.0
DEFAULT_METRIC='runtime_contract_quality_score'

def _finite(v):return type(v) in (int,float) and math.isfinite(v)
def qualify(baseline_score,candidate_score,minimum_delta=5.0):
 if not all(_finite(v) for v in (baseline_score,candidate_score,minimum_delta)):return False
 if minimum_delta<0:raise ValueError('Minimum delta must be non-negative')
 return candidate_score-baseline_score>=minimum_delta

def read_latest_evaluation(base=BASE):
 base=Path(base)
 try:
  pointer=json.loads((base/'runtime-baseline-latest.json').read_text());receipt=ev.load_receipt(base,pointer['evaluation_id'])
  if receipt['sources']!=ev.inventory(base.parent/'runtime/urace'):return None
  return receipt
 except (OSError,ValueError,KeyError,TypeError):return None

def read_latest_score(base=BASE):
 receipt=read_latest_evaluation(base);return receipt['score'] if receipt else None

def gate_config(config):
 wf=config.get('runtime_workflow',{}) if isinstance(config,dict) else {}
 value=wf.get('quality_gate_minimum_score_delta',5.0)
 if not _finite(value) or value<0:raise ValueError('Finite nonnegative score delta required')
 metric=wf.get('quality_gate_metric',DEFAULT_METRIC)
 return {'metric':DEFAULT_METRIC,'requested_metric':metric,'minimum_delta':value}

def gate_decision(base,config,candidate_score=None,*,qualification_id=None):
 params=gate_config(config);result={'schema':SCHEMA,'decision':'GATE_UNAVAILABLE','metric':params['metric'],'minimum_delta':params['minimum_delta'],'baseline_score':None,'candidate_score':None,'delta':None,'suite_sha256':ev.digest(ev.contract())}
 if params['requested_metric'] not in (DEFAULT_METRIC,'executable_benchmark_score'):
  return {**result,'reason':'Unsupported measurement contract; do not reinterpret custom owner weights'}
 if not qualification_id:return {**result,'reason':'Independent source-bound runtime qualification required; caller scores are advisory only'}
 try:
  from runtime_qualification import load_qualification
  receipt=load_qualification(base,qualification_id)
  if receipt['before_sources']!=ev.inventory(Path(base).parent/'runtime/urace'):raise ValueError('Live source changed after baseline')
 except (OSError,ValueError,KeyError,TypeError) as error:return {**result,'reason':str(error)}
 result.update(baseline_score=receipt['baseline_score'],candidate_score=receipt['candidate_score'],delta=receipt['delta'],qualification_id=qualification_id)
 passed=qualify(receipt['baseline_score'],receipt['candidate_score'],params['minimum_delta'])
 return {**result,'decision':'ACCEPTED' if passed else 'REJECTED','reason':'Independent runtime contracts and full regression passed; declared delta met' if passed else 'Measured runtime delta is below the unchanged owner gate'}

def status(base=BASE,config=None):
 params=gate_config(config or {});baseline=read_latest_score(base)
 return {'schema':SCHEMA,'metric':params['metric'],'minimum_delta':params['minimum_delta'],'baseline_score':baseline,'gate_measurable':baseline is not None,'scope':'Frozen runtime helper contracts and independent regression; no specification-score pooling or user-value claim'}
