"""Qualified runtime deployment transaction. Caller scores cannot authorize writes."""
from pathlib import Path
from datetime import datetime,timezone
import contextlib,hashlib,json,os,shutil,stat,subprocess,tempfile,uuid
from common import BASE,atomic
import runtime_evaluation as ev

DEPLOY_LOG='runtime-deployments.jsonl'
class RuntimeDeploymentError(RuntimeError):pass

def _utc():return datetime.now(timezone.utc).isoformat()
def _runtime_root(base):return (Path(base).parent/'runtime').resolve()
def _engine_identity(root):return ev.engine(root)

def _write(path,data):
 path=Path(path);mode=stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
 with tempfile.NamedTemporaryFile('wb',dir=path.parent,delete=False) as stream:
  stream.write(data);stream.flush();os.fsync(stream.fileno());tmp=stream.name
 os.chmod(tmp,mode);os.replace(tmp,path)
 fd=os.open(path.parent,os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def _apply_diff(runtime_root,diff_text,*,dry_run=False):
 """Legacy patch entry is confined to existing explicitly allowed helper modules."""
 if not isinstance(diff_text,str) or len(diff_text.encode())>65536:raise RuntimeDeploymentError('Bounded text diff required')
 headers=[]
 for line in diff_text.splitlines():
  if not line.startswith(('--- ','+++ ')):continue
  name=line[4:].split('\t',1)[0].split(' ',1)[0]
  parts=Path(name).parts
  if len(parts)!=3 or parts[0] not in ('a','b') or parts[1]!='urace' or parts[2] not in ev.ALLOWED:raise RuntimeDeploymentError('Diff path outside automatic source scope')
  path=Path(runtime_root)/'urace'/parts[2]
  if path.is_symlink() or not path.is_file():raise RuntimeDeploymentError('Regular existing helper source required')
  headers.append(parts[2])
 if not headers or any(headers.count(n)!=2 for n in set(headers)):raise RuntimeDeploymentError('Unambiguous paired patch headers required')
 result=subprocess.run(['patch','-p1','--batch',*(['--dry-run'] if dry_run else []),'-d',str(runtime_root)],input=diff_text,capture_output=True,text=True,timeout=10)
 if result.returncode:raise RuntimeDeploymentError('Confined patch did not apply: '+result.stderr[-300:])

def validate_diff(base,change_spec):
 if change_spec.get('files_removed'):raise RuntimeDeploymentError('Automatic deletion requires a separately authorized contract')
 root=_runtime_root(base);before=ev.engine(root/'urace');diff=change_spec.get('diff','')
 if diff:
  with tempfile.TemporaryDirectory() as folder:
   target=Path(folder)/'urace';ev.snapshot(root/'urace',target);_apply_diff(folder,diff);ev.validate_sources(root/'urace',target)
 return before

def quick_verify(runtime_root):
 import ast
 try:
  for path in (Path(runtime_root)/'urace').glob('*.py'):ast.parse(path.read_text())
  return True
 except (OSError,SyntaxError,UnicodeError):return False

@contextlib.contextmanager
def _backup_restore(runtime_root):
 # Compatibility helper restores only its scoped regular source files, never a tree deletion.
 package=Path(runtime_root)/'urace';before={n:(package/n).read_bytes() for n in ev.inventory(package)}
 try:yield before
 except BaseException:
  for name,data in before.items():
   if (package/name).read_bytes()!=data:_write(package/name,data)
  raise

def _controls(base,config):
 from product_controls import get_improvement_enabled
 from controls import effective
 from source_integrity import matches
 base=Path(base);pid='urace-runtime:'+str(base.parent.resolve());products=json.loads((base/'products.json').read_text())
 if not any(p.get('id')==pid and p.get('kind')=='runtime' for p in products.get('products',[])):raise RuntimeDeploymentError('Runtime product not explicitly registered')
 if config.get('runtime_workflow',{}).get('enabled') is not True or not get_improvement_enabled(pid,base):raise RuntimeDeploymentError('Runtime improvement disabled')
 owner=effective(base)
 if owner['paused'] or not owner['executor_enabled'] or not owner['auto_goals']:raise RuntimeDeploymentError('Owner controls defer runtime changes')
 if __import__('time').time()>=json.loads((base/'trial-clock.json').read_text())['ends_unix']:raise RuntimeDeploymentError('Original trial expired')
 pins=json.loads((base/'harness-manifest.json').read_text())
 if not pins or any(not matches(base/n,h) for n,h in pins.items()):raise RuntimeDeploymentError('Source integrity prevents deployment')
 return pins

def _sync_snapshot(base):
 from urace import cli,_common
 config=json.loads((Path(base).parent/'runtime/urace/config.json').read_text())
 with _common.state_lock(_common.state_path(config)):cli.write_runtime_snapshot(config)

def _finish_commit(base,transaction):
 base=Path(base);qid=transaction['qualification_id'];snapshot_id=transaction['snapshot_id']
 if not (base/'runtime-qualifications'/qid/'consumed.json').exists():atomic(base/'runtime-qualifications'/qid/'consumed.json',{'at':ev.now(),'snapshot_id':snapshot_id})
 if not any(row.get('event')=='DEPLOYED' and row.get('transaction_id')==transaction['id'] for row in deployment_log(base)):
  _append_event(base,transaction['deployment_event'])
 return transaction

def _update_metadata(base,qualification):
 from source_integrity import matches
 base=Path(base);root=base.parent;package=root/'runtime/urace';pins=json.loads((base/'harness-manifest.json').read_text())
 for name in qualification['files_changed']:
  path=package/name;aliases=[key for key in pins if (base/key).resolve()==path.resolve()]
  if not aliases:raise RuntimeDeploymentError('Changed runtime file was not pinned')
  for key in aliases:pins[key]=ev.sha(path)
 atomic(base/'harness-manifest.json',pins)
 if not all(matches(base/key,value) for key,value in pins.items()):raise RuntimeDeploymentError('Source pins failed after publication')
 previous=json.loads((base/'verification-latest.json').read_text());sources={str(p.relative_to(root)):ev.sha(p) for folder in ('runtime/urace','runtime/tests','trial') for p in (root/folder).glob('*.py') if not p.is_symlink()}
 atomic(base/'verification-latest.json',{'schema':'owner-source-qualification-v1','at':ev.now(),'source_sha256':sources,'results':[{'suite':'autonomous runtime candidate full core/trial regression','tests':qualification['regression']['tests'],'failures':0,'errors':0,'skipped':qualification['regression']['skipped'],'log':str(base/'runtime-qualifications'/qualification['id']/'regression.log')}],'previous_qualification_receipt':str(base/'runtime-deployment-journals'/json.loads((base/'runtime-deployment-transaction.json').read_text())['id']/'verification-latest.json'),'live_feature_coverage_complete':False,'notes':'Source-bound private runtime cases plus sealed full regression; not user value or universal comparative proof'})
 _sync_snapshot(base)



def recover(base):
 """Recover an interrupted transaction; preserve unexpected concurrent owner edits."""
 base=Path(base);pointer=base/'runtime-deployment-transaction.json'
 if not pointer.exists():return None
 transaction=json.loads(pointer.read_text())
 if not isinstance(transaction.get('id'),str) or not transaction['id'].startswith('transaction-') or not transaction['id'].replace('-','').isalnum():raise RuntimeDeploymentError('Invalid deployment journal id')
 folder=base/'runtime-deployment-journals'/transaction['id']
 if folder.is_symlink():raise RuntimeDeploymentError('Deployment journal symlink')
 if transaction['status']=='COMMITTED':return _finish_commit(base,transaction)
 if transaction['status']=='ROLLED_BACK':return transaction
 package=base.parent/'runtime/urace'
 for name,item in transaction['files'].items():
  path=package/name
  if name not in ev.ALLOWED or path.is_symlink() or ev.sha(path) not in (item['before'],item['after']):raise RuntimeDeploymentError('Concurrent source differs from journal; automatic rollback blocked')
 for name in transaction['files']:_write(package/name,(folder/'sources'/name).read_bytes())
 for name in ('harness-manifest.json','verification-latest.json','runtime-baseline-latest.json'):
  if (folder/name).exists():_write(base/name,(folder/name).read_bytes())
 transaction['status']='ROLLED_BACK';transaction['at']=ev.now();atomic(pointer,transaction);atomic(folder/'transaction.json',transaction)
 # Stable recovery mirror is restored from exact pretransaction source; immutable old snapshots remain.
 _sync_snapshot(base)
 _append_event(base,{'event':'ROLLED_BACK','transaction_id':transaction['id'],'at':ev.now(),'reason':'Incomplete/failed runtime transaction recovered'})
 return transaction

def _deploy(base,config,change_spec,quality_evidence):
 import runtime_quality_gate as gate,runtime_qualification as q,runtime_snapshot
 base=Path(base);config=json.loads((base.parent/'runtime/urace/config.json').read_text());qid=quality_evidence.get('qualification_id')
 decision=gate.gate_decision(base,config,qualification_id=qid)
 if decision['decision']!='ACCEPTED':raise RuntimeDeploymentError(decision['reason'])
 if not q.installation_ready(base):raise RuntimeDeploymentError('Isolated deployment/recovery qualification not installed')
 if config.get('runtime_workflow',{}).get('auto_deploy',True) is not True:raise RuntimeDeploymentError('Automatic deployment disabled by owner')
 # The existing supervisor drains all native workers before entering this method.
 from trial_supervisor import active
 owner=active(base);health=json.loads((base/'supervisor-health.json').read_text())
 if not owner or owner.get('pid')!=os.getpid() or health.get('pid')!=os.getpid() or health.get('running_tasks') or health.get('deployment_draining') is not True:raise RuntimeDeploymentError('Actual owning supervisor must drain all workers before deployment')
 with (base/'trial.guard').open('a') as guard:
  __import__('fcntl').flock(guard,__import__('fcntl').LOCK_EX|__import__('fcntl').LOCK_NB)
  _controls(base,config);qualification=q.load_qualification(base,qid);candidate=base/'runtime-qualifications'/qid/'candidate';package=base.parent/'runtime/urace'
  if ev.inventory(package)!=qualification['before_sources']:raise RuntimeDeploymentError('Concurrent source edit; candidate stale')
  ev.validate_sources(package,candidate,qualification['files_changed'])
  if len(qualification['files_changed'])!=1:raise RuntimeDeploymentError('Current automatic policy permits one helper module per cycle')
  identifier='transaction-'+uuid.uuid4().hex;folder=base/'runtime-deployment-journals'/identifier;(folder/'sources').mkdir(parents=True)
  files={}
  for name in qualification['files_changed']:
   shutil.copyfile(package/name,folder/'sources'/name);files[name]={'before':ev.sha(package/name),'after':ev.sha(candidate/name)}
  for name in ('harness-manifest.json','verification-latest.json','runtime-baseline-latest.json'):
   if (base/name).exists():shutil.copyfile(base/name,folder/name)
  transaction={'id':identifier,'qualification_id':qid,'status':'PREPARED','owner_pid':os.getpid(),'files':files,'at':ev.now()};atomic(base/'runtime-deployment-transaction.json',transaction);atomic(folder/'transaction.json',transaction)
  _append_event(base,{'event':'DEPLOYING','transaction_id':identifier,'at':ev.now()})
  try:
   for name in files:_write(package/name,(candidate/name).read_bytes())
   if ev.inventory(package)!=qualification['candidate_sources'] or not quick_verify(base.parent/'runtime'):raise RuntimeDeploymentError('Published source identity/syntax mismatch')
   post=ev.measure(base,package,'post_deploy')
   if post['score']!=qualification['candidate_score'] or not post['all_pass']:raise RuntimeDeploymentError('Post-deployment contract failed')
   fresh=json.loads((base.parent/'runtime/urace/config.json').read_text())
   from controls import effective
   from product_controls import get_improvement_enabled
   if q.purpose(base)!=qualification['purpose_sha256'] or effective(base)['paused'] or not get_improvement_enabled('urace-runtime:'+str(base.parent.resolve()),base) or not fresh.get('runtime_workflow',{}).get('auto_deploy',True) or not fresh.get('runtime_workflow',{}).get('enabled',False):raise RuntimeDeploymentError('Owner purpose/controls changed during deployment')
   _update_metadata(base,qualification)
   spec={**change_spec,'files_changed':['runtime/urace/'+name for name in files],'engine_sha256_before':ev.digest(qualification['before_sources']),'engine_sha256_after':ev.digest(qualification['candidate_sources'])}
   evidence={'baseline_score':qualification['baseline_score'],'candidate_score':qualification['candidate_score'],'gate_decision':decision,'qualification_id':qid,'post_deploy_id':post['id']}
   snapshot_id=runtime_snapshot.create(base,spec,evidence)
   atomic(base/'runtime-baseline-latest.json',{'evaluation_id':post['id'],'role':'post_deploy','at':ev.now()})
   event={'event':'DEPLOYED','at':ev.now(),'snapshot_id':snapshot_id,'transaction_id':identifier,'delta':decision['delta'],'files_changed':spec['files_changed'],'proposer_provider':spec.get('proposer_provider'),'engine_sha256_after':spec['engine_sha256_after'],'qualification_id':qid}
   transaction.update(status='COMMITTED',snapshot_id=snapshot_id,deployment_event=event,at=ev.now());atomic(base/'runtime-deployment-transaction.json',transaction);atomic(folder/'transaction.json',transaction)
   _finish_commit(base,transaction)
   return snapshot_id
  except BaseException:
   restored=recover(base)
   if restored and restored.get('status')=='COMMITTED':return restored['snapshot_id']
   raise

def run(base,config,change_spec,candidate_score=None):
 import runtime_quality_gate as gate
 qid=change_spec.get('qualification_id');decision=gate.gate_decision(base,config,qualification_id=qid)
 if decision['decision']!='ACCEPTED':return {'status':'REJECTED','snapshot_id':None,'gate_decision':decision,'reason':decision['reason']}
 sid=deploy(base,config,change_spec,{'qualification_id':qid,'supervisor_drained':change_spec.get('supervisor_drained',False)})
 return {'status':'DEPLOYED','snapshot_id':sid,'gate_decision':decision}

def _append_event(base,event):
 path=Path(base)/DEPLOY_LOG
 from urace.authenticated_journal import append_row
 append_row(path,event)
def _append_deployment_event(base,snapshot_id,decision,change_spec):
 _append_event(base,{'event':'DEPLOYED','at':ev.now(),'snapshot_id':snapshot_id,'delta':decision.get('delta'),'files_changed':change_spec.get('files_changed',[])})
def deployment_log(base):
 path=Path(base)/DEPLOY_LOG
 if not path.exists():return []
 return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
def redeployment_report(base):
 rows=deployment_log(base);deployed=[r for r in rows if r.get('event')=='DEPLOYED']
 return {'schema':'runtime-redeployment-report-v2','deployments':deployed,'deployments_total':len(deployed),'events':rows,'scope':'Accepted runtime changes with independent qualification; not proof of user value'}


def deploy(base,config,change_spec,quality_evidence):
 # Peer opt-out/block and incorporation are serialized against the same local policy lock.
 import runtime_qualification as q
 try:cert=q.load_qualification(base,quality_evidence.get('qualification_id')) if quality_evidence.get('qualification_id') else None
 except (ValueError,OSError,KeyError,TypeError):return _deploy(base,config,change_spec,quality_evidence)
 receipt=json.loads((Path(base)/'transport'/(cert['proposal_receipt_id']+'.json')).read_text()) if cert else {}
 if receipt.get('role')!='PEER_CANDIDATE':return _deploy(base,config,change_spec,quality_evidence)
 import peer_runtime
 ex=peer_runtime.exchange(base)
 with ex.lock():
  bundle=peer_runtime.validate_receipt(base,receipt)
  result=_deploy(base,config,change_spec,quality_evidence)
  ex.event('APPLIED_AFTER_LOCAL_QUALIFICATION',bundle=receipt['bundle_id'],peer=receipt['peer_id'],feature=bundle['feature'],snapshot_id=result,qualification_id=cert['id'],actual_use_verified=False)
  return result
