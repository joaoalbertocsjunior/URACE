"""Read only the operator controls shared with the canonical runtime CLI."""
import json
from pathlib import Path


def effective(base):
    base = Path(base)
    path = base.parent / 'runtime/urace/config.json'
    config = json.loads(path.read_text()) if path.exists() else {}
    settings_path = base / 'settings.json'
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    goals = config.get('auto_goals', {})
    resources = config.get('resources', {})
    enabled = goals.get('enabled', settings.get('auto_goals', True))
    replenish = goals.get('replenish_backlog', settings.get('auto_replenish', True))
    if type(enabled) is not bool or type(replenish) is not bool:
        raise ValueError('Automatic goal controls must be booleans')
    effort = resources.get('effort', settings.get('resource_effort', 'medium'))
    overrides = resources.get('executor_effort', {})
    native = config.get('executor', {}).get('native_options', {})
    if effort not in ('low', 'medium', 'high') or not isinstance(overrides, dict) or any(v not in ('low', 'medium', 'high') for v in overrides.values()):
        raise ValueError('Invalid URACE allocation effort')
    providers = {}
    for provider, model in [('codex', 'gpt-5.6-sol'), ('claude', 'claude-sonnet-4-6')]:
        value = native.get(provider, {})
        allocation = overrides.get(provider, effort)
        matched=[]
        for entry in config.get('executor', {}).get('providers', []):
            adapter = entry.get('adapter', config.get('executor', {}).get('kind', ''))
            if adapter == provider + '-cli':
                matched.append(entry)
                value = {**value, **native.get(entry['id'], {})}
                allocation = overrides.get(entry['id'], allocation)
        model = value.get('model', model)
        native_effort = value.get('native_effort', 'medium')
        if not isinstance(model, str) or not model.strip() or model.startswith('-') or any(ord(c) < 32 for c in model):
            raise ValueError('Invalid native model')
        if native_effort not in ('low', 'medium', 'high'):
            raise ValueError('Invalid native effort')
        providers[provider] = {'enabled': any(p.get('enabled',True) for p in matched) if config.get('executor',{}).get('providers') else True, 'model': model, 'native_effort': native_effort, 'resource_effort': allocation}
    paused=False
    state_value=config.get('state_path')
    active=config.get('active_product')
    if active:
        entry=next((p for p in config.get('product_registry',[]) if p.get('name')==active and p.get('status','ACTIVE')=='ACTIVE'),None)
        if entry:state_value=entry['state_path']
    if state_value:
        state_path=Path(state_value)
        if not state_path.is_absolute():state_path=base.parent/'runtime'/state_path
        if state_path.exists():paused=json.loads(state_path.read_text()).get('lifecycle_state')=='PAUSED'
    adaptive={}
    observation=base/'allocation-observation.json';clock=base/'trial-clock.json'
    if observation.exists() and clock.exists():
        import time
        value=json.loads(observation.read_text())
        if value.get('trial_id')==json.loads(clock.read_text()).get('trial_id') and value.get('expires_unix',0)>time.time():
            for provider,entry in value.get('providers',{}).items():
                delay=entry.get('delay_seconds')
                if provider in providers and entry.get('mode')==providers[provider]['resource_effort'] and type(delay) in (int,float) and 1<=delay<=60:
                    adaptive[provider]=delay
    return {'workflow':config.get('execution_workflow','core'),'paused':paused,'executor_enabled':config.get('executor',{}).get('enabled',True) is True,'auto_goals': enabled, 'replenish_backlog': enabled and replenish, 'resources': {'effort': effort, 'executor_effort': overrides, 'adaptive_delay_seconds':adaptive}, 'executors': providers}


def task_eligibility(providers, controls, rows, now):
    """Effort adjusts inter-task idle time, independently for each provider."""
    from datetime import datetime
    delays = {'low': 60, 'medium': 15, 'high': 5}
    ready, waits = [], {}
    for provider in providers:
        finishes = []
        for row in rows:
            if row.get('kind') != 'finished' or row.get('provider') != provider:
                continue
            try:
                finishes.append(datetime.fromisoformat(row['at']).timestamp() + max(0, row.get('wall_seconds') or 0))
            except (KeyError, ValueError, TypeError):
                continue
        delay = controls['resources'].get('adaptive_delay_seconds',{}).get(provider,delays[controls['executors'][provider]['resource_effort']])
        remaining = max(finishes, default=0) + delay - now
        if remaining > 0:
            waits[provider] = {'reason': 'Configured allocation inter-task delay', 'retry_in_seconds': remaining}
        else:
            ready.append(provider)
    return ready, waits
