"""Provider-independent maintenance eligibility; shared launch guards remain authoritative."""
from datetime import datetime
import time

CAPACITY_MARKERS=('rate limit','rate_limit','usage limit','quota','capacity','429','not authenticated','unauthorized','login required','authentication','ordinary usage unavailable')

def choices(snapshot,now,backoffs,codex_decision):
    try:age=now-datetime.fromisoformat(snapshot['at']).timestamp()
    except (KeyError,ValueError,TypeError):return [],{'all':'Missing quota/auth snapshot'}
    if not 0<=age<=21600:return [],{'all':'Stale quota/auth snapshot'}
    eligible=[];skipped={}
    for provider in ('codex','claude'):
        if now<backoffs.get(provider,{}).get('retry_at_unix',0):skipped[provider]='Provider-specific backoff';continue
        if provider=='codex':
            if not codex_decision.get('eligible'):skipped[provider]=codex_decision.get('reason','Quota unavailable');continue
        elif snapshot.get('claude',{}).get('authenticated') is not True:
            skipped[provider]='Claude authentication unavailable or unknown';continue
        eligible.append(provider)
    return eligible,skipped

def update_backoff(backoffs,provider,record,now):
    failure=record.get('failure')
    if not failure:backoffs.pop(provider,None);return
    if any(marker in failure.lower() for marker in CAPACITY_MARKERS):
        backoffs[provider]={'retry_at_unix':now+18900,'reason':failure[:500]}
