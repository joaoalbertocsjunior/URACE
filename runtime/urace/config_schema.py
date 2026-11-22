"""Single source of truth for config.json user-facing fields.

Provides schema definition, validation, default extraction, and
dotted-path get/set helpers.  CLI flags remain valid overrides; this
module drives the config-first UX and urace config get/set/validate/init.

Only user-facing fields are enumerated.  Unknown keys in a real config
file are passed through without error — they come from internal bootstrap
or product overlays.
"""
from __future__ import annotations
import json
from typing import Any

# ── leaf node constructors ──────────────────────────────────────────────────

def _b(default: bool, description: str = '') -> dict:
    return {'type': 'bool', 'default': default, 'description': description}

def _i(default: int, description: str = '') -> dict:
    return {'type': 'int', 'default': default, 'description': description}

def _s(default: str, description: str = '') -> dict:
    return {'type': 'str', 'default': default, 'description': description}

def _e(options: list, default: str, description: str = '') -> dict:
    return {'type': 'enum', 'options': options, 'default': default, 'description': description}

def _f(default: float, description: str = '') -> dict:
    return {'type': 'float', 'default': default, 'description': description}

def _l(description: str = '') -> dict:
    return {'type': 'list', 'default': [], 'description': description}

def _d(description: str = '') -> dict:
    return {'type': 'object', 'default': {}, 'description': description}

# ── schema ──────────────────────────────────────────────────────────────────
# Structure: {section: {field: leaf_node | nested_section}}
# A dict without a "type" key is a nested section.
# _description on a section is advisory only.

SCHEMA: dict[str, Any] = {
    'capability_flags': {
        '_description': 'Granular feature toggles. Absent keys default to enabled.',
        'executor_enabled':          _b(True,  'Allow AI executor calls'),
        'freeform_enabled':          _b(True,  'Allow natural-language freeform input routing'),
        'machine_interface_enabled': _b(True,  'Allow M2M JSON interface (urace m2m)'),
        'compress_enabled':          _b(True,  'Allow state compaction (urace compact)'),
        'decompress_enabled':        _b(True,  'Allow state decompaction (urace decompact)'),
        'p2p_mint_enabled':          _b(False, 'Allow minting tokens from accepted improvements'),
        'p2p_sell_enabled':          _b(False, 'Allow listing features for sale on P2P exchange'),
        'p2p_borrow_enabled':        _b(False, 'Allow borrowing features from P2P exchange'),
        'context_mint_enabled':      _b(True,  'Allow minting context records'),
        'compliance_mode':           _b(False, 'Enable strict compliance enforcement'),
    },
    'network': {
        '_description': 'P2P exchange network settings.',
        'enabled':         _b(False,    'Enable the P2P exchange network'),
        'mode':            _e(['intranet', 'internet', 'hybrid'], 'hybrid', 'Network scope'),
        'port':            _i(7301,     'HTTP RPC listen port'),
        'bootstrap_peers': _l('Bootstrap peer HTTPS endpoints'),
        'advertise':       _b(False,    'Advertise this peer to bootstrap nodes'),
        'relay_only':      _b(False,    'Route all traffic through relays (hides local IP)'),
        'admission_quarantine_enabled': _b(True, 'Gate new peers through quarantine until protocol_gen is verified'),
        'relay_failure_threshold':  _i(5, 'Consecutive heartbeat failures before removing a relay-path peer'),
        'direct_failure_threshold': _i(2, 'Consecutive heartbeat failures before removing a direct-path peer'),
    },
    'executor': {
        '_description': 'AI executor provider settings.',
        'enabled':                      _b(False, 'Enable AI executor calls'),
        'freeform_max_tokens_per_24h':  _i(200000, 'Daily freeform routing token budget (0=unlimited)'),
        'freeform_max_tokens_per_call': _i(0,      'Per-call freeform token ceiling (0=unlimited)'),
        'freeform_confidence_threshold': _f(0.8,   'Min classification confidence to auto-queue (0–1); items below are deferred'),
        'freeform_max_clarification_turns': _i(2,  'Max interactive clarification rounds per freeform call (0 = disable)'),
        'freeform_p2p_top_n':           _i(10,     'Max P2P candidates surfaced per freeform route (1–100)'),
        'freeform_cache_ttl_seconds':   _i(3600,   'Freeform routing cache TTL in seconds (0 = disable cache)'),
        'freeform_semantic_scorer':     _s('tfidf','P2P candidate scorer: lexical or tfidf'),
        'freeform_confidence_thresholds': _d('Per-item-type confidence overrides e.g. {"command":0.9,"goal":0.75}'),
        'agora_quorum_threshold':       _f(0.5,   'Minimum fraction of cohort that must vote for quorum (0–1)'),
        'agora_proposal_ttl_hours':     _i(72,    'Hours before a proposal expires and can no longer be voted on or decided'),
    },
    'api': {
        '_description': 'MCP and A2A server settings.',
        'mcp': {
            '_description': 'Model Context Protocol server.',
            'enabled': _b(False, 'Enable MCP server'),
        },
        'a2a': {
            '_description': 'Agent-to-Agent JSON-RPC server.',
            'enabled': _b(False, 'Enable A2A server'),
            'port':    _i(8080,  'A2A server listen port'),
        },
    },
    'resources': {
        '_description': 'Resource allocation settings.',
        'effort': _e(['low', 'medium', 'high', 'inherit'], 'medium', 'Default effort level for improvement cycles'),
    },
    'auto_goals': {
        '_description': 'Automatic goal generation.',
        'enabled':           _b(False, 'Enable automatic goal suggestions'),
        'replenish_backlog': _b(True,  'Replenish active goal backlog when it empties'),
    },
    'evaluation_system': {
        '_description': 'Improvement evaluation scoring.',
        'minimum_evidence_units': _i(5, 'Minimum evidence records required before accepting an improvement'),
    },
    'execution_workflow': _e(['core', 'specification-trial'], 'core',
        'Improvement workflow: core (default) or specification-trial'),
    'self_evolution_policy': {
        '_description': 'Controls whether URACE may improve its own runtime.',
        'mode': _e(['NECESSARY_ONLY', 'CONTINUOUS', 'DISABLED'], 'NECESSARY_ONLY',
            'NECESSARY_ONLY: evolve only when blocked; CONTINUOUS: always eligible; DISABLED: off'),
    },
    'analytics_export': {
        '_description': 'Automatic report export settings.',
        'mode': _e(['DISABLED', 'ON_DEMAND', 'ON_CHECKPOINT'], 'DISABLED', 'When to export analytics reports'),
    },
    'github': {
        '_description': 'GitHub integration settings.',
        'token_env': _s('URACE_GITHUB_TOKEN', 'Environment variable holding the GitHub token'),
    },
    'logging': {
        '_description': 'Runtime logging configuration.',
        'level':      _e(['DEBUG', 'INFO', 'WARNING', 'ERROR'], 'WARNING',
                         'Root log level; filters all categories unless overridden per-component'),
        'format':     _e(['text', 'json'], 'text', 'Log line format: human-readable text or JSON-lines'),
        'file':       _s('', 'Path for rotating log file; empty string = stderr only'),
        'max_bytes':  _i(10_485_760, 'Rotating log file max size in bytes (default 10 MB)'),
        'backup_count': _i(5, 'Number of rotated log files to keep'),
        'audit_tier': _b(True,  'Write audit-tier events to the signed journal'),
        'm2m_stream': _b(True,  'Publish events to the M2M log stream endpoint'),
        'm2m_diagnostic': _b(False, 'Include diagnostic-tier events (executor I/O) in M2M stream'),
        'redact_executor_output': _b(True, 'Strip executor prompt/response text from operational events'),
        'components': {
            '_description': 'Per-component level overrides. true=inherit root level, false=silent.',
            'source':    _b(True, 'Source adapter lifecycle and sync events'),
            'm2m':       _b(True, 'M2M API request/response events'),
            'config':    _b(True, 'Config read/write events'),
            'lifecycle': _b(True, 'Runtime process lifecycle events'),
            'cycle':     _b(True, 'Improvement cycle events'),
            'cost':      _b(True, 'Credit and cost events'),
            'exchange':  _b(True, 'P2P exchange events'),
            'executor':  _b(True, 'Executor call events'),
            'security':  _b(True, 'Security events (cannot be disabled)'),
            'audit':     _b(True, 'Audit journal events (cannot be disabled)'),
        },
    },
    'p2p': {
        '_description': 'P2P feature economics settings.',
        'mint': {
            '_description': 'Feature minting constraints.',
            'min_evidence_borrows': _i(5,  'Minimum verified borrows before REPRICE_OBSERVED fires'),
            'trial_escrow_pct':     _i(10, 'Percent of borrow cost held in escrow during trial'),
        },
        'pricing': {
            '_description': 'Pricing jitter and floor parameters.',
            'jitter_frac':                 _i(0, 'Borrow jitter fraction ×1000 (3 = 0.3 %)'),
            'earn_jitter_frac':            _i(0, 'Earn jitter fraction ×1000 (5 = 0.5 %)'),
            'consensus_floor_multiplier':  _i(0, 'Consensus floor multiplier ×100 (50 = 0.50)'),
        },
    },
    'feature_matching': {
        '_description': 'Product-to-market feature matching weights (must sum to 1.0).',
        'layer1_strict':            _b(True, 'Hard-block on MIME/dep/license mismatch (layer 1)'),
        'layer2_tfidf_weight':      _i(0, 'TF-IDF similarity weight ×100 (40 = 0.40)'),
        'layer2_outcome_weight':    _i(0, 'Outcome fingerprint weight ×100 (40 = 0.40)'),
        'layer2_propagation_weight': _i(0, 'Propagation score weight ×100 (20 = 0.20)'),
    },
    'mime_policy': {
        '_description': 'MIME type enforcement settings.',
        'network_policy': _e(
            ['quality_gate_only', 'hard_protected_only', 'all_allowed', 'custom'],
            'quality_gate_only',
            'Network-level MIME gate applied to all receive/mint/replicate paths',
        ),
    },
    'config_version': {"type": "integer", "minimum": 1, "default": 1},
    'sources': {
        '_description': 'Source adapter settings.',
        'auto_sync_interval_s': _i(300, 'Seconds between automatic source sync cycles (0=disabled)'),
        'allow_act': _b(False, 'Enable act() path globally — sources can be acted upon only when True'),
        'act_audit_all': _b(True, 'Log every act() call regardless of outcome'),
    },
    'routing': {
        '_description': 'Routing affinity and cache-aware selection settings.',
        'affinity_enabled':              _b(True,  'Enable cache-key and session-hint affinity routing'),
        'cache_evidence_ttl_seconds':    _i(900,   'TTL for in-process cache-affinity evidence (seconds)'),
        'cache_min_saved_tokens':        _i(256,   'Minimum matched tokens before cache evidence changes routing'),
        'demand_window_seconds':         _i(60,    'Rolling window for request-rate demand tracking (seconds)'),
        'tps_weight_min':                _f(0.3,   'Minimum routing weight for slow/cold executors'),
        'tps_weight_max':                _f(2.0,   'Maximum routing weight for fast executors'),
        'throughput_window_seconds':     _i(900,   'Rolling window for TPS measurement (seconds)'),
        'reference_tps':                 _f(10.0,  'Reference tok/s used to normalize routing weights'),
        'local_rep_penalty_window_seconds': _i(300,'How long a failed target remains penalized (seconds)'),
    },
}

# ── helpers ─────────────────────────────────────────────────────────────────

def _is_leaf(node: Any) -> bool:
    return isinstance(node, dict) and 'type' in node


def _walk(schema: dict, prefix: str = '') -> list[tuple[str, dict]]:
    """Yield (dotted_path, leaf_node) for every leaf in schema."""
    result = []
    for key, value in schema.items():
        if key.startswith('_'):
            continue
        path = f'{prefix}.{key}' if prefix else key
        if _is_leaf(value):
            result.append((path, value))
        elif isinstance(value, dict):
            result.extend(_walk(value, path))
    return result


def _get_nested(d: dict, parts: list[str]) -> Any:
    cur = d
    for part in parts:
        if not isinstance(cur, dict):
            raise KeyError(part)
        cur = cur[part]
    return cur


def _set_nested(d: dict, parts: list[str], value: Any) -> None:
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value

# ── public API ───────────────────────────────────────────────────────────────

def validate(config: dict) -> list[dict]:
    """Return a list of {path, error} dicts for every schema violation found."""
    errors = []
    for path, leaf in _walk(SCHEMA):
        parts = path.split('.')
        try:
            value = _get_nested(config, parts)
        except KeyError:
            continue  # missing key uses default — not an error
        expected = leaf['type']
        if expected == 'bool':
            if not isinstance(value, bool):
                errors.append({'path': path, 'error': f'expected bool, got {type(value).__name__}'})
        elif expected == 'int':
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append({'path': path, 'error': f'expected int, got {type(value).__name__}'})
            elif value < 0:
                errors.append({'path': path, 'error': 'must be >= 0'})
        elif expected == 'str':
            if not isinstance(value, str):
                errors.append({'path': path, 'error': f'expected string, got {type(value).__name__}'})
        elif expected == 'enum':
            if value not in leaf['options']:
                errors.append({'path': path, 'error': f'must be one of {leaf["options"]}, got {value!r}'})
        elif expected == 'list':
            if not isinstance(value, list):
                errors.append({'path': path, 'error': f'expected list, got {type(value).__name__}'})
        elif expected == 'object':
            if not isinstance(value, dict):
                errors.append({'path': path, 'error': f'expected object, got {type(value).__name__}'})
    return errors


def defaults() -> dict:
    """Return a nested dict of schema default values."""
    result: dict = {}
    for path, leaf in _walk(SCHEMA):
        _set_nested(result, path.split('.'), leaf['default'])
    return result


def fields() -> list[dict]:
    """Return flat list of {path, type, default, description} for all leaf fields."""
    return [
        {'path': path, 'type': leaf['type'], 'default': leaf['default'],
         'description': leaf['description'],
         **({'options': leaf['options']} if 'options' in leaf else {})}
        for path, leaf in _walk(SCHEMA)
    ]


def get_value(config: dict, path: str) -> Any:
    """Get a dotted-path value from config. Raises KeyError if not found."""
    return _get_nested(config, path.split('.'))


def set_value(config: dict, path: str, raw_value: str) -> Any:
    """Coerce raw_value string to the schema type and set it in config.

    Returns the coerced value.  Raises ValueError for type mismatches.
    """
    parts = path.split('.')
    # Find the schema leaf (may not exist for unlisted keys — treat as str)
    leaf = None
    schema_node: Any = SCHEMA
    for part in parts:
        if isinstance(schema_node, dict) and part in schema_node and not part.startswith('_'):
            schema_node = schema_node[part]
            if _is_leaf(schema_node):
                leaf = schema_node
                break
        else:
            schema_node = None
            break

    if leaf is None:
        # Unknown path — store raw string; callers may JSON-parse if needed
        coerced: Any = raw_value
    elif leaf['type'] == 'bool':
        if raw_value.lower() in ('true', '1', 'yes'):
            coerced = True
        elif raw_value.lower() in ('false', '0', 'no'):
            coerced = False
        else:
            raise ValueError(f'{path}: expected true/false, got {raw_value!r}')
    elif leaf['type'] == 'int':
        try:
            coerced = int(raw_value)
        except ValueError:
            raise ValueError(f'{path}: expected integer, got {raw_value!r}')
        if coerced < 0:
            raise ValueError(f'{path}: must be >= 0')
    elif leaf['type'] == 'enum':
        if raw_value not in leaf['options']:
            raise ValueError(f'{path}: must be one of {leaf["options"]}, got {raw_value!r}')
        coerced = raw_value
    elif leaf['type'] == 'list':
        try:
            coerced = json.loads(raw_value)
        except json.JSONDecodeError:
            # Accept comma-separated as a convenience
            coerced = [v.strip() for v in raw_value.split(',') if v.strip()]
        if not isinstance(coerced, list):
            raise ValueError(f'{path}: expected a JSON array or comma-separated list')
    elif leaf['type'] == 'object':
        try:
            coerced = json.loads(raw_value)
        except json.JSONDecodeError:
            raise ValueError(f'{path}: expected a JSON object')
        if not isinstance(coerced, dict):
            raise ValueError(f'{path}: expected a JSON object')
    else:
        coerced = raw_value

    _set_nested(config, parts, coerced)
    return coerced


def init_template() -> str:
    """Return an annotated JSON5-style config template as a string.

    Comments use // notation so the file is readable; callers must strip
    comments before parsing as JSON (or write a .jsonc file).
    """
    lines = ['{']
    for path, leaf in _walk(SCHEMA):
        parts = path.split('.')
        if len(parts) > 1:
            continue  # only emit top-level keys; nested handled below
    # Build section by section
    sections = {}
    for path, leaf in _walk(SCHEMA):
        top = path.split('.')[0]
        sections.setdefault(top, []).append((path, leaf))

    section_items = list(sections.items())
    for s_idx, (section, leaves) in enumerate(section_items):
        schema_node = SCHEMA.get(section)
        desc = schema_node.get('_description', '') if isinstance(schema_node, dict) else (
            schema_node.get('description', '') if _is_leaf(schema_node) else '')
        if desc:
            lines.append(f'  // {desc}')
        if _is_leaf(schema_node):
            # top-level scalar
            default_val = json.dumps(schema_node['default'])
            opts = f' options: {schema_node["options"]}' if 'options' in schema_node else ''
            lines.append(f'  // type: {schema_node["type"]}{opts}')
            lines.append(f'  "{section}": {default_val}' + (',' if s_idx < len(section_items) - 1 else ''))
        else:
            lines.append(f'  "{section}": {{')
            # group by sub-section
            sub_items = {}
            for path, leaf in leaves:
                sub_key = path.split('.')[1] if len(path.split('.')) > 1 else path
                sub_items.setdefault(sub_key, []).append((path, leaf))
            sub_list = list(sub_items.items())
            for sub_idx, (sub_key, sub_leaves) in enumerate(sub_list):
                if len(sub_leaves) == 1 and sub_leaves[0][0].count('.') == 1:
                    # direct leaf
                    _, leaf = sub_leaves[0]
                    opts = f' options: {leaf["options"]}' if 'options' in leaf else ''
                    if leaf['description']:
                        lines.append(f'    // {leaf["description"]}. type: {leaf["type"]}{opts}')
                    default_val = json.dumps(leaf['default'])
                    comma = ',' if sub_idx < len(sub_list) - 1 else ''
                    lines.append(f'    "{sub_key}": {default_val}{comma}')
                else:
                    # nested section
                    nested_node = SCHEMA.get(section, {}).get(sub_key, {})
                    nested_desc = nested_node.get('_description', '') if isinstance(nested_node, dict) else ''
                    if nested_desc:
                        lines.append(f'    // {nested_desc}')
                    lines.append(f'    "{sub_key}": {{')
                    nested_list = [(p, l) for p, l in sub_leaves if p.count('.') > 1]
                    for n_idx, (path, leaf) in enumerate(nested_list):
                        field = path.split('.')[-1]
                        opts = f' options: {leaf["options"]}' if 'options' in leaf else ''
                        if leaf['description']:
                            lines.append(f'      // {leaf["description"]}. type: {leaf["type"]}{opts}')
                        default_val = json.dumps(leaf['default'])
                        comma = ',' if n_idx < len(nested_list) - 1 else ''
                        lines.append(f'      "{field}": {default_val}{comma}')
                    nested_comma = ',' if sub_idx < len(sub_list) - 1 else ''
                    lines.append(f'    }}{nested_comma}')
            section_comma = ',' if s_idx < len(section_items) - 1 else ''
            lines.append(f'  }}{section_comma}')
    lines.append('}')
    return '\n'.join(lines)


# ── Pydantic v2 typed model ──────────────────────────────────────────────────
# URACEConfig provides structured validation with typed fields.
# model_validate_config() returns errors in the same format as validate()
# so callers can switch without changing error-handling code.

try:
    from pydantic import BaseModel, Field
    from typing import Literal

    class _CapabilityFlags(BaseModel):
        model_config = {"extra": "allow"}
        executor_enabled: bool = True
        freeform_enabled: bool = True
        machine_interface_enabled: bool = True
        compress_enabled: bool = True
        decompress_enabled: bool = True
        p2p_mint_enabled: bool = False
        p2p_sell_enabled: bool = False
        p2p_borrow_enabled: bool = False
        context_mint_enabled: bool = True
        compliance_mode: bool = False

    class _NetworkConfig(BaseModel):
        model_config = {"extra": "allow"}
        enabled: bool = False
        mode: Literal["intranet", "internet", "hybrid"] = "hybrid"
        port: int = Field(default=7301, ge=1, le=65535)
        bootstrap_peers: list[str] = Field(default_factory=list)
        advertise: bool = False
        relay_only: bool = False
        admission_quarantine_enabled: bool = True
        relay_failure_threshold: int = Field(default=5, ge=1)
        direct_failure_threshold: int = Field(default=2, ge=1)

    class _McpConfig(BaseModel):
        model_config = {"extra": "allow"}
        enabled: bool = False

    class _A2aConfig(BaseModel):
        model_config = {"extra": "allow"}
        enabled: bool = False
        port: int = Field(default=8080, ge=1, le=65535)

    class _ApiConfig(BaseModel):
        model_config = {"extra": "allow"}
        mcp: _McpConfig = Field(default_factory=_McpConfig)
        a2a: _A2aConfig = Field(default_factory=_A2aConfig)

    class _ExecutorConfig(BaseModel):
        model_config = {"extra": "allow"}
        enabled: bool = False
        config_version: int = Field(default=1, ge=1)
        freeform_max_tokens_per_24h: int = Field(default=200000, ge=0)
        freeform_max_tokens_per_call: int = Field(default=0, ge=0)
        freeform_confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
        freeform_max_clarification_turns: int = Field(default=2, ge=0)
        freeform_p2p_top_n: int = Field(default=10, ge=1, le=100)
        freeform_cache_ttl_seconds: int = Field(default=3600, ge=0)
        freeform_semantic_scorer: str = 'tfidf'
        freeform_confidence_thresholds: dict = Field(default_factory=dict)
        agora_quorum_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
        agora_proposal_ttl_hours: int = Field(default=72, ge=1)

    class _ResourcesConfig(BaseModel):
        model_config = {"extra": "allow"}
        effort: Literal["low", "medium", "high", "inherit"] = "medium"

    class _AutoGoalsConfig(BaseModel):
        model_config = {"extra": "allow"}
        enabled: bool = False
        replenish_backlog: bool = True

    class _EvaluationSystemConfig(BaseModel):
        model_config = {"extra": "allow"}
        minimum_evidence_units: int = Field(default=5, ge=0)

    class _SelfEvolutionPolicy(BaseModel):
        model_config = {"extra": "allow"}
        mode: Literal["NECESSARY_ONLY", "CONTINUOUS", "DISABLED"] = "NECESSARY_ONLY"

    class _AnalyticsExport(BaseModel):
        model_config = {"extra": "allow"}
        mode: Literal["DISABLED", "ON_DEMAND", "ON_CHECKPOINT"] = "DISABLED"

    class _GithubConfig(BaseModel):
        model_config = {"extra": "allow"}
        token_env: str = "URACE_GITHUB_TOKEN"
        repo: str = ""

    class _RoutingConfig(BaseModel):
        model_config = {"extra": "allow"}
        affinity_enabled: bool = True
        cache_evidence_ttl_seconds: int = Field(default=900, ge=0)
        cache_min_saved_tokens: int = Field(default=256, ge=0)
        demand_window_seconds: int = Field(default=60, ge=10)
        tps_weight_min: float = Field(default=0.3, ge=0.0, le=1.0)
        tps_weight_max: float = Field(default=2.0, ge=1.0)
        throughput_window_seconds: int = Field(default=900, ge=60)
        reference_tps: float = Field(default=10.0, ge=0.1)
        local_rep_penalty_window_seconds: int = Field(default=300, ge=30)

    class URACEConfig(BaseModel):
        """Typed model for config.json. Extra keys are passed through (product overlays)."""
        model_config = {"extra": "allow"}

        capability_flags: _CapabilityFlags = Field(default_factory=_CapabilityFlags)
        network: _NetworkConfig = Field(default_factory=_NetworkConfig)
        executor: _ExecutorConfig = Field(default_factory=_ExecutorConfig)
        api: _ApiConfig = Field(default_factory=_ApiConfig)
        resources: _ResourcesConfig = Field(default_factory=_ResourcesConfig)
        auto_goals: _AutoGoalsConfig = Field(default_factory=_AutoGoalsConfig)
        evaluation_system: _EvaluationSystemConfig = Field(default_factory=_EvaluationSystemConfig)
        execution_workflow: Literal["core", "specification-trial"] = "core"
        self_evolution_policy: _SelfEvolutionPolicy = Field(default_factory=_SelfEvolutionPolicy)
        analytics_export: _AnalyticsExport = Field(default_factory=_AnalyticsExport)
        github: _GithubConfig = Field(default_factory=_GithubConfig)
        routing: _RoutingConfig = Field(default_factory=_RoutingConfig)

    def model_validate_config(config: dict) -> list[dict]:
        """Validate config using pydantic. Returns [{path, error}] like validate()."""
        from pydantic import ValidationError
        try:
            URACEConfig.model_validate(config)
            return []
        except ValidationError as exc:
            return [
                {"path": ".".join(str(loc) for loc in e["loc"]), "error": e["msg"]}
                for e in exc.errors()
            ]

    _PYDANTIC_AVAILABLE = True

except ImportError:
    _PYDANTIC_AVAILABLE = False
    URACEConfig = None  # type: ignore[assignment,misc]

    def model_validate_config(config: dict) -> list[dict]:
        """Fallback: delegates to validate() when pydantic is not installed."""
        return validate(config)
