"""Metadata-only quota monitor; no credit resets/purchases or inference probes."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,json,subprocess,sys,time
from common import operations_root,BASE
ROOT=operations_root()
TRIAL=BASE
MAINTENANCE=ROOT.parent/'autonomous-maintenance-v1'
sys.path.insert(0,str(TRIAL))
from providers import Transport,quota_view
from common import atomic

def probe_codex():
    client=Transport(['codex','app-server','--disable','hooks','--disable','apps','--disable','plugins'],TRIAL/'work')
    def response(identifier):
        while True:
            raw=client.line()
            if raw is None:raise RuntimeError('Metadata server ended')
            event=json.loads(raw)
            if event.get('id')==identifier:
                if 'error' in event:raise RuntimeError('Metadata request rejected')
                return event['result']
    try:
        client.send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'urace-availability-monitor','version':'1'}}});response(1);client.send({'method':'initialized','params':{}})
        client.send({'id':2,'method':'account/rateLimits/read','params':{}})
        return quota_view(response(2))
    finally:client.close()

def should_wake(previous,current):
    return previous.get('last_known_codex_usage_allowed',previous.get('codex',{}).get('ordinaryUsageAllowed')) is False and current.get('codex',{}).get('ordinaryUsageAllowed') is True

def main():
    if (BASE.parent/'.migration-in-progress').exists():
        print(json.dumps({'status':'PAUSED','inference_calls':0,'metadata_probes':0}));return 0
    with (ROOT/'availability.guard').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        previous=json.loads((ROOT/'availability-latest.json').read_text()) if (ROOT/'availability-latest.json').exists() else {}
        now=time.time();report={'at':datetime.now(timezone.utc).isoformat(),'probe_interval_seconds':18900,'inference_calls':0,'model_tokens':0,'credit_resets_or_purchases':0,'attribution':'Quota is account-wide, not per-job billed credits','claude':{'credit_availability':'UNKNOWN','reason':'No established metadata-only quota interface; auth success does not prove usable credits'},'maintenance_wakeup_requested':False}
        try:report['codex']=probe_codex()
        except Exception as error:report['codex']={'ordinaryUsageAllowed':None,'error':type(error).__name__}
        try:
            result=subprocess.run(['claude','auth','status','--json'],capture_output=True,text=True,timeout=15)
            value=json.loads(result.stdout)
            report['claude'].update(authenticated=value.get('loggedIn'),auth_check_returncode=result.returncode)
        except Exception as error:report['claude']['auth_check_error']=type(error).__name__
        allowed=report['codex'].get('ordinaryUsageAllowed')
        report['last_known_codex_usage_allowed']=allowed if isinstance(allowed,bool) else previous.get('last_known_codex_usage_allowed',previous.get('codex',{}).get('ordinaryUsageAllowed'))
        # Wake the bounded maintenance worker only on an observed unavailable -> available transition.
        # Its own cooldown, issue gating, duration and budget remain authoritative.
        atomic(ROOT/'availability-latest.json',report)
        from trial_supervisor import active as supervisor_active
        if should_wake(previous,report) and not supervisor_active():
            marker=json.loads((ROOT/'comparison-current.json').read_text()) if (ROOT/'comparison-current.json').exists() else {}
            target='urace-spec-trial.service' if marker.get('kind')=='urace_spec_improvement' else ('urace-self-improvement-v1.service' if marker.get('kind')=='urace_self_improvement' else 'urace-autonomous-maintenance-v1.service')
            result=subprocess.run(['systemctl','--user','start','--no-block',target],capture_output=True,text=True,timeout=10)
            report['maintenance_wakeup_requested']=result.returncode==0
        report['productive_trial_resume']='Active comparison queues resume independently on eligibility; no fixed repair-slot cap; shared measured/reserved resource guards apply'
        folder=ROOT/'availability';folder.mkdir(exist_ok=True)
        atomic(folder/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'),report);atomic(ROOT/'availability-latest.json',report)
        print(json.dumps({'at':report['at'],'codex':report['codex'],'claude':report['claude'],'inference_calls':0}))

if __name__=='__main__':main()
