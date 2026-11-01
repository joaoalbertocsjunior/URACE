"""Explicit operator bootstrap: reuse real onboarding checks, discover installed clients."""
import copy,shutil,json

def complete(cli,config):
    # Keep initialization, onboarding and lifecycle authority as separately validated operations.
    code=cli.main(['init'])
    if code:return code
    configured=copy.deepcopy(config);executor=configured.setdefault('executor',{});providers=executor.setdefault('providers',[])
    executor.setdefault('max_executor_calls_per_24h',None)
    executor.setdefault('max_executor_calls_per_30d',None)
    executor.setdefault('capacity_fallback_seconds',18900)
    discovered=[];discovered_ids=set()
    for name in ('codex','claude'):
        binary=shutil.which(name)
        if not binary:continue
        same=[p for p in providers if p.get('adapter')==name+'-cli']
        if not same:
            p={'id':name,'adapter':name+'-cli','command':binary,'model':('claude-sonnet-4-6' if name=='claude' else executor.get('model','gpt-5.6-sol')),'enabled':True,'capabilities':(['discovery','planning','evaluation'] if name=='claude' and not executor.get('workspace_write_validated',False) else ['discovery','planning','mutation','evaluation','execution']),'max_calls_per_24h':executor.get('max_executor_calls_per_24h'),'max_calls_per_30d':executor.get('max_executor_calls_per_30d')}
            providers.append(p);discovered_ids.add(id(p))
        else:
            for p in same:p['command']=binary;discovered_ids.add(id(p))
        discovered.append(name)
    available=[p for p in providers if p.get('enabled',True) and (id(p) in discovered_ids or shutil.which(p.get('command','')))]
    if not available:
        print(json.dumps({'status':'setup_required','reason':'No enabled installed executor client; install/authenticate a supported client, then rerun init --ready'}));return 2
    executor['enabled']=True
    configured.setdefault('auto_goals',{}).setdefault('enabled',True)
    configured['auto_goals'].setdefault('replenish_backlog',True)
    configured.setdefault('resources',{}).setdefault('effort','medium')
    with cli.state_lock(cli.state_path(configured)):cli.save_config(configured)
    # This is the real operator-confirmation path, not a synthetic seeded OnboardRecord.
    code=cli.main(['onboard','confirm'])
    if code:return code
    print(json.dumps({'status':'ready','next_command':'urace auto','executors':[p['id'] for p in available],'installed_client_discovery':discovered,'authentication':'Native providers verify account access at dispatch; installation alone is not authentication','resource_effort':configured['resources']['effort']}))
    return 0
