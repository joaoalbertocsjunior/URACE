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


def auto_complete(cli, config):
    """Zero-config init: detect API keys, configure executor, verify health."""
    import os, shutil, json, copy
    steps = []

    # Step 1: init state
    code = cli.main(['init'])
    steps.append({'step': 'init_state', 'status': 'ok' if code == 0 else 'already_exists'})

    # Step 2: detect API keys → auto-configure executor
    configured = copy.deepcopy(config)
    executor = configured.setdefault('executor', {})
    providers = executor.setdefault('providers', [])
    detected = []
    caps = ['discovery', 'planning', 'mutation', 'evaluation', 'execution']

    if os.environ.get('ANTHROPIC_API_KEY'):
        binary = shutil.which('claude')
        existing = [p for p in providers if p.get('id') == 'env-claude' or p.get('adapter') == 'claude-cli']
        if not existing:
            providers.append({
                'id': 'env-claude', 'adapter': 'claude-cli',
                'command': binary or 'claude', 'priority': 90,
                'capabilities': caps, 'enabled': True,
                '_source': 'ANTHROPIC_API_KEY',
            })
            detected.append('env-claude (ANTHROPIC_API_KEY)')
    if os.environ.get('OPENAI_API_KEY'):
        binary = shutil.which('codex')
        existing = [p for p in providers if p.get('id') == 'env-openai' or p.get('adapter') == 'codex-cli']
        if not existing:
            providers.append({
                'id': 'env-openai', 'adapter': 'codex-cli',
                'command': binary or 'codex', 'priority': 80,
                'capabilities': caps, 'enabled': True,
                '_source': 'OPENAI_API_KEY',
            })
            detected.append('env-openai (OPENAI_API_KEY)')

    # Step 3: ensure exchange identity
    from . import peer_exchange as _pe
    from ._common import SYSTEM_ROOT
    exchange_root = SYSTEM_ROOT / 'exchange'
    exchange_root.mkdir(parents=True, exist_ok=True)
    _exc = _pe.Exchange(exchange_root)
    identity = _exc.identity()
    steps.append({'step': 'exchange_identity', 'status': 'ok', 'peer_id': identity.get('peer_id', 'unknown')})

    # Step 4: apply sensible defaults
    executor['enabled'] = bool(providers)
    configured.setdefault('auto_goals', {}).setdefault('enabled', True)
    configured.setdefault('resources', {}).setdefault('effort', 'medium')
    if providers or detected:
        with cli.state_lock(cli.state_path(configured)):
            cli.save_config(configured)
    steps.append({'step': 'defaults_applied', 'status': 'ok',
                  'auto_goals': configured['auto_goals']['enabled'],
                  'effort': configured['resources']['effort']})

    # Step 5: doctor check
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main(['doctor', '--json'])
    try:
        doctor = json.loads(buf.getvalue())
    except Exception:
        doctor = {'overall': 'unknown'}
    steps.append({'step': 'doctor', 'status': doctor.get('overall', 'unknown')})

    # Read product_types written by init (auto-detected or explicit)
    from ._common import CONFIG_PATH as _cp
    try:
        _cfg_data = json.loads(_cp.read_text())
        _product_types = _cfg_data.get('product_types', [_cfg_data.get('product_type', 'software')])
    except Exception:
        _product_types = ['software']
    result = {
        'status': 'ready' if doctor.get('overall') in ('OK', 'WARN') else 'needs_attention',
        'auto_detected_providers': detected,
        'executor_providers': len(providers),
        'product_types': _product_types,
        'steps': steps,
        'next_command': 'urace auto' if providers else 'urace init --ready',
        'note': 'Install pysha3 for EVM-compatible wallet addresses' if not shutil.which('pip') else None,
    }
    if not result['note']:
        del result['note']
    print(json.dumps(result, indent=2))
    return 0
