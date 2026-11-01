"""Runtime cycle settings; canonical package alternative to trial/runtime_cycle.settings."""

SCHEMA = 'runtime-cycle-v1'
DEFAULTS = {'enabled': False, 'auto_deploy': True, 'interval_seconds': 10800}


def settings(config):
    wf = config.get('runtime_workflow', {})
    result = {
        'enabled': wf.get('enabled', DEFAULTS['enabled']),
        'auto_deploy': wf.get('auto_deploy', DEFAULTS['auto_deploy']),
        'interval_seconds': wf.get('interval_seconds', DEFAULTS['interval_seconds']),
    }
    if (type(result['enabled']) is not bool
            or type(result['auto_deploy']) is not bool
            or type(result['interval_seconds']) is not int
            or not 60 <= result['interval_seconds'] <= 86400):
        raise ValueError('Invalid runtime-cycle controls')
    return result
