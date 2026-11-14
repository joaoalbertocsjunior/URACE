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

    # Step 3.7: NAT detection → auto-assign node_roles + optimise network_mode
    nat_step = {'step': 'nat_detection'}
    try:
        from . import nat_check as _nc
        from ._common import atomic_write_json
        cap = _nc.check_node_capability(timeout=4.0, upnp_timeout_ms=2000)
        nat_step.update({
            'status': 'ok',
            'nat_type': cap['nat_type'],
            'public_ip': cap['public_ip'],
            'upnp_available': cap['upnp_available'],
            'recommended_roles': cap['recommended_roles'],
            'recommended_network_mode': cap['recommended_network_mode'],
        })
        # Apply recommended network_mode if better than current
        try:
            _policy = _exc.load()
            current_mode = _policy.get('network_mode', 'hybrid')
            new_mode = cap['recommended_network_mode']
            # Only upgrade (intranet < hybrid < internet)
            _mode_rank = {'intranet': 0, 'hybrid': 1, 'internet': 2}
            if _mode_rank.get(new_mode, 0) > _mode_rank.get(current_mode, 0):
                _policy['network_mode'] = new_mode
            # Write node_roles and urace_credit_usd_rate defaults
            if not _policy.get('node_roles'):
                _policy['node_roles'] = cap['recommended_roles']
            _policy.setdefault('urace_credit_usd_rate', 1000)
            atomic_write_json(exchange_root / 'policy.json', _policy)
        except Exception:
            pass
        # UPnP auto-open if relay role assigned
        if cap['can_relay'] and cap['upnp_available']:
            try:
                _nc.auto_open_upnp_port()
            except Exception:
                pass
    except Exception as _e:
        nat_step.update({'status': 'skipped', 'reason': str(_e)})
    steps.append(nat_step)

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
    }
    # Only surface router config hint when explicitly requested (--verbose), not in default output
    if not result.get('note'):
        result.pop('note', None)
    print(json.dumps(result, indent=2))
    return 0
