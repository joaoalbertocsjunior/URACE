"""One process owns all trial scheduling; native executors are child workers."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import fcntl,json,os,time,sys,signal,traceback,math
from common import BASE,atomic

def active(base=BASE):
 try:
  value=json.loads((Path(base)/'trial-supervisor.json').read_text());pid=value['pid']
  if type(pid) is not int or pid<=0:return None
  stat=Path('/proc')/str(pid)/'stat';ticks=stat.read_text().rsplit(')',1)[1].split()[19]
  return value if ticks==value.get('start_ticks') else None
 except (OSError,ValueError,KeyError,TypeError,IndexError):return None

def external_owner(base=BASE):
 owner=active(base);return owner if owner and owner['pid']!=os.getpid() else None

def legacy_step():
 import spec_trial,cross_audit,quality_restore
 schedule=BASE/'supervisor-legacy.json';value=json.loads(schedule.read_text()) if schedule.exists() else {};now=time.time()
 if now>=value.get('audit_at',now+1):
  cross_audit.run()
  with (BASE/'trial.guard').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);quality_restore.run()
  atomic(schedule,{'audit_at':time.time()+10800});return 'editorial_revalidation'
 if not value:atomic(schedule,{'audit_at':now+10800})
 return spec_trial.main()

def productive_runtime_step():
 from product_controls import get_improvement_enabled
 import runtime_cycle
 config=json.loads((BASE.parent/'runtime/urace/config.json').read_text())
 runtime_id='urace-runtime:'+str(BASE.parent.resolve())
 if not runtime_cycle.settings(config)['enabled'] or not get_improvement_enabled(runtime_id,BASE):
  return {'status':'DISABLED','reason':'Runtime improvement disabled'}
 return runtime_cycle.step(BASE)

def productive_spec_step():
 from product_controls import get_improvement_enabled
 try:spec_id=json.loads((BASE/'contract.json').read_text()).get('product_id')
 except (OSError,ValueError):return {'status':'DISABLED','reason':'No spec contract'}
 if not spec_id or not get_improvement_enabled(spec_id,BASE):
  return {'status':'DISABLED','reason':'Spec improvement disabled'}
 return legacy_step()

def runtime_local_work():
 from product_controls import get_improvement_enabled
 import runtime_cycle
 config=json.loads((BASE.parent/'runtime/urace/config.json').read_text())
 return runtime_cycle.settings(config)['enabled'] and get_improvement_enabled('urace-runtime:'+str(BASE.parent.resolve()),BASE)

def review_step():
 import review
 result=review.main()
 import runtime_regression_guard
 runtime_regression_guard.run_guard(BASE)
 if result==1:
  report=json.loads((BASE/'operational-review-latest.json').read_text())
  if report.get('runtime_integrity_pass') is True and report.get('evidence_warnings'):
   return {'status':'COMPLETED_WITH_EVIDENCE_LIMITATIONS','warnings':report['evidence_warnings']}
 return result

class CapacityAdmission:
 """Cache metadata admission; idle work never repeatedly scans full ledgers."""
 def __init__(self,probe,clock=time.time,interval=30):
  self.probe=probe;self.clock=clock;self.interval=interval;self.next_check=0;self.snapshot={'eligible_executors':[],'waits':{}}
 def ready(self):
  now=self.clock()
  if now>=self.next_check:
   try:
    eligible,waits=self.probe();self.snapshot={'eligible_executors':eligible,'waits':waits}
   except Exception as error:self.snapshot={'eligible_executors':[],'waits':{'admission':type(error).__name__+': '+str(error)[:300]}}
   self.next_check=now+self.interval
  return bool(self.snapshot['eligible_executors'])

def next_review(base,now):
 """A routine controller restart must not postpone the promised assessment."""
 base=Path(base);trial=json.loads((base/'trial-clock.json').read_text())['trial_id'];path=base/'review-schedule.json'
 try:value=json.loads(path.read_text())
 except (OSError,ValueError):value={}
 due=value.get('next_due_unix')
 if value.get('trial_id')!=trial or type(due) not in (int,float) or not math.isfinite(due) or due<0 or due>now+10800:
  due=now+10800;atomic(path,{'trial_id':trial,'next_due_unix':due})
 return due

def main():
 sys.path.insert(0,str(BASE.parent/'runtime'));stopping=False
 def stop(signum,frame):
  nonlocal stopping
  stopping=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 with (BASE/'supervisor.guard').open('a') as guard:
  fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
  ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19];owner={'pid':os.getpid(),'start_ticks':ticks,'started_at':datetime.now(timezone.utc).isoformat(),'mode':'single-process','native_executor_children_expected':True};atomic(BASE/'trial-supervisor.json',owner)
  import runtime_trial
  runtime_trial.recover(BASE)
  from downstream_study import step as run_one
  from spec_trial import eligible
  admission=CapacityAdmission(eligible)
  from availability import main as availability
  from claude_preflight import step as preflight
  review=review_step
  clocks={'preflight':0,'productive_runtime':0,'productive_spec':0,'study':0,'availability':0,'review':next_review(BASE,time.time())};intervals={'preflight':18900,'productive_runtime':5,'productive_spec':5,'study':5,'availability':1200,'review':10800};tasks={'preflight':preflight,'productive_runtime':productive_runtime_step,'productive_spec':productive_spec_step,'study':run_one,'availability':availability,'review':review};running={};last={}
  try:
   with ThreadPoolExecutor(max_workers=4,thread_name_prefix='urace-trial') as pool:
    while not stopping:
     now=time.time();clock=json.loads((BASE/'trial-clock.json').read_text())
     if now>=clock['ends_unix']:break
     if (BASE.parent/'.migration-in-progress').exists():stopping=True;continue
     for name,future in list(running.items()):
      if not future.done():continue
      try:
       value=future.result()
       if type(value) is int and value!=0:raise RuntimeError('Worker exit status '+str(value))
       last[name]={'finished_at':datetime.now(timezone.utc).isoformat(),'status':('FINISHED_WITH_EVIDENCE_LIMITATIONS' if value.get('status')=='COMPLETED_WITH_EVIDENCE_LIMITATIONS' else value.get('status','FINISHED')) if isinstance(value,dict) else 'FINISHED'}
       if isinstance(value,dict) and value.get('reason'):last[name]['reason']=value['reason']
       if isinstance(value,dict) and value.get('warnings'):last[name]['warnings']=value['warnings']
      except Exception as error:last[name]={'finished_at':datetime.now(timezone.utc).isoformat(),'status':'DEFERRED_OR_ERROR','error':type(error).__name__+': '+str(error)[:1000]};traceback.print_exc()
      clocks[name]=now+intervals[name]
      if name=='review':atomic(BASE/'review-schedule.json',{'trial_id':clock['trial_id'],'next_due_unix':clocks[name]})
      del running[name]
     # A qualified runtime transaction runs only after all existing workers finish.
     pending=(BASE/'runtime-deployment-pending.json').exists()
     if pending:
      atomic(BASE/'supervisor-health.json',{'at':datetime.now(timezone.utc).isoformat(),**owner,'running_tasks':list(running),'last_tasks':last,'next_due_unix':clocks,'controller_processes':1,'trial_ended':False,'execution_admission':admission.snapshot,'deployment_draining':True})
      if not running:
       import runtime_cycle
       if runtime_cycle.apply_pending(BASE):return 'RELOAD'
      time.sleep(1);continue
     # Availability metadata must refresh independently of a busy native call.
     import quota_pressure
     for name in ('availability','productive_runtime','productive_spec','study','review','preflight'):
      if name not in running and now>=clocks[name]:
       if name=='study' and not admission.ready():continue
       if name=='productive_runtime' and not runtime_local_work() and not admission.ready():continue
       if name=='productive_spec' and not admission.ready():continue
       if name=='study' and quota_pressure.is_high_pressure(BASE) and not any(p!='claude' for p in admission.snapshot['eligible_executors']):continue
       running[name]=pool.submit(tasks[name])
     atomic(BASE/'supervisor-health.json',{'at':datetime.now(timezone.utc).isoformat(),**owner,'running_tasks':list(running),'last_tasks':last,'next_due_unix':clocks,'controller_processes':1,'trial_ended':False,'execution_admission':{**admission.snapshot,'next_metadata_check_unix':admission.next_check,'idle_metadata_interval_seconds':admission.interval}})
     time.sleep(1)
  finally:
   if active() and active()['pid']==os.getpid():(BASE/'trial-supervisor.json').unlink(missing_ok=True)
 return 0
if __name__=='__main__':
 result=main()
 if result=='RELOAD':os.execv(sys.executable,[sys.executable,str(Path(__file__).resolve())])
 raise SystemExit(result)
