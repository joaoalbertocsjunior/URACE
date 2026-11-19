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

def _l(description: str = '') -> dict:
    return {'type': 'list', 'default': [], 'description': description}

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
    },
    'executor': {
        '_description': 'AI executor provider settings.',
        'enabled':                      _b(False, 'Enable AI executor calls'),
        'freeform_max_tokens_per_24h':  _i(200000, 'Daily freeform routing token budget (0=unlimited)'),
        'freeform_max_tokens_per_call': _i(0,      'Per-call freeform token ceiling (0=unlimited)'),
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
