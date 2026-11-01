"""Independent operator controls for URACE allocation and native executors."""
EFFORTS = {"low", "medium", "high"}
PROFILES = {
    "low": {"initial_matched_samples_per_effort": 2, "descriptive_wilson_lower_target": .80},
    "medium": {"initial_matched_samples_per_effort": 5, "descriptive_wilson_lower_target": .90},
    "high": {"initial_matched_samples_per_effort": 10, "descriptive_wilson_lower_target": .95},
}
def auto_goals(config):
    flags = config.get("auto_goals", {})
    enabled = flags.get("enabled", True) is True
    replenish = flags.get("replenish_backlog", True) is True
    return {"enabled": enabled, "replenish_backlog": replenish, "effective_replenishment": enabled and replenish}
def effort_mode(settings, provider=None, adapter=None):
    overrides=settings.get("executor_effort", {})
    mode=overrides.get(provider,overrides.get(adapter,settings.get("effort","medium")))
    if mode not in EFFORTS:
        raise ValueError("URACE resource effort must be low, medium or high")
    return mode
def resource_profile(config, provider=None):
    entry=next((p for p in config.get("executor",{}).get("providers",[]) if p.get("id")==provider),{})
    mode = effort_mode(config.get("resources", {}), provider,str(entry.get("adapter","")).removesuffix("-cli"))
    return {"effort": mode, **PROFILES[mode]}
def native_settings(config, provider):
    return dict(config.get("executor", {}).get("native_options", {}).get(provider, {}))

def discovery_interval(config, state, base, maximum, streak):
    """Adjust opportunity-assessment cadence, retaining failure/yield guards.

    This is an inspectable allocation policy, not an optimality claim. Native
    reasoning remains governed exclusively by native_options.
    """
    provider = state.get('executor_state', {}).get('provider_pool', {}).get('last_selected_provider')
    profile = resource_profile(config, provider)
    factor = {'low': 4.0, 'medium': 1.0, 'high': .25}[profile['effort']]
    interval = min(maximum, max(0, base) * factor * (2 ** min(streak, 12)))
    return {**profile, 'provider': provider, 'discovery_interval_seconds': interval,
            'strategy': 'effort-scaled assessment cadence with observed no-yield backoff',
            'optimality_established': False}
